"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Bot, FlaskConical, Microscope, Sprout } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/", icon: Activity, label: "Home" },
  { href: "/crop", icon: Sprout, label: "Crop" },
  { href: "/fertilizer", icon: FlaskConical, label: "Fertilizer" },
  { href: "/disease", icon: Microscope, label: "Disease" },
  { href: "/chat", icon: Bot, label: "Chat" },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-4 left-1/2 z-30 flex w-[min(94%,460px)] -translate-x-1/2 items-center justify-between rounded-2xl border border-slate-200 bg-white/95 px-2 py-2 shadow-soft backdrop-blur lg:hidden dark:border-slate-700 dark:bg-slate-900/95">
      {nav.map((item) => {
        const Icon = item.icon;
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex min-w-14 flex-col items-center rounded-xl px-2 py-1 text-[11px] font-medium",
              active ? "text-brand-600" : "text-slate-500 dark:text-slate-400"
            )}
          >
            <Icon className="mb-0.5 h-4 w-4" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
