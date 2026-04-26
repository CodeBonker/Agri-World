"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { toast } from "sonner";
import { PageShell } from "@/components/layout/page-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Markdown } from "@/components/ui/markdown";
import { ProgressBar } from "@/components/ui/progress-bar";
import { Select } from "@/components/ui/select";
import { postFertilizer } from "@/lib/api";
import { CROP_TYPES, SOIL_TYPES } from "@/lib/constants";
import type { FertilizerRequest, FertilizerResponse } from "@/lib/types";
import { toPercent } from "@/lib/utils";

const initial = {
  temperature: "28",
  humidity: "65",
  moisture: "40",
  nitrogen: "37",
  phosphorous: "0",
  potassium: "0",
  soil_type: "Sandy",
  crop_type: "Maize",
};

export default function FertilizerPage() {
  const [form, setForm] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FertilizerResponse | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload: FertilizerRequest = {
        temperature: Number(form.temperature),
        humidity: Number(form.humidity),
        moisture: Number(form.moisture),
        nitrogen: Number(form.nitrogen),
        phosphorous: Number(form.phosphorous),
        potassium: Number(form.potassium),
        soil_type: form.soil_type,
        crop_type: form.crop_type,
      };
      const response = await postFertilizer(payload);
      setResult(response);
      toast.success("Fertilizer recommendation ready");
    } catch (error: any) {
      toast.error(error.message || "Failed to fetch fertilizer recommendation");
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageShell>
      <div className="grid gap-6 xl:grid-cols-[1fr,1.15fr]">
        <Card>
          <h2 className="text-2xl font-semibold">Fertilizer Advisor</h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Balance nutrient application with model-assisted fertilizer planning.
          </p>
          <form className="mt-6 space-y-4" onSubmit={onSubmit}>
            <div className="grid grid-cols-3 gap-3">
              <Input
                placeholder="Temperature"
                value={form.temperature}
                onChange={(e) =>
                  setForm((s) => ({ ...s, temperature: e.target.value }))
                }
                required
              />
              <Input
                placeholder="Humidity"
                value={form.humidity}
                onChange={(e) => setForm((s) => ({ ...s, humidity: e.target.value }))}
                required
              />
              <Input
                placeholder="Moisture"
                value={form.moisture}
                onChange={(e) => setForm((s) => ({ ...s, moisture: e.target.value }))}
                required
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <Input
                placeholder="Nitrogen"
                value={form.nitrogen}
                onChange={(e) => setForm((s) => ({ ...s, nitrogen: e.target.value }))}
                required
              />
              <Input
                placeholder="Phosphorous"
                value={form.phosphorous}
                onChange={(e) =>
                  setForm((s) => ({ ...s, phosphorous: e.target.value }))
                }
                required
              />
              <Input
                placeholder="Potassium"
                value={form.potassium}
                onChange={(e) => setForm((s) => ({ ...s, potassium: e.target.value }))}
                required
              />
            </div>
            <Select
              value={form.soil_type}
              onChange={(e) => setForm((s) => ({ ...s, soil_type: e.target.value }))}
            >
              {SOIL_TYPES.map((soil) => (
                <option key={soil} value={soil}>
                  {soil}
                </option>
              ))}
            </Select>
            <Select
              value={form.crop_type}
              onChange={(e) => setForm((s) => ({ ...s, crop_type: e.target.value }))}
            >
              {CROP_TYPES.map((crop) => (
                <option key={crop} value={crop}>
                  {crop}
                </option>
              ))}
            </Select>
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Computing..." : "Recommend Fertilizer"}
            </Button>
          </form>
        </Card>

        <div className="space-y-4">
          {result ? (
            <>
              <Card>
                <p className="text-xs uppercase tracking-widest text-slate-500">
                  Recommended Fertilizer
                </p>
                <h3 className="mt-2 text-3xl font-semibold">
                  {result.primary_fertilizer ?? "-"}
                </h3>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Badge className="bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300">
                    Confidence {toPercent(result.confidence)}%
                  </Badge>
                  {result.rule_applied && (
                    <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                      Rule-based override
                    </Badge>
                  )}
                </div>
                <div className="mt-4">
                  <ProgressBar value={toPercent(result.confidence)} />
                </div>
                {result.rule_reason && (
                  <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
                    Reason: {result.rule_reason}
                  </p>
                )}
              </Card>

              <Card>
                <p className="mb-3 text-sm font-semibold">Top Suggestions</p>
                <div className="space-y-2">
                  {(result.top_recommendations ?? []).map((item, idx) => (
                    <motion.div
                      key={`${item.fertilizer}-${idx}`}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      className="rounded-xl border border-slate-200 p-3 dark:border-slate-700"
                    >
                      <div className="mb-1 flex items-center justify-between">
                        <p className="font-semibold">{item.fertilizer}</p>
                        <span className="text-xs text-slate-500">
                          {toPercent(item.probability)}%
                        </span>
                      </div>
                      <ProgressBar value={toPercent(item.probability)} className="h-1.5" />
                    </motion.div>
                  ))}
                </div>
              </Card>

              <Card>
                <p className="mb-3 text-sm font-semibold">Explanation</p>
                <Markdown content={result.explanation} />
              </Card>
            </>
          ) : (
            <Card className="flex min-h-[280px] items-center justify-center text-sm text-slate-500 dark:text-slate-400">
              Submit the form to view fertilizer advice.
            </Card>
          )}
        </div>
      </div>
    </PageShell>
  );
}
