"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { 
  Camera, 
  Upload, 
  Sparkles, 
  Layers, 
  CheckCircle, 
  AlertCircle, 
  FileImage,
  ArrowRight,
  BookOpen
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { API_BASE_URL, ScanResult } from "@/lib/api";

export default function ScanPage() {
  const router = useRouter();
  const { token, user } = useAuth();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");

  const pipelineSteps = [
    "Uploading bookstore shelf image...",
    "Running YOLOv8 book spine detector...",
    "Running PaddleOCR typography extraction...",
    "Resolving titles with multimodal vision...",
    "Calculating personalized Buy Fit scores...",
  ];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setErrorMsg("");
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    if (!token) {
      router.push("/login?redirect=/scan");
      return;
    }

    setIsUploading(true);
    setErrorMsg("");
    setCurrentStep(0);

    // Progress animation stepper
    const stepInterval = setInterval(() => {
      setCurrentStep((prev) => (prev < pipelineSteps.length - 1 ? prev + 1 : prev));
    }, 2400);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch(`${API_BASE_URL}/shelf/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      clearInterval(stepInterval);

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Shelf analysis failed. Check server status.");
      }

      const scanData: ScanResult = await res.json();
      
      // Store current scan in session storage for immediate viewing
      sessionStorage.setItem(`scan_${scanData.scan_id}`, JSON.stringify(scanData));
      
      // Navigate to recommendations view
      router.push(`/recommendations?scan_id=${scanData.scan_id}`);
    } catch (err: any) {
      clearInterval(stepInterval);
      setErrorMsg(err.message || "Failed to process image.");
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full">
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 text-xs font-semibold mb-3 border border-amber-500/20">
          <Camera size={14} />
          <span>Computer Vision Shelf Scanner</span>
        </div>
        <h1 className="font-serif-title text-3xl sm:text-5xl font-bold text-white tracking-tight mb-3">
          Scan a Bookstore Shelf
        </h1>
        <p className="text-slate-400 text-sm max-w-lg mx-auto">
          Snap or upload a photo of any physical bookshelf. Our vision pipeline isolates spines, reads titles, and ranks books based on your taste.
        </p>
      </div>

      {!user && (
        <div className="mb-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-center justify-between">
          <span>Tip: Sign in or register to have recommendations personalized to your Reading DNA.</span>
          <button
            onClick={() => router.push("/login?redirect=/scan")}
            className="underline font-bold hover:text-white"
          >
            Sign In Now
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle size={16} />
          <span>{errorMsg}</span>
        </div>
      )}

      <div className="p-8 rounded-2xl bg-[#131620] border border-[#232838] shadow-2xl">
        <form onSubmit={handleUpload} className="flex flex-col gap-6">
          {/* Dropzone */}
          <div className="relative border-2 border-dashed border-[#2d3449] hover:border-amber-500/50 transition rounded-2xl p-8 flex flex-col items-center justify-center text-center bg-[#0d0f15]/50 group cursor-pointer overflow-hidden">
            <input
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              disabled={isUploading}
              className="absolute inset-0 opacity-0 cursor-pointer z-10"
            />

            {previewUrl ? (
              <div className="flex flex-col items-center gap-4">
                <img
                  src={previewUrl}
                  alt="Shelf Preview"
                  className="max-h-72 w-auto object-contain rounded-xl shadow-lg border border-[#232838]"
                />
                <div className="flex items-center gap-2 text-xs text-amber-400 font-semibold bg-amber-500/10 px-3 py-1.5 rounded-full border border-amber-500/20">
                  <FileImage size={14} />
                  <span>{selectedFile?.name}</span>
                </div>
                <p className="text-[11px] text-slate-500">Click or drag a new image to replace</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4 py-8">
                <div className="w-16 h-16 rounded-2xl bg-amber-500/10 text-amber-400 flex items-center justify-center group-hover:scale-105 transition-transform duration-200">
                  <Upload size={28} />
                </div>
                <div>
                  <p className="font-serif-title text-base font-bold text-slate-200">
                    Drag and drop bookstore shelf photo
                  </p>
                  <p className="text-xs text-slate-400 mt-1">Supports JPG, PNG, WEBP up to 20MB</p>
                </div>
                <span className="text-xs px-4 py-2 rounded-xl bg-[#1b202e] text-slate-300 border border-[#2b334a] font-semibold group-hover:border-amber-500/30 transition">
                  Browse Files
                </span>
              </div>
            )}
          </div>

          {/* Stepper progress when uploading */}
          {isUploading && (
            <div className="p-6 rounded-xl bg-[#0f121a] border border-[#1f2638] flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full border-2 border-amber-500 border-t-transparent animate-spin" />
                  <span className="text-xs font-bold text-amber-300">
                    Processing Vision Pipeline
                  </span>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  Step {currentStep + 1} of {pipelineSteps.length}
                </span>
              </div>

              {/* Progress bar */}
              <div className="h-1.5 w-full bg-[#1b202d] rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-amber-600 to-amber-400 transition-all duration-500 rounded-full"
                  style={{ width: `${((currentStep + 1) / pipelineSteps.length) * 100}%` }}
                />
              </div>

              <p className="text-xs text-slate-300 font-medium">
                {pipelineSteps[currentStep]}
              </p>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={!selectedFile || isUploading}
            className={`w-full py-4 rounded-xl font-bold flex items-center justify-center gap-2 text-sm transition-all duration-200 ${
              selectedFile && !isUploading
                ? "bg-gradient-to-r from-amber-600 to-amber-700 text-white hover:brightness-110 shadow-lg shadow-amber-950/60 active:scale-98 cursor-pointer"
                : "bg-[#181c28] text-slate-500 border border-[#242a3b] cursor-not-allowed"
            }`}
          >
            {isUploading ? (
              <>
                <Sparkles size={16} className="animate-spin" />
                Analyzing Spines & Titles...
              </>
            ) : (
              <>
                <Camera size={16} />
                Analyze Shelf & Generate Recommendations
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
