/**
 * Annotated video component — the primary deliverable.
 */

"use client";

import { useState, useEffect } from "react";
import VideoPlayer from "@/components/VideoPlayer";
import { getVideoStreamUrl } from "@/lib/api";
import { AlertCircle } from "lucide-react";

interface AnnotatedVideoProps {
  sessionId: string;
  angle?: "face_on" | "down_the_line";
}

export default function AnnotatedVideo({ sessionId, angle }: AnnotatedVideoProps) {
  const src = getVideoStreamUrl(sessionId, "annotated", angle);
  const [videoError, setVideoError] = useState(false);

  useEffect(() => {
    setVideoError(false);
  }, [src]);

  if (videoError) {
    return (
      <div className="flex flex-col items-center justify-center w-full h-full gap-4 text-center p-6">
        <div className="w-16 h-16 bg-amber-500/10 rounded-full flex items-center justify-center">
          <AlertCircle className="w-8 h-8 text-amber-500" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-slate-200 mb-2">Video Not Available</h3>
          <p className="text-slate-400 text-sm">
            {angle
              ? `The ${angle.replace("_", " ")} video is still processing. Please check back in a moment or refresh the page.`
              : "The video is still processing. Please refresh the page."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <VideoPlayer
      src={src}
      title={angle ? `Annotated Analysis (${angle.replace("_", " ")})` : "Annotated Analysis"}
      className="aspect-video"
      onError={() => setVideoError(true)}
    />
  );
}
