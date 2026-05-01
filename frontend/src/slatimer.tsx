import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { useDraft } from "./draft";

type Ctx = { elapsedSec: number; startIfNeeded: () => void; reset: () => void };
const C = createContext<Ctx>({} as any);

export function SLATimerProvider({ children }: { children: React.ReactNode }) {
  const { draft, set } = useDraft();
  const [tick, setTick] = useState(0);
  const interval = useRef<ReturnType<typeof setInterval> | null>(null);

  const startIfNeeded = () => {
    if (!draft.execution_started_at) {
      set({ execution_started_at: new Date().toISOString() });
    }
  };

  const reset = () => {
    set({ execution_started_at: "", execution_ended_at: "", execution_elapsed_sec: 0 });
  };

  useEffect(() => {
    if (draft.execution_started_at && !draft.execution_ended_at) {
      interval.current = setInterval(() => setTick((x) => x + 1), 1000);
      return () => { if (interval.current) clearInterval(interval.current); };
    }
  }, [draft.execution_started_at, draft.execution_ended_at]);

  let elapsedSec = 0;
  if (draft.execution_started_at) {
    const start = new Date(draft.execution_started_at).getTime();
    const end = draft.execution_ended_at ? new Date(draft.execution_ended_at).getTime() : Date.now();
    elapsedSec = Math.floor((end - start) / 1000);
  }

  return <C.Provider value={{ elapsedSec, startIfNeeded, reset }}>{children}</C.Provider>;
}

export const useSLATimer = () => useContext(C);

export function formatSLA(sec: number) {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function slaColor(sec: number) {
  // verde <30min, amarelo 30-60min, vermelho >60min
  if (sec < 1800) return "#22C55E";
  if (sec < 3600) return "#FFA826";
  return "#FF4D4F";
}
