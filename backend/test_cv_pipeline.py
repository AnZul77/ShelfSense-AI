import os
import sys
from sqlalchemy.orm import Session

# Add backend directory and parent directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize numpy compat
import src.numpy_compat

from backend.database import SessionLocal, User, Rating, Book
from src.cv_pipeline import process_shelf_scan

def test_cv():
    print("=== TESTING BOOKSTORE CV PIPELINE WITH PADDLEOCR & GEMMA ===")
    
    db: Session = SessionLocal()
    
    # Check if there are books in DB
    books_count = db.query(Book).count()
    print(f"Books in database: {books_count}")
    
    # Retrieve or create a test user
    test_email = "tester@shelfsense.ai"
    user = db.query(User).filter(User.email == test_email).first()
    if not user:
        user = User(email=test_email, password_hash="hash", name="CV Tester")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Rate a few books for the user so they have a taste profile
    # Let's rate Elantris and The Way of Kings
    elantris = db.query(Book).filter(Book.title.like("%Elantris%")).first()
    way_of_kings = db.query(Book).filter(Book.title.like("%Way of Kings%")).first()
    
    if elantris:
        existing = db.query(Rating).filter(Rating.user_id == user.id, Rating.book_id == elantris.book_id).first()
        if not existing:
            r1 = Rating(user_id=user.id, book_id=elantris.book_id, rating=5)
            db.add(r1)
    if way_of_kings:
        existing = db.query(Rating).filter(Rating.user_id == user.id, Rating.book_id == way_of_kings.book_id).first()
        if not existing:
            r2 = Rating(user_id=user.id, book_id=way_of_kings.book_id, rating=5)
            db.add(r2)
    db.commit()
    print("Preferences set up for CV test user.")
    
    # Locate a sample image
    # We check in data/cv/images/
    img_path = r"c:\Users\anshu\Documents\codes\ML\BookRecomendation\data\cv\images\20.jpeg"
    if not os.path.exists(img_path):
        # Fallback to 10.jpeg
        img_path = r"c:\Users\anshu\Documents\codes\ML\BookRecomendation\data\cv\images\10.jpeg"
        
    if not os.path.exists(img_path):
        print(f"Error: Sample image not found at {img_path}")
        db.close()
        return
        
    print(f"Running pipeline on: {img_path}")
    try:
        results = process_shelf_scan(img_path, user.id, db)
        
        print("\n=== PIPELINE EXECUTION SUCCESSFUL ===")
        print(f"Heatmap image saved to: {results['heatmap_image_url']}")
        print(f"Total detected spines: {len(results['detected_books'])}")
        
        matched = [b for b in results['detected_books'] if b['isbn']]
        print(f"Total matched books in catalog: {len(matched)}")
        for idx, m in enumerate(matched[:5]):
            print(f"  {idx+1}. BBox: {m['box']} | OCR: {m['ocr_text']}")
            print(f"     Gemma: {m['gemma_title']} (by {m['gemma_author']})")
            print(f"     Database Match: {m['title']} (by {m['author']}) | Stage: {m['match_stage']}")
            
        print("\nRecommendations from shelf:")
        for idx, r in enumerate(results['recommendations'][:5]):
            print(f"  {idx+1}. {r['title']} | Score: {r['score']:.4f} | Buy: {r['buy_score']}%")
            
    except Exception as e:
        print(f"Pipeline error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_cv()
