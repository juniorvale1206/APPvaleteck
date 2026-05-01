import React, { useRef, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert, Image, Platform } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import Signature from "react-native-signature-canvas";
import { Btn, StepProgress } from "../../../../src/components";
import { useDraft } from "../../../../src/draft";
import { colors, fonts, radii, space } from "../../../../src/theme";

export default function StepAssinatura() {
  const router = useRouter();
  const { draft, set } = useDraft();
  const ref = useRef<any>(null);
  const [preview, setPreview] = useState<string>(draft.signature_base64 || "");

  const handleOK = (sig: string) => {
    set({ signature_base64: sig });
    setPreview(sig);
  };

  const onClear = () => {
    ref.current?.clearSignature?.();
    set({ signature_base64: "" });
    setPreview("");
  };

  const onConfirm = () => {
    ref.current?.readSignature?.();
    setTimeout(() => {
      // Wait for handleOK to set state
    }, 300);
  };

  const next = () => {
    if (!preview && !draft.signature_base64) {
      Alert.alert("Atenção", "Capture a assinatura do cliente antes de continuar.");
      return;
    }
    router.push("/(app)/checklist/new/revisao");
  };

  const webStyle = `
    .m-signature-pad { box-shadow: none; border: none; background:#fff; }
    .m-signature-pad--body { border: none; }
    .m-signature-pad--footer { display: none; }
    body,html { background-color: #fff; height: 100%; margin: 0; }
    canvas { background-color: #fff; }
  `;

  const fullName = `${draft.nome} ${draft.sobrenome}`.trim();

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="back-btn" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Assinatura</Text>
        <View style={{ width: 26 }} />
      </View>
      <StepProgress step={4} total={5} />

      <View style={styles.content}>
        <Text style={styles.section}>Assinatura do cliente</Text>
        <View style={styles.clientCard}>
          <Text style={styles.clientLabel}>Cliente</Text>
          <Text style={styles.clientName}>{fullName || "—"}</Text>
        </View>
        <Text style={styles.helper}>Solicite ao cliente que assine no quadro branco abaixo.</Text>

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
          <Btn testID="sig-confirm" title="Confirmar assinatura" icon="checkmark" onPress={onConfirm} />
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
  section: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "800", marginBottom: space.sm },
  clientCard: { backgroundColor: colors.surface, borderRadius: radii.md, padding: space.md, borderWidth: 1, borderColor: colors.border, marginBottom: space.sm },
  clientLabel: { color: colors.textMuted, fontSize: fonts.size.xs, fontWeight: "700", letterSpacing: 1, textTransform: "uppercase" },
  clientName: { color: colors.text, fontSize: fonts.size.lg, fontWeight: "800", marginTop: 4 },
  helper: { color: colors.textMuted, fontSize: fonts.size.sm, marginBottom: space.sm },
  canvas: { flex: 1, borderRadius: radii.md, overflow: "hidden", backgroundColor: "#fff", borderWidth: 2, borderColor: colors.primary, minHeight: 240 },
  actions: { flexDirection: "row", marginTop: space.md },
  confirmBox: { flexDirection: "row", alignItems: "center", marginTop: space.sm, justifyContent: "center" },
  footer: { padding: space.lg, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.bg },
});
