import os
import sys
# Initialize compatibility layer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.numpy_compat

import re
import pickle
import numpy as np
import pandas as pd
import torch
import faiss
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

# Import database Book model if needed
from backend.database import Book

MODELS_DIR = r"c:\Users\anshu\Documents\codes\ML\BookRecomendation\models"
EMBEDDINGS_DIR = r"c:\Users\anshu\Documents\codes\ML\BookRecomendation\embeddings"

# Ensure embeddings directory exists
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

# Global variables for caching
_sentence_model = None
_faiss_index = None
_book_catalog = None
_book_embeddings = None
_semantic_neighbors = None

def get_sentence_model():
    global _sentence_model
    if _sentence_model is None:
        print("Loading Sentence Transformer model (all-MiniLM-L6-v2)...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _sentence_model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    return _sentence_model

def load_content_assets():
    global _faiss_index, _book_catalog, _book_embeddings, _semantic_neighbors
    
    if _faiss_index is not None:
        return
        
    print("Loading Content-Based assets...")
    
    # Load catalog dataframe
    catalog_path = os.path.join(MODELS_DIR, "book_catalog.csv")
    if os.path.exists(catalog_path):
        _book_catalog = pd.read_csv(catalog_path)
    else:
        _book_catalog = pd.DataFrame(columns=["title", "author", "work_key", "description", "genres", "combined_text"])
        
    # Load pre-computed catalog embeddings
    embeddings_path = os.path.join(MODELS_DIR, "book_embeddings.npy")
    if os.path.exists(embeddings_path):
        _book_embeddings = np.load(embeddings_path).astype("float32")
        
        # Build FAISS Index (Inner Product for cosine similarity with normalized vectors)
        dimension = _book_embeddings.shape[1]
        
        # Normalize embeddings for cosine similarity
        norm_embeddings = _book_embeddings.copy()
        faiss.normalize_L2(norm_embeddings)
        
        _faiss_index = faiss.IndexFlatIP(dimension)
        _faiss_index.add(norm_embeddings)
        print(f"FAISS index built with {_faiss_index.ntotal} book embeddings.")
    else:
        print("Warning: book_embeddings.npy not found. FAISS index will be empty.")
        _faiss_index = faiss.IndexFlatIP(384)  # 384 dimensions for all-MiniLM-L6-v2
        _book_embeddings = np.empty((0, 384), dtype="float32")

    # Load pre-computed semantic neighbors
    neighbors_path = os.path.join(MODELS_DIR, "semantic_neighbors.pkl")
    if os.path.exists(neighbors_path):
        with open(neighbors_path, "rb") as f:
            _semantic_neighbors = pickle.load(f)
    else:
        _semantic_neighbors = {}

def get_book_embedding_by_isbn(isbn: str, db: Session) -> np.ndarray:
    """
    Get the embedding of a book. Checks the pre-computed catalog,
    and falls back to generating it on-the-fly using SentenceTransformer if needed.
    """
    load_content_assets()
    
    # Check catalog first: can we find a matching book?
    # In books_master, find title/author of this ISBN to search in book_catalog
    book_record = db.query(Book).filter(Book.book_id == isbn).first()
    if book_record:
        # Normalize and clean title to match catalog (e.g. remove "(Leatherette Edition)")
        clean_title = re.sub(r"\(.*?\)|\[.*?\]", "", book_record.title).strip().lower()
        title_lower = book_record.title.lower().strip()
        author_lower = book_record.author.lower().strip() if book_record.author else ""
        
        # 1. Check exact match in catalog
        match_idx = _book_catalog[
            (_book_catalog["title"].str.lower().str.strip() == title_lower) & 
            (_book_catalog["author"].str.lower().str.strip() == author_lower)
        ].index
        
        # 2. Check clean title match in catalog
        if len(match_idx) == 0:
            match_idx = _book_catalog[
                _book_catalog["title"].str.lower().str.strip() == clean_title
            ].index
            
        if len(match_idx) > 0:
            idx = match_idx[0]
            if idx < len(_book_embeddings):
                return _book_embeddings[idx]
        
        # 3. If book lacks synopsis/genres, auto-enrich it from OpenLibrary
        if not book_record.description or not book_record.genres:
            try:
                from src.enrichment import enrich_book_in_db
                enrich_book_in_db(book_record, db)
            except Exception:
                pass
                
        # 4. Fallback: compile combined text and embed
        comb_text = f"{clean_title} {book_record.author or ''} {book_record.genres or ''} {book_record.description or ''}".strip()
    else:
        comb_text = isbn

    # Generate on-the-fly
    model = get_sentence_model()
    emb = model.encode(comb_text, normalize_embeddings=True)
    return emb.astype("float32")

def generate_user_taste_vector(rated_books: list, db: Session) -> np.ndarray:
    """
    Generate User Taste Vector (User Profile Embedding) as the weighted average
    of their rated books' embeddings.
    rated_books: list of dicts [{'isbn': str, 'rating': int}]
    """
    if not rated_books:
        return np.zeros(384, dtype="float32")
        
    embeddings = []
    weights = []
    
    for r in rated_books:
        isbn = r["isbn"]
        rating = r["rating"]
        
        # Skip low ratings if we have higher ratings to focus on positive preferences
        # e.g., weight = rating - 2.5 (negative or low weights for poor books, high for good ones)
        weight = float(rating)
        
        try:
            emb = get_book_embedding_by_isbn(isbn, db)
            embeddings.append(emb)
            weights.append(weight)
        except Exception as e:
            print(f"Error embedding book {isbn}: {e}")
            continue
            
    if not embeddings:
        return np.zeros(384, dtype="float32")
        
    embeddings = np.array(embeddings)
    weights = np.array(weights)[:, np.newaxis]
    
    # Calculate weighted average
    taste_vector = np.sum(embeddings * weights, axis=0) / np.sum(weights)
    
    # L2 normalize the resulting taste vector
    norm = np.linalg.norm(taste_vector)
    if norm > 0:
        taste_vector = taste_vector / norm
        
    return taste_vector.astype("float32")

def save_user_taste_vector(user_id: int, taste_vector: np.ndarray):
    """Persist user taste vector to disk."""
    path = os.path.join(EMBEDDINGS_DIR, f"user_{user_id}_taste.npy")
    np.save(path, taste_vector)

def load_user_taste_vector(user_id: int) -> np.ndarray:
    """Load user taste vector from disk."""
    path = os.path.join(EMBEDDINGS_DIR, f"user_{user_id}_taste.npy")
    if os.path.exists(path):
        return np.load(path)
    return None

def search_similar_books_faiss(query_text: str, top_k=5):
    """
    Search book catalog by text query using FAISS vector similarity.
    Returns: list of (book_metadata, score)
    """
    load_content_assets()
    model = get_sentence_model()
    
    # Embed query and normalize for cosine similarity
    query_emb = model.encode(query_text).astype("float32")
    faiss.normalize_L2(query_emb.reshape(1, -1))
    
    # Search
    scores, indices = _faiss_index.search(query_emb.reshape(1, -1), top_k)
    
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0 and idx < len(_book_catalog):
            row = _book_catalog.iloc[idx].to_dict()
            results.append((row, float(score)))
            
    return results

def get_genre_overlap_score(user_genres_pref: dict, candidate_genres: str) -> float:
    """
    Calculate Jaccard-like overlap score between candidate book's genres
    and user's favored genres.
    """
    if not candidate_genres or not user_genres_pref:
        return 0.0
    # Clean candidate genres: replace hyphens, underscores, and punctuation
    raw_tokens = [g.strip().lower() for g in re.split(r"[|,;]", candidate_genres) if g.strip()]
    if not raw_tokens:
        return 0.0
        
    best_match = 0.0
    for cand_g in raw_tokens:
        clean_cand = re.sub(r"[^a-z0-9\s]", " ", cand_g).strip()
        cand_words = set(clean_cand.split())
        for ug, weight in user_genres_pref.items():
            clean_ug = re.sub(r"[^a-z0-9\s]", " ", ug).strip()
            ug_words = set(clean_ug.split())
            # Match exact, substring, or token overlap (e.g. fantasy in epic fantasy, sci-fi in science fiction)
            if ug in clean_cand or clean_cand in ug or (ug_words & cand_words):
                if weight > best_match:
                    best_match = weight
                    
    return float(best_match)
