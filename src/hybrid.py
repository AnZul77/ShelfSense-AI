import os
import re
import numpy as np
import pandas as pd
from collections import defaultdict
from sqlalchemy.orm import Session

from backend.database import Book, Rating
from src.collaborative import get_bpr_recommendations, get_cf_recommendations, load_collaborative_assets
from src.content_based import (
    load_content_assets, 
    generate_user_taste_vector, 
    get_book_embedding_by_isbn, 
    get_genre_overlap_score
)

DATA_DIR = r"c:\Users\anshu\Documents\codes\ML\BookRecomendation\data"

# Global popularity cache
_popularity_dict = {}
_max_popularity = 1

def load_popularity_assets():
    global _popularity_dict, _max_popularity
    if _popularity_dict:
        return
        
    print("Loading Popularity assets...")
    train_df_path = os.path.join(DATA_DIR, "processed", "train_df.csv")
    if os.path.exists(train_df_path):
        try:
            df = pd.read_csv(train_df_path)
            counts = df["ISBN"].value_counts().to_dict()
            _popularity_dict = counts
            if counts:
                _max_popularity = max(counts.values())
        except Exception as e:
            print(f"Error loading popularity counts: {e}")
            _popularity_dict = {}
            _max_popularity = 1
    else:
        _popularity_dict = {}
        _max_popularity = 1

def normalize_scores(score_list):
    """Normalize a list of (item, score) tuples to [0, 1] range."""
    if not score_list:
        return {}
    scores = [s for _, s in score_list]
    min_s = min(scores)
    max_s = max(scores)
    if max_s == min_s:
        return {item: 1.0 for item, _ in score_list}
    return {item: (s - min_s) / (max_s - min_s) for item, s in score_list}

def hybrid_recommend_shelf(user_id: int, shelf_isbns: list, db: Session, weights: dict = None):
    """
    Ranks the books physically present on the shelf using a hybrid recommendation score.
    weights: dict of weights for Collaborative, Content, Author, Popularity.
             Defaults to: 0.40 Collaborative, 0.35 Content, 0.15 Author, 0.10 Popularity.
    """
    if weights is None:
        weights = {
            "collaborative": 0.40,
            "content": 0.35,
            "author": 0.15,
            "popularity": 0.10
        }
        
    load_collaborative_assets()
    load_content_assets()
    load_popularity_assets()
    
    # 1. Fetch user's rating history
    user_ratings = db.query(Rating).filter(Rating.user_id == user_id).all()
    user_ratings_list = [{"isbn": r.book_id, "rating": r.rating} for r in user_ratings]
    already_read_isbns = {r.book_id for r in user_ratings}
    
    # User taste vector for semantic search
    user_taste_vector = generate_user_taste_vector(user_ratings_list, db)
    
    # Genre preferences from user history (books rated >= 4)
    user_genres_pref = defaultdict(int)
    liked_books_count = 0
    liked_books = []
    
    for r in user_ratings:
        if r.rating >= 4:
            liked_books_count += 1
            # Fetch book details
            bk = db.query(Book).filter(Book.book_id == r.book_id).first()
            if bk:
                liked_books.append(bk)
                if bk.genres:
                    for g in re.split(r"[|,;]", bk.genres):
                        g_clean = g.strip().lower()
                        if g_clean:
                            user_genres_pref[g_clean] += r.rating
                            
    # Normalize genre weights
    if liked_books_count > 0:
        for g in user_genres_pref:
            user_genres_pref[g] = user_genres_pref[g] / (liked_books_count * 5.0)
            
    # Preferred authors
    user_author_pref = defaultdict(list)
    for r in user_ratings:
        bk = db.query(Book).filter(Book.book_id == r.book_id).first()
        if bk and bk.author:
            user_author_pref[bk.author.lower().strip()].append(r.rating)
            
    # 2. Get collaborative recommendations (CF and BPR)
    cf_raw = get_cf_recommendations(None, rated_books=user_ratings_list, top_k=500)
    bpr_raw = get_bpr_recommendations(user_id, rated_books=user_ratings_list, top_k=500)
    
    cf_norm = normalize_scores(cf_raw)
    bpr_norm = normalize_scores(bpr_raw)
    
    # 3. Calculate scores for candidate shelf books
    scored_recommendations = []
    
    for isbn in shelf_isbns:
        book = db.query(Book).filter(Book.book_id == isbn).first()
        if not book:
            continue
            
        # Already Read duplicate flag
        is_already_read = isbn in already_read_isbns
        
        # A. Collaborative Score (BPR + CF normalized)
        # Fallback if book is missing from collaborative matrices
        bpr_val = bpr_norm.get(isbn, 0.0)
        cf_val = cf_norm.get(isbn, 0.0)
        collab_score = 0.5 * bpr_val + 0.5 * cf_val
        
        # B. Content Score (Semantic Similarity + Genre Overlap)
        # Get book embedding
        book_emb = get_book_embedding_by_isbn(isbn, db)
        semantic_sim = 0.0
        if book_emb is not None and user_taste_vector is not None:
            # Cosine similarity (since both are normalized)
            semantic_sim = float(np.dot(user_taste_vector, book_emb))
            # Clip to [0, 1]
            semantic_sim = max(0.0, min(1.0, semantic_sim))
            
        genre_overlap = get_genre_overlap_score(user_genres_pref, book.genres)
        content_score = 0.7 * semantic_sim + 0.3 * genre_overlap
        
        # C. Author Score (Author preference weighting)
        author_score = 0.0
        if book.author:
            auth_clean = book.author.lower().strip()
            if auth_clean in user_author_pref:
                author_score = sum(user_author_pref[auth_clean]) / (len(user_author_pref[auth_clean]) * 5.0)
                
        # D. Popularity Score
        pop_count = _popularity_dict.get(isbn, 0)
        # Logarithmic scaling
        popularity_score = np.log1p(pop_count) / np.log1p(_max_popularity)
        
        # E. Final Hybrid Weighted Score
        final_score = (
            weights["collaborative"] * collab_score +
            weights["content"] * content_score +
            weights["author"] * author_score +
            weights["popularity"] * popularity_score
        )
        
        # F. Buy Score (0-100)
        buy_score = int(final_score * 100)
        # Clamp between 0 and 100
        buy_score = max(0, min(100, buy_score))
        
        # G. Generate dynamic explanations
        explanation = ""
        # Author check
        if author_score > 0:
            explanation = f"Matches your interest in author {book.author}. "
            
        # Semantic check against individual liked books
        best_match_title = ""
        best_match_sim = -1.0
        if len(liked_books) > 0 and book_emb is not None:
            for l_bk in liked_books:
                l_emb = get_book_embedding_by_isbn(l_bk.book_id, db)
                if l_emb is not None:
                    sim = float(np.dot(l_emb, book_emb))
                    if sim > best_match_sim:
                        best_match_sim = sim
                        best_match_title = l_bk.title
                        
        if best_match_sim > 0.45 and best_match_title:
            explanation += f"Similar themes to '{best_match_title}'. "
        elif genre_overlap > 0.3:
            # Genre overlap check
            # Find the top matching genre
            cand_genres = [g.strip().lower() for g in re.split(r"[|,;]", book.genres) if g.strip()]
            matching_genres = [g for g in cand_genres if g in user_genres_pref]
            if matching_genres:
                explanation += f"Matches your reading interest in {matching_genres[0].capitalize()}. "
        else:
            explanation += "Complements your profile and popular ratings."
            
        scored_recommendations.append({
            "book_id": isbn,
            "title": book.title,
            "author": book.author,
            "description": book.description,
            "genres": book.genres,
            "image_url": book.image_url,
            "score": float(final_score),
            "buy_score": buy_score,
            "explanation": explanation.strip(),
            "already_read": is_already_read
        })
        
    # Sort recommendations by score descending
    scored_recommendations.sort(key=lambda x: x["score"], reverse=True)
    return scored_recommendations

def get_reading_dna(user_id: int, db: Session) -> dict:
    """Generate User Reading DNA genre percentages based on ratings >= 4."""
    user_ratings = db.query(Rating).filter(Rating.user_id == user_id, Rating.rating >= 4).all()
    if not user_ratings:
        return {}
        
    genre_counts = defaultdict(int)
    total_genres = 0
    
    for r in user_ratings:
        book = db.query(Book).filter(Book.book_id == r.book_id).first()
        if book and book.genres:
            # Parse genres
            for g in re.split(r"[|,;]", book.genres):
                g_clean = g.strip().capitalize()
                if g_clean:
                    genre_counts[g_clean] += 1
                    total_genres += 1
                    
    if total_genres == 0:
        return {}
        
    # Convert to percentages
    reading_dna = {}
    for g, count in genre_counts.items():
        reading_dna[g] = round((count / total_genres) * 100, 1)
        
    # Sort descending
    sorted_dna = dict(sorted(reading_dna.items(), key=lambda x: x[1], reverse=True))
    return sorted_dna

def get_author_exploration(user_id: int, db: Session, top_k=5) -> list:
    """Recommend books by authors the user likes, which they haven't read/rated yet."""
    user_ratings = db.query(Rating).filter(Rating.user_id == user_id).all()
    already_read_isbns = {r.book_id for r in user_ratings}
    
    # Get user's favored authors (average rating >= 4)
    author_ratings = defaultdict(list)
    for r in user_ratings:
        book = db.query(Book).filter(Book.book_id == r.book_id).first()
        if book and book.author:
            author_ratings[book.author].append(r.rating)
            
    favored_authors = []
    for author, ratings in author_ratings.items():
        if np.mean(ratings) >= 4.0:
            favored_authors.append(author)
            
    if not favored_authors:
        return []
        
    # Fetch other books by these authors that the user has not read yet
    exploration_books = []
    for author in favored_authors[:3]: # Limit to top 3 authors
        other_books = db.query(Book).filter(
            Book.author == author,
            ~Book.book_id.in_(already_read_isbns)
        ).limit(5).all()
        
        for ob in other_books:
            exploration_books.append({
                "book_id": ob.book_id,
                "title": ob.title,
                "author": ob.author,
                "description": ob.description,
                "genres": ob.genres,
                "image_url": ob.image_url,
                "reason": f"Popular book by one of your favorite authors, {author}"
            })
            
    return exploration_books[:top_k]

def get_reading_path(recommended_books: list) -> list:
    """Suggests reading order if multiple books belong to the same author."""
    # Group books by author
    author_groups = defaultdict(list)
    for b in recommended_books:
        if b["author"]:
            author_groups[b["author"]].append(b)
            
    reading_paths = []
    for author, books in author_groups.items():
        if len(books) >= 2:
            # Sort books alphabetically or by score (since we don't have detailed volume sequence,
            # we sort by publication year or score descending, here we sort by title for stable ordering)
            sorted_books = sorted(books, key=lambda x: x["title"])
            path_str = " ➔ ".join([b["title"] for b in sorted_books])
            reading_paths.append({
                "author": author,
                "path": path_str,
                "books": [b["title"] for b in sorted_books]
            })
            
    return reading_paths
