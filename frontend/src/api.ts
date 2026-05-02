import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

// Storage keys ------------------------------------------------------------
export const TOKEN_KEY = "valeteck_token";              // legacy / access token
export const ACCESS_TOKEN_KEY = "valeteck_access_token";
export const REFRESH_TOKEN_KEY = "valeteck_refresh_token";

// Helpers para token --------------------------------------------------------
export async function setTokens(access: string, refresh?: string | null) {
  await AsyncStorage.multiSet(
    refresh
      ? [
          [TOKEN_KEY, access],
          [ACCESS_TOKEN_KEY, access],
          [REFRESH_TOKEN_KEY, refresh],
        ]
      : [
          [TOKEN_KEY, access],
          [ACCESS_TOKEN_KEY, access],
        ],
  );
}

export async function clearTokens() {
  await AsyncStorage.multiRemove([TOKEN_KEY, ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY]);
}

export async function getAccessToken(): Promise<string | null> {
  // tenta a chave nova; cai pra legacy se não houver
  const a = await AsyncStorage.getItem(ACCESS_TOKEN_KEY);
  if (a) return a;
  return AsyncStorage.getItem(TOKEN_KEY);
}

export async function getRefreshToken(): Promise<string | null> {
  return AsyncStorage.getItem(REFRESH_TOKEN_KEY);
}

// Axios instance + interceptors --------------------------------------------
export const api: AxiosInstance = axios.create({
  baseURL: `${BASE}/api`,
  timeout: 30000,
});

api.interceptors.request.use(async (config) => {
  const token = await getAccessToken();
  if (token) {
    config.headers = config.headers || {};
    (config.headers as any).Authorization = `Bearer ${token}`;
  }
  return config;
});

// Refresh token logic ------------------------------------------------------
let refreshPromise: Promise<string | null> | null = null;
let onSessionExpired: (() => void) | null = null;

/** Permite que o AuthProvider registre um callback para tratar logout
 *  global quando o refresh falhar. */
export function setOnSessionExpired(cb: (() => void) | null) {
  onSessionExpired = cb;
}

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const refresh = await getRefreshToken();
      if (!refresh) return null;
      // Usa axios bare para evitar loop com interceptors
      const { data } = await axios.post(
        `${BASE}/api/auth/refresh`,
        { refresh_token: refresh },
        { timeout: 15000 },
      );
      const newAccess: string = data.access_token || data.token;
      const newRefresh: string | undefined = data.refresh_token;
      if (newAccess) {
        await setTokens(newAccess, newRefresh ?? refresh);
        return newAccess;
      }
      return null;
    } catch {
      return null;
    } finally {
      // libera a próxima chamada (evita race apenas dentro do ciclo atual)
      setTimeout(() => {
        refreshPromise = null;
      }, 50);
    }
  })();
  return refreshPromise;
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    const status = error.response?.status;
    if (status !== 401 || !original || original._retry) return Promise.reject(error);

    // não tenta refresh em rotas de auth (login/refresh)
    const url = (original.url || "").toLowerCase();
    if (url.includes("/auth/login") || url.includes("/auth/refresh")) {
      return Promise.reject(error);
    }

    original._retry = true;
    const newToken = await refreshAccessToken();
    if (!newToken) {
      await clearTokens();
      onSessionExpired?.();
      return Promise.reject(error);
    }
    original.headers = original.headers || {};
    (original.headers as any).Authorization = `Bearer ${newToken}`;
    return api.request(original);
  },
);

// Util -------------------------------------------------------------------
export function apiErrorMessage(e: any): string {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x: any) => x?.msg || JSON.stringify(x)).join(" • ");
  return e?.message || "Erro desconhecido";
}

export type Photo = {
  label?: string;
  base64?: string;
  url?: string;             // URL Cloudinary (preferida)
  workflow_step?: number;
  photo_id?: string;
};
export type Checklist = {
  id: string;
  numero: string;
  user_id: string;
  status: "rascunho" | "enviado" | "em_auditoria" | "aprovado" | "reprovado";
  vehicle_type?: string;
  vehicle_brand?: string;
  vehicle_model?: string;
  vehicle_year?: string;
  vehicle_color?: string;
  vehicle_vin?: string;
  vehicle_odometer?: number | null;
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
  imei?: string;
  iccid?: string;
  device_online?: boolean | null;
  device_tested_at?: string;
  device_test_message?: string;
  execution_started_at?: string;
  execution_ended_at?: string;
  execution_elapsed_sec?: number;
  // v14 — Motor de Comissionamento
  service_type_code?: string;
  service_type_name?: string;
  sla_max_minutes?: number;
  sla_base_value?: number;
  sla_within?: boolean | null;
  // v14.1 — Anti-fraude SLA server-side
  phase?: "draft" | "awaiting_equipment_photo" | "in_execution" | "finalized";
  checklist_sent_at?: string;
  equipment_photo_at?: string;
  equipment_photo_delay_sec?: number;
  equipment_photo_flag?: boolean;
  equipment_photo_url?: string;
  service_finished_at?: string;
  sla_total_sec?: number;
  // v14 Fase 3C — Check-in/out do painel
  dashboard_photo_in_url?: string;
  dashboard_photo_in_at?: string;
  dashboard_photo_in_valid?: boolean | null;
  dashboard_photo_in_reason?: string;
  dashboard_photo_in_confidence?: number;
  dashboard_photo_out_url?: string;
  dashboard_photo_out_at?: string;
  dashboard_photo_out_valid?: boolean | null;
  dashboard_photo_out_reason?: string;
  dashboard_photo_out_confidence?: number;
  // v14 Fase 3B — Motor Financeiro (persistido na aprovação)
  comp_base_value?: number;
  comp_sla_cut?: boolean;
  comp_warranty_zero?: boolean;
  comp_return_flagged?: boolean;
  comp_final_value?: number;
  comp_penalty_on_original?: number;
  comp_previous_os_id?: string | null;
  comp_level_applied?: string;
  comp_elapsed_min?: number;
  comp_max_minutes?: number;
  comp_computed_at?: string;
  photos: Photo[];
  location?: { lat: number; lng: number } | null;
  location_available: boolean;
  signature_base64?: string;
  signature_url?: string | null;
  appointment_id?: string;
  alerts: string[];
  created_at: string;
  updated_at: string;
  sent_at?: string | null;
};
