"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { BookOpen, AlertCircle, ArrowRight } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect") || "/dashboard";
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setIsSubmitting(true);
    try {
      await login(email, password);
      router.push(redirectUrl);
    } catch (err: any) {
      setErrorMsg(err.message || "Invalid email or password.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 py-16 w-full">
      <div className="p-8 rounded-3xl bg-[#12151e] border border-[#212638] shadow-2xl">
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-amber-600/20 text-amber-400 flex items-center justify-center mx-auto mb-3 border border-amber-500/30">
            <BookOpen size={24} />
          </div>
          <h1 className="font-serif-title text-2xl font-bold text-white">
            Welcome Back, Reader
          </h1>
          <p className="text-slate-400 text-xs mt-1">
            Sign in to access your Reading DNA, scan history, and wishlist.
          </p>
        </div>

        {errorMsg && (
          <div className="mb-6 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle size={15} />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="reader@shelfsense.ai"
              className="w-full bg-[#0d0f15] border border-[#23293b] rounded-xl px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-amber-500/60 transition"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              className="w-full bg-[#0d0f15] border border-[#23293b] rounded-xl px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-amber-500/60 transition"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-2 py-3.5 rounded-xl font-bold bg-gradient-to-r from-amber-600 to-amber-700 text-white hover:brightness-110 shadow-md shadow-amber-950/40 text-sm flex items-center justify-center gap-2 active:scale-95 transition"
          >
            {isSubmitting ? "Signing in..." : "Enter Reading Room"}
            <ArrowRight size={15} />
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-slate-400">
          New to ShelfSense?{" "}
          <Link href={`/register?redirect=${encodeURIComponent(redirectUrl)}`} className="text-amber-400 font-bold hover:underline">
            Create an Account
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="p-12 text-center text-slate-400">Loading sign in...</div>}>
      <LoginContent />
    </Suspense>
  );
}
