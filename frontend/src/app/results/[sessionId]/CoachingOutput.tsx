/**
 * Coaching output — personalised feedback from Agent 5.
 */

"use client";

import type { CoachingItem } from "@/lib/types";
import { motion } from "framer-motion";
import { Target, AlertTriangle, Lightbulb, Dumbbell, Focus } from "lucide-react";
import { cn } from "@/lib/utils";

interface CoachingOutputProps {
  items: CoachingItem[] | null;
}

function getSeverityStyle(severity: string) {
  switch (severity) {
    case "high":
      return {
        border: "border-rose-500/20",
        badge: "text-rose-400",
        badgeBg: "bg-rose-500/10",
        icon: <AlertTriangle className="w-4 h-4 text-rose-400" />
      };
    case "medium":
      return {
        border: "border-amber-500/20",
        badge: "text-amber-400",
        badgeBg: "bg-amber-500/10",
        icon: <Target className="w-4 h-4 text-amber-400" />
      };
    default:
      return {
        border: "border-emerald-500/20",
        badge: "text-emerald-400",
        badgeBg: "bg-emerald-500/10",
        icon: <Lightbulb className="w-4 h-4 text-emerald-400" />
      };
  }
}

export default function CoachingOutput({ items }: CoachingOutputProps) {
  if (!items || items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-slate-500 bg-slate-900 border border-slate-800 rounded-3xl">
        <Target className="w-12 h-12 mb-4 opacity-50" />
        <p>No coaching feedback available yet.</p>
      </div>
    );
  }

  const sortedItems = [...items].sort((a, b) => a.priority - b.priority);
  const priorityItem = sortedItems[0];
  const supporting = sortedItems.slice(1);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
        <Target className="w-6 h-6 text-emerald-400" />
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Personalized Coaching</h2>
          <p className="text-sm text-slate-400">AI-generated improvement plan</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Priority-1 focus item */}
        {priorityItem && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className={cn(
              "md:col-span-2 lg:col-span-3 p-6 rounded-2xl border relative overflow-hidden bg-slate-900",
               getSeverityStyle(priorityItem.severity).border
            )}
          >
            <div className="absolute top-0 left-0 w-1 bg-emerald-500 h-full" />
            <div className="absolute -top-10 -right-10 w-40 h-40 bg-emerald-500/5 rounded-full blur-3xl" />
            
            <div className="flex items-center gap-3 mb-4">
              <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-slate-900 bg-emerald-400 px-3 py-1 rounded-full shadow-[0_0_10px_rgba(52,211,153,0.3)]">
                <Focus className="w-3 h-3" /> #1 Focus
              </span>
              <span className={cn(
                "text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full",
                getSeverityStyle(priorityItem.severity).badge,
                getSeverityStyle(priorityItem.severity).badgeBg
              )}>
                {priorityItem.severity} priority
              </span>
            </div>
            
            <h3 className="text-xl font-bold text-slate-100 mb-3 pr-8">
              {priorityItem.title}
            </h3>
            
            <p className="text-slate-400 leading-relaxed mb-6 max-w-4xl text-sm md:text-base">
              {priorityItem.explanation}
            </p>
            
            {priorityItem.drillSuggestion && (
              <div className="flex items-start gap-4 p-5 rounded-xl bg-slate-950/50 border border-slate-800">
                <Dumbbell className="w-6 h-6 text-cyan-400 shrink-0 mt-1" />
                <div>
                  <h4 className="text-sm font-semibold text-cyan-400 mb-1">Recommended Drill</h4>
                  <p className="text-sm text-slate-300 leading-relaxed">
                    {priorityItem.drillSuggestion}
                  </p>
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* Supporting items */}
        {supporting.map((item, idx) => {
          const style = getSeverityStyle(item.severity);
          return (
             <motion.div
              key={item.priority}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * (idx + 1) }}
              className={cn(
                "p-6 rounded-2xl border bg-slate-900/50 flex flex-col hover:bg-slate-900 transition-colors duration-300",
                style.border
              )}
            >
              <div className="flex items-center gap-2 mb-4">
                {style.icon}
                <span className={cn(
                  "text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full",
                  style.badge, style.badgeBg
                )}>
                  #{item.priority} Priority
                </span>
              </div>
              
              <h3 className="text-base font-bold text-slate-200 mb-2">
                {item.title}
              </h3>
              
              <p className="text-sm text-slate-400 leading-relaxed flex-grow mb-4">
                {item.explanation}
              </p>
              
              {item.drillSuggestion && (
                <div className="mt-auto pt-4 border-t border-slate-800/50">
                  <p className="text-xs text-slate-300 flex items-start gap-2">
                    <Dumbbell className="w-3 h-3 text-cyan-400 shrink-0 mt-0.5" />
                    <span>{item.drillSuggestion}</span>
                  </p>
                </div>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
