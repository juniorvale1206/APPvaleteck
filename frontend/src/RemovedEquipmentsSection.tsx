import React, { useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Modal, ScrollView, TextInput, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, fonts, radii, space } from "./theme";

export type RemovedEquipment = {
  tipo: string;
  modelo?: string;
  imei?: string;
  iccid?: string;
  serie?: string;
  estado?: string;
  notes?: string;
};

const TIPOS = ["Rastreador", "Bloqueador", "Câmera", "Outro"];
const ESTADOS = ["funcional", "avariado", "defeituoso"];

function Chip({ label, active, onPress, testID }: { label: string; active: boolean; onPress: () => void; testID?: string }) {
  return (
    <TouchableOpacity testID={testID} onPress={onPress} style={[styles.chip, active && styles.chipActive]}>
      <Text style={[styles.chipTxt, active && styles.chipTxtActive]}>{label}</Text>
    </TouchableOpacity>
  );
}

export function RemovedEquipmentsSection({
  items,
  onChange,
}: {
  items: RemovedEquipment[];
  onChange: (items: RemovedEquipment[]) => void;
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const [editIdx, setEditIdx] = useState<number | null>(null);
  const [form, setForm] = useState<RemovedEquipment>({ tipo: "Rastreador", estado: "funcional" });

  const openNew = () => {
    setForm({ tipo: "Rastreador", estado: "funcional" });
    setEditIdx(null);
    setModalOpen(true);
  };
  const openEdit = (idx: number) => {
    setForm(items[idx]);
    setEditIdx(idx);
    setModalOpen(true);
  };
  const submit = () => {
    if (!form.tipo) return;
    const next = [...items];
    if (editIdx !== null) next[editIdx] = form;
    else next.push(form);
    onChange(next);
    setModalOpen(false);
  };
  const remove = (idx: number) => {
    const next = items.filter((_, i) => i !== idx);
    onChange(next);
  };

  return (
    <View style={styles.wrapper}>
      <View style={styles.header}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>Equipamentos retirados</Text>
          <Text style={styles.subtitle}>Irão automaticamente para seu estoque em logística reversa</Text>
        </View>
        <TouchableOpacity testID="add-removed-equipment" onPress={openNew} style={styles.addBtn}>
          <Ionicons name="add-circle" size={22} color={colors.primary} />
          <Text style={styles.addTxt}>Adicionar</Text>
        </TouchableOpacity>
      </View>

      {items.length === 0 ? (
        <View style={styles.emptyBox}>
          <Ionicons name="return-up-back-outline" size={20} color={colors.textDim} />
          <Text style={styles.emptyTxt}>Nenhum equipamento retirado ainda</Text>
        </View>
      ) : (
        items.map((it, i) => (
          <View key={i} style={styles.item} testID={`removed-item-${i}`}>
            <View style={{ flex: 1 }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                <Text style={styles.itemTitle}>{it.tipo}{it.modelo ? ` — ${it.modelo}` : ""}</Text>
                {it.estado && (
                  <View style={[
                    styles.estadoBadge,
                    it.estado === "avariado" && { backgroundColor: "#FEF3C7", borderColor: "#F59E0B" },
                    it.estado === "defeituoso" && { backgroundColor: "#FEE2E2", borderColor: "#EF4444" },
                  ]}>
                    <Text style={[
                      styles.estadoTxt,
                      it.estado === "avariado" && { color: "#B45309" },
                      it.estado === "defeituoso" && { color: "#7F1D1D" },
                    ]}>{it.estado}</Text>
                  </View>
                )}
              </View>
              {!!(it.imei || it.serie) && (
                <Text style={styles.itemMeta}>
                  {it.imei ? `IMEI ${it.imei}` : ""}{it.imei && it.serie ? " • " : ""}{it.serie ? `SN ${it.serie}` : ""}
                </Text>
              )}
              {!!it.notes && <Text style={styles.itemNotes} numberOfLines={2}>{it.notes}</Text>}
            </View>
            <TouchableOpacity testID={`edit-removed-${i}`} onPress={() => openEdit(i)} style={styles.iconBtn}>
              <Ionicons name="pencil" size={18} color={colors.textMuted} />
            </TouchableOpacity>
            <TouchableOpacity testID={`delete-removed-${i}`} onPress={() => remove(i)} style={styles.iconBtn}>
              <Ionicons name="trash" size={18} color={colors.danger} />
            </TouchableOpacity>
          </View>
        ))
      )}

      {/* MODAL */}
      <Modal visible={modalOpen} transparent animationType="slide" onRequestClose={() => setModalOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setModalOpen(false)}>
          <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation?.()}>
            <View style={{ alignItems: "center", marginBottom: 8 }}>
              <View style={styles.handle} />
            </View>
            <Text style={styles.sheetTitle}>{editIdx === null ? "Novo equipamento retirado" : "Editar equipamento"}</Text>

            <ScrollView style={{ maxHeight: 480 }}>
              <Text style={styles.label}>Tipo *</Text>
              <View style={styles.chipsRow}>
                {TIPOS.map((t) => (
                  <Chip key={t} label={t} active={form.tipo === t} onPress={() => setForm({ ...form, tipo: t })} testID={`eq-tipo-${t}`} />
                ))}
              </View>

              <Text style={styles.label}>Modelo</Text>
              <TextInput
                testID="eq-modelo"
                value={form.modelo || ""}
                onChangeText={(v) => setForm({ ...form, modelo: v })}
                placeholder="Ex: Rastreador XT-2000"
                placeholderTextColor={colors.textDim}
                style={styles.input}
              />

              <View style={{ flexDirection: "row", gap: 8 }}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.label}>IMEI (15 dígitos)</Text>
                  <TextInput
                    testID="eq-imei"
                    value={form.imei || ""}
                    onChangeText={(v) => setForm({ ...form, imei: v.replace(/\D/g, "").slice(0, 15) })}
                    keyboardType="number-pad"
                    placeholder="opcional"
                    placeholderTextColor={colors.textDim}
                    style={styles.input}
                    maxLength={15}
                  />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.label}>N° de série</Text>
                  <TextInput
                    testID="eq-serie"
                    value={form.serie || ""}
                    onChangeText={(v) => setForm({ ...form, serie: v })}
                    placeholder="SN-..."
                    placeholderTextColor={colors.textDim}
                    style={styles.input}
                  />
                </View>
              </View>

              <Text style={styles.label}>Estado do equipamento</Text>
              <View style={styles.chipsRow}>
                {ESTADOS.map((e) => (
                  <Chip
                    key={e}
                    label={e.charAt(0).toUpperCase() + e.slice(1)}
                    active={form.estado === e}
                    onPress={() => setForm({ ...form, estado: e })}
                    testID={`eq-estado-${e}`}
                  />
                ))}
              </View>

              <Text style={styles.label}>Observações</Text>
              <TextInput
                testID="eq-notes"
                value={form.notes || ""}
                onChangeText={(v) => setForm({ ...form, notes: v })}
                placeholder="Ex: antena queimada, lacre violado..."
                placeholderTextColor={colors.textDim}
                style={[styles.input, { height: 70, textAlignVertical: "top" }]}
                multiline
              />
            </ScrollView>

            <View style={{ flexDirection: "row", gap: 10, marginTop: 12 }}>
              <TouchableOpacity testID="eq-cancel" onPress={() => setModalOpen(false)} style={[styles.modalBtn, styles.cancelBtn]}>
                <Text style={{ color: colors.text, fontWeight: "700" }}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity testID="eq-save" onPress={submit} style={[styles.modalBtn, { backgroundColor: colors.primary }]}>
                <Text style={{ color: colors.onPrimary, fontWeight: "900" }}>Salvar</Text>
              </TouchableOpacity>
            </View>
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    backgroundColor: "#FFF7ED", borderColor: "#FDBA74", borderWidth: 1,
    borderRadius: radii.md, padding: space.md, marginTop: space.md,
  },
  header: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: space.sm },
  title: { color: "#9A3412", fontWeight: "900", fontSize: fonts.size.md },
  subtitle: { color: "#9A3412", fontSize: fonts.size.xs, marginTop: 2 },
  addBtn: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 10, paddingVertical: 6, backgroundColor: colors.brandBlack, borderRadius: radii.sm },
  addTxt: { color: colors.primary, fontWeight: "900", fontSize: fonts.size.xs },
  emptyBox: { flexDirection: "row", alignItems: "center", gap: 6, paddingVertical: 8, opacity: 0.7 },
  emptyTxt: { color: colors.textDim, fontSize: fonts.size.sm, fontStyle: "italic" },
  item: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: colors.surface, padding: 10, borderRadius: radii.sm, marginTop: 6, borderWidth: 1, borderColor: colors.border },
  itemTitle: { color: colors.text, fontWeight: "800", fontSize: fonts.size.sm, flex: 1 },
  itemMeta: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 2 },
  itemNotes: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 2, fontStyle: "italic" },
  iconBtn: { padding: 6 },
  estadoBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999, borderWidth: 1, backgroundColor: "#D1FAE5", borderColor: "#10B981" },
  estadoTxt: { fontSize: 10, fontWeight: "800", color: "#065F46", textTransform: "uppercase", letterSpacing: 0.5 },
  // Modal
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.6)", justifyContent: "flex-end" },
  sheet: { backgroundColor: colors.surface, padding: space.lg, borderTopLeftRadius: 20, borderTopRightRadius: 20, maxHeight: "90%" },
  handle: { width: 42, height: 5, borderRadius: 999, backgroundColor: colors.border, marginBottom: 10 },
  sheetTitle: { color: colors.text, fontWeight: "900", fontSize: fonts.size.lg, marginBottom: space.sm },
  label: { color: colors.textMuted, fontWeight: "800", fontSize: fonts.size.xs, marginBottom: 6, marginTop: 10, textTransform: "uppercase", letterSpacing: 0.5 },
  input: { backgroundColor: colors.surfaceAlt, borderColor: colors.border, borderWidth: 1, borderRadius: radii.md, padding: 12, color: colors.text, fontSize: fonts.size.md },
  chipsRow: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  chip: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 999, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surfaceAlt },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipTxt: { color: colors.text, fontWeight: "700", fontSize: fonts.size.xs },
  chipTxtActive: { color: colors.onPrimary, fontWeight: "900" },
  modalBtn: { flex: 1, paddingVertical: 14, alignItems: "center", borderRadius: radii.md },
  cancelBtn: { backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border },
});
