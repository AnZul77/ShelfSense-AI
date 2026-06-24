import os
import sys
import pickle

# Initialize NumPy 2.x compatibility layer for pickling
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.numpy_compat

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from collections import defaultdict

MODELS_DIR = r"c:\Users\anshu\Documents\codes\ML\BookRecomendation\models"
DATA_DIR = r"c:\Users\anshu\Documents\codes\ML\BookRecomendation\data"

class BPRModel(nn.Module):
    def __init__(self, n_users, n_books, embedding_dim=50):
        super().__init__()
        self.user_embedding = nn.Embedding(n_users, embedding_dim)
        self.book_embedding = nn.Embedding(n_books, embedding_dim)

    def forward(self, users, pos_items, neg_items=None):
        user_emb = self.user_embedding(users)
        pos_emb = self.book_embedding(pos_items)
        if neg_items is not None:
            neg_emb = self.book_embedding(neg_items)
            pos_scores = (user_emb * pos_emb).sum(dim=1)
            neg_scores = (user_emb * neg_emb).sum(dim=1)
            return pos_scores, neg_scores
        return (user_emb * pos_emb).sum(dim=1)

# Global variables for caching
_bpr_model = None
_bpr_config = None
_book2idx = None
_user2idx = None
_idx2book = None
_idx2user = None
_item_similarity_df = None
_train_df = None

def load_collaborative_assets():
    global _bpr_model, _bpr_config, _book2idx, _user2idx, _idx2book, _idx2user, _item_similarity_df, _train_df
    
    if _bpr_model is not None:
        return
        
    print("Loading Collaborative Filtering assets...")
    
    # Mappings
    with open(os.path.join(MODELS_DIR, "book2idx.pkl"), "rb") as f:
        _book2idx = pickle.load(f)
    with open(os.path.join(MODELS_DIR, "user2idx.pkl"), "rb") as f:
        _user2idx = pickle.load(f)
    with open(os.path.join(MODELS_DIR, "idx2book.pkl"), "rb") as f:
        _idx2book = pickle.load(f)
    with open(os.path.join(MODELS_DIR, "idx2user.pkl"), "rb") as f:
        _idx2user = pickle.load(f)
        
    # BPR Model Configuration
    # Safe load using CPU
    bpr_cfg_path = os.path.join(MODELS_DIR, "bpr_config.pth")
    if os.path.exists(bpr_cfg_path):
        try:
            # Bypass weights_only for compatibility
            _bpr_config = torch.load(bpr_cfg_path, map_location="cpu", weights_only=False)
        except Exception:
            # Fallback hardcoded matching training parameters
            _bpr_config = {
                "n_users": len(_user2idx),
                "n_books": len(_book2idx),
                "embedding_dim": 50
            }
    else:
        _bpr_config = {
            "n_users": len(_user2idx),
            "n_books": len(_book2idx),
            "embedding_dim": 50
        }
        
    # BPR Model State Dict
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _bpr_model = BPRModel(
        n_users=int(_bpr_config["n_users"]),
        n_books=int(_bpr_config["n_books"]),
        embedding_dim=int(_bpr_config["embedding_dim"])
    )
    _bpr_model.load_state_dict(
        torch.load(os.path.join(MODELS_DIR, "bpr_model.pth"), map_location=device, weights_only=True)
    )
    _bpr_model.to(device)
    _bpr_model.eval()
    
    # Item-Similarity Dataframe (optional/ignored in Git)
    similarity_path = os.path.join(MODELS_DIR, "item_similarity_df.pkl")
    if os.path.exists(similarity_path):
        with open(similarity_path, "rb") as f:
            _item_similarity_df = pickle.load(f)
    else:
        print("Warning: item_similarity_df.pkl not found. Item-based collaborative recommendations will be disabled.")
        _item_similarity_df = None
        
    # Train DF (for ratings CF)
    train_df_path = os.path.join(DATA_DIR, "processed", "train_df.csv")
    if os.path.exists(train_df_path):
        _train_df = pd.read_csv(train_df_path)
    else:
        # Fallback to empty if not found
        _train_df = pd.DataFrame(columns=["User-ID", "ISBN", "Rating", "user_idx", "book_idx"])

def get_bpr_recommendations(user_id, rated_books=None, top_k=100):
    """
    Get BPR scores for candidate books.
    rated_books: list of dicts [{'isbn': str, 'rating': int}] representing the user's active ratings.
    """
    load_collaborative_assets()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Check if user exists in the pre-trained dataset
    user_idx = _user2idx.get(user_id)
    
    _bpr_model.eval()
    with torch.no_grad():
        if user_idx is not None:
            # User exists, get their embedding vector (already on CUDA if model is on CUDA)
            user_vec = _bpr_model.user_embedding.weight[user_idx]
        else:
            # New user (Cold Start): represent user embedding as the mean of their highly rated books' embeddings
            if not rated_books:
                # Absolute cold start with no ratings: return default zero scores
                return []
            
            # Filter high ratings (>= 4 stars) or fallback to all ratings if none >= 4
            high_rated = [b for b in rated_books if b.get("rating", 0) >= 4]
            if not high_rated:
                high_rated = rated_books
                
            book_vecs = []
            for b in high_rated:
                b_idx = _book2idx.get(b.get("isbn"))
                if b_idx is not None:
                    # Retrieve the weight tensor directly from the model (which is on device) and convert to CPU/numpy
                    book_vecs.append(_bpr_model.book_embedding.weight[b_idx].cpu().numpy())
            
            if len(book_vecs) > 0:
                user_vec = torch.tensor(np.mean(book_vecs, axis=0), device=device)
            else:
                # No rated books have BPR embeddings: return empty
                return []
                
        # Calculate dot product score against all book embeddings
        book_vecs = _bpr_model.book_embedding.weight
        scores = torch.matmul(book_vecs, user_vec).cpu().numpy()
        
    # Mask books the user has already rated/read
    seen_isbns = set()
    if rated_books:
        seen_isbns = {b.get("isbn") for b in rated_books}
        
    # Translate BPR index to ISBN and build results list
    recs = []
    for book_idx in range(len(scores)):
        isbn = _idx2book.get(book_idx)
        if isbn and isbn not in seen_isbns:
            recs.append((isbn, float(scores[book_idx])))
            
    # Sort and return top_k
    recs.sort(key=lambda x: x[1], reverse=True)
    return recs[:top_k]

def get_cf_recommendations(user_id, rated_books=None, top_k=100, k=10):
    """
    Get Collaborative Filtering (Item-based) recommendations.
    rated_books: list of dicts [{'isbn': str, 'rating': int}] representing the user's active ratings.
    """
    load_collaborative_assets()
    
    # We rely on user's active ratings. If none are provided, load from train_df if the user exists
    user_ratings = []
    if rated_books:
        user_ratings = rated_books
    elif user_id is not None:
        user_idx = _user2idx.get(user_id)
        if user_idx is not None and _train_df is not None:
            user_rows = _train_df[_train_df["user_idx"] == user_idx]
            for _, row in user_rows.iterrows():
                user_ratings.append({
                    "isbn": row["ISBN"],
                    "rating": row["Rating"]
                })
                
    if not user_ratings or _item_similarity_df is None:
        return []
        
    scores = defaultdict(float)
    already_read = {r["isbn"] for r in user_ratings}
    
    for r in user_ratings:
        isbn = r["isbn"]
        rating = r["rating"]
        
        # Map ISBN to BPR book_idx because item_similarity_df uses book_idx (0 to 9008)
        book_idx = _book2idx.get(isbn)
        if book_idx is None or book_idx not in _item_similarity_df.index:
            continue
            
        # Get k nearest neighbors
        neighbors = _item_similarity_df[book_idx].sort_values(ascending=False).iloc[1:k+1]
        for sim_book, sim_score in neighbors.items():
            sim_isbn = _idx2book.get(sim_book)
            if sim_isbn and sim_isbn not in already_read:
                scores[sim_isbn] += sim_score * rating
                
    recs = [(isbn, score) for isbn, score in scores.items()]
    recs.sort(key=lambda x: x[1], reverse=True)
    return recs[:top_k]
