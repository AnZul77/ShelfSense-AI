"""
Seed Modern Bestsellers from OpenLibrary Search API.

This script fetches works by ~60 popular modern authors across all genres
and inserts them into the local SQLite database. It covers contemporary fiction,
romance, thriller, literary fiction, non-fiction, YA, fantasy, sci-fi, and more.

Usage:
    python backend/seed_modern_books.py
"""
import os
import sys
import re
import time
import requests
import json

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, SessionLocal, Book

# OpenLibrary Search API base URL
OL_SEARCH_URL = "https://openlibrary.org/search.json"
OL_AUTHOR_WORKS_URL = "https://openlibrary.org/search.json"

def normalize_text(text):
    if not text or not isinstance(text, str):
        return ""
    return re.sub(r"[^a-z0-9\s]", "", text.lower()).strip()

# Comprehensive list of popular modern authors across ALL genres
MODERN_AUTHORS = [
    # Contemporary Fiction / Literary Fiction
    "Emily Henry",
    "Colleen Hoover",
    "Taylor Jenkins Reid",
    "Sally Rooney",
    "Matt Haig",
    "Fredrik Backman",
    "Dolly Alderton",
    "Gabrielle Zevin",
    "Amor Towles",
    "Celeste Ng",
    "Brit Bennett",
    "Kiley Reid",
    "Delia Owens",
    "Bonnie Garmus",
    "Madeline Miller",
    "Hanya Yanagihara",
    "Ocean Vuong",
    "Ottessa Moshfegh",
    "Rachel Cusk",
    "Douglas Stuart",
    
    # Romance / Romantic Comedy
    "Ali Hazelwood",
    "Casey McQuiston",
    "Christina Lauren",
    "Talia Hibbert",
    "Jasmine Guillory",
    "Helen Hoang",
    "Abby Jimenez",
    "Tessa Bailey",
    "Lucy Score",
    "Ana Huang",
    "Sophie Kinsella",
    "Marian Keyes",
    "Jojo Moyes",
    "Nicholas Sparks",
    "Beth O'Leary",
    
    # Thriller / Mystery / Suspense
    "Ruth Ware",
    "Liane Moriarty",
    "Lisa Jewell",
    "Freida McFadden",
    "Lucy Foley",
    "Riley Sager",
    "Alex Michaelides",
    "Karin Slaughter",
    "Tana French",
    "Paula Hawkins",
    "Gillian Flynn",
    "A.J. Finn",
    "Harlan Coben",
    "Shari Lapena",
    
    # Horror / Dark Fiction
    "Stephen King",
    "Paul Tremblay",
    "Grady Hendrix",
    "Silvia Moreno-Garcia",
    
    # Fantasy / Sci-Fi
    "Brandon Sanderson",
    "V.E. Schwab",
    "Leigh Bardugo",
    "Rebecca Yarros",
    "Sarah J. Maas",
    "N.K. Jemisin",
    "Andy Weir",
    "Blake Crouch",
    "Cixin Liu",
    "Becky Chambers",
    "T.J. Klune",
    "Travis Baldree",
    "R.F. Kuang",
    "Samantha Shannon",
    "Holly Black",
    
    # Non-Fiction / Memoir / Self-Help
    "James Clear",
    "Brené Brown",
    "Michelle Obama",
    "Matthew McConaughey",
    "Jennette McCurdy",
    "Glennon Doyle",
    "Mark Manson",
    "Adam Grant",
    "Malcolm Gladwell",
    "Yuval Noah Harari",
    "Ta-Nehisi Coates",
    "Educated Tara Westover",
    "Roxane Gay",
    
    # YA / Young Adult
    "Angie Thomas",
    "Adam Silvera",
    "Becky Albertalli",
    "Jenny Han",
    "Nicola Yoon",
    
    # Literary Classics / Evergreen
    "Khaled Hosseini",
    "Chimamanda Ngozi Adichie",
    "Kazuo Ishiguro",
    "Haruki Murakami",
    "Elena Ferrante",
    
    # Additional Popular Contemporary
    "Kevin Kwan",
    "Lev Grossman",
    "Mariana Enriquez",
    "Naomi Alderman",
    "Emma Gannon",
    "Caterina Bonvicini",
    "Nancy Mitford",
    "Stephanie Danler",
    "Katie Cotugno",
    "Marisha Pessl",
]


def fetch_author_books(author_name, max_books=30):
    """Fetch books by a single author from OpenLibrary Search API."""
    books = []
    
    try:
        params = {
            "author": author_name,
            "sort": "rating",
            "limit": max_books,
            "fields": "key,title,author_name,first_publish_year,subject,cover_i,number_of_pages_median,ratings_average",
        }
        
        resp = requests.get(OL_SEARCH_URL, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"  API error for {author_name}: HTTP {resp.status_code}")
            return books
            
        data = resp.json()
        docs = data.get("docs", [])
        
        for doc in docs:
            title = doc.get("title", "").strip()
            if not title:
                continue
                
            authors = doc.get("author_name", [])
            author = authors[0] if authors else author_name
            
            work_key = doc.get("key", "")
            year = doc.get("first_publish_year", None)
            
            # Build genres/subjects from OpenLibrary subjects
            subjects = doc.get("subject", [])
            # Take top 5 relevant subjects, filter out overly generic ones
            filtered_subjects = []
            generic = {"fiction", "literature", "in library", "accessible book", 
                       "protected daisy", "lending library", "large type books",
                       "english language", "english fiction", "american fiction",
                       "reading level", "overdrive"}
            for s in subjects[:20]:
                s_lower = s.lower().strip()
                if s_lower not in generic and len(s_lower) > 2 and len(s_lower) < 40:
                    filtered_subjects.append(s.strip())
                if len(filtered_subjects) >= 5:
                    break
            genres = "|".join(filtered_subjects)
            
            # Cover image URL
            cover_id = doc.get("cover_i")
            image_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else ""
            
            books.append({
                "work_key": work_key,
                "title": title,
                "author": author,
                "description": "",
                "genres": genres,
                "image_url": image_url,
                "year": year,
            })
            
    except requests.exceptions.Timeout:
        print(f"  Timeout fetching {author_name}")
    except Exception as e:
        print(f"  Error fetching {author_name}: {e}")
        
    return books


def seed_modern_books():
    """Main seeding function that fetches modern books and inserts into the database."""
    print("=" * 60)
    print("SEEDING MODERN BESTSELLERS FROM OPENLIBRARY")
    print("=" * 60)
    
    init_db()
    db = SessionLocal()
    
    # Get existing book IDs to avoid duplicates
    existing_ids = set()
    existing_titles_authors = set()
    
    all_books = db.query(Book.book_id, Book.normalized_title, Book.normalized_author).all()
    for book_id, norm_title, norm_author in all_books:
        existing_ids.add(book_id)
        existing_titles_authors.add((norm_title or "", norm_author or ""))
    
    print(f"Existing books in database: {len(existing_ids)}")
    
    total_inserted = 0
    total_skipped = 0
    
    for i, author in enumerate(MODERN_AUTHORS):
        print(f"\n[{i+1}/{len(MODERN_AUTHORS)}] Fetching books by: {author}")
        
        books = fetch_author_books(author, max_books=30)
        author_inserted = 0
        
        for book_data in books:
            work_key = book_data["work_key"]
            title = book_data["title"]
            author_name = book_data["author"]
            
            norm_title = normalize_text(title)
            norm_author = normalize_text(author_name)
            
            # Skip if work_key already exists
            if work_key in existing_ids:
                total_skipped += 1
                continue
                
            # Skip if normalized title+author already exists (avoid dupes with different keys)
            if (norm_title, norm_author) in existing_titles_authors:
                total_skipped += 1
                continue
            
            try:
                new_book = Book(
                    book_id=work_key,
                    title=title,
                    author=author_name,
                    description=book_data["description"],
                    genres=book_data["genres"],
                    image_url=book_data["image_url"],
                    normalized_title=norm_title,
                    normalized_author=norm_author,
                )
                db.add(new_book)
                existing_ids.add(work_key)
                existing_titles_authors.add((norm_title, norm_author))
                author_inserted += 1
                total_inserted += 1
            except Exception as e:
                db.rollback()
                print(f"  Insert error for '{title}': {e}")
                continue
        
        # Commit after each author batch
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"  Commit error for batch '{author}': {e}")
            
        print(f"  Found {len(books)} works, inserted {author_inserted} new books")
        
        # Respect API rate limits (be nice to OpenLibrary)
        time.sleep(0.5)
    
    final_count = db.query(Book).count()
    db.close()
    
    print("\n" + "=" * 60)
    print(f"SEEDING COMPLETE!")
    print(f"  New books inserted: {total_inserted}")
    print(f"  Duplicates skipped: {total_skipped}")
    print(f"  Total books in DB:  {final_count}")
    print("=" * 60)
    
    return total_inserted


if __name__ == "__main__":
    seed_modern_books()
