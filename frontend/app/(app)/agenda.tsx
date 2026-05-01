import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, FlatList, TouchableOpacity, RefreshControl, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api, apiErrorMessage } from "../../src/api";
import { useDraft, formatPlate } from "../../src/draft";
import { Btn, EmptyState } from "../../src/components";
import { colors, fonts, radii, space } from "../../src/theme";

type Appt = {
  id: string; numero_os: string; cliente_nome: string; cliente_sobrenome: string;
  placa: string; empresa: string; endereco: string; scheduled_at: string;
  status: string; checklist_id?: string | null; vehicle_type?: string;
};

export default function Agenda() {
  const router = useRouter();
  const { reset, set } = useDraft();
  const [items, setItems] = useState<Appt[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const { data } = await api.get<Appt[]>("/appointments");
      setItems(data);
    } catch (e) { setError(apiErrorMessage(e)); }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

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
    });
    router.push("/(app)/checklist/new");
  };

  const renderItem = ({ item }: { item: Appt }) => {
    const dt = new Date(item.scheduled_at);
    const concluida = item.status === "concluido";
    return (
      <TouchableOpacity
        activeOpacity={0.85}
        onPress={() => openAppt(item)}
        style={[styles.card, concluida && { opacity: 0.65 }]}
        testID={`appt-${item.numero_os}`}
      >
        <View style={styles.cardTop}>
          <Text style={styles.osNum}>{item.numero_os}</Text>
          <View style={[styles.statusPill, concluida && { backgroundColor: "#143A22" }]}>
            <Text style={[styles.statusTxt, concluida && { color: "#34D399" }]}>
              {concluida ? "Concluído" : item.status === "em_andamento" ? "Em andamento" : "Agendado"}
            </Text>
          </View>
        </View>
        <Text style={styles.cliente}>{item.cliente_nome} {item.cliente_sobrenome}</Text>
        <View style={styles.row}>
          <View style={styles.plate}><Text style={styles.plateTxt}>{formatPlate(item.placa)}</Text></View>
          <Text style={styles.meta}>{item.empresa}</Text>
          {item.vehicle_type && (
            <Ionicons name={item.vehicle_type === "moto" ? "bicycle" : "car-sport"} size={18} color={colors.primary} />
          )}
        </View>
        <View style={styles.iconRow}>
          <Ionicons name="time-outline" size={14} color={colors.textMuted} />
          <Text style={styles.metaSmall}>{dt.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}</Text>
        </View>
        <View style={styles.iconRow}>
          <Ionicons name="location-outline" size={14} color={colors.textMuted} />
          <Text style={styles.metaSmall} numberOfLines={2}>{item.endereco}</Text>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="agenda-back" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Agenda do dia</Text>
        <TouchableOpacity onPress={() => { setRefreshing(true); load(); }}><Ionicons name="refresh" size={22} color={colors.primary} /></TouchableOpacity>
      </View>
      {loading ? (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}><ActivityIndicator color={colors.primary} /></View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(it) => it.id}
          renderItem={renderItem}
          contentContainerStyle={{ padding: space.lg, paddingBottom: 80 }}
          ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
          refreshControl={<RefreshControl tintColor={colors.primary} refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}
          ListEmptyComponent={<EmptyState title={error ? "Erro" : "Sem agendamentos"} message={error || "Nenhuma OS agendada."} icon={error ? "alert-circle-outline" : "calendar-outline"} />}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingTop: space.sm, paddingBottom: space.sm },
  title: { color: colors.text, fontWeight: "800", fontSize: fonts.size.xl },
  card: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: space.md, borderWidth: 1, borderColor: colors.border },
  cardTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  osNum: { color: colors.primary, fontWeight: "800", fontSize: fonts.size.sm, letterSpacing: 0.5 },
  statusPill: { backgroundColor: "#4A3A12", paddingHorizontal: 10, paddingVertical: 3, borderRadius: 999 },
  statusTxt: { color: colors.primary, fontSize: 11, fontWeight: "800", letterSpacing: 0.5 },
  cliente: { color: colors.text, fontSize: fonts.size.lg, fontWeight: "800" },
  row: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 6 },
  iconRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 6 },
  plate: { backgroundColor: "#0a0a0a", borderWidth: 1, borderColor: colors.primary, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  plateTxt: { color: colors.primary, fontWeight: "900", letterSpacing: 1, fontSize: fonts.size.sm },
  meta: { color: colors.textMuted, fontSize: fonts.size.sm, flex: 1 },
  metaSmall: { color: colors.textMuted, fontSize: fonts.size.xs, flex: 1 },
});
