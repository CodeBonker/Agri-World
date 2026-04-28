"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Bot, FlaskConical, Leaf, Microscope, Sprout } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Dashboard", icon: Activity },
  { href: "/crop", label: "Crop Advisor", icon: Sprout },
  { href: "/fertilizer", label: "Fertilizer", icon: FlaskConical },
  { href: "/disease", label: "Disease Scan", icon: Microscope },
  { href: "/chat", label: "AI Chat", icon: Bot },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-72 shrink-0 border-r border-slate-200 bg-white/80 p-5 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-900/60 lg:block">
      <div className="mb-10 flex items-center gap-3">
        <div className="rounded-xl bg-brand-500 p-2 text-white">
          <Leaf className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm font-semibold tracking-wide text-slate-500">Agri World</p>
          <p className="text-lg font-semibold">Control Center</p>
        </div>
      </div>
      <nav className="space-y-2">
        {nav.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
                active
                  ? "bg-brand-500 text-white shadow-soft"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
