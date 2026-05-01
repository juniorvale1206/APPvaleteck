import React, { useState, useRef } from "react";
import { View, Text, StyleSheet, Modal, TouchableOpacity, Platform, ActivityIndicator } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { Ionicons } from "@expo/vector-icons";
import { colors, fonts, radii, space } from "./theme";

type Props = {
  visible: boolean;
  onClose: () => void;
  onScan: (value: string) => void;
  title?: string;
  hint?: string;
  validate?: (v: string) => boolean;
};

export default function BarcodeScanner({ visible, onClose, onScan, title = "Scanner", hint, validate }: Props) {
  const [perm, requestPerm] = useCameraPermissions();
  const [scanned, setScanned] = useState(false);
  const lastRef = useRef<string>("");

  React.useEffect(() => {
    if (visible) { setScanned(false); lastRef.current = ""; }
  }, [visible]);

  React.useEffect(() => {
    if (visible && perm && !perm.granted && perm.canAskAgain) requestPerm();
  }, [visible, perm, requestPerm]);

  const handleBarcode = ({ data }: { data: string }) => {
    if (scanned) return;
    const clean = (data || "").trim();
    if (lastRef.current === clean) return;
    lastRef.current = clean;
    if (validate && !validate(clean)) return;
    setScanned(true);
    onScan(clean);
  };

  const webMsg = Platform.OS === "web" ? "O scanner de código é otimizado no celular. Na web, digite o número manualmente." : null;

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.title}>{title}</Text>
            <TouchableOpacity testID="scanner-close" onPress={onClose}><Ionicons name="close" size={28} color={colors.text} /></TouchableOpacity>
          </View>
          {!!hint && <Text style={styles.hint}>{hint}</Text>}

          <View style={styles.camWrap}>
            {Platform.OS === "web" || !perm?.granted ? (
              <View style={styles.placeholder}>
                <Ionicons name="qr-code-outline" size={56} color={colors.textDim} />
                <Text style={styles.placeholderTxt}>
                  {webMsg ||
                    (!perm
                      ? "Solicitando permissão..."
                      : !perm.granted
                      ? "Câmera não autorizada — digite manualmente"
                      : "Aguardando câmera...")}
                </Text>
                {!perm?.granted && perm?.canAskAgain && (
                  <TouchableOpacity onPress={requestPerm} style={styles.permBtn}>
                    <Text style={styles.permBtnTxt}>Permitir câmera</Text>
                  </TouchableOpacity>
                )}
              </View>
            ) : (
              <>
                <CameraView
                  style={styles.camera}
                  barcodeScannerSettings={{ barcodeTypes: ["code128", "code39", "ean13", "ean8", "qr", "pdf417", "upc_a", "upc_e", "itf14"] }}
                  onBarcodeScanned={scanned ? undefined : handleBarcode}
                  facing="back"
                />
                <View style={styles.overlay}>
                  <View style={styles.scanFrame} />
                  {scanned && <ActivityIndicator size="large" color={colors.primary} style={{ position: "absolute", alignSelf: "center" }} />}
                </View>
              </>
            )}
          </View>

          <Text style={styles.footer}>Aponte a câmera para o código de barras ou QR Code</Text>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.9)" },
  sheet: { flex: 1, backgroundColor: colors.bg, paddingTop: 48, paddingHorizontal: space.lg },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: space.md },
  title: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "800" },
  hint: { color: colors.textMuted, fontSize: fonts.size.sm, marginBottom: space.md },
  camWrap: { flex: 1, borderRadius: radii.lg, overflow: "hidden", backgroundColor: "#111", borderWidth: 2, borderColor: colors.primary, marginBottom: space.md },
  camera: { flex: 1 },
  overlay: { ...StyleSheet.absoluteFillObject, alignItems: "center", justifyContent: "center" },
  scanFrame: { width: "75%", height: 180, borderWidth: 3, borderColor: colors.primary, borderRadius: radii.md, backgroundColor: "transparent" },
  placeholder: { flex: 1, alignItems: "center", justifyContent: "center", padding: space.xl },
  placeholderTxt: { color: colors.textMuted, fontSize: fonts.size.md, textAlign: "center", marginTop: space.md },
  permBtn: { marginTop: 16, backgroundColor: colors.primary, paddingHorizontal: 18, paddingVertical: 10, borderRadius: radii.md },
  permBtnTxt: { color: colors.onPrimary, fontWeight: "800" },
  footer: { color: colors.textDim, textAlign: "center", fontSize: fonts.size.xs, paddingBottom: space.lg },
});
