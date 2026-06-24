import os
import sys
import pandas as pd
import re
from sqlalchemy.orm import Session

# Add backend directory and parent directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, SessionLocal, Book

def normalize_text(text):
    if not text or not isinstance(text, str):
        return ""
    # lowercase, alphanumeric only, trimmed
    return re.sub(r"[^a-z0-9\s]", "", text.lower()).strip()

def seed_database():
    print("Initializing Database Schema...")
    init_db()
    
    db: Session = SessionLocal()
    
    # We will clear the existing books and re-seed to ensure all recent books are cleanly added
    print("Clearing existing books for complete re-seed...")
    db.query(Book).delete()
    db.commit()

    # Track seen book_ids to avoid key collisions
    seen_ids = set()

    # --- 1. Seed from books_master.csv (Book-Crossing, ~271k rows) ---
    csv_path = r"c:\Users\anshu\Documents\codes\ML\BookRecomendation\data\processed\books_master.csv"
    if os.path.exists(csv_path):
        print("Loading books_master.csv...")
        chunksize = 50000
        total_loaded = 0
        try:
            for chunk in pd.read_csv(
                csv_path, 
                chunksize=chunksize, 
                low_memory=False, 
                usecols=['ISBN', 'Book-Title', 'Book-Author', 'description', 'categories', 'Image-URL-L']
            ):
                books_to_insert = []
                for _, row in chunk.iterrows():
                    isbn = str(row['ISBN']).strip()
                    if not isbn or isbn in seen_ids:
                        continue
                    seen_ids.add(isbn)
                    
                    title = str(row['Book-Title']).strip()
                    author = str(row['Book-Author']).strip() if pd.notna(row['Book-Author']) else ""
                    description = str(row['description']).strip() if pd.notna(row['description']) else ""
                    genres = str(row['categories']).strip() if pd.notna(row['categories']) else ""
                    image_url = str(row['Image-URL-L']).strip() if pd.notna(row['Image-URL-L']) else ""
                    
                    books_to_insert.append({
                        "book_id": isbn,
                        "title": title,
                        "author": author,
                        "description": description,
                        "genres": genres,
                        "image_url": image_url,
                        "normalized_title": normalize_text(title),
                        "normalized_author": normalize_text(author)
                    })
                
                if books_to_insert:
                    db.bulk_insert_mappings(Book, books_to_insert)
                    db.commit()
                    total_loaded += len(books_to_insert)
                    print(f"Seeded {total_loaded} books from books_master...")
        except Exception as e:
            db.rollback()
            print(f"Error seeding books_master: {e}")
    else:
        print(f"Warning: {csv_path} not found.")

    # --- 2. Seed from models/book_catalog.csv (OpenLibrary, 6,120 rows) ---
    catalog_path = r"c:\Users\anshu\Documents\codes\ML\BookRecomendation\models\book_catalog.csv"
    if os.path.exists(catalog_path):
        print("Loading book_catalog.csv for recent/catalog books...")
        try:
            df = pd.read_csv(catalog_path)
            books_to_insert = []
            for _, row in df.iterrows():
                work_key = str(row['work_key']).strip()
                if not work_key or work_key in seen_ids:
                    continue
                seen_ids.add(work_key)
                
                title = str(row['title']).strip()
                author = str(row['author']).strip() if pd.notna(row['author']) else ""
                description = str(row['description']).strip() if pd.notna(row['description']) else ""
                genres = str(row['genres']).strip() if pd.notna(row['genres']) else ""
                
                # Image URL helper for OpenLibrary works (covers)
                # Since we don't have cover IDs directly, we use a neat placeholder or fallback
                image_url = f"https://covers.openlibrary.org/b/isbn/{work_key}-L.jpg" if not work_key.startswith("/works/") else ""
                
                books_to_insert.append({
                    "book_id": work_key,
                    "title": title,
                    "author": author,
                    "description": description,
                    "genres": genres,
                    "image_url": image_url,
                    "normalized_title": normalize_text(title),
                    "normalized_author": normalize_text(author)
                })
                
            if books_to_insert:
                db.bulk_insert_mappings(Book, books_to_insert)
                db.commit()
                print(f"Seeded {len(books_to_insert)} books from book_catalog.")
        except Exception as e:
            db.rollback()
            print(f"Error seeding book_catalog: {e}")
    else:
        print(f"Warning: {catalog_path} not found.")

    # --- 3. Seed from data/processed/master_catalog.csv (19,119 rows) ---
    master_cat_path = r"c:\Users\anshu\Documents\codes\ML\BookRecomendation\data\processed\master_catalog.csv"
    if os.path.exists(master_cat_path):
        print("Loading master_catalog.csv for additional recent books...")
        try:
            df = pd.read_csv(master_cat_path)
            books_to_insert = []
            for _, row in df.iterrows():
                work_key = str(row['work_key']).strip()
                if not work_key or work_key in seen_ids:
                    continue
                seen_ids.add(work_key)
                
                title = str(row['title']).strip()
                author = str(row['author']).strip() if pd.notna(row['author']) else ""
                genres = str(row['subject']).strip() if pd.notna(row['subject']) else ""
                
                books_to_insert.append({
                    "book_id": work_key,
                    "title": title,
                    "author": author,
                    "description": "",
                    "genres": genres,
                    "image_url": "",
                    "normalized_title": normalize_text(title),
                    "normalized_author": normalize_text(author)
                })
                
            if books_to_insert:
                db.bulk_insert_mappings(Book, books_to_insert)
                db.commit()
                print(f"Seeded {len(books_to_insert)} books from master_catalog.")
        except Exception as e:
            db.rollback()
            print(f"Error seeding master_catalog: {e}")
    else:
        print(f"Warning: {master_cat_path} not found.")
        
    final_count = db.query(Book).count()
    print(f"Database seeding completed successfully! Total books in DB: {final_count}")
    db.close()

if __name__ == "__main__":
    seed_database()
