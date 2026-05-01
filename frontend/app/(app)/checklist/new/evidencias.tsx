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
import { SLABadge } from "../../../../src/SLABadge";
import { colors, fonts, radii, space } from "../../../../src/theme";

type PhotoSpec = { id: string; label: string; hint: string; required: boolean };
type GroupSpec = { step: number; title: string; color: string; icon: keyof typeof Ionicons.glyphMap; photos: PhotoSpec[] };

const GROUPS: GroupSpec[] = [
  {
    step: 1, title: "Pré-instalação", color: "#3B82F6", icon: "warning-outline",
    photos: [
      { id: "avaria-frontal", label: "Avaria frontal", hint: "Vista frontal do veículo com possíveis avarias", required: true },
      { id: "avaria-traseira", label: "Avaria traseira", hint: "Vista traseira do veículo com possíveis avarias", required: true },
    ],
  },
  {
    step: 2, title: "Equipamento", color: "#F59E0B", icon: "hardware-chip-outline",
    photos: [
      { id: "equip-placa", label: "Equipamento + placa/chassi", hint: "Equipamento e placa/chassi no mesmo enquadramento", required: true },
      { id: "imei-placa", label: "IMEI + placa/chassi", hint: "Etiqueta do IMEI visível junto à placa/chassi", required: true },
    ],
  },
  {
    step: 3, title: "Camuflagem", color: "#A855F7", icon: "eye-off-outline",
    photos: [
      { id: "fiacao", label: "Camuflagem da fiação", hint: "Fiação escondida/organizada", required: true },
      { id: "painel", label: "Painel fechado", hint: "Painel reinstalado após a instalação", required: true },
    ],
  },
  {
    step: 4, title: "Finalização", color: "#22C55E", icon: "checkmark-done-outline",
    photos: [
      { id: "panoramica", label: "Panorâmica final", hint: "Vista geral do veículo após serviço", required: true },
      { id: "odometro", label: "Odômetro", hint: "Leitura do painel / odômetro no momento da entrega", required: true },
    ],
  },
];

export default function StepEvidencias() {
  const router = useRouter();
  const { draft, set } = useDraft();
  const [busy, setBusy] = useState(false);
  const [locBusy, setLocBusy] = useState(false);

  const photoFor = (step: number, photoId: string) =>
    draft.photos.find((p) => p.workflow_step === step && p.photo_id === photoId);

  const capture = async (step: number, photoId: string, label: string, fromCamera: boolean) => {
    const perm = fromCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) { Alert.alert("Permissão", "Permissão negada"); return; }
    setBusy(true);
    try {
      const r = fromCamera
        ? await ImagePicker.launchCameraAsync({ quality: 0.6, mediaTypes: ImagePicker.MediaTypeOptions.Images })
        : await ImagePicker.launchImageLibraryAsync({ quality: 0.6, mediaTypes: ImagePicker.MediaTypeOptions.Images });
      if (r.canceled || !r.assets[0]) return;
      const m = await ImageManipulator.manipulateAsync(r.assets[0].uri, [{ resize: { width: 1200 } }], { compress: 0.6, format: ImageManipulator.SaveFormat.JPEG, base64: true });
      if (!m.base64) throw new Error("Falha ao processar imagem");
      const base64 = `data:image/jpeg;base64,${m.base64}`;
      const filtered = draft.photos.filter((p) => !(p.workflow_step === step && p.photo_id === photoId));
      set({ photos: [...filtered, { base64, label, workflow_step: step, photo_id: photoId }] });
    } catch (e: any) { Alert.alert("Erro", e?.message || "Falha"); }
    finally { setBusy(false); }
  };

  const addPhoto = (step: number, photoId: string, label: string) => {
    Alert.alert(label, "Escolha uma fonte", [
      { text: "Câmera", onPress: () => capture(step, photoId, label, true) },
      { text: "Galeria", onPress: () => capture(step, photoId, label, false) },
      { text: "Cancelar", style: "cancel" },
    ]);
  };

  const removePhoto = (step: number, photoId: string) => {
    set({ photos: draft.photos.filter((p) => !(p.workflow_step === step && p.photo_id === photoId)) });
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

  const allRequiredCaptured = GROUPS.every((g) => g.photos.filter((p) => p.required).every((p) => photoFor(g.step, p.id)));
  const capturedCount = draft.photos.length;
  const requiredCount = GROUPS.flatMap((g) => g.photos.filter((p) => p.required)).length;

  const next = () => {
    if (!allRequiredCaptured) {
      Alert.alert("Fotos faltando", `Capture todas as ${requiredCount} fotos obrigatórias antes de continuar.`);
      return;
    }
    router.push("/(app)/checklist/new/assinatura");
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="back-btn" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Evidências</Text>
        <SLABadge compact />
      </View>
      <StepProgress step={4} total={6} />

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.summary}>
          <Ionicons name="camera" size={22} color={colors.primary} />
          <Text style={styles.summaryTxt}>
            {capturedCount} / {requiredCount} fotos obrigatórias capturadas
          </Text>
          {allRequiredCaptured && <Ionicons name="checkmark-circle" size={20} color={colors.success} />}
        </View>

        {GROUPS.map((g) => {
          const done = g.photos.filter((p) => p.required).every((p) => photoFor(g.step, p.id));
          return (
            <View key={g.step} style={styles.group} testID={`group-${g.step}`}>
              <View style={styles.groupHeader}>
                <View style={[styles.groupIcon, { backgroundColor: g.color + "33", borderColor: g.color }]}>
                  <Ionicons name={g.icon} size={18} color={g.color} />
                </View>
                <Text style={styles.groupTitle}>Grupo {g.step} — {g.title}</Text>
                {done && <Ionicons name="checkmark-circle" size={20} color={colors.success} />}
              </View>
              {g.photos.map((ph) => {
                const captured = photoFor(g.step, ph.id);
                return (
                  <View key={ph.id} style={styles.photoRow} testID={`photo-${g.step}-${ph.id}`}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.photoLabel}>
                        {ph.label}{ph.required && <Text style={{ color: colors.primary }}> *</Text>}
                      </Text>
                      <Text style={styles.photoHint}>{ph.hint}</Text>
                    </View>
                    {captured ? (
                      <View style={styles.photoPreview}>
                        <Image source={{ uri: captured.base64 }} style={styles.thumb} />
                        <TouchableOpacity onPress={() => removePhoto(g.step, ph.id)} style={styles.removeBtn} testID={`remove-${g.step}-${ph.id}`}>
                          <Ionicons name="close" size={14} color="#fff" />
                        </TouchableOpacity>
                      </View>
                    ) : (
                      <TouchableOpacity onPress={() => addPhoto(g.step, ph.id, ph.label)} style={styles.addPhotoBtn} testID={`add-${g.step}-${ph.id}`}>
                        <Ionicons name="camera" size={20} color={colors.onPrimary} />
                      </TouchableOpacity>
                    )}
                  </View>
                );
              })}
            </View>
          );
        })}

        {busy && <ActivityIndicator color={colors.primary} style={{ marginVertical: 12 }} />}

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
        <Btn testID="step-next" title={allRequiredCaptured ? "Continuar" : `Falta ${requiredCount - capturedCount} foto(s)`} icon="arrow-forward" onPress={next} disabled={!allRequiredCaptured} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingTop: space.sm, paddingBottom: space.xs },
  title: { color: colors.text, fontWeight: "800", fontSize: fonts.size.lg },
  content: { padding: space.lg, paddingBottom: 100 },
  summary: { flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: colors.surface, padding: space.md, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, marginBottom: space.md },
  summaryTxt: { color: colors.text, fontSize: fonts.size.md, fontWeight: "700", flex: 1 },
  group: { backgroundColor: colors.surface, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, padding: space.md, marginBottom: space.md },
  groupHeader: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: space.sm },
  groupIcon: { width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center", borderWidth: 1 },
  groupTitle: { color: colors.text, fontWeight: "800", fontSize: fonts.size.md, flex: 1 },
  photoRow: { flexDirection: "row", alignItems: "center", paddingVertical: 10, gap: 12, borderTopWidth: 1, borderTopColor: colors.border },
  photoLabel: { color: colors.text, fontSize: fonts.size.sm, fontWeight: "700" },
  photoHint: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 2 },
  addPhotoBtn: { width: 52, height: 52, borderRadius: radii.md, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  photoPreview: { position: "relative" },
  thumb: { width: 52, height: 52, borderRadius: radii.md, backgroundColor: colors.surfaceAlt },
  removeBtn: { position: "absolute", top: -6, right: -6, width: 22, height: 22, borderRadius: 11, backgroundColor: colors.danger, alignItems: "center", justifyContent: "center", borderWidth: 2, borderColor: colors.bg },
  geoCard: { marginTop: space.sm, backgroundColor: colors.surface, borderRadius: radii.md, padding: space.md, borderWidth: 1, borderColor: colors.border, flexDirection: "row", alignItems: "center" },
  geoTitle: { color: colors.text, fontSize: fonts.size.md, fontWeight: "700" },
  geoMsg: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 2 },
  geoBtn: { width: 48, height: 48, borderRadius: 24, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  footer: { padding: space.lg, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.bg },
});
