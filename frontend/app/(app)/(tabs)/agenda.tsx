import React, { useCallback, useEffect, useMemo, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, RefreshControl, ActivityIndicator, Alert, TextInput, Modal, Pressable, Linking, Platform } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { api, apiErrorMessage } from "../../../src/api";
import { useAuth } from "../../../src/auth";
import { useDraft, formatPlate } from "../../../src/draft";
import { useNotifications } from "../../../src/notifications";
import { colors, fonts, radii, shadow, space } from "../../../src/theme";

type Appt = {
  id: string; numero_os: string; cliente_nome: string; cliente_sobrenome: string;
  placa: string; empresa: string; endereco: string; scheduled_at: string;
  status: string; checklist_id?: string | null;
  vehicle_type?: string; vehicle_brand?: string; vehicle_model?: string; vehicle_year?: string;
  prioridade?: string; telefone?: string; tempo_estimado_min?: number;
  observacoes?: string; comissao?: number; delay_min?: number; penalty_amount?: number;
  refuse_reason?: string; accepted_at?: string | null; refused_at?: string | null;
};

type Period = "hoje" | "semana" | "mes";
type Status = "todas" | "novas" | "aceitas" | "feitas";

const BRL = (n?: number) => (n ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const dayKey = (iso: string) => { const d = new Date(iso); return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`; };
const isToday = (iso: string) => dayKey(iso) === dayKey(new Date().toISOString());
const isThisWeek = (iso: string) => {
  const d = new Date(iso);
  const now = new Date();
  const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - now.getDay() + (now.getDay() === 0 ? -6 : 1));
  const sunday = new Date(monday); sunday.setDate(monday.getDate() + 7);
  return d >= monday && d < sunday;
};
const isThisMonth = (iso: string) => { const d = new Date(iso); const n = new Date(); return d.getFullYear() === n.getFullYear() && d.getMonth() === n.getMonth(); };

const dataPtBr = () => {
  const d = new Date();
  const dias = ["Domingo","Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira","Sábado"];
  const meses = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
  return `${dias[d.getDay()]}, ${String(d.getDate()).padStart(2,"0")} de ${meses[d.getMonth()]}`;
};

export default function Agenda() {
  const router = useRouter();
  const { user } = useAuth();
  const { reset, set } = useDraft();
  const { newCount, markAllSeen } = useNotifications();
  const [items, setItems] = useState<Appt[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [period, setPeriod] = useState<Period>("hoje");
  const [statusTab, setStatusTab] = useState<Status>("todas");
  const [todayEarnings, setTodayEarnings] = useState<{ total: number; count: number }>({ total: 0, count: 0 });
  const [refuseFor, setRefuseFor] = useState<Appt | null>(null);
  const [refuseReason, setRefuseReason] = useState("");
  const [acting, setActing] = useState<string>("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [appts, earn] = await Promise.all([
        api.get<Appt[]>("/appointments"),
        api.get("/earnings/me", { params: { period: "day" } }).catch(() => ({ data: { total_net: 0, count: 0 } })),
      ]);
      setItems(appts.data);
      setTodayEarnings({ total: (earn.data as any).total_net || 0, count: (earn.data as any).count || 0 });
      markAllSeen();
    } catch (e) { setError(apiErrorMessage(e)); }
    finally { setLoading(false); setRefreshing(false); }
  }, [markAllSeen]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const filtered = useMemo(() => {
    let arr = items;
    if (period === "hoje") arr = arr.filter((a) => isToday(a.scheduled_at));
    else if (period === "semana") arr = arr.filter((a) => isThisWeek(a.scheduled_at));
    else arr = arr.filter((a) => isThisMonth(a.scheduled_at));
    if (statusTab === "novas") arr = arr.filter((a) => a.status === "agendado" && (a.delay_min || 0) <= 30);
    else if (statusTab === "aceitas") arr = arr.filter((a) => a.status === "aceita" || a.status === "em_andamento");
    else if (statusTab === "feitas") arr = arr.filter((a) => a.status === "concluido");
    return arr;
  }, [items, period, statusTab]);

  const counts = useMemo(() => {
    const periodArr = period === "hoje" ? items.filter((a) => isToday(a.scheduled_at))
      : period === "semana" ? items.filter((a) => isThisWeek(a.scheduled_at))
      : items.filter((a) => isThisMonth(a.scheduled_at));
    const todas = periodArr.length;
    const novas = periodArr.filter((a) => a.status === "agendado" && (a.delay_min || 0) <= 30).length;
    const aceitas = periodArr.filter((a) => a.status === "aceita" || a.status === "em_andamento").length;
    const feitas = periodArr.filter((a) => a.status === "concluido").length;
    return { todas, novas, aceitas, feitas };
  }, [items, period]);

  const headerStats = useMemo(() => {
    const hojeTotal = items.filter((a) => isToday(a.scheduled_at)).length;
    const hojeFeitas = items.filter((a) => isToday(a.scheduled_at) && a.status === "concluido").length;
    return { hojeTotal, hojeFeitas };
  }, [items]);

  const onAccept = async (a: Appt) => {
    setActing(a.id);
    try {
      await api.post(`/appointments/${a.id}/accept`, { notes: "" });
      await load();
    } catch (e: any) { Alert.alert("Erro", apiErrorMessage(e)); }
    finally { setActing(""); }
  };

  const onRefuse = async () => {
    if (!refuseFor || !refuseReason.trim()) { Alert.alert("Motivo obrigatório", "Informe um motivo para recusar."); return; }
    setActing(refuseFor.id);
    try {
      await api.post(`/appointments/${refuseFor.id}/refuse`, { reason: refuseReason.trim() });
      setRefuseFor(null); setRefuseReason("");
      await load();
    } catch (e: any) { Alert.alert("Erro", apiErrorMessage(e)); }
    finally { setActing(""); }
  };

  const openChecklist = (a: Appt) => {
    if (a.checklist_id) {
      router.push({ pathname: "/(app)/checklist/[id]", params: { id: a.checklist_id } });
      return;
    }
    reset();
    set({
      appointment_id: a.id,
      nome: a.cliente_nome,
      sobrenome: a.cliente_sobrenome,
      placa: formatPlate(a.placa),
      empresa: a.empresa,
      vehicle_type: (a.vehicle_type as any) || "",
      telefone: a.telefone || "",
    });
    router.push("/(app)/checklist/new");
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.brandBlack }} edges={["top"]}>
      {/* Dark brand header */}
      <View style={styles.brandHeader}>
        <View style={styles.brandRow}>
          <View style={styles.avatar}>
            <Text style={styles.avatarTxt}>{(user?.name || "T").charAt(0).toUpperCase()}</Text>
          </View>
          <View style={{ flex: 1, marginLeft: 12 }}>
            <Text style={styles.hello}>Olá, {user?.name?.split(" ")[0] || "Técnico"}</Text>
            <Text style={styles.logo}>VALE<Text style={{ color: colors.primary }}>TECK</Text></Text>
          </View>
          <View style={styles.onlinePill}>
            <View style={styles.onlineDot} />
            <Text style={styles.onlineTxt}>Online</Text>
          </View>
        </View>
        <View style={styles.statsRow}>
          <View style={styles.statsItem}>
            <Ionicons name="checkmark-circle" size={14} color={colors.success} />
            <Text style={styles.statsTxt}>{headerStats.hojeFeitas} feitas hoje</Text>
          </View>
          <Text style={styles.statsSep}>|</Text>
          <Text style={[styles.statsTxt, { color: colors.success, fontWeight: "800" }]}>{BRL(todayEarnings.total)}</Text>
          <Text style={styles.statsTxtMuted}>ganhos</Text>
          <Text style={styles.statsSep}>|</Text>
          <View style={styles.credPill}>
            <Ionicons name="shield-checkmark" size={12} color={colors.primary} />
            <Text style={styles.credTxt}>Credenciado</Text>
          </View>
        </View>
      </View>

      {/* Light content */}
      <ScrollView
        style={{ backgroundColor: colors.bg }}
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}
      >
        <View style={styles.sectionHeader}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <View style={styles.iconSq}><Ionicons name="calendar" size={18} color={colors.primary} /></View>
            <View>
              <Text style={styles.sectionTitle}>Minha Agenda</Text>
              <Text style={styles.sectionSub}>{dataPtBr()}</Text>
            </View>
          </View>
          <View style={{ flexDirection: "row", gap: 8 }}>
            <TouchableOpacity style={styles.roundBtn} onPress={() => { setRefreshing(true); load(); }} testID="refresh-btn">
              <Ionicons name="refresh" size={18} color={colors.text} />
            </TouchableOpacity>
          </View>
        </View>

        {/* 3 summary cards */}
        <View style={styles.summaryRow}>
          <View style={[styles.summaryCard, { backgroundColor: colors.surface }]}>
            <Text style={[styles.summaryValue, { color: colors.info }]}>{counts.todas}</Text>
            <Text style={styles.summaryLabel}>Agendadas</Text>
          </View>
          <View style={[styles.summaryCard, { backgroundColor: colors.surface }]}>
            <Text style={[styles.summaryValue, { color: colors.success }]}>{counts.feitas}</Text>
            <Text style={styles.summaryLabel}>Concluídas</Text>
          </View>
          <View style={[styles.summaryCard, { backgroundColor: colors.surface }]}>
            <Text style={[styles.summaryValue, { color: colors.success, fontSize: 18 }]}>{BRL(todayEarnings.total)}</Text>
            <Text style={styles.summaryLabel}>Ganhos</Text>
          </View>
        </View>

        {/* Period tabs */}
        <View style={styles.periodRow}>
          {(["hoje", "semana", "mes"] as Period[]).map((p) => (
            <TouchableOpacity
              key={p}
              testID={`period-${p}`}
              onPress={() => setPeriod(p)}
              style={[styles.periodTab, period === p && styles.periodTabActive]}
              activeOpacity={0.85}
            >
              <Ionicons name={p === "hoje" ? "time-outline" : "calendar-outline"} size={16} color={period === p ? colors.onPrimary : colors.textMuted} />
              <Text style={[styles.periodTxt, period === p && styles.periodTxtActive]}>
                {p === "hoje" ? "Hoje" : p === "semana" ? "Esta Semana" : "Este Mês"}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Status sub-tabs */}
        <View style={styles.statusRow}>
          {([
            { id: "todas", label: "Todas", count: counts.todas },
            { id: "novas", label: "Novas", count: counts.novas },
            { id: "aceitas", label: "Aceitas", count: counts.aceitas },
            { id: "feitas", label: "Feitas", count: counts.feitas },
          ] as { id: Status; label: string; count: number }[]).map((s) => (
            <TouchableOpacity
              key={s.id}
              testID={`status-${s.id}`}
              onPress={() => setStatusTab(s.id)}
              style={[styles.statusTab, statusTab === s.id && styles.statusTabActive]}
              activeOpacity={0.85}
            >
              <Text style={[styles.statusTxt, statusTab === s.id && styles.statusTxtActive]}>{s.label}</Text>
              <View style={[styles.statusBadge, statusTab === s.id && styles.statusBadgeActive]}>
                <Text style={[styles.statusBadgeTxt, statusTab === s.id && styles.statusBadgeTxtActive]}>{s.count}</Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {/* Section: Ordens */}
        <View style={styles.ordersHeader}>
          <Ionicons name="triangle-outline" size={14} color={colors.textMuted} style={{ transform: [{ rotate: "0deg" }] }} />
          <Text style={styles.ordersTitle}>Ordens {period === "hoje" ? "de hoje" : period === "semana" ? "da semana" : "do mês"}</Text>
          <View style={styles.ordersCount}><Text style={styles.ordersCountTxt}>{filtered.length} OS</Text></View>
        </View>

        {loading ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 40 }} />
        ) : filtered.length === 0 ? (
          <View style={styles.empty}>
            <Ionicons name="calendar-outline" size={40} color={colors.textDim} />
            <Text style={styles.emptyTitle}>Sem ordens aqui</Text>
            <Text style={styles.emptyMsg}>Nenhuma OS {period === "hoje" ? "para hoje" : period === "semana" ? "esta semana" : "este mês"} no filtro {statusTab}.</Text>
          </View>
        ) : (
          filtered.map((a) => <OSCard key={a.id} appt={a} onAccept={onAccept} onRefuseRequest={(x) => { setRefuseFor(x); setRefuseReason(""); }} onOpen={openChecklist} acting={acting === a.id} />)
        )}
      </ScrollView>

      {/* Modal recusar */}
      <Modal visible={!!refuseFor} transparent animationType="fade" onRequestClose={() => setRefuseFor(null)}>
        <Pressable style={styles.modalBg} onPress={() => setRefuseFor(null)}>
          <Pressable style={styles.modalCard} onPress={(e) => e.stopPropagation()}>
            <Text style={styles.modalTitle}>Recusar OS</Text>
            <Text style={styles.modalSub}>{refuseFor?.numero_os} — {refuseFor?.empresa}</Text>
            <Text style={styles.modalLabel}>Motivo da recusa</Text>
            <TextInput
              testID="refuse-reason"
              value={refuseReason}
              onChangeText={setRefuseReason}
              placeholder="Informe o motivo..."
              placeholderTextColor={colors.textDim}
              multiline
              style={styles.modalInput}
            />
            <View style={{ flexDirection: "row", gap: 10, marginTop: 16 }}>
              <TouchableOpacity style={[styles.modalBtn, styles.modalBtnSec]} onPress={() => setRefuseFor(null)}>
                <Text style={styles.modalBtnSecTxt}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity testID="confirm-refuse" style={[styles.modalBtn, styles.modalBtnDanger]} onPress={onRefuse} disabled={!refuseReason.trim()}>
                <Text style={styles.modalBtnDangerTxt}>Confirmar recusa</Text>
              </TouchableOpacity>
            </View>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

function OSCard({ appt, onAccept, onRefuseRequest, onOpen, acting }: { appt: Appt; onAccept: (a: Appt) => void; onRefuseRequest: (a: Appt) => void; onOpen: (a: Appt) => void; acting: boolean }) {
  const dt = new Date(appt.scheduled_at);
  const isMoto = appt.vehicle_type === "moto";
  const delay = appt.delay_min || 0;
  const critical = delay > 120;
  const late = delay > 30;
  const statusNovo = appt.status === "agendado";
  const statusAceita = appt.status === "aceita" || appt.status === "em_andamento";
  const statusFeita = appt.status === "concluido";
  const statusRecusada = appt.status === "recusada";
  const barColor = statusRecusada ? colors.danger : statusFeita ? colors.success : critical ? colors.danger : late ? colors.warning : statusAceita ? colors.info : colors.primary;

  return (
    <View style={[styles.osCard, { borderLeftColor: barColor }]} testID={`os-card-${appt.numero_os}`}>
      <View style={{ flex: 1, padding: space.md }}>
        {/* Top meta */}
        <View style={styles.osTopRow}>
          <View style={[styles.timeChip, late && { backgroundColor: colors.dangerBg, borderColor: colors.danger }]}>
            <Ionicons name="time-outline" size={12} color={late ? colors.danger : colors.text} />
            <Text style={[styles.timeTxt, late && { color: colors.danger }]}>{dt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</Text>
          </View>
          {delay > 0 && (
            <View style={[styles.delayChip, critical && { backgroundColor: colors.danger }, !critical && { backgroundColor: colors.warning }]}>
              <Text style={styles.delayTxt}>+{delay} min</Text>
            </View>
          )}
          <View style={styles.serviceChip}>
            <MaterialCommunityIcons name="wrench-outline" size={14} color={colors.info} />
            <Text style={styles.serviceTxt}>Instalação</Text>
          </View>
          <View style={{ flex: 1 }} />
          <Text style={styles.osNum}>{appt.numero_os}</Text>
        </View>

        {/* Delay alert */}
        {critical && (
          <View style={styles.delayAlert} testID={`delay-alert-${appt.numero_os}`}>
            <Ionicons name="warning" size={18} color={colors.danger} />
            <View style={{ flex: 1 }}>
              <Text style={styles.delayAlertTitle}>Atraso Crítico — {delay} min</Text>
              <Text style={styles.delayAlertSub}>Penalidade de {BRL(appt.penalty_amount)} pode ser aplicada ao check-in</Text>
            </View>
          </View>
        )}

        {/* Cliente */}
        <Text style={styles.cliente}>{appt.cliente_nome} {appt.cliente_sobrenome}</Text>

        {/* Veículo */}
        <View style={styles.vehicleRow}>
          {isMoto ? <MaterialCommunityIcons name="motorbike" size={16} color={colors.textMuted} /> : <Ionicons name="car-sport-outline" size={16} color={colors.textMuted} />}
          <Text style={styles.vehicleTxt} numberOfLines={1}>
            {[appt.vehicle_brand, appt.vehicle_model, appt.vehicle_year].filter(Boolean).join(" ") || (isMoto ? "Motocicleta" : "Veículo")}
          </Text>
          <View style={styles.plate}>
            <Text style={styles.plateTxt}>{formatPlate(appt.placa)}</Text>
          </View>
        </View>

        {/* Endereço */}
        <TouchableOpacity
          testID={`maps-${appt.numero_os}`}
          onPress={() => {
            const q = encodeURIComponent(appt.endereco);
            const url = Platform.OS === "ios"
              ? `http://maps.apple.com/?q=${q}`
              : `https://www.google.com/maps/search/?api=1&query=${q}`;
            Linking.openURL(url).catch(() => {});
          }}
          style={styles.addressRow}
          activeOpacity={0.7}
        >
          <Ionicons name="location-outline" size={16} color={colors.info} />
          <Text style={[styles.addressTxt, { color: colors.info, textDecorationLine: "underline" }]} numberOfLines={2}>{appt.endereco}</Text>
          <Ionicons name="open-outline" size={14} color={colors.info} />
        </TouchableOpacity>

        {/* Quick actions: Waze / Telefone */}
        <View style={styles.quickRow}>
          <TouchableOpacity
            testID={`waze-${appt.numero_os}`}
            onPress={() => {
              const q = encodeURIComponent(appt.endereco);
              Linking.openURL(`https://waze.com/ul?q=${q}&navigate=yes`).catch(() => {});
            }}
            style={styles.quickBtn}
          >
            <Ionicons name="navigate-circle-outline" size={18} color={colors.info} />
            <Text style={styles.quickTxt}>Waze</Text>
          </TouchableOpacity>
          {!!appt.telefone && (
            <TouchableOpacity
              testID={`call-${appt.numero_os}`}
              onPress={() => Linking.openURL(`tel:${appt.telefone!.replace(/\D/g, "")}`).catch(() => {})}
              style={styles.quickBtn}
            >
              <Ionicons name="call-outline" size={18} color={colors.success} />
              <Text style={[styles.quickTxt, { color: colors.success }]}>Ligar</Text>
            </TouchableOpacity>
          )}
          {!!appt.telefone && (
            <TouchableOpacity
              testID={`whats-${appt.numero_os}`}
              onPress={() => {
                const phone = appt.telefone!.replace(/\D/g, "");
                const msg = encodeURIComponent(`Olá ${appt.cliente_nome}, aqui é da Valeteck. Estou a caminho para a instalação do rastreador (${appt.numero_os}).`);
                Linking.openURL(`https://wa.me/55${phone}?text=${msg}`).catch(() => {});
              }}
              style={styles.quickBtn}
            >
              <Ionicons name="logo-whatsapp" size={18} color="#25D366" />
              <Text style={[styles.quickTxt, { color: "#25D366" }]}>WhatsApp</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Comissão */}
        <View style={styles.commRow}>
          <Text style={styles.commLabel}>Comissão</Text>
          <Text style={styles.commValue} testID={`comm-${appt.numero_os}`}>{BRL(appt.comissao)}</Text>
        </View>

        {/* Observações */}
        {!!appt.observacoes && (
          <View style={styles.noteCard}>
            <Ionicons name="alert-circle" size={16} color={colors.warning} />
            <Text style={styles.noteTxt} numberOfLines={3}>{appt.observacoes}</Text>
          </View>
        )}

        {/* Recusada info */}
        {statusRecusada && (
          <View style={styles.refusedCard}>
            <Ionicons name="close-circle" size={16} color={colors.danger} />
            <Text style={styles.refusedTxt}>Recusada{appt.refuse_reason ? `: ${appt.refuse_reason}` : ""}</Text>
          </View>
        )}

        {/* Actions */}
        {statusNovo && (
          <View style={styles.actionsRow}>
            <TouchableOpacity testID={`refuse-${appt.numero_os}`} disabled={acting} onPress={() => onRefuseRequest(appt)} style={[styles.btnRefuse]}>
              <Ionicons name="close" size={18} color={colors.danger} />
              <Text style={styles.btnRefuseTxt}>Recusar</Text>
            </TouchableOpacity>
            <TouchableOpacity testID={`accept-${appt.numero_os}`} disabled={acting} onPress={() => onAccept(appt)} style={[styles.btnAccept]}>
              {acting ? <ActivityIndicator color={colors.onPrimary} /> : <>
                <Ionicons name="checkmark" size={20} color={colors.onPrimary} />
                <Text style={styles.btnAcceptTxt}>Aceitar OS</Text>
              </>}
            </TouchableOpacity>
          </View>
        )}
        {(statusAceita || statusFeita) && (
          <TouchableOpacity testID={`open-${appt.numero_os}`} onPress={() => onOpen(appt)} style={[styles.btnOpen]}>
            <Ionicons name={statusFeita ? "eye-outline" : "clipboard-outline"} size={20} color={colors.onPrimary} />
            <Text style={styles.btnOpenTxt}>{statusFeita ? "Ver checklist" : "Iniciar checklist"}</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  brandHeader: { backgroundColor: colors.brandBlack, paddingBottom: space.sm, paddingHorizontal: space.lg, paddingTop: space.sm, borderBottomLeftRadius: 20, borderBottomRightRadius: 20 },
  brandRow: { flexDirection: "row", alignItems: "center", marginBottom: 12 },
  avatar: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  avatarTxt: { color: colors.onPrimary, fontWeight: "900", fontSize: fonts.size.lg },
  hello: { color: colors.textDim, fontSize: fonts.size.xs, fontWeight: "600" },
  logo: { color: colors.onDark, fontSize: fonts.size.lg, fontWeight: "900", letterSpacing: 1 },
  onlinePill: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: "rgba(16,185,129,0.15)", borderWidth: 1, borderColor: colors.success, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  onlineDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.success },
  onlineTxt: { color: colors.success, fontSize: fonts.size.xs, fontWeight: "700" },
  statsRow: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 8 },
  statsItem: { flexDirection: "row", alignItems: "center", gap: 4 },
  statsTxt: { color: colors.onDark, fontSize: fonts.size.xs, fontWeight: "600" },
  statsTxtMuted: { color: colors.textDim, fontSize: fonts.size.xs },
  statsSep: { color: colors.textDim, fontSize: fonts.size.sm },
  credPill: { flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: "rgba(255,212,0,0.15)", borderWidth: 1, borderColor: colors.primary, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999 },
  credTxt: { color: colors.primary, fontSize: 11, fontWeight: "800" },
  content: { padding: space.lg, paddingBottom: 40 },
  sectionHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: space.md },
  iconSq: { width: 36, height: 36, borderRadius: 8, backgroundColor: colors.primary + "22", alignItems: "center", justifyContent: "center" },
  sectionTitle: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "900" },
  sectionSub: { color: colors.textMuted, fontSize: fonts.size.xs },
  roundBtn: { width: 38, height: 38, borderRadius: 19, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: "center", justifyContent: "center" },
  summaryRow: { flexDirection: "row", gap: 10, marginBottom: space.md },
  summaryCard: { flex: 1, borderRadius: radii.md, padding: space.md, alignItems: "center", ...shadow.sm },
  summaryValue: { fontSize: 24, fontWeight: "900" },
  summaryLabel: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 4, fontWeight: "600" },
  periodRow: { flexDirection: "row", gap: 8, marginBottom: space.sm },
  periodTab: { flex: 1, paddingVertical: 12, borderRadius: radii.pill, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  periodTabActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  periodTxt: { color: colors.textMuted, fontWeight: "700", fontSize: fonts.size.sm },
  periodTxtActive: { color: colors.onPrimary },
  statusRow: { flexDirection: "row", gap: 8, marginBottom: space.md },
  statusTab: { flex: 1, paddingVertical: 10, borderRadius: radii.md, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  statusTabActive: { backgroundColor: colors.brandBlack, borderColor: colors.brandBlack },
  statusTxt: { color: colors.textMuted, fontWeight: "700", fontSize: fonts.size.xs },
  statusTxtActive: { color: colors.primary },
  statusBadge: { backgroundColor: colors.surfaceAlt, paddingHorizontal: 6, paddingVertical: 1, borderRadius: 999, minWidth: 22, alignItems: "center" },
  statusBadgeActive: { backgroundColor: colors.primary },
  statusBadgeTxt: { color: colors.textMuted, fontSize: 11, fontWeight: "800" },
  statusBadgeTxtActive: { color: colors.onPrimary },
  ordersHeader: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: space.sm },
  ordersTitle: { color: colors.text, fontSize: fonts.size.md, fontWeight: "800", flex: 1 },
  ordersCount: { backgroundColor: colors.info + "22", paddingHorizontal: 10, paddingVertical: 3, borderRadius: 999 },
  ordersCountTxt: { color: colors.info, fontWeight: "800", fontSize: fonts.size.xs },
  osCard: { backgroundColor: colors.surface, borderRadius: radii.lg, borderLeftWidth: 5, marginBottom: space.md, ...shadow.sm },
  osTopRow: { flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap", marginBottom: 8 },
  timeChip: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surfaceAlt },
  timeTxt: { color: colors.text, fontSize: fonts.size.xs, fontWeight: "700" },
  delayChip: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999 },
  delayTxt: { color: "#fff", fontSize: 11, fontWeight: "900" },
  serviceChip: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, backgroundColor: colors.infoBg },
  serviceTxt: { color: colors.info, fontSize: fonts.size.xs, fontWeight: "700" },
  osNum: { color: colors.textMuted, fontWeight: "800", fontSize: 11 },
  delayAlert: { flexDirection: "row", alignItems: "flex-start", gap: 10, backgroundColor: colors.dangerBg, borderWidth: 1, borderColor: colors.danger + "55", padding: 10, borderRadius: radii.md, marginBottom: 10 },
  delayAlertTitle: { color: colors.danger, fontWeight: "900", fontSize: fonts.size.sm },
  delayAlertSub: { color: colors.danger, fontSize: 11, marginTop: 2, opacity: 0.9 },
  cliente: { color: colors.text, fontWeight: "900", fontSize: fonts.size.lg, marginBottom: 6 },
  vehicleRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 6, flexWrap: "wrap" },
  vehicleTxt: { color: colors.text, fontSize: fonts.size.sm, fontWeight: "600", flexShrink: 1 },
  plate: { backgroundColor: colors.primary, paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, borderWidth: 1, borderColor: colors.primaryDark },
  plateTxt: { color: colors.onPrimary, fontWeight: "900", letterSpacing: 1, fontSize: fonts.size.sm },
  addressRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10 },
  addressTxt: { color: colors.textMuted, fontSize: fonts.size.sm, flex: 1 },
  quickRow: { flexDirection: "row", gap: 8, marginBottom: 10 },
  quickBtn: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 4, paddingVertical: 8, borderRadius: radii.sm, backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border },
  quickTxt: { color: colors.info, fontWeight: "700", fontSize: fonts.size.xs },
  commRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingTop: 10, borderTopWidth: 1, borderTopColor: colors.divider },
  commLabel: { color: colors.textMuted, fontSize: fonts.size.sm, fontWeight: "600" },
  commValue: { color: colors.success, fontSize: fonts.size.xl, fontWeight: "900" },
  noteCard: { flexDirection: "row", alignItems: "flex-start", gap: 8, backgroundColor: colors.warningBg, padding: 10, borderRadius: radii.sm, marginTop: 10 },
  noteTxt: { color: "#92400E", fontSize: fonts.size.sm, flex: 1, fontWeight: "600" },
  refusedCard: { flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: colors.dangerBg, padding: 10, borderRadius: radii.sm, marginTop: 10 },
  refusedTxt: { color: colors.danger, fontSize: fonts.size.sm, flex: 1, fontWeight: "600" },
  actionsRow: { flexDirection: "row", gap: 10, marginTop: 14 },
  btnRefuse: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, paddingVertical: 14, borderRadius: radii.md, borderWidth: 1, borderColor: colors.danger, backgroundColor: colors.dangerBg },
  btnRefuseTxt: { color: colors.danger, fontWeight: "900", fontSize: fonts.size.md },
  btnAccept: { flex: 1.5, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, paddingVertical: 14, borderRadius: radii.md, backgroundColor: colors.primary },
  btnAcceptTxt: { color: colors.onPrimary, fontWeight: "900", fontSize: fonts.size.md },
  btnOpen: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingVertical: 14, borderRadius: radii.md, backgroundColor: colors.brandBlack, marginTop: 14 },
  btnOpenTxt: { color: colors.primary, fontWeight: "900", fontSize: fonts.size.md },
  empty: { alignItems: "center", padding: space.xl },
  emptyTitle: { color: colors.text, fontWeight: "800", marginTop: 10, fontSize: fonts.size.md },
  emptyMsg: { color: colors.textMuted, fontSize: fonts.size.sm, textAlign: "center", marginTop: 4 },
  modalBg: { flex: 1, backgroundColor: "rgba(10,10,10,0.55)", alignItems: "center", justifyContent: "center", padding: 20 },
  modalCard: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: 20, width: "100%", maxWidth: 420 },
  modalTitle: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "900" },
  modalSub: { color: colors.textMuted, fontSize: fonts.size.sm, marginBottom: 14 },
  modalLabel: { color: colors.textMuted, fontSize: fonts.size.xs, fontWeight: "700", textTransform: "uppercase", marginBottom: 6 },
  modalInput: { backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, padding: 12, color: colors.text, fontSize: fonts.size.md, minHeight: 90, textAlignVertical: "top" },
  modalBtn: { flex: 1, paddingVertical: 14, borderRadius: radii.md, alignItems: "center" },
  modalBtnSec: { backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border },
  modalBtnSecTxt: { color: colors.text, fontWeight: "800" },
  modalBtnDanger: { backgroundColor: colors.danger },
  modalBtnDangerTxt: { color: "#fff", fontWeight: "900" },
});
