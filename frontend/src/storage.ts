import AsyncStorage from "@react-native-async-storage/async-storage";

export const KEYS = {
  draftCurrent: "valeteck_draft_current",
  syncQueue: "valeteck_sync_queue",
  offlineChecklists: "valeteck_offline_checklists",
};

export async function readJson<T>(key: string, fallback: T): Promise<T> {
  try {
    const raw = await AsyncStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch { return fallback; }
}

export async function writeJson(key: string, value: any): Promise<void> {
  try { await AsyncStorage.setItem(key, JSON.stringify(value)); } catch {}
}

export async function removeKey(key: string): Promise<void> {
  try { await AsyncStorage.removeItem(key); } catch {}
}
