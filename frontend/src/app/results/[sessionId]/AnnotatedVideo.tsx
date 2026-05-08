/**
 * Annotated video component — the primary deliverable.
 */

"use client";

import VideoPlayer from "@/components/VideoPlayer";
import { getVideoStreamUrl } from "@/lib/api";

interface AnnotatedVideoProps {
  sessionId: string;
  angle?: "face_on" | "down_the_line";
}

export default function AnnotatedVideo({ sessionId, angle }: AnnotatedVideoProps) {
  const src = getVideoStreamUrl(sessionId, "annotated", angle);

  return (
    <VideoPlayer
      src={src}
      title={angle ? `Annotated Analysis (${angle.replace("_", " ")})` : "Annotated Analysis"}
      className="aspect-video"
    />
  );
}
