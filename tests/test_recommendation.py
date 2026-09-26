import pytest
import src.numpy_compat
from src.collaborative import load_collaborative_assets, get_bpr_recommendations, get_cf_recommendations
from src.hybrid import normalize_scores, get_reading_dna
from backend.database import SessionLocal, User, Book, Rating

def test_collaborative_assets_loading():
    load_collaborative_assets()
    from src.collaborative import _bpr_model, _item_top_neighbors
    assert _bpr_model is not None
    assert _item_top_neighbors is not None
    assert len(_item_top_neighbors) > 0

def test_cf_recommendations():
    # Test item-item CF using Harry Potter ISBN 0439139597
    recs = get_cf_recommendations(user_id=None, rated_books=[{"isbn": "0439139597", "rating": 5}], top_k=5)
    assert len(recs) > 0
    # Top recs should be other Harry Potter books
    top_isbns = [isbn for isbn, score in recs]
    assert any(hp_isbn in top_isbns for hp_isbn in ["0439136350", "0439064864", "0590353403", "043935806X"])

def test_bpr_cold_start_recommendations():
    # User with single high rating gets cold start embedding
    recs = get_bpr_recommendations(user_id=999999, rated_books=[{"isbn": "0439139597", "rating": 5}], top_k=10)
    assert len(recs) > 0

def test_score_normalization():
    raw_scores = [("A", 10.0), ("B", 20.0), ("C", 30.0)]
    normalized = normalize_scores(raw_scores)
    assert normalized["A"] == 0.0
    assert normalized["C"] == 1.0
    assert normalized["B"] == 0.5

def test_reading_dna_fallback():
    db = SessionLocal()
    try:
        dna = get_reading_dna(user_id=999999, db=db)
        # Empty user should return empty dict
        assert dna == {}
    finally:
        db.close()
