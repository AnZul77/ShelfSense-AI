import os
import sys

# Ensure repository root is always in sys.path for pytest
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Ensure database tables and basic test catalog exist for CI / clean clones
from backend.database import init_db, SessionLocal, Book

init_db()
db = SessionLocal()
try:
    if db.query(Book).count() == 0:
        seed_books = [
            Book(
                book_id="0439139597",
                title="Harry Potter and the Goblet of Fire",
                author="J.K. Rowling",
                description="Harry Potter's fourth year at Hogwarts School of Witchcraft and Wizardry.",
                genres="Fantasy, Magic, Young Adult",
                image_url="",
                normalized_title="harry potter and the goblet of fire",
                normalized_author="jk rowling"
            ),
            Book(
                book_id="0439136350",
                title="Harry Potter and the Prisoner of Azkaban",
                author="J.K. Rowling",
                description="Harry Potter's third year at Hogwarts.",
                genres="Fantasy, Magic",
                image_url="",
                normalized_title="harry potter and the prisoner of azkaban",
                normalized_author="jk rowling"
            ),
            Book(
                book_id="0395177111",
                title="The Hobbit",
                author="J.R.R. Tolkien",
                description="The journey of Bilbo Baggins to the Lonely Mountain.",
                genres="Fantasy, Adventure",
                image_url="",
                normalized_title="the hobbit",
                normalized_author="jrr tolkien"
            )
        ]
        db.add_all(seed_books)
        db.commit()
except Exception:
    db.rollback()
finally:
    db.close()
