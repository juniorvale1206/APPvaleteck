import React, { useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { Btn, StepProgress } from "../../../../src/components";
import { useDraft } from "../../../../src/draft";
import { api, apiErrorMessage } from "../../../../src/api";
import { SLABadge } from "../../../../src/SLABadge";
import { formatSLA } from "../../../../src/slatimer";
import { useSync } from "../../../../src/sync";
import { colors, fonts, radii, space } from "../../../../src/theme";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value || "—"}</Text>
    </View>
  );
}

export default function Revisao() {
  const router = useRouter();
  const { draft, reset } = useDraft();
  const { online, enqueue, syncNow } = useSync();
  const [loading, setLoading] = useState(false);

  const submit = async (status: "rascunho" | "enviado") => {
    setLoading(true);
    try {
      const payload: any = {
        ...draft,
        battery_voltage: draft.battery_voltage ? parseFloat(draft.battery_voltage.replace(",", ".")) : null,
        vehicle_odometer: draft.vehicle_odometer ? parseInt(draft.vehicle_odometer.replace(/\D/g, "") || "0", 10) : null,
        status,
      };
      if (!online && status === "enviado") {
        // offline: enqueue for later sync
        const item = await enqueue(payload);
        reset();
        Alert.alert(
          "📡 Salvo offline",
          `Sem internet no momento.\n\nChecklist ${item.numero_local} foi salvo no dispositivo e será enviado automaticamente quando a conexão voltar.`,
          [{ text: "OK", onPress: () => router.replace("/(app)/(tabs)/agenda") }]
        );
        return;
      }
      try {
        const { data } = await api.post("/checklists", payload);
        reset();
        Alert.alert(
          status === "enviado" ? "Checklist enviado!" : "Rascunho salvo",
          status === "enviado" ? `Número: ${data.numero}` : "Você pode continuar depois.",
          [{ text: "OK", onPress: () => router.replace({ pathname: "/(app)/checklist/[id]", params: { id: data.id } }) }]
        );
      } catch (e: any) {
        // Network/server error during online submit → queue as fallback if it was send
        if (status === "enviado") {
          const item = await enqueue(payload);
          reset();
          Alert.alert(
            "📡 Salvo na fila",
            `Servidor indisponível. Checklist ${item.numero_local} ficará em fila e será reenviado automaticamente.`,
            [{ text: "OK", onPress: () => router.replace("/(app)/(tabs)/agenda") }]
          );
        } else {
          throw e;
        }
      }
    } catch (e: any) {
      Alert.alert("Erro", apiErrorMessage(e));
    } finally { setLoading(false); }
  };

  const onSend = () => {
    Alert.alert("Enviar checklist", "Confirma o envio? Após o envio não será possível editar.", [
      { text: "Cancelar", style: "cancel" },
      { text: "Enviar", onPress: () => submit("enviado") },
    ]);
  };

  const editStep = (path: string) => router.push(path as any);
  const voltage = draft.battery_voltage ? `${draft.battery_voltage}V` : "";
  const problemsClient = [...draft.problems_client, draft.problems_client_other].filter(Boolean).join(", ");
  const problemsTech = [...draft.problems_technician, draft.problems_technician_other].filter(Boolean).join(", ");

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="back-btn" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Revisão</Text>
        <SLABadge compact />
      </View>
      <StepProgress step={6} total={6} />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.section}>Confira antes de enviar</Text>

        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.cardTitle}>Veículo</Text>
            <TouchableOpacity onPress={() => editStep("/(app)/checklist/new")}><Text style={styles.editLink}>Editar</Text></TouchableOpacity>
          </View>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
            {draft.vehicle_type === "moto" ? (
              <MaterialCommunityIcons name="motorbike" size={32} color={colors.primary} />
            ) : (
              <Ionicons name="car-sport" size={32} color={colors.primary} />
            )}
            <Text style={styles.vehicleLabel}>{draft.vehicle_type === "moto" ? "Moto" : draft.vehicle_type === "carro" ? "Carro" : "—"}</Text>
          </View>
        </View>

        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.cardTitle}>Cliente</Text>
            <TouchableOpacity onPress={() => editStep("/(app)/checklist/new/cliente")}><Text style={styles.editLink}>Editar</Text></TouchableOpacity>
          </View>
          <Row label="Nome" value={`${draft.nome} ${draft.sobrenome}`.trim()} />
          <Row label="Placa" value={draft.placa} />
          <Row label="Telefone" value={draft.telefone} />
          <Row label="Obs. cliente" value={draft.obs_iniciais} />
          <Row label="Problemas" value={problemsClient} />
        </View>

        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.cardTitle}>Instalação</Text>
            <TouchableOpacity onPress={() => editStep("/(app)/checklist/new/instalacao")}><Text style={styles.editLink}>Editar</Text></TouchableOpacity>
          </View>
          <Row label="Empresa" value={draft.empresa} />
          <Row label="Equipamento" value={draft.equipamento} />
          <Row label="Tipo" value={draft.tipo_atendimento} />
          {draft.removed_equipments && draft.removed_equipments.length > 0 && (
            <Row
              label={`Retirados (${draft.removed_equipments.length})`}
              value={draft.removed_equipments
                .map((e) => `${e.tipo}${e.modelo ? ` ${e.modelo}` : ""}${e.imei ? ` IMEI ${e.imei}` : ""}${e.estado ? ` (${e.estado})` : ""}`)
                .join(" • ")}
            />
          )}
          <Row label="IMEI" value={draft.imei} />
          <Row label="ICCID" value={draft.iccid} />
          <Row label="Acessórios" value={draft.acessorios.join(", ") || "Nenhum"} />
          <Row label="Bateria" value={[draft.battery_state, voltage].filter(Boolean).join(" • ")} />
          <Row label="Problemas técnico" value={problemsTech} />
          <Row label="Obs. técnicas" value={draft.obs_tecnicas} />
        </View>

        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.cardTitle}>Teste de comunicação</Text>
            <TouchableOpacity onPress={() => editStep("/(app)/checklist/new/assinatura")}><Text style={styles.editLink}>Editar</Text></TouchableOpacity>
          </View>
          <Row label="Status" value={draft.device_online === true ? "✅ Online" : draft.device_online === false ? "❌ Offline" : "Não testado"} />
          {!!draft.device_test_message && <Row label="Mensagem" value={draft.device_test_message} />}
          {!!draft.execution_elapsed_sec && <Row label="Tempo execução" value={formatSLA(draft.execution_elapsed_sec)} />}
        </View>

        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.cardTitle}>Evidências</Text>
            <TouchableOpacity onPress={() => editStep("/(app)/checklist/new/evidencias")}><Text style={styles.editLink}>Editar</Text></TouchableOpacity>
          </View>
          <Row label="Fotos" value={`${draft.photos.length} foto(s)`} />
          <Row label="Localização" value={draft.location_available && draft.location ? `${draft.location.lat.toFixed(4)}, ${draft.location.lng.toFixed(4)}` : "Não capturada"} />
        </View>

        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.cardTitle}>Assinatura</Text>
            <TouchableOpacity onPress={() => editStep("/(app)/checklist/new/assinatura")}><Text style={styles.editLink}>Editar</Text></TouchableOpacity>
          </View>
          <Row label="Status" value={draft.signature_base64 ? "Capturada" : "Pendente"} />
        </View>

        <Text style={styles.timestamp}>Data/hora: {new Date().toLocaleString("pt-BR")}</Text>
      </ScrollView>

      <View style={styles.footer}>
        <Btn testID="save-draft" title="Salvar rascunho" icon="save-outline" variant="secondary" onPress={() => submit("rascunho")} loading={loading} />
        <View style={{ height: 10 }} />
        <Btn testID="send-checklist" title="Enviar checklist" icon="cloud-upload-outline" onPress={onSend} loading={loading} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingTop: space.sm, paddingBottom: space.xs },
  title: { color: colors.text, fontWeight: "800", fontSize: fonts.size.lg },
  content: { padding: space.lg, paddingBottom: 200 },
  section: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "800", marginBottom: space.md },
  card: { backgroundColor: colors.surface, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, padding: space.md, marginBottom: space.md },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: space.sm },
  cardTitle: { color: colors.text, fontWeight: "800", fontSize: fonts.size.md },
  editLink: { color: colors.primary, fontWeight: "700" },
  vehicleLabel: { color: colors.text, fontSize: fonts.size.lg, fontWeight: "800" },
  row: { flexDirection: "row", paddingVertical: 6 },
  rowLabel: { color: colors.textMuted, width: 120, fontSize: fonts.size.sm },
  rowValue: { color: colors.text, flex: 1, fontSize: fonts.size.sm, fontWeight: "600" },
  timestamp: { color: colors.textDim, fontSize: fonts.size.xs, textAlign: "center", marginTop: space.md },
  footer: { padding: space.lg, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.bg },
});
