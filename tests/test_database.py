import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base, User, Book, Rating, ShelfScan

# Use in-memory SQLite for fast testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    yield session
    session.close()

def test_user_creation_and_auth(db_session):
    user = User(email="reader@shelfsense.ai", password_hash="hashed_secret", name="Jane Austen")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == "reader@shelfsense.ai"
    assert user.name == "Jane Austen"

def test_book_catalog_and_rating(db_session):
    book = Book(
        book_id="0439139597",
        title="Harry Potter and the Goblet of Fire",
        author="J.K. Rowling",
        normalized_title="harry potter and the goblet of fire",
        normalized_author="j k rowling",
        genres="Fantasy, Young Adult"
    )
    db_session.add(book)
    db_session.commit()

    user = User(email="test@test.com", password_hash="hash", name="User")
    db_session.add(user)
    db_session.commit()

    rating = Rating(user_id=user.id, book_id=book.book_id, rating=5)
    db_session.add(rating)
    db_session.commit()

    fetched = db_session.query(Rating).filter_by(user_id=user.id).first()
    assert fetched is not None
    assert fetched.rating == 5
    assert fetched.book_id == "0439139597"

def test_shelf_scan_record(db_session):
    scan = ShelfScan(
        scan_id="scan_123",
        user_id=1,
        image_path="/uploads/original.jpg",
        annotated_image_path="/uploads/heatmap.jpg"
    )
    scan.set_detected_books([{"title": "Dune", "score": 90}])
    db_session.add(scan)
    db_session.commit()
    db_session.refresh(scan)

    assert scan.scan_id == "scan_123"
    assert len(scan.get_detected_books()) == 1
    assert scan.get_detected_books()[0]["title"] == "Dune"
