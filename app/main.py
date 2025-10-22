from fastapi import FastAPI, Depends, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List
from sentence_transformers import SentenceTransformer
from contextlib import asynccontextmanager
from fastmcp import FastMCP

from app import query, schema, llm, prompts
from app.database import get_db, SessionLocal

# --- Configuration ---
MODEL_NAME = "thenlper/gte-large"

# --- Global Model Cache ---
# We store the model in a dictionary to be loaded during app startup
model_cache = {}


# --- MCP Server Definition ---
mcp = FastMCP(
    title="Quranic Name Suggester",
    description="An MCP server for generating culturally and religiously appropriate Quranic name suggestions.",
)


@mcp.tool
def get_quranic_name_suggestions(query_text: str) -> List[schema.NameSuggestion]:
    """
    Given a user's query, performs a semantic search for relevant Quranic roots
    and uses a Large Language Model to generate valid, appropriate name suggestions.

    Args:
        query_text: The user's query (e.g., "a name that means strong and wise").

    Returns:
        A list of name suggestion objects.
    """
    db: Session = SessionLocal()
    try:
        # 1. Generate embedding for the query
        model = model_cache.get("sentence_transformer")
        if not model:
            raise HTTPException(status_code=503, detail="Embedding model is not loaded.")

        query_embedding = model.encode(query_text)

        # 2. Find similar words from the database
        search_results = query.get_similar_words(db, query_embedding, limit=5)
        if not search_results:
            return []

        # 3. Build the prompt for the LLM
        # Convert search results to a list of dicts for the prompt
        results_for_prompt = [
            {
                "sequence": r.sequence,
                "category": r.category,
                "english_text": r.occurrences[0].english_text if r.occurrences else "N/A",
            }
            for r in search_results
        ]
        user_prompt = prompts.build_prompt(query_text, results_for_prompt)

        # 4. Call the LLM to get suggestions
        llm_response = llm.call_llm_with_retry(prompts.SYSTEM_PROMPT, user_prompt)

        # 5. Parse and validate the response
        suggestions_data = llm_response.get("suggestions", [])
        validated_suggestions = [schema.NameSuggestion(**s) for s in suggestions_data]

        return validated_suggestions
    finally:
        db.close()


@mcp.tool
def find_quranic_roots_by_meaning(query_text: str) -> List[schema.RootInfo]:
    """
    Given a user's query, performs a semantic search for relevant Quranic roots
    and returns a list of the most relevant root words and their meanings.

    Args:
        query_text: The user's query (e.g., "a name that means strong and wise").

    Returns:
        A list of root information objects.
    """
    db: Session = SessionLocal()
    try:
        model = model_cache.get("sentence_transformer")
        if not model:
            # In a real MCP server, you might return an error object
            raise Exception("Embedding model is not loaded.")

        query_embedding = model.encode(query_text)
        search_results = query.get_similar_words(db, query_embedding, limit=5)

        if not search_results:
            return []

        # Convert the database results into a structured list of RootInfo objects
        root_info_list = [
            schema.RootInfo(
                sequence=r.sequence,
                category=r.category,
                english_text=r.occurrences[0].english_text if r.occurrences else "N/A",
            )
            for r in search_results
        ]
        return root_info_list
    finally:
        db.close()


@mcp.tool
def generate_names_from_roots(user_query: str, roots: List[schema.RootInfo]) -> List[schema.NameSuggestion]:
    """
    Given a list of Quranic roots, uses a Large Language Model to generate
    valid and appropriate name suggestions relevant to the user's original query.

    Args:
        user_query: The original user query to provide context.
        roots: A list of root information objects from the find_quranic_roots tool.

    Returns:
        A list of name suggestion objects.
    """
    if not roots:
        return []

    # Convert roots to a list of dicts for the prompt
    results_for_prompt = [root.model_dump() for root in roots]
    user_prompt = prompts.build_prompt(user_query, results_for_prompt)

    # Call the LLM to get suggestions
    llm_response = llm.call_llm_with_retry(prompts.SYSTEM_PROMPT, user_prompt)

    # Parse and validate the response
    suggestions_data = llm_response.get("suggestions", [])
    validated_suggestions = [schema.NameSuggestion(**s) for s in suggestions_data]

    return validated_suggestions


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

# Mount the MCP server on the FastAPI app
app.mount("/mcp", mcp)

# Allow frontend to connect (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    # 1. Generate embedding for the query
    query_embedding = model.encode(q)

    # 2. Find the most similar words and their sequences from the database
    search_results = query.get_similar_words(
        db,
        query_embedding=query_embedding,
        limit=limit,
        min_similarity=min_similarity
    )

    # No need for post-processing as the query module now handles grouping and sorting
    return search_results


@api_router.post("/chat", response_model=schema.ChatResponse)
async def chat_with_ai(
    request: schema.ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Main endpoint to get personalized Quranic name suggestions.
    This now orchestrates calls to our MCP tools.
    """
    session_token = request.session_token
    if not session_token:
        import uuid
        session_token = str(uuid.uuid4())

    # Orchestrate the MCP tools
    try:
        # Step 1: Find relevant roots
        roots = find_quranic_roots_by_meaning(request.query)
        # Step 2: Generate names from those roots
        suggestions = generate_names_from_roots(request.query, roots)

        return schema.ChatResponse(
            session_token=session_token,
            suggestions=suggestions
        )
    except Exception as e:
        # In a real app, you'd have more sophisticated error handling
        raise HTTPException(status_code=500, detail=str(e)) from e


# A root endpoint for health checks
@api_router.get("/")
def read_root():
    return {"status": "API is running"}

# Include API router and mount static files
app.include_router(api_router)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
