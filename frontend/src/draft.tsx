import React, { createContext, useContext, useState, useCallback } from "react";
import type { Photo } from "./api";

export type Draft = {
  nome: string;
  sobrenome: string;
  placa: string;
  telefone: string;
  obs_iniciais: string;
  empresa: string;
  equipamento: string;
  tipo_atendimento: string;
  acessorios: string[];
  obs_tecnicas: string;
  photos: Photo[];
  location: { lat: number; lng: number } | null;
  location_available: boolean;
  signature_base64: string;
};

const empty: Draft = {
  nome: "",
  sobrenome: "",
  placa: "",
  telefone: "",
  obs_iniciais: "",
  empresa: "",
  equipamento: "",
  tipo_atendimento: "",
  acessorios: [],
  obs_tecnicas: "",
  photos: [],
  location: null,
  location_available: false,
  signature_base64: "",
};

type Ctx = {
  draft: Draft;
  set: (patch: Partial<Draft>) => void;
  reset: () => void;
};

const C = createContext<Ctx>({} as any);

export function DraftProvider({ children }: { children: React.ReactNode }) {
  const [draft, setDraft] = useState<Draft>(empty);
  const set = useCallback((patch: Partial<Draft>) => setDraft((d) => ({ ...d, ...patch })), []);
  const reset = useCallback(() => setDraft(empty), []);
  return <C.Provider value={{ draft, set, reset }}>{children}</C.Provider>;
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
