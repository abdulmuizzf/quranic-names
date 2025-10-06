from fastapi import FastAPI, Depends, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List
from sentence_transformers import SentenceTransformer
from contextlib import asynccontextmanager

from app import query, schema
from app.database import get_db

# --- Configuration ---
MODEL_NAME = "thenlper/gte-large"

# --- Global Model Cache ---
# We store the model in a dictionary to be loaded during app startup
model_cache = {}


# --- FastAPI Lifespan Management (for loading the model) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the model on startup
    print(f"Loading sentence transformer model '{MODEL_NAME}'...")
    model_cache["sentence_transformer"] = SentenceTransformer(MODEL_NAME)
    print("✅ Model loaded successfully.")
    yield
    # Clean up on shutdown
    model_cache.clear()


# --- FastAPI App Initialization ---
app = FastAPI(
    title="Quranic Root Word Semantic Search",
    description="An API to find Quranic root words based on semantic meaning.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow frontend to connect (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Create API Router ---
from fastapi import APIRouter
api_router = APIRouter(prefix="/api")

# --- API Endpoints ---
@api_router.get("/search", response_model=List[schema.SearchResult])
def search_words(q: str, db: Session = Depends(get_db)):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty.")

    model = model_cache.get("sentence_transformer")
    if not model:
        raise HTTPException(status_code=503, detail="Model is not loaded yet. Please try again in a moment.")

    # 1. Generate embedding for the query
    query_embedding = model.encode(q)

    # 2. Find the most similar words from the database
    similar_words = query.get_similar_words(db, query_embedding=query_embedding, limit=10)

    # 3. Post-process to get unique sequences and format the output
    unique_sequences = {}
    for word in similar_words:
        # If we haven't seen this sequence before, add it to our results
        if word.sequence not in unique_sequences:
            unique_sequences[word.sequence] = schema.SearchResult(
                sequence=word.sequence, category=word.category, letter=word.letter, sample_meaning=word.english_text
            )

    return list(unique_sequences.values())


# A root endpoint for health checks
@api_router.get("/")
def read_root():
    return {"status": "API is running"}

# Include API router and mount static files
app.include_router(api_router)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
