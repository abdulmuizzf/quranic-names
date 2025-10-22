from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sentence_transformers import SentenceTransformer
from contextlib import asynccontextmanager

from app.api import api_router
from app.tools import mcp
from app.state import model_cache

# --- Configuration ---
MODEL_NAME = "thenlper/gte-large"

# --- Global Model Cache ---
# This is now imported from app.state, but the lifespan function will populate it.


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
    title="Quranic Name Suggester API",
    description="An API and MCP server for Quranic name suggestions.",
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

# Include API router and mount static files
app.include_router(api_router)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
