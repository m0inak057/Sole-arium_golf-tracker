/**
 * Upload page — Enhanced for Dual Camera Analysis.
 *
 * Supports single video upload (legacy) and dual camera upload (new).
 * Uses high-end animations and clear visual hierarchy for pro-level UX.
 */

"use client";

import { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { createSession, createDualSession, ApiError } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { 
  UploadCloud, 
  FileVideo, 
  Activity, 
  Users, 
  ChevronRight, 
  CheckCircle2, 
  AlertCircle, 
  Camera, 
  Monitor,
  ArrowRightLeft,
  Info
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function UploadPage() {
  const router = useRouter();
  const faceOnInputRef = useRef<HTMLInputElement>(null);
  const dtlInputRef = useRef<HTMLInputElement>(null);
  const singleInputRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<"single" | "dual">("dual");
  const [faceOnFile, setFaceOnFile] = useState<File | null>(null);
  const [dtlFile, setDtlFile] = useState<File | null>(null);
  const [singleFile, setSingleFile] = useState<File | null>(null);
  
  const [gender, setGender] = useState<"male" | "female" | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateFile = (f: File) => {
    const ext = f.name.split(".").pop()?.toLowerCase();
    if (ext !== "mp4" && ext !== "mov") {
      setError("Only .mp4 and .mov files are supported.");
      return false;
    }
    return true;
  };

  const handleUpload = async () => {
    if (!gender) {
      setError("Please select golfer baseline (gender).");
      return;
    }

    if (mode === "dual") {
      if (!faceOnFile || !dtlFile) {
        setError("Please provide both Face-On and Down-The-Line videos for dual analysis.");
        return;
      }
    } else {
      if (!singleFile) {
        setError("Please provide a video file.");
        return;
      }
    }

    setIsUploading(true);
    setError(null);

    try {
      let session_id: string;
      if (mode === "dual" && faceOnFile && dtlFile) {
        const res = await createDualSession(faceOnFile, dtlFile, gender);
        session_id = res.session_id;
      } else if (singleFile) {
        const res = await createSession(singleFile, gender);
        session_id = res.session_id;
      } else {
        throw new Error("Invalid state");
      }

      setTimeout(() => {
        router.push(`/progress/${session_id}`);
      }, 800);
    } catch (err) {
      setIsUploading(false);
      if (err instanceof ApiError) {
        setError(err.message || "Failed to create session.");
      } else {
        setError("An unexpected error occurred.");
      }
    }
  };

  const VideoDropzone = ({ 
    file, 
    setFile, 
    inputRef, 
    label, 
    description, 
    icon: Icon 
  }: { 
    file: File | null, 
    setFile: (f: File | null) => void, 
    inputRef: React.RefObject<HTMLInputElement | null>,
    label: string,
    description: string,
    icon: any
  }) => {
    const [isDragging, setIsDragging] = useState(false);

    return (
      <div className="flex flex-col space-y-2">
        <div className="flex items-center justify-between px-1">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">{label}</span>
          {file && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />}
        </div>
        <div 
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files?.[0] && validateFile(e.dataTransfer.files[0])) {
              setFile(e.dataTransfer.files[0]);
            }
          }}
          onClick={() => !file && inputRef.current?.click()}
          className={cn(
            "relative group flex flex-col items-center justify-center p-6 rounded-2xl border-2 border-dashed transition-all duration-300 text-center cursor-pointer min-h-[160px]",
            isDragging ? "border-emerald-500 bg-emerald-500/5 shadow-[0_0_15px_rgba(16,185,129,0.1)]" : "border-slate-800 hover:border-slate-700 bg-slate-950/40",
            file ? "border-emerald-500/40 bg-emerald-500/5" : ""
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".mp4,.mov"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f && validateFile(f)) setFile(f);
            }}
            className="hidden"
          />
          
          <AnimatePresence mode="wait">
            {file ? (
              <motion.div 
                key="file"
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="flex flex-col items-center"
              >
                <div className="w-12 h-12 bg-emerald-500/20 rounded-full flex items-center justify-center mb-3">
                  <FileVideo className="w-6 h-6 text-emerald-400" />
                </div>
                <p className="font-semibold text-slate-200 text-sm truncate max-w-[150px]">{file.name}</p>
                <button 
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                  className="mt-3 text-[10px] font-bold uppercase tracking-widest text-slate-500 hover:text-emerald-400 transition-colors"
                >
                  Change
                </button>
              </motion.div>
            ) : (
              <motion.div 
                key="empty"
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="flex flex-col items-center"
              >
                <div className="w-12 h-12 bg-slate-900 border border-slate-800 rounded-full flex items-center justify-center mb-3 group-hover:scale-110 transition-transform shadow-lg">
                  <Icon className="w-6 h-6 text-slate-400 group-hover:text-emerald-400" />
                </div>
                <p className="text-sm font-semibold text-slate-300">{description}</p>
                <p className="text-[10px] text-slate-600 mt-1 uppercase tracking-widest font-bold">Select Video</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 flex flex-col pt-20 md:pt-0 md:justify-center px-4 overflow-hidden relative selection:bg-emerald-500/30">
      {/* Dynamic Background */}
      <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] rounded-full bg-emerald-600/5 blur-[120px] pointer-events-none animate-pulse" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] rounded-full bg-blue-600/5 blur-[120px] pointer-events-none" />

      <main className="max-w-6xl w-full mx-auto relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-16 items-center">
        
        {/* Left Content */}
        <motion.div 
          initial={{ opacity: 0, x: -40 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="lg:col-span-5 flex flex-col space-y-8"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 w-fit backdrop-blur-md">
            <Activity className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-bold text-emerald-400 uppercase tracking-widest">Next-Gen Swing Intel</span>
          </div>
          
          <div className="space-y-4">
            <h1 className="text-6xl md:text-7xl font-black tracking-tight leading-[0.95]">
              PRO<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-br from-emerald-300 via-emerald-400 to-cyan-500">
                ANALYTICS.
              </span>
            </h1>
            <p className="text-xl text-slate-400 leading-relaxed max-w-lg font-medium">
              Precision biomechanical analysis for serious golfers. Capture every angle, optimize every move.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-6 pt-4">
            <div className="space-y-2">
              <div className="text-2xl font-bold text-slate-100 italic">13+</div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Core Metrics</div>
            </div>
            <div className="space-y-2">
              <div className="text-2xl font-bold text-slate-100 italic">90FPS</div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Slow-Mo</div>
            </div>
          </div>

          <div className="flex flex-col gap-4 p-5 rounded-2xl bg-slate-900/40 border border-slate-800/50 backdrop-blur-sm">
            <div className="flex gap-3 items-start">
              <div className="mt-1 p-1 bg-emerald-500/20 rounded">
                <Info className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <p className="text-sm text-slate-400 leading-snug">
                For the best results, use <span className="text-slate-200 font-semibold">Dual Camera</span> mode to track both rotation and club-path simultaneously.
              </p>
            </div>
          </div>
        </motion.div>

        {/* Right Upload Panel */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
          className="lg:col-span-7"
        >
          <div className="bg-slate-900/80 backdrop-blur-3xl border border-slate-800/80 p-1 rounded-[2.5rem] shadow-[0_25px_50px_-12px_rgba(0,0,0,0.5)] overflow-hidden">
            <div className="p-8 md:p-10 flex flex-col h-full">
              
              {/* Header & Mode Switch */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
                <h2 className="text-3xl font-black italic tracking-tight text-white uppercase">Upload Lab</h2>
                
                <div className="flex p-1 bg-slate-950 rounded-xl border border-slate-800 w-fit self-start">
                  <button 
                    onClick={() => setMode("dual")}
                    className={cn(
                      "px-4 py-2 rounded-lg text-xs font-black uppercase tracking-widest transition-all",
                      mode === "dual" ? "bg-emerald-500 text-slate-950 shadow-lg" : "text-slate-500 hover:text-slate-300"
                    )}
                  >
                    Dual Cam
                  </button>
                  <button 
                    onClick={() => setMode("single")}
                    className={cn(
                      "px-4 py-2 rounded-lg text-xs font-black uppercase tracking-widest transition-all",
                      mode === "single" ? "bg-emerald-500 text-slate-950 shadow-lg" : "text-slate-500 hover:text-slate-300"
                    )}
                  >
                    Single
                  </button>
                </div>
              </div>

              {/* Upload Grid */}
              <div className="flex-1">
                <AnimatePresence mode="wait">
                  {mode === "dual" ? (
                    <motion.div 
                      key="dual"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="grid grid-cols-1 md:grid-cols-2 gap-6"
                    >
                      <VideoDropzone 
                        label="Angle 01"
                        description="Face-On Video"
                        file={faceOnFile}
                        setFile={setFaceOnFile}
                        inputRef={faceOnInputRef}
                        icon={Camera}
                      />
                      <VideoDropzone 
                        label="Angle 02"
                        description="Down-The-Line"
                        file={dtlFile}
                        setFile={setDtlFile}
                        inputRef={dtlInputRef}
                        icon={Monitor}
                      />
                    </motion.div>
                  ) : (
                    <motion.div 
                      key="single"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                    >
                      <VideoDropzone 
                        label="Standard Analysis"
                        description="Upload Swing Video"
                        file={singleFile}
                        setFile={setSingleFile}
                        inputRef={singleInputRef}
                        icon={UploadCloud}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Error Box */}
                <AnimatePresence>
                  {error && (
                    <motion.div 
                      initial={{ opacity: 0, y: -10 }} 
                      animate={{ opacity: 1, y: 0 }} 
                      exit={{ opacity: 0, y: -10 }}
                      className="mt-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm font-bold flex items-center gap-3"
                    >
                      <AlertCircle className="w-4 h-4 shrink-0" />
                      {error}
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Settings & Action */}
                <div className="mt-10 pt-8 border-t border-slate-800/50">
                  <div className="flex flex-col md:flex-row items-center gap-8">
                    <div className="flex-1 w-full">
                      <label className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 mb-4 block">Golfer Baseline</label>
                      <div className="grid grid-cols-2 gap-3">
                        {(["male", "female"] as const).map((g) => (
                          <button
                            key={g}
                            type="button"
                            onClick={() => setGender(g)}
                            className={cn(
                              "py-3 rounded-xl border-2 font-black uppercase tracking-widest text-[11px] transition-all",
                              gender === g 
                                ? "bg-emerald-500/10 border-emerald-500 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.2)]" 
                                : "bg-slate-950/50 border-slate-800 text-slate-500 hover:border-slate-700 hover:text-slate-300"
                            )}
                          >
                            {g}
                          </button>
                        ))}
                      </div>
                    </div>
                    
                    <div className="flex-1 w-full pt-4 md:pt-0">
                      <button
                        onClick={handleUpload}
                        disabled={isUploading}
                        className={cn(
                          "w-full h-16 rounded-2xl font-black uppercase tracking-[0.15em] text-sm flex items-center justify-center gap-3 transition-all duration-500 shadow-2xl group",
                          isUploading
                            ? "bg-slate-800 text-slate-600 cursor-wait"
                            : "bg-emerald-500 text-slate-950 hover:bg-emerald-400 hover:shadow-[0_0_30px_rgba(16,185,129,0.4)] hover:-translate-y-1 active:scale-[0.98]"
                        )}
                      >
                        {isUploading ? (
                          <>
                            <div className="w-5 h-5 border-[3px] border-slate-950/20 border-t-slate-950 rounded-full animate-spin" />
                            Calibrating
                          </>
                        ) : (
                          <>
                            Start Session <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          {/* Footer Stats */}
          <div className="mt-8 flex justify-between items-center px-4">
            <div className="flex gap-4">
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Compute Ready</span>
              </div>
            </div>
            <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">v2.4.0-pro-dual</span>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
