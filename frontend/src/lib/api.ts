export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface BookItem {
  book_id: string;
  title: string;
  author: string;
  description?: string;
  genres?: string;
  image_url?: string;
}

export interface RecommendationItem extends BookItem {
  score: number;
  buy_score: number;
  explanation: string;
  already_read: boolean;
}

export interface DetectedSpine {
  box_idx?: number;
  box: [number, number, number, number];
  isbn: string | null;
  title: string | null;
  author: string | null;
  ocr_text?: string;
  gemma_title?: string;
  gemma_author?: string;
  match_stage?: string;
  match_score?: number;
}

export interface ScanResult {
  scan_id: string;
  original_image_url: string;
  heatmap_image_url: string;
  detected_books: DetectedSpine[];
  recommendations: RecommendationItem[];
  reading_paths?: Array<{ author: string; path: string }>;
  author_exploration?: Array<{ book_id: string; title: string; author: string; reason: string }>;
  timestamp?: string;
}

export interface UserProfile {
  user_id: number;
  name: string;
  email: string;
  ratings_count: number;
  reading_dna: Record<string, number>;
  wishlist: BookItem[];
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Only set Content-Type to JSON if body is not FormData
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorDetail = `Request failed (${res.status})`;
    try {
      const errorJson = await res.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json();
}
