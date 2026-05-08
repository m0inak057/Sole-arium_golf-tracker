/**
 * Slow-mo video tab — the plain slow-motion deliverable.
 */

"use client";

import VideoPlayer from "@/components/VideoPlayer";
import { getVideoStreamUrl } from "@/lib/api";

interface SlowMoTabProps {
  sessionId: string;
  angle?: "face_on" | "down_the_line";
}

export default function SlowMoTab({ sessionId, angle }: SlowMoTabProps) {
  const src = getVideoStreamUrl(sessionId, "slowmo", angle);

  return (
    <VideoPlayer
      src={src}
      title={angle ? `Slow Motion (${angle.replace("_", " ")})` : "Slow Motion"}
      className="aspect-video"
    />
  );
}
