import os
import sys
import time
import numpy as np

# Compatibility layer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.numpy_compat

from backend.database import SessionLocal, Book, User, Rating
from src.hybrid import (
    load_collaborative_assets,
    load_content_assets,
    load_popularity_assets,
    hybrid_recommend_shelf,
    get_reading_dna
)
from src.content_based import get_sentence_model, get_book_embedding_by_isbn

def run_mlops_evaluation():
    print("=" * 60)
    print("ShelfSense AI - MLOps Offline Evaluation & Quality Benchmark")
    print("=" * 60)
    
    t0 = time.time()
    db = SessionLocal()
    
    # 1. Asset Loading & Memory Benchmarks
    print("\n[1/4] Verifying ML Asset Loading & Latency Benchmarks...")
    t_start = time.time()
    load_collaborative_assets()
    t_collab = time.time() - t_start
    print(f"  - Collaborative Assets Load Time: {t_collab:.3f}s")
    
    t_start = time.time()
    load_content_assets()
    t_content = time.time() - t_start
    print(f"  - Content & Vector Index Load Time: {t_content:.3f}s")
    
    load_popularity_assets()
    
    # 2. Embedding Latency Benchmark
    print("\n[2/4] Benchmarking Semantic Encoder Latency...")
    model = get_sentence_model()
    test_texts = [
        "The Way of Kings: Roshar is a world of stone and storms.",
        "Dune: Set on the desert planet Arrakis, following Paul Atreides.",
        "Pride and Prejudice: Romantic clash between Elizabeth and Darcy."
    ]
    t_start = time.time()
    embs = model.encode(test_texts, normalize_embeddings=True)
    t_embed = (time.time() - t_start) / len(test_texts)
    print(f"  - Per-item Vector Inference: {t_embed*1000:.2f}ms (Device: {model.device})")
    assert embs.shape == (3, 384), f"Unexpected embedding shape: {embs.shape}"
    assert np.isclose(np.linalg.norm(embs[0]), 1.0, atol=1e-3), "Embeddings are not unit normalized!"
    print("  - Vector Normalization Verification: PASSED (L2 Norm = 1.000)")

    # 3. Persona Scoring Accuracy & Calibration
    print("\n[3/4] Evaluating Recommendation Persona Calibration...")
    
    # Create or fetch benchmark user
    bench_user = db.query(User).filter(User.email == "mlops_benchmark@shelfsense.test").first()
    if not bench_user:
        bench_user = User(
            email="mlops_benchmark@shelfsense.test",
            password_hash="test_hash",
            name="MLOps Benchmark Reader"
        )
        db.add(bench_user)
        db.commit()
        db.refresh(bench_user)

    # Clean existing ratings
    db.query(Rating).filter(Rating.user_id == bench_user.id).delete()
    
    # Seed Fantasy/Sci-Fi Persona Ratings: Dune, Ender's Game, Hobbit
    seed_specs = [
        ("Dune", "Herbert"),
        ("Ender's Game", "Card"),
        ("The Hobbit", "Tolkien")
    ]
    seeded_books = []
    from src.enrichment import enrich_book_in_db
    for t_spec, a_spec in seed_specs:
        bk = db.query(Book).filter(Book.title.like(f"%{t_spec}%"), Book.author.like(f"%{a_spec}%")).first()
        if bk:
            if not bk.genres or not bk.description:
                try:
                    enrich_book_in_db(bk, db)
                except Exception:
                    pass
            db.add(Rating(user_id=bench_user.id, book_id=bk.book_id, rating=5))
            seeded_books.append(bk)
    db.commit()
    print(f"  - Seeded {len(seeded_books)} positive ratings for Fantasy/Sci-Fi persona:")
    for b in seeded_books:
        print(f"    * {b.title} ({b.author}) [Genres: {b.genres or 'None'}]")

    # Evaluate Candidate Shelf
    # 1 High Fantasy (Target positive), 1 Modern Sci-Fi (Target positive), 1 Out-of-domain Romance/Finance (Target negative)
    candidates = []
    
    c1 = db.query(Book).filter(Book.normalized_title == "words of radiance").first()
    if not c1:
        c1 = db.query(Book).filter(Book.normalized_title.like("%words of radiance%")).first()
    if c1:
        if not c1.genres or not c1.description: enrich_book_in_db(c1, db)
        candidates.append(("Words of Radiance (Sanderson Fantasy)", c1.book_id, "POSITIVE"))
    
    c2 = db.query(Book).filter(Book.normalized_title == "project hail mary", Book.genres.like("%science%")).first()
    if not c2:
        c2 = db.query(Book).filter(Book.normalized_title == "project hail mary").first()
    if c2:
        if not c2.genres or not c2.description: enrich_book_in_db(c2, db)
        candidates.append(("Project Hail Mary (Weir Sci-Fi)", c2.book_id, "POSITIVE"))
    
    c3 = db.query(Book).filter(Book.normalized_title == "the catcher in the rye").first()
    if not c3:
        c3 = db.query(Book).filter(Book.normalized_title.like("%catcher in the rye%")).first()
    if c3:
        if not c3.genres or not c3.description: enrich_book_in_db(c3, db)
        candidates.append(("Catcher in the Rye (General Fiction)", c3.book_id, "NEGATIVE"))

    candidate_isbns = [c[1] for c in candidates]
    
    t_start = time.time()
    recs = hybrid_recommend_shelf(bench_user.id, candidate_isbns, db)
    t_rec = time.time() - t_start
    print(f"\n  - Hybrid Ranking Latency: {t_rec*1000:.2f}ms for {len(candidate_isbns)} books")
    
    print("\n[4/4] Persona Accuracy & Discrimination Test Results:")
    print("  " + "-" * 75)
    print(f"  {'Book Title':<40} {'Expected':<10} {'Buy Score':<12} {'Status':<10}")
    print("  " + "-" * 75)
    
    rec_dict = {r["book_id"]: r for r in recs}
    all_passed = True
    
    for label, book_id, expected in candidates:
        r = rec_dict.get(book_id)
        if not r:
            continue
        score = r["buy_score"]
        if expected == "POSITIVE":
            passed = score >= 38
            status_str = "PASS" if passed else "FAIL"
        else:
            passed = score < 25
            status_str = "PASS" if passed else "FAIL"
            
        if not passed:
            all_passed = False
            
        print(f"  {label:<40} {expected:<10} {score:>3}% Fit     [{status_str}]")
        print(f"    Explanation: {r['explanation']}")

    print("  " + "-" * 75)
    total_time = time.time() - t0
    print(f"\nEvaluation Complete in {total_time:.2f}s.")
    if all_passed:
        print("ALL QUALITY & CALIBRATION GATES PASSED! (Accuracy meets production criteria)")
    else:
        print("WARNING: Some calibration gates failed. Review weights and thresholds.")
        
    db.close()
    return all_passed

if __name__ == "__main__":
    success = run_mlops_evaluation()
    sys.exit(0 if success else 1)
