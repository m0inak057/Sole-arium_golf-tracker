/**
 * Reusable video player component with controls.
 */

"use client";

import { useRef } from "react";

interface VideoPlayerProps {
  src: string;
  title?: string;
  className?: string;
}

export default function VideoPlayer({ src, title, className = "" }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  return (
    <div className={`relative rounded-2xl overflow-hidden bg-black/50 backdrop-blur-sm border border-white/10 ${className}`}>
      {title && (
        <div className="absolute top-4 left-4 z-10 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-lg">
          <span className="text-sm font-medium text-white/90">{title}</span>
        </div>
      )}
      <video
        ref={videoRef}
        src={src}
        controls
        playsInline
        className="w-full h-full object-contain"
      >
        <track kind="captions" />
      </video>
    </div>
  );
}
