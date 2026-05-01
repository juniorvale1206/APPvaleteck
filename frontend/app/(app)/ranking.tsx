import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, RefreshControl } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api, apiErrorMessage } from "../../src/api";
import { colors, fonts, radii, shadow, space } from "../../src/theme";

type Entry = {
  user_id: string; name: string; email: string; total_net: number; count: number; fast_count: number;
  avg_elapsed_min: number; badge: string; is_me: boolean;
};
type Ranking = { period: string; top_earners: Entry[]; top_fast: Entry[]; me_earners_pos?: number | null; me_fast_pos?: number | null };

const BRL = (n: number) => n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const BADGE = { gold: { emoji: "🥇", color: "#F59E0B" }, silver: { emoji: "🥈", color: "#9CA3AF" }, bronze: { emoji: "🥉", color: "#C97E3D" } };

export default function Ranking() {
  const router = useRouter();
  const [data, setData] = useState<Ranking | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [tab, setTab] = useState<"earners" | "fast">("earners");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try { const { data } = await api.get<Ranking>("/rankings/weekly"); setData(data); }
    catch (e) { setError(apiErrorMessage(e)); }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const list = data ? (tab === "earners" ? data.top_earners : data.top_fast) : [];
  const mePos = data ? (tab === "earners" ? data.me_earners_pos : data.me_fast_pos) : null;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="ranking-back" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Ranking Semanal</Text>
        <TouchableOpacity testID="ranking-refresh" onPress={() => { setRefreshing(true); load(); }}>
          <Ionicons name="refresh" size={22} color={colors.text} />
        </TouchableOpacity>
      </View>

      <View style={styles.tabs}>
        <TouchableOpacity testID="tab-earners" onPress={() => setTab("earners")} style={[styles.tab, tab === "earners" && styles.tabActive]}>
          <Ionicons name="cash" size={16} color={tab === "earners" ? colors.onPrimary : colors.textMuted} />
          <Text style={[styles.tabTxt, tab === "earners" && styles.tabTxtActive]}>Top Ganhos</Text>
        </TouchableOpacity>
        <TouchableOpacity testID="tab-fast" onPress={() => setTab("fast")} style={[styles.tab, tab === "fast" && styles.tabActive]}>
          <Ionicons name="flash" size={16} color={tab === "fast" ? colors.onPrimary : colors.textMuted} />
          <Text style={[styles.tabTxt, tab === "fast" && styles.tabTxtActive]}>Top SLA</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator color={colors.primary} style={{ marginTop: 40 }} />
      ) : (
        <ScrollView
          contentContainerStyle={{ padding: space.lg, paddingBottom: 60 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}
        >
          {error && <Text style={{ color: colors.danger }}>{error}</Text>}

          {!!mePos && (
            <View style={styles.mePos} testID="my-rank">
              <Ionicons name="person-circle" size={24} color={colors.primary} />
              <Text style={styles.meTxt}>Sua posição: <Text style={styles.meNum}>#{mePos}</Text></Text>
            </View>
          )}

          {list.length === 0 && <Text style={{ color: colors.textMuted, textAlign: "center", marginTop: 30 }}>Sem ranking disponível esta semana</Text>}

          {list.map((e, i) => {
            const b = BADGE[e.badge as keyof typeof BADGE];
            return (
              <View key={e.user_id} style={[styles.row, e.is_me && styles.rowMe]} testID={`rank-${i + 1}`}>
                <View style={styles.pos}>
                  {b ? <Text style={{ fontSize: 28 }}>{b.emoji}</Text> : <Text style={styles.posNum}>#{i + 1}</Text>}
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.name, e.is_me && { color: colors.primary }]}>{e.name}{e.is_me && " (Você)"}</Text>
                  <Text style={styles.sub}>
                    {tab === "earners"
                      ? `${e.count} OS • ${e.fast_count} c/ bônus SLA`
                      : `${e.fast_count} OS rápidas • média ${e.avg_elapsed_min}min`}
                  </Text>
                </View>
                <View style={{ alignItems: "flex-end" }}>
                  <Text style={[styles.valor, { color: tab === "earners" ? colors.success : colors.info }]}>
                    {tab === "earners" ? BRL(e.total_net) : `${e.fast_count} ⚡`}
                  </Text>
                </View>
              </View>
            );
          })}

          <View style={styles.infoBox}>
            <Ionicons name="information-circle" size={16} color={colors.info} />
            <Text style={styles.infoTxt}>Ranking resetado toda segunda-feira. Top 3 ganham medalhas!</Text>
          </View>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingVertical: space.sm },
  title: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "900" },
  tabs: { flexDirection: "row", marginHorizontal: space.lg, backgroundColor: colors.surface, borderRadius: radii.md, padding: 4, gap: 4, marginBottom: space.md },
  tab: { flex: 1, paddingVertical: 10, borderRadius: radii.sm, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6 },
  tabActive: { backgroundColor: colors.primary },
  tabTxt: { color: colors.textMuted, fontWeight: "800", fontSize: fonts.size.sm },
  tabTxtActive: { color: colors.onPrimary },
  mePos: { flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: colors.surface, padding: 12, borderRadius: radii.md, marginBottom: space.md, borderWidth: 2, borderColor: colors.primary },
  meTxt: { color: colors.text, fontSize: fonts.size.md, fontWeight: "700" },
  meNum: { color: colors.primary, fontWeight: "900" },
  row: { flexDirection: "row", alignItems: "center", padding: 12, backgroundColor: colors.surface, borderRadius: radii.md, marginBottom: 8, ...shadow.sm },
  rowMe: { borderWidth: 2, borderColor: colors.primary },
  pos: { width: 48, alignItems: "center" },
  posNum: { color: colors.textMuted, fontWeight: "900", fontSize: fonts.size.lg },
  name: { color: colors.text, fontWeight: "800", fontSize: fonts.size.md },
  sub: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 2 },
  valor: { fontSize: fonts.size.md, fontWeight: "900" },
  infoBox: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: colors.infoBg, padding: 10, borderRadius: radii.sm, marginTop: space.md },
  infoTxt: { color: colors.info, fontSize: fonts.size.xs, flex: 1 },
});
