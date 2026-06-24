"use client";

import React, { useState, useEffect } from "react";
import { 
  BookOpen, 
  Upload, 
  History, 
  User as UserIcon, 
  LogOut, 
  Search, 
  Star, 
  Trash2, 
  Sparkles, 
  ArrowRight, 
  Heart, 
  TrendingUp, 
  BookMarked, 
  Compass, 
  CheckCircle,
  HelpCircle,
  Dna,
  FileImage,
  AlertCircle
} from "lucide-react";

const API_BASE_URL = "http://localhost:8000";

export default function Home() {
  // Navigation & Auth State
  const [currentTab, setCurrentTab] = useState<"landing" | "login" | "register" | "onboarding" | "dashboard" | "scan" | "recommendations">("landing");
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<{ id: number; name: string; email: string } | null>(null);
  
  // Auth Form State
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authName, setAuthName] = useState("");
  const [authError, setAuthError] = useState("");
  
  // Dashboard & Profile Data
  const [profile, setProfile] = useState<{
    ratings_count: number;
    reading_dna: Record<string, number>;
    wishlist: Array<{ book_id: string; title: string; author: string; genres: string; image_url: string }>;
  } | null>(null);
  const [scanHistory, setScanHistory] = useState<any[]>([]);
  const [authorExploration, setAuthorExploration] = useState<any[]>([]);
  const [readingPaths, setReadingPaths] = useState<any[]>([]);

  // Onboarding / Rating State
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [onboardingRatings, setOnboardingRatings] = useState<Record<string, { book: any; rating: number }>>({});
  const [ratingError, setRatingError] = useState("");
  const [ratingSuccess, setRatingSuccess] = useState(false);

  // Upload Shelf State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");
  const [scanResult, setScanResult] = useState<{
    scan_id: string;
    original_image_url: string;
    heatmap_image_url: string;
    detected_books: any[];
    recommendations: any[];
  } | null>(null);
  const [hoveredBoxIdx, setHoveredBoxIdx] = useState<number | null>(null);

  // Load user session on startup
  useEffect(() => {
    const savedToken = localStorage.getItem("shelf_token");
    const savedUser = localStorage.getItem("shelf_user");
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
      setCurrentTab("dashboard");
    }
  }, []);

  // Fetch Dashboard details when user/tab changes
  useEffect(() => {
    if (token) {
      fetchProfile();
      fetchHistory();
    }
    if (currentTab === "onboarding") {
      handleCatalogSearch();
    }
  }, [token, currentTab]);

  const fetchProfile = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/profile`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setProfile({
          ratings_count: data.ratings_count,
          reading_dna: data.reading_dna,
          wishlist: data.wishlist
        });
      }
    } catch (err) {
      console.error("Error fetching profile:", err);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/history`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setScanHistory(data);
      }
    } catch (err) {
      console.error("Error fetching scan history:", err);
    }
  };

  // --- Auth Handlers ---
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");
    try {
      const res = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail, password: authPassword, name: authName })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Registration failed");
      
      localStorage.setItem("shelf_token", data.token);
      localStorage.setItem("shelf_user", JSON.stringify({ id: data.user_id, name: data.name, email: authEmail }));
      setToken(data.token);
      setUser({ id: data.user_id, name: data.name, email: authEmail });
      
      // Go to onboarding rating page
      setCurrentTab("onboarding");
    } catch (err: any) {
      setAuthError(err.message);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");
    try {
      const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail, password: authPassword })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Login failed");
      
      localStorage.setItem("shelf_token", data.token);
      localStorage.setItem("shelf_user", JSON.stringify({ id: data.user_id, name: data.name, email: authEmail }));
      setToken(data.token);
      setUser({ id: data.user_id, name: data.name, email: authEmail });
      setCurrentTab("dashboard");
    } catch (err: any) {
      setAuthError(err.message);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("shelf_token");
    localStorage.removeItem("shelf_user");
    setToken(null);
    setUser(null);
    setProfile(null);
    setScanHistory([]);
    setCurrentTab("landing");
  };

  // --- Onboarding / Rating Search ---
  const handleCatalogSearch = async () => {
    try {
      const url = searchQuery.trim()
        ? `${API_BASE_URL}/books?q=${encodeURIComponent(searchQuery)}`
        : `${API_BASE_URL}/books`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const addOnboardingRating = (book: any, rating: number) => {
    setOnboardingRatings(prev => ({
      ...prev,
      [book.book_id]: { book, rating }
    }));
  };

  const removeOnboardingRating = (isbn: string) => {
    setOnboardingRatings(prev => {
      const copy = { ...prev };
      delete copy[isbn];
      return copy;
    });
  };

  const submitOnboardingRatings = async () => {
    setRatingError("");
    setRatingSuccess(false);
    const ratingsArray = Object.keys(onboardingRatings).map(isbn => ({
      isbn,
      rating: onboardingRatings[isbn].rating
    }));
    
    if (ratingsArray.length < 5) {
      setRatingError("Please rate at least 5 books to generate your taste profile.");
      return;
    }
    
    try {
      const res = await fetch(`${API_BASE_URL}/user/preferences`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ ratings: ratingsArray })
      });
      if (res.ok) {
        setRatingSuccess(true);
        setTimeout(() => {
          setCurrentTab("dashboard");
        }, 1500);
      } else {
        const data = await res.json();
        setRatingError(data.detail || "Failed to save ratings.");
      }
    } catch (err) {
      setRatingError("Network error. Please try again.");
    }
  };

  // --- Upload Shelf Photo ---
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleShelfUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    
    setIsUploading(true);
    setUploadProgress("Detecting book spines...");
    
    const formData = new FormData();
    formData.append("file", selectedFile);
    
    try {
      const res = await fetch(`${API_BASE_URL}/shelf/upload`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData
      });
      
      if (!res.ok) {
        throw new Error("Upload failed. Make sure server is running and YOLO model is accessible.");
      }
      
      const data = await res.json();
      setScanResult(data);
      
      // Load reading paths and author explorations
      const matchIsbns = data.detected_books.filter((b: any) => b.isbn).map((b: any) => b.isbn);
      if (matchIsbns.length > 0) {
        fetchExtraRecommendations(matchIsbns);
      }
      
      setCurrentTab("recommendations");
    } catch (err: any) {
      alert(err.message);
    } finally {
      setIsUploading(false);
      setUploadProgress("");
    }
  };

  const fetchExtraRecommendations = async (isbns: string[]) => {
    try {
      const res = await fetch(`${API_BASE_URL}/recommend`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ shelf_isbns: isbns })
      });
      if (res.ok) {
        const data = await res.json();
        setReadingPaths(data.reading_paths || []);
        setAuthorExploration(data.author_exploration || []);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // --- Wishlist Management ---
  const addToWishlist = async (isbn: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/wishlist/add`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ isbn })
      });
      if (res.ok) {
        fetchProfile();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const removeFromWishlist = async (isbn: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/wishlist/remove/${isbn}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        fetchProfile();
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans select-none overflow-x-hidden selection:bg-teal-500 selection:text-white">
      {/* NAVBAR */}
      <nav className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => setCurrentTab(token ? "dashboard" : "landing")}>
          <div className="bg-gradient-to-tr from-teal-500 to-indigo-500 p-2 rounded-xl text-slate-950 font-bold shadow-md shadow-teal-500/20">
            <BookOpen size={20} />
          </div>
          <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-teal-400 to-indigo-400 bg-clip-text text-transparent">
            ShelfSense <span className="text-xs bg-slate-800 text-teal-300 py-0.5 px-2 rounded-full font-semibold border border-teal-500/20">AI</span>
          </span>
        </div>
        
        <div className="flex items-center gap-6">
          {token ? (
            <>
              <button 
                onClick={() => setCurrentTab("dashboard")} 
                className={`flex items-center gap-1.5 text-sm font-medium transition ${currentTab === "dashboard" ? "text-teal-400" : "text-slate-400 hover:text-slate-200"}`}
              >
                <Compass size={16} /> Dashboard
              </button>
              <button 
                onClick={() => setCurrentTab("scan")} 
                className={`flex items-center gap-1.5 text-sm font-medium transition ${currentTab === "scan" ? "text-teal-400" : "text-slate-400 hover:text-slate-200"}`}
              >
                <Upload size={16} /> Scan Shelf
              </button>
              <div className="h-4 w-[1px] bg-slate-800"></div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-slate-300 flex items-center gap-1">
                  <UserIcon size={14} className="text-indigo-400" /> {user?.name}
                </span>
                <button 
                  onClick={handleLogout}
                  className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition"
                  title="Logout"
                >
                  <LogOut size={16} />
                </button>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-3">
              <button 
                onClick={() => { setCurrentTab("login"); setAuthError(""); }}
                className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition"
              >
                Sign In
              </button>
              <button 
                onClick={() => { setCurrentTab("register"); setAuthError(""); }}
                className="px-4 py-2 rounded-xl text-sm font-semibold bg-gradient-to-r from-teal-500 to-indigo-500 text-slate-950 hover:shadow-lg hover:shadow-teal-500/20 transition active:scale-95"
              >
                Get Started
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* MAIN CONTAINER */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-6 py-8 flex flex-col justify-center">
        {/* Tab 1: Landing Page */}
        {currentTab === "landing" && (
          <div className="py-12 flex flex-col items-center text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs text-teal-400 font-semibold mb-6 shadow-inner animate-pulse">
              <Sparkles size={12} /> Next-Generation AI Bookstore Recommendations
            </div>
            
            <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight max-w-4xl leading-tight mb-8">
              Personalized Reading Choices,{" "}
              <span className="bg-gradient-to-r from-teal-400 via-emerald-400 to-indigo-400 bg-clip-text text-transparent">
                Instantly from any Bookstore Shelf
              </span>
            </h1>
            
            <p className="text-slate-400 text-lg md:text-xl max-w-2xl mb-12 font-medium">
              Discover which books you will love while browsing. Just snap a photo of any shelf to extract books, analyze themes, and calculate your custom purchase fit scores.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center gap-4 mb-16">
              <button 
                onClick={() => setCurrentTab("register")}
                className="w-full sm:w-auto px-8 py-4 rounded-xl text-base font-bold bg-gradient-to-r from-teal-500 to-indigo-500 text-slate-950 flex items-center justify-center gap-2 hover:shadow-xl hover:shadow-teal-500/25 transition duration-300 active:scale-98"
              >
                Find Your Next Favorite Book <ArrowRight size={18} />
              </button>
              <button 
                onClick={() => { setCurrentTab("login"); setAuthError(""); }}
                className="w-full sm:w-auto px-8 py-4 rounded-xl text-base font-bold border border-slate-700 bg-slate-900/50 hover:bg-slate-800/80 transition duration-300"
              >
                Sign In Profile
              </button>
            </div>
            
            {/* Visual Feature Cards */}
            <div className="grid md:grid-cols-3 gap-8 w-full max-w-5xl mt-8">
              <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 hover:border-teal-500/35 transition hover:-translate-y-1">
                <div className="h-10 w-10 rounded-lg bg-teal-500/10 text-teal-400 flex items-center justify-center mb-4">
                  <Upload size={20} />
                </div>
                <h3 className="text-lg font-bold mb-2">Shelf scanning</h3>
                <p className="text-slate-400 text-sm">Upload a photo of a shelf. YOLOv8 book spine extraction segmenting identifies every book title in the picture.</p>
              </div>
              
              <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 hover:border-indigo-500/35 transition hover:-translate-y-1">
                <div className="h-10 w-10 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center mb-4">
                  <Compass size={20} />
                </div>
                <h3 className="text-lg font-bold mb-2">Hybrid recommendations</h3>
                <p className="text-slate-400 text-sm">Calculates scores from Collaborative Filtering, Sentence Transformer Embeddings, and Genre Overlaps.</p>
              </div>
              
              <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 hover:border-emerald-500/35 transition hover:-translate-y-1">
                <div className="h-10 w-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-4">
                  <Dna size={20} />
                </div>
                <h3 className="text-lg font-bold mb-2">Reading DNA DNA</h3>
                <p className="text-slate-400 text-sm">Builds your mathematical taste vector. Inspect category charts, save a wishlist, and explore reading paths.</p>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Register */}
        {currentTab === "register" && (
          <div className="w-full max-w-md mx-auto p-8 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md shadow-2xl">
            <h2 className="text-2xl font-bold mb-2 text-center bg-gradient-to-r from-teal-400 to-indigo-400 bg-clip-text text-transparent">Create ShelfSense Account</h2>
            <p className="text-slate-400 text-sm text-center mb-6">Register to build your taste DNA and start scanning shelves.</p>
            
            {authError && (
              <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle size={14} /> {authError}
              </div>
            )}
            
            <form onSubmit={handleRegister} className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Your Name</label>
                <input 
                  type="text" 
                  value={authName} 
                  onChange={(e) => setAuthName(e.target.value)} 
                  required 
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:border-teal-500 focus:outline-none transition text-slate-100"
                  placeholder="John Doe"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Email Address</label>
                <input 
                  type="email" 
                  value={authEmail} 
                  onChange={(e) => setAuthEmail(e.target.value)} 
                  required 
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:border-teal-500 focus:outline-none transition text-slate-100"
                  placeholder="name@domain.com"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Password</label>
                <input 
                  type="password" 
                  value={authPassword} 
                  onChange={(e) => setAuthPassword(e.target.value)} 
                  required 
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:border-teal-500 focus:outline-none transition text-slate-100"
                  placeholder="••••••••"
                />
              </div>
              
              <button 
                type="submit" 
                className="w-full mt-2 py-3.5 rounded-xl font-bold bg-gradient-to-r from-teal-500 to-indigo-500 text-slate-950 hover:shadow-lg transition duration-250 hover:brightness-105 active:scale-98"
              >
                Register & Initialize
              </button>
            </form>
            <p className="mt-4 text-center text-xs text-slate-400">
              Already have an account?{" "}
              <button onClick={() => setCurrentTab("login")} className="text-teal-400 font-semibold hover:underline">Sign In</button>
            </p>
          </div>
        )}

        {/* Tab 3: Login */}
        {currentTab === "login" && (
          <div className="w-full max-w-md mx-auto p-8 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md shadow-2xl">
            <h2 className="text-2xl font-bold mb-2 text-center bg-gradient-to-r from-teal-400 to-indigo-400 bg-clip-text text-transparent">Welcome Back</h2>
            <p className="text-slate-400 text-sm text-center mb-6">Sign in to access your dashboard, ratings, and shelf scans.</p>
            
            {authError && (
              <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle size={14} /> {authError}
              </div>
            )}
            
            <form onSubmit={handleLogin} className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Email Address</label>
                <input 
                  type="email" 
                  value={authEmail} 
                  onChange={(e) => setAuthEmail(e.target.value)} 
                  required 
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:border-teal-500 focus:outline-none transition text-slate-100"
                  placeholder="name@domain.com"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Password</label>
                <input 
                  type="password" 
                  value={authPassword} 
                  onChange={(e) => setAuthPassword(e.target.value)} 
                  required 
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:border-teal-500 focus:outline-none transition text-slate-100"
                  placeholder="••••••••"
                />
              </div>
              
              <button 
                type="submit" 
                className="w-full mt-2 py-3.5 rounded-xl font-bold bg-gradient-to-r from-teal-500 to-indigo-500 text-slate-950 hover:shadow-lg transition duration-250 hover:brightness-105 active:scale-98"
              >
                Sign In
              </button>
            </form>
            <p className="mt-4 text-center text-xs text-slate-400">
              Don't have an account?{" "}
              <button onClick={() => setCurrentTab("register")} className="text-teal-400 font-semibold hover:underline">Register</button>
            </p>
          </div>
        )}

        {/* Tab 4: Onboarding (Rate Books) */}
        {currentTab === "onboarding" && (
          <div className="flex flex-col gap-6 max-w-5xl mx-auto">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
              <div>
                <h2 className="text-3xl font-extrabold tracking-tight">Onboarding: Rate 5-20 Books</h2>
                <p className="text-slate-400 text-sm mt-1">Search the catalog and rate books to seed your Collaborative and Semantic taste vectors.</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold px-3 py-1 rounded-full bg-slate-800 text-teal-400 border border-teal-500/20">
                  Rated: {Object.keys(onboardingRatings).length} books
                </span>
                <button 
                  onClick={submitOnboardingRatings}
                  disabled={Object.keys(onboardingRatings).length < 5}
                  className={`px-5 py-2.5 rounded-xl font-semibold text-sm transition ${Object.keys(onboardingRatings).length >= 5 ? "bg-gradient-to-r from-teal-500 to-indigo-500 text-slate-950 hover:shadow-md hover:brightness-105 active:scale-95 cursor-pointer" : "bg-slate-800 text-slate-500 cursor-not-allowed"}`}
                >
                  Complete Onboarding
                </button>
              </div>
            </div>

            {ratingError && (
              <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-2">
                <AlertCircle size={16} /> {ratingError}
              </div>
            )}

            {ratingSuccess && (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm flex items-center gap-2">
                <CheckCircle size={16} /> Taste vector generated! Loading your dashboard...
              </div>
            )}

            <div className="grid md:grid-cols-3 gap-6 items-start">
              {/* Search catalog pane */}
              <div className="md:col-span-2 p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 flex flex-col gap-4">
                <h3 className="font-bold text-base flex items-center gap-2"><Search size={16} className="text-teal-400" /> Search Catalog</h3>
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleCatalogSearch()}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm focus:border-teal-500 focus:outline-none transition text-slate-100"
                    placeholder="Search by Title, Author (e.g. Brandon Sanderson, Tolkien...)"
                  />
                  <button 
                    onClick={handleCatalogSearch}
                    className="px-5 py-2.5 rounded-xl bg-teal-500 text-slate-950 font-bold hover:brightness-105 transition"
                  >
                    Search
                  </button>
                </div>

                {/* Search Results Grid */}
                <div className="grid sm:grid-cols-2 gap-4 max-h-[450px] overflow-y-auto pr-2 mt-2">
                  {searchResults.length > 0 ? (
                    searchResults.map((b) => (
                      <div key={b.book_id} className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/50 flex gap-3 hover:border-slate-700 transition">
                        {b.image_url ? (
                          <img src={b.image_url} alt={b.title} className="w-12 h-16 object-cover rounded shadow" />
                        ) : (
                          <div className="w-12 h-16 bg-slate-850 rounded flex items-center justify-center text-slate-500 text-xs font-semibold">No Cover</div>
                        )}
                        <div className="flex-1 flex flex-col justify-between min-w-0">
                          <div>
                            <h4 className="font-bold text-xs truncate" title={b.title}>{b.title}</h4>
                            <p className="text-slate-400 text-[10px] truncate mt-0.5">{b.author || "Unknown Author"}</p>
                            <p className="text-slate-500 text-[9px] mt-1 italic line-clamp-1">{b.genres}</p>
                          </div>
                          
                          {/* Stars */}
                          <div className="flex items-center gap-1 mt-2">
                            {[1, 2, 3, 4, 5].map((star) => (
                              <button 
                                key={star}
                                onClick={() => addOnboardingRating(b, star)}
                                className="p-0.5 text-slate-600 hover:text-amber-400 transition"
                              >
                                <Star 
                                  size={12} 
                                  className={onboardingRatings[b.book_id]?.rating >= star ? "fill-amber-400 text-amber-400" : ""}
                                />
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="sm:col-span-2 py-12 text-center text-slate-500 text-sm">
                      Enter search query to look up books in the catalog.
                    </div>
                  )}
                </div>
              </div>

              {/* Rated books list pane */}
              <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 flex flex-col gap-4">
                <h3 className="font-bold text-base flex items-center gap-2"><Star size={16} className="text-amber-400 fill-amber-400/25" /> Rated Preference Books</h3>
                
                <div className="flex flex-col gap-3 max-h-[450px] overflow-y-auto pr-1">
                  {Object.keys(onboardingRatings).length > 0 ? (
                    Object.values(onboardingRatings).map(({ book, rating }) => (
                      <div key={book.book_id} className="p-3 rounded-xl bg-slate-950 border border-slate-800/60 flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <h4 className="font-bold text-xs truncate">{book.title}</h4>
                          <div className="flex items-center gap-1.5 mt-1">
                            <div className="flex text-amber-400">
                              {Array.from({ length: rating }).map((_, i) => (
                                <Star key={i} size={10} className="fill-amber-400" />
                              ))}
                            </div>
                            <span className="text-[10px] text-slate-400 font-semibold">{rating} ★</span>
                          </div>
                        </div>
                        <button 
                          onClick={() => removeOnboardingRating(book.book_id)}
                          className="p-1.5 text-slate-500 hover:text-rose-400 rounded-lg hover:bg-slate-900 transition"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    ))
                  ) : (
                    <div className="py-16 text-center text-slate-500 text-xs">
                      No books rated yet. Search and rate 5-20 books.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 5: Dashboard */}
        {currentTab === "dashboard" && (
          <div className="flex flex-col gap-8">
            {/* Upper profile panel */}
            <div className="grid md:grid-cols-3 gap-6">
              {/* Profile Overview Card */}
              <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 flex flex-col justify-between gap-4">
                <div>
                  <h3 className="font-bold text-lg mb-4 flex items-center gap-2"><UserIcon size={18} className="text-teal-400" /> User Profile Summary</h3>
                  <div className="flex flex-col gap-2">
                    <div className="flex justify-between border-b border-slate-800/60 pb-2 text-sm">
                      <span className="text-slate-400">Name</span>
                      <span className="font-semibold text-slate-200">{user?.name}</span>
                    </div>
                    <div className="flex justify-between border-b border-slate-800/60 pb-2 text-sm">
                      <span className="text-slate-400">Email</span>
                      <span className="font-semibold text-slate-200">{user?.email}</span>
                    </div>
                    <div className="flex justify-between pb-2 text-sm">
                      <span className="text-slate-400">Books Rated</span>
                      <span className="font-bold text-teal-400">{profile?.ratings_count || 0}</span>
                    </div>
                  </div>
                </div>
                
                <button 
                  onClick={() => setCurrentTab("scan")}
                  className="w-full py-3 rounded-xl font-bold bg-gradient-to-r from-teal-500 to-indigo-500 text-slate-950 flex items-center justify-center gap-2 hover:shadow-lg shadow-teal-500/10 active:scale-95 transition"
                >
                  <Upload size={16} /> Scan Bookstore Shelf
                </button>
              </div>

              {/* Reading DNA Chart Card */}
              <div className="md:col-span-2 p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 flex flex-col gap-4">
                <h3 className="font-bold text-lg flex items-center gap-2"><Dna size={18} className="text-indigo-400" /> Your Reading DNA</h3>
                
                {profile?.reading_dna && Object.keys(profile.reading_dna).length > 0 ? (
                  <div className="grid sm:grid-cols-2 gap-6 items-center flex-1">
                    {/* List view */}
                    <div className="flex flex-col gap-3">
                      {Object.entries(profile.reading_dna).slice(0, 4).map(([genre, pct]) => (
                        <div key={genre} className="flex flex-col gap-1">
                          <div className="flex justify-between text-xs font-semibold">
                            <span className="text-slate-300">{genre}</span>
                            <span className="text-teal-400">{pct}%</span>
                          </div>
                          <div className="h-2 w-full bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                            <div 
                              className="h-full bg-gradient-to-r from-teal-500 to-indigo-500 rounded-full"
                              style={{ width: `${pct}%` }}
                            ></div>
                          </div>
                        </div>
                      ))}
                    </div>
                    
                    {/* Visual DNA circle */}
                    <div className="flex flex-col items-center justify-center gap-2">
                      <div className="relative h-28 w-28 flex items-center justify-center">
                        {/* SVG circular progress ring representation */}
                        <svg className="w-full h-full transform -rotate-90">
                          <circle cx="56" cy="56" r="46" stroke="#0f172a" strokeWidth="8" fill="transparent" />
                          <circle 
                            cx="56" 
                            cy="56" 
                            r="46" 
                            stroke="url(#dnaGradient)" 
                            strokeWidth="8" 
                            fill="transparent" 
                            strokeDasharray={289}
                            strokeDashoffset={289 - (289 * (Object.values(profile.reading_dna)[0] || 0)) / 100}
                            strokeLinecap="round"
                          />
                          <defs>
                            <linearGradient id="dnaGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                              <stop offset="0%" stopColor="#2dd4bf" />
                              <stop offset="100%" stopColor="#6366f1" />
                            </linearGradient>
                          </defs>
                        </svg>
                        <div className="absolute flex flex-col items-center text-center">
                          <span className="text-lg font-extrabold text-slate-200">
                            {Object.values(profile.reading_dna)[0] || 0}%
                          </span>
                          <span className="text-[9px] text-slate-500 uppercase tracking-widest font-bold">
                            {Object.keys(profile.reading_dna)[0]?.split(" ")[0]}
                          </span>
                        </div>
                      </div>
                      <span className="text-xs text-slate-400 text-center font-medium">Favorite Genre: {Object.keys(profile.reading_dna)[0]}</span>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex flex-col items-center justify-center text-center py-6 text-slate-500">
                    <p className="text-sm mb-2">Not enough ratings to calculate Reading DNA.</p>
                    <button onClick={() => setCurrentTab("onboarding")} className="text-xs text-teal-400 font-bold hover:underline">Go rate books</button>
                  </div>
                )}
              </div>
            </div>

            {/* Lower row: scan history & wishlist */}
            <div className="grid md:grid-cols-2 gap-6">
              {/* Scan History Card */}
              <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 flex flex-col gap-4">
                <h3 className="font-bold text-lg flex items-center gap-2"><History size={18} className="text-teal-400" /> Recent Bookstore Scans</h3>
                
                <div className="flex flex-col gap-3 max-h-[350px] overflow-y-auto pr-1">
                  {scanHistory.length > 0 ? (
                    scanHistory.map((s) => (
                      <div 
                        key={s.scan_id} 
                        className="p-4 rounded-xl bg-slate-950 border border-slate-800/60 flex items-center justify-between hover:border-slate-700 transition cursor-pointer"
                        onClick={() => {
                          setScanResult({
                            scan_id: s.scan_id,
                            original_image_url: s.original_image_url,
                            heatmap_image_url: s.heatmap_image_url,
                            detected_books: s.detected_books,
                            recommendations: []
                          });
                          // Fetch recommendations for these matched ISBNs
                          const isbns = s.detected_books.filter((b: any) => b.isbn).map((b: any) => b.isbn);
                          if (isbns.length > 0) {
                            fetchExtraRecommendations(isbns);
                          }
                          setCurrentTab("recommendations");
                        }}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-slate-900 border border-slate-800 overflow-hidden flex items-center justify-center text-slate-500">
                            <FileImage size={18} />
                          </div>
                          <div>
                            <h4 className="font-bold text-xs text-slate-200">Scan: {s.scan_id.substring(0, 8)}</h4>
                            <p className="text-[10px] text-slate-500 mt-0.5">{new Date(s.timestamp).toLocaleDateString()} @ {new Date(s.timestamp).toLocaleTimeString()}</p>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <div className="text-xs font-bold text-teal-400">{s.detected_books.length}</div>
                            <div className="text-[9px] text-slate-500 font-semibold uppercase">Spines</div>
                          </div>
                          <ChevronRightIcon size={14} className="text-slate-600" />
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="py-20 text-center text-slate-500 text-sm">
                      No bookstore scans yet. Take a photo of a shelf and scan it!
                    </div>
                  )}
                </div>
              </div>

              {/* Wishlist Card */}
              <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 flex flex-col gap-4">
                <h3 className="font-bold text-lg flex items-center gap-2"><Heart size={18} className="text-rose-400 fill-rose-400/10" /> Saved Wishlist</h3>
                
                <div className="grid sm:grid-cols-2 gap-3 max-h-[350px] overflow-y-auto pr-1">
                  {profile?.wishlist && profile.wishlist.length > 0 ? (
                    profile.wishlist.map((b) => (
                      <div key={b.book_id} className="p-3 rounded-xl bg-slate-950 border border-slate-800/60 flex gap-2.5 hover:border-slate-700 transition">
                        {b.image_url ? (
                          <img src={b.image_url} alt={b.title} className="w-10 h-14 object-cover rounded shadow" />
                        ) : (
                          <div className="w-10 h-14 bg-slate-850 rounded flex items-center justify-center text-[10px] font-semibold text-slate-600">Cover</div>
                        )}
                        <div className="flex-1 flex flex-col justify-between min-w-0">
                          <div>
                            <h4 className="font-bold text-xs truncate">{b.title}</h4>
                            <p className="text-slate-400 text-[9px] truncate">{b.author}</p>
                          </div>
                          <button 
                            onClick={() => removeFromWishlist(b.book_id)}
                            className="text-[9px] text-rose-400 font-bold hover:underline flex items-center gap-0.5 mt-1"
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="sm:col-span-2 py-20 text-center text-slate-500 text-sm">
                      Your wishlist is empty. Add recommended books to save them here.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 6: Scan Shelf */}
        {currentTab === "scan" && (
          <div className="w-full max-w-2xl mx-auto p-8 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md shadow-2xl">
            <h2 className="text-2xl font-bold mb-2 text-center bg-gradient-to-r from-teal-400 to-indigo-400 bg-clip-text text-transparent">Scan Bookstore Shelf</h2>
            <p className="text-slate-400 text-sm text-center mb-8">Upload a photo of a bookstore bookshelf. The AI will segment spines, read titles, and score recommendations.</p>
            
            <form onSubmit={handleShelfUpload} className="flex flex-col gap-6">
              {/* Drag and Drop Box */}
              <div className="border-2 border-dashed border-slate-800 hover:border-teal-500/50 rounded-2xl p-8 text-center flex flex-col items-center justify-center gap-3 bg-slate-950/40 cursor-pointer transition relative group">
                <input 
                  type="file" 
                  accept="image/*" 
                  onChange={handleFileChange}
                  className="absolute inset-0 opacity-0 cursor-pointer"
                  disabled={isUploading}
                />
                
                <div className="p-4 rounded-full bg-slate-900 text-teal-400 group-hover:scale-105 transition duration-300">
                  <Upload size={32} />
                </div>
                
                <div>
                  <p className="text-sm font-semibold text-slate-200">
                    {selectedFile ? selectedFile.name : "Drag & drop bookstore shelf photo"}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Supports PNG, JPG, JPEG up to 10MB</p>
                </div>
                
                {selectedFile && (
                  <div className="mt-2 text-xs text-teal-400 font-bold bg-teal-500/10 px-3 py-1 rounded-full border border-teal-500/20">
                    File selected successfully!
                  </div>
                )}
              </div>
              
              {isUploading ? (
                <div className="flex flex-col items-center justify-center gap-4 py-4">
                  <div className="relative h-12 w-12 flex items-center justify-center">
                    {/* Ring Spinner */}
                    <div className="absolute h-full w-full rounded-full border-4 border-slate-800"></div>
                    <div className="absolute h-full w-full rounded-full border-4 border-teal-500 border-t-transparent animate-spin"></div>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-bold text-slate-200 animate-pulse">{uploadProgress}</p>
                    <p className="text-xs text-slate-500 mt-1">This will take 5-15 seconds. Running YOLO segmenter and PaddleOCR CUDA batch recognition...</p>
                  </div>
                </div>
              ) : (
                <button 
                  type="submit"
                  disabled={!selectedFile}
                  className={`w-full py-4 rounded-xl font-bold bg-gradient-to-r from-teal-500 to-indigo-500 text-slate-950 hover:shadow-xl transition duration-300 active:scale-98 ${selectedFile ? "cursor-pointer brightness-100" : "cursor-not-allowed opacity-50"}`}
                >
                  Analyze Bookstore Shelf
                </button>
              )}
            </form>
          </div>
        )}

        {/* Tab 7: Scan Results & Recommendations */}
        {currentTab === "recommendations" && scanResult && (
          <div className="flex flex-col gap-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
              <div>
                <h2 className="text-3xl font-extrabold tracking-tight">Personalized Recommendations</h2>
                <p className="text-slate-400 text-sm mt-1">Ranked recommendations from books physically identified on the shelf.</p>
              </div>
              <button 
                onClick={() => setCurrentTab("scan")}
                className="px-5 py-2.5 rounded-xl border border-slate-700 bg-slate-900 hover:bg-slate-800 transition font-semibold text-sm"
              >
                Scan Another Shelf
              </button>
            </div>

            {/* Signature Feature: Shelf Heatmap Overlay & Recommendation List split */}
            <div className="grid lg:grid-cols-5 gap-8 items-start">
              {/* Heatmap Overlay Display (Columns 2/5) */}
              <div className="lg:col-span-2 flex flex-col gap-4">
                <h3 className="font-bold text-base flex items-center gap-2"><FileImage size={16} className="text-teal-400" /> Interactive Shelf Heatmap</h3>
                
                {/* Heatmap Image Container */}
                <div className="relative rounded-2xl overflow-hidden border border-slate-800 bg-slate-900/40 shadow-inner group">
                  <img 
                    src={`${API_BASE_URL}${scanResult.heatmap_image_url}`} 
                    alt="Shelf Heatmap" 
                    className="w-full object-contain max-h-[500px]" 
                  />
                  
                  {/* Bounding box hover coordinate visualizer helper */}
                  {/* Let's render transparent interactive overlay spots based on bounding boxes */}
                  {scanResult.detected_books.map((item, idx) => {
                    const [x1, y1, x2, y2] = item.box;
                    // To do accurate overlays we would need the raw image size vs rendered size.
                    // For now, this is a clean visualization, and hover highlights happen in list.
                    return null;
                  })}
                </div>
                
                {/* Heatmap Legend */}
                <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80 flex flex-wrap gap-4 justify-between text-[10px] font-bold uppercase tracking-wider">
                  <div className="flex items-center gap-1.5 text-emerald-400">
                    <span className="h-2.5 w-2.5 rounded-full bg-emerald-500"></span> Highly Rec (80+)
                  </div>
                  <div className="flex items-center gap-1.5 text-yellow-400">
                    <span className="h-2.5 w-2.5 rounded-full bg-yellow-500"></span> Maybe (50-79)
                  </div>
                  <div className="flex items-center gap-1.5 text-rose-400">
                    <span className="h-2.5 w-2.5 rounded-full bg-rose-500"></span> Low match (&lt;50)
                  </div>
                  <div className="flex items-center gap-1.5 text-sky-400">
                    <span className="h-2.5 w-2.5 rounded-full bg-sky-500"></span> Already Read
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-400">
                    <span className="h-2.5 w-2.5 rounded-full bg-slate-500"></span> Unmatched
                  </div>
                </div>
              </div>

              {/* Recommendations list display (Columns 3/5) */}
              <div className="lg:col-span-3 flex flex-col gap-6">
                <h3 className="font-bold text-base flex items-center gap-2"><Sparkles size={16} className="text-indigo-400" /> Ranked Shelf Books</h3>
                
                {/* Display Reading Path Series if any */}
                {readingPaths.length > 0 && (
                  <div className="p-5 rounded-2xl bg-indigo-950/20 border border-indigo-500/20 flex flex-col gap-3">
                    <h4 className="font-bold text-xs text-indigo-400 uppercase tracking-widest flex items-center gap-1.5">
                      <BookMarked size={12} /> Suggested Reading Order
                    </h4>
                    {readingPaths.map((path, idx) => (
                      <div key={idx} className="text-sm">
                        <span className="font-bold text-slate-300">{path.author}:</span>{" "}
                        <span className="text-teal-300 font-semibold">{path.path}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Recommendations Loop */}
                <div className="flex flex-col gap-4">
                  {scanResult.recommendations.length > 0 ? (
                    scanResult.recommendations.map((r, idx) => {
                      const isSaved = profile?.wishlist.some(wb => wb.book_id === r.book_id);
                      return (
                        <div 
                          key={r.book_id} 
                          className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800/80 flex flex-col sm:flex-row gap-4 hover:border-slate-700 transition"
                        >
                          {/* Book Cover */}
                          {r.image_url ? (
                            <img src={r.image_url} alt={r.title} className="w-20 h-28 object-cover rounded-xl shadow-lg border border-slate-800/80 self-start" />
                          ) : (
                            <div className="w-20 h-28 bg-slate-950 rounded-xl border border-slate-800/80 flex items-center justify-center text-xs text-slate-600 font-bold self-start">No Cover</div>
                          )}
                          
                          {/* Book Metadata & Scores */}
                          <div className="flex-1 flex flex-col justify-between min-w-0">
                            <div>
                              <div className="flex items-start justify-between gap-2">
                                <h4 className="font-bold text-base text-slate-200 line-clamp-1">{r.title}</h4>
                                <div className="flex items-center gap-2">
                                  {r.already_read ? (
                                    <span className="text-[9px] bg-sky-500/10 border border-sky-500/20 text-sky-400 py-1 px-2.5 rounded-full font-bold uppercase tracking-wider">Already Read</span>
                                  ) : (
                                    <span className={`text-[9px] py-1 px-2.5 rounded-full font-extrabold uppercase tracking-wider ${r.buy_score >= 80 ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400" : r.buy_score >= 50 ? "bg-yellow-500/10 border border-yellow-500/20 text-yellow-400" : "bg-rose-500/10 border border-rose-500/20 text-rose-400"}`}>
                                      Buy Fit: {r.buy_score}%
                                    </span>
                                  )}
                                </div>
                              </div>
                              <p className="text-slate-400 text-xs font-semibold mt-0.5">{r.author || "Unknown Author"}</p>
                              {r.genres && <p className="text-[10px] text-slate-500 mt-1 italic">{r.genres}</p>}
                              <p className="text-slate-350 text-xs mt-3 line-clamp-2">{r.description || "No description available."}</p>
                            </div>
                            
                            {/* Explanation & Save button */}
                            <div className="mt-4 pt-3 border-t border-slate-800/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                              <span className="text-[11px] text-teal-400 font-semibold bg-teal-950/20 py-1 px-2.5 rounded-lg border border-teal-500/10 flex items-center gap-1.5 self-start">
                                <Sparkles size={12} className="text-teal-400" /> {r.explanation}
                              </span>
                              
                              <button 
                                onClick={() => isSaved ? removeFromWishlist(r.book_id) : addToWishlist(r.book_id)}
                                className={`text-xs font-bold flex items-center gap-1 transition-all ${isSaved ? "text-rose-400 hover:text-rose-300" : "text-slate-400 hover:text-white"}`}
                              >
                                <Heart size={14} className={isSaved ? "fill-rose-500 text-rose-500" : ""} /> {isSaved ? "Saved" : "Save to Wishlist"}
                              </button>
                            </div>
                          </div>
                        </div>
                      )
                    })
                  ) : (
                    <div className="py-24 text-center text-slate-500 text-sm bg-slate-900/20 border border-slate-800 rounded-2xl">
                      No books matching our catalog could be identified on the shelf. Ensure titles are visible and readable.
                    </div>
                  )}
                </div>

                {/* Author Exploration Recommendations */}
                {authorExploration.length > 0 && (
                  <div className="mt-6 p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80 flex flex-col gap-4">
                    <h4 className="font-bold text-sm flex items-center gap-2"><Compass size={16} className="text-teal-400" /> Explore More by Favorite Authors</h4>
                    <div className="grid sm:grid-cols-2 gap-4">
                      {authorExploration.map((b) => (
                        <div key={b.book_id} className="p-3 rounded-xl bg-slate-950 border border-slate-850 flex gap-2">
                          <div className="flex-1 min-w-0">
                            <h5 className="font-bold text-xs truncate">{b.title}</h5>
                            <p className="text-slate-400 text-[10px] truncate">{b.author}</p>
                            <p className="text-[9px] text-slate-500 mt-1.5 italic line-clamp-1">{b.reason}</p>
                          </div>
                          <button 
                            onClick={() => addToWishlist(b.book_id)}
                            className="p-2 text-slate-500 hover:text-rose-400 self-center"
                            title="Add to Wishlist"
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
        )}
      </main>

      {/* FOOTER */}
      <footer className="border-t border-slate-900 bg-slate-950 px-6 py-6 text-center text-xs text-slate-500">
        © 2026 ShelfSense AI. Portfolio-grade hybrid recommender, Computer Vision & OCR bookstore scanner. Built using Next.js 15, FastAPI, PyTorch, YOLOv8, PaddleOCR, and FAISS.
      </footer>
    </div>
  );
}

// Chevron Right placeholder
function ChevronRightIcon({ className, size }: { className?: string; size?: number }) {
  return (
    <svg className={className} width={size || 16} height={size || 16} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  );
}
