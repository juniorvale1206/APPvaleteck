import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../../src/auth";
import { Btn } from "../../src/components";
import { colors, fonts, radii, space } from "../../src/theme";

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

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="profile-back" onPress={() => router.back()} style={styles.iconBtn}>
          <Ionicons name="arrow-back" size={24} color={colors.text} />
        </TouchableOpacity>
        <Text style={styles.title}>Perfil</Text>
        <View style={{ width: 24 }} />
      </View>

      <View style={{ padding: space.lg }}>
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
          <Btn testID="logout-btn" title="Sair" icon="log-out-outline" variant="danger" onPress={onLogout} />
        </View>

        <Text style={styles.versionInfo}>Valeteck • v1.0.0 MVP</Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: space.lg,
    paddingVertical: space.sm,
  },
  iconBtn: { padding: 4 },
  title: { color: colors.text, fontWeight: "800", fontSize: fonts.size.xl },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: space.lg,
    alignItems: "center",
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  name: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "800", marginTop: 12 },
  email: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 4 },
  roleBadge: {
    marginTop: 10,
    backgroundColor: colors.surfaceAlt,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: radii.pill,
  },
  roleTxt: { color: colors.primary, fontWeight: "800", fontSize: fonts.size.xs, letterSpacing: 1 },
  versionInfo: { color: colors.textDim, textAlign: "center", marginTop: space.xl, fontSize: fonts.size.xs },
});
