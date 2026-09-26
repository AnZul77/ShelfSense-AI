import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_api_health():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["status"] == "running"

def test_catalog_search():
    res = client.get("/books?q=Harry&limit=5")
    assert res.status_code == 200
    books = res.json()
    assert isinstance(books, list)
    assert len(books) > 0
    assert "title" in books[0]
    assert "book_id" in books[0]

def test_auth_and_user_profile():
    import uuid
    random_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    
    # 1. Register
    reg_res = client.post("/auth/register", json={
        "email": random_email,
        "password": "Password123!",
        "name": "Test Runner"
    })
    assert reg_res.status_code == 200
    token = reg_res.json()["token"]

    # 2. Get User Profile with JWT via /profile
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/profile", headers=headers)
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data["email"] == random_email
    assert user_data["name"] == "Test Runner"

def test_get_nonexistent_scan_unauthorized():
    res = client.get("/scan/999999")
    assert res.status_code == 401

def test_get_nonexistent_scan_authorized():
    import uuid
    random_email = f"scan_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = client.post("/auth/register", json={
        "email": random_email,
        "password": "Password123!",
        "name": "Scanner"
    })
    token = reg_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/scan/nonexistent_scan_id", headers=headers)
    assert res.status_code == 404

def test_jwt_token_structure():
    import uuid
    random_email = f"jwt_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = client.post("/auth/register", json={
        "email": random_email,
        "password": "Password123!",
        "name": "JWT User"
    })
    assert reg_res.status_code == 200
    token = reg_res.json()["token"]
    # Cryptographic JWT has 3 parts: header.payload.signature
    parts = token.split(".")
    assert len(parts) == 3
