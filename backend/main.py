import os
import sys

# Initialize NumPy 2.x compatibility layer for pickling
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.numpy_compat

import uuid
import hashlib
from datetime import datetime
import json
from typing import List, Optional, Dict
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db, init_db, User, Book, Rating, ShelfScan, Recommendation, Wishlist
from src.cv_pipeline import process_shelf_scan, UPLOADS_DIR
from src.hybrid import get_reading_dna, get_author_exploration, get_reading_path, hybrid_recommend_shelf

# Initialize DB on startup
init_db()

app = FastAPI(
    title="ShelfSense AI API",
    description="Backend API for bookstore spine detection and personalized hybrid book recommendations.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded images statically
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# --- Self-contained Auth Helpers ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_current_user_id(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> int:
    """Simple token authentication. Token format: 'Bearer user_id' or a simple session token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format. Use Bearer <token>"
            )
        token = parts[1]
        
        # In a real app we'd decode JWT. Here we use user ID directly or decrypt simple base
        # to ensure it's robust and works for local testing
        user_id = int(token)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        return user.id
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# --- Pydantic Schemas ---
class UserRegister(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    token: str
    user_id: int
    name: str

class RatingItem(BaseModel):
    isbn: str
    rating: int

class PreferencesSubmit(BaseModel):
    ratings: List[RatingItem]

class WishlistRequest(BaseModel):
    isbn: str

class BookResponse(BaseModel):
    book_id: str
    title: str
    author: Optional[str]
    description: Optional[str]
    genres: Optional[str]
    image_url: Optional[str]

class RecommendRequest(BaseModel):
    shelf_isbns: List[str]
    weights: Optional[Dict[str, float]] = None

# --- Auth Routes ---
@app.post("/auth/register", response_model=TokenResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if user already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
        
    password_hash = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=password_hash,
        name=user_data.name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "token": str(new_user.id),
        "user_id": new_user.id,
        "name": new_user.name
    }

@app.post("/auth/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or user.password_hash != hash_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    return {
        "token": str(user.id),
        "user_id": user.id,
        "name": user.name
    }

# --- Onboarding & Preferences ---
@app.post("/user/preferences")
def save_preferences(pref_data: PreferencesSubmit, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Save user ratings (onboarding rates 5-20 books)."""
    # Remove existing ratings for these books if any to avoid uniqueness constraint violation
    isbns = [r.isbn for r in pref_data.ratings]
    db.query(Rating).filter(Rating.user_id == user_id, Rating.book_id.in_(isbns)).delete(synchronize_session=False)
    
    # Save new ratings
    for r in pref_data.ratings:
        new_rating = Rating(
            user_id=user_id,
            book_id=r.isbn,
            rating=r.rating
        )
        db.add(new_rating)
        
    db.commit()
    return {"status": "success", "message": f"Successfully saved {len(pref_data.ratings)} ratings."}

@app.get("/profile")
def get_profile(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Get profile overview including Reading DNA percentages and wishlist books."""
    user = db.query(User).filter(User.id == user_id).first()
    
    # Calculate DNA
    dna = get_reading_dna(user_id, db)
    
    # Get Wishlist
    wishlist_items = db.query(Wishlist).filter(Wishlist.user_id == user_id).all()
    wishlist_books = []
    for item in wishlist_items:
        bk = db.query(Book).filter(Book.book_id == item.book_id).first()
        if bk:
            wishlist_books.append({
                "book_id": bk.book_id,
                "title": bk.title,
                "author": bk.author,
                "genres": bk.genres,
                "image_url": bk.image_url
            })
            
    # Get ratings count
    ratings_count = db.query(Rating).filter(Rating.user_id == user_id).count()
    
    return {
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "ratings_count": ratings_count,
        "reading_dna": dna,
        "wishlist": wishlist_books
    }

# --- Computer Vision & Shelf Scanning ---
@app.post("/shelf/upload")
def upload_shelf_image(file: UploadFile = File(...), user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """
    Upload a bookstore shelf photo. Runs YOLOv8 spine crops, EasyOCR text extraction,
    multi-stage database matching, renders a heatmap overlay and returns results.
    """
    # Save uploaded file
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"scan_{uuid.uuid4().hex}{file_ext}"
    local_path = os.path.join(UPLOADS_DIR, filename)
    
    with open(local_path, "wb") as buffer:
        buffer.write(file.file.read())
        
    try:
        # Run CV Pipeline
        scan_results = process_shelf_scan(local_path, user_id, db)
        
        # Save scan history
        # detected_books list -> JSON
        detected_json = json.dumps([
            {
                "box": d["box"],
                "isbn": d["isbn"],
                "title": d["title"],
                "author": d["author"]
            } for d in scan_results["detected_books"]
        ])
        
        new_scan = ShelfScan(
            scan_id=uuid.uuid4().hex,
            user_id=user_id,
            image_path=f"/uploads/{filename}",
            annotated_image_path=scan_results["heatmap_image_url"],
            detected_books_json=detected_json
        )
        db.add(new_scan)
        db.commit()
        
        # Return results to client
        return {
            "scan_id": new_scan.scan_id,
            "original_image_url": f"/uploads/{filename}",
            "heatmap_image_url": scan_results["heatmap_image_url"],
            "detected_books": scan_results["detected_books"],
            "recommendations": scan_results["recommendations"]
        }
    except Exception as e:
        print(f"Error processing shelf scan: {e}")
        # Clean up file on error
        if os.path.exists(local_path):
            os.remove(local_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process shelf scan: {str(e)}"
        )

# --- Recommendations & History ---
@app.post("/recommend")
def recommend(req: RecommendRequest, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Get hybrid rankings and explanations for a list of candidate book ISBNs."""
    recs = hybrid_recommend_shelf(user_id, req.shelf_isbns, db, req.weights)
    
    # Extra features: reading path, author exploration
    reading_paths = get_reading_path(recs)
    author_exploration = get_author_exploration(user_id, db)
    
    return {
        "recommendations": recs,
        "reading_paths": reading_paths,
        "author_exploration": author_exploration
    }

@app.get("/history")
def get_history(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Retrieve historical shelf scans."""
    scans = db.query(ShelfScan).filter(ShelfScan.user_id == user_id).order_by(ShelfScan.timestamp.desc()).all()
    history = []
    for s in scans:
        history.append({
            "scan_id": s.scan_id,
            "original_image_url": s.image_path,
            "heatmap_image_url": s.annotated_image_path,
            "timestamp": s.timestamp,
            "detected_books": s.get_detected_books()
        })
    return history

# --- Wishlist Routes ---
@app.post("/wishlist/add")
def add_to_wishlist(req: WishlistRequest, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    # Check if book exists
    book = db.query(Book).filter(Book.book_id == req.isbn).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
        
    # Check if already in wishlist
    existing = db.query(Wishlist).filter(Wishlist.user_id == user_id, Wishlist.book_id == req.isbn).first()
    if existing:
        return {"status": "success", "message": "Already in wishlist"}
        
    new_item = Wishlist(user_id=user_id, book_id=req.isbn)
    db.add(new_item)
    db.commit()
    return {"status": "success", "message": "Added to wishlist"}

@app.delete("/wishlist/remove/{isbn}")
def remove_from_wishlist(isbn: str, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    item = db.query(Wishlist).filter(Wishlist.user_id == user_id, Wishlist.book_id == isbn).first()
    if not item:
        raise HTTPException(status_code=404, detail="Wishlist item not found")
    db.delete(item)
    db.commit()
    return {"status": "success", "message": "Removed from wishlist"}

# --- Catalog Search & Lookup ---
@app.get("/books")
def search_books(q: Optional[str] = None, db: Session = Depends(get_db)):
    """Search catalog books by title or author with normalized multi-word matching."""
    import re
    if not q or not q.strip():
        # Curate a high-quality list of recent, popular fantasy/sci-fi authors
        popular_authors = [
            "Brandon Sanderson", "Terry Pratchett", "J.R.R. Tolkien", 
            "George R.R. Martin", "Patrick Rothfuss", "Robert Jordan", 
            "Joe Abercrombie", "John Gwynne", "Alastair Reynolds"
        ]
        # Match popular authors to return diverse set of recent books
        conditions = [Book.author.like(f"%{auth}%") for auth in popular_authors]
        books = db.query(Book).filter(or_(*conditions)).limit(40).all()
    else:
        # Split search query into normalized words
        terms = [re.sub(r"[^a-z0-9]", "", t.lower()) for t in q.split() if t]
        if not terms:
            return []
        
        # Build query where each term must match normalized_title or normalized_author
        conditions = []
        for term in terms:
            conditions.append(
                or_(
                    Book.normalized_title.like(f"%{term}%"),
                    Book.normalized_author.like(f"%{term}%")
                )
            )
        books = db.query(Book).filter(*conditions).limit(40).all()
        
    return [
        {
            "book_id": b.book_id,
            "title": b.title,
            "author": b.author,
            "genres": b.genres,
            "image_url": b.image_url,
            "description": b.description
        } for b in books
    ]

@app.get("/book/{isbn}")
def get_book_details(isbn: str, db: Session = Depends(get_db)):
    """Fetch details of a single book by ISBN."""
    book = db.query(Book).filter(Book.book_id == isbn).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return {
        "book_id": book.book_id,
        "title": book.title,
        "author": book.author,
        "description": book.description,
        "genres": book.genres,
        "image_url": book.image_url
    }

# Root Status
@app.get("/")
def root():
    return {
        "status": "running",
        "service": "ShelfSense AI API",
        "timestamp": datetime.utcnow()
    }