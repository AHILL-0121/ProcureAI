// Design tokens - warm, sophisticated color palette
export const tokens = {
  // Base colors
  cream: "#FDFAF4",
  parchment: "#F5EFE0",
  sand: "#E8DCC8",
  
  // Primary palette
  amber: "#D97706",
  gold: "#F59E0B",
  ember: "#B45309",
  
  // Accent colors
  forest: "#15803D",
  sage: "#4ADE80",
  coral: "#F97316",
  crimson: "#DC2626",
  
  // Neutrals
  charcoal: "#1C1917",
  slate: "#44403C",
  mist: "#A8A29E",
};

// Status color mappings
export const statusColors = {
  FULL_MATCH: { bg: "#DCFCE7", color: tokens.forest, dot: "#16A34A", label: "Full Match" },
  PARTIAL_MATCH: { bg: "#FEF9C3", color: "#854D0E", dot: tokens.gold, label: "Partial Match" },
  NO_MATCH: { bg: "#FEE2E2", color: tokens.crimson, dot: tokens.crimson, label: "No Match" },
  PROCESSING: { bg: "#FFF7ED", color: tokens.ember, dot: tokens.amber, label: "Processing" },
  MATCHED: { bg: "#DCFCE7", color: tokens.forest, dot: "#16A34A", label: "Matched" },
  DISCREPANCY: { bg: "#FEF9C3", color: "#854D0E", dot: tokens.gold, label: "Discrepancy" },
  RECEIVED: { bg: "#F0F9FF", color: "#0369A1", dot: "#0284C7", label: "Received" },
  EXTRACTING: { bg: "#FFF7ED", color: tokens.ember, dot: tokens.amber, label: "Extracting" },
  EXTRACTED: { bg: "#F3F4F6", color: tokens.slate, dot: tokens.mist, label: "Extracted" },
  VALIDATED: { bg: "#EDE9FE", color: "#7C3AED", dot: "#8B5CF6", label: "Validated" },
  FAILED: { bg: "#FEE2E2", color: tokens.crimson, dot: tokens.crimson, label: "Failed" },
};
