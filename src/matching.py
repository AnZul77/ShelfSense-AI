import os
import sys
# Initialize compatibility layer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.numpy_compat

import re
from typing import Optional, Dict, Any
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session
from rapidfuzz import process, fuzz
import numpy as np

from backend.database import Book
from src.content_based import search_similar_books_faiss

# Common English stopwords to avoid unconstrained SQL queries
STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "book", "novel", "vol",
    "volume", "edition", "part", "series", "story", "into", "over", "under", "about",
    "are", "was", "were", "been", "being", "have", "has", "had", "can", "could",
    "a", "an", "in", "on", "of", "to", "by", "at", "as", "is", "it"
}

def clean_ocr(text: str) -> str:
    """Clean OCR text output: alphanumeric and spaces, normalize spacing."""
    if not text:
        return ""
    # Remove vertical letter gaps: e.g. "S A N D E R S O N" -> "SANDERSON"
    collapsed = re.sub(r'(?<=\b[A-Za-z])\s+(?=[A-Za-z]\b)', '', text)
    cleaned = re.sub(r"[^A-Za-z0-9\s]", " ", collapsed)
    words = [w.lower() for w in cleaned.split() if len(w) >= 2]
    return " ".join(words)

def normalize_text(text: str) -> str:
    """Normalize text consistent with database seeder (alphanumeric + spaces)."""
    if not text or not isinstance(text, str):
        return ""
    return re.sub(r"[^a-z0-9\s]", "", text.lower()).strip()

def extract_meaningful_keywords(text: str):
    """Extract informative search tokens excluding common stopwords."""
    words = [w for w in text.lower().split() if len(w) >= 3]
    meaningful = [w for w in words if w not in STOPWORDS]
    return meaningful if meaningful else words

def match_book_entity(
    title: Optional[str] = None,
    author: Optional[str] = None,
    raw_query: Optional[str] = None,
    db: Session = None,
    similarity_threshold: float = 0.35,
    fuzzy_threshold: float = 72.0
) -> Optional[Dict[str, Any]]:
    """
    Multi-stage book entity resolver:
    1. Exact / Case-insensitive Title Match (optionally author-verified)
    2. Normalized Title Match
    3. Filtered RapidFuzz with Token-Sort scoring (guards against length bias)
    4. FAISS Semantic Embedding vector lookup
    """
    if not db:
        return None

    # Determine primary title candidate
    search_title = title.strip() if title and title.strip() and title != "UNKNOWN" else None
    search_author = author.strip() if author and author.strip() and author != "UNKNOWN" else None
    
    if not search_title and raw_query:
        search_title = raw_query.strip()

    if not search_title:
        return None

    cleaned_title = clean_ocr(search_title)
    norm_title = normalize_text(search_title)
    norm_author = normalize_text(search_author) if search_author else None

    # =========================================================================
    # STAGE 1: Exact Case-Insensitive Title Match
    # =========================================================================
    # Check exact title match
    title_matches = db.query(Book).filter(func.lower(Book.title) == search_title.lower()).limit(10).all()
    if title_matches:
        # If author provided, pick the one matching the author
        if norm_author:
            for b in title_matches:
                if b.normalized_author and (norm_author in b.normalized_author or b.normalized_author in norm_author):
                    return {
                        "book": b,
                        "stage": "Stage 1: Exact Title+Author Match",
                        "score": 100.0
                    }
        # Otherwise return first title match
        return {
            "book": title_matches[0],
            "stage": "Stage 1: Exact Title Match",
            "score": 98.0
        }

    # =========================================================================
    # STAGE 2: Normalized Title Match
    # =========================================================================
    if norm_title:
        norm_matches = db.query(Book).filter(Book.normalized_title == norm_title).limit(10).all()
        if norm_matches:
            if norm_author:
                for b in norm_matches:
                    if b.normalized_author and (norm_author in b.normalized_author or b.normalized_author in norm_author):
                        return {
                            "book": b,
                            "stage": "Stage 2: Normalized Title+Author Match",
                            "score": 96.0
                        }
            return {
                "book": norm_matches[0],
                "stage": "Stage 2: Normalized Title Match",
                "score": 94.0
            }

    # =========================================================================
    # STAGE 3: Targeted RapidFuzz with Token-Sort Ratio
    # =========================================================================
    keywords = extract_meaningful_keywords(search_title)
    if keywords:
        # Build candidate filter: require at least one meaningful keyword in title
        conditions = [Book.title.like(f"%{kw}%") for kw in keywords[:4]]
        
        # If author is known, add author condition to pull author's catalog books directly
        if norm_author and len(norm_author) >= 3:
            author_kw = [akw for akw in norm_author.split() if akw not in STOPWORDS and len(akw) >= 3]
            for akw in author_kw[:2]:
                conditions.append(Book.author.like(f"%{akw}%"))

        candidates = db.query(Book).filter(or_(*conditions)).limit(200).all()

        if candidates:
            # Score each candidate against search_title
            best_book = None
            best_score = 0.0

            target_str = f"{search_title} {search_author or ''}".strip().lower()

            for cand in candidates:
                cand_title = (cand.title or "").strip().lower()
                cand_full = f"{cand_title} {cand.author or ''}".strip().lower()

                # Score 1: Token Sort Ratio between titles
                title_score = fuzz.token_sort_ratio(cleaned_title, cand_title)
                
                # Score 2: Full query vs full candidate
                full_score = fuzz.token_sort_ratio(target_str, cand_full)
                
                combined_score = max(title_score, full_score)

                # Author agreement bonus
                if norm_author and cand.normalized_author:
                    if norm_author in cand.normalized_author or cand.normalized_author in norm_author:
                        combined_score = min(100.0, combined_score + 15.0)

                # Heavy penalty if length ratio is extreme (prevents matching short titles into 100-char medical titles)
                len_ratio = min(len(cleaned_title), len(cand_title)) / max(len(cleaned_title), len(cand_title))
                if len_ratio < 0.35 and title_score < 85:
                    combined_score *= 0.5

                if combined_score > best_score:
                    best_score = combined_score
                    best_book = cand

            if best_book and best_score >= fuzzy_threshold:
                return {
                    "book": best_book,
                    "stage": "Stage 3: Filtered RapidFuzz",
                    "score": float(best_score)
                }

    # =========================================================================
    # STAGE 4: FAISS Semantic Vector Lookup
    # =========================================================================
    try:
        faiss_query = f"{search_title} {search_author or ''}".strip()
        faiss_results = search_similar_books_faiss(faiss_query, top_k=3)
        if faiss_results:
            best_cat, score = faiss_results[0]
            if score >= similarity_threshold:
                # Find corresponding book in DB
                db_book = db.query(Book).filter(
                    Book.title == best_cat["title"]
                ).first()

                if db_book:
                    return {
                        "book": db_book,
                        "stage": "Stage 4: FAISS Vector Embedding",
                        "score": float(score * 100)
                    }
    except Exception as e:
        # FAISS index empty or lookup error
        pass

    return None

def match_ocr_query(raw_query: str, db: Session, similarity_threshold=0.35, fuzzy_threshold=72.0):
    """Backward compatibility wrapper around match_book_entity."""
    return match_book_entity(
        raw_query=raw_query,
        db=db,
        similarity_threshold=similarity_threshold,
        fuzzy_threshold=fuzzy_threshold
    )
