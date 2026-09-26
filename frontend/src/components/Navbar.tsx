"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { 
  BookOpen, 
  Camera, 
  Compass, 
  Search, 
  Heart, 
  LogOut, 
  User as UserIcon, 
  Sparkles,
  BookMarked
} from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();
  const { user, profile, logout } = useAuth();

  const navLinks = [
    { href: "/", label: "Discover", icon: Compass },
    { href: "/scan", label: "Scan Shelf", icon: Camera, highlight: true },
    { href: "/browse", label: "Browse Catalog", icon: Search },
    { href: "/dashboard", label: "Reading DNA", icon: BookMarked },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#0d0f14]/90 backdrop-blur-md border-b border-[#232838]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-600 to-amber-700 p-0.5 shadow-md shadow-amber-950/50 group-hover:scale-105 transition-transform duration-200">
            <div className="w-full h-full bg-[#12151d] rounded-[10px] flex items-center justify-center text-amber-400">
              <BookOpen size={20} />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-serif-title text-xl font-bold tracking-tight text-white group-hover:text-amber-300 transition-colors">
                ShelfSense
              </span>
              <span className="text-[10px] font-mono uppercase tracking-widest px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold">
                AI
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-sans tracking-wide">
              The Bookstore Companion
            </p>
          </div>
        </Link>

        {/* Center Nav Links */}
        <nav className="hidden md:flex items-center gap-1">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                  link.highlight
                    ? isActive
                      ? "bg-amber-600 text-white shadow-md shadow-amber-900/40"
                      : "bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 border border-amber-500/30"
                    : isActive
                    ? "bg-[#1d2232] text-amber-300 font-semibold border border-[#2e364f]"
                    : "text-slate-300 hover:text-white hover:bg-[#151924]"
                }`}
              >
                <Icon size={16} className={link.highlight ? "text-amber-300" : isActive ? "text-amber-400" : "text-slate-400"} />
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Right Auth / Profile Controls */}
        <div className="flex items-center gap-3">
          {user ? (
            <div className="flex items-center gap-3">
              <Link
                href="/dashboard"
                className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#141824] border border-[#252b3d] text-xs text-slate-300 hover:border-amber-500/40 transition"
              >
                <UserIcon size={14} className="text-amber-400" />
                <span className="font-medium max-w-[120px] truncate">{user.name}</span>
                {profile?.wishlist && profile.wishlist.length > 0 && (
                  <span className="flex items-center gap-1 text-[11px] text-rose-400 font-semibold pl-1.5 border-l border-[#2e364f]">
                    <Heart size={11} className="fill-rose-400" /> {profile.wishlist.length}
                  </span>
                )}
              </Link>

              <button
                onClick={logout}
                className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-[#1a1e2d] transition"
                title="Sign Out"
              >
                <LogOut size={17} />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                href="/login"
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-300 hover:text-white transition"
              >
                Sign In
              </Link>
              <Link
                href="/register"
                className="px-4 py-2 rounded-lg text-xs font-bold bg-gradient-to-r from-amber-600 to-amber-700 text-white hover:brightness-110 shadow-md shadow-amber-950/40 active:scale-95 transition"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
