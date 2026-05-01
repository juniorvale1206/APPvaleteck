import React, { useCallback, useMemo, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, RefreshControl } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api, apiErrorMessage } from "../../src/api";
import { EmptyState } from "../../src/components";
import { colors, fonts, radii, space } from "../../src/theme";

type Period = "day" | "week" | "month" | "all";

type Job = {
  id: string; numero: string; empresa: string; tipo_atendimento?: string;
  nome: string; sobrenome: string; placa: string;
  base_amount: number; bonus_amount: number; total_amount: number;
  elapsed_sec: number; elapsed_min: number; sla_fast: boolean;
  sent_at?: string | null; created_at: string;
};
type Summary = {
  period: string;
  total_base: number; total_bonus: number; total_net: number;
  count: number; avg_elapsed_min: number; fast_count: number;
  breakdown_by_company: Record<string, number>;
  breakdown_by_type: Record<string, number>;
  jobs: Job[];
  price_table: Record<string, Record<string, number>>;
  penalty_total?: number;
  penalty_count?: number;
  net_after_penalty?: number;
};

const BRL = (n: number) => n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const PERIODS: { id: Period; label: string }[] = [
  { id: "day", label: "Hoje" },
  { id: "week", label: "Semana" },
  { id: "month", label: "Mês" },
  { id: "all", label: "Total" },
];

export default function Earnings() {
  const router = useRouter();
  const [period, setPeriod] = useState<Period>("month");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [showPrices, setShowPrices] = useState(false);

  const load = useCallback(async (p: Period) => {
    setError("");
    try {
      const { data } = await api.get<Summary>("/earnings/me", { params: { period: p } });
      setSummary(data);
    } catch (e) { setError(apiErrorMessage(e)); }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useFocusEffect(useCallback(() => { setLoading(true); load(period); }, [load, period]));

  const companies = useMemo(() => {
    if (!summary) return [] as { name: string; value: number; pct: number }[];
    const total = Object.values(summary.breakdown_by_company).reduce((a, b) => a + b, 0);
    return Object.entries(summary.breakdown_by_company)
      .map(([name, value]) => ({ name, value, pct: total ? value / total : 0 }))
      .sort((a, b) => b.value - a.value);
  }, [summary]);

  const types = useMemo(() => {
    if (!summary) return [] as { name: string; value: number }[];
    return Object.entries(summary.breakdown_by_type)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);
  }, [summary]);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="earnings-back" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Meus ganhos</Text>
        <TouchableOpacity onPress={() => setShowPrices((v) => !v)} testID="toggle-pricing">
          <Ionicons name="pricetag-outline" size={22} color={colors.primary} />
        </TouchableOpacity>
      </View>

      <View style={styles.tabs}>
        {PERIODS.map((p) => (
          <TouchableOpacity
            key={p.id}
            onPress={() => setPeriod(p.id)}
            testID={`period-${p.id}`}
            style={[styles.tab, period === p.id && styles.tabActive]}
            activeOpacity={0.85}
          >
            <Text style={[styles.tabTxt, period === p.id && styles.tabTxtActive]}>{p.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}><ActivityIndicator color={colors.primary} /></View>
      ) : (
        <ScrollView
          contentContainerStyle={{ padding: space.lg, paddingBottom: 100 }}
          refreshControl={<RefreshControl tintColor={colors.primary} refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(period); }} />}
        >
          {error ? (
            <EmptyState title="Erro" message={error} icon="alert-circle-outline" />
          ) : !summary || summary.count === 0 ? (
            <EmptyState title="Sem atendimentos" message="Nenhum checklist enviado neste período." icon="cash-outline" />
          ) : (
            <>
              {/* Hero Card */}
              <View style={styles.hero} testID="hero-total">
                <Text style={styles.heroLabel}>Total líquido ({PERIODS.find((p) => p.id === period)?.label.toLowerCase()})</Text>
                <Text style={styles.heroAmount} testID="total-amount">{BRL(summary.total_net)}</Text>
                <View style={styles.heroBreak}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.heroBreakLabel}>Base</Text>
                    <Text style={styles.heroBreakVal}>{BRL(summary.total_base)}</Text>
                  </View>
                  <View style={styles.heroDivider} />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.heroBreakLabel}>Bônus SLA</Text>
                    <Text style={[styles.heroBreakVal, { color: colors.success }]}>+ {BRL(summary.total_bonus)}</Text>
                  </View>
                </View>
              </View>

              {/* Penalidade por equipamentos vencidos */}
              {!!summary.penalty_total && summary.penalty_total > 0 && (
                <View style={styles.penaltyCard} testID="penalty-card">
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 6 }}>
                    <Ionicons name="warning" size={20} color="#EF4444" />
                    <Text style={styles.penaltyTitle}>Penalidade por equipamentos não devolvidos</Text>
                  </View>
                  <View style={{ flexDirection: "row", alignItems: "baseline", justifyContent: "space-between" }}>
                    <Text style={styles.penaltyDesc}>
                      {summary.penalty_count} item(ns) vencido(s)
                    </Text>
                    <Text style={styles.penaltyAmount}>- {BRL(summary.penalty_total)}</Text>
                  </View>
                  <View style={styles.penaltyDivider} />
                  <View style={{ flexDirection: "row", alignItems: "baseline", justifyContent: "space-between" }}>
                    <Text style={styles.netLabel}>Líquido após descontos</Text>
                    <Text style={styles.netAmount} testID="net-after-penalty">
                      {BRL(summary.net_after_penalty || 0)}
                    </Text>
                  </View>
                  <TouchableOpacity
                    testID="goto-closure"
                    onPress={() => router.push("/estoque/fechamento")}
                    style={styles.penaltyCTA}
                  >
                    <Ionicons name="calendar-outline" size={16} color={colors.onPrimary} />
                    <Text style={styles.penaltyCTATxt}>Ver fechamento mensal</Text>
                  </TouchableOpacity>
                </View>
              )}

              {/* Stats */}
              <View style={styles.statsRow}>
                <View style={styles.statCard}>
                  <Ionicons name="checkmark-done" size={20} color={colors.primary} />
                  <Text style={styles.statVal}>{summary.count}</Text>
                  <Text style={styles.statLabel}>OS enviadas</Text>
                </View>
                <View style={styles.statCard}>
                  <Ionicons name="flash" size={20} color={colors.success} />
                  <Text style={[styles.statVal, { color: colors.success }]}>{summary.fast_count}</Text>
                  <Text style={styles.statLabel}>Com bônus SLA</Text>
                </View>
                <View style={styles.statCard}>
                  <Ionicons name="time" size={20} color={colors.warning} />
                  <Text style={styles.statVal}>{summary.avg_elapsed_min}m</Text>
                  <Text style={styles.statLabel}>Tempo médio</Text>
                </View>
              </View>

              {showPrices && (
                <View style={styles.priceTable} testID="price-table">
                  <Text style={styles.sectionTitle}>Tabela de preços (BRL)</Text>
                  {Object.entries(summary.price_table).map(([company, prices]) => (
                    <View key={company} style={styles.priceRow}>
                      <Text style={styles.priceCompany}>{company}</Text>
                      {Object.entries(prices).map(([tipo, v]) => (
                        <View key={tipo} style={styles.priceItem}>
                          <Text style={styles.priceTipo}>{tipo}</Text>
                          <Text style={styles.priceVal}>{BRL(v as number)}</Text>
                        </View>
                      ))}
                    </View>
                  ))}
                  <View style={styles.infoBox}>
                    <Ionicons name="flash" size={14} color={colors.success} />
                    <Text style={styles.infoTxt}>Bônus SLA: +20% se tempo de execução &lt; 30 minutos.</Text>
                  </View>
                </View>
              )}

              {/* Breakdown por empresa */}
              {companies.length > 0 && (
                <View style={styles.card}>
                  <Text style={styles.sectionTitle}>Por empresa parceira</Text>
                  {companies.map((c) => (
                    <View key={c.name} style={styles.barRow} testID={`company-bar-${c.name}`}>
                      <View style={styles.barHeader}>
                        <Text style={styles.barLabel}>{c.name}</Text>
                        <Text style={styles.barValue}>{BRL(c.value)}</Text>
                      </View>
                      <View style={styles.barTrack}>
                        <View style={[styles.barFill, { width: `${Math.max(c.pct * 100, 4)}%` }]} />
                      </View>
                    </View>
                  ))}
                </View>
              )}

              {/* Breakdown por tipo */}
              {types.length > 0 && (
                <View style={styles.card}>
                  <Text style={styles.sectionTitle}>Por tipo de atendimento</Text>
                  <View style={styles.chipsRow}>
                    {types.map((t) => (
                      <View key={t.name} style={styles.typePill}>
                        <Text style={styles.typePillLabel}>{t.name}</Text>
                        <Text style={styles.typePillVal}>{BRL(t.value)}</Text>
                      </View>
                    ))}
                  </View>
                </View>
              )}

              {/* Lista de OS */}
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Atendimentos do período</Text>
                {summary.jobs.map((j) => (
                  <TouchableOpacity
                    key={j.id}
                    testID={`job-${j.id}`}
                    onPress={() => router.push({ pathname: "/(app)/checklist/[id]", params: { id: j.id } })}
                    style={styles.jobRow}
                    activeOpacity={0.8}
                  >
                    <View style={{ flex: 1 }}>
                      <Text style={styles.jobNumero}>{j.numero}</Text>
                      <Text style={styles.jobClient}>{j.nome} {j.sobrenome} • {j.placa}</Text>
                      <Text style={styles.jobMeta}>{j.empresa} • {j.tipo_atendimento || "—"} {j.elapsed_min > 0 ? `• ${j.elapsed_min}m` : ""}</Text>
                    </View>
                    <View style={{ alignItems: "flex-end" }}>
                      <Text style={styles.jobTotal}>{BRL(j.total_amount)}</Text>
                      {j.sla_fast && (
                        <View style={styles.bonusChip}>
                          <Ionicons name="flash" size={10} color={colors.success} />
                          <Text style={styles.bonusTxt}>+{BRL(j.bonus_amount)}</Text>
                        </View>
                      )}
                    </View>
                  </TouchableOpacity>
                ))}
              </View>
            </>
          )}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingTop: space.sm, paddingBottom: space.sm },
  title: { color: colors.text, fontWeight: "800", fontSize: fonts.size.xl },
  tabs: { flexDirection: "row", marginHorizontal: space.lg, backgroundColor: colors.surface, borderRadius: radii.md, padding: 4, gap: 4, marginBottom: space.sm },
  tab: { flex: 1, paddingVertical: 10, borderRadius: radii.sm, alignItems: "center" },
  tabActive: { backgroundColor: colors.primary },
  tabTxt: { color: colors.textMuted, fontWeight: "800", fontSize: fonts.size.sm, letterSpacing: 0.3 },
  tabTxtActive: { color: colors.onPrimary },
  hero: { backgroundColor: colors.primary, borderRadius: radii.lg, padding: space.lg, marginBottom: space.md },
  heroLabel: { color: colors.onPrimary, fontSize: fonts.size.sm, opacity: 0.8, fontWeight: "600", textTransform: "uppercase", letterSpacing: 0.5 },
  heroAmount: { color: colors.onPrimary, fontSize: 40, fontWeight: "900", marginTop: 6, fontVariant: ["tabular-nums"] as any },
  heroBreak: { flexDirection: "row", marginTop: space.md, paddingTop: space.md, borderTopWidth: 1, borderTopColor: "rgba(0,0,0,0.2)" },
  heroDivider: { width: 1, backgroundColor: "rgba(0,0,0,0.2)", marginHorizontal: 10 },
  heroBreakLabel: { color: colors.onPrimary, opacity: 0.7, fontSize: fonts.size.xs, fontWeight: "700", textTransform: "uppercase" },
  heroBreakVal: { color: colors.onPrimary, fontSize: fonts.size.lg, fontWeight: "900", marginTop: 2 },
  statsRow: { flexDirection: "row", gap: 10, marginBottom: space.md },
  statCard: { flex: 1, backgroundColor: colors.surface, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, padding: space.md, alignItems: "center", gap: 4 },
  statVal: { color: colors.text, fontSize: fonts.size.xxl, fontWeight: "900" },
  statLabel: { color: colors.textMuted, fontSize: fonts.size.xs, textAlign: "center" },
  card: { backgroundColor: colors.surface, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, padding: space.md, marginBottom: space.md },
  sectionTitle: { color: colors.text, fontWeight: "800", fontSize: fonts.size.md, marginBottom: space.sm },
  barRow: { marginBottom: space.sm },
  barHeader: { flexDirection: "row", justifyContent: "space-between", marginBottom: 6 },
  barLabel: { color: colors.text, fontSize: fonts.size.sm, fontWeight: "600" },
  barValue: { color: colors.primary, fontSize: fonts.size.sm, fontWeight: "800" },
  barTrack: { height: 8, backgroundColor: colors.surfaceAlt, borderRadius: 4, overflow: "hidden" },
  barFill: { height: "100%", backgroundColor: colors.primary, borderRadius: 4 },
  chipsRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  typePill: { backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 12, paddingVertical: 8, borderRadius: radii.pill, flexDirection: "row", gap: 8, alignItems: "center" },
  typePillLabel: { color: colors.text, fontWeight: "700", fontSize: fonts.size.sm },
  typePillVal: { color: colors.primary, fontWeight: "900", fontSize: fonts.size.sm },
  jobRow: { flexDirection: "row", alignItems: "center", paddingVertical: 10, borderTopWidth: 1, borderTopColor: colors.border, gap: 10 },
  jobNumero: { color: colors.primary, fontWeight: "800", fontSize: fonts.size.sm },
  jobClient: { color: colors.text, fontWeight: "700", fontSize: fonts.size.sm, marginTop: 2 },
  jobMeta: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 2 },
  jobTotal: { color: colors.text, fontWeight: "900", fontSize: fonts.size.md },
  bonusChip: { flexDirection: "row", alignItems: "center", gap: 3, backgroundColor: "#143A22", paddingHorizontal: 6, paddingVertical: 2, borderRadius: 999, marginTop: 4 },
  bonusTxt: { color: colors.success, fontSize: 10, fontWeight: "800" },
  priceTable: { backgroundColor: colors.surface, borderRadius: radii.md, borderWidth: 1, borderColor: colors.primary, padding: space.md, marginBottom: space.md },
  priceRow: { marginBottom: space.sm, paddingBottom: space.sm, borderBottomWidth: 1, borderBottomColor: colors.border },
  priceCompany: { color: colors.primary, fontWeight: "800", fontSize: fonts.size.sm, marginBottom: 6 },
  priceItem: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 2 },
  priceTipo: { color: colors.textMuted, fontSize: fonts.size.sm },
  priceVal: { color: colors.text, fontWeight: "700", fontSize: fonts.size.sm },
  infoBox: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: "#143A22", padding: 8, borderRadius: radii.sm, marginTop: 8 },
  infoTxt: { color: colors.success, fontSize: fonts.size.xs, flex: 1, fontWeight: "600" },
  // Penalty
  penaltyCard: {
    backgroundColor: "#FEF2F2", borderColor: "#FCA5A5", borderWidth: 1,
    padding: space.md, borderRadius: radii.md, marginBottom: space.md,
  },
  penaltyTitle: { color: "#7F1D1D", fontWeight: "900", fontSize: fonts.size.sm, flex: 1 },
  penaltyDesc: { color: "#991B1B", fontSize: fonts.size.sm, fontWeight: "600" },
  penaltyAmount: { color: "#DC2626", fontWeight: "900", fontSize: fonts.size.lg },
  penaltyDivider: { height: 1, backgroundColor: "#FCA5A5", marginVertical: 10 },
  netLabel: { color: "#374151", fontWeight: "700", fontSize: fonts.size.sm },
  netAmount: { color: "#111827", fontWeight: "900", fontSize: fonts.size.lg },
  penaltyCTA: {
    marginTop: 12, paddingVertical: 10, backgroundColor: "#7F1D1D",
    borderRadius: radii.md, alignItems: "center", flexDirection: "row", justifyContent: "center", gap: 6,
  },
  penaltyCTATxt: { color: colors.onPrimary, fontWeight: "900", fontSize: fonts.size.sm },
});
