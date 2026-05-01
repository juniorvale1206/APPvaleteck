import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, Image } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api, apiErrorMessage, type Checklist } from "../../../src/api";
import { StatusBadge } from "../../../src/components";
import { colors, fonts, radii, space } from "../../../src/theme";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value || "—"}</Text>
    </View>
  );
}

export default function ChecklistDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [item, setItem] = useState<Checklist | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get<Checklist>(`/checklists/${id}`);
        setItem(data);
      } catch (e) { setError(apiErrorMessage(e)); }
    })();
  }, [id]);

  if (error) return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg, padding: 16 }}><Text style={{ color: colors.danger }}>{error}</Text></SafeAreaView>
  );
  if (!item) return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg, alignItems: "center", justifyContent: "center" }}><ActivityIndicator color={colors.primary} /></SafeAreaView>
  );

  const dt = new Date(item.created_at);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="detail-back" onPress={() => router.replace("/(app)/(tabs)/agenda")}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Detalhes</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: space.lg, paddingBottom: 60 }}>
        <View style={styles.topCard}>
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <Text style={styles.numero}>{item.numero}</Text>
            <StatusBadge value={item.status} />
          </View>
          <Text style={styles.client}>{item.nome} {item.sobrenome}</Text>
          <View style={styles.plate}><Text style={styles.plateTxt}>{item.placa}</Text></View>
          <Text style={styles.timestamp}>{dt.toLocaleString("pt-BR")}</Text>
        </View>

        {item.alerts?.length > 0 && (
          <View style={styles.alertCard} testID="alerts">
            {item.alerts.map((a, i) => (
              <View key={i} style={styles.alertRow}>
                <Ionicons name="warning" size={18} color={colors.warning} />
                <Text style={styles.alertTxt}>{a}</Text>
              </View>
            ))}
          </View>
        )}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Veículo</Text>
          <Row label="Tipo" value={item.vehicle_type === "moto" ? "Moto" : item.vehicle_type === "carro" ? "Carro" : ""} />
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Cliente</Text>
          <Row label="Nome" value={`${item.nome} ${item.sobrenome}`} />
          <Row label="Telefone" value={item.telefone || ""} />
          <Row label="Observações" value={item.obs_iniciais || ""} />
          <Row label="Problemas relatados" value={[...(item.problems_client || []), item.problems_client_other || ""].filter(Boolean).join(", ")} />
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Instalação</Text>
          <Row label="Empresa" value={item.empresa} />
          <Row label="Equipamento" value={item.equipamento} />
          <Row label="Tipo" value={item.tipo_atendimento || ""} />
          <Row label="IMEI" value={item.imei || ""} />
          <Row label="ICCID" value={item.iccid || ""} />
          <Row label="Acessórios" value={item.acessorios?.join(", ") || ""} />
          <Row label="Bateria" value={[item.battery_state || "", item.battery_voltage ? `${item.battery_voltage}V` : ""].filter(Boolean).join(" • ")} />
          <Row label="Problemas técnico" value={[...(item.problems_technician || []), item.problems_technician_other || ""].filter(Boolean).join(", ")} />
          <Row label="Obs. técnicas" value={item.obs_tecnicas || ""} />
          <Row label="Dispositivo" value={item.device_online === true ? "✅ Online" : item.device_online === false ? "❌ Offline" : "Não testado"} />
          {!!item.device_test_message && <Row label="Detalhe teste" value={item.device_test_message} />}
          {!!item.execution_elapsed_sec && <Row label="Tempo execução" value={`${Math.floor(item.execution_elapsed_sec / 60)} min`} />}
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Localização</Text>
          <Row label="Capturada" value={item.location_available ? "Sim" : "Não"} />
          {item.location && <Row label="Coordenadas" value={`${item.location.lat.toFixed(5)}, ${item.location.lng.toFixed(5)}`} />}
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Fotos ({item.photos.length})</Text>
          <View style={styles.grid}>
            {item.photos.map((p, i) => (
              <Image key={i} source={{ uri: p.base64 }} style={styles.thumb} />
            ))}
          </View>
        </View>

        {!!item.signature_base64 && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Assinatura</Text>
            <View style={styles.sigBox}>
              <Image source={{ uri: item.signature_base64 }} style={{ flex: 1 }} resizeMode="contain" />
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingVertical: space.sm },
  title: { color: colors.text, fontWeight: "800", fontSize: fonts.size.lg },
  topCard: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: space.lg, borderWidth: 1, borderColor: colors.border, marginBottom: space.md },
  numero: { color: colors.primary, fontWeight: "800", fontSize: fonts.size.md },
  client: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "800", marginTop: 8 },
  plate: { backgroundColor: "#0a0a0a", borderWidth: 1, borderColor: colors.primary, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 6, alignSelf: "flex-start", marginTop: 8 },
  plateTxt: { color: colors.primary, fontWeight: "900", letterSpacing: 1.5, fontSize: fonts.size.md },
  timestamp: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 8 },
  alertCard: { backgroundColor: "#3A2A0A", borderRadius: radii.md, padding: space.md, borderWidth: 1, borderColor: "#5A4012", marginBottom: space.md },
  alertRow: { flexDirection: "row", alignItems: "flex-start", gap: 8, paddingVertical: 4 },
  alertTxt: { color: colors.warning, flex: 1, fontSize: fonts.size.sm, fontWeight: "600" },
  card: { backgroundColor: colors.surface, borderRadius: radii.md, padding: space.md, borderWidth: 1, borderColor: colors.border, marginBottom: space.md },
  cardTitle: { color: colors.text, fontWeight: "800", fontSize: fonts.size.md, marginBottom: space.sm },
  row: { flexDirection: "row", paddingVertical: 6 },
  rowLabel: { color: colors.textMuted, width: 110, fontSize: fonts.size.sm },
  rowValue: { color: colors.text, flex: 1, fontSize: fonts.size.sm, fontWeight: "600" },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  thumb: { width: "31%", aspectRatio: 1, borderRadius: radii.sm, backgroundColor: colors.surfaceAlt },
  sigBox: { height: 160, backgroundColor: "#fff", borderRadius: radii.md, padding: 8 },
});
