# Implementation Plan: LLM-Powered Quranic Name Suggester

**Directive:** Do not proceed with any step in this plan until explicitly instructed to do so.

This document outlines the step-by-step process for implementing the architecture defined in `app/claude-arch-plan.md`.

---

### **Phase 1: Foundational Setup & Database Migration**

**Goal:** Prepare the database schema to support all new features, including name suggestions, caching, user sessions, and detailed, categorized user preferences.

1.  **Update Database Models (`app/models.py`):**
    *   Add the `NameSuggestion` model.
    *   Add the `QueryCache` model.
    *   Add the `UserSession` model.
    *   Add the `PreferenceReasonCategory` model.
    *   Add the `UserPreference` model, ensuring it includes the `preference_score` (Float) and the relationship to `PreferenceReasonCategory`.

2.  **Generate Database Migration:**
    *   Run the command: `alembic revision --autogenerate -m "Add tables for name suggestions, caching, and user preferences"`
    *   Review the generated migration script in `migrations/versions/` to ensure it correctly creates all new tables and relationships.

3.  **Apply Database Migration:**
    *   Run the command: `alembic upgrade head`
    *   Verify in the database that the new tables (`name_suggestions`, `query_cache`, `user_sessions`, `preference_reason_categories`, `user_preferences`) have been created successfully.

---

### **Phase 2: Core Backend Logic & LLM Integration**

**Goal:** Build the API endpoint and core logic for generating name suggestions, without personalization.

1.  **Create Chat Endpoint (`app/main.py`):**
    *   Create a new POST endpoint: `/api/chat`.
    *   Define the request and response Pydantic models (`ChatRequest`, `ChatResponse`).
    *   Implement the basic flow: receive a query, perform a vector search, and prepare for the LLM call.

2.  **Implement Prompt Engineering (`app/prompts.py`):**
    *   Create a new file `app/prompts.py` to store the `SYSTEM_PROMPT` and the `build_prompt` function.
    *   Ensure the prompt is detailed and follows the safety-first principles from the architecture plan.

3.  **Integrate LLM Service (`app/llm.py`):**
    *   Create a new file `app/llm.py` to house the `call_llm_with_retry` function.
    *   Use an environment variable for the LLM API key.
    *   Implement the retry logic with exponential backoff.

---

### **Phase 3: Frontend Chat Interface**

**Goal:** Develop the user-facing chat interface.

1.  **Build Basic Chat UI (`static/index.html` & `static/style.css`):**
    *   Create the HTML structure for a chat window, message display area, and input form.
    *   Style the components to be clean and user-friendly.

2.  **Implement Frontend Logic (`static/script.js`):**
    *   Write JavaScript to handle sending user messages to the `/api/chat` endpoint.
    *   Implement logic to display user messages and AI responses in the chat window.
    *   Create the `createNameCard` function to render name suggestions dynamically.

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
