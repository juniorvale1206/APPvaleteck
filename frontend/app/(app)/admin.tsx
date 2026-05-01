import React, { useCallback, useMemo, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, RefreshControl } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api, apiErrorMessage } from "../../src/api";
import { useAuth } from "../../src/auth";
import { colors, fonts, radii, shadow, space } from "../../src/theme";

type TechResult = {
  technician: { id: string; name: string; email: string };
  month: string;
  confirmed_at: string | null;
  confirmed: boolean;
  breakdown: {
    total_gross?: number; total_jobs?: number; inventory_total?: number;
    overdue_count?: number; penalty_total?: number; net_after_penalty?: number;
  };
};

type Closures = {
  month: string;
  total_technicians: number;
  confirmed_count: number;
  totals: { gross: number; penalty: number; net: number };
  results: TechResult[];
};

type InvSummary = {
  total_items: number;
  total_technicians: number;
  total_overdue: number;
  total_penalty: number;
  by_status: Record<string, number>;
  by_technician: { user_id: string; name: string; email: string; total: number; overdue: number; penalty: number; by_status: Record<string, number> }[];
};

const BRL = (n: number) => (n || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
function ymFromDate(d: Date) { return `${d.getFullYear().toString().padStart(4,"0")}-${(d.getMonth()+1).toString().padStart(2,"0")}`; }
function labelFromYm(ym: string) {
  try { const [y,m]=ym.split("-").map(Number); return new Date(y,m-1,1).toLocaleDateString("pt-BR",{month:"long",year:"numeric"}); }
  catch { return ym; }
}

export default function AdminDashboard() {
  const router = useRouter();
  const { user } = useAuth();
  const [month, setMonth] = useState<string>(ymFromDate(new Date()));
  const [closures, setClosures] = useState<Closures | null>(null);
  const [inv, setInv] = useState<InvSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const [c, i] = await Promise.all([
        api.get<Closures>(`/admin/closures?month=${month}`),
        api.get<InvSummary>(`/admin/inventory/summary`),
      ]);
      setClosures(c.data); setInv(i.data);
    } catch (e) { setError(apiErrorMessage(e)); }
    finally { setLoading(false); setRefreshing(false); }
  }, [month]);

  useFocusEffect(useCallback(() => { setLoading(true); load(); }, [load]));

  const months = useMemo(() => {
    const out: { ym: string; label: string }[] = [];
    const now = new Date();
    for (let i = 0; i < 6; i++) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      out.push({ ym: ymFromDate(d), label: d.toLocaleDateString("pt-BR", { month: "short", year: "2-digit" }).replace(".", "") });
    }
    return out;
  }, []);

  if (user && user.role !== "admin") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg, justifyContent: "center", alignItems: "center" }}>
        <Ionicons name="lock-closed" size={48} color={colors.textDim} />
        <Text style={{ color: colors.textMuted, fontWeight: "800", marginTop: 16 }}>Acesso restrito a administradores</Text>
        <TouchableOpacity onPress={() => router.back()} style={{ marginTop: 20, padding: 12 }}>
          <Text style={{ color: colors.primary, fontWeight: "800" }}>← Voltar</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="admin-back" onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={26} color={colors.text} />
        </TouchableOpacity>
        <Text style={styles.title}>Dashboard Admin</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: space.lg, gap: 8, paddingBottom: 8 }}>
        {months.map((m) => {
          const active = m.ym === month;
          return (
            <TouchableOpacity key={m.ym} testID={`admin-month-${m.ym}`} onPress={() => setMonth(m.ym)} style={[styles.chip, active && styles.chipActive]}>
              <Text style={[styles.chipTxt, active && styles.chipTxtActive]}>{m.label}</Text>
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
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}
        >
          {error ? <Text style={{ color: colors.danger }}>{error}</Text> : null}

          {/* KPIs Globais */}
          {closures && (
            <View style={styles.kpisRow}>
              <View style={styles.kpi}>
                <Text style={styles.kpiVal}>{closures.total_technicians}</Text>
                <Text style={styles.kpiLabel}>Técnicos</Text>
              </View>
              <View style={styles.kpi}>
                <Text style={[styles.kpiVal, { color: colors.success }]}>{closures.confirmed_count}</Text>
                <Text style={styles.kpiLabel}>Fechados</Text>
              </View>
              <View style={styles.kpi}>
                <Text style={[styles.kpiVal, { color: colors.danger }]}>{inv?.total_overdue || 0}</Text>
                <Text style={styles.kpiLabel}>Vencidos</Text>
              </View>
            </View>
          )}

          {/* Totais financeiros */}
          {closures && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Totais de {labelFromYm(month)}</Text>
              <View style={styles.row}><Text style={styles.rowLabel}>Ganhos brutos</Text><Text style={[styles.rowVal, { color: colors.success }]}>{BRL(closures.totals.gross)}</Text></View>
              <View style={styles.row}><Text style={[styles.rowLabel, { color: colors.danger }]}>Penalidades</Text><Text style={[styles.rowVal, { color: colors.danger }]}>- {BRL(closures.totals.penalty)}</Text></View>
              <View style={styles.divider} />
              <View style={styles.row}><Text style={[styles.rowLabel, { fontWeight: "900" }]}>Líquido consolidado</Text><Text style={[styles.rowVal, { fontWeight: "900", fontSize: fonts.size.lg, color: colors.primary }]}>{BRL(closures.totals.net)}</Text></View>
            </View>
          )}

          {/* Lista de técnicos */}
          {closures && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Por técnico ({closures.results.length})</Text>
              {closures.results.map((r) => (
                <View key={r.technician.id} style={styles.techRow}>
                  <View style={{ flex: 1 }}>
                    <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                      <Text style={styles.techName}>{r.technician.name}</Text>
                      <View style={[styles.badge, r.confirmed ? styles.badgeOk : styles.badgeWarn]}>
                        <Text style={[styles.badgeTxt, r.confirmed ? { color: "#166534" } : { color: "#78350F" }]}>
                          {r.confirmed ? "FECHADO" : "EM ABERTO"}
                        </Text>
                      </View>
                    </View>
                    <Text style={styles.techMeta}>
                      {r.breakdown.total_jobs || 0} OS • {r.breakdown.inventory_total || 0} itens • {r.breakdown.overdue_count || 0} vencidos
                    </Text>
                    <View style={{ flexDirection: "row", justifyContent: "space-between", marginTop: 4 }}>
                      <Text style={styles.techMeta}>Ganhos: <Text style={{ color: colors.text, fontWeight: "700" }}>{BRL(r.breakdown.total_gross || 0)}</Text></Text>
                      <Text style={styles.techMeta}>Penalidade: <Text style={{ color: colors.danger, fontWeight: "800" }}>-{BRL(r.breakdown.penalty_total || 0)}</Text></Text>
                    </View>
                    <Text style={[styles.techMeta, { marginTop: 4 }]}>Líquido: <Text style={{ color: colors.primary, fontWeight: "900" }}>{BRL(r.breakdown.net_after_penalty || 0)}</Text></Text>
                  </View>
                </View>
              ))}
            </View>
          )}

          {/* Resumo de estoque por técnico */}
          {inv && inv.by_technician.length > 0 && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Estoque consolidado</Text>
              <View style={{ flexDirection: "row", gap: 10, marginBottom: 10 }}>
                <View style={{ flex: 1 }}><Text style={styles.miniLabel}>Total</Text><Text style={styles.miniVal}>{inv.total_items}</Text></View>
                <View style={{ flex: 1 }}><Text style={styles.miniLabel}>Vencidos</Text><Text style={[styles.miniVal, { color: colors.danger }]}>{inv.total_overdue}</Text></View>
                <View style={{ flex: 1 }}><Text style={styles.miniLabel}>Penalidade</Text><Text style={[styles.miniVal, { color: colors.danger, fontSize: 14 }]}>{BRL(inv.total_penalty)}</Text></View>
              </View>
              {inv.by_technician.map((t) => (
                <View key={t.user_id} style={styles.techRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.techName}>{t.name}</Text>
                    <Text style={styles.techMeta}>{t.total} itens • {t.overdue > 0 ? `${t.overdue} vencido(s)` : "tudo em dia ✅"}</Text>
                  </View>
                  {t.penalty > 0 && <Text style={{ color: colors.danger, fontWeight: "900" }}>-{BRL(t.penalty)}</Text>}
                </View>
              ))}
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
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface },
  chipActive: { backgroundColor: colors.brandBlack, borderColor: colors.primary },
  chipTxt: { color: colors.text, fontSize: fonts.size.sm, fontWeight: "700", textTransform: "capitalize" },
  chipTxtActive: { color: colors.primary, fontWeight: "900" },
  kpisRow: { flexDirection: "row", gap: 10, marginBottom: space.md },
  kpi: { flex: 1, backgroundColor: colors.surface, padding: space.md, borderRadius: radii.md, alignItems: "center", ...shadow.sm },
  kpiVal: { color: colors.text, fontWeight: "900", fontSize: 24 },
  kpiLabel: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 4, fontWeight: "700" },
  card: { backgroundColor: colors.surface, padding: space.md, borderRadius: radii.md, marginBottom: space.md, ...shadow.sm },
  cardTitle: { color: colors.text, fontWeight: "900", fontSize: fonts.size.md, marginBottom: 10 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 6 },
  rowLabel: { color: colors.textMuted, fontSize: fonts.size.sm, flex: 1 },
  rowVal: { color: colors.text, fontWeight: "800", fontSize: fonts.size.sm },
  divider: { height: 1, backgroundColor: colors.border, marginVertical: 4 },
  techRow: { flexDirection: "row", alignItems: "center", paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.border, gap: 8 },
  techName: { color: colors.text, fontWeight: "800", fontSize: fonts.size.sm },
  techMeta: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 2 },
  badge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999, borderWidth: 1 },
  badgeOk: { backgroundColor: "#DCFCE7", borderColor: "#86EFAC" },
  badgeWarn: { backgroundColor: "#FEF3C7", borderColor: "#FCD34D" },
  badgeTxt: { fontSize: 9, fontWeight: "900", letterSpacing: 0.3 },
  miniLabel: { color: colors.textMuted, fontSize: fonts.size.xs, fontWeight: "700" },
  miniVal: { color: colors.text, fontSize: 18, fontWeight: "900", marginTop: 2 },
});
