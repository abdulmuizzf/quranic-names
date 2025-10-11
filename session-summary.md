### **Project Goal**

To build and maintain a sophisticated semantic search application that finds Quranic root words based on the semantic meaning of an English query.

### **Current Architecture & Features**

**1. Backend API (FastAPI)**

*   **Endpoint:** `/api/search`
*   **Parameters:** `q` (query), `limit` (results count), `min_similarity` (filter threshold).
*   **Core Logic:** Uses the `thenlper/gte-large` sentence transformer model to generate a vector embedding from the English query.

**2. Database & Search (PostgreSQL with `pgvector`)**

*   **Schema:** The database stores pre-computed embeddings for individual Quranic word occurrences, linked to root words (sequences), categories, and letters.
*   **Search Method:** The primary search query is built using the **SQLAlchemy ORM** and `pgvector`'s native `.cosine_distance()` function for safe and efficient vector similarity search. This is the standard implementation and should be the reference for any future database work.

**3. Search Results Structure**

*   The API groups results by the root word "sequence."
*   Each sequence includes a `best_match_score` (the highest similarity of any word in that group).
*   Each sequence contains a list of individual `occurrences`, with each word having its own `similarity_score`.

**4. Frontend (HTML, CSS, JavaScript)**

*   **UI:** A clean interface for entering a search query and setting the result limit and minimum similarity percentage.
*   **Filtering:** The "Minimum Match %" filter is handled by the backend via an API parameter.
*   **Display:**
    *   Results are shown in dynamically loaded cards, one for each root word.
    *   Each card contains a table of individual word occurrences.
    *   Match percentages are color-coded for readability.
    *   Verse reference links correctly point to the specific verse on `corpus.quran.com`.
