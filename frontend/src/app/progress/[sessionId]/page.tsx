/**
 * Progress page — polls session status and shows pipeline progress.
 */

"use client";

import { useParams, useRouter } from "next/navigation";
import { useSessionPolling } from "@/hooks/useSessionPolling";
import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, ChevronRight, AlertCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

const PHASE_LABELS: Record<string, string> = {
  uploaded: "Preparing Engine...",
  agent1_running: "Analysing video metadata...",
  agent1_done: "Video intelligence complete",
  phase1_running: "Detecting swing impact...",
  phase1_done: "Impact detected",
  agent2_running: "Calibrating body proportions...",
  agent2_done: "Body calibration complete",
  phase2_running: "Extracting 3D keypoints...",
  phase2_done: "Keypoints extracted",
  phase3_running: "Analysing setup posture...",
  phase3_done: "Setup analysis complete",
  agent3_running: "Classifying shot type...",
  agent3_done: "Shot type classified",
  phase4_running: "Computing biomechanics...",
  phase4_done: "Metrics calculated",
  agent4_running: "Adapting thresholds...",
  agent4_done: "Thresholds set",
  phase5_running: "Scoring performance...",
  phase5_done: "Scoring complete",
  agent5_running: "Generating coaching insights...",
  agent5_done: "Coaching complete",
  phase7_running: "Rendering slow-motion...",
  phase7_done: "Slow-motion ready",
  phase8_running: "Creating AI annotated overlay...",
  phase8_done: "Overlay rendered",
  complete: "Analysis 100% complete!",
  failed: "Analysis Failed :(",
};

export default function ProgressPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const { data, error } = useSessionPolling(sessionId);

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
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 relative overflow-hidden selection:bg-emerald-500/30">
      
      {/* Background Gradients */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-emerald-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-cyan-500/5 rounded-full blur-[100px] pointer-events-none" />

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="w-full max-w-md z-10 flex flex-col items-center"
      >
        
        {/* Progress Ring */}
        <div className="relative w-64 h-64 mb-12 flex items-center justify-center">
          
          {/* Subtle Glow Behind */}
          <div className="absolute inset-0 bg-emerald-500/20 blur-2xl rounded-full scale-75" />

          <svg className="absolute w-full h-full -rotate-90 transform-origin-center transition-all duration-500" viewBox="0 0 100 100">
            {/* Track bg circle */}
            <circle
              cx="50" cy="50" r="46"
              fill="none"
              stroke="#0f172a" 
              strokeWidth="4"
            />
            {/* Outline highlight (Progress) */}
            <motion.circle
              cx="50" cy="50" r="46"
              fill="none"
              stroke={isFailed ? "#f43f5e" : "#10b981"}
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray="289"
              initial={{ strokeDashoffset: 289 }}
              animate={{ strokeDashoffset: 289 - (289 * progress) / 100 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              style={{ filter: `drop-shadow(0 0 8px ${isFailed ? "rgba(244,63,94,0.6)" : "rgba(16,185,129,0.6)"})` }}
            />
          </svg>
          
          <div className="absolute z-10 flex flex-col items-center justify-center text-slate-100 font-bold tabular-nums tracking-tighter">
            <span className="text-5xl drop-shadow-md flex items-baseline">
              <AnimatePresence mode="popLayout">
                <motion.span
                  key={progress}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  transition={{ duration: 0.2 }}
                >
                  {progress}
                </motion.span>
              </AnimatePresence>
              <span className="text-2xl text-slate-500 ml-1">%</span>
            </span>
          </div>
        </div>

        {/* Text Section */}
        <div className="text-center space-y-4">
          <h2 className="text-2xl font-bold text-slate-100 tracking-tight">
            {isFailed ? "Analysis Failed" : status === "complete" ? "Analysis Complete!" : "Analyzing Your Swing"}
          </h2>

          <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-4 min-w-[320px] backdrop-blur-xl shadow-xl flex items-center justify-center gap-3">
             {isFailed ? (
                <AlertCircle className="w-5 h-5 text-rose-500" />
             ) : status === "complete" ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-500" />
             ) : (
                <RefreshCw className="w-5 h-5 text-emerald-400 animate-spin" />
             )}
             
             <span className={cn(
               "font-medium", 
               isFailed ? "text-rose-400" : status === "complete" ? "text-emerald-400" : "text-slate-300 animate-pulse"
             )}>
                {label}
             </span>
          </div>

          <p className="text-xs text-slate-500 font-mono tracking-widest uppercase mt-4">
            SESSION: {sessionId.substring(0, 8)}...
          </p>
        </div>

        {/* Error state details & action */}
        {error && (
          <div className="mt-8 text-center p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-sm text-rose-400 max-w-sm">
            {error}
          </div>
        )}

        <AnimatePresence>
          {isFailed && (
            <motion.div 
               initial={{ opacity: 0, y: 10 }}
               animate={{ opacity: 1, y: 0 }}
               className="mt-8"
            >
              <button
                onClick={() => router.push("/")}
                className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-medium transition-colors flex items-center justify-center gap-2"
              >
                Try Again <ChevronRight className="w-4 h-4" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

      </motion.div>
    </div>
  );
}
