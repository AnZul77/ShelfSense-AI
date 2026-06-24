import os
from datetime import datetime
import json
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Determine Database URL: fall back to SQLite locally
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///c:/Users/anshu/Documents/codes/ML/BookRecomendation/backend/bookshelf.db")

# For SQLite, enable check_same_thread=False
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    ratings = relationship("Rating", back_populates="user", cascade="all, delete-orphan")
    scans = relationship("ShelfScan", back_populates="user", cascade="all, delete-orphan")
    wishlist = relationship("Wishlist", back_populates="user", cascade="all, delete-orphan")

class Book(Base):
    __tablename__ = "books"

    book_id = Column(String, primary_key=True, index=True)  # Primary key maps to ISBN or work_key
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    genres = Column(String, nullable=True)  # Pipe separated, e.g. "Fantasy|Fiction"
    image_url = Column(String, nullable=True)
    normalized_title = Column(String, nullable=False, index=True)
    normalized_author = Column(String, nullable=True, index=True)

    ratings = relationship("Rating", back_populates="book", cascade="all, delete-orphan")
    wishlist = relationship("Wishlist", back_populates="book", cascade="all, delete-orphan")

class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(String, ForeignKey("books.book_id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 rating
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ratings")
    book = relationship("Book", back_populates="ratings")

class ShelfScan(Base):
    __tablename__ = "shelf_scans"

    scan_id = Column(String, primary_key=True, index=True)  # Unique scan UUID or string
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_path = Column(String, nullable=False)
    annotated_image_path = Column(String, nullable=True)
    detected_books_json = Column(Text, nullable=True)  # JSON representation of detected books & bounding boxes
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="scans")

    def get_detected_books(self):
        if not self.detected_books_json:
            return []
        try:
            return json.loads(self.detected_books_json)
        except Exception:
            return []

    def set_detected_books(self, data):
        self.detected_books_json = json.dumps(data)

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(String, ForeignKey("books.book_id"), nullable=False)
    score = Column(Float, nullable=False)
    buy_score = Column(Integer, nullable=False)  # 0-100 buy score
    explanation = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Wishlist(Base):
    __tablename__ = "wishlist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(String, ForeignKey("books.book_id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="wishlist")
    book = relationship("Book", back_populates="wishlist")

# Database indexes for optimization
Index("idx_rating_user_book", Rating.user_id, Rating.book_id, unique=True)
Index("idx_wishlist_user_book", Wishlist.user_id, Wishlist.book_id, unique=True)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
