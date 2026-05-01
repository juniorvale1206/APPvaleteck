import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { Animated, Easing, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { api } from "./api";
import { useAuth } from "./auth";
import { colors, fonts, radii, space } from "./theme";

type Toast = { id: string; title: string; message: string; route?: string };

type Ctx = {
  newCount: number;
  markAllSeen: () => void;
  showToast: (t: Omit<Toast, "id">) => void;
};

const C = createContext<Ctx>({} as any);
const POLL_MS = 30000;

export function NotificationsProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const seen = useRef<Set<string>>(new Set());
  const initialized = useRef(false);
  const overdueChecked = useRef(false);
  const [newCount, setNewCount] = useState(0);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((t: Omit<Toast, "id">) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((cur) => [...cur, { ...t, id }]);
    setTimeout(() => setToasts((cur) => cur.filter((x) => x.id !== id)), 5000);
  }, []);

  const markAllSeen = useCallback(() => setNewCount(0), []);

  const poll = useCallback(async () => {
    if (!user) return;
    try {
      // 1) Novas OS recebidas
      const { data } = await api.get<any[]>("/appointments");
      const ids = new Set(data.map((d) => d.id));
      if (!initialized.current) {
        seen.current = ids;
        initialized.current = true;
      } else {
        const newOnes = data.filter((d) => !seen.current.has(d.id));
        if (newOnes.length > 0) {
          setNewCount((c) => c + newOnes.length);
          newOnes.forEach((n) =>
            showToast({
              title: "🔔 Nova OS recebida",
              message: `${n.numero_os} • ${n.cliente_nome} ${n.cliente_sobrenome} (${n.placa})`,
              route: "/(app)/(tabs)/agenda",
            })
          );
        }
        seen.current = ids;
      }
      // 2) Equipamentos vencidos (somente técnicos) - 1x por sessão
      if (user.role === "tecnico" && !overdueChecked.current) {
        overdueChecked.current = true;
        try {
          const { data: sum } = await api.get<any>("/inventory/summary");
          if (sum?.overdue_count > 0) {
            showToast({
              title: "⚠️ Equipamentos vencidos",
              message: `${sum.overdue_count} item(ns) aguardando devolução — até R$ ${sum.penalty_total.toFixed(2)} em penalidades`,
              route: "/estoque",
            });
          }
        } catch { /* silencioso */ }
      }
    } catch {}
  }, [user, showToast]);

  useEffect(() => {
    if (!user) {
      initialized.current = false;
      overdueChecked.current = false;
      seen.current = new Set();
      setNewCount(0);
      return;
    }
    poll();
    const i = setInterval(poll, POLL_MS);
    return () => clearInterval(i);
  }, [user, poll]);

  return (
    <C.Provider value={{ newCount, markAllSeen, showToast }}>
      {children}
      <View pointerEvents="box-none" style={styles.toastWrap}>
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} />
        ))}
      </View>
    </C.Provider>
  );
}

function ToastItem({ toast }: { toast: Toast }) {
  const router = useRouter();
  const op = useRef(new Animated.Value(0)).current;
  const ty = useRef(new Animated.Value(-20)).current;
  useEffect(() => {
    Animated.parallel([
      Animated.timing(op, { toValue: 1, duration: 220, useNativeDriver: true }),
      Animated.timing(ty, { toValue: 0, duration: 260, easing: Easing.out(Easing.cubic), useNativeDriver: true }),
    ]).start();
  }, [op, ty]);
  return (
    <Animated.View style={[styles.toast, { opacity: op, transform: [{ translateY: ty }] }]}>
      <TouchableOpacity
        activeOpacity={0.9}
        style={styles.toastInner}
        onPress={() => toast.route && router.push(toast.route as any)}
        testID="toast-new-os"
      >
        <View style={styles.bell}>
          <Ionicons name="notifications" size={18} color={colors.onPrimary} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.tTitle}>{toast.title}</Text>
          <Text style={styles.tMsg} numberOfLines={2}>{toast.message}</Text>
        </View>
        <Ionicons name="chevron-forward" size={20} color={colors.text} />
      </TouchableOpacity>
    </Animated.View>
  );
}

export const useNotifications = () => useContext(C);

const styles = StyleSheet.create({
  toastWrap: { position: "absolute", top: 60, left: 0, right: 0, alignItems: "center", zIndex: 9999, gap: 8 },
  toast: { width: "92%", maxWidth: 480 },
  toastInner: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: 2,
    borderColor: colors.primary,
    padding: 12,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    shadowColor: "#000",
    shadowOpacity: 0.5,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 8,
  },
  bell: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  tTitle: { color: colors.primary, fontWeight: "800", fontSize: fonts.size.sm },
  tMsg: { color: colors.text, fontSize: fonts.size.sm, marginTop: 2 },
});
