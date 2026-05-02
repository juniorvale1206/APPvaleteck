import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, RefreshControl } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api, apiErrorMessage } from "../../src/api";
import { EmptyState } from "../../src/components";
import { useAuth } from "../../src/auth";
import { colors, fonts, radii, space } from "../../src/theme";

type Statement = {
  month: string;
  level: string;
  total_os: number;
  valid_os: number;
  duplicates: number;
  within_sla: number;
  out_sla: number;
  sla_compliance_pct: number;
  gross_estimated: number;
  penalty_total: number;
  penalty_count: number;
  net_estimated: number;
  meta_target: number;
  meta_reached: boolean;
  meta_remaining: number;
  by_service: { code: string; name: string; count: number; total: number }[];
};

const BRL = (n: number) => n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const LEVEL_NAME: Record<string, { label: string; color: string; icon: any }> = {
  junior: { label: "Júnior", color: "#64748B", icon: "school" },
  n1: { label: "Nível 1", color: "#3B82F6", icon: "construct" },
  n2: { label: "Nível 2", color: "#8B5CF6", icon: "star" },
  n3: { label: "Nível 3 (Instrutor)", color: "#F59E0B", icon: "ribbon" },
};

export default function Extrato() {
  const router = useRouter();
  const { user } = useAuth();
  const [data, setData] = useState<Statement | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const { data } = await api.get<Statement>("/statement/me");
      setData(data);
    } catch (e) { setError(apiErrorMessage(e)); }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useFocusEffect(useCallback(() => { setLoading(true); load(); }, [load]));

  const lvl = LEVEL_NAME[data?.level || user?.level || "n1"];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} testID="extrato-back">
          <Ionicons name="arrow-back" size={26} color={colors.text} />
        </TouchableOpacity>
        <Text style={styles.title}>Extrato mensal</Text>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : error ? (
        <EmptyState title="Erro" message={error} icon="alert-circle-outline" />
      ) : !data ? (
        <EmptyState title="Sem dados" message="Nenhuma OS registrada no mês." icon="calendar-outline" />
      ) : (
        <ScrollView
          contentContainerStyle={{ padding: space.lg, paddingBottom: 100 }}
          refreshControl={<RefreshControl tintColor={colors.primary} refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}
        >
          {/* Header: nível + mês */}
          <View style={[styles.hero, { borderColor: lvl.color }]} testID="hero-level">
            <View style={styles.heroTop}>
              <View style={[styles.lvlDot, { backgroundColor: lvl.color }]}>
                <Ionicons name={lvl.icon} size={22} color="#FFF" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.heroLabel}>Seu nível</Text>
                <Text style={styles.heroName}>{lvl.label}</Text>
              </View>
              <View>
                <Text style={styles.heroLabel}>Referência</Text>
                <Text style={styles.heroMonth}>{data.month}</Text>
              </View>
            </View>
          </View>

          {/* Resumo financeiro */}
          <View style={styles.moneyCard} testID="card-money">
            <View style={styles.moneyRow}>
              <Text style={styles.moneyLabel}>Bruto estimado</Text>
              <Text style={styles.moneyBruto}>{BRL(data.gross_estimated)}</Text>
            </View>
            {data.penalty_total > 0 && (
              <View style={styles.moneyRow}>
                <Text style={styles.moneyLabel}>Descontos ({data.penalty_count} pendência{data.penalty_count === 1 ? "" : "s"})</Text>
                <Text style={styles.moneyNeg}>- {BRL(data.penalty_total)}</Text>
              </View>
            )}
            <View style={styles.moneyDivider} />
            <View style={styles.moneyRow}>
              <Text style={styles.netLabel}>Líquido estimado</Text>
              <Text style={[styles.netValue, { color: data.net_estimated < 0 ? colors.danger : colors.text }]} testID="net-estimated">
                {BRL(data.net_estimated)}
              </Text>
            </View>
          </View>

          {/* Meta */}
          <View style={styles.metaCard} testID="card-meta">
            <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <Ionicons name={data.meta_reached ? "trophy" : "flag"} size={20} color={data.meta_reached ? "#F59E0B" : colors.primary} />
              <Text style={styles.metaTitle}>
                {data.meta_reached ? "Meta mensal atingida!" : "Meta mensal"}
              </Text>
            </View>
            <Text style={styles.metaSub}>
              {data.valid_os} de {data.meta_target} OS válidas
              {data.meta_reached ? " 🎉" : ` • faltam ${data.meta_remaining}`}
            </Text>
            <View style={styles.metaBar}>
              <View style={[
                styles.metaFill,
                {
                  width: `${Math.min((data.valid_os / data.meta_target) * 100, 100)}%`,
                  backgroundColor: data.meta_reached ? "#F59E0B" : colors.primary,
                },
              ]} />
            </View>
          </View>

          {/* Stats SLA */}
          <View style={styles.statsRow}>
            <View style={styles.statCard}>
              <Ionicons name="checkmark-done" size={20} color={colors.primary} />
              <Text style={styles.statVal}>{data.total_os}</Text>
              <Text style={styles.statLabel}>OS totais</Text>
            </View>
            <View style={styles.statCard}>
              <Ionicons name="time" size={20} color={colors.success} />
              <Text style={[styles.statVal, { color: colors.success }]}>{data.sla_compliance_pct}%</Text>
              <Text style={styles.statLabel}>Dentro SLA</Text>
            </View>
            <View style={styles.statCard}>
              <Ionicons name="warning" size={20} color={colors.warning} />
              <Text style={[styles.statVal, { color: colors.warning }]}>{data.out_sla}</Text>
              <Text style={styles.statLabel}>Fora SLA</Text>
            </View>
          </View>

          {data.duplicates > 0 && (
            <View style={styles.alertCard} testID="alert-dup">
              <Ionicons name="alert-circle" size={18} color={colors.danger} />
              <Text style={styles.alertTxt}>
                {data.duplicates} OS com duplicidade de placa (90d) — valor R$ 0,00
              </Text>
            </View>
          )}

          {/* Breakdown por serviço */}
          {data.by_service.length > 0 && (
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Por tipo de serviço</Text>
              {data.by_service.map((s) => (
                <View key={s.code} style={styles.svcRow} testID={`svc-${s.code}`}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.svcName}>{s.name}</Text>
                    <Text style={styles.svcMeta}>{s.count} OS</Text>
                  </View>
                  <Text style={styles.svcTotal}>{BRL(s.total)}</Text>
                </View>
              ))}
            </View>
          )}

          <Text style={styles.footnote}>
            *Valores estimados — o fechamento oficial inclui bônus por nível, tutoria e é processado pela administração.
          </Text>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingTop: space.sm, paddingBottom: space.sm },
  title: { color: colors.text, fontWeight: "800", fontSize: fonts.size.xl },
  hero: {
    backgroundColor: colors.surface, borderWidth: 1, borderRadius: radii.lg,
    padding: space.md, marginBottom: space.md,
  },
  heroTop: { flexDirection: "row", alignItems: "center", gap: 12 },
  lvlDot: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center" },
  heroLabel: { color: colors.textMuted, fontSize: fonts.size.xs, fontWeight: "700", textTransform: "uppercase", letterSpacing: 0.5 },
  heroName: { color: colors.text, fontSize: fonts.size.lg, fontWeight: "900", marginTop: 2 },
  heroMonth: { color: colors.text, fontSize: fonts.size.md, fontWeight: "900", marginTop: 2, textAlign: "right" },
  moneyCard: {
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
    borderRadius: radii.lg, padding: space.md, marginBottom: space.md,
  },
  moneyRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 6 },
  moneyLabel: { color: colors.textMuted, fontSize: fonts.size.sm, fontWeight: "600" },
  moneyBruto: { color: colors.text, fontSize: fonts.size.lg, fontWeight: "900" },
  moneyNeg: { color: colors.danger, fontSize: fonts.size.lg, fontWeight: "900" },
  moneyDivider: { height: 1, backgroundColor: colors.border, marginVertical: 8 },
  netLabel: { color: colors.text, fontSize: fonts.size.md, fontWeight: "800" },
  netValue: { fontSize: 22, fontWeight: "900", fontVariant: ["tabular-nums"] as any },
  metaCard: {
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
    borderRadius: radii.lg, padding: space.md, marginBottom: space.md,
  },
  metaTitle: { color: colors.text, fontSize: fonts.size.md, fontWeight: "900" },
  metaSub: { color: colors.textMuted, fontSize: fonts.size.sm, marginBottom: 10 },
  metaBar: { height: 8, backgroundColor: colors.surfaceAlt, borderRadius: 4, overflow: "hidden" },
  metaFill: { height: "100%", borderRadius: 4 },
  statsRow: { flexDirection: "row", gap: 8, marginBottom: space.md },
  statCard: {
    flex: 1, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
    borderRadius: radii.md, padding: space.sm, alignItems: "center", gap: 4,
  },
  statVal: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "900" },
  statLabel: { color: colors.textMuted, fontSize: fonts.size.xs, textAlign: "center" },
  alertCard: {
    backgroundColor: "#FEF2F2", borderColor: "#FCA5A5", borderWidth: 1,
    padding: space.sm, borderRadius: radii.md, flexDirection: "row", gap: 8,
    alignItems: "center", marginBottom: space.md,
  },
  alertTxt: { color: "#991B1B", flex: 1, fontSize: fonts.size.sm, fontWeight: "600" },
  card: {
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
    borderRadius: radii.md, padding: space.md, marginBottom: space.md,
  },
  sectionTitle: { color: colors.text, fontWeight: "800", fontSize: fonts.size.md, marginBottom: space.sm },
  svcRow: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    paddingVertical: 8, borderTopWidth: 1, borderTopColor: colors.border,
  },
  svcName: { color: colors.text, fontWeight: "700", fontSize: fonts.size.sm },
  svcMeta: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 2 },
  svcTotal: { color: colors.primary, fontWeight: "900", fontSize: fonts.size.md },
  footnote: { color: colors.textMuted, fontSize: fonts.size.xs, textAlign: "center", marginTop: space.md, fontStyle: "italic" },
});
