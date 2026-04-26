"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type ProgressBarProps = {
  value: number;
  className?: string;
  colorClassName?: string;
};

export function ProgressBar({ value, className, colorClassName }: ProgressBarProps) {
  const bounded = Math.max(0, Math.min(100, value));

  return (
    <div className={cn("h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800", className)}>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${bounded}%` }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className={cn("h-full rounded-full bg-brand-500", colorClassName)}
      />
    </div>
  );
}
