import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../../src/auth";
import { Btn } from "../../src/components";
import { colors, fonts, radii, shadow, space } from "../../src/theme";

export default function Profile() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const onLogout = () => {
    Alert.alert("Sair", "Deseja realmente sair?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Sair",
        style: "destructive",
        onPress: async () => {
          await logout();
          router.replace("/login");
        },
      },
    ]);
  };

  const MenuRow = ({ icon, label, color, onPress, testID }: { icon: keyof typeof Ionicons.glyphMap; label: string; color: string; onPress: () => void; testID: string }) => (
    <TouchableOpacity testID={testID} onPress={onPress} style={styles.menuRow} activeOpacity={0.8}>
      <View style={[styles.menuIcon, { backgroundColor: color + "22" }]}>
        <Ionicons name={icon} size={22} color={color} />
      </View>
      <Text style={styles.menuLabel}>{label}</Text>
      <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <ScrollView contentContainerStyle={{ padding: space.lg, paddingBottom: 80 }}>
        <View style={styles.card}>
          <View style={styles.avatar}>
            <Ionicons name="person" size={40} color={colors.onPrimary} />
          </View>
          <Text style={styles.name}>{user?.name}</Text>
          <Text style={styles.email}>{user?.email}</Text>
          <View style={styles.roleBadge}>
            <Text style={styles.roleTxt}>{(user?.role || "").toUpperCase()}</Text>
          </View>
        </View>

        <View style={{ marginTop: space.lg }}>
          <Text style={styles.sectionTitle}>Operações</Text>
          <MenuRow testID="menu-ranking" icon="trophy-outline" label="Ranking semanal" color="#F59E0B" onPress={() => router.push("/(app)/ranking")} />
          <MenuRow testID="menu-gamification" icon="ribbon-outline" label="Conquistas e níveis" color="#8B5CF6" onPress={() => router.push("/(app)/gamification")} />
          <MenuRow testID="menu-estoque" icon="cube-outline" label="Meu estoque" color="#3B82F6" onPress={() => router.push("/(app)/estoque")} />
          <MenuRow testID="menu-sync" icon="sync-outline" label="Fila de sincronização" color="#10B981" onPress={() => router.push("/(app)/sync")} />
        </View>

        <View style={{ marginTop: space.lg }}>
          <Btn testID="logout-btn" title="Sair" icon="log-out-outline" variant="danger" onPress={onLogout} />
        </View>

        <Text style={styles.versionInfo}>Valeteck • v10 — Gamificação avançada</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: space.lg, alignItems: "center", ...shadow.sm },
  avatar: { width: 80, height: 80, borderRadius: 40, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  name: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "800", marginTop: 12 },
  email: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 4 },
  roleBadge: { marginTop: 10, backgroundColor: colors.surfaceAlt, paddingHorizontal: 12, paddingVertical: 4, borderRadius: radii.pill },
  roleTxt: { color: colors.brandBlack, fontWeight: "800", fontSize: fonts.size.xs, letterSpacing: 1 },
  sectionTitle: { color: colors.textMuted, fontWeight: "800", fontSize: fonts.size.xs, marginBottom: 10, textTransform: "uppercase", letterSpacing: 1 },
  menuRow: { flexDirection: "row", alignItems: "center", gap: 12, backgroundColor: colors.surface, borderRadius: radii.md, padding: 14, marginBottom: 8, ...shadow.sm },
  menuIcon: { width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center" },
  menuLabel: { color: colors.text, fontSize: fonts.size.md, fontWeight: "700", flex: 1 },
  versionInfo: { color: colors.textDim, textAlign: "center", marginTop: space.xl, fontSize: fonts.size.xs },
});
