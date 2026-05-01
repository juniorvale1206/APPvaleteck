import React, { useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Btn } from "../../../../src/components";
import { useDraft } from "../../../../src/draft";
import { api, apiErrorMessage } from "../../../../src/api";
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
  const [loading, setLoading] = useState(false);

  const submit = async (status: "rascunho" | "enviado") => {
    setLoading(true);
    try {
      const payload = { ...draft, status };
      const { data } = await api.post("/checklists", payload);
      reset();
      Alert.alert(
        status === "enviado" ? "Checklist enviado!" : "Rascunho salvo",
        status === "enviado" ? `Número: ${data.numero}` : "Você pode continuar depois.",
        [
          {
            text: "OK",
            onPress: () => router.replace({ pathname: "/(app)/checklist/[id]", params: { id: data.id } }),
          },
        ]
      );
    } catch (e: any) {
      Alert.alert("Erro", apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const onSend = () => {
    Alert.alert("Enviar checklist", "Confirma o envio? Após o envio não será possível editar.", [
      { text: "Cancelar", style: "cancel" },
      { text: "Enviar", onPress: () => submit("enviado") },
    ]);
  };

  const editStep = (path: string) => router.push(path as any);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="back-btn" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Revisão</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.section}>Confira antes de enviar</Text>

        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.cardTitle}>Cliente</Text>
            <TouchableOpacity onPress={() => editStep("/(app)/checklist/new")}><Text style={styles.editLink}>Editar</Text></TouchableOpacity>
          </View>
          <Row label="Nome" value={`${draft.nome} ${draft.sobrenome}`.trim()} />
          <Row label="Placa" value={draft.placa} />
          <Row label="Telefone" value={draft.telefone} />
        </View>

        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.cardTitle}>Instalação</Text>
            <TouchableOpacity onPress={() => editStep("/(app)/checklist/new/instalacao")}><Text style={styles.editLink}>Editar</Text></TouchableOpacity>
          </View>
          <Row label="Empresa" value={draft.empresa} />
          <Row label="Equipamento" value={draft.equipamento} />
          <Row label="Tipo" value={draft.tipo_atendimento} />
          <Row label="Acessórios" value={draft.acessorios.join(", ") || "Nenhum"} />
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
  row: { flexDirection: "row", paddingVertical: 6 },
  rowLabel: { color: colors.textMuted, width: 110, fontSize: fonts.size.sm },
  rowValue: { color: colors.text, flex: 1, fontSize: fonts.size.sm, fontWeight: "600" },
  timestamp: { color: colors.textDim, fontSize: fonts.size.xs, textAlign: "center", marginTop: space.md },
  footer: { padding: space.lg, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.bg },
});
