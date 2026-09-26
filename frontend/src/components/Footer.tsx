import React from "react";
import Link from "next/link";
import { BookOpen, Sparkles, Heart } from "lucide-react";

export default function Footer() {
  return (
    <footer className="mt-auto border-t border-[#1f2433] bg-[#090b0f] text-slate-400 text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg bg-amber-600/20 text-amber-400 flex items-center justify-center">
                <BookOpen size={16} />
              </div>
              <span className="font-serif-title text-base font-bold text-slate-200">
                ShelfSense AI
              </span>
            </div>
            <p className="text-slate-400 text-xs leading-relaxed max-w-sm mb-4">
              Designed for readers who love physical bookstores. Snap a shelf, extract spines with computer vision, and discover your next great read tailored to your personal Reading DNA.
            </p>
            <p className="font-serif-title italic text-slate-500 text-xs">
              “A reader lives a thousand lives before he dies. The man who never reads lives only one.”
            </p>
          </div>

          <div>
            <h4 className="font-semibold text-slate-200 uppercase tracking-wider text-[11px] mb-3">
              Platform
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/scan" className="hover:text-amber-400 transition">
                  Shelf Scanner
                </Link>
              </li>
              <li>
                <Link href="/browse" className="hover:text-amber-400 transition">
                  Catalog Search
                </Link>
              </li>
              <li>
                <Link href="/dashboard" className="hover:text-amber-400 transition">
                  Reading DNA Profile
                </Link>
              </li>
              <li>
                <Link href="/onboarding" className="hover:text-amber-400 transition">
                  Rate Books & Preferences
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-slate-200 uppercase tracking-wider text-[11px] mb-3">
              Architecture
            </h4>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Powered by custom YOLOv8 spine segmentation, isolated PaddleOCR transcription, local multimodal vision LLM, FAISS semantic vector search, and Bayesian Personalized Ranking.
            </p>
          </div>
        </div>

        <div className="pt-6 border-t border-[#171b26] flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-slate-500">
          <p>© {new Date().getFullYear()} ShelfSense AI. Handcrafted for book lovers.</p>
          <div className="flex items-center gap-1 text-slate-500">
            <span>Built with Next.js 15 & PyTorch</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
