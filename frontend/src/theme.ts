// Valeteck design tokens — Light theme, brand preto+amarelo
export const colors = {
  // Base (light)
  bg: "#F5F7FA",
  surface: "#FFFFFF",
  surfaceAlt: "#F0F3F7",
  border: "#E1E6ED",
  divider: "#EEF1F5",
  // Text
  text: "#0A0A0A",
  textMuted: "#6B7280",
  textDim: "#9CA3AF",
  // Brand
  brandBlack: "#0A0A0A",
  brandYellow: "#FFD400",
  primary: "#FFD400",      // Yellow for accents/buttons
  primaryDark: "#D4B000",
  onPrimary: "#0A0A0A",    // Text on yellow
  onDark: "#FFFFFF",       // Text on brandBlack
  // Status
  danger: "#EF4444",
  dangerBg: "#FEE2E2",
  warning: "#F59E0B",
  warningBg: "#FEF3C7",
  success: "#10B981",
  successBg: "#D1FAE5",
  info: "#3B82F6",
  infoBg: "#DBEAFE",
};

export const status = {
  rascunho:     { label: "Rascunho",     bg: "#E5E7EB", fg: "#374151" },
  enviado:      { label: "Enviado",      bg: "#DBEAFE", fg: "#1E40AF" },
  em_auditoria: { label: "Em auditoria", bg: "#FEF3C7", fg: "#92400E" },
  aprovado:     { label: "Aprovado",     bg: "#D1FAE5", fg: "#065F46" },
  reprovado:    { label: "Reprovado",    bg: "#FEE2E2", fg: "#991B1B" },
} as const;

export const radii = { sm: 8, md: 12, lg: 16, xl: 24, pill: 999 };
export const space = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 };
export const fonts = {
  size: { xs: 12, sm: 14, md: 16, lg: 18, xl: 22, xxl: 28 },
  weight: { regular: "400" as const, medium: "500" as const, bold: "700" as const, black: "900" as const },
};

export const shadow = {
  sm: {
    shadowColor: "#0A0A0A",
    shadowOpacity: 0.06,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 1 },
    elevation: 2,
  },
  md: {
    shadowColor: "#0A0A0A",
    shadowOpacity: 0.08,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 3 },
    elevation: 4,
  },
};
