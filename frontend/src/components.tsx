import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  ScrollView,
  Modal,
  Pressable,
  TextInputProps,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, fonts, radii, space, status as statusMap } from "./theme";

export function Btn({
  title,
  onPress,
  variant = "primary",
  loading,
  disabled,
  icon,
  testID,
}: {
  title: string;
  onPress: () => void;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  loading?: boolean;
  disabled?: boolean;
  icon?: keyof typeof Ionicons.glyphMap;
  testID?: string;
}) {
  const isDisabled = disabled || loading;
  const styleMap = {
    primary: { bg: colors.primary, fg: colors.onPrimary, border: colors.primary },
    secondary: { bg: colors.surfaceAlt, fg: colors.text, border: colors.border },
    ghost: { bg: "transparent", fg: colors.text, border: "transparent" },
    danger: { bg: "#3A1414", fg: colors.danger, border: "#5A2020" },
  }[variant];
  return (
    <TouchableOpacity
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={title}
      activeOpacity={0.85}
      onPress={onPress}
      disabled={isDisabled}
      style={[
        styles.btn,
        { backgroundColor: styleMap.bg, borderColor: styleMap.border, opacity: isDisabled ? 0.55 : 1 },
      ]}
    >
      {loading ? (
        <ActivityIndicator color={styleMap.fg} />
      ) : (
        <>
          {icon && <Ionicons name={icon} size={20} color={styleMap.fg} style={{ marginRight: 8 }} />}
          <Text style={[styles.btnTxt, { color: styleMap.fg }]}>{title}</Text>
        </>
      )}
    </TouchableOpacity>
  );
}

export function Field({
  label,
  required,
  error,
  ...props
}: { label: string; required?: boolean; error?: string } & TextInputProps) {
  return (
    <View style={{ marginBottom: space.md }}>
      <Text style={styles.label}>
        {label}
        {required ? <Text style={{ color: colors.primary }}> *</Text> : null}
      </Text>
      <TextInput
        placeholderTextColor={colors.textDim}
        style={[styles.input, !!error && { borderColor: colors.danger }]}
        {...props}
      />
      {!!error && <Text style={styles.error}>{error}</Text>}
    </View>
  );
}

export function Select<T extends string>({
  label,
  required,
  value,
  options,
  onChange,
  error,
  testID,
}: {
  label: string;
  required?: boolean;
  value: T | "";
  options: T[];
  onChange: (v: T) => void;
  error?: string;
  testID?: string;
}) {
  const [open, setOpen] = React.useState(false);
  return (
    <View style={{ marginBottom: space.md }}>
      <Text style={styles.label}>
        {label}
        {required ? <Text style={{ color: colors.primary }}> *</Text> : null}
      </Text>
      <TouchableOpacity
        testID={testID}
        activeOpacity={0.8}
        onPress={() => setOpen(true)}
        style={[styles.input, styles.selectBox, !!error && { borderColor: colors.danger }]}
      >
        <Text style={{ color: value ? colors.text : colors.textDim, fontSize: fonts.size.md }}>
          {value || "Selecione..."}
        </Text>
        <Ionicons name="chevron-down" size={20} color={colors.textMuted} />
      </TouchableOpacity>
      {!!error && <Text style={styles.error}>{error}</Text>}
      <Modal transparent visible={open} animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.modalBackdrop} onPress={() => setOpen(false)}>
          <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation()}>
            <Text style={styles.sheetTitle}>{label}</Text>
            <ScrollView>
              {options.map((opt) => (
                <TouchableOpacity
                  key={opt}
                  testID={`select-option-${opt}`}
                  style={styles.sheetItem}
                  onPress={() => { onChange(opt); setOpen(false); }}
                >
                  <Text style={{ color: colors.text, fontSize: fonts.size.md }}>{opt}</Text>
                  {opt === value && <Ionicons name="checkmark" size={20} color={colors.primary} />}
                </TouchableOpacity>
              ))}
            </ScrollView>
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}

export function MultiSelect({
  label,
  values,
  options,
  onChange,
  testID,
}: {
  label: string;
  values: string[];
  options: string[];
  onChange: (v: string[]) => void;
  testID?: string;
}) {
  const toggle = (opt: string) => {
    if (values.includes(opt)) onChange(values.filter((v) => v !== opt));
    else onChange([...values, opt]);
  };
  return (
    <View style={{ marginBottom: space.md }} testID={testID}>
      <Text style={styles.label}>{label}</Text>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
        {options.map((opt) => {
          const active = values.includes(opt);
          return (
            <TouchableOpacity
              key={opt}
              onPress={() => toggle(opt)}
              testID={`accessory-${opt}`}
              style={[
                styles.chip,
                active && { backgroundColor: colors.primary, borderColor: colors.primary },
              ]}
            >
              <Text style={{ color: active ? colors.onPrimary : colors.text, fontWeight: "600" }}>
                {opt}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

export function StatusBadge({ value, testID }: { value: keyof typeof statusMap; testID?: string }) {
  const s = statusMap[value] || statusMap.rascunho;
  return (
    <View testID={testID} style={[styles.badge, { backgroundColor: s.bg }]}>
      <Text style={[styles.badgeTxt, { color: s.fg }]}>{s.label}</Text>
    </View>
  );
}

export function StepProgress({ step, total }: { step: number; total: number }) {
  return (
    <View style={{ paddingHorizontal: space.lg, paddingTop: space.md }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: 8 }}>
        <Text style={{ color: colors.textMuted, fontSize: fonts.size.sm }}>
          Etapa {step} de {total}
        </Text>
        <Text style={{ color: colors.primary, fontSize: fonts.size.sm, fontWeight: "700" }}>
          {Math.round((step / total) * 100)}%
        </Text>
      </View>
      <View style={styles.progressBar}>
        <View style={[styles.progressFill, { width: `${(step / total) * 100}%` }]} />
      </View>
    </View>
  );
}

export function EmptyState({ title, message, icon = "document-text-outline" }: { title: string; message: string; icon?: keyof typeof Ionicons.glyphMap }) {
  return (
    <View style={styles.empty}>
      <Ionicons name={icon} size={56} color={colors.textDim} />
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.emptyMsg}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  btn: {
    minHeight: 56,
    paddingHorizontal: space.lg,
    borderRadius: radii.md,
    borderWidth: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
  },
  btnTxt: { fontSize: fonts.size.md, fontWeight: "700" },
  label: {
    color: colors.textMuted,
    fontSize: fonts.size.sm,
    fontWeight: "600",
    marginBottom: 6,
    letterSpacing: 0.3,
    textTransform: "uppercase",
  },
  input: {
    minHeight: 52,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.md,
    paddingHorizontal: space.md,
    color: colors.text,
    fontSize: fonts.size.md,
  },
  selectBox: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  error: { color: colors.danger, marginTop: 4, fontSize: fonts.size.sm },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(10,10,10,0.55)",
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radii.xl,
    borderTopRightRadius: radii.xl,
    padding: space.lg,
    maxHeight: "70%",
  },
  sheetTitle: {
    color: colors.text,
    fontSize: fonts.size.lg,
    fontWeight: "700",
    marginBottom: space.md,
  },
  sheetItem: {
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: radii.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radii.pill,
    alignSelf: "flex-start",
  },
  badgeTxt: { fontSize: fonts.size.xs, fontWeight: "700", letterSpacing: 0.5 },
  progressBar: {
    height: 6,
    backgroundColor: colors.surfaceAlt,
    borderRadius: 3,
    overflow: "hidden",
  },
  progressFill: { height: "100%", backgroundColor: colors.primary, borderRadius: 3 },
  empty: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: space.xl,
  },
  emptyTitle: {
    color: colors.text,
    fontSize: fonts.size.lg,
    fontWeight: "700",
    marginTop: space.md,
  },
  emptyMsg: {
    color: colors.textMuted,
    fontSize: fonts.size.sm,
    textAlign: "center",
    marginTop: 6,
  },
});
