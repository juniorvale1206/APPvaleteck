import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, fonts } from "./theme";
import { formatSLA, slaColor, useSLATimer } from "./slatimer";

export function SLABadge({ compact }: { compact?: boolean }) {
  const { elapsedSec } = useSLATimer();
  if (elapsedSec <= 0) return null;
  const c = slaColor(elapsedSec);
  return (
    <View style={[styles.wrap, compact && styles.compact, { borderColor: c }]} testID="sla-badge">
      <Ionicons name="time" size={14} color={c} />
      <Text style={[styles.txt, { color: c }]}>{formatSLA(elapsedSec)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
    backgroundColor: colors.surface,
  },
  compact: { paddingHorizontal: 8, paddingVertical: 2 },
  txt: { fontWeight: "800", fontSize: fonts.size.sm, fontVariant: ["tabular-nums"] as any },
});
