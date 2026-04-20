/**
 * Annotated video component — the primary deliverable.
 */

"use client";

import VideoPlayer from "@/components/VideoPlayer";
import { getVideoStreamUrl } from "@/lib/api";

interface AnnotatedVideoProps {
  sessionId: string;
}

export default function AnnotatedVideo({ sessionId }: AnnotatedVideoProps) {
  const src = getVideoStreamUrl(sessionId, "annotated");

  return (
    <VideoPlayer
      src={src}
      title="Annotated Analysis"
      className="aspect-video"
    />
  );
}
