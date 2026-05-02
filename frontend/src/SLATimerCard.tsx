import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, fonts, radii, space } from "./theme";
import { formatSLA, useSLATimer } from "./slatimer";
import { useDraft } from "./draft";
import type { ServiceTypeDef } from "./ServiceTypePicker";

type Props = {
  serviceDef: ServiceTypeDef | null;
};

/**
 * Card de cronômetro ao vivo com barra de progresso vs SLA máximo.
 * - Verde: dentro de 80% do SLA
 * - Amarelo: 80-100%
 * - Vermelho: acima de 100% (SLA extrapolado)
 */
export function SLATimerCard({ serviceDef }: Props) {
  const { elapsedSec, startIfNeeded } = useSLATimer();
  const { draft, set } = useDraft();
  const maxSec = (serviceDef?.max_minutes || 0) * 60;
  const started = !!draft.execution_started_at;
  const ended = !!draft.execution_ended_at;
  const pct = maxSec > 0 ? Math.min(elapsedSec / maxSec, 2) : 0;    // cap 200%
  const over = pct > 1;
  const warn = pct >= 0.8 && !over;
  const color = over ? colors.danger : warn ? colors.warning : colors.success;
  const bgTint = color + "15";

  const remainingSec = Math.max(maxSec - elapsedSec, 0);
  const overSec = Math.max(elapsedSec - maxSec, 0);

  const handleStart = () => {
    if (!serviceDef) {
      Alert.alert("Selecione o tipo de serviço", "Escolha o tipo antes de iniciar o cronômetro.");
      return;
    }
    startIfNeeded();
  };

  const handleStop = () => {
    if (!started || ended) return;
    Alert.alert(
      "Finalizar serviço?",
      `Confirmar parada do cronômetro em ${formatSLA(elapsedSec)}?`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Finalizar", onPress: () => {
            const now = new Date().toISOString();
            set({ execution_ended_at: now, execution_elapsed_sec: elapsedSec });
          },
        },
      ],
    );
  };

  return (
    <View style={[styles.card, { borderColor: color, backgroundColor: bgTint }]} testID="sla-timer-card">
      <View style={styles.row}>
        <View style={[styles.iconWrap, { backgroundColor: color + "30" }]}>
          <Ionicons
            name={over ? "alert-circle" : warn ? "warning" : "time"}
            size={22}
            color={color}
          />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>
            {!started ? "Cronômetro SLA" : ended ? "⏹️ Serviço finalizado" : "⏱️ Em execução"}
          </Text>
          <Text style={styles.sub}>
            {serviceDef
              ? `${serviceDef.name} • Máx ${serviceDef.max_minutes} min`
              : "Selecione o tipo de serviço para ativar o SLA"}
          </Text>
        </View>
        <Text style={[styles.timer, { color }]}>{formatSLA(elapsedSec)}</Text>
      </View>

      {serviceDef && started && (
        <View style={styles.barWrap}>
          <View style={styles.barBg}>
            <View style={[styles.barFill, { width: `${Math.min(pct * 100, 100)}%`, backgroundColor: color }]} />
            {over && <View style={[styles.barOver, { width: `${Math.min((pct - 1) * 100, 100)}%` }]} />}
          </View>
          <Text style={[styles.barText, { color }]}>
            {over
              ? `⚠️ SLA extrapolado em ${formatSLA(overSec)} — valor pode ser cortado em 50%`
              : `Restam ${formatSLA(remainingSec)} para cumprir o SLA`}
          </Text>
        </View>
      )}

      <View style={styles.btnRow}>
        {!started && (
          <TouchableOpacity
            testID="btn-start-sla"
            onPress={handleStart}
            style={[styles.btn, { backgroundColor: colors.primary }]}
          >
            <Ionicons name="play" size={18} color={colors.onPrimary} />
            <Text style={styles.btnTxtPrimary}>Iniciar serviço</Text>
          </TouchableOpacity>
        )}
        {started && !ended && (
          <TouchableOpacity
            testID="btn-stop-sla"
            onPress={handleStop}
            style={[styles.btn, { backgroundColor: colors.danger }]}
          >
            <Ionicons name="stop" size={18} color="#FFF" />
            <Text style={styles.btnTxtWhite}>Finalizar serviço</Text>
          </TouchableOpacity>
        )}
        {ended && (
          <View style={[styles.btn, { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border }]}>
            <Ionicons name="checkmark-circle" size={18} color={colors.success} />
            <Text style={[styles.btnTxtPrimary, { color: colors.text }]}>
              Finalizado em {formatSLA(draft.execution_elapsed_sec || elapsedSec)}
            </Text>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderRadius: radii.lg, padding: space.md, marginBottom: space.md },
  row: { flexDirection: "row", alignItems: "center", gap: 10 },
  iconWrap: { width: 42, height: 42, borderRadius: 21, alignItems: "center", justifyContent: "center" },
  title: { color: colors.text, fontWeight: "900", fontSize: fonts.size.md },
  sub: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 2 },
  timer: { fontSize: 20, fontWeight: "900", fontVariant: ["tabular-nums"] as any },
  barWrap: { marginTop: space.sm },
  barBg: {
    height: 10, backgroundColor: colors.surfaceAlt,
    borderRadius: 5, overflow: "hidden", position: "relative",
  },
  barFill: { height: "100%", borderRadius: 5 },
  barOver: {
    position: "absolute", top: 0, right: 0, height: "100%",
    backgroundColor: colors.danger, opacity: 0.5,
  },
  barText: { fontSize: fonts.size.xs, fontWeight: "700", marginTop: 6 },
  btnRow: { marginTop: space.sm },
  btn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 8, paddingVertical: 12, borderRadius: radii.md,
  },
  btnTxtPrimary: { color: colors.onPrimary, fontWeight: "900" },
  btnTxtWhite: { color: "#FFF", fontWeight: "900" },
});
