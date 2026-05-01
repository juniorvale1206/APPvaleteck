import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useRouter } from "expo-router";
import { api } from "./api";
import { useAuth } from "./auth";
import { colors, fonts, radii, space } from "./theme";

type Summary = {
  overdue_count: number;
  penalty_total: number;
  pending_reverse_count: number;
};

/** Banner flutuante que aparece quando o técnico tem equipamentos vencidos
 *  (ou próximos a vencer) aguardando devolução. Atalho para a tela do Estoque. */
export default function OverdueInventoryBanner() {
  const router = useRouter();
  const { user } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useFocusEffect(useCallback(() => {
    if (!user || user.role !== "tecnico") return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get<Summary>("/inventory/summary");
        if (!cancelled) setSummary(data);
      } catch {
        /* silencioso — banner some */
      }
    })();
    return () => { cancelled = true; };
  }, [user]));

  if (!summary || summary.overdue_count === 0 || dismissed) return null;

  return (
    <View style={styles.wrapper} testID="overdue-agenda-banner">
      <View style={styles.iconBox}>
        <Ionicons name="warning" size={22} color="#FFF" />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.title}>
          {summary.overdue_count} equipamento(s) vencido(s)
        </Text>
        <Text style={styles.subtitle}>
          Até R$ {summary.penalty_total.toFixed(2)} pode ser descontado dos seus ganhos
        </Text>
      </View>
      <TouchableOpacity
        testID="goto-estoque-from-banner"
        onPress={() => router.push("/estoque")}
        style={styles.actionBtn}
      >
        <Text style={styles.actionTxt}>Resolver</Text>
        <Ionicons name="arrow-forward" size={14} color="#7F1D1D" />
      </TouchableOpacity>
      <TouchableOpacity
        testID="dismiss-overdue-banner"
        onPress={() => setDismissed(true)}
        style={styles.closeBtn}
      >
        <Ionicons name="close" size={18} color="#FFF" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: "#DC2626",
    padding: space.md,
    borderRadius: radii.md,
    marginHorizontal: space.lg,
    marginTop: space.md,
    marginBottom: space.sm,
  },
  iconBox: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.2)",
    alignItems: "center", justifyContent: "center",
  },
  title: { color: "#FFF", fontWeight: "900", fontSize: fonts.size.sm },
  subtitle: { color: "#FEE2E2", fontSize: fonts.size.xs, marginTop: 2 },
  actionBtn: {
    flexDirection: "row", alignItems: "center", gap: 4,
    backgroundColor: "#FEF2F2", paddingHorizontal: 12, paddingVertical: 8,
    borderRadius: radii.sm,
  },
  actionTxt: { color: "#7F1D1D", fontWeight: "900", fontSize: fonts.size.xs },
  closeBtn: { padding: 4 },
});
