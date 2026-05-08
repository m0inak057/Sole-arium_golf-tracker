/**
 * Score card — overall score and performance band.
 */

"use client";

import type { Scores } from "@/lib/types";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface ScoreCardProps {
  scores: Scores | null;
}

function getBandStyle(band: string | null | undefined): string {
  switch (band) {
    case "Advanced": return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
    case "Proficient": return "text-cyan-400 bg-cyan-500/10 border-cyan-500/20";
    case "Developing": return "text-amber-400 bg-amber-500/10 border-amber-500/20";
    default: return "text-slate-400 bg-slate-500/10 border-slate-500/20";
  }
}

function getScoreColor(score: number): string {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-cyan-400";
  if (score >= 40) return "text-amber-400";
  return "text-rose-400";
}

export default function ScoreCard({ scores }: ScoreCardProps) {
  if (!scores?.overall) return null;

  const scoreNum = Math.round(scores.overall);
  const strokeDashoffset = 283 - (283 * scoreNum) / 100;

  return (
    <div className="flex items-center gap-6 bg-slate-900 border border-slate-800 p-4 rounded-2xl shadow-xl backdrop-blur-xl">
      <div className="relative w-16 h-16 flex items-center justify-center">
        {/* Background Track */}
        <svg className="absolute w-full h-full -rotate-90 transform-origin-center" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" fill="none" stroke="#1e293b" strokeWidth="6" />
          <motion.circle
             cx="50" cy="50" r="45"
             fill="none"
             stroke="currentColor"
             className={getScoreColor(scoreNum)}
             strokeWidth="6"
             strokeLinecap="round"
             strokeDasharray="283"
             initial={{ strokeDashoffset: 283 }}
             animate={{ strokeDashoffset }}
             transition={{ duration: 1.5, ease: "easeOut" }}
          />
        </svg>
        <span className={cn("text-2xl font-bold tabular-nums z-10", getScoreColor(scoreNum))}>
          {scoreNum}
        </span>
      </div>

      <div className="flex flex-col gap-1 items-start">
         <span className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold flex items-center gap-1">
           Performance <span className="w-1.5 h-1.5 rounded-full bg-slate-700" />
         </span>
         {scores.bandOverall && (
           <div className={cn("px-3 py-1 rounded-full text-xs font-bold border", getBandStyle(scores.bandOverall))}>
             {scores.bandOverall.toUpperCase()}
           </div>
         )}
      </div>
    </div>
  );
}
