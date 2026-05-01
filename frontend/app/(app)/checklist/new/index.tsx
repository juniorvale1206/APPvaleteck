import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { Btn, StepProgress } from "../../../../src/components";
import { useDraft } from "../../../../src/draft";
import { colors, fonts, radii, space } from "../../../../src/theme";

export default function StepTipoVeiculo() {
  const router = useRouter();
  const { draft, set } = useDraft();

  const choose = (t: "carro" | "moto") => {
    set({ vehicle_type: t, acessorios: [] });
  };

  const next = () => {
    if (!draft.vehicle_type) return;
    router.push("/(app)/checklist/new/cliente");
  };

  const Card = ({ type, label, icon }: { type: "carro" | "moto"; label: string; icon: React.ReactNode }) => {
    const active = draft.vehicle_type === type;
    return (
      <TouchableOpacity
        testID={`vehicle-${type}`}
        activeOpacity={0.85}
        onPress={() => choose(type)}
        style={[styles.card, active && styles.cardActive]}
      >
        <View style={[styles.iconBg, active && { backgroundColor: colors.primary }]}>{icon}</View>
        <Text style={[styles.cardLabel, active && { color: colors.primary }]}>{label}</Text>
        {active && (
          <View style={styles.check}>
            <Ionicons name="checkmark-circle" size={22} color={colors.primary} />
          </View>
        )}
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="back-btn" onPress={() => router.back()}><Ionicons name="close" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Novo Checklist</Text>
        <View style={{ width: 26 }} />
      </View>
      <StepProgress step={1} total={6} />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.section}>Tipo de veículo</Text>
        <Text style={styles.helper}>Selecione o tipo para continuar</Text>
        <View style={styles.grid}>
          <Card
            type="carro"
            label="Carro"
            icon={<Ionicons name="car-sport" size={68} color={draft.vehicle_type === "carro" ? colors.onPrimary : colors.text} />}
          />
          <Card
            type="moto"
            label="Moto"
            icon={<MaterialCommunityIcons name="motorbike" size={68} color={draft.vehicle_type === "moto" ? colors.onPrimary : colors.text} />}
          />
        </View>
      </ScrollView>
      <View style={styles.footer}>
        <Btn testID="step-next" title="Continuar" icon="arrow-forward" onPress={next} disabled={!draft.vehicle_type} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingTop: space.sm, paddingBottom: space.xs },
  title: { color: colors.text, fontWeight: "800", fontSize: fonts.size.lg },
  content: { padding: space.lg, paddingBottom: 100 },
  section: { color: colors.text, fontSize: fonts.size.xxl, fontWeight: "900" },
  helper: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 4, marginBottom: space.xl },
  grid: { flexDirection: "row", gap: 14 },
  card: { flex: 1, backgroundColor: colors.surface, borderRadius: radii.xl, padding: space.lg, alignItems: "center", borderWidth: 2, borderColor: colors.border, minHeight: 200, justifyContent: "center", position: "relative" },
  cardActive: { borderColor: colors.primary, backgroundColor: colors.surfaceAlt },
  iconBg: { width: 100, height: 100, borderRadius: 50, backgroundColor: colors.surfaceAlt, alignItems: "center", justifyContent: "center", marginBottom: 12 },
  cardLabel: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "800" },
  check: { position: "absolute", top: 12, right: 12 },
  footer: { padding: space.lg, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.bg },
});
