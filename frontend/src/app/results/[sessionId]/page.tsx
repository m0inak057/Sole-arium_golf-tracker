/**
 * Results page — the main output surface.
 *
 * Annotated video is the hero. Metrics and coaching sit beneath.
 * See architecture.md §6 and PRD §9.
 */

"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getFullSession, getVideoStreamUrl, getVideoDownloadUrl, ApiError } from "@/lib/api";
import type { SessionJSON } from "@/lib/types";
import AnnotatedVideo from "./AnnotatedVideo";
import SlowMoTab from "./SlowMoTab";
import MetricsPanel from "./MetricsPanel";
import CoachingOutput from "./CoachingOutput";
import ScoreCard from "./ScoreCard";

type VideoTab = "annotated" | "slowmo";

export default function ResultsPage() {
  const params = useParams();
  const sessionId = params.sessionId as string;

  const [session, setSession] = useState<SessionJSON | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<VideoTab>("annotated");

  useEffect(() => {
    getFullSession(sessionId)
      .then(setSession)
      .catch((err) => {
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError("Failed to load results.");
        }
      });
  }, [sessionId]);

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-24 text-center animate-fade-in">
        <h1 className="text-2xl font-bold mb-4 text-red-400">Error</h1>
        <p className="text-white/50 mb-8">{error}</p>
        <a href="/" className="text-cyan-400 hover:text-cyan-300 text-sm">
          ← Back to upload
        </a>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-24 text-center animate-fade-in">
        <div className="w-12 h-12 mx-auto rounded-full border-2 border-cyan-400/30 border-t-cyan-400 animate-spin" />
        <p className="mt-6 text-white/40">Loading results…</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Analysis Results</h1>
          <p className="text-sm text-white/40 mt-1">
            {session.detected_shot_type?.replace("_", " ")
              ? `${session.detected_shot_type.replace("_", " ")} • ${session.camera_angle?.replace("_", " ") ?? "unknown angle"}`
              : "Processing complete"
            }
          </p>
        </div>
        <ScoreCard scores={session.scores} />
      </div>

      {/* Video section */}
      <div className="glass-card overflow-hidden">
        {/* Tabs */}
        <div className="flex border-b border-white/5">
          <button
            onClick={() => setActiveTab("annotated")}
            className={`px-6 py-3 text-sm font-medium transition-all ${
              activeTab === "annotated"
                ? "text-cyan-400 border-b-2 border-cyan-400 bg-cyan-400/5"
                : "text-white/40 hover:text-white/60"
            }`}
            id="tab-annotated"
          >
            Annotated Video
          </button>
          <button
            onClick={() => setActiveTab("slowmo")}
            className={`px-6 py-3 text-sm font-medium transition-all ${
              activeTab === "slowmo"
                ? "text-cyan-400 border-b-2 border-cyan-400 bg-cyan-400/5"
                : "text-white/40 hover:text-white/60"
            }`}
            id="tab-slowmo"
          >
            Slow-Motion
          </button>
        </div>

        {/* Video content */}
        <div className="p-4">
          {activeTab === "annotated" ? (
            <AnnotatedVideo sessionId={sessionId} />
          ) : (
            <SlowMoTab sessionId={sessionId} />
          )}
        </div>

        {/* Download buttons */}
        <div className="flex gap-3 px-4 pb-4">
          <a
            href={getVideoDownloadUrl(sessionId, "annotated")}
            className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white/60 hover:text-white hover:border-white/20 transition-all"
            id="download-annotated"
          >
            ↓ Annotated MP4
          </a>
          <a
            href={getVideoDownloadUrl(sessionId, "slowmo")}
            className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white/60 hover:text-white hover:border-white/20 transition-all"
            id="download-slowmo"
          >
            ↓ Slow-Mo MP4
          </a>
        </div>
      </div>

      {/* Metrics & Coaching grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <MetricsPanel
            metrics={session.metrics}
            thresholds={session.active_thresholds}
            scores={session.scores}
          />
        </div>
        <div>
          <CoachingOutput items={session.coaching_output} />
        </div>
      </div>

      {/* Footer */}
      <div className="text-center pb-8">
        <a
          href="/"
          className="text-sm text-white/30 hover:text-cyan-400 transition-colors"
        >
          ← Analyse another swing
        </a>
      </div>
    </div>
  );
}
