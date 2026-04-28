"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import { AnimatePresence, motion } from "framer-motion";
import { PageShell } from "@/components/layout/page-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Markdown } from "@/components/ui/markdown";
import { ProgressBar } from "@/components/ui/progress-bar";
import { postDisease } from "@/lib/api";
import type { DiseaseResponse } from "@/lib/types";
import { severityColor, toPercent } from "@/lib/utils";

const MAX_SIZE = 10 * 1024 * 1024;

export default function DiseasePage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DiseaseResponse | null>(null);

  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  const onDrop = (acceptedFiles: File[], rejected: any[]) => {
    if (rejected.length > 0) {
      toast.error("Invalid file. Use JPG, PNG, WEBP, BMP and keep size <= 10MB.");
      return;
    }
    const picked = acceptedFiles[0];
    if (!picked) return;
    if (picked.size > MAX_SIZE) {
      toast.error("File too large. Maximum 10MB.");
      return;
    }
    setFile(picked);
    setResult(null);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxSize: MAX_SIZE,
    maxFiles: 1,
    accept: {
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "image/webp": [".webp"],
      "image/bmp": [".bmp"],
    },
  });

  const runDetection = async () => {
    if (!file) {
      toast.error("Upload an image first");
      return;
    }
    setLoading(true);
    try {
      const response = await postDisease(file);
      setResult(response);
      toast.success("Disease analysis completed");
    } catch (error: any) {
      toast.error(error.message || "Disease analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageShell>
      <div className="grid gap-6 xl:grid-cols-[1fr,1.15fr]">
        <Card>
          <h2 className="text-2xl font-semibold">Disease Detection</h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Drop a leaf image to detect disease class and treatment recommendations.
          </p>
          <div
            {...getRootProps()}
            className={`mt-6 cursor-pointer rounded-2xl border-2 border-dashed p-6 text-center transition ${
              isDragActive
                ? "border-brand-500 bg-brand-50 dark:bg-brand-900/20"
                : "border-slate-300 dark:border-slate-700"
            }`}
          >
            <input {...getInputProps()} aria-label="Upload leaf image" />
            <p className="text-sm font-medium">Drag and drop image here</p>
            <p className="mt-1 text-xs text-slate-500">or click to browse (max 10MB)</p>
          </div>

          {preview && (
            <div className="mt-4 overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-700">
              <Image
                src={preview}
                alt="Leaf preview"
                width={1200}
                height={800}
                unoptimized
                className="h-64 w-full object-cover"
              />
            </div>
          )}

          <Button onClick={runDetection} disabled={loading || !file} className="mt-4 w-full">
            {loading ? "Scanning..." : "Analyze Disease"}
          </Button>
        </Card>

        <div className="space-y-4">
          <AnimatePresence mode="wait">
            {result ? (
              <motion.div
                key="result"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                className="space-y-4"
              >
                <Card>
                  <p className="text-xs uppercase tracking-widest text-slate-500">
                    Detection Result
                  </p>
                  <h3 className="mt-2 text-2xl font-semibold">{result.primary_disease}</h3>
                  <div className="mt-3 flex items-center gap-2">
                    <Badge className={severityColor(result.severity, result.is_healthy)}>
                      {result.is_healthy ? "Healthy" : result.severity}
                    </Badge>
                    <Badge className="bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                      {toPercent(result.confidence)}% confidence
                    </Badge>
                  </div>
                  <div className="mt-4">
                    <ProgressBar
                      value={toPercent(result.confidence)}
                      colorClassName={
                        result.is_healthy
                          ? "bg-emerald-500"
                          : result.severity === "high"
                          ? "bg-rose-500"
                          : "bg-amber-500"
                      }
                    />
                  </div>
                </Card>

                <Card>
                  <p className="mb-2 text-sm font-semibold">Treatment Checklist</p>
                  <ul className="space-y-2 text-sm text-slate-700 dark:text-slate-200">
                    {(result.treatment_recommendations ?? []).map((step, idx) => (
                      <li
                        key={`${step}-${idx}`}
                        className="rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-800/60"
                      >
                        {step}
                      </li>
                    ))}
                  </ul>
                </Card>

                <Card>
                  <p className="mb-3 text-sm font-semibold">Top Predictions</p>
                  <div className="space-y-2">
                    {(result.top_3 ?? []).map((item, idx) => (
                      <motion.div
                        key={`${item.disease}-${idx}`}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.05 }}
                      >
                        <div className="mb-1 flex items-center justify-between text-sm">
                          <span>{item.disease}</span>
                          <span className="text-slate-500">{toPercent(item.confidence)}%</span>
                        </div>
                        <ProgressBar value={toPercent(item.confidence)} className="h-1.5" />
                      </motion.div>
                    ))}
                  </div>
                </Card>

                <Card>
                  <p className="mb-3 text-sm font-semibold">Explanation</p>
                  <Markdown content={result.explanation} />
                </Card>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0.6 }}
                animate={{ opacity: 1 }}
                className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400"
              >
                Upload and analyze an image to see diagnosis details.
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </PageShell>
  );
}
