import re
from sqlalchemy import or_
from sqlalchemy.orm import Session
from rapidfuzz import process, fuzz
import numpy as np

from backend.database import Book
from src.content_based import search_similar_books_faiss

def clean_ocr(text: str) -> str:
    """Clean EasyOCR text output by removing punctuation and retaining words > 2 chars."""
    if not text:
        return ""
    words = []
    # Replace non-alphabetic chars with space, then split
    cleaned_text = re.sub(r"[^A-Za-z0-9\s]", " ", text)
    for w in cleaned_text.split():
        # Keep alphanumeric words with length >= 3
        if len(w) >= 3:
            words.append(w.lower())
    return " ".join(words)

def normalize_text(text: str) -> str:
    """Normalize text for Stage 2 matching."""
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]", "", text.lower())

def match_ocr_query(raw_query: str, db: Session, similarity_threshold=0.35, fuzzy_threshold=70.0):
    """
    Multi-stage matching pipeline:
    - Stage 1: Exact Match (searches exact title in DB)
    - Stage 2: Normalized Match (searches matching normalized title in DB)
    - Stage 3: RapidFuzz (fuzzy matching on a pre-filtered keyword candidate list)
    - Stage 4: FAISS Embedding Similarity (Sentence Transformers + FAISS vector lookup)
    
    Returns: A Book DB object and the matching score/metadata, or None if no match meets thresholds.
    """
    cleaned = clean_ocr(raw_query)
    if not cleaned:
        return None
        
    # ==========================================
    # STAGE 1: Exact Match (Title or Title+Author)
    # ==========================================
    # Try exact match on cleaned query
    exact_match = db.query(Book).filter(Book.title == raw_query).first()
    if exact_match:
        return {
            "book": exact_match,
            "stage": "Stage 1: Exact Match",
            "score": 100.0
        }
        
    # ==========================================
    # STAGE 2: Normalized Match
    # ==========================================
    norm_query = normalize_text(raw_query)
    norm_match = db.query(Book).filter(Book.normalized_title == norm_query).first()
    if norm_match:
        return {
            "book": norm_match,
            "stage": "Stage 2: Normalized Match",
            "score": 95.0
        }

    # ==========================================
    # STAGE 3: Pre-filtered RapidFuzz (Fuzzy)
    # ==========================================
    # To prevent slow O(N) fuzzy comparisons on 270k rows, we filter by query keywords first
    keywords = [kw for kw in cleaned.split() if len(kw) >= 3]
    if keywords:
        # Build OR condition for title contains keyword
        conditions = [Book.title.like(f"%{kw}%") for kw in keywords]
        
        # Pull top 300 candidates from DB
        candidates = db.query(Book).filter(or_(*conditions)).limit(300).all()
        
        if candidates:
            # Build list of strings for fuzzy matching: "Title Author"
            choices = {}
            for c in candidates:
                cand_str = f"{c.title} {c.author or ''}".lower()
                choices[cand_str] = c
                
            # Perform RapidFuzz match
            best_fuzzy = process.extractOne(
                cleaned, 
                list(choices.keys()), 
                scorer=fuzz.WRatio
            )
            
            if best_fuzzy and best_fuzzy[1] >= fuzzy_threshold:
                match_str = best_fuzzy[0]
                matched_book = choices[match_str]
                return {
                    "book": matched_book,
                    "stage": "Stage 3: RapidFuzz",
                    "score": float(best_fuzzy[1])
                }

    # ==========================================
    # STAGE 4: FAISS Embedding Similarity
    # ==========================================
    # Fallback to Sentence Transformer + FAISS on catalog books
    try:
        faiss_results = search_similar_books_faiss(cleaned, top_k=3)
        if faiss_results:
            best_cat, score = faiss_results[0]
            if score >= similarity_threshold:
                # Find matching book in our main DB by title / work_key
                # First try matching by work_key in catalog_books (or using work_key directly)
                work_key = best_cat.get("work_key")
                db_book = None
                
                if work_key:
                    # Let's see if we can find this work_key or find it by Title + Author in the main DB
                    # The Book table uses ISBN as book_id.
                    # Search by exact title and author in DB
                    db_book = db.query(Book).filter(
                        Book.title == best_cat["title"],
                        Book.author == best_cat["author"]
                    ).first()
                    
                if not db_book:
                    # Fallback to match by title
                    db_book = db.query(Book).filter(Book.title == best_cat["title"]).first()
                    
                if db_book:
                    return {
                        "book": db_book,
                        "stage": "Stage 4: FAISS Embedding",
                        "score": float(score * 100)  # Scale to 0-100
                    }
    except Exception as e:
        print(f"Error in Stage 4 Matching: {e}")
        
    return None
