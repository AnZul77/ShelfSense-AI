"use client";

import React, { useState, useEffect } from "react";
import { 
  Search, 
  BookOpen, 
  Heart, 
  Sparkles, 
  Layers, 
  ArrowRight,
  Bookmark
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch, BookItem } from "@/lib/api";

export default function BrowsePage() {
  const { token, profile, refreshProfile } = useAuth();
  const [query, setQuery] = useState("");
  const [books, setBooks] = useState<BookItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [savedIsbns, setSavedIsbns] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchBooks();
  }, []);

  useEffect(() => {
    if (profile?.wishlist) {
      setSavedIsbns(new Set(profile.wishlist.map((b) => b.book_id)));
    }
  }, [profile]);

  const fetchBooks = async (searchQuery: string = "") => {
    setIsLoading(true);
    try {
      const url = searchQuery.trim() ? `/books?q=${encodeURIComponent(searchQuery.trim())}` : `/books`;
      const data = await apiFetch<BookItem[]>(url);
      setBooks(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchBooks(query);
  };

  const toggleWishlist = async (isbn: string) => {
    if (!token) return;
    const isSaved = savedIsbns.has(isbn);
    try {
      if (isSaved) {
        await apiFetch(`/wishlist/remove/${isbn}`, { method: "DELETE" }, token);
        setSavedIsbns((prev) => {
          const next = new Set(prev);
          next.delete(isbn);
          return next;
        });
      } else {
        await apiFetch("/wishlist/add", {
          method: "POST",
          body: JSON.stringify({ isbn }),
        }, token);
        setSavedIsbns((prev) => new Set(prev).add(isbn));
      }
      refreshProfile();
    } catch (e) {
      console.error("Wishlist toggle error:", e);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto mb-10">
        <span className="text-xs font-mono uppercase tracking-wider text-amber-500 font-bold">
          291,000+ Works Indexed
        </span>
        <h1 className="font-serif-title text-3xl sm:text-5xl font-bold text-white tracking-tight mt-1 mb-3">
          Explore the Library Catalog
        </h1>
        <p className="text-slate-400 text-xs sm:text-sm">
          Browse classical literature, modern bestsellers, fantasy epics, and thrillers. Save prospective reads straight to your personal wishlist.
        </p>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="max-w-2xl mx-auto mb-12 flex gap-2">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by title, author, or keyword (e.g. Brandon Sanderson, Donna Tartt, Hemingway)..."
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

      {/* Grid of Books */}
      {isLoading ? (
        <div className="py-24 text-center text-slate-400 text-xs flex flex-col items-center">
          <div className="w-8 h-8 rounded-full border-2 border-amber-500 border-t-transparent animate-spin mb-3" />
          <span>Searching the catalog...</span>
        </div>
      ) : books.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {books.map((book) => {
            const isSaved = savedIsbns.has(book.book_id);
            return (
              <div
                key={book.book_id}
                className="p-5 rounded-2xl bg-[#12151e] border border-[#212638] hover:border-amber-500/40 transition flex flex-col justify-between group shadow-lg"
              >
                <div>
                  {/* Cover */}
                  <div className="aspect-[2/3] w-full rounded-xl overflow-hidden bg-[#181d2a] border border-[#232a3d] mb-4 relative book-cover-shadow">
                    {book.image_url ? (
                      <img
                        src={book.image_url}
                        alt={book.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center text-slate-600 p-4 text-center">
                        <BookOpen size={28} className="mb-2" />
                        <span className="font-serif-title text-xs font-semibold text-slate-400 leading-snug line-clamp-3">
                          {book.title}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Title & Author */}
                  <h3 className="font-serif-title text-base font-bold text-white group-hover:text-amber-200 transition-colors line-clamp-1 mb-0.5">
                    {book.title}
                  </h3>
                  <p className="text-xs text-slate-400 font-medium truncate mb-2">
                    {book.author || "Unknown Author"}
                  </p>

                  {/* Genres */}
                  {book.genres && (
                    <p className="text-[10px] text-slate-500 italic truncate mb-2">
                      {book.genres}
                    </p>
                  )}

                  {/* Description snippet */}
                  {book.description && (
                    <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                      {book.description}
                    </p>
                  )}
                </div>

                {/* Bottom Actions */}
                <div className="mt-4 pt-3 border-t border-[#1c2233] flex items-center justify-between">
                  <span className="text-[10px] font-mono text-slate-500 truncate max-w-[120px]">
                    {book.book_id}
                  </span>

                  <button
                    onClick={() => toggleWishlist(book.book_id)}
                    className={`text-xs font-bold flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition ${
                      isSaved
                        ? "bg-rose-500/15 border-rose-500/30 text-rose-300"
                        : "bg-[#181d2a] border-[#293147] text-slate-300 hover:text-white hover:border-amber-500/40"
                    }`}
                  >
                    <Heart size={13} className={isSaved ? "fill-rose-400 text-rose-400" : ""} />
                    <span>{isSaved ? "Saved" : "Save"}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="py-24 text-center text-slate-500 text-xs">
          No books found matching &quot;{query}&quot;. Try another title or author.
        </div>
      )}
    </div>
  );
}
