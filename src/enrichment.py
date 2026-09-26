import re
import requests
from sqlalchemy.orm import Session
from backend.database import Book

def fetch_openlibrary_metadata(title: str, author: str = None) -> dict:
    """
    Query OpenLibrary Search & Works API to retrieve official synopsis,
    cover image, genres/subjects, and publication year.
    Returns: dict with title, author, description, genres, image_url.
    """
    if not title or len(title.strip()) < 2:
        return {}

    # Clean publication edition tags and subtitles for high-recall search
    clean_title = re.sub(r"\(.*?\)|\[.*?\]", "", title).strip()
    if ":" in clean_title:
        clean_title = clean_title.split(":")[0].strip()

    clean_author = re.sub(r"\s+", " ", author.replace(".", " ")).strip() if author else ""
    query = f"{clean_title} {clean_author}".strip()
    search_url = "https://openlibrary.org/search.json"

    try:
        res = requests.get(search_url, params={"q": query, "limit": 1}, timeout=4.0)
        if res.status_code != 200:
            return {}

        data = res.json()
        docs = data.get("docs", [])
        if not docs:
            return {}

        doc = docs[0]
        meta = {
            "title": doc.get("title", title),
            "author": doc.get("author_name", [author])[0] if doc.get("author_name") else author,
            "year": doc.get("first_publish_year"),
            "cover_url": "",
            "genres": "",
            "description": ""
        }

        # Cover image
        cover_id = doc.get("cover_i")
        if cover_id:
            meta["cover_url"] = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"

        # Genres from subjects
        subjects = doc.get("subject", [])
        clean_subjects = []
        for s in subjects[:8]:
            if not s.startswith("nyt:") and len(s) < 30:
                clean_subjects.append(s.capitalize())
        if clean_subjects:
            meta["genres"] = ", ".join(clean_subjects[:4])

        # Work key for full description
        work_key = doc.get("key")
        if work_key:
            try:
                w_res = requests.get(f"https://openlibrary.org{work_key}.json", timeout=3.5)
                if w_res.status_code == 200:
                    w_data = w_res.json()
                    desc = w_data.get("description", "")
                    if isinstance(desc, dict):
                        desc = desc.get("value", "")
                    if desc and isinstance(desc, str):
                        meta["description"] = desc.strip()
                    
                    # Complement subjects if empty
                    if not meta["genres"] and w_data.get("subjects"):
                        w_subs = [s.capitalize() for s in w_data.get("subjects") if len(s) < 30]
                        meta["genres"] = ", ".join(w_subs[:4])
            except Exception:
                pass

        return meta

    except Exception as e:
        # Graceful timeout or offline fallback
        return {}

def enrich_book_in_db(book: Book, db: Session) -> bool:
    """
    Enrich a book record in SQLite if it lacks description or cover image.
    Persists changes and returns True if enriched.
    """
    if not book:
        return False

    needs_enrichment = not book.description or not book.genres or not book.image_url
    if not needs_enrichment:
        return False

    meta = fetch_openlibrary_metadata(book.title, book.author)
    if not meta:
        return False

    changed = False
    if not book.description and meta.get("description"):
        book.description = meta["description"]
        changed = True

    if not book.genres and meta.get("genres"):
        book.genres = meta["genres"]
        changed = True

    if not book.image_url and meta.get("cover_url"):
        book.image_url = meta["cover_url"]
        changed = True

    if changed:
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

    return False
