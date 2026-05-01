import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, Alert, RefreshControl, Modal, TextInput, Pressable, KeyboardAvoidingView, Platform } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api, apiErrorMessage } from "../../src/api";
import { useAuth } from "../../src/auth";
import { colors, fonts, radii, shadow, space } from "../../src/theme";

type Pending = {
  id: string; numero: string; user_id: string; placa: string; empresa: string;
  nome: string; sobrenome: string; tipo_atendimento: string; imei?: string;
  sent_at?: string; technician_name: string; technician_email: string;
  execution_elapsed_sec?: number; status: string;
};

export default function AdminApprovals() {
  const router = useRouter();
  const { user } = useAuth();
  const [items, setItems] = useState<Pending[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [acting, setActing] = useState("");
  const [error, setError] = useState("");
  const [rejectModal, setRejectModal] = useState<Pending | null>(null);
  const [reason, setReason] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const { data } = await api.get<{ pending: Pending[]; count: number }>("/admin/pending-approvals");
      setItems(data.pending);
    } catch (e) { setError(apiErrorMessage(e)); }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useFocusEffect(useCallback(() => { setLoading(true); load(); }, [load]));

  const approve = async (id: string, numero: string) => {
    Alert.alert(
      "Aprovar e Processar",
      `Confirmar aprovação de ${numero}?\n\nO sistema vai executar:\n• Regra de Duplicidade (30 dias)\n• Atualizar contagem de meta do técnico\n\nSe válido: +R$ 5,00. Se duplicidade: R$ 0,00.`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Aprovar", onPress: async () => {
            setActing(id);
            try {
              const { data } = await api.post<any>(`/admin/checklists/${id}/approve`);
              Alert.alert(
                data.validation_status === "valido" ? "✅ Aprovado — Válido" : "⚠️ Aprovado — Duplicidade",
                data.message,
              );
              await load();
            } catch (e) { Alert.alert("Erro", apiErrorMessage(e)); }
            finally { setActing(""); }
          },
        },
      ],
    );
  };

  const submitReject = async () => {
    if (!rejectModal) return;
    if (!reason.trim()) { Alert.alert("Motivo", "Informe o motivo da recusa"); return; }
    setActing(rejectModal.id);
    try {
      await api.post(`/admin/checklists/${rejectModal.id}/reject`, { reason: reason.trim() });
      setRejectModal(null); setReason("");
      await load();
    } catch (e) { Alert.alert("Erro", apiErrorMessage(e)); }
    finally { setActing(""); }
  };

  if (user && user.role !== "admin") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg, justifyContent: "center", alignItems: "center" }}>
        <Ionicons name="lock-closed" size={48} color={colors.textDim} />
        <Text style={{ color: colors.textMuted, fontWeight: "800", marginTop: 16 }}>Acesso restrito a administradores</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <View>
          <Text style={styles.title}>Aprovações</Text>
          <Text style={styles.subtitle}>{items.length} pendente(s)</Text>
        </View>
        <TouchableOpacity onPress={() => { setRefreshing(true); load(); }}>
          <Ionicons name="refresh" size={22} color={colors.text} />
        </TouchableOpacity>
      </View>

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

          {items.length === 0 ? (
            <View style={{ alignItems: "center", padding: 40 }}>
              <Ionicons name="checkmark-circle" size={56} color={colors.success} />
              <Text style={{ color: colors.textMuted, fontWeight: "700", marginTop: 12 }}>Nenhuma aprovação pendente 🎉</Text>
            </View>
          ) : items.map((p) => (
            <TouchableOpacity
              key={p.id}
              onPress={() => router.push(`/admin/approval/${p.id}` as any)}
              style={styles.card}
              testID={`pending-${p.numero}`}
            >
              <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <View style={styles.plateBadge}><Text style={styles.plateTxt}>{p.placa}</Text></View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.cardTitle}>{p.numero}</Text>
                  <Text style={styles.cardSub}>{p.empresa} • {p.tipo_atendimento}</Text>
                </View>
                <Ionicons name="chevron-forward" size={22} color={colors.textMuted} />
              </View>
              <View style={styles.row}>
                <Ionicons name="person-outline" size={14} color={colors.textMuted} />
                <Text style={styles.rowTxt}>{p.nome} {p.sobrenome}</Text>
              </View>
              <View style={styles.row}>
                <Ionicons name="briefcase-outline" size={14} color={colors.textMuted} />
                <Text style={styles.rowTxt}>Técnico: {p.technician_name}</Text>
              </View>
              {!!p.imei && (
                <View style={styles.row}>
                  <Ionicons name="hardware-chip-outline" size={14} color={colors.textMuted} />
                  <Text style={styles.rowTxt}>IMEI {p.imei}</Text>
                </View>
              )}
              {!!p.execution_elapsed_sec && (
                <View style={styles.row}>
                  <Ionicons name="time-outline" size={14} color={colors.textMuted} />
                  <Text style={styles.rowTxt}>Execução: {Math.floor((p.execution_elapsed_sec || 0) / 60)} min</Text>
                </View>
              )}
              <View style={styles.hintRow}>
                <Ionicons name="eye-outline" size={14} color={colors.primary} />
                <Text style={styles.hintTxt}>Toque para revisar detalhes, fotos e assinatura antes de aprovar</Text>
              </View>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      {/* Modal de recusa */}
      <Modal visible={!!rejectModal} transparent animationType="slide" onRequestClose={() => setRejectModal(null)}>
        <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={{ flex: 1 }}>
          <Pressable style={styles.backdrop} onPress={() => setRejectModal(null)}>
            <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation?.()}>
              <Text style={styles.sheetTitle}>Recusar {rejectModal?.numero}</Text>
              <Text style={styles.sheetSub}>Informe o motivo da recusa</Text>
              <TextInput
                value={reason}
                onChangeText={setReason}
                placeholder="Ex: fotos ruins, falta de evidências..."
                placeholderTextColor={colors.textDim}
                style={[styles.input, { minHeight: 90, textAlignVertical: "top" }]}
                multiline
              />
              <View style={{ flexDirection: "row", gap: 10, marginTop: 12 }}>
                <TouchableOpacity onPress={() => setRejectModal(null)} style={[styles.btn, { flex: 1, backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border }]}>
                  <Text style={{ color: colors.text, fontWeight: "700" }}>Cancelar</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={submitReject} disabled={!!acting} style={[styles.btn, { flex: 1, backgroundColor: colors.danger }]}>
                  {acting ? <ActivityIndicator color="#FFF" /> : <Text style={styles.btnTxtWhite}>Confirmar recusa</Text>}
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
  subtitle: { color: colors.textMuted, fontSize: fonts.size.xs },
  card: { backgroundColor: colors.surface, padding: space.md, borderRadius: radii.md, marginBottom: space.sm, borderWidth: 1, borderColor: colors.border, ...shadow.sm },
  cardTitle: { color: colors.text, fontWeight: "900", fontSize: fonts.size.sm },
  cardSub: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 2 },
  plateBadge: { backgroundColor: colors.primary, paddingHorizontal: 10, paddingVertical: 6, borderRadius: radii.sm },
  plateTxt: { color: colors.onPrimary, fontWeight: "900", fontSize: fonts.size.xs, letterSpacing: 1 },
  row: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 4 },
  rowTxt: { color: colors.textMuted, fontSize: fonts.size.xs },
  hintRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 10, paddingTop: 8, borderTopWidth: 1, borderTopColor: colors.border },
  hintTxt: { color: colors.primary, fontSize: 11, fontWeight: "700", flex: 1 },
  btnRow: { flexDirection: "row", gap: 8, marginTop: 12 },
  btn: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, paddingVertical: 10, borderRadius: radii.md },
  btnApprove: { backgroundColor: colors.success },
  btnReject: { backgroundColor: colors.danger },
  btnTxtWhite: { color: "#FFF", fontWeight: "900", fontSize: fonts.size.xs },
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.6)", justifyContent: "flex-end" },
  sheet: { backgroundColor: colors.surface, padding: space.lg, borderTopLeftRadius: 20, borderTopRightRadius: 20 },
  sheetTitle: { color: colors.text, fontWeight: "900", fontSize: fonts.size.md },
  sheetSub: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 4, marginBottom: 10 },
  input: { backgroundColor: colors.surfaceAlt, borderColor: colors.border, borderWidth: 1, borderRadius: radii.md, padding: 12, color: colors.text, fontSize: fonts.size.md },
});
