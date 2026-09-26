"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { 
  Star, 
  Search, 
  Trash2, 
  Sparkles, 
  CheckCircle, 
  AlertCircle, 
  BookOpen, 
  ArrowRight,
  BookMarked
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch, BookItem } from "@/lib/api";

export default function OnboardingPage() {
  const router = useRouter();
  const { token, refreshProfile } = useAuth();

  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<BookItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [ratedBooks, setRatedBooks] = useState<Record<string, { book: BookItem; rating: number }>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: "error" | "success"; text: string } | null>(null);

  // Load default popular books on page load
  useEffect(() => {
    fetchInitialBooks();
  }, []);

  const fetchInitialBooks = async () => {
    setIsSearching(true);
    try {
      const data = await apiFetch<BookItem[]>("/books");
      setSearchResults(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsSearching(true);
    try {
      const url = query.trim() ? `/books?q=${encodeURIComponent(query.trim())}` : `/books`;
      const data = await apiFetch<BookItem[]>(url);
      setSearchResults(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsSearching(false);
    }
  };

  const setRating = (book: BookItem, rating: number) => {
    setRatedBooks((prev) => ({
      ...prev,
      [book.book_id]: { book, rating },
    }));
    setStatusMsg(null);
  };

  const removeRating = (isbn: string) => {
    setRatedBooks((prev) => {
      const next = { ...prev };
      delete next[isbn];
      return next;
    });
  };

  const submitRatings = async () => {
    if (!token) {
      router.push("/login?redirect=/onboarding");
      return;
    }

    const ratingsList = Object.values(ratedBooks).map(({ book, rating }) => ({
      isbn: book.book_id,
      rating,
    }));

    if (ratingsList.length < 5) {
      setStatusMsg({
        type: "error",
        text: `Please rate at least 5 books (currently rated: ${ratingsList.length}).`,
      });
      return;
    }

    setIsSaving(true);
    setStatusMsg(null);

    try {
      await apiFetch(
        "/user/preferences",
        {
          method: "POST",
          body: JSON.stringify({ ratings: ratingsList }),
        },
        token
      );

      await refreshProfile();

      setStatusMsg({
        type: "success",
        text: "Your Reading DNA taste vector has been synthesized!",
      });

      setTimeout(() => {
        router.push("/dashboard");
      }, 1200);
    } catch (err: any) {
      setStatusMsg({
        type: "error",
        text: err.message || "Failed to save ratings.",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const ratedCount = Object.keys(ratedBooks).length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 mb-8 border-b border-[#1f2638]">
        <div>
          <span className="text-xs font-mono uppercase tracking-wider text-amber-500 font-bold">
            Taste Calibration
          </span>
          <h1 className="font-serif-title text-3xl sm:text-4xl font-bold text-white tracking-tight mt-1">
            Build Your Reading DNA
          </h1>
          <p className="text-slate-400 text-xs mt-1">
            Search for books you&apos;ve read and assign star ratings to train your personalized Bayesian Collaborative & Semantic taste profile.
          </p>
        </div>

        {/* Counter & Complete Button */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-[#141824] border border-[#232a3d] text-xs">
            <span className="text-slate-400">Rated:</span>
            <span className="font-mono font-bold text-amber-400">{ratedCount} / 5 required</span>
          </div>

          <button
            onClick={submitRatings}
            disabled={ratedCount < 5 || isSaving}
            className={`px-5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition duration-200 ${
              ratedCount >= 5 && !isSaving
                ? "bg-gradient-to-r from-amber-600 to-amber-700 text-white hover:brightness-110 shadow-md shadow-amber-950/40 active:scale-95 cursor-pointer"
                : "bg-[#181d2a] text-slate-500 border border-[#252b3d] cursor-not-allowed"
            }`}
          >
            {isSaving ? "Synthesizing..." : "Save Taste Profile"}
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {statusMsg && (
        <div
          className={`mb-6 p-4 rounded-xl text-xs flex items-center gap-2 border ${
            statusMsg.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/25 text-emerald-400"
              : "bg-rose-500/10 border-rose-500/25 text-rose-400"
          }`}
        >
          {statusMsg.type === "success" ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
          <span>{statusMsg.text}</span>
        </div>
      )}

      {/* Main Grid: Catalog Search (8 cols) + Rated Books Pane (4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Catalog Search & Browse */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by title or author (e.g., Sanderson, Tolkien, Colleen Hoover, Matt Haig)..."
                className="w-full bg-[#12151e] border border-[#23293b] rounded-xl pl-11 pr-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-amber-500/60 transition"
              />
            </div>
            <button
              type="submit"
              className="px-6 py-3 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs transition shrink-0"
            >
              Search
            </button>
          </form>

          {/* Search Results Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {isSearching ? (
              <div className="sm:col-span-2 py-20 text-center text-slate-400 text-xs">
                Searching catalog...
              </div>
            ) : searchResults.length > 0 ? (
              searchResults.map((book) => {
                const currentRating = ratedBooks[book.book_id]?.rating || 0;
                return (
                  <div
                    key={book.book_id}
                    className="p-4 rounded-2xl bg-[#12151e] border border-[#212638] hover:border-[#2f3750] transition flex gap-3.5 group"
                  >
                    {book.image_url ? (
                      <img
                        src={book.image_url}
                        alt={book.title}
                        className="w-16 aspect-[2/3] object-cover rounded-lg book-cover-shadow border border-[#202534] shrink-0"
                      />
                    ) : (
                      <div className="w-16 aspect-[2/3] rounded-lg bg-[#181d2a] border border-[#252b3b] flex items-center justify-center text-slate-600 shrink-0">
                        <BookOpen size={18} />
                      </div>
                    )}

                    <div className="flex-1 flex flex-col justify-between min-w-0">
                      <div>
                        <h4 className="font-serif-title text-sm font-bold text-white group-hover:text-amber-200 transition-colors line-clamp-1">
                          {book.title}
                        </h4>
                        <p className="text-xs text-slate-400 truncate mt-0.5">
                          {book.author || "Unknown Author"}
                        </p>
                        {book.genres && (
                          <span className="text-[10px] text-slate-500 truncate block mt-1 italic">
                            {book.genres}
                          </span>
                        )}
                      </div>

                      {/* 5-Star Rating Buttons */}
                      <div className="mt-3 pt-2 border-t border-[#1a1f2e] flex items-center justify-between">
                        <span className="text-[10px] font-mono text-slate-400">Rate:</span>
                        <div className="flex items-center gap-1">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <button
                              key={star}
                              type="button"
                              onClick={() => setRating(book, star)}
                              className="p-1 text-slate-600 hover:text-amber-400 transition"
                              title={`${star} stars`}
                            >
                              <Star
                                size={14}
                                className={
                                  currentRating >= star
                                    ? "fill-amber-400 text-amber-400"
                                    : "text-slate-600 hover:text-amber-400"
                                }
                              />
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="sm:col-span-2 py-20 text-center text-slate-500 text-xs">
                No matching books found. Try searching with different terms.
              </div>
            )}
          </div>
        </div>

        {/* Right Pane: Selected & Rated Books Shelf */}
        <div className="lg:col-span-4 sticky top-24">
          <div className="p-6 rounded-2xl bg-[#12151e] border border-[#212638] shadow-xl flex flex-col gap-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#1c2233]">
              <div className="flex items-center gap-2">
                <BookMarked size={16} className="text-amber-400" />
                <h3 className="font-serif-title text-sm font-bold text-white">
                  Your Taste Shelf ({ratedCount})
                </h3>
              </div>
              {ratedCount >= 5 && (
                <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">
                  Ready to Save
                </span>
              )}
            </div>

            {ratedCount > 0 ? (
              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                {Object.values(ratedBooks).map(({ book, rating }) => (
                  <div
                    key={book.book_id}
                    className="p-3 rounded-xl bg-[#0f121a] border border-[#1e2436] flex items-center justify-between gap-3"
                  >
                    <div className="min-w-0">
                      <h5 className="font-serif-title text-xs font-bold text-slate-200 truncate">
                        {book.title}
                      </h5>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <div className="flex text-amber-400">
                          {Array.from({ length: rating }).map((_, i) => (
                            <Star key={i} size={10} className="fill-amber-400 text-amber-400" />
                          ))}
                        </div>
                        <span className="text-[10px] font-mono text-slate-400">{rating} ★</span>
                      </div>
                    </div>

                    <button
                      onClick={() => removeRating(book.book_id)}
                      className="p-1.5 text-slate-500 hover:text-rose-400 rounded-lg hover:bg-[#181d2a] transition"
                      title="Remove"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-16 text-center text-slate-500 text-xs">
                <p className="mb-1">No books rated yet.</p>
                <p className="text-[11px] text-slate-600">
                  Search the catalog on the left and assign 1 to 5 stars to books you’ve read.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
