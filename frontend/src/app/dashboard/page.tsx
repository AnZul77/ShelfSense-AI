"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { 
  Dna, 
  Heart, 
  History, 
  BookMarked, 
  Camera, 
  Trash2, 
  User, 
  ArrowRight, 
  Sparkles,
  BookOpen,
  Calendar,
  Layers
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch, BookItem } from "@/lib/api";

interface ScanHistoryItem {
  scan_id: string;
  original_image_url: string;
  heatmap_image_url: string;
  timestamp: string;
  detected_books: any[];
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, token, profile, refreshProfile } = useAuth();
  const [scanHistory, setScanHistory] = useState<ScanHistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  useEffect(() => {
    if (!token && !user) {
      router.push("/login?redirect=/dashboard");
      return;
    }

    if (token) {
      apiFetch<ScanHistoryItem[]>("/history", {}, token)
        .then((data) => setScanHistory(data))
        .catch((err) => console.error("Failed to load history:", err))
        .finally(() => setIsLoadingHistory(false));
    }
  }, [token, user]);

  const removeFromWishlist = async (isbn: string) => {
    if (!token) return;
    try {
      await apiFetch(`/wishlist/remove/${isbn}`, { method: "DELETE" }, token);
      refreshProfile();
    } catch (e) {
      console.error("Failed to remove item from wishlist:", e);
    }
  };

  const readingDnaEntries = profile?.reading_dna ? Object.entries(profile.reading_dna) : [];
  const topGenre = readingDnaEntries.length > 0 ? readingDnaEntries[0] : null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full">
      {/* Top Profile Header */}
      <div className="p-8 rounded-3xl bg-gradient-to-br from-[#141824] to-[#10131d] border border-[#232a3d] mb-10 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-amber-600/20 border border-amber-500/30 text-amber-400 flex items-center justify-center text-2xl font-serif-title font-bold shadow-md">
            {user?.name?.charAt(0).toUpperCase() || "R"}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-serif-title text-2xl sm:text-3xl font-bold text-white">
                {user?.name || "Reader"}&apos;s Library
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold uppercase tracking-wider">
                Member
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {user?.email} · {profile?.ratings_count || 0} books rated in taste profile
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/onboarding"
            className="px-4 py-2.5 rounded-xl border border-[#2e374f] bg-[#161b2a] hover:bg-[#1e253a] text-slate-200 text-xs font-semibold transition"
          >
            Refine Taste Ratings
          </Link>
          <Link
            href="/scan"
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-600 to-amber-700 text-white text-xs font-bold hover:brightness-110 shadow-md shadow-amber-950/40 flex items-center gap-2 active:scale-95 transition"
          >
            <Camera size={14} /> Scan a Shelf
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Reading DNA Card (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-8">
          <div className="p-6 rounded-2xl bg-[#12151e] border border-[#212638] shadow-xl">
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-[#1c2233]">
              <div className="flex items-center gap-2">
                <Dna size={18} className="text-amber-400" />
                <h2 className="font-serif-title text-lg font-bold text-white">Your Reading DNA</h2>
              </div>
              <Link href="/onboarding" className="text-xs text-amber-400 font-semibold hover:underline">
                Update
              </Link>
            </div>

            {readingDnaEntries.length > 0 ? (
              <div className="flex flex-col gap-6">
                {/* Top Genre Hero */}
                {topGenre && (
                  <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/15 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] font-mono uppercase tracking-wider text-amber-400/90 font-bold block mb-0.5">
                        Dominant Genre Affection
                      </span>
                      <h3 className="font-serif-title text-xl font-bold text-white">{topGenre[0]}</h3>
                    </div>
                    <div className="text-right">
                      <span className="font-serif-title text-2xl font-bold text-amber-400">{topGenre[1]}%</span>
                      <span className="text-[9px] text-slate-500 block">of preference weight</span>
                    </div>
                  </div>
                )}

                {/* Genre percentage bars */}
                <div className="space-y-3.5">
                  {readingDnaEntries.slice(0, 6).map(([genre, pct]) => (
                    <div key={genre}>
                      <div className="flex items-center justify-between text-xs font-semibold mb-1">
                        <span className="text-slate-300 font-medium">{genre}</span>
                        <span className="text-amber-400 font-mono text-[11px]">{pct}%</span>
                      </div>
                      <div className="h-2 w-full bg-[#181d2a] rounded-full overflow-hidden border border-[#232a3d]">
                        <div
                          className="h-full bg-gradient-to-r from-amber-600 to-amber-400 rounded-full transition-all duration-500"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-slate-400 text-xs">
                <p className="mb-3">You haven&apos;t rated enough books to calculate a definitive Reading DNA profile.</p>
                <Link
                  href="/onboarding"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-600 text-white font-bold"
                >
                  <Sparkles size={14} /> Rate 5 Books Now
                </Link>
              </div>
            )}
          </div>

          {/* Past Bookstore Scans */}
          <div className="p-6 rounded-2xl bg-[#12151e] border border-[#212638] shadow-xl">
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-[#1c2233]">
              <div className="flex items-center gap-2">
                <History size={18} className="text-amber-400" />
                <h2 className="font-serif-title text-lg font-bold text-white">Bookshelf Scan History</h2>
              </div>
              <span className="text-xs text-slate-400 font-mono">{scanHistory.length} scans</span>
            </div>

            {isLoadingHistory ? (
              <div className="py-8 text-center text-slate-400 text-xs">Loading history...</div>
            ) : scanHistory.length > 0 ? (
              <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                {scanHistory.map((scan) => (
                  <div
                    key={scan.scan_id}
                    onClick={() => router.push(`/recommendations?scan_id=${scan.scan_id}`)}
                    className="p-3.5 rounded-xl bg-[#0f121a] border border-[#1e2436] hover:border-amber-500/40 cursor-pointer transition flex items-center justify-between group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-[#181d2a] border border-[#272f44] flex items-center justify-center text-slate-400 group-hover:text-amber-400 transition-colors">
                        <Camera size={18} />
                      </div>
                      <div>
                        <h4 className="font-serif-title text-xs font-bold text-slate-200 group-hover:text-amber-200 transition-colors">
                          Scan {scan.scan_id.substring(0, 8)}
                        </h4>
                        <p className="text-[10px] text-slate-500 flex items-center gap-1 mt-0.5">
                          <Calendar size={10} />
                          {new Date(scan.timestamp).toLocaleDateString()}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <span className="text-xs font-mono font-bold text-amber-400">
                          {scan.detected_books?.length || 0}
                        </span>
                        <span className="text-[9px] text-slate-500 uppercase block font-semibold">Spines</span>
                      </div>
                      <ArrowRight size={14} className="text-slate-600 group-hover:text-slate-300 transition-colors" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-10 text-center text-slate-500 text-xs">
                <p className="mb-2">No shelf scans recorded yet.</p>
                <Link href="/scan" className="text-amber-400 font-bold hover:underline">
                  Scan your first bookshelf
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Wishlist Collection (7 cols) */}
        <div className="lg:col-span-7">
          <div className="p-6 rounded-2xl bg-[#12151e] border border-[#212638] shadow-xl">
            <div className="flex items-center justify-between pb-4 mb-6 border-b border-[#1c2233]">
              <div className="flex items-center gap-2">
                <Heart size={18} className="text-rose-400 fill-rose-400/20" />
                <h2 className="font-serif-title text-xl font-bold text-white">
                  Curated Wishlist
                </h2>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                {profile?.wishlist?.length || 0} books saved
              </span>
            </div>

            {profile?.wishlist && profile.wishlist.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {profile.wishlist.map((book) => (
                  <div
                    key={book.book_id}
                    className="p-4 rounded-xl bg-[#0e1118] border border-[#1e2436] hover:border-slate-700 transition flex gap-3.5 group"
                  >
                    {book.image_url ? (
                      <img
                        src={book.image_url}
                        alt={book.title}
                        className="w-16 aspect-[2/3] object-cover rounded-lg book-cover-shadow border border-[#212739] shrink-0"
                      />
                    ) : (
                      <div className="w-16 aspect-[2/3] rounded-lg bg-[#181d2a] border border-[#262e42] flex items-center justify-center text-slate-600 shrink-0">
                        <BookOpen size={16} />
                      </div>
                    )}

                    <div className="flex-1 flex flex-col justify-between min-w-0">
                      <div>
                        <h3 className="font-serif-title text-sm font-bold text-slate-100 group-hover:text-amber-200 transition-colors line-clamp-1">
                          {book.title}
                        </h3>
                        <p className="text-xs text-slate-400 truncate mt-0.5">
                          {book.author || "Unknown Author"}
                        </p>
                        {book.genres && (
                          <span className="inline-block text-[10px] text-slate-500 mt-1 truncate max-w-full italic">
                            {book.genres}
                          </span>
                        )}
                      </div>

                      <button
                        onClick={() => removeFromWishlist(book.book_id)}
                        className="text-[11px] text-slate-500 hover:text-rose-400 font-semibold flex items-center gap-1 self-start mt-2 transition-colors"
                      >
                        <Trash2 size={12} /> Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-24 text-center text-slate-500 text-xs">
                <BookOpen size={36} className="text-slate-700 mx-auto mb-3" />
                <p className="text-sm font-serif-title font-semibold text-slate-300 mb-1">
                  Your Wishlist is Empty
                </p>
                <p className="max-w-xs mx-auto mb-4">
                  Whenever you scan a bookstore shelf or search the catalog, click the heart icon on any title to save it for later.
                </p>
                <Link
                  href="/scan"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-600 text-white font-bold"
                >
                  <Camera size={14} /> Scan a Shelf to Find Books
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
