/**
 * Reusable video player component with controls.
 */

"use client";

import { useRef, useState, useEffect } from "react";
import { Play, Pause, Maximize, Volume2, Video } from "lucide-react";
import { cn } from "@/lib/utils";

interface VideoPlayerProps {
  src: string;
  title?: string;
  className?: string;
  onError?: () => void;
}

export default function VideoPlayer({ src, title, className = "", onError }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleError = () => onError?.();

    video.addEventListener("play", handlePlay);
    video.addEventListener("pause", handlePause);
    video.addEventListener("error", handleError);

    return () => {
      video.removeEventListener("play", handlePlay);
      video.removeEventListener("pause", handlePause);
      video.removeEventListener("error", handleError);
    };
  }, [onError]);

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
    }
  };

  return (
    <div 
      className={cn("group relative rounded-3xl overflow-hidden bg-slate-950/80 border border-slate-800 shadow-2xl transition-all duration-500 hover:border-slate-700/50 hover:shadow-cyan-500/10", className)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Top Header overlay */}
      <div className="absolute top-0 left-0 right-0 p-4 z-10 bg-gradient-to-b from-black/80 to-transparent pointer-events-none flex items-start justify-between opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        {title && (
          <div className="flex items-center gap-2 bg-slate-900/60 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10">
            <Video className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-semibold text-slate-200 tracking-wide uppercase">{title}</span>
          </div>
        )}
      </div>

      <video
        ref={videoRef}
        src={src}
        controls
        playsInline
        className="w-full h-full object-contain cursor-pointer"
        onClick={togglePlay}
        crossOrigin="anonymous"
      >
        <track kind="captions" />
      </video>

      {/* Central Play Button Overlay when paused */}
      {!isPlaying && (
        <div className="absolute inset-0 z-20 flex items-center justify-center pointer-events-none group-hover:bg-black/10 transition-colors">
          <div className={cn(
            "w-20 h-20 flex items-center justify-center rounded-full bg-cyan-500/90 text-slate-950 backdrop-blur-md shadow-[0_0_30px_rgba(34,211,238,0.3)] transition-transform duration-300",
            isHovered ? "scale-110" : "scale-100 opacity-90"
          )}>
            <Play className="w-8 h-8 ml-1" fill="currentColor" />
          </div>
        </div>
      )}
    </div>
  );
}
