/**
 * Coaching output — personalised feedback from Agent 5.
 *
 * Priority-1 item is displayed prominently. Supporting items beneath.
 * See PRD §9 and data-schema.md §5.
 */

"use client";

import type { CoachingItem } from "@/lib/types";

interface CoachingOutputProps {
  items: CoachingItem[] | null;
}

function getSeverityStyle(severity: string): { border: string; badge: string; badgeBg: string } {
  switch (severity) {
    case "high":
      return {
        border: "border-red-500/20",
        badge: "text-red-400",
        badgeBg: "bg-red-500/10",
      };
    case "medium":
      return {
        border: "border-amber-500/20",
        badge: "text-amber-400",
        badgeBg: "bg-amber-500/10",
      };
    default:
      return {
        border: "border-green-500/20",
        badge: "text-green-400",
        badgeBg: "bg-green-500/10",
      };
  }
}

export default function CoachingOutput({ items }: CoachingOutputProps) {
  if (!items || items.length === 0) {
    return (
      <div className="glass-card p-8 text-center text-white/30">
        No coaching feedback available yet.
      </div>
    );
  }

  const priorityItem = items.find((i) => i.priority === 1);
  const supporting = items.filter((i) => i.priority !== 1);

  return (
    <div className="glass-card overflow-hidden">
      <div className="px-6 py-4 border-b border-white/5">
        <h2 className="text-lg font-semibold">Coaching</h2>
        <p className="text-xs text-white/30 mt-1">AI-generated recommendations</p>
      </div>

      <div className="p-4 space-y-3">
        {/* Priority-1 focus item */}
        {priorityItem && (
          <div className={`p-4 rounded-xl border ${getSeverityStyle(priorityItem.severity).border} bg-white/[0.02]`}>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 bg-cyan-400/10 px-2 py-0.5 rounded-full">
                Focus
              </span>
              <span className={`text-[10px] font-bold uppercase tracking-wider ${getSeverityStyle(priorityItem.severity).badge} ${getSeverityStyle(priorityItem.severity).badgeBg} px-2 py-0.5 rounded-full`}>
                {priorityItem.severity}
              </span>
            </div>
            <h3 className="text-sm font-semibold text-white mb-2">
              {priorityItem.title}
            </h3>
            <p className="text-xs text-white/50 leading-relaxed mb-3">
              {priorityItem.explanation}
            </p>
            {priorityItem.drillSuggestion && (
              <div className="text-xs text-cyan-400/70 bg-cyan-400/5 rounded-lg p-3">
                <span className="font-medium text-cyan-400">Drill:</span>{" "}
                {priorityItem.drillSuggestion}
              </div>
            )}
          </div>
        )}

        {/* Supporting items */}
        {supporting.map((item) => {
          const style = getSeverityStyle(item.severity);
          return (
            <div
              key={item.priority}
              className={`p-4 rounded-xl border ${style.border} bg-white/[0.01]`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-[10px] font-bold uppercase tracking-wider ${style.badge} ${style.badgeBg} px-2 py-0.5 rounded-full`}>
                  {item.severity}
                </span>
              </div>
              <h3 className="text-sm font-medium text-white/80 mb-1">
                {item.title}
              </h3>
              <p className="text-xs text-white/40 leading-relaxed">
                {item.explanation}
              </p>
              {item.drillSuggestion && (
                <p className="text-xs text-white/30 mt-2">
                  <span className="font-medium">Drill:</span> {item.drillSuggestion}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
