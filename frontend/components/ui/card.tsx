import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-soft backdrop-blur-sm dark:border-slate-800 dark:bg-slate-900/70",
        className
      )}
      {...props}
    />
  );
}
