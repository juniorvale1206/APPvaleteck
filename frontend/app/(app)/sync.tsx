import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, Alert } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useSync, type QueueItem } from "../../src/sync";
import { colors, fonts, radii, shadow, space } from "../../src/theme";

const BRL = (n?: number) => (n ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export default function SyncQueueScreen() {
  const router = useRouter();
  const { queue, online, syncing, syncNow, removeItem } = useSync();
  const [acting, setActing] = useState(false);

  const onSync = async () => { setActing(true); try { await syncNow(); } finally { setActing(false); } };

  const confirmRemove = (item: QueueItem) => {
    Alert.alert("Descartar item?", `${item.numero_local} será removido permanentemente.`, [
      { text: "Cancelar", style: "cancel" },
      { text: "Descartar", style: "destructive", onPress: () => removeItem(item.id) },
    ]);
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="sync-back" onPress={() => router.back()}><Ionicons name="arrow-back" size={26} color={colors.text} /></TouchableOpacity>
        <Text style={styles.title}>Fila de sincronização</Text>
        <View style={{ width: 26 }} />
      </View>

      <View style={[styles.statusBar, { backgroundColor: online ? colors.successBg : colors.warningBg }]}>
        <Ionicons name={online ? "cloud-done" : "cloud-offline"} size={18} color={online ? colors.success : colors.warning} />
        <Text style={[styles.statusTxt, { color: online ? colors.success : colors.warning }]}>
          {online ? "Online — pronto para sincronizar" : "Modo offline — será sincronizado quando a conexão voltar"}
        </Text>
      </View>

      <View style={{ padding: space.lg }}>
        <View style={styles.summary}>
          <View style={styles.sumItem}>
            <Text style={styles.sumVal}>{queue.length}</Text>
            <Text style={styles.sumLabel}>Pendentes</Text>
          </View>
          <View style={styles.sumItem}>
            <Text style={[styles.sumVal, { color: colors.danger }]}>{queue.filter((q) => q.status === "failed").length}</Text>
            <Text style={styles.sumLabel}>Falharam</Text>
          </View>
          <TouchableOpacity
            testID="sync-now"
            disabled={!online || queue.length === 0 || acting}
            onPress={onSync}
            style={[styles.syncBtn, (!online || queue.length === 0) && { opacity: 0.5 }]}
          >
            {acting || syncing ? <ActivityIndicator color={colors.onPrimary} /> : <>
              <Ionicons name="sync" size={18} color={colors.onPrimary} />
              <Text style={styles.syncTxt}>Sincronizar</Text>
            </>}
          </TouchableOpacity>
        </View>

        <ScrollView contentContainerStyle={{ paddingBottom: 40 }}>
          {queue.length === 0 && (
            <View style={{ alignItems: "center", padding: space.xl }}>
              <Ionicons name="checkmark-done-circle-outline" size={56} color={colors.success} />
              <Text style={{ color: colors.text, fontWeight: "800", fontSize: fonts.size.md, marginTop: 10 }}>Tudo sincronizado</Text>
              <Text style={{ color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 4, textAlign: "center" }}>
                Não há checklists aguardando envio.
              </Text>
            </View>
          )}

          {queue.map((it) => {
            const st = it.status;
            const color = st === "sent" ? colors.success : st === "failed" ? colors.danger : st === "sending" ? colors.info : colors.warning;
            const bg = st === "sent" ? colors.successBg : st === "failed" ? colors.dangerBg : st === "sending" ? colors.infoBg : colors.warningBg;
            const label = st === "sent" ? "Enviado" : st === "failed" ? "Falhou" : st === "sending" ? "Enviando..." : "Aguardando";
            return (
              <View key={it.id} style={styles.item} testID={`queue-${it.numero_local}`}>
                <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                  <Text style={styles.itemNum}>{it.numero_local}</Text>
                  <View style={[styles.pill, { backgroundColor: bg }]}>
                    <Text style={[styles.pillTxt, { color }]}>{label}</Text>
                  </View>
                </View>
                <Text style={styles.itemName}>{it.payload?.nome} {it.payload?.sobrenome}</Text>
                <Text style={styles.itemMeta}>{it.payload?.empresa} • {it.payload?.placa} • {it.payload?.equipamento}</Text>
                <Text style={styles.itemDate}>Salvo em {new Date(it.queued_at).toLocaleString("pt-BR")}</Text>
                {!!it.last_error && <Text style={styles.err}>Erro: {it.last_error}</Text>}
                {!!it.attempts && <Text style={styles.attempts}>Tentativas: {it.attempts}</Text>}
                <View style={{ flexDirection: "row", gap: 8, marginTop: 8 }}>
                  <TouchableOpacity onPress={() => confirmRemove(it)} style={[styles.actBtn, { backgroundColor: colors.dangerBg }]} testID={`remove-${it.numero_local}`}>
                    <Ionicons name="trash-outline" size={14} color={colors.danger} />
                    <Text style={[styles.actTxt, { color: colors.danger }]}>Descartar</Text>
                  </TouchableOpacity>
                </View>
              </View>
            );
          })}
        </ScrollView>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: space.lg, paddingVertical: space.sm },
  title: { color: colors.text, fontSize: fonts.size.xl, fontWeight: "900" },
  statusBar: { flexDirection: "row", alignItems: "center", gap: 10, padding: 12, marginHorizontal: space.lg, borderRadius: radii.md, marginBottom: 6 },
  statusTxt: { fontWeight: "700", fontSize: fonts.size.sm, flex: 1 },
  summary: { flexDirection: "row", gap: 10, alignItems: "center", marginBottom: space.md },
  sumItem: { flex: 1, backgroundColor: colors.surface, borderRadius: radii.md, padding: 12, alignItems: "center", ...shadow.sm },
  sumVal: { color: colors.warning, fontWeight: "900", fontSize: 24 },
  sumLabel: { color: colors.textMuted, fontWeight: "700", fontSize: fonts.size.xs, marginTop: 2 },
  syncBtn: { flex: 1.2, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, paddingVertical: 14, borderRadius: radii.md, backgroundColor: colors.brandBlack },
  syncTxt: { color: colors.primary, fontWeight: "900", fontSize: fonts.size.sm },
  item: { backgroundColor: colors.surface, padding: space.md, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, marginBottom: 10, ...shadow.sm },
  itemNum: { color: colors.warning, fontWeight: "900", fontSize: fonts.size.sm },
  pill: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999 },
  pillTxt: { fontWeight: "900", fontSize: 11 },
  itemName: { color: colors.text, fontWeight: "800", fontSize: fonts.size.md },
  itemMeta: { color: colors.textMuted, fontSize: fonts.size.sm, marginTop: 2 },
  itemDate: { color: colors.textDim, fontSize: fonts.size.xs, marginTop: 4 },
  err: { color: colors.danger, fontSize: fonts.size.xs, marginTop: 4 },
  attempts: { color: colors.textMuted, fontSize: fonts.size.xs, marginTop: 2 },
  actBtn: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 10, paddingVertical: 6, borderRadius: radii.sm },
  actTxt: { fontWeight: "800", fontSize: fonts.size.xs },
});
