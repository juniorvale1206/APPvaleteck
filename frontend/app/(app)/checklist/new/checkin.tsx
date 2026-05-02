import React, { useState } from "react";
import {
  View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Image, Alert,
  ScrollView, Platform, KeyboardAvoidingView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { useDraft } from "../../../../src/draft";
import { colors, fonts, radii, shadow, space } from "../../../../src/theme";

/**
 * Check-in do Veículo — v14 Fase 3C
 * Tela dedicada entre Cliente e Instalação.
 * Captura foto obrigatória do painel (ignição ligada + KM visível).
 * A foto só será validada server-side no /send-initial; aqui só fazemos
 * UX (preview, retake, tips).
 */
export default function Checkin() {
  const router = useRouter();
  const { draft, set } = useDraft();
  const [busy, setBusy] = useState(false);
  const hasPhoto = !!draft.dashboard_photo_in_base64;

  const takePhoto = async () => {
    setBusy(true);
    try {
      const perm = await ImagePicker.requestCameraPermissionsAsync();
      if (!perm.granted) {
        Alert.alert("Permissão", "Câmera necessária para foto do painel.");
        return;
      }
      const res = await ImagePicker.launchCameraAsync({
        allowsEditing: false, quality: 0.6, base64: true,
      });
      if (res.canceled || !res.assets?.[0]?.base64) return;
      const uri = `data:image/jpeg;base64,${res.assets[0].base64}`;
      set({ dashboard_photo_in_base64: uri });
    } catch (e: any) {
      Alert.alert("Erro", e?.message || "Falha ao abrir câmera");
    } finally { setBusy(false); }
  };

  const retake = () => set({ dashboard_photo_in_base64: "" });

  const next = () => {
    if (!hasPhoto) {
      Alert.alert(
        "Foto obrigatória",
        "O check-in do veículo exige a foto do painel com a ignição ligada antes de prosseguir.",
      );
      return;
    }
    router.push("/(app)/checklist/new/instalacao");
  };

  return (
    <SafeAreaView style={styles.sa} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} testID="checkin-back">
          <Ionicons name="arrow-back" size={26} color={colors.text} />
        </TouchableOpacity>
        <Text style={styles.title}>Check-in do veículo</Text>
        <View style={{ width: 26 }} />
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.bigIcon}>
            <Ionicons name="speedometer" size={56} color={colors.primary} />
          </View>
          <Text style={styles.headline}>Foto do Painel (obrigatória)</Text>
          <Text style={styles.subtitle}>
            Registre o estado do veículo ANTES de iniciar o serviço.{"\n"}
            Esta foto será o Marco Zero do cronômetro de SLA.
          </Text>

          <View style={styles.tipsCard}>
            <Text style={styles.tipsTitle}>Como fazer</Text>
            <Tip num="1" txt="Ligue a ignição do veículo" />
            <Tip num="2" txt="Enquadre o painel com as luzes acesas" />
            <Tip num="3" txt="Certifique-se que o KM está visível" />
          </View>

          {hasPhoto ? (
            <View style={styles.previewCard} testID="checkin-preview">
              <Image source={{ uri: draft.dashboard_photo_in_base64 }} style={styles.preview} />
              <View style={styles.previewActions}>
                <TouchableOpacity style={[styles.btn, styles.btnSecondary]} onPress={retake} testID="btn-retake">
                  <Ionicons name="camera-reverse" size={18} color={colors.text} />
                  <Text style={styles.btnSecondaryTxt}>Refazer</Text>
                </TouchableOpacity>
                <View style={styles.okBadge}>
                  <Ionicons name="checkmark-circle" size={18} color={colors.success} />
                  <Text style={styles.okTxt}>Pronta para envio</Text>
                </View>
              </View>
            </View>
          ) : (
            <TouchableOpacity
              style={[styles.cameraBtn, busy && { opacity: 0.6 }]}
              onPress={takePhoto}
              disabled={busy}
              testID="btn-take-photo"
            >
              {busy ? (
                <ActivityIndicator color="#FFF" />
              ) : (
                <>
                  <Ionicons name="camera" size={36} color="#FFF" />
                  <Text style={styles.cameraTxt}>Abrir câmera</Text>
                </>
              )}
            </TouchableOpacity>
          )}

          <View style={styles.warnBox}>
            <Ionicons name="shield-checkmark" size={18} color={colors.warning} />
            <Text style={styles.warnTxt}>
              A foto será validada por IA (Gemini Vision) no envio.
              Imagens escuras, sem painel ou sem ignição serão rejeitadas.
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>

      <View style={styles.footer}>
        <TouchableOpacity
          style={[styles.btn, hasPhoto ? styles.btnPrimary : styles.btnDisabled]}
          onPress={next}
          disabled={!hasPhoto}
          testID="btn-continue-checkin"
        >
          <Text style={[styles.btnTxt, !hasPhoto && { color: colors.textMuted }]}>
            {hasPhoto ? "Continuar para Instalação" : "📸 Tire a foto para continuar"}
          </Text>
          {hasPhoto && <Ionicons name="arrow-forward" size={18} color={colors.onPrimary} />}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

function Tip({ num, txt }: { num: string; txt: string }) {
  return (
    <View style={styles.tipRow}>
      <View style={styles.tipNum}>
        <Text style={styles.tipNumTxt}>{num}</Text>
      </View>
      <Text style={styles.tipTxt}>{txt}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  sa: { flex: 1, backgroundColor: colors.bg },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingTop: space.sm, paddingBottom: space.sm },
  title: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "900" },
  content: { padding: space.lg, paddingBottom: 120 },
  bigIcon: { alignSelf: "center", width: 96, height: 96, borderRadius: 48, backgroundColor: colors.primary + "20", alignItems: "center", justifyContent: "center", marginVertical: space.md },
  headline: { color: colors.text, fontSize: 22, fontWeight: "900", textAlign: "center" },
  subtitle: { color: colors.textMuted, fontSize: fonts.size.sm, textAlign: "center", marginTop: 6, marginBottom: space.md },
  tipsCard: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, padding: space.md, marginBottom: space.md },
  tipsTitle: { color: colors.text, fontWeight: "800", marginBottom: 8, fontSize: fonts.size.sm, textTransform: "uppercase", letterSpacing: 0.5 },
  tipRow: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 4 },
  tipNum: { width: 22, height: 22, borderRadius: 11, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  tipNumTxt: { color: colors.onPrimary, fontSize: fonts.size.xs, fontWeight: "900" },
  tipTxt: { color: colors.text, fontSize: fonts.size.sm, flex: 1 },
  cameraBtn: {
    backgroundColor: colors.primary, borderRadius: radii.lg,
    paddingVertical: 28, alignItems: "center", justifyContent: "center", gap: 8,
    ...shadow.card,
  },
  cameraTxt: { color: "#FFF", fontWeight: "900", fontSize: fonts.size.lg },
  previewCard: { backgroundColor: colors.surface, borderWidth: 2, borderColor: colors.success, borderRadius: radii.lg, overflow: "hidden" },
  preview: { width: "100%", height: 280, backgroundColor: "#000" },
  previewActions: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: space.sm },
  okBadge: { flexDirection: "row", alignItems: "center", gap: 6 },
  okTxt: { color: colors.success, fontWeight: "800" },
  btn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    paddingVertical: 12, paddingHorizontal: 16, borderRadius: radii.md,
  },
  btnPrimary: { backgroundColor: colors.primary },
  btnSecondary: { backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border },
  btnSecondaryTxt: { color: colors.text, fontWeight: "800" },
  btnDisabled: { backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border },
  btnTxt: { color: colors.onPrimary, fontWeight: "900", fontSize: fonts.size.md },
  warnBox: {
    flexDirection: "row", alignItems: "center", gap: 8,
    backgroundColor: "#FFF9E6", borderRadius: radii.md, padding: space.sm, marginTop: space.md,
    borderWidth: 1, borderColor: "#F59E0B33",
  },
  warnTxt: { color: colors.text, flex: 1, fontSize: fonts.size.xs, lineHeight: 16 },
  footer: { padding: space.lg, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.bg },
});
