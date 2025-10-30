# Implementation Plan: LLM-Powered Quranic Name Suggester

**Directive:** Do not proceed with any step in this plan until explicitly instructed to do so.

This document outlines the step-by-step process for implementing the architecture defined in `app/claude-arch-plan.md`.

---

### **Phase 1: Foundational Setup & Database Migration (COMPLETE)**

**Goal:** Prepare the database schema to support all new features, including name suggestions, caching, user sessions, and detailed, categorized user preferences.

**Status:** This phase is complete. All database models have been created and the migration has been successfully applied.

---

### **Phase 2: Core Backend Logic & LLM Integration (COMPLETE)**

**Goal:** Build the API endpoint and core logic for generating name suggestions, without personalization.

**Status:** This phase is complete. The backend is fully functional and exposes both a RESTful API and an MCP server.

#### **Architectural Overview & Code Snippets**

The backend is built on a modular architecture that separates concerns into distinct files, preventing issues like circular imports and improving maintainability.

**1. `app/state.py`: Shared Application State**

This file holds shared, in-memory objects like the sentence transformer model cache. Centralizing the cache in this way allows other modules to access it without creating circular dependencies.

**2. `app/tools.py`: MCP Server and Core Logic**

This module contains the `FastMCP` server and the core business logic of the application.

*   **`_find_quranic_roots_by_meaning`:** The internal function that takes a user query and performs a vector search.
*   **`_generate_names_from_roots`:** The internal function that takes the results of the search and calls the Gemini LLM to generate name suggestions.
*   **MCP Tools:** The module also defines the `@mcp.tool`-decorated functions that wrap the internal logic, exposing it to the MCP server.

**3. `app/api.py`: RESTful API Endpoints**

This module contains the FastAPI `APIRouter` and all the user-facing REST endpoints.

*   **`/api/search`:** The original endpoint for direct vector searches.
*   **`/api/chat`:** This endpoint orchestrates the name suggestion process by calling the internal logic functions from `app/tools.py`.

    ```python
    # Example from app/api.py
    @api_router.post("/chat", response_model=schema.ChatResponse)
    async def chat_with_ai(request: schema.ChatRequest, db: Session = Depends(get_db)):
        # Step 1: Find relevant roots
        roots = _find_quranic_roots_by_meaning(request.query, db)
        # Step 2: Generate names from those roots
        suggestions = _generate_names_from_roots(request.query, roots)
        # ...
    ```

**4. `app/main.py`: Application Entry Point**

This file is now a clean entry point responsible only for assembling the application. It creates the main `FastAPI` app, includes the router from `app/api.py`, and mounts the MCP server from `app/tools.py`.

**5. `app/llm.py`: The LLM Service**

This module is responsible for all communication with the Gemini 2.5 Pro API.

*   **`call_llm_with_retry`:** This is the primary function. It takes the system and user prompts, handles API key configuration, and implements an exponential backoff retry mechanism to ensure resilience.

    ```python
    # Example from app/llm.py
    def call_llm_with_retry(...):
        model = genai.GenerativeModel(
            model_name='gemini-2.5-pro',
            system_instruction=system_prompt
        )
        # ... retry logic ...
        response = model.generate_content(user_prompt)
        return json.loads(response.text)
    ```

**6. `app/prompts.py`: Prompt Engineering**

This module contains the templates and logic for constructing the prompts sent to the LLM.

*   **`SYSTEM_PROMPT`:** A constant that contains the critical, high-level instructions and rules for the LLM (e.g., "VALID DERIVATIONS ONLY", "NO FORBIDDEN NAMES", "FORMATTING").
*   **`build_prompt`:** A function that takes the user's query and the search results and formats them into the final user-facing prompt.

---

### **Phase 3: Frontend Chat Interface (COMPLETE)**

**Goal:** Develop the user-facing chat interface.

**Status:** This phase is complete. The frontend has been built with a tabbed interface to accommodate both the original semantic search and the new AI-powered chat. The chat UI is fully functional, calling the `/api/chat` endpoint and rendering the returned name suggestions in individual, styled cards.

---

### **New Feature: Batch Name Generation (COMPLETE)**

**Goal:** Allow users to generate names from all Quranic root words without a semantic search.

**Status:** This feature is complete.

1.  **Backend Endpoint (`app/api.py`):**
    *   A new GET endpoint, `/api/root-words`, was created, with pagination support.
    *   The endpoint was updated to filter out grammatical categories.
    *   A new POST endpoint, `/api/generate-names`, was created to handle batch generation requests.
    *   The backend now returns a list of unsuccessful roots from the LLM.

2.  **Frontend Implementation (`static/`):**
    *   A new "Batch Generate" tab was added to the UI.
    *   The frontend now fetches root words in pages and handles the batch generation process with pause/resume functionality.
    *   The UI now displays unsuccessful roots.
    *   Copy buttons for both successful and unsuccessful results have been added.

3.  **Developer Tools:**
    *   A script, `get_categories.py`, was created to query and analyze database categories.

4.  **Prompt Engineering:**
    *   The system prompt was updated to request unsuccessful roots and use Arabic script for examples.

---

### **Phase 4: Advanced Personalization & Feedback Loop**

**Goal:** Implement the full personalization engine based on user feedback.

1.  **Implement Preference Endpoint (`app/main.py`):**
    *   Create a new POST endpoint: `/api/preferences`.
    *   This endpoint will receive a `suggestion_id`, a `score` (e.g., 1.0 for like, -1.0 for dislike), and an optional `reason_text`.

2.  **Develop Reason Categorization Logic:**
    *   When a preference with a `reason_text` is submitted, send a request to the LLM with a specialized prompt: *"Categorize the following reason for liking/disliking a name into one of these existing categories, or create a new one if none fit: [list of categories]. Reason: '{reason_text}'. Respond with the category name only."*
    *   Implement logic to either retrieve or create a `PreferenceReasonCategory` in the database based on the LLM's response.
    *   Store the user's preference with the associated category.

3.  **Integrate Personalization into Chat Flow:**
    *   Implement the `get_user_preferences` function to retrieve all liked/disliked suggestion vectors for a session.
    *   Implement the `get_boosted_query_vector` function to modify the search vector based on user preferences.
    *   Implement the `rerank_suggestions` function to sort the LLM's output based on similarity to the user's liked vectors.
    *   Update the `/api/chat` endpoint to use these new functions.

4.  **Enhance Frontend with Feedback UI:**
    *   Add "Like" and "Dislike" buttons to the name cards.
    *   When a user clicks a button, prompt them for an optional reason.
    *   Send the preference data to the `/api/preferences` endpoint.
    *   Update the UI to reflect the user's choice (e.g., highlight the liked card).

5.  **Implement Post-Processing and Fallbacks:**
    *   In a new file `app/validation.py`, create the `validate_llm_suggestions` function with all the required safety checks (forbidden names, gender markers, etc.).
    *   Implement the `fallback_response` function in `app/main.py` to handle LLM failures gracefully.

6.  **Integrate Programmatic Morphological Validation:**
    *   Add `camel-tools` to the `requirements.txt` file.
    *   In `app/validation.py`, create a new function `is_morphologically_valid(name: str, root: str) -> bool`.
    *   This function will use `camel-tools`'s `Analyzer` to programmatically verify that the suggested `name` is a valid morphological derivation of the `root`.
    *   Update the main chat endpoint logic to call this function for each suggestion from the LLM and filter out any that fail validation.

---

### **Phase 5: Caching, Monitoring, and Iteration**

**Goal:** Optimize performance and cost, and build tools for continuous improvement.

1.  **Implement Caching Layer:**
    *   Create the `QueryCache` database model (already done in Phase 1).
    *   Implement the `check_query_cache` and `cache_response` functions.
    *   Integrate caching into the `/api/chat` endpoint as the first step.

2.  **Build Reporting and Admin Tools:**
    *   Implement the `/api/report-suggestion` endpoint.
    *   Create the `SuggestionReport` model and apply the migration.
    *   Build a simple, protected admin endpoint (`/api/admin/reported-suggestions`) to review reported names.

3.  **Set Up A/B Testing Framework:**
    *   Create the `PromptVersion` model and apply the migration.
    *   Implement the `get_active_prompt` function to allow for testing different prompt versions.
    *   Log which prompt version is used for each request to analyze performance.
