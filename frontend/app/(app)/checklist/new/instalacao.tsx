import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, KeyboardAvoidingView, Platform } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Btn, Field, MultiSelect, Select, StepProgress } from "../../../../src/components";
import { useDraft } from "../../../../src/draft";
import { api } from "../../../../src/api";
import { colors, fonts, space } from "../../../../src/theme";

export default function StepInstalacao() {
  const router = useRouter();
  const { draft, set } = useDraft();
  const [companies, setCompanies] = useState<string[]>([]);
  const [equipments, setEquipments] = useState<string[]>([]);
  const [accessories, setAccessories] = useState<string[]>([]);
  const [serviceTypes, setServiceTypes] = useState<string[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    (async () => {
      try {
        const [c, e, a, s] = await Promise.all([
          api.get("/reference/companies"),
          api.get("/reference/equipments"),
          api.get("/reference/accessories"),
          api.get("/reference/service-types"),
        ]);
        setCompanies(c.data.companies);
        setEquipments(e.data.equipments);
        setAccessories(a.data.accessories);
        setServiceTypes(s.data.service_types);
      } catch {}
    })();
  }, []);

  const next = () => {
    const er: Record<string, string> = {};
    if (!draft.empresa) er.empresa = "Obrigatório";
    if (!draft.equipamento) er.equipamento = "Obrigatório";
    setErrors(er);
    if (Object.keys(er).length) return;
    router.push("/(app)/checklist/new/evidencias");
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="back-btn" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Instalação</Text>
        <View style={{ width: 26 }} />
      </View>
      <StepProgress step={2} total={5} />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <Text style={styles.section}>Dados da instalação</Text>
          <Select testID="select-empresa" label="Empresa / Parceiro" required value={draft.empresa as any} options={companies} onChange={(v) => set({ empresa: v })} error={errors.empresa} />
          <Select testID="select-equipamento" label="Equipamento principal" required value={draft.equipamento as any} options={equipments} onChange={(v) => set({ equipamento: v })} error={errors.equipamento} />
          <Select testID="select-tipo" label="Tipo de atendimento" value={draft.tipo_atendimento as any} options={serviceTypes} onChange={(v) => set({ tipo_atendimento: v })} />
          <MultiSelect testID="select-acessorios" label="Acessórios instalados" values={draft.acessorios} options={accessories} onChange={(v) => set({ acessorios: v })} />
          <Field testID="instal-obs" label="Observações técnicas" value={draft.obs_tecnicas} onChangeText={(v) => set({ obs_tecnicas: v })} multiline numberOfLines={3} style={{ minHeight: 90, textAlignVertical: "top" } as any} placeholder="Opcional" />
        </ScrollView>
      </KeyboardAvoidingView>
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
  section: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "800", marginBottom: space.md },
  footer: { padding: space.lg, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.bg },
});
