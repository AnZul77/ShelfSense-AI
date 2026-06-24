import os
import sys

# Initialize NumPy 2.x compatibility layer for pickling
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.numpy_compat

from sqlalchemy.orm import Session

# Add backend directory and parent directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, User, Book, Rating, ShelfScan
from src.hybrid import hybrid_recommend_shelf, get_reading_dna
from src.evaluation import calculate_hit_ratio_at_k, calculate_ndcg_at_k, calculate_map_at_k

def run_verification():
    print("=== STARTING SHELFSENSE AI SYSTEM VERIFICATION ===")
    
    db: Session = SessionLocal()
    
    # 1. Create a verification user
    test_email = "verify_user@shelfsense.ai"
    # Clean up previous test run
    old_user = db.query(User).filter(User.email == test_email).first()
    if old_user:
        db.query(Rating).filter(Rating.user_id == old_user.id).delete()
        db.query(ShelfScan).filter(ShelfScan.user_id == old_user.id).delete()
        db.delete(old_user)
        db.commit()
        print("Cleaned up previous verification user.")

    verify_user = User(
        email=test_email,
        password_hash="verified_hash",
        name="Verification Tester"
    )
    db.add(verify_user)
    db.commit()
    db.refresh(verify_user)
    print(f"Created test user: {verify_user.name} (ID: {verify_user.id})")

    # 2. Add onboarding ratings (Rate 5 books Brandon Sanderson & others)
    # Let's search books in our database to rate them
    books_to_rate = db.query(Book).limit(6).all()
    if len(books_to_rate) < 5:
        print("Error: Seeding is incomplete or database lacks books!")
        db.close()
        return

    ratings = [5, 5, 4, 5, 4, 3]
    for b, rating in zip(books_to_rate, ratings):
        r = Rating(
            user_id=verify_user.id,
            book_id=b.book_id,
            rating=rating
        )
        db.add(r)
    db.commit()
    print(f"Added {len(books_to_rate)} preference ratings to user profile.")

    # 3. Verify Reading DNA
    dna = get_reading_dna(verify_user.id, db)
    print(f"Generated Reading DNA: {dna}")

    # 4. Run Hybrid Recommendation on mock shelf (the rated books + a few other candidates)
    candidate_books = db.query(Book).offset(5).limit(10).all()
    shelf_isbns = [b.book_id for b in books_to_rate] + [b.book_id for b in candidate_books]
    
    print(f"\nSimulating shelf upload with {len(shelf_isbns)} books...")
    recs = hybrid_recommend_shelf(verify_user.id, shelf_isbns, db)
    
    print("\nRecommendations Output (Top 5):")
    for idx, r in enumerate(recs[:5]):
        print(f"  {idx+1}. Book: {r['title']} (by {r['author']})")
        print(f"     Buy Score: {r['buy_score']}% | Already Read: {r['already_read']}")
        print(f"     Explanation: {r['explanation']}")
        print("-" * 50)

    # 5. Evaluate Recommendation Quality metrics (Hit@5, NDCG@5, MAP@5)
    # Let's say our ground truth (relevant books) are the ones rated 5 stars by the user
    ground_truth = [b.book_id for b, r in zip(books_to_rate, ratings) if r == 5]
    recommended_ids = [r["book_id"] for r in recs]
    
    hit_ratio = calculate_hit_ratio_at_k(recommended_ids, ground_truth, k=5)
    ndcg = calculate_ndcg_at_k(recommended_ids, ground_truth, k=5)
    map_score = calculate_map_at_k(recommended_ids, ground_truth, k=5)
    
    print("\n=== SYSTEM METRICS VERIFICATION ===")
    print(f"  Ground Truth Books (5-star ratings): {ground_truth}")
    print(f"  Hit Ratio @ 5: {hit_ratio * 100:.1f}%")
    print(f"  NDCG @ 5: {ndcg:.4f}")
    print(f"  MAP @ 5: {map_score:.4f}")
    print("=========================================")

    # Clean up test user
    db.query(Rating).filter(Rating.user_id == verify_user.id).delete()
    db.delete(verify_user)
    db.commit()
    db.close()
    print("Verification completed and database cleaned up.")

if __name__ == "__main__":
    run_verification()
