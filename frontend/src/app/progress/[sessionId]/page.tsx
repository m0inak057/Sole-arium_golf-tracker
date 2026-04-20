/**
 * Progress page — polls session status and shows pipeline progress.
 *
 * See PRD §3 step 6.
 */

"use client";

import { useParams, useRouter } from "next/navigation";
import { useSessionPolling } from "@/hooks/useSessionPolling";
import { useEffect } from "react";

const PHASE_LABELS: Record<string, string> = {
  uploaded: "Preparing…",
  agent1_running: "Analysing video metadata",
  agent1_done: "Video intelligence complete",
  phase1_running: "Detecting swing impact",
  phase1_done: "Impact detected",
  agent2_running: "Calibrating body proportions",
  agent2_done: "Body calibration complete",
  phase2_running: "Extracting keypoints",
  phase2_done: "Keypoints extracted",
  phase3_running: "Analysing setup",
  phase3_done: "Setup analysis complete",
  agent3_running: "Classifying shot type",
  agent3_done: "Shot type classified",
  phase4_running: "Computing biomechanics",
  phase4_done: "Metrics calculated",
  agent4_running: "Adapting thresholds",
  agent4_done: "Thresholds set",
  phase5_running: "Scoring performance",
  phase5_done: "Scoring complete",
  agent5_running: "Generating coaching feedback",
  agent5_done: "Coaching complete",
  phase7_running: "Rendering slow-motion",
  phase7_done: "Slow-motion ready",
  phase8_running: "Creating annotated overlay",
  phase8_done: "Overlay rendered",
  complete: "Analysis complete!",
  failed: "Analysis failed",
};

export default function ProgressPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const { data, error, isPolling } = useSessionPolling(sessionId);

  // Redirect to results on completion
  useEffect(() => {
    if (data?.status === "complete") {
      const timer = setTimeout(() => {
        router.push(`/results/${sessionId}`);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [data?.status, sessionId, router]);

  const progress = data?.progress_pct ?? 0;
  const status = data?.status ?? "uploaded";
  const label = PHASE_LABELS[status] ?? status;
  const isFailed = data?.failed ?? false;

  return (
    <div className="max-w-xl mx-auto px-6 py-24 animate-fade-in">
      <div className="text-center mb-16">
        <h1 className="text-3xl font-bold tracking-tight mb-3">
          {isFailed ? "Something went wrong" : "Analysing Your Swing"}
        </h1>
        <p className="text-white/40">
          {isFailed
            ? data?.status_reason ?? "An unexpected error occurred."
            : "Sit tight — our AI pipeline is working through 8 analysis phases."
          }
        </p>
      </div>

      {/* Progress ring */}
      <div className="flex justify-center mb-12">
        <div className="relative w-48 h-48">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
            {/* Track */}
            <circle
              cx="50" cy="50" r="42"
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="6"
            />
            {/* Progress */}
            <circle
              cx="50" cy="50" r="42"
              fill="none"
              stroke={isFailed ? "#EF4444" : "#00D4FF"}
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={`${2 * Math.PI * 42}`}
              strokeDashoffset={`${2 * Math.PI * 42 * (1 - progress / 100)}`}
              className="transition-all duration-700 ease-out"
              style={{
                filter: isFailed ? "none" : "drop-shadow(0 0 8px rgba(0, 212, 255, 0.4))",
              }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-4xl font-bold tabular-nums">
              {progress}
              <span className="text-lg text-white/40">%</span>
            </span>
          </div>
        </div>
      </div>

      {/* Status label */}
      <div className="glass-card p-6 text-center">
        <div className="flex items-center justify-center gap-3 mb-2">
          {!isFailed && status !== "complete" && (
            <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
          )}
          {status === "complete" && (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#22C55E" strokeWidth="2.5" strokeLinecap="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          )}
          {isFailed && (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2.5" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          )}
          <span className={`font-medium ${isFailed ? "text-red-400" : status === "complete" ? "text-green-400" : "text-white/80"}`}>
            {label}
          </span>
        </div>
        <p className="text-xs text-white/30 font-mono">{sessionId}</p>
      </div>

      {/* Error details */}
      {error && (
        <div className="mt-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center">
          {error}
        </div>
      )}

      {/* Failed action */}
      {isFailed && (
        <div className="mt-8 text-center">
          <a
            href="/"
            className="inline-block px-6 py-3 rounded-xl bg-white/5 border border-white/10 text-white/60 hover:text-white hover:border-white/20 transition-all text-sm font-medium"
          >
            ← Try another video
          </a>
        </div>
      )}
    </div>
  );
}
