"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { 
  Sparkles, 
  Heart, 
  BookMarked, 
  Camera, 
  FileImage, 
  ChevronRight, 
  CheckCircle2, 
  Info, 
  ArrowLeft,
  Share2,
  Compass,
  BookOpen
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { API_BASE_URL, ScanResult, RecommendationItem, apiFetch } from "@/lib/api";

function RecommendationsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { token, profile, refreshProfile } = useAuth();
  
  const scanId = searchParams.get("scan_id");
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const [savedIsbns, setSavedIsbns] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!scanId) {
      setErrorMsg("No scan ID provided. Please scan a bookshelf first.");
      setIsLoading(false);
      return;
    }

    // Try reading from sessionStorage first
    try {
      const cached = sessionStorage.getItem(`scan_${scanId}`);
      if (cached) {
        const parsed: ScanResult = JSON.parse(cached);
        setScanResult(parsed);
        setIsLoading(false);
        return;
      }
    } catch (e) {
      console.warn("Could not parse cached scan:", e);
    }

    // Otherwise fetch from backend API
    if (token) {
      apiFetch<ScanResult>(`/scan/${scanId}`, {}, token)
        .then((data) => {
          setScanResult(data);
          setIsLoading(false);
        })
        .catch((err) => {
          setErrorMsg(err.message || "Failed to load scan recommendations.");
          setIsLoading(false);
        });
    } else {
      setIsLoading(false);
      setErrorMsg("Please sign in to view recommendations.");
    }
  }, [scanId, token]);

  useEffect(() => {
    if (profile?.wishlist) {
      setSavedIsbns(new Set(profile.wishlist.map((b) => b.book_id)));
    }
  }, [profile]);

  const toggleWishlist = async (isbn: string) => {
    if (!token) {
      router.push("/login");
      return;
    }

    const isAlreadySaved = savedIsbns.has(isbn);
    try {
      if (isAlreadySaved) {
        await apiFetch(`/wishlist/remove/${isbn}`, { method: "DELETE" }, token);
        setSavedIsbns((prev) => {
          const next = new Set(prev);
          next.delete(isbn);
          return next;
        });
      } else {
        await apiFetch(`/wishlist/add`, {
          method: "POST",
          body: JSON.stringify({ isbn }),
        }, token);
        setSavedIsbns((prev) => new Set(prev).add(isbn));
      }
      refreshProfile();
    } catch (err) {
      console.error("Wishlist update failed:", err);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-24 flex flex-col items-center justify-center text-center">
        <div className="w-12 h-12 rounded-full border-4 border-[#252b3d] border-t-amber-500 animate-spin mb-4" />
        <h2 className="font-serif-title text-xl font-bold text-slate-200">
          Curating Your Bookshelf Recommendations...
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Loading detected titles and scoring them against your Reading DNA.
        </p>
      </div>
    );
  }

  if (errorMsg || !scanResult) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center">
        <div className="w-14 h-14 rounded-2xl bg-rose-500/10 text-rose-400 flex items-center justify-center mx-auto mb-4 border border-rose-500/20">
          <Info size={28} />
        </div>
        <h2 className="font-serif-title text-2xl font-bold text-white mb-2">Scan Not Found</h2>
        <p className="text-slate-400 text-sm mb-6">{errorMsg || "We could not find the requested shelf scan."}</p>
        <Link
          href="/scan"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-sm transition"
        >
          <Camera size={16} /> Scan a New Shelf
        </Link>
      </div>
    );
  }

  const { detected_books = [], recommendations = [], reading_paths = [], author_exploration = [] } = scanResult;
  const matchedCount = detected_books.filter((b) => b.isbn).length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 mb-8 border-b border-[#1f2638]">
        <div>
          <div className="flex items-center gap-2 text-xs text-amber-400 font-semibold mb-1">
            <Link href="/scan" className="hover:underline flex items-center gap-1 text-slate-400 hover:text-white">
              <ArrowLeft size={13} /> Scanner
            </Link>
            <span>/</span>
            <span>Bookshelf Analysis</span>
          </div>
          <h1 className="font-serif-title text-3xl sm:text-4xl font-bold text-white tracking-tight">
            Curated Shelf Recommendations
          </h1>
          <p className="text-slate-400 text-xs mt-1">
            {detected_books.length} book spines isolated · {matchedCount} matched entities · Ranked by Reading DNA & BPR Hybrid Model
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/scan"
            className="px-4 py-2.5 rounded-xl border border-[#2d344a] bg-[#121622] hover:bg-[#1a2030] text-slate-200 text-xs font-bold transition flex items-center gap-2"
          >
            <Camera size={15} /> Scan Another
          </Link>
          <Link
            href="/dashboard"
            className="px-4 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition shadow-md shadow-amber-950/40 flex items-center gap-2"
          >
            <BookMarked size={15} /> Your Library
          </Link>
        </div>
      </div>

      {/* Main Split Screen */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Interactive Heatmap Shelf (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-4 sticky top-24">
          <div className="p-4 rounded-2xl bg-[#12151e] border border-[#212638] shadow-xl">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#1b202e]">
              <div className="flex items-center gap-2">
                <FileImage size={16} className="text-amber-400" />
                <h3 className="font-serif-title text-sm font-bold text-white">
                  Physical Shelf Heatmap
                </h3>
              </div>
              <span className="text-[11px] font-mono text-slate-400 font-semibold">
                {detected_books.length} Spines
              </span>
            </div>

            {/* Heatmap Image */}
            <div className="relative rounded-xl overflow-hidden bg-black/60 border border-[#1b202e] flex items-center justify-center">
              <img
                src={`${API_BASE_URL}${scanResult.heatmap_image_url}`}
                alt="Shelf Heatmap"
                className="w-full h-auto max-h-[520px] object-contain"
              />
            </div>

            {/* Heatmap Legend */}
            <div className="mt-4 pt-3 border-t border-[#1b202e] grid grid-cols-3 gap-2 text-[10px] font-bold uppercase tracking-wider">
              <div className="flex items-center gap-1.5 text-emerald-400">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Highly Rec (&gt;80%)
              </div>
              <div className="flex items-center gap-1.5 text-amber-400">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Maybe (50-79%)
              </div>
              <div className="flex items-center gap-1.5 text-rose-400">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Low Fit (&lt;50%)
              </div>
              <div className="flex items-center gap-1.5 text-sky-400">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-500" /> Already Read
              </div>
              <div className="flex items-center gap-1.5 text-slate-400">
                <span className="w-2.5 h-2.5 rounded-full bg-slate-500" /> Unmatched
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Ranked Recommendations List (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {/* Series Reading Paths (if detected) */}
          {reading_paths && reading_paths.length > 0 && (
            <div className="p-5 rounded-2xl bg-amber-950/20 border border-amber-500/25 flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <BookMarked size={16} className="text-amber-400" />
                <h4 className="font-serif-title text-sm font-bold text-amber-300">
                  Recommended Reading Sequence
                </h4>
              </div>
              {reading_paths.map((path, idx) => (
                <div key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                  <span className="font-bold text-white shrink-0">{path.author}:</span>
                  <span className="text-amber-200/90 font-medium">{path.path}</span>
                </div>
              ))}
            </div>
          )}

          {/* Recommendations Feed */}
          <div className="flex flex-col gap-4">
            {recommendations.length > 0 ? (
              recommendations.map((rec, idx) => {
                const isSaved = savedIsbns.has(rec.book_id);
                const isHighFit = rec.buy_score >= 80;
                const isMediumFit = rec.buy_score >= 50 && rec.buy_score < 80;

                return (
                  <article
                    key={rec.book_id || idx}
                    className="p-5 rounded-2xl bg-[#131620] border border-[#232838] hover:border-amber-500/40 transition-all duration-200 flex flex-col sm:flex-row gap-5 shadow-lg group"
                  >
                    {/* Book Cover */}
                    <div className="shrink-0">
                      {rec.image_url ? (
                        <img
                          src={rec.image_url}
                          alt={rec.title}
                          className="w-24 sm:w-28 aspect-[2/3] object-cover rounded-xl book-cover-shadow border border-[#262c3e] group-hover:scale-[1.02] transition-transform"
                        />
                      ) : (
                        <div className="w-24 sm:w-28 aspect-[2/3] rounded-xl bg-[#1b202f] border border-[#2b334a] flex flex-col items-center justify-center text-center p-2 text-slate-500">
                          <BookOpen size={24} className="mb-1 text-slate-600" />
                          <span className="text-[10px] font-serif-title font-semibold leading-tight line-clamp-2">
                            {rec.title}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Metadata & Scores */}
                    <div className="flex-1 flex flex-col justify-between min-w-0">
                      <div>
                        {/* Top bar: Rank, Title, Buy Score */}
                        <div className="flex items-start justify-between gap-3 mb-1">
                          <div className="min-w-0">
                            <span className="text-[11px] font-mono text-amber-500 font-bold uppercase tracking-wider block mb-0.5">
                              #{idx + 1} Shelf Match
                            </span>
                            <h3 className="font-serif-title text-lg font-bold text-white group-hover:text-amber-200 transition-colors leading-snug line-clamp-2">
                              {rec.title}
                            </h3>
                            <p className="text-xs text-slate-400 font-medium mt-0.5">
                              by <span className="text-slate-200 font-semibold">{rec.author || "Unknown Author"}</span>
                            </p>
                          </div>

                          {/* Fit Score Badge */}
                          <div className="shrink-0 text-right">
                            {rec.already_read ? (
                              <span className="inline-block px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-sky-500/10 text-sky-400 border border-sky-500/20">
                                Already Read
                              </span>
                            ) : (
                              <div className={`px-3 py-1.5 rounded-xl border flex flex-col items-center ${
                                isHighFit
                                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                                  : isMediumFit
                                  ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                                  : "bg-rose-500/10 border-rose-500/30 text-rose-400"
                              }`}>
                                <span className="text-xs font-mono font-extrabold leading-none">
                                  {rec.buy_score}%
                                </span>
                                <span className="text-[8px] font-bold uppercase tracking-widest mt-0.5 opacity-80">
                                  Buy Fit
                                </span>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Genres */}
                        {rec.genres && (
                          <div className="flex flex-wrap gap-1.5 my-2.5">
                            {rec.genres.split("|").slice(0, 3).map((g, i) => (
                              <span
                                key={i}
                                className="text-[10px] px-2 py-0.5 rounded-md bg-[#1c2233] text-slate-300 border border-[#2b334a]"
                              >
                                {g.trim()}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Description snippet */}
                        {rec.description && (
                          <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed mt-2 font-normal">
                            {rec.description}
                          </p>
                        )}
                      </div>

                      {/* Bottom Explanations & Wishlist button */}
                      <div className="mt-4 pt-3 border-t border-[#1c2233] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="flex items-center gap-1.5 text-[11px] text-amber-300/90 font-medium bg-amber-500/5 px-2.5 py-1 rounded-lg border border-amber-500/15 max-w-md">
                          <Sparkles size={13} className="text-amber-400 shrink-0" />
                          <span className="truncate">{rec.explanation}</span>
                        </div>

                        <button
                          onClick={() => toggleWishlist(rec.book_id)}
                          className={`text-xs font-bold flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-all self-end sm:self-auto ${
                            isSaved
                              ? "bg-rose-500/15 border-rose-500/30 text-rose-300 hover:bg-rose-500/20"
                              : "bg-[#181d2a] border-[#293147] text-slate-300 hover:text-white hover:border-amber-500/40"
                          }`}
                        >
                          <Heart size={13} className={isSaved ? "fill-rose-400 text-rose-400" : ""} />
                          <span>{isSaved ? "Saved" : "Save to Wishlist"}</span>
                        </button>
                      </div>
                    </div>
                  </article>
                );
              })
            ) : (
              <div className="py-20 text-center p-8 rounded-2xl bg-[#12151e] border border-[#212638]">
                <BookOpen size={36} className="text-slate-600 mx-auto mb-3" />
                <h3 className="font-serif-title text-base font-bold text-slate-200 mb-1">
                  No Titles Matched Catalog
                </h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto mb-4">
                  The spine text could not be mapped to our database. Try scanning from a closer angle with good lighting.
                </p>
                <Link
                  href="/scan"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-600 text-white text-xs font-bold hover:bg-amber-500"
                >
                  <Camera size={14} /> Try Another Photo
                </Link>
              </div>
            )}
          </div>

          {/* Author Exploration Suggestions */}
          {author_exploration && author_exploration.length > 0 && (
            <div className="p-6 rounded-2xl bg-[#12151e] border border-[#212638] mt-4">
              <div className="flex items-center gap-2 mb-4">
                <Compass size={18} className="text-amber-400" />
                <h4 className="font-serif-title text-base font-bold text-white">
                  More by Authors on This Shelf
                </h4>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {author_exploration.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-[#0f121a] border border-[#1d2334] flex items-center justify-between"
                  >
                    <div className="min-w-0 pr-2">
                      <h5 className="font-serif-title text-xs font-bold text-slate-200 truncate">
                        {item.title}
                      </h5>
                      <p className="text-[11px] text-slate-400 truncate">{item.author}</p>
                      <p className="text-[10px] text-amber-400/80 mt-1 italic line-clamp-1">{item.reason}</p>
                    </div>
                    <button
                      onClick={() => toggleWishlist(item.book_id)}
                      className="p-2 rounded-lg hover:bg-[#1a202f] text-slate-400 hover:text-rose-400"
                      title="Save to Wishlist"
                    >
                      <Heart size={14} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function RecommendationsPage() {
  return (
    <Suspense fallback={<div className="p-12 text-center text-slate-400">Loading recommendations...</div>}>
      <RecommendationsContent />
    </Suspense>
  );
}
