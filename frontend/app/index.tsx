import React, { useEffect } from "react";
import { View, Text, StyleSheet, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "../src/auth";
import { colors, fonts } from "../src/theme";

export default function Splash() {
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user === undefined) return;
    const t = setTimeout(() => {
      if (user) router.replace("/(app)/(tabs)/agenda");
      else router.replace("/login");
    }, 600);
    return () => clearTimeout(t);
  }, [user, router]);

  return (
    <View style={styles.container} testID="splash-screen">
      <View style={styles.logoWrap}>
        <View style={styles.dot} />
        <Text style={styles.logoText}>
          VALE<Text style={{ color: colors.primary }}>TECK</Text>
        </Text>
        <Text style={styles.tag}>Instalamos tudo em segurança automotiva</Text>
      </View>
      <ActivityIndicator color={colors.primary} style={{ marginTop: 32 }} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, alignItems: "center", justifyContent: "center", padding: 24 },
  logoWrap: { alignItems: "center" },
  dot: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.primary,
    marginBottom: 20,
    shadowColor: colors.primary,
    shadowOpacity: 0.5,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 0 },
  },
  logoText: { color: colors.text, fontSize: 40, fontWeight: "900", letterSpacing: 2 },
  tag: { color: colors.textMuted, marginTop: 8, fontSize: fonts.size.sm },
});
