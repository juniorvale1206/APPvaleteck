import React, { useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Image, Alert, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import * as ImageManipulator from "expo-image-manipulator";
import * as Location from "expo-location";
import { Btn, StepProgress } from "../../../../src/components";
import { useDraft } from "../../../../src/draft";
import { colors, fonts, radii, space } from "../../../../src/theme";

export default function StepEvidencias() {
  const router = useRouter();
  const { draft, set } = useDraft();
  const [busy, setBusy] = useState(false);
  const [locBusy, setLocBusy] = useState(false);

  const compressAndAdd = async (uri: string, label: string) => {
    const manipulated = await ImageManipulator.manipulateAsync(
      uri,
      [{ resize: { width: 1200 } }],
      { compress: 0.6, format: ImageManipulator.SaveFormat.JPEG, base64: true }
    );
    if (!manipulated.base64) throw new Error("Falha ao processar imagem");
    set({ photos: [...draft.photos, { label, base64: `data:image/jpeg;base64,${manipulated.base64}` }] });
  };

  const takePhoto = async (label: string) => {
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) { Alert.alert("Permissão", "Permissão de câmera negada"); return; }
    setBusy(true);
    try {
      const r = await ImagePicker.launchCameraAsync({ quality: 0.6, mediaTypes: ImagePicker.MediaTypeOptions.Images, base64: false });
      if (!r.canceled && r.assets[0]) await compressAndAdd(r.assets[0].uri, label);
    } catch (e: any) { Alert.alert("Erro", e?.message || "Falha"); }
    finally { setBusy(false); }
  };

  const pickPhoto = async (label: string) => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) { Alert.alert("Permissão", "Permissão da galeria negada"); return; }
    setBusy(true);
    try {
      const r = await ImagePicker.launchImageLibraryAsync({ quality: 0.6, mediaTypes: ImagePicker.MediaTypeOptions.Images, base64: false });
      if (!r.canceled && r.assets[0]) await compressAndAdd(r.assets[0].uri, label);
    } catch (e: any) { Alert.alert("Erro", e?.message || "Falha"); }
    finally { setBusy(false); }
  };

  const addPhoto = (label: string) => {
    Alert.alert("Adicionar foto", label, [
      { text: "Câmera", onPress: () => takePhoto(label) },
      { text: "Galeria", onPress: () => pickPhoto(label) },
      { text: "Cancelar", style: "cancel" },
    ]);
  };

  const removePhoto = (idx: number) => {
    set({ photos: draft.photos.filter((_, i) => i !== idx) });
  };

  const captureLocation = async () => {
    setLocBusy(true);
    try {
      const perm = await Location.requestForegroundPermissionsAsync();
      if (!perm.granted) {
        set({ location: null, location_available: false });
        Alert.alert("Localização", "Permissão negada — atendimento será registrado sem GPS.");
        return;
      }
      const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      set({ location: { lat: pos.coords.latitude, lng: pos.coords.longitude }, location_available: true });
    } catch {
      set({ location: null, location_available: false });
      Alert.alert("Localização", "Não foi possível obter a localização.");
    } finally { setLocBusy(false); }
  };

  const next = () => {
    if (draft.photos.length < 2) { Alert.alert("Atenção", "É obrigatório anexar no mínimo 2 fotos."); return; }
    router.push("/(app)/checklist/new/assinatura");
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="back-btn" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Evidências</Text>
        <View style={{ width: 26 }} />
      </View>
      <StepProgress step={3} total={5} />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.section}>Fotos do atendimento</Text>
        <Text style={styles.helper}>Mínimo 2 fotos obrigatórias: placa/veículo e equipamento.</Text>

        <View style={styles.actions}>
          <Btn testID="add-photo-veiculo" title="Foto da placa/veículo" icon="car-sport-outline" variant="secondary" onPress={() => addPhoto("Veículo / Placa")} />
          <View style={{ height: 12 }} />
          <Btn testID="add-photo-equipamento" title="Foto do equipamento" icon="hardware-chip-outline" variant="secondary" onPress={() => addPhoto("Equipamento")} />
          <View style={{ height: 12 }} />
          <Btn testID="add-photo-extra" title="Adicionar mais foto" icon="add" variant="ghost" onPress={() => addPhoto("Adicional")} />
        </View>

        {busy && <ActivityIndicator style={{ marginVertical: 12 }} color={colors.primary} />}

        <View style={styles.grid}>
          {draft.photos.map((p, i) => (
            <View key={i} style={styles.thumbWrap} testID={`photo-${i}`}>
              <Image source={{ uri: p.base64 }} style={styles.thumb} />
              <TouchableOpacity onPress={() => removePhoto(i)} style={styles.removeBtn} testID={`remove-photo-${i}`}>
                <Ionicons name="close" size={16} color="#fff" />
              </TouchableOpacity>
              {!!p.label && <Text style={styles.thumbLabel} numberOfLines={1}>{p.label}</Text>}
            </View>
          ))}
        </View>

        <View style={styles.geoCard}>
          <View style={{ flex: 1 }}>
            <Text style={styles.geoTitle}>Geolocalização</Text>
            <Text style={styles.geoMsg}>
              {draft.location_available && draft.location
                ? `Lat ${draft.location.lat.toFixed(5)} • Lng ${draft.location.lng.toFixed(5)}`
                : "Não capturada (opcional)"}
            </Text>
          </View>
          <TouchableOpacity onPress={captureLocation} style={styles.geoBtn} testID="capture-location">
            {locBusy ? <ActivityIndicator color={colors.onPrimary} /> : <Ionicons name="location" size={20} color={colors.onPrimary} />}
          </TouchableOpacity>
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <Btn testID="step-next" title="Continuar" icon="arrow-forward" onPress={next} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingTop: space.sm, paddingBottom: space.xs },
  title: { color: colors.text, fontWeight: "800", fontSize: fonts.size.lg },
  content: { padding: space.lg, paddingBottom: 100 },
  section: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "800" },
  helper: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 4, marginBottom: space.md },
  actions: { marginBottom: space.lg },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  thumbWrap: { width: "31%", aspectRatio: 1, borderRadius: radii.md, overflow: "hidden", backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, position: "relative" },
  thumb: { width: "100%", height: "100%" },
  removeBtn: { position: "absolute", top: 4, right: 4, backgroundColor: "rgba(0,0,0,0.7)", borderRadius: 12, padding: 4 },
  thumbLabel: { position: "absolute", bottom: 0, left: 0, right: 0, backgroundColor: "rgba(0,0,0,0.65)", color: "#fff", fontSize: 10, textAlign: "center", paddingVertical: 2 },
  geoCard: { marginTop: space.lg, backgroundColor: colors.surface, borderRadius: radii.md, padding: space.md, borderWidth: 1, borderColor: colors.border, flexDirection: "row", alignItems: "center" },
  geoTitle: { color: colors.text, fontSize: fonts.size.md, fontWeight: "700" },
  geoMsg: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 2 },
  geoBtn: { width: 48, height: 48, borderRadius: 24, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  footer: { padding: space.lg, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.bg },
});
