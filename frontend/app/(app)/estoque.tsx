import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, RefreshControl, Alert, Modal, TextInput, Pressable, KeyboardAvoidingView, Platform } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { api, apiErrorMessage } from "../../src/api";
import { colors, fonts, radii, shadow, space } from "../../src/theme";

type Item = {
  id: string; user_id: string; tipo: string; modelo: string; imei?: string; iccid?: string; serie?: string;
  empresa?: string; status: string; checklist_id?: string | null; placa?: string; tracking_code?: string;
  equipment_category?: string; equipment_value?: number;
  pending_reverse_at?: string | null; reverse_deadline_at?: string | null;
  reverse_carrier?: string | null; reverse_tracking_code?: string | null;
  reverse_sent_at?: string | null; reverse_expected_at?: string | null; reverse_received_at?: string | null;
  reverse_overdue?: boolean; reverse_days_left?: number | null;
  updated_at: string; created_at: string;
};

type Summary = {
  total: number; by_status: Record<string, number>;
  with_tech_count: number; installed_count: number; pending_reverse_count: number;
  overdue_count: number; penalty_total: number;
  overdue_items: { id: string; modelo: string; serie?: string; placa?: string; equipment_value?: number; days_overdue: number }[];
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

const NEXT_STATUS: Record<string, { status: string; label: string; needsReverseForm?: boolean } | null> = {
  in_transit_to_tech: { status: "with_tech", label: "Confirmar recebimento" },
  with_tech: null,
  installed: { status: "pending_reverse", label: "Marcar p/ reversa" },
  pending_reverse: { status: "in_transit_to_hq", label: "Registrar envio p/ central", needsReverseForm: true },
  in_transit_to_hq: null,
  in_stock: null,
  received_at_hq: null,
};

const CARRIER_OPTIONS = ["Correios", "Jadlog", "Mercado Envios", "Total Express", "Loggi", "Outro"];

function fmtDate(iso?: string | null) {
  if (!iso) return "—";
  try { const d = new Date(iso); return d.toLocaleDateString("pt-BR"); } catch { return iso; }
}

export default function Estoque() {
  const router = useRouter();
  const [items, setItems] = useState<Item[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [acting, setActing] = useState("");

  // Modal de logística reversa (pending_reverse → in_transit_to_hq)
  const [reverseModal, setReverseModal] = useState<Item | null>(null);
  const [revCarrier, setRevCarrier] = useState("Correios");
  const [revTracking, setRevTracking] = useState("");
  const [revSentAt, setRevSentAt] = useState("");
  const [revExpectedAt, setRevExpectedAt] = useState("");
  const [revNotes, setRevNotes] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [a, b] = await Promise.all([
        api.get<Item[]>("/inventory/me"),
        api.get<Summary>("/inventory/summary"),
      ]);
      setItems(a.data);
      setSummary(b.data);
    } catch (e) { setError(apiErrorMessage(e)); }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const openReverseModal = (item: Item) => {
    setReverseModal(item);
    setRevCarrier("Correios");
    setRevTracking(item.reverse_tracking_code || "");
    setRevSentAt(new Date().toISOString().slice(0, 10));
    setRevExpectedAt("");
    setRevNotes("");
  };

  const submitReverse = async () => {
    if (!reverseModal) return;
    if (!revTracking.trim()) {
      Alert.alert("Código de rastreio", "Informe o código de rastreio");
      return;
    }
    setActing(reverseModal.id);
    try {
      await api.post(`/inventory/${reverseModal.id}/transfer`, {
        new_status: "in_transit_to_hq",
        reverse_carrier: revCarrier,
        reverse_tracking_code: revTracking.trim(),
        reverse_sent_at: revSentAt ? new Date(revSentAt).toISOString() : undefined,
        reverse_expected_at: revExpectedAt ? new Date(revExpectedAt).toISOString() : undefined,
        reverse_notes: revNotes.trim() || undefined,
      });
      setReverseModal(null);
      await load();
    } catch (e: any) {
      Alert.alert("Erro", apiErrorMessage(e));
    } finally {
      setActing("");
    }
  };

  const transfer = async (item: Item) => {
    const next = NEXT_STATUS[item.status];
    if (!next) return;
    if (next.needsReverseForm) {
      openReverseModal(item);
      return;
    }
    setActing(item.id);
    try {
      await api.post(`/inventory/${item.id}/transfer`, { new_status: next.status });
      await load();
    } catch (e: any) { Alert.alert("Erro", apiErrorMessage(e)); }
    finally { setActing(""); }
  };

  const grouped: Record<string, Item[]> = items.reduce((acc, it) => {
    (acc[it.status] ||= []).push(it);
    return acc;
  }, {} as Record<string, Item[]>);

  const statusOrder = ["pending_reverse", "with_tech", "in_transit_to_tech", "installed", "in_transit_to_hq", "in_stock", "received_at_hq"];

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

          {/* Alerta de penalidade */}
          {summary && summary.overdue_count > 0 && (
            <View style={styles.alertBox} testID="penalty-alert">
              <View style={{ flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 6 }}>
                <Ionicons name="warning" size={22} color="#EF4444" />
                <Text style={styles.alertTitle}>Equipamentos atrasados!</Text>
              </View>
              <Text style={styles.alertText}>
                Você tem <Text style={{ fontWeight: "900", color: "#EF4444" }}>{summary.overdue_count} item(ns)</Text> vencido(s)
                para devolução. Se não regularizar, pode ser descontado{' '}
                <Text style={{ fontWeight: "900", color: "#EF4444" }}>R$ {summary.penalty_total.toFixed(2)}</Text> dos seus ganhos.
              </Text>
            </View>
          )}

          {/* Summary cards */}
          <View style={styles.summaryRow}>
            <View style={styles.summaryCard}>
              <Text style={styles.sumVal}>{summary?.with_tech_count ?? (grouped.with_tech || []).length}</Text>
              <Text style={styles.sumLabel}>Comigo</Text>
            </View>
            <View style={styles.summaryCard}>
              <Text style={[styles.sumVal, { color: colors.info }]}>{summary?.installed_count ?? (grouped.installed || []).length}</Text>
              <Text style={styles.sumLabel}>Instalados</Text>
            </View>
            <View style={styles.summaryCard}>
              <Text style={[styles.sumVal, { color: "#F59E0B" }]}>{summary?.pending_reverse_count ?? (grouped.pending_reverse || []).length}</Text>
              <Text style={styles.sumLabel}>Aguard. reversa</Text>
            </View>
            <View style={styles.summaryCard}>
              <Text style={[styles.sumVal, { color: colors.danger }]}>{summary?.overdue_count ?? 0}</Text>
              <Text style={styles.sumLabel}>Vencidos</Text>
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
                  const overdue = !!it.reverse_overdue;
                  const daysLeft = it.reverse_days_left;
                  return (
                    <View key={it.id} style={[styles.itemCard, overdue && styles.itemCardOverdue]} testID={`inv-${it.serie || it.id}`}>
                      {overdue && (
                        <View style={styles.overdueBadge}>
                          <Ionicons name="alert-circle" size={14} color="#FFF" />
                          <Text style={styles.overdueBadgeTxt}>
                            ATRASADO {daysLeft != null ? `• ${Math.abs(daysLeft)}d` : ""}
                          </Text>
                        </View>
                      )}
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
                          {!!it.equipment_value && (
                            <Text style={styles.itemMetaSmall}>Valor do equipamento: R$ {it.equipment_value.toFixed(2)}</Text>
                          )}
                          {/* Bloco de logística reversa quando relevante */}
                          {st === "pending_reverse" && it.reverse_deadline_at && (
                            <View style={styles.reverseBlock}>
                              <Text style={[styles.reverseLabel, overdue && { color: "#EF4444" }]}>
                                {overdue ? `⚠️ Prazo vencido em ${fmtDate(it.reverse_deadline_at)}` : `Devolver até ${fmtDate(it.reverse_deadline_at)}`}
                              </Text>
                              {!overdue && daysLeft != null && daysLeft >= 0 && (
                                <Text style={styles.reverseLabelSmall}>
                                  {daysLeft === 0 ? "Vence hoje!" : `${daysLeft} dia(s) restante(s)`}
                                </Text>
                              )}
                            </View>
                          )}
                          {st === "in_transit_to_hq" && (
                            <View style={styles.reverseBlock}>
                              <Text style={styles.reverseLabel}>
                                📦 {it.reverse_carrier || "Transportadora"} • {it.reverse_tracking_code || "—"}
                              </Text>
                              {!!it.reverse_sent_at && (
                                <Text style={styles.reverseLabelSmall}>Enviado em {fmtDate(it.reverse_sent_at)}</Text>
                              )}
                              {!!it.reverse_expected_at && (
                                <Text style={styles.reverseLabelSmall}>Previsão: {fmtDate(it.reverse_expected_at)}</Text>
                              )}
                            </View>
                          )}
                          {!!it.tracking_code && st === "in_transit_to_tech" && (
                            <Text style={[styles.itemMetaSmall, { color: colors.info, fontWeight: "700" }]}>Rastreio: {it.tracking_code}</Text>
                          )}
                        </View>
                      </View>
                      {nxt && (
                        <TouchableOpacity
                          testID={`transfer-${it.serie || it.id}`}
                          onPress={() => transfer(it)}
                          disabled={acting === it.id}
                          style={[styles.transferBtn, overdue && { backgroundColor: "#7F1D1D" }]}
                        >
                          {acting === it.id ? <ActivityIndicator color={colors.onPrimary} /> : <>
                            <Ionicons name="arrow-forward-circle" size={18} color={colors.primary} />
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

      {/* MODAL LOGÍSTICA REVERSA ------------------------------------ */}
      <Modal visible={!!reverseModal} transparent animationType="slide" onRequestClose={() => setReverseModal(null)}>
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : "height"}
          style={{ flex: 1 }}
        >
          <Pressable style={styles.modalBackdrop} onPress={() => setReverseModal(null)}>
            <Pressable style={styles.modalSheet} onPress={(e) => e.stopPropagation?.()}>
              <View style={{ alignItems: "center", marginBottom: 8 }}>
                <View style={styles.modalHandle} />
              </View>
              <Text style={styles.modalTitle}>📦 Logística Reversa</Text>
              <Text style={styles.modalSub}>{reverseModal?.modelo} — {reverseModal?.serie}</Text>

              <ScrollView style={{ maxHeight: 420 }} contentContainerStyle={{ paddingBottom: 8 }}>
                <Text style={styles.fieldLabel}>Transportadora *</Text>
                <View style={styles.chipsRow}>
                  {CARRIER_OPTIONS.map((c) => (
                    <TouchableOpacity
                      key={c}
                      testID={`carrier-${c}`}
                      onPress={() => setRevCarrier(c)}
                      style={[styles.chip, revCarrier === c && styles.chipActive]}
                    >
                      <Text style={[styles.chipTxt, revCarrier === c && styles.chipTxtActive]}>{c}</Text>
                    </TouchableOpacity>
                  ))}
                </View>

                <Text style={styles.fieldLabel}>Código de rastreio *</Text>
                <TextInput
                  testID="reverse-tracking-input"
                  value={revTracking}
                  onChangeText={setRevTracking}
                  placeholder="Ex: BR123456789BR"
                  placeholderTextColor={colors.textDim}
                  style={styles.input}
                  autoCapitalize="characters"
                />

                <Text style={styles.fieldLabel}>Data de envio</Text>
                <TextInput
                  value={revSentAt}
                  onChangeText={setRevSentAt}
                  placeholder="AAAA-MM-DD"
                  placeholderTextColor={colors.textDim}
                  style={styles.input}
                />

                <Text style={styles.fieldLabel}>Previsão de chegada (opcional)</Text>
                <TextInput
                  value={revExpectedAt}
                  onChangeText={setRevExpectedAt}
                  placeholder="AAAA-MM-DD"
                  placeholderTextColor={colors.textDim}
                  style={styles.input}
                />

                <Text style={styles.fieldLabel}>Observações (opcional)</Text>
                <TextInput
                  value={revNotes}
                  onChangeText={setRevNotes}
                  placeholder="Qualquer observação relevante..."
                  placeholderTextColor={colors.textDim}
                  style={[styles.input, { height: 70, textAlignVertical: "top" }]}
                  multiline
                />
              </ScrollView>

              <View style={{ flexDirection: "row", gap: 10, marginTop: 12 }}>
                <TouchableOpacity
                  testID="reverse-cancel"
                  onPress={() => setReverseModal(null)}
                  style={[styles.modalBtn, { backgroundColor: colors.surfaceAlt, borderColor: colors.border, borderWidth: 1 }]}
                >
                  <Text style={{ color: colors.text, fontWeight: "700" }}>Cancelar</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  testID="reverse-confirm"
                  onPress={submitReverse}
                  disabled={!!acting}
                  style={[styles.modalBtn, { backgroundColor: colors.primary }]}
                >
                  {acting ? <ActivityIndicator color={colors.onPrimary} /> : (
                    <Text style={{ color: colors.onPrimary, fontWeight: "900" }}>Confirmar envio</Text>
                  )}
                </TouchableOpacity>
              </View>
            </Pressable>
          </Pressable>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingVertical: space.sm },
  title: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "900" },
  alertBox: {
    backgroundColor: "#FEE2E2", borderColor: "#EF4444", borderWidth: 1,
    padding: space.md, borderRadius: radii.md, marginBottom: space.md,
  },
  alertTitle: { color: "#7F1D1D", fontWeight: "900", fontSize: fonts.size.md },
  alertText: { color: "#7F1D1D", fontSize: fonts.size.sm, lineHeight: 20 },
  summaryRow: { flexDirection: "row", gap: 8, marginBottom: space.md },
  summaryCard: { flex: 1, backgroundColor: colors.surface, padding: space.sm, borderRadius: radii.md, alignItems: "center", ...shadow.sm, minHeight: 66 },
  sumVal: { color: colors.success, fontWeight: "900", fontSize: 22 },
  sumLabel: { color: colors.textMuted, fontWeight: "700", fontSize: 10, marginTop: 4, textAlign: "center" },
  sectionHead: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  sIcon: { width: 30, height: 30, borderRadius: 15, alignItems: "center", justifyContent: "center" },
  sectionTitle: { color: colors.text, fontWeight: "800", fontSize: fonts.size.md, flex: 1 },
  sectionCount: { paddingHorizontal: 10, paddingVertical: 3, borderRadius: 999 },
  sectionCountTxt: { fontWeight: "800", fontSize: fonts.size.xs },
  itemCard: { backgroundColor: colors.surface, padding: space.md, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, marginBottom: 10, ...shadow.sm, position: "relative" },
  itemCardOverdue: { borderColor: "#EF4444", borderWidth: 2, backgroundColor: "#FFF5F5" },
  overdueBadge: {
    position: "absolute", top: -8, right: 12, backgroundColor: "#EF4444",
    paddingHorizontal: 10, paddingVertical: 3, borderRadius: 999,
    flexDirection: "row", alignItems: "center", gap: 4, zIndex: 2,
  },
  overdueBadgeTxt: { color: "#FFF", fontWeight: "900", fontSize: 10, letterSpacing: 0.5 },
  itemIcon: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center" },
  itemModel: { color: colors.text, fontWeight: "800", fontSize: fonts.size.md },
  itemMeta: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 2 },
  itemMetaSmall: { color: colors.textDim, fontSize: fonts.size.xs, marginTop: 2 },
  reverseBlock: { marginTop: 6, paddingVertical: 6, paddingHorizontal: 8, backgroundColor: colors.surfaceAlt, borderRadius: 6 },
  reverseLabel: { color: colors.text, fontSize: fonts.size.xs, fontWeight: "700" },
  reverseLabelSmall: { color: colors.textMuted, fontSize: 10, marginTop: 2 },
  transferBtn: { flexDirection: "row", gap: 6, alignItems: "center", justifyContent: "center", marginTop: 12, paddingVertical: 10, backgroundColor: colors.brandBlack, borderRadius: radii.md },
  transferTxt: { color: colors.primary, fontWeight: "900", fontSize: fonts.size.sm },

  // Modal
  modalBackdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.6)", justifyContent: "flex-end" },
  modalSheet: { backgroundColor: colors.surface, padding: space.lg, borderTopLeftRadius: 20, borderTopRightRadius: 20, maxHeight: "88%" },
  modalHandle: { width: 42, height: 5, borderRadius: 999, backgroundColor: colors.border, marginBottom: 10 },
  modalTitle: { color: colors.text, fontWeight: "900", fontSize: fonts.size.lg },
  modalSub: { color: colors.textMuted, fontSize: fonts.size.sm, marginBottom: space.md },
  fieldLabel: { color: colors.textMuted, fontWeight: "800", fontSize: fonts.size.xs, marginBottom: 6, marginTop: 10, textTransform: "uppercase", letterSpacing: 0.5 },
  input: {
    backgroundColor: colors.surfaceAlt, borderColor: colors.border, borderWidth: 1,
    borderRadius: radii.md, padding: 12, color: colors.text, fontSize: fonts.size.md,
  },
  chipsRow: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  chip: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 999, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surfaceAlt },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipTxt: { color: colors.text, fontWeight: "700", fontSize: fonts.size.xs },
  chipTxtActive: { color: colors.onPrimary, fontWeight: "900" },
  modalBtn: { flex: 1, paddingVertical: 14, alignItems: "center", justifyContent: "center", borderRadius: radii.md },
});
