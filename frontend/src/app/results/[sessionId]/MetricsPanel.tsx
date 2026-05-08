/**
 * Metrics panel — all 13 biomechanical measurements with targets.
 */

"use client";

import type { MetricEntry, ThresholdRange, Scores } from "@/lib/types";
import { motion } from "framer-motion";
import { Info, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricsPanelProps {
  metrics: Record<string, MetricEntry> | null;
  thresholds: Record<string, ThresholdRange> | null;
  scores: Scores | null;
}

const METRIC_LABELS: Record<string, string> = {
  tempo_ratio: "Tempo Ratio",
  x_factor: "X-Factor",
  spine_deviation_max: "Spine Deviation",
  hip_sway: "Hip Sway",
  head_sway: "Head Sway",
  hip_turn: "Hip Turn",
  shoulder_turn: "Shoulder Turn",
  side_bend: "Side Bend",
  hips_open: "Hips Open at Impact",
  wrist_lag: "Wrist Lag",
  knee_flex_left: "Knee Flex (Left)",
  knee_flex_right: "Knee Flex (Right)",
  stance_width: "Stance Width",
};

function getBandColor(band: string | null | undefined): string {
  switch (band) {
    case "green": return "text-emerald-400";
    case "amber": return "text-amber-400";
    case "red": return "text-rose-400";
    default: return "text-slate-500";
  }
}

function getBandBg(band: string | null | undefined): string {
  switch (band) {
    case "green": return "bg-emerald-500/10 border-emerald-500/20";
    case "amber": return "bg-amber-500/10 border-amber-500/20";
    case "red": return "bg-rose-500/10 border-rose-500/20";
    default: return "bg-slate-800/50 border-slate-700/50";
  }
}

function getBandDot(band: string | null | undefined): string {
  switch (band) {
    case "green": return "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]";
    case "amber": return "bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]";
    case "red": return "bg-rose-400 shadow-[0_0_8px_rgba(244,63,94,0.8)]";
    default: return "bg-slate-600";
  }
}

export default function MetricsPanel({ metrics, thresholds, scores }: MetricsPanelProps) {
  if (!metrics) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-slate-500 bg-slate-900 border border-slate-800 rounded-2xl h-full">
        <Info className="w-12 h-12 mb-4 opacity-50" />
        <p>No metrics available yet.</p>
      </div>
    );
  }

  // Sort metrics: Red -> Amber -> Green -> null
  const metricKeys = Object.keys(METRIC_LABELS).sort((a, b) => {
    const primaryA = metrics[a]?.primary ? 1 : 0;
    const primaryB = metrics[b]?.primary ? 1 : 0;
    if (primaryA !== primaryB) return primaryB - primaryA;

    const bandOrder: Record<string, number> = { red: 0, amber: 1, green: 2, undefined: 3 };
    const bandA = scores?.perMetric?.[a]?.band as string | undefined;
    const bandB = scores?.perMetric?.[b]?.band as string | undefined;
    return (bandOrder[bandA ?? "undefined"] ?? 3) - (bandOrder[bandB ?? "undefined"] ?? 3);
  });

  return (
    <div className="space-y-3">
      {metricKeys.map((key, idx) => {
        const metric = metrics[key];
        const score = scores?.perMetric?.[key];
        const band = score?.band;
        const target = thresholds?.[key];

        if (!metric) return null;

        // format value
        const formattedValue = metric.value !== null
          ? `${metric.value.toFixed(1)}${metric.unit === "deg" ? "°" : metric.unit === "ratio" ? "" : ` ${metric.unit}`}`
          : "—";

        let targetStr = "";
        if (target) {
            targetStr = target.targetVal !== null 
              ? `${target.targetVal}${metric.unit === "deg" ? "°" : ""}`
              : `${target.minVal}-${target.maxVal}${metric.unit === "deg" ? "°" : ""}`;
        }

        return (
          <motion.div
            key={key}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
            className={cn(
              "group relative flex flex-col p-4 rounded-2xl border transition-all duration-200 overflow-hidden",
              getBandBg(band)
            )}
          >
            {/* Top row */}
            <div className="flex items-start justify-between mb-2 z-10 w-full">
              <div className="flex items-center gap-3">
                <div className={cn("w-2.5 h-2.5 rounded-full shrink-0", getBandDot(band))} />
                <div>
                   <h4 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                     {METRIC_LABELS[key]}
                     {!metric.primary && (
                       <span className="text-[9px] px-1.5 py-0.5 rounded-sm bg-slate-800 text-slate-400 font-mono tracking-widest uppercase">Sec</span>
                     )}
                   </h4>
                </div>
              </div>
              
              <div className={cn("text-lg font-bold tabular-nums tracking-tight", getBandColor(band))}>
                {formattedValue}
              </div>
            </div>

            {/* Bottom Row / Info */}
            <div className="flex items-center justify-between z-10">
              <div className="text-[11px] text-slate-400 font-medium">
                 {metric.value === null && metric.nullReason ? (
                   <span className="text-rose-400/80 flex items-center gap-1">
                     <HelpCircle className="w-3 h-3" /> {metric.nullReason.replace(/_/g, " ")}
                   </span>
                 ) : targetStr ? (
                   <span>Target: <span className="text-slate-300">{targetStr}</span></span>
                 ) : null}
              </div>

               {score?.score !== undefined && (
                   <div className="text-[10px] font-mono text-slate-500 uppercase">
                      P: {Math.round(score.score)}/100
                   </div>
               )}
            </div>

            {/* Highlight overlay hover effect */}
            <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-[0.02] transition-opacity" />
          </motion.div>
        );
      })}
    </div>
  );
}
