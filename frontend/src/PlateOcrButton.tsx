import React, { useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert, ActivityIndicator } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import * as ImageManipulator from "expo-image-manipulator";
import { api, apiErrorMessage } from "./api";
import { colors, fonts, radii } from "./theme";

type Props = {
  onDetected: (plate: string, confidence: number) => void;
  testID?: string;
  label?: string;
};

/**
 * Botão que abre câmera/galeria, comprime e envia para /api/ocr/plate,
 * retornando a placa detectada via callback.
 */
export default function PlateOcrButton({ onDetected, testID = "ocr-plate-btn", label = "Escanear placa" }: Props) {
  const [busy, setBusy] = useState(false);

  const runOcr = async (fromCamera: boolean) => {
    const perm = fromCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) { Alert.alert("Permissão", "Permissão negada"); return; }
    setBusy(true);
    try {
      const r = fromCamera
        ? await ImagePicker.launchCameraAsync({ quality: 0.6, mediaTypes: ImagePicker.MediaTypeOptions.Images })
        : await ImagePicker.launchImageLibraryAsync({ quality: 0.6, mediaTypes: ImagePicker.MediaTypeOptions.Images });
      if (r.canceled || !r.assets[0]) { setBusy(false); return; }
      const m = await ImageManipulator.manipulateAsync(
        r.assets[0].uri,
        [{ resize: { width: 1200 } }],
        { compress: 0.7, format: ImageManipulator.SaveFormat.JPEG, base64: true }
      );
      if (!m.base64) throw new Error("Falha ao processar imagem");
      const b64 = `data:image/jpeg;base64,${m.base64}`;
      const { data } = await api.post("/ocr/plate", { base64: b64 });
      if (data.plate) {
        onDetected(data.plate, data.confidence);
        Alert.alert(
          "✅ Placa detectada",
          `${data.plate} (confiança ${Math.round((data.confidence || 0) * 100)}%)`,
          [{ text: "OK" }]
        );
      } else {
        Alert.alert("Não detectado", "Não foi possível ler a placa. Tente com iluminação melhor ou digite manualmente.");
      }
    } catch (e: any) {
      Alert.alert("Erro", apiErrorMessage(e));
    } finally { setBusy(false); }
  };

  const onPress = () => {
    Alert.alert(label, "Escolha a fonte da imagem", [
      { text: "Câmera", onPress: () => runOcr(true) },
      { text: "Galeria", onPress: () => runOcr(false) },
      { text: "Cancelar", style: "cancel" },
    ]);
  };

  return (
    <TouchableOpacity testID={testID} onPress={onPress} disabled={busy} style={styles.btn} activeOpacity={0.85}>
      {busy ? <ActivityIndicator color={colors.onPrimary} /> : <>
        <Ionicons name="scan" size={18} color={colors.onPrimary} />
        <Text style={styles.txt}>{label}</Text>
      </>}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  btn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingVertical: 12, paddingHorizontal: 16, backgroundColor: colors.brandBlack, borderRadius: radii.md, minHeight: 48 },
  txt: { color: colors.primary, fontWeight: "900", fontSize: fonts.size.sm },
});
