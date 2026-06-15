from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="BookVision API"
)

class RatedBook(BaseModel):
    title: str
    rating: int

class UserProfile(BaseModel):
    books: list[RatedBook]

@app.get("/")
def root():
    return {
        "status": "running"
    }

@app.post("/profile")
def create_profile(profile: UserProfile):

    return {
        "received": len(profile.books),
        "books": profile.books
    }