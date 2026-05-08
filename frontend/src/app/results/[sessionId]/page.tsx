/**
 * Results page — the main output surface.
 */

"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getFullSession, getVideoDownloadUrl, ApiError } from "@/lib/api";
import type { SessionJSON } from "@/lib/types";
import AnnotatedVideo from "./AnnotatedVideo";
import SlowMoTab from "./SlowMoTab";
import MetricsPanel from "./MetricsPanel";
import CoachingOutput from "./CoachingOutput";
import ScoreCard from "./ScoreCard";
import { motion } from "framer-motion";
import { Download, ChevronLeft, Video, AlertCircle, Activity } from "lucide-react";
import { cn } from "@/lib/utils";

type VideoTab = "annotated" | "slowmo";

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [session, setSession] = useState<SessionJSON | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<VideoTab>("annotated");
  const [activeAngle, setActiveAngle] = useState<"face_on" | "down_the_line">("face_on");

  useEffect(() => {
    getFullSession(sessionId)
      .then((data) => {
        setSession(data);
        if (data.primary_camera_angle) {
          setActiveAngle(data.primary_camera_angle);
        }
      })
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
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6 selection:bg-emerald-500/30">
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-slate-900/50 backdrop-blur-xl border border-red-500/20 p-8 rounded-3xl text-center max-w-md"
        >
          <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>
          <h1 className="text-2xl font-bold mb-4 text-slate-100">Analysis Failed</h1>
          <p className="text-slate-400 mb-8">{error}</p>
          <button 
             onClick={() => router.push("/")}
             className="px-6 py-3 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 transition"
          >
            ← Back to upload
          </button>
        </motion.div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center relative overflow-hidden">
         <div className="w-16 h-16 border-4 border-slate-800 border-t-emerald-500 rounded-full animate-spin" />
         <p className="mt-6 text-slate-400 font-medium">Assembling your insights...</p>
      </div>
    );
  }

  const isDual = session.dual_video_status?.dual_processing_mode || false;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 selection:bg-emerald-500/30 pb-20">
      {/* Top Banner Area */}
      <div className="bg-slate-900 border-b border-slate-800 sticky top-0 z-40 backdrop-blur-xl bg-opacity-80">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4 flex items-center justify-between">
          <button 
            onClick={() => router.push("/")}
            className="flex items-center gap-2 text-sm font-medium text-slate-400 hover:text-emerald-400 transition"
          >
            <ChevronLeft className="w-4 h-4" /> Analyze Another
          </button>
          <div className="text-xs font-mono text-slate-600 bg-slate-950 px-3 py-1 rounded-md border border-slate-800">
            {session.session_id.split("-")[0]}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 md:px-8 pt-8 md:pt-12 space-y-12">
        
        {/* Header Hero */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col lg:flex-row items-start lg:items-end justify-between gap-8"
        >
          <div>
            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-3">
              Swing <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">Analysis.</span>
            </h1>
            <div className="flex items-center gap-3 text-slate-400">
              <span className="capitalize px-3 py-1 bg-slate-800 rounded-full text-xs font-semibold text-slate-300">
                {session.gender ?? "Baseline"}
              </span>
              <span>•</span>
              <span className="capitalize">{session.detected_shot_type?.replace("_", " ") ?? "Unknown Shot"}</span>
              <span>•</span>
              <span className="capitalize">{isDual ? "Dual Angle" : (session.camera_angle?.replace("_", " ") ?? "Unknown View")}</span>
            </div>
          </div>
          
          <div className="shrink-0">
             <ScoreCard scores={session.scores} />
          </div>
        </motion.div>

        {/* Video & Primary Layout */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-8"
        >
          {/* Main Visualizer (Videos) */}
          <div className="flex flex-col bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl">
            {/* Tabs */}
            <div className="flex flex-col sm:flex-row p-2 bg-slate-950 border-b border-slate-800 gap-2">
              <div className="flex p-1 bg-slate-900 rounded-xl flex-1">
                <button
                  onClick={() => setActiveTab("annotated")}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-2 py-2.5 px-4 text-xs font-bold uppercase tracking-wider rounded-lg transition-all",
                    activeTab === "annotated" 
                      ? "bg-slate-800 text-emerald-400 shadow-sm" 
                      : "text-slate-500 hover:text-slate-300"
                  )}
                >
                  <Video className="w-4 h-4" /> Annotated
                </button>
                <button
                  onClick={() => setActiveTab("slowmo")}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-2 py-2.5 px-4 text-xs font-bold uppercase tracking-wider rounded-lg transition-all",
                    activeTab === "slowmo" 
                      ? "bg-slate-800 text-cyan-400 shadow-sm" 
                      : "text-slate-500 hover:text-slate-300"
                  )}
                >
                  <Video className="w-4 h-4" /> Slow-Mo
                </button>
              </div>

              {isDual && (
                <div className="flex p-1 bg-slate-900 rounded-xl">
                  <button
                    onClick={() => setActiveAngle("face_on")}
                    className={cn(
                      "px-4 py-2.5 text-[10px] font-black uppercase tracking-widest rounded-lg transition-all",
                      activeAngle === "face_on" 
                        ? "bg-emerald-500 text-slate-950 shadow-lg" 
                        : "text-slate-500 hover:text-slate-300"
                    )}
                  >
                    Face-On
                  </button>
                  <button
                    onClick={() => setActiveAngle("down_the_line")}
                    className={cn(
                      "px-4 py-2.5 text-[10px] font-black uppercase tracking-widest rounded-lg transition-all",
                      activeAngle === "down_the_line" 
                        ? "bg-emerald-500 text-slate-950 shadow-lg" 
                        : "text-slate-500 hover:text-slate-300"
                    )}
                  >
                    DTL
                  </button>
                </div>
              )}
            </div>

            <div className="flex-1 bg-slate-950/50 p-6 flex flex-col items-center justify-center min-h-[500px]">
              {activeTab === "annotated" ? (
                <AnnotatedVideo sessionId={sessionId} angle={isDual ? activeAngle : undefined} />
              ) : (
                <SlowMoTab sessionId={sessionId} angle={isDual ? activeAngle : undefined} />
              )}
            </div>

            {/* DL Actions */}
            <div className="p-4 bg-slate-950 border-t border-slate-800 flex flex-wrap justify-end gap-3">
              <a
                href={getVideoDownloadUrl(sessionId, "annotated", isDual ? activeAngle : undefined)}
                className="px-4 py-2 bg-slate-800 hover:bg-emerald-500/20 hover:text-emerald-400 text-slate-300 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 border border-slate-700 hover:border-emerald-500/50"
              >
                <Download className="w-4 h-4" /> Annotated MP4
              </a>
              <a
                href={getVideoDownloadUrl(sessionId, "slowmo", isDual ? activeAngle : undefined)}
                 className="px-4 py-2 bg-slate-800 hover:bg-cyan-500/20 hover:text-cyan-400 text-slate-300 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 border border-slate-700 hover:border-cyan-500/50"
              >
                <Download className="w-4 h-4" /> Slow-Mo MP4
              </a>
            </div>
          </div>

           {/* Metrics Grid */}
          <div className="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl p-6">
            <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
              <Activity className="w-5 h-5 text-emerald-400" />
              Biomechanics
            </h3>
            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
              <MetricsPanel
                metrics={session.metrics}
                thresholds={session.active_thresholds}
                scores={session.scores}
              />
            </div>
          </div>
          
        </motion.div>

        {/* Coaching Section Full Width */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl">
            <CoachingOutput items={session.coaching_output} />
          </div>
        </motion.div>
      </div>
    </div>
  );
}
