/**
 * Score card — overall score and performance band.
 *
 * See data-schema.md §1 scores section.
 */

"use client";

import type { Scores } from "@/lib/types";

interface ScoreCardProps {
  scores: Scores | null;
}

function getBandStyle(band: string | null | undefined): string {
  switch (band) {
    case "Advanced": return "text-green-400 bg-green-500/10 border-green-500/20";
    case "Proficient": return "text-cyan-400 bg-cyan-500/10 border-cyan-500/20";
    case "Developing": return "text-amber-400 bg-amber-500/10 border-amber-500/20";
    default: return "text-white/40 bg-white/5 border-white/10";
  }
}

function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-400";
  if (score >= 60) return "text-cyan-400";
  if (score >= 40) return "text-amber-400";
  return "text-red-400";
}

export default function ScoreCard({ scores }: ScoreCardProps) {
  if (!scores?.overall) {
    return null;
  }

  return (
    <div className="flex items-center gap-4">
      <div className="text-right">
        <div className={`text-3xl font-bold tabular-nums ${getScoreColor(scores.overall)}`}>
          {Math.round(scores.overall)}
        </div>
        <div className="text-[10px] text-white/30 uppercase tracking-wider">Score</div>
      </div>
      {scores.bandOverall && (
        <div className={`px-3 py-1.5 rounded-lg border text-xs font-semibold ${getBandStyle(scores.bandOverall)}`}>
          {scores.bandOverall}
        </div>
      )}
    </div>
  );
}
