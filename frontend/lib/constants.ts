export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const SOIL_TYPES = ["Sandy", "Loamy", "Black", "Red", "Clayey"] as const;

export const CROP_TYPES = [
  "Wheat",
  "Rice",
  "Maize",
  "Cotton",
  "Sugarcane",
  "Soybean",
  "Barley",
  "Potato",
  "Tomato",
  "Onion",
  "Mustard",
  "Groundnut",
  "Millets",
  "Pulses",
] as const;

export const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/crop", label: "Crop Advisor" },
  { href: "/fertilizer", label: "Fertilizer" },
  { href: "/disease", label: "Disease Scan" },
  { href: "/chat", label: "AI Chat" },
];
