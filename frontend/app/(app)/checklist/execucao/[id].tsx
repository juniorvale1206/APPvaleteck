import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator,
  Alert, AppState, Modal, Image, Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { api, apiErrorMessage, type Checklist } from "../../../../src/api";
import { colors, fonts, radii, shadow, space } from "../../../../src/theme";

const EQUIPMENT_PHOTO_WINDOW_SEC = 180; // 3 minutos

function formatDuration(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  const hh = Math.floor(s / 3600);
  const mm = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const pad = (n: number) => n.toString().padStart(2, "0");
  return hh > 0 ? `${pad(hh)}:${pad(mm)}:${pad(ss)}` : `${pad(mm)}:${pad(ss)}`;
}

export default function Execucao() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [item, setItem] = useState<Checklist | null>(null);
  const [loading, setLoading] = useState(true);
  const [nowMs, setNowMs] = useState(Date.now());
  const [photoPicking, setPhotoPicking] = useState(false);
  const [photoUploading, setPhotoUploading] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [finalizeModalOpen, setFinalizeModalOpen] = useState(false);
  const [checkoutPhoto, setCheckoutPhoto] = useState<string>("");
  const [checkoutBusy, setCheckoutBusy] = useState(false);
  const tickRef = useRef<any>(null);

  const loadItem = useCallback(async () => {
    if (!id) return;
    try {
      const { data } = await api.get<Checklist>(`/checklists/${id}`);
      setItem(data);
    } catch (e) { Alert.alert("Erro", apiErrorMessage(e)); }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => { loadItem(); }, [loadItem]);

  // Tick global a cada segundo
  useEffect(() => {
    tickRef.current = setInterval(() => setNowMs(Date.now()), 1000);
    const sub = AppState.addEventListener("change", (s) => { if (s === "active") setNowMs(Date.now()); });
    return () => { clearInterval(tickRef.current); sub.remove(); };
  }, []);

  const sentMs = item?.checklist_sent_at ? new Date(item.checklist_sent_at).getTime() : null;
  const elapsedSec = useMemo(() => {
    if (!sentMs) return 0;
    if (item?.service_finished_at) {
      return Math.floor((new Date(item.service_finished_at).getTime() - sentMs) / 1000);
    }
    return Math.floor((nowMs - sentMs) / 1000);
  }, [sentMs, nowMs, item?.service_finished_at]);

  const slaMax = item?.sla_max_minutes || 0;
  const slaMaxSec = slaMax * 60;
  const slaPct = slaMaxSec > 0 ? Math.min(elapsedSec / slaMaxSec, 2) : 0;
  const slaOver = slaMaxSec > 0 && elapsedSec > slaMaxSec;
  const slaWarn = slaPct >= 0.8 && !slaOver;
  const slaColor = slaOver ? colors.danger : slaWarn ? colors.warning : colors.success;

  // Janela de 3 min para foto do equipamento (apenas instalação/telemetria)
  const needsEquipmentPhoto = item?.phase === "awaiting_equipment_photo";
  const photoRemainingSec = needsEquipmentPhoto && sentMs
    ? Math.max(0, EQUIPMENT_PHOTO_WINDOW_SEC - Math.floor((nowMs - sentMs) / 1000))
    : 0;
  const photoOverdue = needsEquipmentPhoto && photoRemainingSec === 0 && elapsedSec > EQUIPMENT_PHOTO_WINDOW_SEC;

  const finished = item?.phase === "finalized";

  // --- Actions ---
  const uploadEquipmentPhoto = async () => {
    setPhotoPicking(true);
    try {
      const perm = await ImagePicker.requestCameraPermissionsAsync();
      if (!perm.granted) { Alert.alert("Permissão", "Câmera necessária para foto do equipamento."); return; }
      const res = await ImagePicker.launchCameraAsync({
        allowsEditing: false, quality: 0.6, base64: true,
      });
      if (res.canceled || !res.assets?.[0]?.base64) return;
      const base64 = `data:image/jpeg;base64,${res.assets[0].base64}`;
      setPhotoUploading(true);
      try {
        const { data } = await api.post<Checklist>(`/checklists/${id}/equipment-photo`, {
          photo_base64: base64,
        });
        setItem(data);
        if (data.equipment_photo_flag) {
          Alert.alert("⚠️ Foto com atraso", `Enviada ${data.equipment_photo_delay_sec}s após início. Admin será notificado.`);
        } else {
          Alert.alert("✅ Foto registrada", `Em ${data.equipment_photo_delay_sec}s após início.`);
        }
      } finally { setPhotoUploading(false); }
    } catch (e) { Alert.alert("Erro", apiErrorMessage(e)); }
    finally { setPhotoPicking(false); }
  };

  const confirmFinalize = () => { setCheckoutPhoto(""); setFinalizeModalOpen(true); };

  const captureCheckoutPhoto = async () => {
    setCheckoutBusy(true);
    try {
      const perm = await ImagePicker.requestCameraPermissionsAsync();
      if (!perm.granted) { Alert.alert("Permissão", "Câmera necessária."); return; }
      const res = await ImagePicker.launchCameraAsync({
        allowsEditing: false, quality: 0.6, base64: true,
      });
      if (res.canceled || !res.assets?.[0]?.base64) return;
      setCheckoutPhoto(`data:image/jpeg;base64,${res.assets[0].base64}`);
    } catch (e: any) { Alert.alert("Erro", e?.message || "Falha na câmera"); }
    finally { setCheckoutBusy(false); }
  };

  const doFinalize = async () => {
    if (!checkoutPhoto) {
      Alert.alert("Foto obrigatória", "Tire a foto do painel (check-out) antes de finalizar.");
      return;
    }
    setFinishing(true);
    try {
      const { data } = await api.post<Checklist>(`/checklists/${id}/finalize`, {
        dashboard_photo_base64: checkoutPhoto,
      });
      setItem(data);
      setFinalizeModalOpen(false);
      Alert.alert(
        "✅ Serviço finalizado",
        `Tempo total: ${formatDuration(data.sla_total_sec || 0)}\n✓ Check-in e Check-out registrados.\nAgora conclua as evidências e assinatura.`,
        [{ text: "OK", onPress: () => router.replace({ pathname: "/(app)/checklist/new/evidencias", params: { id } }) }],
      );
    } catch (e) { Alert.alert("Erro", apiErrorMessage(e)); }
    finally { setFinishing(false); }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.sa}>
        <ActivityIndicator color={colors.primary} style={{ marginTop: 40 }} />
      </SafeAreaView>
    );
  }

  if (!item || !sentMs) {
    return (
      <SafeAreaView style={styles.sa}>
        <View style={{ padding: space.lg }}>
          <Text style={{ color: colors.text }}>Checklist não iniciado.</Text>
          <TouchableOpacity onPress={() => router.back()} style={[styles.btn, { backgroundColor: colors.primary, marginTop: 16 }]}>
            <Text style={styles.btnTxt}>Voltar</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.sa} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} testID="exec-back">
          <Ionicons name="arrow-back" size={26} color={colors.text} />
        </TouchableOpacity>
        <Text style={styles.title}>Em execução</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: space.lg, paddingBottom: 140 }}>
        {/* Cronômetro ao vivo */}
        <View style={[styles.timerCard, { borderColor: slaColor, backgroundColor: slaColor + "10" }]} testID="live-timer">
          <Text style={styles.timerLabel}>SLA total — server-side</Text>
          <Text style={[styles.timerValue, { color: slaColor }]} testID="timer-value">{formatDuration(elapsedSec)}</Text>
          <Text style={styles.timerSub}>
            {item.service_type_name}{slaMax ? ` • Máx ${slaMax} min` : ""}
          </Text>
          {slaMax > 0 && (
            <View style={styles.barWrap}>
              <View style={[styles.barFill, {
                width: `${Math.min(slaPct * 100, 100)}%`, backgroundColor: slaColor,
              }]} />
            </View>
          )}
          {slaOver && (
            <Text style={styles.warnTxt}>⚠️ SLA extrapolado — valor pode ser cortado em 50% na aprovação</Text>
          )}
        </View>

        {/* Banner foto 3min (só instalação/telemetria) */}
        {needsEquipmentPhoto && (
          <View style={[styles.photoBanner, { backgroundColor: photoOverdue ? "#7F1D1D" : "#B45309" }]} testID="photo-banner">
            <Ionicons name={photoOverdue ? "alert-circle" : "camera"} size={28} color="#FFF" />
            <View style={{ flex: 1 }}>
              <Text style={styles.bannerTitle}>
                {photoOverdue ? "⚠️ Foto em atraso — envie agora" : "📸 Foto obrigatória do equipamento"}
              </Text>
              <Text style={styles.bannerSub}>
                {photoOverdue
                  ? `Atraso: ${formatDuration(elapsedSec - EQUIPMENT_PHOTO_WINDOW_SEC)} (admin notificado)`
                  : `Tempo restante: ${formatDuration(photoRemainingSec)}`}
              </Text>
              <Text style={styles.bannerTip}>Rastreador + IMEI + placa/chassi numa só foto</Text>
            </View>
            <TouchableOpacity
              testID="btn-camera"
              style={styles.bannerBtn}
              onPress={uploadEquipmentPhoto}
              disabled={photoPicking || photoUploading}
            >
              {photoPicking || photoUploading ? (
                <ActivityIndicator color="#FFF" />
              ) : (
                <Ionicons name="camera" size={28} color="#FFF" />
              )}
            </TouchableOpacity>
          </View>
        )}

        {/* Foto já enviada */}
        {item.equipment_photo_at && (
          <View style={[styles.successBanner, { borderColor: item.equipment_photo_flag ? colors.warning : colors.success }]} testID="photo-ok">
            <Ionicons name={item.equipment_photo_flag ? "warning" : "checkmark-circle"} size={22}
              color={item.equipment_photo_flag ? colors.warning : colors.success} />
            <Text style={[styles.successTxt, { color: item.equipment_photo_flag ? colors.warning : colors.success }]}>
              {item.equipment_photo_flag
                ? `⚠️ Foto com atraso (${item.equipment_photo_delay_sec}s)`
                : `✅ Foto enviada em ${item.equipment_photo_delay_sec}s`}
            </Text>
            {item.equipment_photo_url && item.equipment_photo_url.startsWith("data:") && (
              <Image source={{ uri: item.equipment_photo_url }} style={styles.thumb} />
            )}
          </View>
        )}

        {/* Dados compactos */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Dados da OS</Text>
          <Row label="Número" value={item.numero} />
          <Row label="Cliente" value={`${item.nome} ${item.sobrenome}`} />
          <Row label="Placa" value={item.placa} />
          <Row label="Empresa" value={item.empresa} />
          <Row label="Fase" value={(item.phase || "").toUpperCase()} />
        </View>

        {/* Botão Finalizar */}
        {!finished ? (
          <TouchableOpacity
            testID="btn-finalize"
            style={[styles.btn, { backgroundColor: colors.danger }]}
            onPress={confirmFinalize}
            disabled={finishing}
          >
            {finishing
              ? <ActivityIndicator color="#FFF" />
              : <>
                <Ionicons name="stop-circle" size={22} color="#FFF" />
                <Text style={styles.btnTxt}>⏹️ Finalizar OS</Text>
              </>}
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            testID="btn-continue-evidencias"
            style={[styles.btn, { backgroundColor: colors.primary }]}
            onPress={() => router.replace({ pathname: "/(app)/checklist/new/evidencias", params: { id } })}
          >
            <Ionicons name="arrow-forward" size={22} color={colors.onPrimary} />
            <Text style={[styles.btnTxt, { color: colors.onPrimary }]}>Continuar: evidências + assinatura</Text>
          </TouchableOpacity>
        )}
      </ScrollView>

      {/* Modal confirmação de finalização com check-out do painel */}
      <Modal visible={finalizeModalOpen} transparent animationType="fade" onRequestClose={() => setFinalizeModalOpen(false)}>
        <View style={styles.modalBd}>
          <View style={styles.modalCard}>
            <Ionicons name="speedometer" size={44} color={colors.primary} style={{ alignSelf: "center" }} />
            <Text style={styles.modalTitle}>Check-out do veículo</Text>
            <Text style={styles.modalMsg}>
              Foto do painel obrigatória (ignição ligada + KM visível).{"\n"}
              O cronômetro será parado em {formatDuration(elapsedSec)}.
              {slaOver ? "\n\n⚠️ SLA já extrapolado — valor pode ser cortado em 50%." : ""}
            </Text>

            {checkoutPhoto ? (
              <View style={styles.modalPreview}>
                <Image source={{ uri: checkoutPhoto }} style={styles.modalThumb} />
                <TouchableOpacity onPress={() => setCheckoutPhoto("")} style={styles.modalRetake}>
                  <Ionicons name="camera-reverse" size={16} color={colors.text} />
                  <Text style={{ color: colors.text, fontWeight: "700" }}>Refazer</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <TouchableOpacity
                testID="btn-capture-checkout"
                style={[styles.btn, { backgroundColor: colors.primary, marginTop: 8 }]}
                onPress={captureCheckoutPhoto}
                disabled={checkoutBusy}
              >
                {checkoutBusy ? (
                  <ActivityIndicator color={colors.onPrimary} />
                ) : (
                  <>
                    <Ionicons name="camera" size={20} color={colors.onPrimary} />
                    <Text style={[styles.btnTxt, { color: colors.onPrimary }]}>Tirar foto do painel</Text>
                  </>
                )}
              </TouchableOpacity>
            )}

            <View style={styles.modalBtns}>
              <TouchableOpacity style={[styles.btn, { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, flex: 1 }]} onPress={() => setFinalizeModalOpen(false)}>
                <Text style={[styles.btnTxt, { color: colors.text }]}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                testID="btn-finalize-confirm"
                style={[styles.btn, { backgroundColor: checkoutPhoto ? colors.danger : colors.surfaceAlt, flex: 1 }]}
                onPress={doFinalize}
                disabled={finishing || !checkoutPhoto}
              >
                {finishing
                  ? <ActivityIndicator color="#FFF" />
                  : <Text style={[styles.btnTxt, { color: checkoutPhoto ? "#FFF" : colors.textMuted }]}>
                      {checkoutPhoto ? "Finalizar agora" : "📸 Tire a foto"}
                    </Text>}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

function Row({ label, value }: { label: string; value?: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value || "—"}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  sa: { flex: 1, backgroundColor: colors.bg },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingTop: space.sm, paddingBottom: space.sm },
  title: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "800" },
  timerCard: {
    borderWidth: 2, borderRadius: radii.lg, padding: space.lg,
    alignItems: "center", marginBottom: space.md,
  },
  timerLabel: { color: colors.textMuted, fontSize: fonts.size.xs, textTransform: "uppercase", letterSpacing: 1, fontWeight: "700" },
  timerValue: { fontSize: 64, fontWeight: "900", marginVertical: 4, fontVariant: ["tabular-nums"] as any },
  timerSub: { color: colors.text, fontSize: fonts.size.sm, fontWeight: "700" },
  barWrap: { width: "100%", height: 10, backgroundColor: colors.surfaceAlt, borderRadius: 5, overflow: "hidden", marginTop: 12 },
  barFill: { height: "100%", borderRadius: 5 },
  warnTxt: { color: colors.danger, fontWeight: "800", marginTop: 8, fontSize: fonts.size.sm, textAlign: "center" },
  photoBanner: {
    flexDirection: "row", alignItems: "center", gap: 12,
    padding: space.md, borderRadius: radii.md, marginBottom: space.md,
    ...shadow.card,
  },
  bannerTitle: { color: "#FFF", fontWeight: "900", fontSize: fonts.size.md },
  bannerSub: { color: "#FFF", fontSize: fonts.size.sm, marginTop: 2, fontWeight: "700", fontVariant: ["tabular-nums"] as any },
  bannerTip: { color: "#FFD580", fontSize: fonts.size.xs, marginTop: 2 },
  bannerBtn: { backgroundColor: "rgba(0,0,0,0.35)", width: 60, height: 60, borderRadius: 30, alignItems: "center", justifyContent: "center" },
  successBanner: {
    flexDirection: "row", alignItems: "center", gap: 10,
    backgroundColor: colors.surface, borderWidth: 1,
    padding: space.sm, borderRadius: radii.md, marginBottom: space.md,
  },
  successTxt: { flex: 1, fontWeight: "800", fontSize: fonts.size.sm },
  thumb: { width: 48, height: 48, borderRadius: 6 },
  card: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, padding: space.md, marginBottom: space.md },
  cardTitle: { color: colors.text, fontWeight: "800", fontSize: fonts.size.md, marginBottom: 8 },
  row: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 4 },
  rowLabel: { color: colors.textMuted, fontSize: fonts.size.sm },
  rowValue: { color: colors.text, fontSize: fonts.size.sm, fontWeight: "700" },
  btn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    paddingVertical: 14, borderRadius: radii.md,
  },
  btnTxt: { color: "#FFF", fontWeight: "900", fontSize: fonts.size.md },
  modalBd: { flex: 1, backgroundColor: "rgba(0,0,0,0.6)", padding: space.lg, justifyContent: "center" },
  modalCard: { backgroundColor: colors.bg, borderRadius: radii.lg, padding: space.lg, gap: 10 },
  modalTitle: { color: colors.text, fontWeight: "900", fontSize: fonts.size.lg, textAlign: "center" },
  modalMsg: { color: colors.textMuted, fontSize: fonts.size.sm, textAlign: "center", marginBottom: 8 },
  modalPreview: { alignItems: "center", gap: 6, marginVertical: 8 },
  modalThumb: { width: 200, height: 140, borderRadius: 8, backgroundColor: "#000" },
  modalRetake: { flexDirection: "row", alignItems: "center", gap: 6, paddingVertical: 6, paddingHorizontal: 12, borderRadius: 8, backgroundColor: colors.surfaceAlt },
  modalBtns: { flexDirection: "row", gap: 10, marginTop: 8 },
});
