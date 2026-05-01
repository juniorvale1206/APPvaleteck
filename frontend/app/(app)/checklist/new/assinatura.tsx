import React, { useRef, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert, Image, Platform, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import Signature from "react-native-signature-canvas";
import { Btn, StepProgress } from "../../../../src/components";
import { useDraft } from "../../../../src/draft";
import { api, apiErrorMessage } from "../../../../src/api";
import { SLABadge } from "../../../../src/SLABadge";
import { colors, fonts, radii, space } from "../../../../src/theme";

export default function StepAssinatura() {
  const router = useRouter();
  const { draft, set } = useDraft();
  const ref = useRef<any>(null);
  const [preview, setPreview] = useState<string>(draft.signature_base64 || "");
  const [testing, setTesting] = useState(false);

  const handleOK = (sig: string) => { set({ signature_base64: sig }); setPreview(sig); };
  const onClear = () => { ref.current?.clearSignature?.(); set({ signature_base64: "" }); setPreview(""); };
  const onConfirm = () => ref.current?.readSignature?.();

  const testDevice = async () => {
    if (!/^\d{15}$/.test(draft.imei)) {
      Alert.alert("IMEI inválido", "Informe o IMEI completo (15 dígitos) na etapa de Instalação antes de testar.");
      return;
    }
    setTesting(true);
    try {
      const { data } = await api.post("/device/test", { imei: draft.imei });
      set({ device_online: data.online, device_tested_at: data.tested_at, device_test_message: data.message });
      Alert.alert(data.online ? "✅ Dispositivo online" : "❌ Dispositivo offline", data.message);
    } catch (e: any) {
      Alert.alert("Erro", apiErrorMessage(e));
    } finally { setTesting(false); }
  };

  const next = () => {
    if (!preview && !draft.signature_base64) {
      Alert.alert("Atenção", "Capture a assinatura do cliente antes de continuar.");
      return;
    }
    // Ao confirmar a assinatura, encerra o cronômetro de SLA
    if (!draft.execution_ended_at && draft.execution_started_at) {
      const start = new Date(draft.execution_started_at).getTime();
      const now = new Date();
      const sec = Math.floor((now.getTime() - start) / 1000);
      set({ execution_ended_at: now.toISOString(), execution_elapsed_sec: sec });
    }
    router.push("/(app)/checklist/new/revisao");
  };

  const webStyle = `.m-signature-pad{box-shadow:none;border:none;background:#fff}.m-signature-pad--body{border:none}.m-signature-pad--footer{display:none}body,html{background:#fff;height:100%;margin:0}canvas{background:#fff}`;
  const fullName = `${draft.nome} ${draft.sobrenome}`.trim();
  const online = draft.device_online;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="back-btn" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Assinatura</Text>
        <SLABadge compact />
      </View>
      <StepProgress step={5} total={6} />

      <View style={styles.content}>
        {/* Teste de comunicação */}
        <View style={[styles.testCard, online === true && styles.testCardOk, online === false && styles.testCardFail]} testID="device-test-card">
          <View style={{ flex: 1 }}>
            <Text style={styles.testTitle}>Teste de comunicação</Text>
            {online === null && <Text style={styles.testSub}>Verifique se o rastreador está respondendo antes da assinatura</Text>}
            {online === true && <Text style={[styles.testSub, { color: colors.success }]} testID="device-online-msg">✅ {draft.device_test_message}</Text>}
            {online === false && <Text style={[styles.testSub, { color: colors.danger }]} testID="device-offline-msg">❌ {draft.device_test_message}</Text>}
          </View>
          <TouchableOpacity testID="test-device-btn" onPress={testDevice} disabled={testing} style={[styles.testBtn, online === true && { backgroundColor: colors.success }]}>
            {testing ? <ActivityIndicator color={colors.onPrimary} /> : (
              <>
                <Ionicons name={online === true ? "checkmark" : "wifi"} size={18} color={colors.onPrimary} />
                <Text style={styles.testBtnTxt}>{online === true ? "Testar novamente" : online === false ? "Tentar novamente" : "Testar"}</Text>
              </>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.clientCard}>
          <Text style={styles.clientLabel}>Cliente</Text>
          <Text style={styles.clientName}>{fullName || "—"}</Text>
        </View>
        <Text style={styles.helper}>Solicite ao cliente que assine no quadro abaixo.</Text>

        <View style={styles.canvas}>
          {Platform.OS === "web" && preview ? (
            <Image source={{ uri: preview }} style={{ flex: 1, resizeMode: "contain" }} />
          ) : (
            <Signature
              ref={ref}
              onOK={handleOK}
              onEmpty={() => Alert.alert("Atenção", "A assinatura está vazia.")}
              descriptionText=""
              webStyle={webStyle}
              backgroundColor="#fff"
              penColor="#000"
              autoClear={false}
              imageType="image/png"
            />
          )}
        </View>

        <View style={styles.actions}>
          <Btn testID="sig-clear" title="Limpar" icon="trash-outline" variant="secondary" onPress={onClear} />
          <View style={{ width: 12 }} />
          <Btn testID="sig-confirm" title="Confirmar" icon="checkmark" onPress={onConfirm} />
        </View>

        {!!preview && (
          <View style={styles.confirmBox} testID="sig-preview">
            <Ionicons name="checkmark-circle" size={18} color={colors.success} />
            <Text style={{ color: colors.success, marginLeft: 6, fontWeight: "700" }}>Assinatura capturada</Text>
          </View>
        )}
      </View>

      <View style={styles.footer}>
        <Btn testID="step-next" title="Revisar" icon="arrow-forward" onPress={next} disabled={!preview} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingTop: space.sm, paddingBottom: space.xs },
  title: { color: colors.text, fontWeight: "800", fontSize: fonts.size.lg },
  content: { flex: 1, padding: space.lg },
  testCard: { flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: colors.surface, padding: space.md, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, marginBottom: space.md },
  testCardOk: { borderColor: colors.success, backgroundColor: "#143A22" },
  testCardFail: { borderColor: colors.danger, backgroundColor: "#3A1414" },
  testTitle: { color: colors.text, fontWeight: "800", fontSize: fonts.size.md },
  testSub: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 2 },
  testBtn: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: colors.primary, paddingHorizontal: 14, paddingVertical: 10, borderRadius: radii.md },
  testBtnTxt: { color: colors.onPrimary, fontWeight: "800", fontSize: fonts.size.sm },
  clientCard: { backgroundColor: colors.surface, borderRadius: radii.md, padding: space.md, borderWidth: 1, borderColor: colors.border, marginBottom: space.sm },
  clientLabel: { color: colors.textMuted, fontSize: fonts.size.xs, fontWeight: "700", letterSpacing: 1, textTransform: "uppercase" },
  clientName: { color: colors.text, fontSize: fonts.size.lg, fontWeight: "800", marginTop: 4 },
  helper: { color: colors.textMuted, fontSize: fonts.size.sm, marginBottom: space.sm },
  canvas: { flex: 1, borderRadius: radii.md, overflow: "hidden", backgroundColor: "#fff", borderWidth: 2, borderColor: colors.primary, minHeight: 200 },
  actions: { flexDirection: "row", marginTop: space.md },
  confirmBox: { flexDirection: "row", alignItems: "center", marginTop: space.sm, justifyContent: "center" },
  footer: { padding: space.lg, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.bg },
});
