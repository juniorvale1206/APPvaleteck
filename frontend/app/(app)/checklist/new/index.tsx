import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, KeyboardAvoidingView, Platform, Alert } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Btn, Field, StepProgress } from "../../../../src/components";
import { useDraft, isValidPlate, formatPlate } from "../../../../src/draft";
import { colors, fonts, space } from "../../../../src/theme";

export default function StepCliente() {
  const router = useRouter();
  const { draft, set } = useDraft();
  const [errors, setErrors] = useState<Record<string, string>>({});

  const next = () => {
    const e: Record<string, string> = {};
    if (!draft.nome.trim()) e.nome = "Obrigatório";
    if (!draft.sobrenome.trim()) e.sobrenome = "Obrigatório";
    if (!draft.placa.trim()) e.placa = "Obrigatório";
    else if (!isValidPlate(draft.placa)) e.placa = "Placa inválida (ex: ABC1D23)";
    setErrors(e);
    if (Object.keys(e).length) return;
    router.push("/(app)/checklist/new/instalacao");
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="back-btn" onPress={() => router.back()}><Ionicons name="close" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Novo Checklist</Text>
        <View style={{ width: 26 }} />
      </View>
      <StepProgress step={1} total={5} />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <Text style={styles.section}>Dados do cliente</Text>
          <Field testID="cliente-nome" label="Nome" required value={draft.nome} onChangeText={(v) => set({ nome: v })} error={errors.nome} placeholder="João" />
          <Field testID="cliente-sobrenome" label="Sobrenome" required value={draft.sobrenome} onChangeText={(v) => set({ sobrenome: v })} error={errors.sobrenome} placeholder="Silva" />
          <Field
            testID="cliente-placa"
            label="Placa do veículo"
            required
            autoCapitalize="characters"
            value={draft.placa}
            onChangeText={(v) => set({ placa: formatPlate(v) })}
            error={errors.placa}
            placeholder="ABC-1D23"
            maxLength={8}
          />
          <Field testID="cliente-telefone" label="Telefone" value={draft.telefone} onChangeText={(v) => set({ telefone: v })} keyboardType="phone-pad" placeholder="(11) 99999-9999" />
          <Field testID="cliente-obs" label="Observações iniciais" value={draft.obs_iniciais} onChangeText={(v) => set({ obs_iniciais: v })} placeholder="Opcional" multiline numberOfLines={3} style={{ minHeight: 90, textAlignVertical: "top" } as any} />
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
