"""
This module defines the MCP (Model Context Protocol) server and its tools.
It encapsulates the core business logic of the application.
"""

from typing import List
from sqlalchemy.orm import Session
from fastmcp import FastMCP

from app import query, schema, llm, prompts
from app.database import SessionLocal
from app.state import model_cache  # Import model_cache from the new state file

# --- MCP Server Definition ---
mcp = FastMCP("Quranic Name Suggester")


# --- Internal Business Logic ---

def _find_quranic_roots_by_meaning(query_text: str, db: Session) -> List[schema.RootInfo]:
    """Internal logic to find Quranic roots by semantic meaning."""
    model = model_cache.get("sentence_transformer")
    if not model:
        raise Exception("Embedding model is not loaded.")

    query_embedding = model.encode(query_text)
    search_results = query.get_similar_words(db, query_embedding, limit=20)

    if not search_results:
        return []

    print(f"Found {len(search_results)} similar roots for query '{query_text}'.")
    print(f"First result details: {search_results[0]}")
    # The query returns a list of dicts, so we access items by key
    root_info_list = [
        schema.RootInfo(
            sequence=r['sequence'],
            category=r['category'],
            english_text=r['occurrences'][0]['english_text'] if r['occurrences'] else "N/A",
            best_match_score=r['best_match_score']
        )
        for r in search_results
    ]
    return root_info_list


def _generate_names_from_roots(user_query: str, roots: List[schema.RootInfo]) -> List[schema.NameSuggestion]:
    """Internal logic to generate name suggestions from roots using an LLM."""
    if not roots:
        return []

    results_for_prompt = [root.model_dump() for root in roots]
    user_prompt = prompts.build_prompt(user_query, results_for_prompt)

    llm_response = llm.call_llm_with_retry(prompts.SYSTEM_PROMPT, user_prompt)

    suggestions_data = llm_response.get("suggestions", [])
    validated_suggestions = [schema.NameSuggestion(**s) for s in suggestions_data]
    return validated_suggestions


# --- MCP Tool Definitions ---

@mcp.tool
def find_quranic_roots_by_meaning(query_text: str) -> List[schema.RootInfo]:
    """
    Given a user's query, performs a semantic search for relevant Quranic roots
    and returns a list of the most relevant root words and their meanings.
    """
    db: Session = SessionLocal()
    try:
        return _find_quranic_roots_by_meaning(query_text, db)
    finally:
        db.close()


@mcp.tool
def generate_names_from_roots(user_query: str, roots: List[schema.RootInfo]) -> List[schema.NameSuggestion]:
    """
    Given a list of Quranic roots, uses a Large Language Model to generate
    valid and appropriate name suggestions relevant to the user's original query.
    """
    return _generate_names_from_roots(user_query, roots)
