"use client";

import React from "react";
import Link from "next/link";
import { 
  Camera, 
  Sparkles, 
  ArrowRight, 
  BookOpen, 
  Dna, 
  Compass, 
  CheckCircle2, 
  Bookmark, 
  Search,
  ScanEye,
  Layers,
  Heart
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function HomePage() {
  const { user } = useAuth();

  return (
    <div className="flex flex-col">
      {/* HERO SECTION */}
      <section className="relative overflow-hidden pt-12 pb-20 lg:pt-20 lg:pb-28 border-b border-[#1c2130]">
        {/* Ambient warm gradient orbs */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-amber-600/10 blur-[130px] rounded-full pointer-events-none -z-10" />
        <div className="absolute bottom-10 right-10 w-[400px] h-[250px] bg-indigo-600/10 blur-[120px] rounded-full pointer-events-none -z-10" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center flex flex-col items-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-semibold mb-8 shadow-sm">
            <Sparkles size={13} className="text-amber-400" />
            <span>AI-Powered Bookshelf Vision & Personalized Sommelier</span>
          </div>

          {/* Headline */}
          <h1 className="font-serif-title text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white max-w-4xl leading-[1.15] mb-6">
            Discover the books you’ll love, <br />
            <span className="italic font-normal text-amber-300">
              right from the shelf in front of you.
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-slate-300 text-base sm:text-lg max-w-2xl font-normal leading-relaxed mb-10">
            Never stand in a bookstore paralyzed by endless rows of spines again. Take a quick photo of any shelf to segment titles, extract themes, and get curated recommendations tailored to your unique Reading DNA.
          </p>

          {/* Action CTAs */}
          <div className="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto mb-16">
            <Link
              href="/scan"
              className="w-full sm:w-auto px-8 py-4 rounded-xl text-base font-bold bg-gradient-to-r from-amber-600 to-amber-700 text-white flex items-center justify-center gap-2.5 hover:brightness-110 shadow-lg shadow-amber-950/60 active:scale-98 transition duration-200"
            >
              <Camera size={18} />
              Scan a Bookshelf
              <ArrowRight size={16} />
            </Link>

            <Link
              href={user ? "/dashboard" : "/onboarding"}
              className="w-full sm:w-auto px-7 py-4 rounded-xl text-base font-semibold border border-[#2b334a] bg-[#121622]/80 hover:bg-[#1a1f30] text-slate-200 hover:text-white transition duration-200"
            >
              {user ? "View Your Reading DNA" : "Build Your Taste Profile"}
            </Link>
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 max-w-4xl w-full pt-8 border-t border-[#1c2233]">
            <div className="flex flex-col items-center">
              <span className="font-serif-title text-2xl sm:text-3xl font-bold text-amber-400">291,000+</span>
              <span className="text-xs text-slate-400 mt-0.5">Indexed Works</span>
            </div>
            <div className="flex flex-col items-center">
              <span className="font-serif-title text-2xl sm:text-3xl font-bold text-amber-400">&lt; 150ms</span>
              <span className="text-xs text-slate-400 mt-0.5">YOLO Spine Detection</span>
            </div>
            <div className="flex flex-col items-center">
              <span className="font-serif-title text-2xl sm:text-3xl font-bold text-amber-400">Hybrid</span>
              <span className="text-xs text-slate-400 mt-0.5">BPR + Semantic Vector Recs</span>
            </div>
            <div className="flex flex-col items-center">
              <span className="font-serif-title text-2xl sm:text-3xl font-bold text-amber-400">100%</span>
              <span className="text-xs text-slate-400 mt-0.5">Local & Private ML</span>
            </div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
        <div className="text-center mb-16">
          <h2 className="font-serif-title text-3xl sm:text-4xl font-bold text-white mb-3">
            How ShelfSense Reads the Shelves
          </h2>
          <p className="text-slate-400 text-sm max-w-lg mx-auto">
            From raw camera snapshot to deep literary evaluation in four automated steps.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Step 1 */}
          <div className="p-6 rounded-2xl bg-[#12151e] border border-[#212638] flex flex-col justify-between hover:border-amber-500/30 transition-all duration-300 group">
            <div>
              <div className="w-12 h-12 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center mb-5 group-hover:scale-105 transition-transform">
                <ScanEye size={22} />
              </div>
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-amber-500">Step 01</span>
              <h3 className="font-serif-title text-lg font-bold text-white mt-1 mb-2">Spine Detection</h3>
              <p className="text-slate-400 text-xs leading-relaxed">
                Trained YOLOv8 vision isolates every book spine vertically or horizontally, bounding all titles across the shelves.
              </p>
            </div>
          </div>

          {/* Step 2 */}
          <div className="p-6 rounded-2xl bg-[#12151e] border border-[#212638] flex flex-col justify-between hover:border-amber-500/30 transition-all duration-300 group">
            <div>
              <div className="w-12 h-12 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center mb-5 group-hover:scale-105 transition-transform">
                <Layers size={22} />
              </div>
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-amber-500">Step 02</span>
              <h3 className="font-serif-title text-lg font-bold text-white mt-1 mb-2">PaddleOCR Extraction</h3>
              <p className="text-slate-400 text-xs leading-relaxed">
                Angle-aware OCR extracts rotated, stylized, and vertical typography from spine crops without GPU lockups.
              </p>
            </div>
          </div>

          {/* Step 3 */}
          <div className="p-6 rounded-2xl bg-[#12151e] border border-[#212638] flex flex-col justify-between hover:border-amber-500/30 transition-all duration-300 group">
            <div>
              <div className="w-12 h-12 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center mb-5 group-hover:scale-105 transition-transform">
                <Sparkles size={22} />
              </div>
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-amber-500">Step 03</span>
              <h3 className="font-serif-title text-lg font-bold text-white mt-1 mb-2">Entity Resolution</h3>
              <p className="text-slate-400 text-xs leading-relaxed">
                Multimodal vision resolves noisy OCR transcriptions into verified title and author entities against SQLite catalog.
              </p>
            </div>
          </div>

          {/* Step 4 */}
          <div className="p-6 rounded-2xl bg-[#12151e] border border-[#212638] flex flex-col justify-between hover:border-amber-500/30 transition-all duration-300 group">
            <div>
              <div className="w-12 h-12 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center mb-5 group-hover:scale-105 transition-transform">
                <Dna size={22} />
              </div>
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-amber-500">Step 04</span>
              <h3 className="font-serif-title text-lg font-bold text-white mt-1 mb-2">Reading DNA Scoring</h3>
              <p className="text-slate-400 text-xs leading-relaxed">
                Ranks books on the shelf by combining Bayesian collaborative filtering, semantic embeddings, and genre affinity.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SAMPLE SHELF BANNER */}
      <section className="py-16 bg-[#0f121a] border-y border-[#1c2233]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col lg:flex-row items-center justify-between gap-8">
            <div className="max-w-xl">
              <span className="text-xs font-mono uppercase tracking-wider text-amber-400 font-bold">
                Instant Interactive Demo
              </span>
              <h2 className="font-serif-title text-3xl font-bold text-white mt-1 mb-3">
                Experience a bookstore scan right now
              </h2>
              <p className="text-slate-300 text-sm leading-relaxed mb-6">
                Don&apos;t have a bookshelf photo ready? Jump straight into an analysis of a real bookstore shelf photograph to see the spine detection and recommendations in action.
              </p>
              <Link
                href="/scan"
                className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl font-bold bg-amber-600 hover:bg-amber-500 text-white transition active:scale-95"
              >
                <Camera size={18} /> Open Scanner Studio
              </Link>
            </div>

            <div className="p-5 rounded-2xl bg-[#161a25] border border-[#272e42] max-w-md w-full shadow-2xl">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-3 border-b border-[#242b3d] pb-2.5">
                <span className="font-semibold text-slate-200">Pre-loaded Shelf Example</span>
                <span className="text-amber-400 font-mono">165 Spines Detected</span>
              </div>
              <div className="space-y-3">
                <div className="p-3 rounded-lg bg-[#0e1118] border border-[#1f2638] flex items-center justify-between">
                  <div>
                    <h4 className="font-serif-title text-sm font-bold text-slate-100">Fantasy & Sci-Fi Shelf</h4>
                    <p className="text-[11px] text-slate-400">Brandon Sanderson, Philip Pullman, Andy Weir</p>
                  </div>
                  <span className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-bold">
                    94% Buy Fit
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-[#0e1118] border border-[#1f2638] flex items-center justify-between">
                  <div>
                    <h4 className="font-serif-title text-sm font-bold text-slate-100">Contemporary Fiction Shelf</h4>
                    <p className="text-[11px] text-slate-400">Emily Henry, Haruki Murakami, Matt Haig</p>
                  </div>
                  <span className="px-2 py-1 rounded bg-amber-500/10 text-amber-400 text-[10px] font-bold">
                    88% Buy Fit
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
