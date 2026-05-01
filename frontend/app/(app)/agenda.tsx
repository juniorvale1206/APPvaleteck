import React, { useCallback, useMemo, useState } from "react";
import { View, Text, StyleSheet, FlatList, TouchableOpacity, RefreshControl, ActivityIndicator, Alert } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { api, apiErrorMessage } from "../../src/api";
import { useDraft, formatPlate } from "../../src/draft";
import { useNotifications } from "../../src/notifications";
import { Btn, EmptyState } from "../../src/components";
import { colors, fonts, radii, space } from "../../src/theme";

type Appt = {
  id: string; numero_os: string; cliente_nome: string; cliente_sobrenome: string;
  placa: string; empresa: string; endereco: string; scheduled_at: string;
  status: string; checklist_id?: string | null; vehicle_type?: string;
  prioridade?: "alta" | "normal" | "baixa"; telefone?: string; tempo_estimado_min?: number;
};

type Mode = "diaria" | "semanal";

const dayKeyLocal = (iso: string) => {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
const todayKey = () => dayKeyLocal(new Date().toISOString());
const tomorrowKey = () => {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return dayKeyLocal(d.toISOString());
};

const dayLabel = (key: string) => {
  if (key === todayKey()) return "HOJE";
  if (key === tomorrowKey()) return "AMANHÃ";
  const [y, m, d] = key.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  const dias = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"];
  return `${dias[date.getDay()]} ${String(d).padStart(2, "0")}/${String(m).padStart(2, "0")}`;
};

const prioColor = (p?: string) =>
  p === "alta" ? colors.danger : p === "baixa" ? colors.textMuted : colors.warning;
const prioLabel = (p?: string) => (p === "alta" ? "ALTA" : p === "baixa" ? "BAIXA" : "NORMAL");

export default function Agenda() {
  const router = useRouter();
  const { reset, set } = useDraft();
  const { markAllSeen, newCount, showToast } = useNotifications();
  const [items, setItems] = useState<Appt[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<Mode>("diaria");
  const [seedingDemo, setSeedingDemo] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const { data } = await api.get<Appt[]>("/appointments");
      setItems(data);
      markAllSeen();
    } catch (e) { setError(apiErrorMessage(e)); }
    finally { setLoading(false); setRefreshing(false); }
  }, [markAllSeen]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const filtered = useMemo(() => {
    const today = todayKey();
    if (mode === "diaria") return items.filter((a) => dayKeyLocal(a.scheduled_at) === today);
    // semanal: 7 dias a partir de hoje
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const end = new Date(start);
    end.setDate(end.getDate() + 7);
    return items.filter((a) => {
      const d = new Date(a.scheduled_at);
      return d >= start && d < end;
    });
  }, [items, mode]);

  const grouped = useMemo(() => {
    const map: Record<string, Appt[]> = {};
    filtered.forEach((a) => {
      const k = dayKeyLocal(a.scheduled_at);
      (map[k] ||= []).push(a);
    });
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
  }, [filtered]);

  const counts = useMemo(() => {
    const today = todayKey();
    const now = new Date();
    const weekEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 7);
    const diaria = items.filter((a) => dayKeyLocal(a.scheduled_at) === today).length;
    const semanal = items.filter((a) => {
      const d = new Date(a.scheduled_at);
      return d >= new Date(now.getFullYear(), now.getMonth(), now.getDate()) && d < weekEnd;
    }).length;
    return { diaria, semanal };
  }, [items]);

  const openAppt = (a: Appt) => {
    if (a.checklist_id) {
      router.push({ pathname: "/(app)/checklist/[id]", params: { id: a.checklist_id } });
      return;
    }
    reset();
    set({
      appointment_id: a.id,
      nome: a.cliente_nome,
      sobrenome: a.cliente_sobrenome,
      placa: formatPlate(a.placa),
      empresa: a.empresa,
      vehicle_type: (a.vehicle_type as any) || "",
      telefone: a.telefone || "",
    });
    router.push("/(app)/checklist/new");
  };

  const simulateNew = async () => {
    setSeedingDemo(true);
    try {
      const { data } = await api.post("/appointments/seed-new");
      showToast({ title: "🔔 Nova OS recebida", message: `${data.numero_os} • ${data.cliente_nome} ${data.cliente_sobrenome}` });
      await load();
    } catch (e: any) {
      Alert.alert("Erro", apiErrorMessage(e));
    } finally { setSeedingDemo(false); }
  };

  const renderAppt = ({ item }: { item: Appt }) => {
    const dt = new Date(item.scheduled_at);
    const concluida = item.status === "concluido";
    const isMoto = item.vehicle_type === "moto";
    return (
      <TouchableOpacity
        activeOpacity={0.85}
        onPress={() => openAppt(item)}
        style={[styles.card, concluida && { opacity: 0.6 }]}
        testID={`appt-${item.numero_os}`}
      >
        <View style={[styles.priorityBar, { backgroundColor: prioColor(item.prioridade) }]} />
        <View style={{ flex: 1, padding: space.md }}>
          <View style={styles.cardTop}>
            <Text style={styles.osNum}>{item.numero_os}</Text>
            <View style={[styles.prioPill, { backgroundColor: prioColor(item.prioridade) + "22", borderColor: prioColor(item.prioridade) }]}>
              <Text style={[styles.prioTxt, { color: prioColor(item.prioridade) }]}>{prioLabel(item.prioridade)}</Text>
            </View>
          </View>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            {isMoto ? <MaterialCommunityIcons name="motorbike" size={20} color={colors.primary} /> : <Ionicons name="car-sport" size={20} color={colors.primary} />}
            <Text style={styles.cliente}>{item.cliente_nome} {item.cliente_sobrenome}</Text>
          </View>
          <View style={styles.row}>
            <View style={styles.plate}><Text style={styles.plateTxt}>{formatPlate(item.placa)}</Text></View>
            <Text style={styles.meta}>{item.empresa}</Text>
          </View>
          <View style={styles.metaGrid}>
            <View style={styles.metaItem}>
              <Ionicons name="time-outline" size={14} color={colors.textMuted} />
              <Text style={styles.metaSmall}>{dt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</Text>
            </View>
            <View style={styles.metaItem}>
              <Ionicons name="hourglass-outline" size={14} color={colors.textMuted} />
              <Text style={styles.metaSmall}>{item.tempo_estimado_min || 60} min</Text>
            </View>
            {!!item.telefone && (
              <View style={styles.metaItem}>
                <Ionicons name="call-outline" size={14} color={colors.textMuted} />
                <Text style={styles.metaSmall}>{item.telefone}</Text>
              </View>
            )}
          </View>
          <View style={styles.iconRow}>
            <Ionicons name="location-outline" size={14} color={colors.textMuted} />
            <Text style={styles.metaSmall} numberOfLines={2}>{item.endereco}</Text>
          </View>
          {concluida && (
            <View style={styles.doneBadge}>
              <Ionicons name="checkmark-circle" size={14} color={colors.success} />
              <Text style={{ color: colors.success, fontSize: 11, fontWeight: "800", marginLeft: 4 }}>CONCLUÍDA</Text>
            </View>
          )}
        </View>
      </TouchableOpacity>
    );
  };

  const ToggleBtn = ({ m, label, count }: { m: Mode; label: string; count: number }) => (
    <TouchableOpacity
      onPress={() => setMode(m)}
      testID={`toggle-${m}`}
      style={[styles.tab, mode === m && styles.tabActive]}
      activeOpacity={0.85}
    >
      <Text style={[styles.tabTxt, mode === m && styles.tabTxtActive]}>{label}</Text>
      <View style={[styles.tabBadge, mode === m && { backgroundColor: colors.onPrimary }]}>
        <Text style={[styles.tabBadgeTxt, mode === m && { color: colors.primary }]}>{count}</Text>
      </View>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="agenda-back" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Agenda</Text>
        <TouchableOpacity onPress={() => { setRefreshing(true); load(); }}><Ionicons name="refresh" size={22} color={colors.primary} /></TouchableOpacity>
      </View>

      <View style={styles.tabs}>
        <ToggleBtn m="diaria" label="Diária" count={counts.diaria} />
        <ToggleBtn m="semanal" label="Semanal" count={counts.semanal} />
      </View>

      <TouchableOpacity testID="simulate-new-os" onPress={simulateNew} disabled={seedingDemo} style={styles.demoBtn}>
        {seedingDemo ? <ActivityIndicator color={colors.primary} /> : <>
          <Ionicons name="flash-outline" size={16} color={colors.primary} />
          <Text style={styles.demoTxt}>Simular nova OS recebida</Text>
        </>}
      </TouchableOpacity>

      {loading ? (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}><ActivityIndicator color={colors.primary} /></View>
      ) : (
        <FlatList
          data={grouped}
          keyExtractor={([k]) => k}
          contentContainerStyle={{ padding: space.lg, paddingBottom: 80 }}
          ItemSeparatorComponent={() => <View style={{ height: 18 }} />}
          refreshControl={<RefreshControl tintColor={colors.primary} refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}
          ListEmptyComponent={
            <EmptyState
              title={error ? "Erro" : `Sem OS ${mode === "diaria" ? "para hoje" : "esta semana"}`}
              message={error || (mode === "diaria" ? "Aproveite para revisar os checklists." : "Nenhuma OS nos próximos 7 dias.")}
              icon={error ? "alert-circle-outline" : "calendar-outline"}
            />
          }
          renderItem={({ item }) => {
            const [k, list] = item;
            return (
              <View>
                <View style={styles.daySection}>
                  <Text style={styles.dayLabel}>{dayLabel(k)}</Text>
                  <View style={styles.dayLine} />
                  <Text style={styles.dayCount}>{list.length} OS</Text>
                </View>
                <View style={{ gap: 10 }}>
                  {list.map((a) => (
                    <View key={a.id}>{renderAppt({ item: a } as any)}</View>
                  ))}
                </View>
              </View>
            );
          }}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingTop: space.sm, paddingBottom: space.sm },
  title: { color: colors.text, fontWeight: "800", fontSize: fonts.size.xl },
  tabs: { flexDirection: "row", marginHorizontal: space.lg, backgroundColor: colors.surface, borderRadius: radii.md, padding: 4, gap: 4 },
  tab: { flex: 1, paddingVertical: 12, borderRadius: radii.sm, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8 },
  tabActive: { backgroundColor: colors.primary },
  tabTxt: { color: colors.textMuted, fontWeight: "800", fontSize: fonts.size.sm, letterSpacing: 0.5 },
  tabTxtActive: { color: colors.onPrimary },
  tabBadge: { backgroundColor: colors.surfaceAlt, paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999, minWidth: 24, alignItems: "center" },
  tabBadgeTxt: { color: colors.text, fontSize: 11, fontWeight: "800" },
  demoBtn: { marginHorizontal: space.lg, marginTop: space.sm, paddingVertical: 10, borderRadius: radii.md, borderWidth: 1, borderColor: colors.primary, borderStyle: "dashed", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6 },
  demoTxt: { color: colors.primary, fontWeight: "700", fontSize: fonts.size.sm },
  daySection: { flexDirection: "row", alignItems: "center", marginBottom: 10, gap: 10 },
  dayLabel: { color: colors.primary, fontWeight: "900", fontSize: fonts.size.xs, letterSpacing: 1.5 },
  dayLine: { flex: 1, height: 1, backgroundColor: colors.border },
  dayCount: { color: colors.textMuted, fontSize: fonts.size.xs, fontWeight: "600" },
  card: { flexDirection: "row", backgroundColor: colors.surface, borderRadius: radii.lg, borderWidth: 1, borderColor: colors.border, overflow: "hidden" },
  priorityBar: { width: 5 },
  cardTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  osNum: { color: colors.primary, fontWeight: "800", fontSize: fonts.size.sm, letterSpacing: 0.5 },
  prioPill: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999, borderWidth: 1 },
  prioTxt: { fontSize: 10, fontWeight: "900", letterSpacing: 0.5 },
  cliente: { color: colors.text, fontSize: fonts.size.lg, fontWeight: "800" },
  row: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 6 },
  plate: { backgroundColor: "#0a0a0a", borderWidth: 1, borderColor: colors.primary, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  plateTxt: { color: colors.primary, fontWeight: "900", letterSpacing: 1, fontSize: fonts.size.sm },
  meta: { color: colors.textMuted, fontSize: fonts.size.sm, flex: 1 },
  metaGrid: { flexDirection: "row", flexWrap: "wrap", gap: 12, marginTop: 8 },
  metaItem: { flexDirection: "row", alignItems: "center", gap: 4 },
  metaSmall: { color: colors.textMuted, fontSize: fonts.size.xs },
  iconRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 6 },
  doneBadge: { flexDirection: "row", alignItems: "center", marginTop: 8, alignSelf: "flex-start", backgroundColor: "#143A22", paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999 },
});
