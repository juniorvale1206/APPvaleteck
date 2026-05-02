import React, { useEffect, useMemo, useState } from "react";
import { View, Text, StyleSheet, Modal, Pressable, ScrollView, TouchableOpacity } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { api } from "./api";
import { colors, fonts, radii, space } from "./theme";

export type ServiceTypeDef = {
  code: string;
  name: string;
  category: string;
  max_minutes: number;
  base_value: number;
  level_restriction?: string | null;
};

type Props = {
  value: string;
  onChange: (code: string, def: ServiceTypeDef | null) => void;
  level?: string;
  testID?: string;
};

const CATEGORY_META: Record<string, { icon: any; color: string; label: string }> = {
  desinstalacao: { icon: "remove-circle", color: "#EF4444", label: "Desinstalação" },
  auditoria: { icon: "eye", color: "#8B5CF6", label: "Auditoria" },
  instalacao: { icon: "construct", color: "#3B82F6", label: "Instalação" },
  telemetria: { icon: "speedometer", color: "#10B981", label: "Telemetria" },
  acessorio: { icon: "star", color: "#F59E0B", label: "Acessório" },
};

export function ServiceTypePicker({ value, onChange, level, testID }: Props) {
  const [items, setItems] = useState<ServiceTypeDef[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const qs = level ? `?level=${level}` : "";
        const { data } = await api.get<{ items: ServiceTypeDef[] }>(`/reference/service-catalog${qs}`);
        setItems(data.items);
      } catch {}
    })();
  }, [level]);

  const selected = useMemo(() => items.find((i) => i.code === value) || null, [items, value]);

  const grouped = useMemo(() => {
    const map: Record<string, ServiceTypeDef[]> = {};
    for (const it of items) {
      (map[it.category] = map[it.category] || []).push(it);
    }
    return map;
  }, [items]);

  return (
    <>
      <View style={styles.wrap}>
        <Text style={styles.label}>Tipo de serviço (SLA)</Text>
        <TouchableOpacity
          testID={testID}
          style={[styles.trigger, selected && styles.triggerSelected]}
          onPress={() => setOpen(true)}
        >
          {selected ? (
            <>
              <View style={[styles.catDot, { backgroundColor: CATEGORY_META[selected.category]?.color || colors.primary }]}>
                <Ionicons name={CATEGORY_META[selected.category]?.icon || "construct"} size={14} color="#FFF" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.selTitle} numberOfLines={1}>{selected.name}</Text>
                <Text style={styles.selSub}>Máx {selected.max_minutes} min • R$ {selected.base_value.toFixed(2)}</Text>
              </View>
            </>
          ) : (
            <>
              <Ionicons name="construct-outline" size={22} color={colors.textMuted} />
              <Text style={styles.placeholder}>Selecionar tipo de serviço</Text>
            </>
          )}
          <Ionicons name="chevron-down" size={20} color={colors.textMuted} />
        </TouchableOpacity>
      </View>

      <Modal visible={open} transparent animationType="slide" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation?.()}>
            <View style={styles.sheetHandle} />
            <Text style={styles.sheetTitle}>Escolha o tipo de serviço</Text>
            <Text style={styles.sheetSub}>
              O SLA e o valor base são definidos aqui. O cronômetro vai alertar se passar do tempo máximo.
            </Text>
            <ScrollView style={{ maxHeight: 480 }} contentContainerStyle={{ paddingBottom: space.lg }}>
              {Object.entries(grouped).map(([cat, list]) => (
                <View key={cat} style={{ marginTop: space.md }}>
                  <View style={styles.catHeader}>
                    <View style={[styles.catDot, { backgroundColor: CATEGORY_META[cat]?.color || colors.primary }]}>
                      <Ionicons name={CATEGORY_META[cat]?.icon || "construct"} size={14} color="#FFF" />
                    </View>
                    <Text style={styles.catLabel}>{CATEGORY_META[cat]?.label || cat}</Text>
                  </View>
                  {list.map((it) => {
                    const active = it.code === value;
                    return (
                      <TouchableOpacity
                        key={it.code}
                        testID={`svc-${it.code}`}
                        style={[styles.row, active && styles.rowActive]}
                        onPress={() => { onChange(it.code, it); setOpen(false); }}
                      >
                        <View style={{ flex: 1 }}>
                          <Text style={styles.rowTitle}>{it.name}</Text>
                          <Text style={styles.rowSub}>
                            ⏱️ Máx {it.max_minutes} min • 💰 R$ {it.base_value.toFixed(2)}
                            {it.level_restriction ? `  •  Apenas ${it.level_restriction.toUpperCase()}` : ""}
                          </Text>
                        </View>
                        {active ? (
                          <Ionicons name="checkmark-circle" size={22} color={colors.primary} />
                        ) : (
                          <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
                        )}
                      </TouchableOpacity>
                    );
                  })}
                </View>
              ))}
            </ScrollView>
          </Pressable>
        </Pressable>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: space.md },
  label: { color: colors.textMuted, fontSize: fonts.size.sm, fontWeight: "600", marginBottom: 6, letterSpacing: 0.3, textTransform: "uppercase" },
  trigger: {
    flexDirection: "row", alignItems: "center", gap: 10,
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
    borderRadius: radii.md, paddingHorizontal: 12, paddingVertical: 12, minHeight: 58,
  },
  triggerSelected: { borderColor: colors.primary },
  placeholder: { color: colors.textMuted, flex: 1, fontSize: fonts.size.md },
  selTitle: { color: colors.text, fontWeight: "800", fontSize: fonts.size.md },
  selSub: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 2 },
  catDot: {
    width: 28, height: 28, borderRadius: 14,
    alignItems: "center", justifyContent: "center",
  },
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.6)", justifyContent: "flex-end" },
  sheet: {
    backgroundColor: colors.bg, paddingHorizontal: space.lg, paddingTop: space.sm, paddingBottom: space.lg,
    borderTopLeftRadius: 22, borderTopRightRadius: 22,
  },
  sheetHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: colors.border, alignSelf: "center", marginBottom: space.sm },
  sheetTitle: { color: colors.text, fontSize: fonts.size.lg, fontWeight: "900" },
  sheetSub: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 4, marginBottom: space.sm },
  catHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  catLabel: { color: colors.textMuted, fontSize: fonts.size.xs, fontWeight: "800", textTransform: "uppercase", letterSpacing: 1 },
  row: {
    flexDirection: "row", alignItems: "center", gap: 10,
    backgroundColor: colors.surface, borderRadius: radii.md, padding: 12, marginBottom: 6,
    borderWidth: 1, borderColor: colors.border,
  },
  rowActive: { borderColor: colors.primary, backgroundColor: colors.primary + "15" },
  rowTitle: { color: colors.text, fontSize: fonts.size.md, fontWeight: "700" },
  rowSub: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 3 },
});
