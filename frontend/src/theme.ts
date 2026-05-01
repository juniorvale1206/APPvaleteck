// Valeteck design tokens
export const colors = {
  bg: "#0A0A0A",
  surface: "#141414",
  surfaceAlt: "#1C1C1C",
  border: "#2A2A2A",
  text: "#FFFFFF",
  textMuted: "#9A9A9A",
  textDim: "#6E6E6E",
  primary: "#FFD400", // Valeteck yellow
  primaryDark: "#D4B000",
  onPrimary: "#0A0A0A",
  danger: "#FF4D4F",
  warning: "#FFA826",
  success: "#22C55E",
  info: "#3B82F6",
};

export const status = {
  rascunho: { label: "Rascunho", bg: "#2A2A2A", fg: "#E0E0E0" },
  enviado: { label: "Enviado", bg: "#1E3A5F", fg: "#7CB7FF" },
  em_auditoria: { label: "Em auditoria", bg: "#4A3A12", fg: "#FFD400" },
  aprovado: { label: "Aprovado", bg: "#143A22", fg: "#34D399" },
  reprovado: { label: "Reprovado", bg: "#4A1414", fg: "#FF7A7A" },
} as const;

export const radii = { sm: 8, md: 12, lg: 16, xl: 24, pill: 999 };
export const space = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 };
export const fonts = {
  size: { xs: 12, sm: 14, md: 16, lg: 18, xl: 22, xxl: 28 },
  weight: { regular: "400" as const, medium: "500" as const, bold: "700" as const, black: "900" as const },
};
