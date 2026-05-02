import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from "react";
import type { Photo } from "./api";
import { KEYS, readJson, writeJson, removeKey } from "./storage";

export type Draft = {
  vehicle_type: "" | "carro" | "moto";
  vehicle_brand: string;
  vehicle_model: string;
  vehicle_year: string;
  vehicle_color: string;
  vehicle_vin: string;
  vehicle_odometer: string;
  nome: string;
  sobrenome: string;
  placa: string;
  telefone: string;
  obs_iniciais: string;
  problems_client: string[];
  problems_client_other: string;
  empresa: string;
  equipamento: string;
  tipo_atendimento: string;
  acessorios: string[];
  obs_tecnicas: string;
  problems_technician: string[];
  problems_technician_other: string;
  battery_state: string;
  battery_voltage: string;
  imei: string;
  iccid: string;
  device_online: boolean | null;
  device_tested_at: string;
  device_test_message: string;
  execution_started_at: string;
  execution_ended_at: string;
  execution_elapsed_sec: number;
  // v14 — Motor de Comissionamento
  service_type_code: string;        // código da tabela oficial (desinstalacao, instalacao_com_bloqueio, etc.)
  photos: Photo[];
  location: { lat: number; lng: number } | null;
  location_available: boolean;
  signature_base64: string;
  appointment_id: string;
  // FASE 3 — Integração O.S ↔ Estoque
  removed_equipments: { tipo: string; modelo?: string; imei?: string; iccid?: string; serie?: string; estado?: string; notes?: string }[];
  installed_from_inventory_id?: string | null;
};

const empty: Draft = {
  vehicle_type: "",
  vehicle_brand: "",
  vehicle_model: "",
  vehicle_year: "",
  vehicle_color: "",
  vehicle_vin: "",
  vehicle_odometer: "",
  nome: "",
  sobrenome: "",
  placa: "",
  telefone: "",
  obs_iniciais: "",
  problems_client: [],
  problems_client_other: "",
  empresa: "",
  equipamento: "",
  tipo_atendimento: "",
  acessorios: [],
  obs_tecnicas: "",
  problems_technician: [],
  problems_technician_other: "",
  battery_state: "",
  battery_voltage: "",
  imei: "",
  iccid: "",
  device_online: null,
  device_tested_at: "",
  device_test_message: "",
  execution_started_at: "",
  execution_ended_at: "",
  execution_elapsed_sec: 0,
  service_type_code: "",
  photos: [],
  location: null,
  location_available: false,
  signature_base64: "",
  appointment_id: "",
  removed_equipments: [],
  installed_from_inventory_id: null,
};

type Ctx = {
  draft: Draft;
  set: (patch: Partial<Draft>) => void;
  reset: () => void;
  hasStored: boolean;       // true if there's a persisted draft to restore
  loadStored: () => Promise<void>;
  discardStored: () => Promise<void>;
};

const C = createContext<Ctx>({} as any);

function isMeaningful(d: Draft): boolean {
  return !!(d.nome || d.sobrenome || d.placa || d.empresa || d.equipamento || d.photos.length > 0 || d.signature_base64);
}

export function DraftProvider({ children }: { children: React.ReactNode }) {
  const [draft, setDraft] = useState<Draft>(empty);
  const [hasStored, setHasStored] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const saveRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // On mount: check if there's a stored draft (don't auto-apply, just flag)
  useEffect(() => {
    (async () => {
      const stored = await readJson<Draft | null>(KEYS.draftCurrent, null);
      if (stored && isMeaningful(stored)) setHasStored(true);
      setLoaded(true);
    })();
  }, []);

  // Auto-persist on every change (debounced) — só depois de ter carregado
  useEffect(() => {
    if (!loaded) return;
    if (saveRef.current) clearTimeout(saveRef.current);
    saveRef.current = setTimeout(() => {
      if (isMeaningful(draft)) writeJson(KEYS.draftCurrent, draft);
      else removeKey(KEYS.draftCurrent);
    }, 400);
    return () => { if (saveRef.current) clearTimeout(saveRef.current); };
  }, [draft, loaded]);

  const set = useCallback((patch: Partial<Draft>) => setDraft((d) => ({ ...d, ...patch })), []);
  const reset = useCallback(() => {
    setDraft(empty);
    removeKey(KEYS.draftCurrent);
    setHasStored(false);
  }, []);
  const loadStored = useCallback(async () => {
    const stored = await readJson<Draft | null>(KEYS.draftCurrent, null);
    if (stored) setDraft({ ...empty, ...stored });
    setHasStored(false);
  }, []);
  const discardStored = useCallback(async () => {
    await removeKey(KEYS.draftCurrent);
    setHasStored(false);
  }, []);

  return <C.Provider value={{ draft, set, reset, hasStored, loadStored, discardStored }}>{children}</C.Provider>;
}

export const useDraft = () => useContext(C);

// Brazilian plate: ABC1234 (old) or ABC1D23 (Mercosul)
export function isValidPlate(raw: string): boolean {
  const s = (raw || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
  return /^[A-Z]{3}\d[A-Z0-9]\d{2}$/.test(s);
}

export function formatPlate(raw: string): string {
  const s = (raw || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 7);
  if (s.length <= 3) return s;
  return s.slice(0, 3) + "-" + s.slice(3);
}
