import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, Platform } from "react-native";
import { Tabs, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { colors, fonts, shadow } from "../../../src/theme";
import { useDraft } from "../../../src/draft";

function FabButton() {
  const router = useRouter();
  const { reset } = useDraft();
  return (
    <TouchableOpacity
      testID="fab-new-checklist"
      activeOpacity={0.85}
      onPress={() => { reset(); router.push("/(app)/checklist/new"); }}
      style={styles.fab}
    >
      <Ionicons name="add" size={32} color={colors.onPrimary} />
    </TouchableOpacity>
  );
}

export default function TabsLayout() {
  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <Tabs
        screenOptions={{
          headerShown: false,
          tabBarActiveTintColor: colors.brandBlack,
          tabBarInactiveTintColor: colors.textMuted,
          tabBarLabelStyle: { fontSize: 11, fontWeight: "700" },
          tabBarStyle: {
            backgroundColor: colors.surface,
            borderTopColor: colors.border,
            borderTopWidth: 1,
            height: Platform.OS === "ios" ? 86 : 68,
            paddingBottom: Platform.OS === "ios" ? 28 : 10,
            paddingTop: 8,
          },
        }}
      >
        <Tabs.Screen
          name="agenda"
          options={{
            tabBarLabel: "Agenda",
            tabBarIcon: ({ color, focused }) => (
              <Ionicons name={focused ? "calendar" : "calendar-outline"} size={24} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="historico"
          options={{
            tabBarLabel: "Histórico",
            tabBarIcon: ({ color, focused }) => (
              <Ionicons name={focused ? "time" : "time-outline"} size={24} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="novo"
          options={{
            tabBarLabel: "",
            tabBarIcon: () => <FabButton />,
            tabBarItemStyle: { height: 0 },
          }}
          listeners={({ navigation }) => ({
            tabPress: (e) => e.preventDefault(),
          })}
        />
        <Tabs.Screen
          name="ganhos"
          options={{
            tabBarLabel: "Ganhos",
            tabBarIcon: ({ color, focused }) => (
              <Ionicons name={focused ? "cash" : "cash-outline"} size={24} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="perfil"
          options={{
            tabBarLabel: "Perfil",
            tabBarIcon: ({ color, focused }) => (
              <Ionicons name={focused ? "person" : "person-outline"} size={24} color={color} />
            ),
          }}
        />
      </Tabs>
    </View>
  );
}

const styles = StyleSheet.create({
  fab: {
    position: "absolute",
    top: -22,
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 4,
    borderColor: colors.surface,
    ...shadow.md,
  },
});
