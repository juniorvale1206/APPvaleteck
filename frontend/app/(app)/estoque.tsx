import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, RefreshControl, Alert } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { api, apiErrorMessage } from "../../src/api";
import { colors, fonts, radii, shadow, space } from "../../src/theme";

type Item = {
  id: string; user_id: string; tipo: string; modelo: string; imei?: string; iccid?: string; serie?: string;
  empresa?: string; status: string; checklist_id?: string | null; placa?: string; tracking_code?: string;
  updated_at: string; created_at: string;
};

const STATUS_META: Record<string, { label: string; color: string; bg: string; icon: keyof typeof Ionicons.glyphMap }> = {
  in_stock:           { label: "Na central",           color: "#6B7280", bg: "#F0F3F7", icon: "cube-outline" },
  in_transit_to_tech: { label: "A caminho",            color: "#F59E0B", bg: "#FEF3C7", icon: "paper-plane-outline" },
  with_tech:          { label: "Comigo",               color: "#10B981", bg: "#D1FAE5", icon: "person-outline" },
  installed:          { label: "Instalado",            color: "#3B82F6", bg: "#DBEAFE", icon: "checkmark-done-outline" },
  pending_reverse:    { label: "Aguardando reversa",   color: "#EF4444", bg: "#FEE2E2", icon: "return-up-back-outline" },
  in_transit_to_hq:   { label: "Enviado à central",    color: "#F59E0B", bg: "#FEF3C7", icon: "cube-outline" },
  received_at_hq:     { label: "Recebido na central",  color: "#6B7280", bg: "#F0F3F7", icon: "archive-outline" },
};

const NEXT_STATUS: Record<string, { status: string; label: string; needsTracking?: boolean } | null> = {
  in_transit_to_tech: { status: "with_tech", label: "Confirmar recebimento" },
  with_tech: null, // installed only happens via checklist
  installed: { status: "pending_reverse", label: "Marcar p/ reversa" },
  pending_reverse: { status: "in_transit_to_hq", label: "Enviar para central", needsTracking: true },
  in_transit_to_hq: null,
  in_stock: null,
  received_at_hq: null,
};

export default function Estoque() {
  const router = useRouter();
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [acting, setActing] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const { data } = await api.get<Item[]>("/inventory/me");
      setItems(data);
    } catch (e) { setError(apiErrorMessage(e)); }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const transfer = async (item: Item) => {
    const next = NEXT_STATUS[item.status];
    if (!next) return;
    setActing(item.id);
    try {
      if (next.needsTracking) {
        // simple prompt approach
        Alert.prompt?.("Código de rastreio", "Informe o código dos Correios / transportadora", async (code?: string) => {
          if (!code) { setActing(""); return; }
          try { await api.post(`/inventory/${item.id}/transfer`, { new_status: next.status, tracking_code: code }); await load(); }
          catch (e: any) { Alert.alert("Erro", apiErrorMessage(e)); }
          finally { setActing(""); }
        });
        // if Alert.prompt not available (Android), default
        if (typeof (Alert as any).prompt !== "function") {
          await api.post(`/inventory/${item.id}/transfer`, { new_status: next.status, tracking_code: "BR" + Date.now() });
          await load();
        }
      } else {
        await api.post(`/inventory/${item.id}/transfer`, { new_status: next.status });
        await load();
      }
    } catch (e: any) { Alert.alert("Erro", apiErrorMessage(e)); }
    finally { if (!NEXT_STATUS[item.status]?.needsTracking) setActing(""); }
  };

  const grouped: Record<string, Item[]> = items.reduce((acc, it) => {
    (acc[it.status] ||= []).push(it);
    return acc;
  }, {} as Record<string, Item[]>);

  const statusOrder = ["with_tech", "in_transit_to_tech", "installed", "pending_reverse", "in_transit_to_hq", "in_stock", "received_at_hq"];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="estoque-back" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Meu Estoque</Text>
        <TouchableOpacity testID="estoque-refresh" onPress={() => { setRefreshing(true); load(); }}>
          <Ionicons name="refresh" size={22} color={colors.text} />
        </TouchableOpacity>
      </View>

      {loading ? (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}><ActivityIndicator color={colors.primary} /></View>
      ) : (
        <ScrollView
          contentContainerStyle={{ padding: space.lg, paddingBottom: 80 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}
        >
          {error ? <Text style={{ color: colors.danger }}>{error}</Text> : null}

          <View style={styles.summaryRow}>
            <View style={styles.summaryCard}>
              <Text style={styles.sumVal}>{(grouped.with_tech || []).length}</Text>
              <Text style={styles.sumLabel}>Comigo</Text>
            </View>
            <View style={styles.summaryCard}>
              <Text style={[styles.sumVal, { color: colors.info }]}>{(grouped.installed || []).length}</Text>
              <Text style={styles.sumLabel}>Instalados</Text>
            </View>
            <View style={styles.summaryCard}>
              <Text style={[styles.sumVal, { color: colors.danger }]}>{(grouped.pending_reverse || []).length}</Text>
              <Text style={styles.sumLabel}>Aguard. reversa</Text>
            </View>
          </View>

          {statusOrder.filter((s) => (grouped[s] || []).length > 0).map((st) => {
            const meta = STATUS_META[st];
            const list = grouped[st] || [];
            return (
              <View key={st} style={{ marginBottom: space.lg }}>
                <View style={styles.sectionHead}>
                  <View style={[styles.sIcon, { backgroundColor: meta.bg }]}><Ionicons name={meta.icon} size={16} color={meta.color} /></View>
                  <Text style={styles.sectionTitle}>{meta.label}</Text>
                  <View style={[styles.sectionCount, { backgroundColor: meta.bg }]}>
                    <Text style={[styles.sectionCountTxt, { color: meta.color }]}>{list.length}</Text>
                  </View>
                </View>
                {list.map((it) => {
                  const nxt = NEXT_STATUS[it.status];
                  return (
                    <View key={it.id} style={styles.itemCard} testID={`inv-${it.serie || it.id}`}>
                      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: 12 }}>
                        <View style={[styles.itemIcon, { backgroundColor: meta.bg }]}>
                          <MaterialCommunityIcons name={it.tipo.toLowerCase().includes("bloqu") ? "lock-outline" : "crosshairs-gps"} size={22} color={meta.color} />
                        </View>
                        <View style={{ flex: 1 }}>
                          <Text style={styles.itemModel}>{it.modelo}</Text>
                          <Text style={styles.itemMeta}>{it.tipo} • {it.empresa} • {it.serie}</Text>
                          {!!it.imei && <Text style={styles.itemMetaSmall}>IMEI {it.imei}</Text>}
                          {!!it.iccid && <Text style={styles.itemMetaSmall}>ICCID {it.iccid}</Text>}
                          {!!it.placa && <Text style={styles.itemMetaSmall}>Instalado em: {it.placa}</Text>}
                          {!!it.tracking_code && <Text style={[styles.itemMetaSmall, { color: colors.info, fontWeight: "700" }]}>Rastreio: {it.tracking_code}</Text>}
                        </View>
                      </View>
                      {nxt && (
                        <TouchableOpacity
                          testID={`transfer-${it.serie || it.id}`}
                          onPress={() => transfer(it)}
                          disabled={acting === it.id}
                          style={styles.transferBtn}
                        >
                          {acting === it.id ? <ActivityIndicator color={colors.onPrimary} /> : <>
                            <Ionicons name="arrow-forward-circle" size={18} color={colors.onPrimary} />
                            <Text style={styles.transferTxt}>{nxt.label}</Text>
                          </>}
                        </TouchableOpacity>
                      )}
                    </View>
                  );
                })}
              </View>
            );
          })}

          {items.length === 0 && !error && (
            <View style={{ alignItems: "center", padding: 40 }}>
              <Ionicons name="cube-outline" size={44} color={colors.textDim} />
              <Text style={{ color: colors.textMuted, marginTop: 10, fontWeight: "700" }}>Sem itens em estoque</Text>
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
  summaryRow: { flexDirection: "row", gap: 10, marginBottom: space.md },
  summaryCard: { flex: 1, backgroundColor: colors.surface, padding: space.md, borderRadius: radii.md, alignItems: "center", ...shadow.sm },
  sumVal: { color: colors.success, fontWeight: "900", fontSize: 24 },
  sumLabel: { color: colors.textMuted, fontWeight: "700", fontSize: fonts.size.xs, marginTop: 4 },
  sectionHead: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  sIcon: { width: 30, height: 30, borderRadius: 15, alignItems: "center", justifyContent: "center" },
  sectionTitle: { color: colors.text, fontWeight: "800", fontSize: fonts.size.md, flex: 1 },
  sectionCount: { paddingHorizontal: 10, paddingVertical: 3, borderRadius: 999 },
  sectionCountTxt: { fontWeight: "800", fontSize: fonts.size.xs },
  itemCard: { backgroundColor: colors.surface, padding: space.md, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, marginBottom: 10, ...shadow.sm },
  itemIcon: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center" },
  itemModel: { color: colors.text, fontWeight: "800", fontSize: fonts.size.md },
  itemMeta: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 2 },
  itemMetaSmall: { color: colors.textDim, fontSize: fonts.size.xs, marginTop: 2 },
  transferBtn: { flexDirection: "row", gap: 6, alignItems: "center", justifyContent: "center", marginTop: 12, paddingVertical: 10, backgroundColor: colors.brandBlack, borderRadius: radii.md },
  transferTxt: { color: colors.primary, fontWeight: "900", fontSize: fonts.size.sm },
});
