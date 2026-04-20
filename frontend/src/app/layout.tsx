import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Golf Trainer AI — Swing Analysis",
  description:
    "AI-powered golf swing analysis. Upload your video, get professional coaching — skeleton overlays, biomechanical metrics, and personalised feedback.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-gradient-radial min-h-screen antialiased">
        <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-xl bg-[#0A0E17]/80 border-b border-white/5">
          <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <a href="/" className="flex items-center gap-3 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 group-hover:shadow-cyan-500/40 transition-shadow">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
                  <circle cx="12" cy="5" r="2" />
                  <path d="M12 7v6" />
                  <path d="M8 21l4-8 4 8" />
                  <path d="M6 13l6-3" />
                </svg>
              </div>
              <span className="text-lg font-bold tracking-tight">
                Golf Trainer <span className="text-cyan-400">AI</span>
              </span>
            </a>
            <span className="text-xs text-white/30 font-mono">v1.3</span>
          </div>
        </nav>
        <main className="pt-20 min-h-screen">{children}</main>
      </body>
    </html>
  );
}
