import { Redirect } from "expo-router";
// Placeholder route just so Tabs can render a center FAB slot. Never reached; tabPress is preventedDefault.
export default function Novo() {
  return <Redirect href="/(app)/checklist/new" />;
}
