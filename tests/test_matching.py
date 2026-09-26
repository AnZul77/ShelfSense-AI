import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base, Book
from src.matching import match_book_entity, normalize_text, extract_meaningful_keywords

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    # Seed test books
    b1 = Book(
        book_id="9780765326355",
        title="The Way of Kings",
        author="Brandon Sanderson",
        normalized_title="the way of kings",
        normalized_author="brandon sanderson"
    )
    b2 = Book(
        book_id="9780061120084",
        title="To Kill a Mockingbird",
        author="Harper Lee",
        normalized_title="to kill a mockingbird",
        normalized_author="harper lee"
    )
    b3 = Book(
        book_id="9780679720201",
        title="Flu: The Story of the Great Influenza Pandemic of 1918 and the Search for the Virus That Caused It",
        author="Gina Kolata",
        normalized_title="flu the story of the great influenza pandemic of 1918 and the search for the virus that caused it",
        normalized_author="gina kolata"
    )
    session.add_all([b1, b2, b3])
    session.commit()

    yield session
    session.close()

def test_string_normalization():
    assert normalize_text("The WAY of Kings!!") == "the way of kings"
    assert normalize_text("  J.K. Rowling... ") == "jk rowling"

def test_extract_meaningful_keywords():
    kws = extract_meaningful_keywords("The Way of Kings by Brandon Sanderson")
    assert "kings" in kws
    assert "brandon" in kws
    assert "sanderson" in kws
    assert "the" not in kws
    assert "of" not in kws
    assert "by" not in kws

def test_exact_title_match(db_session):
    res = match_book_entity(title="The Way of Kings", author="Brandon Sanderson", db=db_session)
    assert res is not None
    assert res["book"].book_id == "9780765326355"
    assert res["score"] >= 95.0

def test_flu_pandemic_trap_eliminated(db_session):
    # A short generic fantasy query should NEVER match the 100-character Flu pandemic book!
    res = match_book_entity(raw_query="The Great Hero", db=db_session, fuzzy_threshold=80.0)
    if res:
        assert res["book"].title != "Flu: The Story of the Great Influenza Pandemic of 1918 and the Search for the Virus That Caused It"

def test_fuzzy_ocr_query_matching(db_session):
    # OCR noisy text with extra characters
    res = match_book_entity(raw_query="SANDERSON WAY OF KINGS", db=db_session, fuzzy_threshold=70.0)
    assert res is not None
    assert res["book"].title == "The Way of Kings"
