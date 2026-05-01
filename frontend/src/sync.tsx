import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import NetInfo, { NetInfoState } from "@react-native-community/netinfo";
import { api, apiErrorMessage } from "./api";
import { KEYS, readJson, writeJson } from "./storage";

export type QueueItem = {
  id: string;             // uuid local
  numero_local: string;   // número temporário local (LCL-xxxxx)
  payload: any;           // ChecklistInput completo
  queued_at: string;
  attempts: number;
  last_error?: string;
  status: "pending" | "sending" | "failed" | "sent";
  server_id?: string;
  server_numero?: string;
};

type Ctx = {
  online: boolean;
  queue: QueueItem[];
  syncing: boolean;
  enqueue: (payload: any) => Promise<QueueItem>;
  syncNow: () => Promise<void>;
  removeItem: (id: string) => Promise<void>;
};

const C = createContext<Ctx>({} as any);

function genLocalNumero() {
  const now = new Date();
  const r = Math.random().toString(36).slice(2, 6).toUpperCase();
  return `LCL-${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}-${r}`;
}

export function SyncProvider({ children }: { children: React.ReactNode }) {
  const [online, setOnline] = useState<boolean>(true);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const syncingRef = useRef(false);

  // Carrega fila ao montar
  useEffect(() => {
    (async () => {
      const q = await readJson<QueueItem[]>(KEYS.syncQueue, []);
      setQueue(q);
      setLoaded(true);
    })();
  }, []);

  // Listener de conectividade
  useEffect(() => {
    const unsub = NetInfo.addEventListener((s: NetInfoState) => {
      const isOnline = !!(s.isConnected && s.isInternetReachable !== false);
      setOnline(isOnline);
      if (isOnline) {
        // try sync on reconnect
        setTimeout(() => { void syncNow(); }, 500);
      }
    });
    NetInfo.fetch().then((s) => setOnline(!!(s.isConnected && s.isInternetReachable !== false)));
    return () => unsub();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persiste fila sempre que mudar (apenas após carregar inicial para não sobrescrever)
  useEffect(() => { if (loaded) void writeJson(KEYS.syncQueue, queue); }, [queue, loaded]);

  const enqueue = useCallback(async (payload: any): Promise<QueueItem> => {
    const item: QueueItem = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      numero_local: genLocalNumero(),
      payload,
      queued_at: new Date().toISOString(),
      attempts: 0,
      status: "pending",
    };
    setQueue((q) => [...q, item]);
    return item;
  }, []);

  const removeItem = useCallback(async (id: string) => {
    setQueue((q) => q.filter((x) => x.id !== id));
  }, []);

  const syncNow = useCallback(async () => {
    if (syncingRef.current) return;
    syncingRef.current = true;
    setSyncing(true);
    try {
      // Process one by one (keep fifo)
      const current = await readJson<QueueItem[]>(KEYS.syncQueue, []);
      for (const it of current) {
        if (it.status === "sent") continue;
        // mark sending
        setQueue((q) => q.map((x) => (x.id === it.id ? { ...x, status: "sending", attempts: x.attempts + 1 } : x)));
        try {
          const { data } = await api.post("/checklists", it.payload);
          setQueue((q) => q.map((x) => (x.id === it.id ? { ...x, status: "sent", server_id: data.id, server_numero: data.numero, last_error: undefined } : x)));
          // remove sent items after a short delay so UI can flash "sent"
          setTimeout(() => {
            setQueue((q) => q.filter((x) => x.id !== it.id));
          }, 1500);
        } catch (e: any) {
          const msg = apiErrorMessage(e);
          setQueue((q) => q.map((x) => (x.id === it.id ? { ...x, status: "failed", last_error: msg } : x)));
        }
      }
    } finally {
      syncingRef.current = false;
      setSyncing(false);
    }
  }, []);

  return (
    <C.Provider value={{ online, queue, syncing, enqueue, syncNow, removeItem }}>
      {children}
    </C.Provider>
  );
}

export const useSync = () => useContext(C);
