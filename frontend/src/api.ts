import axios, { AxiosInstance } from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;
export const TOKEN_KEY = "valeteck_token";

export const api: AxiosInstance = axios.create({
  baseURL: `${BASE}/api`,
  timeout: 30000,
});

api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers = config.headers || {};
    (config.headers as any).Authorization = `Bearer ${token}`;
  }
  return config;
});

export function apiErrorMessage(e: any): string {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x: any) => x?.msg || JSON.stringify(x)).join(" • ");
  return e?.message || "Erro desconhecido";
}

export type Photo = { label?: string; base64: string };
export type Checklist = {
  id: string;
  numero: string;
  user_id: string;
  status: "rascunho" | "enviado" | "em_auditoria" | "aprovado" | "reprovado";
  vehicle_type?: string;
  nome: string;
  sobrenome: string;
  placa: string;
  telefone?: string;
  obs_iniciais?: string;
  problems_client?: string[];
  problems_client_other?: string;
  empresa: string;
  equipamento: string;
  tipo_atendimento?: string;
  acessorios: string[];
  obs_tecnicas?: string;
  problems_technician?: string[];
  problems_technician_other?: string;
  battery_state?: string;
  battery_voltage?: number | null;
  photos: Photo[];
  location?: { lat: number; lng: number } | null;
  location_available: boolean;
  signature_base64?: string;
  appointment_id?: string;
  alerts: string[];
  created_at: string;
  updated_at: string;
  sent_at?: string | null;
};
