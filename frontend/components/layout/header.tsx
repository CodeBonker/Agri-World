"use client";

import { Activity } from "lucide-react";
import { ThemeToggle } from "@/components/layout/theme-toggle";

export function Header() {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-slate-50/85 px-4 py-4 backdrop-blur-xl dark:border-slate-800/80 dark:bg-slate-950/85 sm:px-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">AI Agriculture Platform</p>
          <h1 className="text-xl font-semibold">Agri World</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className="hidden items-center gap-2 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 sm:flex">
            <Activity className="h-3.5 w-3.5" />
            Operational
          </div>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
