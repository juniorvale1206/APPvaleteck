import React, { useCallback, useState, useEffect } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, RefreshControl } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api, apiErrorMessage } from "../../src/api";
import { useNotifications } from "../../src/notifications";
import { colors, fonts, radii, shadow, space } from "../../src/theme";

const BRL = (n: number) => n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const LAST_LEVEL_KEY = "valeteck_last_level_seen";

type LevelInfo = {
  number: number; name: string; min_xp: number; icon: string; color: string;
  xp: number; xp_current_level: number; xp_next_level: number; progress_pct: number;
  next?: { number: number; name: string; icon: string; color: string; min_xp: number } | null;
};
type Achievement = {
  id: string; name: string; description: string; icon: string; target: number;
  current: number; unlocked: boolean; progress_pct: number;
};
type WeeklyBucket = { week_start: string; week_label: string; total_net: number; count: number; fast_count: number; xp: number };
type Profile = { level: LevelInfo; achievements: Achievement[]; weekly_history: WeeklyBucket[]; total_xp: number; unlocked_count: number; achievements_total: number };

export default function Gamification() {
  const router = useRouter();
  const { showToast } = useNotifications();
  const [p, setP] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [tab, setTab] = useState<"achievements" | "history">("achievements");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const { data } = await api.get<Profile>("/gamification/profile");
      setP(data);
      // Level-up detection
      const last = await AsyncStorage.getItem(LAST_LEVEL_KEY);
      const lastNum = last ? parseInt(last, 10) : 0;
      if (lastNum > 0 && data.level.number > lastNum) {
        showToast({
          title: `${data.level.icon} Subiu de nível!`,
          message: `Parabéns! Você alcançou ${data.level.name}. Continue assim!`,
        });
      }
      await AsyncStorage.setItem(LAST_LEVEL_KEY, String(data.level.number));
    } catch (e) { setError(apiErrorMessage(e)); }
    finally { setLoading(false); setRefreshing(false); }
  }, [showToast]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  if (loading) return <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg, alignItems: "center", justifyContent: "center" }}><ActivityIndicator color={colors.primary} /></SafeAreaView>;
  if (!p || error) return <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg, padding: 20 }}><Text style={{ color: colors.danger }}>{error}</Text></SafeAreaView>;

  const maxWeekNet = Math.max(...p.weekly_history.map((w) => w.total_net), 1);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="gami-back" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Conquistas</Text>
        <TouchableOpacity testID="gami-refresh" onPress={() => { setRefreshing(true); load(); }}>
          <Ionicons name="refresh" size={22} color={colors.text} />
        </TouchableOpacity>
      </View>

      <ScrollView
        contentContainerStyle={{ padding: space.lg, paddingBottom: 80 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}
      >
        {/* Level Hero Card */}
        <View style={[styles.levelCard, { backgroundColor: colors.brandBlack }]} testID="level-card">
          <View style={styles.levelTop}>
            <View>
              <Text style={styles.levelNumber}>NÍVEL {p.level.number}</Text>
              <Text style={[styles.levelName, { color: p.level.color }]}>{p.level.icon} {p.level.name}</Text>
            </View>
            <View style={{ alignItems: "flex-end" }}>
              <Text style={styles.xpLabel}>XP Total</Text>
              <Text style={styles.xpValue}>{p.total_xp}</Text>
            </View>
          </View>
          <View style={styles.xpBar}>
            <View style={[styles.xpFill, { width: `${p.level.progress_pct * 100}%`, backgroundColor: p.level.color }]} />
          </View>
          {p.level.next ? (
            <Text style={styles.xpToNext}>
              {p.level.xp_current_level} / {p.level.xp_next_level} XP para {p.level.next.icon} {p.level.next.name}
            </Text>
          ) : (
            <Text style={[styles.xpToNext, { color: colors.primary, fontWeight: "900" }]}>NÍVEL MÁXIMO ALCANÇADO 👑</Text>
          )}
        </View>

        {/* Stats summary */}
        <View style={styles.summaryRow}>
          <View style={styles.summaryCard}>
            <Ionicons name="ribbon" size={22} color={colors.warning} />
            <Text style={styles.sumVal}>{p.unlocked_count}/{p.achievements_total}</Text>
            <Text style={styles.sumLabel}>Conquistas</Text>
          </View>
          <View style={styles.summaryCard}>
            <Ionicons name="trending-up" size={22} color={colors.success} />
            <Text style={styles.sumVal}>{p.weekly_history[p.weekly_history.length - 1]?.count || 0}</Text>
            <Text style={styles.sumLabel}>OS esta semana</Text>
          </View>
          <View style={styles.summaryCard}>
            <Ionicons name="flash" size={22} color={colors.info} />
            <Text style={styles.sumVal}>{p.weekly_history[p.weekly_history.length - 1]?.fast_count || 0}</Text>
            <Text style={styles.sumLabel}>SLA rápidos</Text>
          </View>
        </View>

        {/* Tabs */}
        <View style={styles.tabs}>
          <TouchableOpacity testID="tab-achievements" style={[styles.tab, tab === "achievements" && styles.tabActive]} onPress={() => setTab("achievements")}>
            <Ionicons name="trophy" size={16} color={tab === "achievements" ? colors.onPrimary : colors.textMuted} />
            <Text style={[styles.tabTxt, tab === "achievements" && styles.tabTxtActive]}>Conquistas</Text>
          </TouchableOpacity>
          <TouchableOpacity testID="tab-history" style={[styles.tab, tab === "history" && styles.tabActive]} onPress={() => setTab("history")}>
            <Ionicons name="bar-chart" size={16} color={tab === "history" ? colors.onPrimary : colors.textMuted} />
            <Text style={[styles.tabTxt, tab === "history" && styles.tabTxtActive]}>Histórico</Text>
          </TouchableOpacity>
        </View>

        {tab === "achievements" ? (
          <View style={styles.grid}>
            {p.achievements.map((a) => (
              <View key={a.id} style={[styles.ach, a.unlocked && styles.achUnlocked]} testID={`ach-${a.id}`}>
                <View style={[styles.achIcon, { backgroundColor: a.unlocked ? colors.primary + "22" : colors.surfaceAlt }]}>
                  <Ionicons name={a.icon as any} size={26} color={a.unlocked ? colors.primary : colors.textDim} />
                </View>
                <Text style={[styles.achName, !a.unlocked && { color: colors.textMuted }]} numberOfLines={1}>{a.name}</Text>
                <Text style={styles.achDesc} numberOfLines={2}>{a.description}</Text>
                {a.unlocked ? (
                  <View style={styles.achUnlockedPill}>
                    <Ionicons name="checkmark-circle" size={14} color={colors.success} />
                    <Text style={styles.achUnlockedTxt}>Desbloqueado</Text>
                  </View>
                ) : (
                  <>
                    <View style={styles.achBar}>
                      <View style={[styles.achBarFill, { width: `${a.progress_pct * 100}%` }]} />
                    </View>
                    <Text style={styles.achProg}>{a.current}/{a.target}</Text>
                  </>
                )}
              </View>
            ))}
          </View>
        ) : (
          <View style={styles.history}>
            {p.weekly_history.map((w, i) => {
              const isCurrent = i === p.weekly_history.length - 1;
              const barPct = (w.total_net / maxWeekNet) * 100;
              return (
                <View key={w.week_start} style={[styles.weekRow, isCurrent && styles.weekRowCurrent]} testID={`week-${w.week_label}`}>
                  <Text style={[styles.weekLabel, isCurrent && { color: colors.primary }]}>
                    {isCurrent ? "Esta semana" : `Semana ${w.week_label}`}
                  </Text>
                  <View style={styles.weekBar}>
                    <View style={[styles.weekBarFill, { width: `${Math.max(barPct, 4)}%` }]} />
                  </View>
                  <View style={styles.weekStats}>
                    <Text style={styles.weekNet}>{BRL(w.total_net)}</Text>
                    <Text style={styles.weekMeta}>{w.count} OS • {w.xp} XP • {w.fast_count}⚡</Text>
                  </View>
                </View>
              );
            })}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingVertical: space.sm },
  title: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "900" },
  levelCard: { borderRadius: radii.lg, padding: space.lg, marginBottom: space.md, ...shadow.md },
  levelTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 },
  levelNumber: { color: colors.textMuted, fontWeight: "800", fontSize: fonts.size.xs, letterSpacing: 2 },
  levelName: { fontSize: 28, fontWeight: "900", marginTop: 4 },
  xpLabel: { color: colors.textMuted, fontSize: fonts.size.xs, fontWeight: "700" },
  xpValue: { color: colors.primary, fontSize: fonts.size.xxl, fontWeight: "900" },
  xpBar: { height: 10, backgroundColor: "rgba(255,255,255,0.1)", borderRadius: 5, overflow: "hidden" },
  xpFill: { height: "100%", borderRadius: 5 },
  xpToNext: { color: "rgba(255,255,255,0.7)", fontSize: fonts.size.xs, marginTop: 8, textAlign: "center", fontWeight: "700" },
  summaryRow: { flexDirection: "row", gap: 10, marginBottom: space.md },
  summaryCard: { flex: 1, backgroundColor: colors.surface, padding: 12, borderRadius: radii.md, alignItems: "center", ...shadow.sm },
  sumVal: { color: colors.text, fontWeight: "900", fontSize: fonts.size.xl, marginTop: 4 },
  sumLabel: { color: colors.textMuted, fontWeight: "700", fontSize: 11, marginTop: 2, textAlign: "center" },
  tabs: { flexDirection: "row", backgroundColor: colors.surface, borderRadius: radii.md, padding: 4, gap: 4, marginBottom: space.md, ...shadow.sm },
  tab: { flex: 1, paddingVertical: 10, borderRadius: radii.sm, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6 },
  tabActive: { backgroundColor: colors.primary },
  tabTxt: { color: colors.textMuted, fontWeight: "800", fontSize: fonts.size.sm },
  tabTxtActive: { color: colors.onPrimary },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  ach: { width: "48%", backgroundColor: colors.surface, padding: 12, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, alignItems: "center" },
  achUnlocked: { borderColor: colors.primary, backgroundColor: "#FEF9C3" },
  achIcon: { width: 50, height: 50, borderRadius: 25, alignItems: "center", justifyContent: "center", marginBottom: 8 },
  achName: { color: colors.text, fontWeight: "900", fontSize: fonts.size.sm, textAlign: "center" },
  achDesc: { color: colors.textMuted, fontSize: 11, textAlign: "center", marginTop: 4, marginBottom: 8 },
  achBar: { width: "100%", height: 4, backgroundColor: colors.surfaceAlt, borderRadius: 2, overflow: "hidden" },
  achBarFill: { height: "100%", backgroundColor: colors.primary },
  achProg: { color: colors.textMuted, fontSize: 11, marginTop: 4, fontWeight: "700" },
  achUnlockedPill: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 4 },
  achUnlockedTxt: { color: colors.success, fontSize: 11, fontWeight: "800" },
  history: { gap: 10 },
  weekRow: { backgroundColor: colors.surface, padding: 12, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, ...shadow.sm },
  weekRowCurrent: { borderColor: colors.primary, borderWidth: 2 },
  weekLabel: { color: colors.text, fontWeight: "800", fontSize: fonts.size.sm, marginBottom: 6 },
  weekBar: { height: 8, backgroundColor: colors.surfaceAlt, borderRadius: 4, overflow: "hidden", marginBottom: 6 },
  weekBarFill: { height: "100%", backgroundColor: colors.primary, borderRadius: 4 },
  weekStats: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  weekNet: { color: colors.success, fontWeight: "900", fontSize: fonts.size.md },
  weekMeta: { color: colors.textMuted, fontSize: 11, fontWeight: "700" },
});
