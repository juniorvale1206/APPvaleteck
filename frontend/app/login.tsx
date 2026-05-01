import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  TouchableWithoutFeedback,
  Keyboard,
  ScrollView,
  Alert,
} from "react-native";
import { useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuth } from "../src/auth";
import { Btn, Field } from "../src/components";
import { colors, fonts, space } from "../src/theme";
import { apiErrorMessage } from "../src/api";

export default function Login() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("tecnico@valeteck.com");
  const [password, setPassword] = useState("tecnico123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onSubmit = async () => {
    setError("");
    if (!email.trim() || !password.trim()) {
      setError("Informe e-mail e senha");
      return;
    }
    setLoading(true);
    try {
      await login(email.trim().toLowerCase(), password);
      router.replace("/(app)/home");
    } catch (e: any) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
          <ScrollView
            contentContainerStyle={styles.container}
            keyboardShouldPersistTaps="handled"
          >
            <View style={styles.brand}>
              <View style={styles.dot} />
              <Text style={styles.logo}>
                VALE<Text style={{ color: colors.primary }}>TECK</Text>
              </Text>
              <Text style={styles.tag}>Checklist de instalação veicular</Text>
            </View>

            <View style={styles.card}>
              <Text style={styles.title}>Entrar</Text>
              <Text style={styles.subtitle}>Acesse sua conta de técnico</Text>

              <Field
                testID="login-email"
                label="E-mail"
                required
                placeholder="seu@email.com"
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                keyboardType="email-address"
                autoComplete="email"
              />
              <Field
                testID="login-password"
                label="Senha"
                required
                placeholder="••••••••"
                value={password}
                onChangeText={setPassword}
                secureTextEntry
              />

              {!!error && <Text style={styles.errorBox} testID="login-error">{error}</Text>}

              <Btn
                testID="login-submit"
                title="Entrar"
                onPress={onSubmit}
                loading={loading}
                icon="log-in-outline"
              />

              <Text style={styles.helper}>
                Demo: tecnico@valeteck.com / tecnico123
              </Text>
            </View>
          </ScrollView>
        </TouchableWithoutFeedback>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { padding: space.lg, paddingTop: space.xl, flexGrow: 1 },
  brand: { alignItems: "center", marginBottom: space.xl, marginTop: space.md },
  dot: { width: 48, height: 48, borderRadius: 24, backgroundColor: colors.primary, marginBottom: 12 },
  logo: { color: colors.text, fontSize: 32, fontWeight: "900", letterSpacing: 2 },
  tag: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 4 },
  card: {
    backgroundColor: colors.surface,
    padding: space.lg,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
  },
  title: { color: colors.text, fontSize: fonts.size.xxl, fontWeight: "900" },
  subtitle: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 4, marginBottom: space.lg },
  errorBox: {
    color: colors.danger,
    backgroundColor: "#3A1414",
    padding: 12,
    borderRadius: 10,
    marginBottom: 12,
    fontSize: fonts.size.sm,
  },
  helper: { color: colors.textDim, fontSize: fonts.size.xs, marginTop: 14, textAlign: "center" },
});
