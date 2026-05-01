import React, { useCallback, useEffect, useState } from "react";
import { View, Text, StyleSheet, FlatList, TouchableOpacity, RefreshControl, TextInput, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api, apiErrorMessage, type Checklist } from "../../../src/api";
import { EmptyState, StatusBadge } from "../../../src/components";
import { colors, fonts, radii, shadow, space } from "../../../src/theme";

export default function Historico() {
  const router = useRouter();
  const [items, setItems] = useState<Checklist[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [q, setQ] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async (query?: string) => {
    setError("");
    try {
      const { data } = await api.get<Checklist[]>("/checklists", { params: query ? { q: query } : {} });
      setItems(data);
    } catch (e) { setError(apiErrorMessage(e)); }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useFocusEffect(useCallback(() => { load(q); }, [load, q]));
  useEffect(() => { const t = setTimeout(() => load(q), 300); return () => clearTimeout(t); }, [q, load]);

  const renderItem = ({ item }: { item: Checklist }) => (
    <TouchableOpacity
      activeOpacity={0.85}
      onPress={() => router.push({ pathname: "/(app)/checklist/[id]", params: { id: item.id } })}
      style={styles.card}
      testID={`checklist-card-${item.id}`}
    >
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <Text style={styles.cardNumber}>{item.numero}</Text>
        <StatusBadge value={item.status} testID={`status-${item.id}`} />
      </View>
      <Text style={styles.cardClient}>{item.nome} {item.sobrenome}</Text>
      <View style={{ flexDirection: "row", alignItems: "center", marginTop: 6, gap: 12 }}>
        <View style={styles.plate}><Text style={styles.plateTxt}>{item.placa}</Text></View>
        <Text style={styles.cardMeta} numberOfLines={1}>{item.empresa} • {item.equipamento}</Text>
      </View>
      {item.alerts?.length > 0 && (
        <View style={styles.alertRow}>
          <Ionicons name="warning" size={14} color={colors.warning} />
          <Text style={styles.alertTxt} numberOfLines={1}>{item.alerts[0]}</Text>
        </View>
      )}
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <View style={styles.header}>
        <Text style={styles.title}>Histórico</Text>
        <Text style={styles.sub}>{items.length} checklists</Text>
      </View>
      <View style={styles.searchRow}>
        <Ionicons name="search" size={18} color={colors.textMuted} />
        <TextInput
          testID="search-input"
          value={q}
          onChangeText={setQ}
          placeholder="Buscar por placa ou cliente"
          placeholderTextColor={colors.textDim}
          style={styles.search}
          autoCapitalize="characters"
        />
        {!!q && (
          <TouchableOpacity onPress={() => setQ("")}>
            <Ionicons name="close-circle" size={18} color={colors.textMuted} />
          </TouchableOpacity>
        )}
      </View>
      {loading ? (
        <View style={{ flex: 1, justifyContent: "center" }}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(it) => it.id}
          renderItem={renderItem}
          contentContainerStyle={{ padding: space.lg, paddingBottom: 120 }}
          ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
          refreshControl={<RefreshControl refreshing={refreshing} tintColor={colors.primary} onRefresh={() => { setRefreshing(true); load(q); }} />}
          ListEmptyComponent={<EmptyState title={error ? "Erro" : "Nenhum checklist"} message={error || 'Use o botão "+" para começar.'} icon={error ? "alert-circle-outline" : "document-text-outline"} />}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { paddingHorizontal: space.lg, paddingTop: space.md, paddingBottom: space.sm },
  title: { color: colors.text, fontSize: fonts.size.xxl, fontWeight: "900" },
  sub: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 2 },
  searchRow: { marginHorizontal: space.lg, backgroundColor: colors.surface, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 12, height: 48, flexDirection: "row", alignItems: "center", gap: 10, marginBottom: space.sm, ...shadow.sm },
  search: { flex: 1, color: colors.text, fontSize: fonts.size.md },
  card: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: space.md, borderWidth: 1, borderColor: colors.border, ...shadow.sm },
  cardNumber: { color: colors.brandBlack, fontWeight: "800", fontSize: fonts.size.sm },
  cardClient: { color: colors.text, fontSize: fonts.size.lg, fontWeight: "800", marginTop: 6 },
  plate: { backgroundColor: colors.primary, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  plateTxt: { color: colors.onPrimary, fontWeight: "900", letterSpacing: 1, fontSize: fonts.size.sm },
  cardMeta: { color: colors.textMuted, fontSize: fonts.size.sm, flex: 1 },
  alertRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: colors.divider },
  alertTxt: { color: colors.warning, fontSize: fonts.size.xs, flex: 1 },
});
