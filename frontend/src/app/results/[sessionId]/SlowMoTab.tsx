/**
 * Slow-mo video tab — the plain slow-motion deliverable.
 */

"use client";

import VideoPlayer from "@/components/VideoPlayer";
import { getVideoStreamUrl } from "@/lib/api";

interface SlowMoTabProps {
  sessionId: string;
}

export default function SlowMoTab({ sessionId }: SlowMoTabProps) {
  const src = getVideoStreamUrl(sessionId, "slowmo");

  return (
    <VideoPlayer
      src={src}
      title="Slow Motion"
      className="aspect-video"
    />
  );
}
