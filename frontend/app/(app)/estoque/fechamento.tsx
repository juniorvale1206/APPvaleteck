import React, { useCallback, useMemo, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, Alert, RefreshControl } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api, apiErrorMessage } from "../../../src/api";
import { colors, fonts, radii, shadow, space } from "../../../src/theme";

type OverdueItem = {
  id: string; modelo: string; serie?: string; imei?: string; placa?: string;
  equipment_category?: string; equipment_value?: number;
  days_overdue: number; reverse_deadline_at?: string;
};

type Breakdown = {
  total_gross: number; total_jobs: number; inventory_total: number;
  overdue_count: number; penalty_total: number; net_after_penalty: number;
  overdue_items: OverdueItem[];
};

type Closure = {
  id?: string | null; user_id: string; month: string;
  confirmed_at?: string | null; breakdown: Breakdown;
  signature_base64?: string; notes?: string;
};

const BRL = (n: number) => (n || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function ymFromDate(d: Date): string {
  return `${d.getFullYear().toString().padStart(4, "0")}-${(d.getMonth() + 1).toString().padStart(2, "0")}`;
}
function labelFromYm(ym: string): string {
  try {
    const [y, m] = ym.split("-").map(Number);
    const d = new Date(y, m - 1, 1);
    return d.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
  } catch {
    return ym;
  }
}

export default function Fechamento() {
  const router = useRouter();
  const [month, setMonth] = useState<string>(ymFromDate(new Date()));
  const [data, setData] = useState<Closure | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (ym: string) => {
    setError("");
    try {
      const { data: r } = await api.get<Closure>(`/inventory/monthly-closure?month=${ym}`);
      setData(r);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { setLoading(true); load(month); }, [load, month]));

  const handleConfirm = () => {
    if (!data || data.confirmed_at) return;
    Alert.alert(
      "Confirmar fechamento do mês?",
      `Ao confirmar, será gravado um snapshot imutável de ${labelFromYm(month)}.\n\n` +
      `Ganhos brutos: ${BRL(data.breakdown.total_gross)}\n` +
      `Penalidade: ${BRL(data.breakdown.penalty_total)}\n` +
      `Líquido: ${BRL(data.breakdown.net_after_penalty)}`,
      [
        { text: "Cancelar", style: "cancel" },
        { text: "Confirmar", onPress: confirmClosure, style: "destructive" },
      ],
    );
  };

  const confirmClosure = async () => {
    setConfirming(true);
    try {
      const { data: r } = await api.post<Closure>("/inventory/monthly-closure/confirm", { month });
      setData(r);
      Alert.alert("✅ Fechamento confirmado", `O fechamento de ${labelFromYm(month)} foi registrado.`);
    } catch (e) {
      Alert.alert("Erro", apiErrorMessage(e));
    } finally {
      setConfirming(false);
    }
  };

  const months = useMemo(() => {
    const out: { ym: string; label: string }[] = [];
    const now = new Date();
    for (let i = 0; i < 6; i++) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      out.push({ ym: ymFromDate(d), label: d.toLocaleDateString("pt-BR", { month: "short", year: "2-digit" }).replace(".", "") });
    }
    return out;
  }, []);

  const confirmed = !!data?.confirmed_at;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="closure-back" onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={26} color={colors.text} />
        </TouchableOpacity>
        <Text style={styles.title}>Fechamento Mensal</Text>
        <View style={{ width: 26 }} />
      </View>

      {/* Seletor de mês */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: space.lg, gap: 8, paddingBottom: 8 }}>
        {months.map((m) => {
          const active = m.ym === month;
          return (
            <TouchableOpacity
              key={m.ym}
              testID={`month-${m.ym}`}
              onPress={() => setMonth(m.ym)}
              style={[styles.monthChip, active && styles.monthChipActive]}
            >
              <Text style={[styles.monthChipTxt, active && styles.monthChipTxtActive]}>{m.label}</Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {loading ? (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={{ padding: space.lg, paddingBottom: 80 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(month); }} tintColor={colors.primary} />}
        >
          {error ? <Text style={{ color: colors.danger }}>{error}</Text> : null}

          {/* Status do fechamento */}
          {data && (
            <View style={[styles.statusCard, confirmed ? styles.statusConfirmed : styles.statusOpen]}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
                <Ionicons
                  name={confirmed ? "lock-closed" : "lock-open-outline"}
                  size={22}
                  color={confirmed ? "#166534" : "#78350F"}
                />
                <View style={{ flex: 1 }}>
                  <Text style={[styles.statusTitle, { color: confirmed ? "#166534" : "#78350F" }]}>
                    {confirmed ? "Fechamento confirmado" : "Fechamento em aberto"}
                  </Text>
                  <Text style={[styles.statusSub, { color: confirmed ? "#166534" : "#78350F" }]}>
                    {confirmed ? `Registrado em ${new Date(data.confirmed_at!).toLocaleString("pt-BR")}` : labelFromYm(month)}
                  </Text>
                </View>
              </View>
            </View>
          )}

          {/* Breakdown */}
          {data && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Resumo de {labelFromYm(month)}</Text>

              <View style={styles.row}>
                <Text style={styles.rowLabel}>OS enviadas</Text>
                <Text style={styles.rowVal}>{data.breakdown.total_jobs}</Text>
              </View>
              <View style={styles.row}>
                <Text style={styles.rowLabel}>Itens no estoque</Text>
                <Text style={styles.rowVal}>{data.breakdown.inventory_total}</Text>
              </View>
              <View style={styles.rowDivider} />
              <View style={styles.row}>
                <Text style={styles.rowLabel}>Ganhos brutos</Text>
                <Text style={[styles.rowVal, { color: colors.success }]}>{BRL(data.breakdown.total_gross)}</Text>
              </View>
              <View style={styles.row}>
                <Text style={[styles.rowLabel, { color: colors.danger }]}>
                  Penalidades ({data.breakdown.overdue_count} item{data.breakdown.overdue_count === 1 ? "" : "s"} vencido{data.breakdown.overdue_count === 1 ? "" : "s"})
                </Text>
                <Text style={[styles.rowVal, { color: colors.danger }]}>- {BRL(data.breakdown.penalty_total)}</Text>
              </View>
              <View style={styles.rowDivider} />
              <View style={styles.row}>
                <Text style={[styles.rowLabel, { fontWeight: "900", fontSize: fonts.size.md }]}>Líquido final</Text>
                <Text style={[styles.rowVal, { fontWeight: "900", fontSize: fonts.size.lg, color: colors.primary }]}>
                  {BRL(data.breakdown.net_after_penalty)}
                </Text>
              </View>
            </View>
          )}

          {/* Lista de itens vencidos */}
          {data && data.breakdown.overdue_items.length > 0 && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Itens vencidos ({data.breakdown.overdue_items.length})</Text>
              {data.breakdown.overdue_items.map((it) => (
                <View key={it.id} style={styles.overdueRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.overdueName}>{it.modelo}</Text>
                    <Text style={styles.overdueMeta}>
                      {it.serie ? `${it.serie} • ` : ""}{it.placa || "sem placa"} • {it.days_overdue} dia(s) atrasado
                    </Text>
                  </View>
                  <Text style={styles.overdueAmount}>- {BRL(it.equipment_value || 0)}</Text>
                </View>
              ))}
              <TouchableOpacity
                testID="btn-goto-estoque"
                onPress={() => router.push("/estoque")}
                style={styles.resolverBtn}
              >
                <Ionicons name="arrow-forward" size={16} color={colors.primary} />
                <Text style={styles.resolverTxt}>Resolver no estoque</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* Botão confirmar */}
          {data && !confirmed && (
            <TouchableOpacity
              testID="confirm-closure-btn"
              onPress={handleConfirm}
              disabled={confirming}
              style={[styles.confirmBtn, confirming && { opacity: 0.6 }]}
            >
              {confirming ? (
                <ActivityIndicator color={colors.onPrimary} />
              ) : (
                <>
                  <Ionicons name="shield-checkmark" size={20} color={colors.onPrimary} />
                  <Text style={styles.confirmTxt}>Confirmar fechamento de {labelFromYm(month)}</Text>
                </>
              )}
            </TouchableOpacity>
          )}

          {confirmed && (
            <View style={styles.confirmedBox}>
              <Ionicons name="checkmark-circle" size={24} color="#166534" />
              <Text style={styles.confirmedTxt}>Este mês foi fechado. Não é possível alterar.</Text>
            </View>
          )}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingVertical: space.sm },
  title: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "900" },
  monthChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface },
  monthChipActive: { backgroundColor: colors.brandBlack, borderColor: colors.primary },
  monthChipTxt: { color: colors.text, fontSize: fonts.size.sm, fontWeight: "700", textTransform: "capitalize" },
  monthChipTxtActive: { color: colors.primary, fontWeight: "900" },
  statusCard: { padding: space.md, borderRadius: radii.md, marginBottom: space.md, borderWidth: 1 },
  statusOpen: { backgroundColor: "#FEF3C7", borderColor: "#FCD34D" },
  statusConfirmed: { backgroundColor: "#DCFCE7", borderColor: "#86EFAC" },
  statusTitle: { fontWeight: "900", fontSize: fonts.size.md },
  statusSub: { fontSize: fonts.size.xs, marginTop: 2 },
  card: { backgroundColor: colors.surface, padding: space.lg, borderRadius: radii.md, marginBottom: space.md, ...shadow.sm },
  cardTitle: { color: colors.text, fontWeight: "900", fontSize: fonts.size.md, marginBottom: 10 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 6 },
  rowLabel: { color: colors.textMuted, fontSize: fonts.size.sm, flex: 1 },
  rowVal: { color: colors.text, fontWeight: "800", fontSize: fonts.size.sm },
  rowDivider: { height: 1, backgroundColor: colors.border, marginVertical: 4 },
  overdueRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.border },
  overdueName: { color: colors.text, fontWeight: "700", fontSize: fonts.size.sm },
  overdueMeta: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 2 },
  overdueAmount: { color: colors.danger, fontWeight: "900", fontSize: fonts.size.md },
  resolverBtn: { marginTop: 12, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, paddingVertical: 10, backgroundColor: colors.brandBlack, borderRadius: radii.md },
  resolverTxt: { color: colors.primary, fontWeight: "900", fontSize: fonts.size.sm },
  confirmBtn: { flexDirection: "row", gap: 10, alignItems: "center", justifyContent: "center", paddingVertical: 16, backgroundColor: colors.primary, borderRadius: radii.md, ...shadow.md },
  confirmTxt: { color: colors.onPrimary, fontWeight: "900", fontSize: fonts.size.md },
  confirmedBox: { flexDirection: "row", alignItems: "center", gap: 10, padding: space.md, backgroundColor: "#DCFCE7", borderRadius: radii.md, borderWidth: 1, borderColor: "#86EFAC" },
  confirmedTxt: { color: "#166534", fontWeight: "800", fontSize: fonts.size.sm, flex: 1 },
});
