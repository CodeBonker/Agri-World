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
import { postCrop } from "@/lib/api";
import type { CropRequest, CropResponse } from "@/lib/types";
import { confidenceLabelToPercent, seasonColor, toPercent } from "@/lib/utils";

const initialForm = {
  N: "90",
  P: "42",
  K: "43",
  ph: "6.5",
  temperature: "",
  humidity: "",
  rainfall: "",
  month: "",
  top_n: "5",
  location: "",
};

export default function CropPage() {
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CropResponse | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (
        !form.location.trim() &&
        (!form.temperature.trim() || !form.humidity.trim() || !form.rainfall.trim())
      ) {
        toast.error("Provide temperature, humidity, and rainfall or enter a location.");
        setLoading(false);
        return;
      }

      const payload: CropRequest = {
        N: Number(form.N),
        P: Number(form.P),
        K: Number(form.K),
        ph: Number(form.ph),
        top_n: Number(form.top_n) || 5,
      };

      if (form.location.trim()) {
        payload.location = form.location.trim();
      } else {
        payload.temperature = Number(form.temperature);
        payload.humidity = Number(form.humidity);
        payload.rainfall = Number(form.rainfall);
      }

      if (form.month) payload.month = Number(form.month);

      const response = await postCrop(payload);
      setResult(response);
      toast.success("Crop recommendation generated");
    } catch (error: any) {
      toast.error(error.message || "Failed to generate crop recommendation");
    } finally {
      setLoading(false);
    }
  };

  const confidencePct = result?.confidence
    ? confidenceLabelToPercent(result.confidence)
    : toPercent(result?.weather_score ?? 0);

  return (
    <PageShell>
      <div className="grid gap-6 xl:grid-cols-[1fr,1.15fr]">
        <Card>
          <h2 className="text-2xl font-semibold">Crop Advisor</h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Enter core soil values and either weather metrics or location for auto-weather.
          </p>
          <form className="mt-6 space-y-4" onSubmit={onSubmit}>
            <div className="grid grid-cols-2 gap-3">
              <Input
                placeholder="Nitrogen (N)"
                value={form.N}
                onChange={(e) => setForm((s) => ({ ...s, N: e.target.value }))}
                required
              />
              <Input
                placeholder="Phosphorus (P)"
                value={form.P}
                onChange={(e) => setForm((s) => ({ ...s, P: e.target.value }))}
                required
              />
              <Input
                placeholder="Potassium (K)"
                value={form.K}
                onChange={(e) => setForm((s) => ({ ...s, K: e.target.value }))}
                required
              />
              <Input
                placeholder="pH"
                value={form.ph}
                onChange={(e) => setForm((s) => ({ ...s, ph: e.target.value }))}
                required
              />
            </div>

            <Input
              placeholder="Location (optional, e.g. Hyderabad)"
              value={form.location}
              onChange={(e) => setForm((s) => ({ ...s, location: e.target.value }))}
            />

            <div className="grid grid-cols-3 gap-3">
              <Input
                placeholder="Temperature"
                value={form.temperature}
                onChange={(e) => setForm((s) => ({ ...s, temperature: e.target.value }))}
                disabled={!!form.location.trim()}
              />
              <Input
                placeholder="Humidity"
                value={form.humidity}
                onChange={(e) => setForm((s) => ({ ...s, humidity: e.target.value }))}
                disabled={!!form.location.trim()}
              />
              <Input
                placeholder="Rainfall"
                value={form.rainfall}
                onChange={(e) => setForm((s) => ({ ...s, rainfall: e.target.value }))}
                disabled={!!form.location.trim()}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Input
                placeholder="Month (1-12)"
                value={form.month}
                onChange={(e) => setForm((s) => ({ ...s, month: e.target.value }))}
              />
              <Input
                placeholder="Top N (1-10)"
                value={form.top_n}
                onChange={(e) => setForm((s) => ({ ...s, top_n: e.target.value }))}
              />
            </div>

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Analyzing..." : "Recommend Crop"}
            </Button>
          </form>
        </Card>

        <div className="space-y-4">
          {result ? (
            <>
              <Card className="relative overflow-hidden">
                <div className="absolute right-0 top-0 h-24 w-24 rounded-bl-full bg-brand-200/40 dark:bg-brand-600/20" />
                <p className="text-xs uppercase tracking-widest text-slate-500">Primary Crop</p>
                <h3 className="mt-2 text-3xl font-semibold capitalize">
                  {result.primary_crop ?? "-"}
                </h3>
                <div className="mt-3 flex items-center gap-3">
                  <Badge className={seasonColor(result.season)}>
                    {result.season ?? "unknown"}
                  </Badge>
                  <Badge className="bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                    Confidence: {result.confidence ?? "-"}
                  </Badge>
                </div>
                <div className="mt-5">
                  <div className="mb-2 flex items-center justify-between text-sm text-slate-600 dark:text-slate-300">
                    <span>Confidence</span>
                    <span>{confidencePct}%</span>
                  </div>
                  <ProgressBar value={confidencePct} />
                </div>
              </Card>

              <Card>
                <p className="mb-2 text-sm font-semibold">Why this crop now</p>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  {result.why_this_crop_now}
                </p>
              </Card>

              <Card>
                <p className="mb-3 text-sm font-semibold">Top Recommendations</p>
                <div className="space-y-2">
                  {(result.top_recommendations ?? []).map((item, idx) => (
                    <motion.div
                      key={`${item.crop}-${idx}`}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      className="rounded-xl border border-slate-200 p-3 dark:border-slate-700"
                    >
                      <div className="mb-1 flex items-center justify-between">
                        <p className="font-semibold capitalize">{item.crop}</p>
                        <span className="text-xs text-slate-500">
                          {toPercent(item.composite_score)}%
                        </span>
                      </div>
                      <ProgressBar value={toPercent(item.composite_score)} className="h-1.5" />
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
              Submit the form to view crop insights.
            </Card>
          )}
        </div>
      </div>
    </PageShell>
  );
}
