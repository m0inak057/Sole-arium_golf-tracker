/**
 * Metrics panel — all 13 biomechanical measurements with targets.
 *
 * See PRD §8.
 */

"use client";

import type { MetricEntry, ThresholdRange, Scores } from "@/lib/types";

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
    case "green": return "text-green-400";
    case "amber": return "text-amber-400";
    case "red": return "text-red-400";
    default: return "text-white/30";
  }
}

function getBandDot(band: string | null | undefined): string {
  switch (band) {
    case "green": return "bg-green-400";
    case "amber": return "bg-amber-400";
    case "red": return "bg-red-400";
    default: return "bg-white/20";
  }
}

export default function MetricsPanel({ metrics, thresholds, scores }: MetricsPanelProps) {
  if (!metrics) {
    return (
      <div className="glass-card p-8 text-center text-white/30">
        No metrics available yet.
      </div>
    );
  }

  const metricKeys = Object.keys(METRIC_LABELS);

  return (
    <div className="glass-card overflow-hidden">
      <div className="px-6 py-4 border-b border-white/5">
        <h2 className="text-lg font-semibold">Biomechanical Metrics</h2>
        <p className="text-xs text-white/30 mt-1">13 measurements analysed per session</p>
      </div>

      <div className="divide-y divide-white/5">
        {metricKeys.map((key) => {
          const metric = metrics[key];
          const score = scores?.perMetric?.[key];
          const band = score?.band;

          if (!metric) return null;

          return (
            <div
              key={key}
              className="px-6 py-3.5 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${getBandDot(band)}`} />
                <div>
                  <span className="text-sm font-medium text-white/80">
                    {METRIC_LABELS[key]}
                  </span>
                  {!metric.primary && (
                    <span className="ml-2 text-[10px] text-white/20 uppercase tracking-wider">
                      secondary
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-4">
                <span className={`text-sm font-mono tabular-nums ${getBandColor(band)}`}>
                  {metric.value !== null
                    ? `${metric.value}${metric.unit === "deg" ? "°" : metric.unit === "ratio" ? "" : ` ${metric.unit}`}`
                    : "—"
                  }
                </span>
                {metric.value === null && metric.nullReason && (
                  <span className="text-[10px] text-white/20 max-w-[120px] truncate">
                    {metric.nullReason.replace(/_/g, " ")}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
