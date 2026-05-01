import { Redirect } from "expo-router";
import React from "react";
export default function HomeRedirect() {
  return <Redirect href="/(app)/(tabs)/agenda" />;
}
