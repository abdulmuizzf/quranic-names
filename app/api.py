"""
This module defines the RESTful API endpoints for the application.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from app import query, schema
from app.database import get_db
from app.state import model_cache  # Import model_cache from the new state file
from app.tools import _find_quranic_roots_by_meaning, _generate_names_from_roots

# --- Create API Router ---
api_router = APIRouter(prefix="/api")


# --- API Endpoints ---

@api_router.get("/search", response_model=List[schema.SearchResult])
def search_words(
    q: str,
    limit: int = 10,
    min_similarity: float = 0,
    db: Session = Depends(get_db)
):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty.")

    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 50.")

    model = model_cache.get("sentence_transformer")
    if not model:
        raise HTTPException(status_code=503, detail="Model is not loaded yet. Please try again in a moment.")

    query_embedding = model.encode(q)
    search_results = query.get_similar_words(
        db,
        query_embedding=query_embedding,
        limit=limit,
        min_similarity=min_similarity
    )
    return search_results


@api_router.post("/chat", response_model=schema.ChatResponse)
async def chat_with_ai(
    request: schema.ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Main endpoint to get personalized Quranic name suggestions.
    This now orchestrates calls to our internal logic functions.
    """
    session_token = request.session_token
    if not session_token:
        import uuid
        session_token = str(uuid.uuid4())

    try:
        roots = _find_quranic_roots_by_meaning(request.query, db)
        suggestions = _generate_names_from_roots(request.query, roots)
        return schema.ChatResponse(
            session_token=session_token,
            suggestions=suggestions
        )
    except Exception as e:
        logging.exception("An error occurred in the chat endpoint.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/root-words", response_model=schema.AllRootWordsResponse)
def get_root_words(db: Session = Depends(get_db)):
    """
    Returns a complete list of all unique Quranic root words in the database.
    """
    try:
        all_roots = query.get_all_root_words(db)
        return schema.AllRootWordsResponse(root_words=all_roots)
    except Exception as e:
        logging.exception("An error occurred while fetching all root words.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.post("/generate-names", response_model=List[schema.NameSuggestion])
async def generate_names_from_roots_endpoint(
    request: schema.GenerateNamesRequest,
):
    """
    Generates name suggestions directly from a provided list of root words.
    """
    try:
        # Create a descriptive query for the LLM's context.
        context_query = (
            "Generate names from the following Quranic roots: " +
            ", ".join(f"{rw.sequence} ({rw.english_text})" for rw in request.root_words)
        )
        
        # The `_generate_names_from_roots` function expects `RootInfo` objects.
        # We can map our `RootWordInfo` objects to this, setting a default
        # score since it's not applicable here.
        root_infos = [
            schema.RootInfo(
                sequence=rw.sequence,
                category=rw.category,
                english_text=rw.english_text,
                best_match_score=0.0
            ) for rw in request.root_words
        ]

        suggestions = _generate_names_from_roots(context_query, root_infos)
        return suggestions
    except Exception as e:
        logging.exception("An error occurred during batch name generation.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/")
def read_root():
    return {"status": "API is running"}
