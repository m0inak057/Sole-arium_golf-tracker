/**
 * Upload page — the landing page.
 *
 * Two inputs: video file + gender radio. Nothing else.
 * See PRD §3 and rules.md §1.
 */

"use client";

import { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { createSession, ApiError } from "@/lib/api";

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [gender, setGender] = useState<"male" | "female" | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback((f: File) => {
    const ext = f.name.split(".").pop()?.toLowerCase();
    if (ext !== "mp4" && ext !== "mov") {
      setError("Only .mp4 and .mov files are supported.");
      return;
    }
    setFile(f);
    setError(null);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile],
  );

  const handleSubmit = async () => {
    if (!file || !gender) return;

    setIsUploading(true);
    setError(null);

    try {
      const result = await createSession(file, gender);
      router.push(`/progress/${result.session_id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
      setIsUploading(false);
    }
  };

  const isReady = file !== null && gender !== null && !isUploading;

  return (
    <div className="max-w-2xl mx-auto px-6 py-16 animate-fade-in">
      {/* Hero */}
      <div className="text-center mb-12">
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-4">
          Analyse Your{" "}
          <span className="bg-gradient-to-r from-cyan-400 to-cyan-300 bg-clip-text text-transparent">
            Swing
          </span>
        </h1>
        <p className="text-lg text-white/50 max-w-md mx-auto">
          Upload a swing video and get professional-grade coaching with AI-powered biomechanical analysis.
        </p>
      </div>

      {/* Upload card */}
      <div className="glass-card p-8 glow-cyan">
        {/* Dropzone */}
        <div
          role="button"
          tabIndex={0}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => { if (e.key === "Enter") fileInputRef.current?.click(); }}
          className={`
            relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
            transition-all duration-300 mb-8
            ${isDragging
              ? "border-cyan-400 bg-cyan-400/5 scale-[1.01]"
              : file
                ? "border-green-500/40 bg-green-500/5"
                : "border-white/15 hover:border-white/30 dropzone-pulse"
            }
          `}
          id="video-dropzone"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp4,.mov"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
            id="video-input"
          />

          {file ? (
            <div className="space-y-2">
              <div className="w-14 h-14 mx-auto rounded-full bg-green-500/10 flex items-center justify-center">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#22C55E" strokeWidth="2" strokeLinecap="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <p className="font-semibold text-white">{file.name}</p>
              <p className="text-sm text-white/40">
                {(file.size / (1024 * 1024)).toFixed(1)} MB
              </p>
              <button
                onClick={(e) => { e.stopPropagation(); setFile(null); }}
                className="text-xs text-red-400/70 hover:text-red-400 transition-colors mt-1"
              >
                Remove
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="w-14 h-14 mx-auto rounded-full bg-white/5 flex items-center justify-center">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white/40">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <p className="font-medium text-white/70">
                Drop your swing video here
              </p>
              <p className="text-sm text-white/30">or click to browse — .mp4 or .mov</p>
            </div>
          )}
        </div>

        {/* Gender selection */}
        <div className="mb-8">
          <label className="block text-sm font-medium text-white/60 mb-3">
            Golfer
          </label>
          <div className="grid grid-cols-2 gap-3">
            {(["male", "female"] as const).map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGender(g)}
                className={`
                  py-3 rounded-xl font-medium text-sm transition-all duration-200 border
                  ${gender === g
                    ? "bg-cyan-500/15 border-cyan-400/50 text-cyan-300 shadow-lg shadow-cyan-500/10"
                    : "bg-white/3 border-white/10 text-white/50 hover:border-white/20 hover:text-white/70"
                  }
                `}
                id={`gender-${g}`}
              >
                {g === "male" ? "♂ Male" : "♀ Female"}
              </button>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!isReady}
          className={`
            w-full py-4 rounded-xl font-semibold text-base transition-all duration-300
            ${isReady
              ? "bg-gradient-to-r from-cyan-500 to-cyan-400 text-black hover:shadow-lg hover:shadow-cyan-500/25 hover:scale-[1.01] active:scale-[0.99]"
              : "bg-white/5 text-white/20 cursor-not-allowed"
            }
          `}
          id="submit-button"
        >
          {isUploading ? (
            <span className="flex items-center justify-center gap-3">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Uploading…
            </span>
          ) : (
            "Analyse Swing"
          )}
        </button>
      </div>

      {/* Footer note */}
      <p className="text-center text-xs text-white/20 mt-8">
        Your video is processed securely. Two camera angles supported: Face-On and Down-the-Line.
      </p>
    </div>
  );
}
