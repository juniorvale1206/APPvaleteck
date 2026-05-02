import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, Alert, Image, Modal, TextInput, Pressable, KeyboardAvoidingView, Platform, Linking } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import * as FileSystem from "expo-file-system";
import * as Sharing from "expo-sharing";
import { api, apiErrorMessage, getAccessToken, type Checklist } from "../../../../src/api";
import { useAuth } from "../../../../src/auth";
import { colors, fonts, radii, shadow, space } from "../../../../src/theme";

function Row({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowVal}>{value}</Text>
    </View>
  );
}

export default function AdminApprovalDetail() {
  const router = useRouter();
  const { user } = useAuth();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [item, setItem] = useState<Checklist | null>(null);
  const [techName, setTechName] = useState("");
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState("");
  const [rejectOpen, setRejectOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [zoomPhoto, setZoomPhoto] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setError("");
    try {
      const { data } = await api.get<Checklist>(`/checklists/${id}`);
      setItem(data);
      // buscar nome do técnico
      try {
        const r = await api.get<{ technicians: any[] }>("/admin/technicians");
        const t = r.data.technicians.find((u: any) => u.id === data.user_id);
        setTechName(t?.name || data.user_id);
      } catch { /* ignore */ }
    } catch (e) { setError(apiErrorMessage(e)); }
    finally { setLoading(false); }
  }, [id]);

  useFocusEffect(useCallback(() => { setLoading(true); load(); }, [load]));

  const approve = () => {
    if (!item) return;
    const svcName = item.service_type_name || "Sem tipo";
    const slaMax = item.sla_max_minutes || 0;
    const elapsed = Math.round((item.sla_total_sec || item.execution_elapsed_sec || 0) / 60);
    const slaTxt = slaMax ? `${elapsed}min / ${slaMax}min SLA` : "SLA não definido";
    Alert.alert(
      "Aprovar e Processar",
      `${item.numero} — ${svcName}\n⏱️ ${slaTxt}\n\nO motor financeiro vai executar:\n• Duplicidade 30d (regra antiga)\n• Garantia ≤90d (mesma placa+tipo → R$ 0)\n• Retorno ≤30d (débito R$ 30 no técnico original)\n• Corte SLA 50% se extrapolar\n• Valor final creditado`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Aprovar", onPress: async () => {
            setActing(true);
            try {
              const { data } = await api.post<any>(`/admin/checklists/${item.id}/approve`);
              const c = data.compensation || {};
              const lines = [
                `💰 Valor final: R$ ${(c.comp_final_value || 0).toFixed(2)}`,
                `📊 Base (antes de regras): R$ ${(c.comp_base_value || 0).toFixed(2)}`,
              ];
              if (c.comp_sla_cut) lines.push("⏱️ SLA extrapolado — corte de 50% aplicado");
              if (c.comp_warranty_zero) lines.push("🔒 Garantia 90d (mesma placa+tipo) — OS = R$ 0,00");
              if (c.comp_return_flagged) lines.push(`💸 Retorno 30d — R$ ${(c.comp_penalty_on_original || 0).toFixed(2)} debitado do técnico original`);
              if (data.validation_status === "duplicidade_garantia") lines.push("⚠️ Duplicidade detectada (regra 30d antiga)");
              lines.push(`Nível aplicado: ${(c.comp_level_applied || "").toUpperCase()}`);
              Alert.alert(
                c.comp_warranty_zero ? "⚠️ Aprovado — Garantia"
                  : c.comp_sla_cut ? "⏱️ Aprovado — SLA Cortado"
                  : "✅ Aprovado",
                lines.join("\n"),
                [{ text: "OK", onPress: () => router.back() }],
              );
            } catch (e) { Alert.alert("Erro", apiErrorMessage(e)); }
            finally { setActing(false); }
          },
        },
      ],
    );
  };

  const submitReject = async () => {
    if (!item) return;
    if (!reason.trim()) { Alert.alert("Motivo", "Informe o motivo da recusa"); return; }
    setActing(true);
    try {
      await api.post(`/admin/checklists/${item.id}/reject`, { reason: reason.trim() });
      setRejectOpen(false); setReason("");
      Alert.alert("Checklist reprovado", "O técnico será notificado.", [{ text: "OK", onPress: () => router.back() }]);
    } catch (e) { Alert.alert("Erro", apiErrorMessage(e)); }
    finally { setActing(false); }
  };

  const downloadPdf = async () => {
    if (!item) return;
    try {
      const base = process.env.EXPO_PUBLIC_BACKEND_URL;
      const token = await getAccessToken();
      const url = `${base}/api/checklists/${item.id}/pdf`;
      if (Platform.OS === "web") {
        const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
        const blob = await res.blob();
        window.open(URL.createObjectURL(blob), "_blank");
        return;
      }
      const fname = `${FileSystem.cacheDirectory}checklist-${item.numero}.pdf`;
      const res = await FileSystem.downloadAsync(url, fname, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(res.uri, { mimeType: "application/pdf" });
    } catch (e) { Alert.alert("Erro", apiErrorMessage(e)); }
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
        <Text style={styles.title}>Revisar OS</Text>
        <TouchableOpacity onPress={downloadPdf}><Ionicons name="document-text-outline" size={22} color={colors.text} /></TouchableOpacity>
      </View>

      {loading ? (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}><ActivityIndicator color={colors.primary} /></View>
      ) : item ? (
        <>
          <ScrollView contentContainerStyle={{ padding: space.lg, paddingBottom: 140 }}>
            {error ? <Text style={{ color: colors.danger }}>{error}</Text> : null}

            {/* Header card */}
            <View style={styles.heroCard}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 8 }}>
                <View style={styles.plateBadge}><Text style={styles.plateTxt}>{item.placa}</Text></View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.heroNumero}>{item.numero}</Text>
                  <Text style={styles.heroSub}>Status: <Text style={{ fontWeight: "900", color: colors.primary }}>{item.status.toUpperCase()}</Text></Text>
                </View>
              </View>
              <Text style={styles.heroTech}>Técnico: {techName || item.user_id}</Text>
              {!!item.sent_at && <Text style={styles.heroMeta}>Enviado em {new Date(item.sent_at).toLocaleString("pt-BR")}</Text>}
            </View>

            {/* v14 — Preview do Motor de Comissionamento */}
            {(item.service_type_code || item.sla_total_sec) && (() => {
              const slaMax = item.sla_max_minutes || 0;
              const elapsedMin = Math.round((item.sla_total_sec || item.execution_elapsed_sec || 0) / 60);
              const baseValue = item.sla_base_value || 0;
              const slaOver = slaMax > 0 && elapsedMin > slaMax;
              const estFinal = slaOver ? baseValue / 2 : baseValue;
              const photoDelay = item.equipment_photo_delay_sec || 0;
              const photoFlag = !!item.equipment_photo_flag;
              return (
                <View style={[styles.card, { borderColor: slaOver ? colors.danger : colors.success, borderWidth: 1.5 }]} testID="motor-preview">
                  <Text style={styles.cardTitle}>⚙️ Motor de Comissionamento (preview)</Text>
                  <Row label="Serviço" value={item.service_type_name || item.service_type_code} />
                  <Row
                    label="Tempo de execução"
                    value={`${elapsedMin} min${slaMax > 0 ? ` / ${slaMax} min SLA` : ""}`}
                  />
                  <Row
                    label="Status SLA"
                    value={slaOver ? "⏱️ EXTRAPOLADO — corte 50%" : "✅ Dentro do SLA"}
                  />
                  <Row label="Valor base" value={`R$ ${baseValue.toFixed(2)}`} />
                  <Row label="Valor estimado" value={`R$ ${estFinal.toFixed(2)}`} />
                  {item.comp_final_value !== undefined && (
                    <Row label="Valor FINAL (já processado)" value={`R$ ${item.comp_final_value.toFixed(2)}`} />
                  )}
                  {photoDelay > 0 && (
                    <Row
                      label="Foto equipamento enviada em"
                      value={`${photoDelay}s ${photoFlag ? "⚠️ > 3min (FRAUDE DE SLA)" : "✓"}`}
                    />
                  )}
                  {item.comp_warranty_zero && (
                    <Row label="⚠️ Garantia 90d" value="OS ficará R$ 0,00" />
                  )}
                  {item.comp_return_flagged && (
                    <Row label="💸 Retorno 30d" value={`-R$ ${(item.comp_penalty_on_original || 0).toFixed(2)} do técnico original`} />
                  )}
                </View>
              );
            })()}

            {/* Cliente */}
            <View style={styles.card}>
              <Text style={styles.cardTitle}>👤 Cliente</Text>
              <Row label="Nome" value={`${item.nome} ${item.sobrenome}`} />
              <Row label="Placa" value={item.placa} />
              <Row label="Telefone" value={item.telefone} />
              <Row label="Observações" value={item.obs_iniciais} />
              {!!item.problems_client?.length && (
                <Row label="Problemas relatados" value={item.problems_client.join(" • ")} />
              )}
            </View>

            {/* Veículo */}
            {(item.vehicle_brand || item.vehicle_model) && (
              <View style={styles.card}>
                <Text style={styles.cardTitle}>🚗 Veículo</Text>
                <Row label="Tipo" value={item.vehicle_type} />
                <Row label="Marca/Modelo" value={`${item.vehicle_brand || ""} ${item.vehicle_model || ""}`.trim()} />
                <Row label="Ano" value={item.vehicle_year} />
                <Row label="Cor" value={item.vehicle_color} />
                <Row label="KM" value={item.vehicle_odometer != null ? String(item.vehicle_odometer) : ""} />
              </View>
            )}

            {/* Instalação */}
            <View style={styles.card}>
              <Text style={styles.cardTitle}>🔧 Instalação</Text>
              <Row label="Empresa" value={item.empresa} />
              <Row label="Equipamento" value={item.equipamento} />
              <Row label="Tipo" value={item.tipo_atendimento} />
              <Row label="IMEI" value={item.imei} />
              <Row label="ICCID" value={item.iccid} />
              <Row label="Bateria" value={`${item.battery_state || "—"}${item.battery_voltage ? ` • ${item.battery_voltage}V` : ""}`} />
              <Row label="Acessórios" value={(item.acessorios || []).join(" • ")} />
              <Row label="Obs. técnicas" value={item.obs_tecnicas} />
              {!!item.execution_elapsed_sec && (
                <Row label="Tempo de execução" value={`${Math.floor(item.execution_elapsed_sec / 60)} min`} />
              )}
              {item.device_online != null && (
                <Row label="Dispositivo" value={item.device_online ? "✅ Online" : "❌ Offline"} />
              )}
            </View>

            {/* Equipamentos Retirados (Fase 3) */}
            {!!item.removed_equipments?.length && (
              <View style={styles.card}>
                <Text style={styles.cardTitle}>📤 Equipamentos retirados ({item.removed_equipments.length})</Text>
                {item.removed_equipments.map((e: any, i: number) => (
                  <View key={i} style={styles.removedRow}>
                    <Ionicons name="return-up-back-outline" size={16} color="#9A3412" />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.removedTitle}>{e.tipo}{e.modelo ? ` — ${e.modelo}` : ""}</Text>
                      <Text style={styles.removedMeta}>
                        {e.imei ? `IMEI ${e.imei}` : ""}{e.serie ? ` • SN ${e.serie}` : ""}
                        {e.estado ? ` • Estado: ${e.estado}` : ""}
                      </Text>
                      {!!e.notes && <Text style={styles.removedNotes}>{e.notes}</Text>}
                    </View>
                  </View>
                ))}
              </View>
            )}

            {/* Alerts de fraude */}
            {!!item.alerts?.length && (
              <View style={[styles.card, { backgroundColor: "#FFFBEB", borderColor: "#FCD34D", borderWidth: 1 }]}>
                <Text style={[styles.cardTitle, { color: "#78350F" }]}>⚠️ Alertas do sistema</Text>
                {item.alerts.map((a, i) => (
                  <View key={i} style={{ flexDirection: "row", gap: 6, alignItems: "flex-start", marginTop: 4 }}>
                    <Ionicons name="warning" size={16} color="#78350F" />
                    <Text style={{ color: "#78350F", fontSize: fonts.size.sm, flex: 1 }}>{a}</Text>
                  </View>
                ))}
              </View>
            )}

            {/* Fotos */}
            {!!item.photos?.length && (
              <View style={styles.card}>
                <Text style={styles.cardTitle}>📸 Fotos ({item.photos.length})</Text>
                <View style={styles.photosGrid}>
                  {item.photos.map((p: any, i: number) => {
                    const uri = p.url || p.base64;
                    if (!uri) return null;
                    return (
                      <TouchableOpacity key={i} onPress={() => setZoomPhoto(uri)} style={styles.photoBox}>
                        <Image source={{ uri }} style={styles.photoThumb} />
                        {!!p.label && <Text style={styles.photoLabel}>{p.label}</Text>}
                      </TouchableOpacity>
                    );
                  })}
                </View>
              </View>
            )}

            {/* Assinatura */}
            {(!!item.signature_url || !!item.signature_base64) && (
              <View style={styles.card}>
                <Text style={styles.cardTitle}>✍️ Assinatura do cliente</Text>
                <View style={styles.sigBox}>
                  <Image source={{ uri: item.signature_url || item.signature_base64 }} style={{ flex: 1 }} resizeMode="contain" />
                </View>
              </View>
            )}

            {/* Localização */}
            {item.location && (
              <View style={styles.card}>
                <Text style={styles.cardTitle}>📍 Localização</Text>
                <Row label="Lat" value={String(item.location.lat)} />
                <Row label="Lng" value={String(item.location.lng)} />
                <TouchableOpacity
                  onPress={() => Linking.openURL(`https://www.google.com/maps?q=${item.location!.lat},${item.location!.lng}`)}
                  style={styles.mapBtn}
                >
                  <Ionicons name="map-outline" size={16} color={colors.primary} />
                  <Text style={styles.mapBtnTxt}>Ver no Google Maps</Text>
                </TouchableOpacity>
              </View>
            )}
          </ScrollView>

          {/* STICKY FOOTER com ações */}
          {["enviado", "em_auditoria"].includes(item.status) && (
            <View style={styles.footer}>
              <TouchableOpacity
                testID="footer-reject"
                onPress={() => setRejectOpen(true)}
                disabled={acting}
                style={[styles.footerBtn, { backgroundColor: colors.danger }]}
              >
                <Ionicons name="close-circle" size={20} color="#FFF" />
                <Text style={styles.footerBtnTxt}>Recusar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                testID="footer-approve"
                onPress={approve}
                disabled={acting}
                style={[styles.footerBtn, { backgroundColor: colors.success, flex: 2 }]}
              >
                {acting ? <ActivityIndicator color="#FFF" /> : (
                  <>
                    <Ionicons name="checkmark-circle" size={20} color="#FFF" />
                    <Text style={styles.footerBtnTxt}>Aprovar e Processar</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          )}

          {/* Modal zoom foto */}
          <Modal visible={!!zoomPhoto} transparent animationType="fade" onRequestClose={() => setZoomPhoto(null)}>
            <Pressable style={styles.zoomBackdrop} onPress={() => setZoomPhoto(null)}>
              <Image source={{ uri: zoomPhoto || "" }} style={styles.zoomImg} resizeMode="contain" />
              <TouchableOpacity style={styles.zoomClose} onPress={() => setZoomPhoto(null)}>
                <Ionicons name="close" size={28} color="#FFF" />
              </TouchableOpacity>
            </Pressable>
          </Modal>

          {/* Modal recusa */}
          <Modal visible={rejectOpen} transparent animationType="slide" onRequestClose={() => setRejectOpen(false)}>
            <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={{ flex: 1 }}>
              <Pressable style={styles.backdrop} onPress={() => setRejectOpen(false)}>
                <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation?.()}>
                  <Text style={styles.sheetTitle}>Recusar {item.numero}</Text>
                  <Text style={styles.sheetSub}>Informe o motivo da recusa (obrigatório)</Text>
                  <TextInput
                    value={reason}
                    onChangeText={setReason}
                    placeholder="Ex: fotos ruins, falta de evidências..."
                    placeholderTextColor={colors.textDim}
                    style={[styles.input, { minHeight: 90, textAlignVertical: "top" }]}
                    multiline
                  />
                  <View style={{ flexDirection: "row", gap: 10, marginTop: 12 }}>
                    <TouchableOpacity onPress={() => setRejectOpen(false)} style={[styles.footerBtn, { flex: 1, backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border }]}>
                      <Text style={{ color: colors.text, fontWeight: "700" }}>Cancelar</Text>
                    </TouchableOpacity>
                    <TouchableOpacity onPress={submitReject} disabled={acting} style={[styles.footerBtn, { flex: 1, backgroundColor: colors.danger }]}>
                      {acting ? <ActivityIndicator color="#FFF" /> : <Text style={styles.footerBtnTxt}>Confirmar recusa</Text>}
                    </TouchableOpacity>
                  </View>
                </Pressable>
              </Pressable>
            </KeyboardAvoidingView>
          </Modal>
        </>
      ) : null}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingVertical: space.sm },
  title: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "900" },
  heroCard: { backgroundColor: colors.brandBlack, padding: space.md, borderRadius: radii.md, marginBottom: space.md },
  heroNumero: { color: colors.primary, fontWeight: "900", fontSize: fonts.size.md },
  heroSub: { color: "#DDD", fontSize: fonts.size.xs, marginTop: 2 },
  heroTech: { color: "#FFF", fontSize: fonts.size.sm, marginTop: 4, fontWeight: "700" },
  heroMeta: { color: "#AAA", fontSize: fonts.size.xs, marginTop: 2 },
  plateBadge: { backgroundColor: colors.primary, paddingHorizontal: 10, paddingVertical: 6, borderRadius: radii.sm },
  plateTxt: { color: colors.onPrimary, fontWeight: "900", fontSize: fonts.size.xs, letterSpacing: 1 },
  card: { backgroundColor: colors.surface, padding: space.md, borderRadius: radii.md, marginBottom: space.sm, borderWidth: 1, borderColor: colors.border, ...shadow.sm },
  cardTitle: { color: colors.text, fontWeight: "900", fontSize: fonts.size.md, marginBottom: 8 },
  row: { flexDirection: "row", paddingVertical: 4, gap: 8 },
  rowLabel: { color: colors.textMuted, fontSize: fonts.size.xs, width: 120, fontWeight: "700" },
  rowVal: { color: colors.text, fontSize: fonts.size.sm, flex: 1, fontWeight: "600" },
  photosGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  photoBox: { width: "31%" },
  photoThumb: { width: "100%", aspectRatio: 1, borderRadius: radii.sm, backgroundColor: colors.surfaceAlt },
  photoLabel: { color: colors.textMuted, fontSize: 10, marginTop: 2, textAlign: "center" },
  sigBox: { height: 100, backgroundColor: "#FFF", borderRadius: radii.sm, borderWidth: 1, borderColor: colors.border },
  mapBtn: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 8, padding: 8, backgroundColor: colors.brandBlack, borderRadius: radii.sm, alignSelf: "flex-start" },
  mapBtnTxt: { color: colors.primary, fontSize: fonts.size.xs, fontWeight: "800" },
  removedRow: { flexDirection: "row", gap: 8, paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: colors.border },
  removedTitle: { color: colors.text, fontWeight: "800", fontSize: fonts.size.sm },
  removedMeta: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 2 },
  removedNotes: { color: colors.textMuted, fontSize: fonts.size.xs, fontStyle: "italic", marginTop: 2 },
  footer: {
    position: "absolute", left: 0, right: 0, bottom: 0,
    flexDirection: "row", gap: 10, padding: space.lg,
    backgroundColor: colors.bg, borderTopWidth: 1, borderTopColor: colors.border,
  },
  footerBtn: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, paddingVertical: 14, borderRadius: radii.md },
  footerBtnTxt: { color: "#FFF", fontWeight: "900", fontSize: fonts.size.sm },
  zoomBackdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.95)", alignItems: "center", justifyContent: "center" },
  zoomImg: { width: "100%", height: "80%" },
  zoomClose: { position: "absolute", top: 40, right: 20, padding: 10, backgroundColor: "rgba(255,255,255,0.2)", borderRadius: 999 },
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.6)", justifyContent: "flex-end" },
  sheet: { backgroundColor: colors.surface, padding: space.lg, borderTopLeftRadius: 20, borderTopRightRadius: 20 },
  sheetTitle: { color: colors.text, fontWeight: "900", fontSize: fonts.size.md },
  sheetSub: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 4, marginBottom: 10 },
  input: { backgroundColor: colors.surfaceAlt, borderColor: colors.border, borderWidth: 1, borderRadius: radii.md, padding: 12, color: colors.text, fontSize: fonts.size.md },
});
