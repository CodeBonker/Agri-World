"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  AlertCircle,
  FlaskConical,
  MessageCircle,
  Microscope,
  Sprout,
  Waves,
} from "lucide-react";
import { useEffect } from "react";
import { PageShell } from "@/components/layout/page-shell";
import { StatCard } from "@/components/feature/stat-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/use-api";
import { getHealth } from "@/lib/api";
import type { HealthResponse } from "@/lib/types";

const features = [
  {
    href: "/crop",
    title: "Crop Recommendation",
    icon: Sprout,
    desc: "Season-aware crop planning",
  },
  {
    href: "/fertilizer",
    title: "Fertilizer Advice",
    icon: FlaskConical,
    desc: "Nutrient-specific input strategy",
  },
  {
    href: "/disease",
    title: "Disease Detection",
    icon: Microscope,
    desc: "Leaf image diagnosis",
  },
  {
    href: "/chat",
    title: "AI Chat Assistant",
    icon: MessageCircle,
    desc: "Conversational guidance",
  },
];

export default function DashboardPage() {
  const { data, loading, error, run } = useApi<HealthResponse>();

  useEffect(() => {
    run(getHealth).catch(() => undefined);
  }, [run]);

  return (
    <PageShell>
      <section className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <p className="mb-2 text-sm text-slate-500">Operational Overview</p>
          <h2 className="text-3xl font-semibold tracking-tight">
            Agri World Intelligence Hub
          </h2>
          <p className="mt-3 max-w-2xl text-sm text-slate-600 dark:text-slate-300">
            Unified farming intelligence for crop planning, nutrient optimization,
            disease prevention, and multilingual AI support.
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <Badge className="bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300">
              Premium AI SaaS Experience
            </Badge>
            {data?.status && (
              <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                System: {data.status}
              </Badge>
            )}
          </div>
        </Card>
        <StatCard
          label="Model Status"
          value={data?.models?.crop ?? "Loading..."}
          icon={<Waves className="h-4 w-4" />}
        />
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Accuracy" value="92%" />
        <StatCard label="Crops Supported" value="20+" />
        <StatCard label="Disease Classes" value="38" />
        <StatCard
          label="LLM Provider"
          value={data?.llm?.provider?.toUpperCase() ?? "-"}
        />
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-semibold">Core Modules</h3>
          {error && (
            <Button
              variant="secondary"
              onClick={() => run(getHealth).catch(() => undefined)}
            >
              Retry Health Check
            </Button>
          )}
        </div>

        {loading ? (
          <div className="grid gap-4 md:grid-cols-2">
            {Array.from({ length: 4 }).map((_, idx) => (
              <Skeleton key={idx} className="h-32" />
            ))}
          </div>
        ) : error ? (
          <Card className="border-rose-200 bg-rose-50 dark:border-rose-900/60 dark:bg-rose-900/20">
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 h-5 w-5 text-rose-600" />
              <div>
                <p className="font-semibold text-rose-700 dark:text-rose-300">
                  Unable to fetch backend health
                </p>
                <p className="mt-1 text-sm text-rose-600 dark:text-rose-200">
                  {error.message}
                </p>
              </div>
            </div>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {features.map((feature, idx) => {
              const Icon = feature.icon;
              return (
                <motion.div
                  key={feature.href}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.08, duration: 0.28 }}
                  whileHover={{ y: -4 }}
                >
                  <Link href={feature.href}>
                    <Card className="group h-full transition duration-200 hover:border-brand-300 hover:shadow-lg">
                      <div className="mb-4 flex items-center justify-between">
                        <div className="rounded-xl bg-brand-100 p-2 text-brand-700 transition group-hover:bg-brand-500 group-hover:text-white dark:bg-brand-900/30 dark:text-brand-300">
                          <Icon className="h-5 w-5" />
                        </div>
                        <Badge className="bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                          Open
                        </Badge>
                      </div>
                      <h4 className="text-lg font-semibold">{feature.title}</h4>
                      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                        {feature.desc}
                      </p>
                    </Card>
                  </Link>
                </motion.div>
              );
            })}
          </div>
        )}
      </section>
    </PageShell>
  );
}
