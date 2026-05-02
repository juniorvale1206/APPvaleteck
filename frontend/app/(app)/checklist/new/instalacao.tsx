import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, KeyboardAvoidingView, Platform, Alert } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Btn, Field, MultiSelect, Select, StepProgress } from "../../../../src/components";
import { useDraft } from "../../../../src/draft";
import { api } from "../../../../src/api";
import { SLABadge } from "../../../../src/SLABadge";
import { SLATimerCard } from "../../../../src/SLATimerCard";
import { ServiceTypePicker, type ServiceTypeDef } from "../../../../src/ServiceTypePicker";
import { useAuth } from "../../../../src/auth";
import BarcodeScanner from "../../../../src/scanner";
import { RemovedEquipmentsSection } from "../../../../src/RemovedEquipmentsSection";
import { colors, fonts, radii, space } from "../../../../src/theme";

function Chip({ label, active, onPress, testID }: { label: string; active: boolean; onPress: () => void; testID?: string }) {
  return (
    <TouchableOpacity testID={testID} onPress={onPress} style={[styles.chip, active && { backgroundColor: colors.primary, borderColor: colors.primary }]}>
      <Text style={{ color: active ? colors.onPrimary : colors.text, fontWeight: "700" }}>{label}</Text>
    </TouchableOpacity>
  );
}

function voltageStatus(v: number | null) {
  if (v === null || isNaN(v)) return { color: colors.textDim, label: "" };
  if (v >= 12.4) return { color: colors.success, label: "OK" };
  if (v >= 11.8) return { color: colors.warning, label: "Atenção" };
  return { color: colors.danger, label: "Baixa" };
}

export default function StepInstalacao() {
  const router = useRouter();
  const { draft, set } = useDraft();
  const { user } = useAuth();
  const [companies, setCompanies] = useState<string[]>([]);
  const [equipments, setEquipments] = useState<string[]>([]);
  const [accessories, setAccessories] = useState<string[]>([]);
  const [serviceTypes, setServiceTypes] = useState<string[]>([]);
  const [batteryStates, setBatteryStates] = useState<string[]>([]);
  const [techProblems, setTechProblems] = useState<string[]>([]);
  const [serviceDef, setServiceDef] = useState<ServiceTypeDef | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [scanMode, setScanMode] = useState<null | "imei" | "iccid">(null);

  useEffect(() => {
    (async () => {
      try {
        const [c, e, a, s, b, p] = await Promise.all([
          api.get("/reference/companies"),
          api.get("/reference/equipments"),
          api.get("/reference/accessories", { params: draft.vehicle_type ? { vehicle_type: draft.vehicle_type } : {} }),
          api.get("/reference/service-types"),
          api.get("/reference/battery-states"),
          api.get("/reference/problems"),
        ]);
        setCompanies(c.data.companies);
        setEquipments(e.data.equipments);
        setAccessories(a.data.accessories);
        setServiceTypes(s.data.service_types);
        setBatteryStates(b.data.battery_states);
        setTechProblems(p.data.technician || []);
      } catch {}
    })();
  }, [draft.vehicle_type]);

  const next = () => {
    const er: Record<string, string> = {};
    if (!draft.empresa) er.empresa = "Obrigatório";
    if (!draft.equipamento) er.equipamento = "Obrigatório";
    if (draft.imei && !/^\d{15}$/.test(draft.imei)) er.imei = "IMEI deve ter 15 dígitos";
    setErrors(er);
    if (Object.keys(er).length) return;
    router.push("/(app)/checklist/new/evidencias");
  };

  // v14 Fase 3A — Envia Checklist Inicial ao servidor e navega para /execucao
  const sendInitialAndExecute = async () => {
    const er: Record<string, string> = {};
    if (!draft.service_type_code) er.service_type_code = "Selecione o tipo de serviço";
    if (!draft.empresa) er.empresa = "Obrigatório";
    if (!draft.equipamento) er.equipamento = "Obrigatório";
    if (!draft.nome || !draft.placa) er.nome = "Preencha Cliente na etapa anterior";
    setErrors(er);
    if (Object.keys(er).length) {
      Alert.alert("Campos obrigatórios", Object.values(er).join("\n"));
      return;
    }
    try {
      // 1) Salva o rascunho no servidor
      const base = {
        status: "rascunho",
        nome: draft.nome, sobrenome: draft.sobrenome, cpf: draft.cpf,
        placa: draft.placa, telefone: draft.telefone, obs_iniciais: draft.obs_iniciais,
        problems_client: draft.problems_client, problems_client_other: draft.problems_client_other,
        empresa: draft.empresa, equipamento: draft.equipamento,
        tipo_atendimento: draft.tipo_atendimento || "Instalação",
        vehicle_type: draft.vehicle_type, vehicle_brand: draft.vehicle_brand,
        vehicle_model: draft.vehicle_model, vehicle_year: draft.vehicle_year,
        vehicle_color: draft.vehicle_color, vehicle_vin: draft.vehicle_vin,
        acessorios: draft.acessorios,
        battery_state: draft.battery_state,
        battery_voltage: voltageNum,
        imei: draft.imei, iccid: draft.iccid,
        obs_tecnicas: draft.obs_tecnicas,
        service_type_code: draft.service_type_code,
        photos: [],
      };
      const { data: created } = await api.post<any>("/checklists", base);
      // 2) Inicia o SLA server-side
      await api.post(`/checklists/${created.id}/send-initial`, {
        service_type_code: draft.service_type_code,
      });
      // 3) Vai para tela de execução
      router.replace({ pathname: "/(app)/checklist/execucao/[id]", params: { id: created.id } });
    } catch (e: any) {
      Alert.alert("Erro", e?.response?.data?.detail || e?.message || "Falha ao enviar checklist inicial");
    }
  };

  const voltageNum = draft.battery_voltage ? parseFloat(draft.battery_voltage.replace(",", ".")) : null;
  const vs = voltageStatus(voltageNum);
  const imeiValid = draft.imei.length === 15 && /^\d+$/.test(draft.imei);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="back-btn" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Instalação</Text>
        <SLABadge compact />
      </View>
      <StepProgress step={3} total={6} />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          {/* v14 — Motor de Comissionamento: cronômetro + tipo de serviço oficial */}
          <SLATimerCard serviceDef={serviceDef} />
          <ServiceTypePicker
            testID="service-type-picker"
            value={draft.service_type_code}
            level={user?.level || undefined}
            onChange={(code, def) => {
              set({ service_type_code: code });
              setServiceDef(def);
            }}
          />

          <Text style={styles.section}>Dados da instalação</Text>
          <Select testID="select-empresa" label="Empresa / Parceiro" required value={draft.empresa as any} options={companies} onChange={(v) => set({ empresa: v })} error={errors.empresa} />
          <Select testID="select-equipamento" label="Equipamento principal" required value={draft.equipamento as any} options={equipments} onChange={(v) => set({ equipamento: v })} error={errors.equipamento} />
          <Select testID="select-tipo" label="Tipo de atendimento" value={draft.tipo_atendimento as any} options={serviceTypes} onChange={(v) => set({ tipo_atendimento: v })} />

          {/* FASE 3 — Equipamentos Retirados (aparece em Retirada/Manutenção/Garantia) */}
          {["Retirada", "Manutenção", "Garantia"].includes(draft.tipo_atendimento) && (
            <RemovedEquipmentsSection
              items={draft.removed_equipments}
              onChange={(v) => set({ removed_equipments: v })}
            />
          )}

          <Text style={[styles.section, { marginTop: space.md }]}>Identificação do dispositivo</Text>
          <Text style={styles.helper}>Escaneie ou digite o IMEI e ICCID do rastreador</Text>

          <View style={styles.scanRow}>
            <View style={{ flex: 1 }}>
              <Field
                testID="imei-input"
                label="IMEI (15 dígitos)"
                value={draft.imei}
                onChangeText={(v) => set({ imei: v.replace(/\D/g, "").slice(0, 15) })}
                keyboardType="number-pad"
                placeholder="123456789012345"
                error={errors.imei}
                maxLength={15}
              />
            </View>
            <TouchableOpacity testID="scan-imei" style={[styles.scanBtn, imeiValid && styles.scanBtnValid]} onPress={() => setScanMode("imei")}>
              <Ionicons name={imeiValid ? "checkmark" : "scan"} size={22} color={imeiValid ? colors.success : colors.onPrimary} />
            </TouchableOpacity>
          </View>

          <View style={styles.scanRow}>
            <View style={{ flex: 1 }}>
              <Field
                testID="iccid-input"
                label="ICCID do chip"
                value={draft.iccid}
                onChangeText={(v) => set({ iccid: v.replace(/\s/g, "").slice(0, 22) })}
                placeholder="89550100..."
                maxLength={22}
              />
            </View>
            <TouchableOpacity testID="scan-iccid" style={styles.scanBtn} onPress={() => setScanMode("iccid")}>
              <Ionicons name="scan" size={22} color={colors.onPrimary} />
            </TouchableOpacity>
          </View>

          <Text style={[styles.section, { marginTop: space.md }]}>Acessórios e observações</Text>
          <MultiSelect testID="select-acessorios" label={`Acessórios instalados${draft.vehicle_type ? ` (${draft.vehicle_type})` : ""}`} values={draft.acessorios} options={accessories} onChange={(v) => set({ acessorios: v })} />

          <Text style={[styles.section, { marginTop: space.md }]}>Bateria do veículo</Text>
          <Text style={styles.label}>Estado da bateria</Text>
          <View style={styles.chipRow}>
            {batteryStates.map((b) => (
              <Chip key={b} label={b} active={draft.battery_state === b} onPress={() => set({ battery_state: draft.battery_state === b ? "" : b })} testID={`battery-${b}`} />
            ))}
          </View>
          <View style={{ marginTop: space.md }}>
            <Field testID="battery-voltage" label="Tensão medida (V)" value={draft.battery_voltage} onChangeText={(v) => set({ battery_voltage: v.replace(/[^0-9.,]/g, "") })} keyboardType="decimal-pad" placeholder="ex: 12.6" maxLength={5} />
            {voltageNum !== null && !isNaN(voltageNum) && (
              <View style={[styles.voltBadge, { backgroundColor: vs.color + "22", borderColor: vs.color }]} testID="voltage-status">
                <Ionicons name={voltageNum >= 12.4 ? "checkmark-circle" : voltageNum >= 11.8 ? "alert-circle" : "close-circle"} size={16} color={vs.color} />
                <Text style={{ color: vs.color, fontWeight: "800", marginLeft: 6 }}>{voltageNum.toFixed(1)}V — {vs.label}</Text>
              </View>
            )}
          </View>

          <Text style={[styles.section, { marginTop: space.lg }]}>Problemas constatados pelo técnico</Text>
          <MultiSelect testID="problems-technician" label="Problemas identificados" values={draft.problems_technician} options={techProblems} onChange={(v) => set({ problems_technician: v })} />
          <Field testID="problems-technician-other" label="Outros (texto livre)" value={draft.problems_technician_other} onChangeText={(v) => set({ problems_technician_other: v })} multiline numberOfLines={2} style={{ minHeight: 70, textAlignVertical: "top" } as any} placeholder="Outras constatações..." />
          <Field testID="instal-obs" label="Observações técnicas" value={draft.obs_tecnicas} onChangeText={(v) => set({ obs_tecnicas: v })} multiline numberOfLines={3} style={{ minHeight: 90, textAlignVertical: "top" } as any} placeholder="Opcional" />
        </ScrollView>
      </KeyboardAvoidingView>
      <View style={styles.footer}>
        {draft.service_type_code ? (
          <Btn
            testID="btn-send-initial"
            title="🚀 Enviar Checklist Inicial (inicia SLA)"
            icon="rocket-outline"
            variant="primary"
            onPress={sendInitialAndExecute}
          />
        ) : (
          <Btn testID="step-next" title="Continuar" icon="arrow-forward" onPress={next} />
        )}
      </View>

      <BarcodeScanner
        visible={scanMode !== null}
        onClose={() => setScanMode(null)}
        onScan={(v) => {
          if (scanMode === "imei") {
            const clean = v.replace(/\D/g, "").slice(0, 15);
            set({ imei: clean });
          } else if (scanMode === "iccid") {
            set({ iccid: v.replace(/\s/g, "").slice(0, 22) });
          }
          setScanMode(null);
        }}
        title={scanMode === "imei" ? "Scanner IMEI" : "Scanner ICCID"}
        hint={scanMode === "imei" ? "Aponte para o código de barras do IMEI (15 dígitos)" : "Aponte para o ICCID do chip SIM"}
        validate={scanMode === "imei" ? (v) => /^\d{15}$/.test(v.replace(/\D/g, "").slice(0, 15)) : undefined}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingTop: space.sm, paddingBottom: space.xs },
  title: { color: colors.text, fontWeight: "800", fontSize: fonts.size.lg },
  content: { padding: space.lg, paddingBottom: 100 },
  section: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "800", marginBottom: space.md },
  helper: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: -10, marginBottom: space.md },
  label: { color: colors.textMuted, fontSize: fonts.size.sm, fontWeight: "600", marginBottom: 6, letterSpacing: 0.3, textTransform: "uppercase" },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { paddingHorizontal: 14, paddingVertical: 10, borderRadius: radii.pill, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface },
  voltBadge: { flexDirection: "row", alignItems: "center", paddingHorizontal: 12, paddingVertical: 8, borderRadius: radii.md, borderWidth: 1, alignSelf: "flex-start", marginTop: 8 },
  scanRow: { flexDirection: "row", alignItems: "flex-end", gap: 10, marginBottom: space.md },
  scanBtn: { backgroundColor: colors.primary, width: 52, height: 52, borderRadius: radii.md, alignItems: "center", justifyContent: "center", marginBottom: 16 },
  scanBtnValid: { backgroundColor: "#143A22", borderWidth: 1, borderColor: colors.success },
  footer: { padding: space.lg, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.bg },
});
