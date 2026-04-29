import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function toPercent(value?: number | null, digits = 1) {
  if (typeof value !== "number" || Number.isNaN(value)) return 0;
  return Number((value * 100).toFixed(digits));
}

export function confidenceLabelToPercent(label?: string | null) {
  if (!label) return 0;
  const map: Record<string, number> = {
    low: 35,
    medium: 65,
    high: 90,
  };
  return map[label.toLowerCase()] ?? 0;
}

export function seasonColor(season?: string | null) {
  switch ((season || "").toLowerCase()) {
    case "kharif":
      return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
    case "rabi":
      return "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300";
    case "zaid":
      return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
    default:
      return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300";
  }
}

export function severityColor(severity?: string | null, isHealthy?: boolean) {
  if (isHealthy || severity === "none") {
    return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
  }
  switch ((severity || "").toLowerCase()) {
    case "high":
      return "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300";
    case "moderate":
      return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
    default:
      return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300";
  }
}
