# Quranic Name Finder - Complete Architecture Plan

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Single Page Application (SPA)               │   │
│  │                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │ Search UI    │  │  Chat UI     │  │ Results UI   │  │   │
│  │  │              │  │              │  │              │  │   │
│  │  │ - Input      │  │ - Messages   │  │ - Name Cards │  │   │
│  │  │ - Filters    │  │ - Input Box  │  │ - Root Words │  │   │
│  │  │              │  │ - History    │  │ - Preferences│  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │   │
│  │                                                          │   │
│  │              HTML + CSS + Vanilla JavaScript            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS / REST API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  FastAPI Application                     │   │
│  │                                                          │   │
│  │  ┌────────────────────────────────────────────────────┐ │   │
│  │  │              API Endpoints                         │ │   │
│  │  │                                                    │ │   │
│  │  │  /api/search          (existing)                  │ │   │
│  │  │  /api/chat            (new)                       │ │   │
│  │  │  /api/generate-names  (new)                       │ │   │
│  │  │  /api/preferences     (new)                       │ │   │
│  │  │  /api/suggestions     (new)                       │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  │                                                          │   │
│  │  ┌────────────────────────────────────────────────────┐ │   │
│  │  │              Business Logic Layer                  │ │   │
│  │  │                                                    │ │   │
│  │  │  ┌──────────────┐  ┌──────────────┐             │ │   │
│  │  │  │ query.py     │  │ llm_service  │             │ │   │
│  │  │  │              │  │              │             │ │   │
│  │  │  │ - Vector     │  │ - Name Gen   │             │ │   │
│  │  │  │   Search     │  │ - Prompt     │             │ │   │
│  │  │  │ - Similarity │  │ - Parse      │             │ │   │
│  │  │  └──────────────┘  └──────────────┘             │ │   │
│  │  │                                                    │ │   │
│  │  │  ┌──────────────┐  ┌──────────────┐             │ │   │
│  │  │  │ models.py    │  │ schema.py    │             │ │   │
│  │  │  │ (SQLAlchemy) │  │ (Pydantic)   │             │ │   │
│  │  │  └──────────────┘  └──────────────┘             │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  │                                                          │   │
│  │  ┌────────────────────────────────────────────────────┐ │   │
│  │  │           Sentence Transformer Model               │ │   │
│  │  │         (thenlper/gte-large - in memory)          │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│    DATA LAYER            │  │   EXTERNAL SERVICES      │
│                          │  │                          │
│  PostgreSQL + pgvector   │  │  OpenAI API (GPT-4o)    │
│                          │  │  or                      │
│  ┌────────────────────┐  │  │  Anthropic (Claude)     │
│  │ Existing Tables:   │  │  │                          │
│  │ - words           │  │  │  ┌────────────────────┐  │
│  │ - sequences       │  │  │  │ LLM Endpoints:     │  │
│  │ - embeddings      │  │  │  │                    │  │
│  │ - embedding_models│  │  │  │ - chat.completions │  │
│  └────────────────────┘  │  │  │ - embeddings       │  │
│                          │  │  └────────────────────┘  │
│  ┌────────────────────┐  │  │                          │
│  │ New Tables:        │  │  └──────────────────────────┘
│  │ - user_sessions   │  │
│  │ - name_suggestions│  │
│  │ - name_preferences│  │
│  │ - chat_messages   │  │
│  └────────────────────┘  │
│                          │
└──────────────────────────┘
```

---

## 2. Data Flow Architecture

### Flow 1: Initial Search Query

```
┌─────────┐
│  User   │
│ enters  │
│ "peace" │
└────┬────┘
     │
     ▼
┌─────────────────────────────────────────┐
│ Frontend: search()                      │
│ - Capture input                         │
│ - Generate/retrieve session_id          │
│ - POST /api/chat                        │
└────┬────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│ Backend: /api/chat endpoint             │
│                                         │
│ Step 1: Vector Search                  │
│ ┌─────────────────────────────────┐   │
│ │ - Encode "peace" using          │   │
│ │   sentence transformer          │   │
│ │ - Query embeddings table        │   │
│ │ - Use pgvector cosine_distance  │   │
│ │ - Return top 20 similar words   │   │
│ └─────────────────────────────────┘   │
│         │                               │
│         ▼                               │
│ Step 2: Extract Root Words             │
│ ┌─────────────────────────────────┐   │
│ │ - Group by arabic_word          │   │
│ │ - Take top 5 unique roots       │   │
│ │ - Example: سلم, أمن, سكن        │   │
│ └─────────────────────────────────┘   │
│         │                               │
│         ▼                               │
│ Step 3: Get User Preferences           │
│ ┌─────────────────────────────────┐   │
│ │ - Query name_preferences        │   │
│ │ - Filter by session_id          │   │
│ │ - Get liked names               │   │
│ │ - Get disliked names            │   │
│ └─────────────────────────────────┘   │
│         │                               │
│         ▼                               │
│ Step 4: Call LLM Service               │
│ ┌─────────────────────────────────┐   │
│ │ generate_names_from_roots()     │   │
│ │                                 │   │
│ │ a) Build prompt:                │   │
│ │    - Root words data            │   │
│ │    - Meanings & verses          │   │
│ │    - User preferences           │   │
│ │    - User query context         │   │
│ │                                 │   │
│ │ b) Call OpenAI API:             │   │
│ │    - Model: gpt-4o-mini         │   │
│ │    - Temperature: 0.7           │   │
│ │    - response_format: json      │   │
│ │                                 │   │
│ │ c) Parse JSON response          │   │
│ │                                 │   │
│ │ d) Save to name_suggestions     │   │
│ └─────────────────────────────────┘   │
│         │                               │
│         ▼                               │
│ Step 5: Save Chat History              │
│ ┌─────────────────────────────────┐   │
│ │ - Insert user message           │   │
│ │ - Insert assistant response     │   │
│ └─────────────────────────────────┘   │
│         │                               │
│         ▼                               │
│ Step 6: Return Response                │
│ ┌─────────────────────────────────┐   │
│ │ {                               │   │
│ │   message: "I found 8 names..." │   │
│ │   suggestions: [...],           │   │
│ │   root_words: [...]             │   │
│ │ }                               │   │
│ └─────────────────────────────────┘   │
└────┬────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│ Frontend: Display Results               │
│                                         │
│ Left Panel:                             │
│ ┌─────────────────────────────────┐   │
│ │ Name Cards                      │   │
│ │ - سليم (Salim) "Safe"          │   │
│ │   [👍 Like] [👎 Dislike]       │   │
│ │ - سلمى (Salma) "Peaceful"      │   │
│ │   [👍 Like] [👎 Dislike]       │   │
│ └─────────────────────────────────┘   │
│                                         │
│ Right Panel:                            │
│ ┌─────────────────────────────────┐   │
│ │ Root Word Analysis              │   │
│ │ - Root: سلم                     │   │
│ │ - Verses: [2:208, 5:16...]     │   │
│ │ - Meanings: peace, safety...    │   │
│ └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Flow 2: User Likes a Name

```
┌─────────┐
│  User   │
│ clicks  │
│  "👍"   │
└────┬────┘
     │
     ▼
┌─────────────────────────────────────────┐
│ Frontend: setPreference()               │
│ POST /api/preferences                   │
│ {                                       │
│   session_id: "session_123",           │
│   suggestion_id: 42,                   │
│   preference: "like"                   │
│ }                                       │
└────┬────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│ Backend: Save Preference                │
│                                         │
│ 1. Check if preference exists           │
│    - Query by session_id + suggestion_id│
│                                         │
│ 2. If exists: UPDATE                    │
│    - Set preference = "like"            │
│                                         │
│ 3. If not: INSERT                       │
│    - Create new row                     │
│    - is_active = TRUE                   │
│                                         │
│ 4. Commit to database                   │
└────┬────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│ Frontend: Update UI                     │
│ - Highlight like button                 │
│ - Store in local state                  │
└─────────────────────────────────────────┘
```

### Flow 3: Subsequent Chat Messages

```
┌─────────┐
│  User   │
│ types:  │
│"similar"│
└────┬────┘
     │
     ▼
┌─────────────────────────────────────────┐
│ Backend: /api/chat                      │
│                                         │
│ This time preferences exist:            │
│                                         │
│ preferences = {                         │
│   liked: ["Salim", "Amin"],            │
│   disliked: ["Qasim"]                  │
│ }                                       │
│                                         │
│ LLM Prompt includes:                    │
│ "User previously liked: Salim, Amin"    │
│ "Avoid names similar to: Qasim"         │
│                                         │
│ → LLM generates similar names           │
│ → Filters out "Qasim" from results      │
└─────────────────────────────────────────┘
```

---

## 3. Database Architecture

### Entity Relationship Diagram

```
┌─────────────────────────┐
│   user_sessions         │
│─────────────────────────│
│ id (UUID) [PK]          │
│ created_at              │
│ last_active             │
└────────┬────────────────┘
         │
         │ 1:N
         │
         ├──────────────────────────────┐
         │                              │
         ▼                              ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│   chat_messages         │    │   name_suggestions      │
│─────────────────────────│    │─────────────────────────│
│ id [PK]                 │    │ id [PK]                 │
│ session_id [FK]         │    │ session_id [FK]         │
│ role (user/assistant)   │    │ name_arabic             │
│ content                 │    │ name_transliteration    │
│ created_at              │    │ name_meaning            │
└─────────────────────────┘    │ root_word               │
                               │ gender                  │
                               │ verse_references (JSON) │
                               │ explanation             │
                               │ source                  │
                               │ created_at              │
                               └────────┬────────────────┘
                                        │
                                        │ 1:N
                                        │
                                        ▼
                               ┌─────────────────────────┐
                               │   name_preferences      │
                               │─────────────────────────│
                               │ id [PK]                 │
                               │ session_id [FK]         │
                               │ suggestion_id [FK]      │
                               │ preference              │
                               │ rating                  │
                               │ is_active               │
                               │ created_at              │
                               └─────────────────────────┘

┌─────────────────────────┐
│   EXISTING TABLES       │
│─────────────────────────│
│ words                   │◄─── Used for vector search
│ sequences               │◄─── Root word definitions
│ embeddings              │◄─── Vector storage (pgvector)
│ embedding_models        │◄─── Model metadata
└─────────────────────────┘
```

### Database Queries Overview

```sql
-- Query 1: Vector Search (existing)
SELECT 
    w.*, 
    e.embedding <=> :query_embedding AS similarity
FROM words w
JOIN embeddings e ON w.id = e.word_id
WHERE e.embedding <=> :query_embedding < 0.7
ORDER BY similarity
LIMIT 20;

-- Query 2: Get User Preferences
SELECT 
    ns.*,
    np.preference,
    np.rating
FROM name_suggestions ns
LEFT JOIN name_preferences np 
    ON ns.id = np.suggestion_id 
    AND np.session_id = :session_id
    AND np.is_active = TRUE
WHERE ns.session_id = :session_id;

-- Query 3: Filter Out Disliked Names
SELECT ns.*
FROM name_suggestions ns
WHERE ns.session_id = :session_id
  AND ns.id NOT IN (
    SELECT suggestion_id 
    FROM name_preferences 
    WHERE session_id = :session_id 
      AND preference = 'dislike'
      AND is_active = TRUE
  );

-- Query 4: Get Chat History
SELECT role, content, created_at
FROM chat_messages
WHERE session_id = :session_id
ORDER BY created_at DESC
LIMIT 10;
```

---

## 4. API Architecture

### API Contract Specifications

```yaml
# Existing Endpoint (no changes)
GET /api/search
  Query Params:
    - q: string (required)
    - limit: integer (default: 10)
    - min_similarity: float (default: 0.3)
  
  Response: 200 OK
    {
      "results": [
        {
          "arabic_word": "سلم",
          "transliteration": "salama",
          "english_text": "peace",
          "category": "Noun",
          "verse_reference": "2:208",
          "quran_verse": "...",
          "similarity": 0.85
        }
      ]
    }

# New Endpoints

POST /api/chat
  Body:
    {
      "message": "I want a name meaning light",
      "session_id": "session_123",
      "context": {  // optional
        "gender": "male",
        "preferences": {...}
      }
    }
  
  Response: 200 OK
    {
      "message": "I found 8 name suggestions...",
      "suggestions": [
        {
          "id": 1,
          "name_arabic": "سليم",
          "name_transliteration": "Salim",
          "name_meaning": "Safe, Sound",
          "root_word": "سلم",
          "gender": "male",
          "verse_references": ["37:84", "2:208"],
          "explanation": "Derived from...",
          "preference": null,  // or "like"/"dislike"
          "rating": null
        }
      ],
      "root_words": [
        // Same as /api/search response
      ]
    }

POST /api/generate-names
  Body:
    {
      "root_words": ["سلم", "أمن", "نور"],
      "session_id": "session_123",
      "user_preferences": {
        "liked": [...],
        "disliked": [...]
      }
    }
  
  Response: 200 OK
    {
      "suggestions": [
        // Same structure as above
      ]
    }

POST /api/preferences
  Body:
    {
      "session_id": "session_123",
      "suggestion_id": 42,
      "preference": "like",  // or "dislike", "neutral"
      "rating": 5  // optional, 1-5
    }
  
  Response: 200 OK
    {
      "status": "success",
      "preference_id": 123
    }

DELETE /api/preferences/{preference_id}
  Response: 200 OK
    {
      "status": "success"
    }

GET /api/preferences/{session_id}
  Response: 200 OK
    {
      "liked": [
        {
          "id": 1,
          "name_arabic": "سليم",
          // ... full suggestion object
        }
      ],
      "disliked": [...],
      "total_ratings": 15
    }

GET /api/suggestions/{session_id}
  Query Params:
    - include_disliked: boolean (default: false)
  
  Response: 200 OK
    {
      "suggestions": [
        // All suggestions with preferences attached
      ]
    }

GET /api/chat/history/{session_id}
  Query Params:
    - limit: integer (default: 50)
  
  Response: 200 OK
    {
      "messages": [
        {
          "role": "user",
          "content": "I want a name meaning peace",
          "created_at": "2025-10-19T10:30:00Z"
        },
        {
          "role": "assistant",
          "content": "I found 8 names...",
          "created_at": "2025-10-19T10:30:02Z"
        }
      ]
    }
```

---

## 5. Component Architecture

### Backend Components

```
app/
├── main.py                    # FastAPI app, routes
├── database.py                # DB connection, session
├── models.py                  # SQLAlchemy models
├── schema.py                  # Pydantic schemas
├── query.py                   # Vector search logic (existing)
│
├── services/                  # New directory
│   ├── __init__.py
│   ├── llm_service.py        # LLM integration
│   ├── name_service.py       # Name generation logic
│   └── preference_service.py # Preference management
│
├── utils/                     # New directory
│   ├── __init__.py
│   ├── session.py            # Session management
│   └── filters.py            # Preference filtering
│
└── config.py                  # Configuration (new)
```

### Service Layer Details

```python
# services/llm_service.py
class LLMService:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    async def generate_names(
        self,
        root_words: List[Dict],
        preferences: Dict,
        user_query: str
    ) -> List[Dict]:
        """Generate names from root words"""
        pass
    
    def build_prompt(self, ...):
        """Build LLM prompt"""
        pass
    
    def parse_response(self, response: str) -> List[Dict]:
        """Parse LLM JSON response"""
        pass

# services/name_service.py
class NameService:
    def __init__(self, db: Session, llm_service: LLMService):
        self.db = db
        self.llm = llm_service
    
    async def generate_and_save(
        self,
        root_words: List[str],
        session_id: str,
        preferences: Dict
    ) -> List[NameSuggestion]:
        """Generate names and save to DB"""
        pass
    
    def get_suggestions(
        self,
        session_id: str,
        include_disliked: bool = False
    ) -> List[NameSuggestion]:
        """Get all suggestions for session"""
        pass

# services/preference_service.py
class PreferenceService:
    def __init__(self, db: Session):
        self.db = db
    
    def save_preference(self, ...):
        """Save user preference"""
        pass
    
    def undo_preference(self, preference_id: int):
        """Soft delete preference"""
        pass
    
    def get_user_preferences(self, session_id: str) -> Dict:
        """Get all preferences for session"""
        pass
    
    def filter_by_preferences(
        self,
        suggestions: List,
        preferences: Dict
    ) -> List:
        """Filter out disliked suggestions"""
        pass
```

---

## 6. Frontend Architecture

### Component Structure

```
static/
├── index.html                 # Main HTML
├── style.css                  # Styles
├── script.js                  # Main logic
│
└── js/                        # Modular JS (optional refactor)
    ├── api.js                 # API calls
    ├── chat.js                # Chat interface
    ├── names.js               # Name cards
    ├── preferences.js         # Like/dislike logic
    └── session.js             # Session management
```

### State Management

```javascript
// Global application state
const AppState = {
    sessionId: null,
    currentQuery: null,
    suggestions: [],
    rootWords: [],
    preferences: {
        liked: [],
        disliked: []
    },
    chatHistory: []
};

// State updates
function updateState(key, value) {
    AppState[key] = value;
    localStorage.setItem('appState', JSON.stringify(AppState));
    renderUI();
}

// Initialize from localStorage
function initState() {
    const saved = localStorage.getItem('appState');
    if (saved) {
        Object.assign(AppState, JSON.parse(saved));
    } else {
        AppState.sessionId = generateSessionId();
    }
}
```

---

## 7. LLM Integration Architecture

### Prompt Strategy

```
┌─────────────────────────────────────────┐
│         LLM Prompt Structure            │
├─────────────────────────────────────────┤
│                                         │
│ 1. System Message (Role)                │
│    "You are an expert in Arabic names   │
│     from the Quran..."                  │
│                                         │
│ 2. Context (Data)                       │
│    ┌─────────────────────────────┐     │
│    │ Root Words:                 │     │
│    │ - Arabic: سلم               │     │
│    │ - Meanings: [peace, safety] │     │
│    │ - Verses: [2:208, 5:16]    │     │
│    └─────────────────────────────┘     │
│                                         │
│ 3. User Preferences                     │
│    ┌─────────────────────────────┐     │
│    │ Liked: Salim, Amin          │     │
│    │ Disliked: Qasim             │     │
│    └─────────────────────────────┘     │
│                                         │
│ 4. User Query                           │
│    "I want a name meaning peace"        │
│                                         │
│ 5. Instructions                         │
│    - Generate 2-4 names per root        │
│    - Return JSON only                   │
│    - Include explanations               │
│                                         │
│ 6. Output Format (JSON Schema)          │
│    [{ name_arabic, transliteration,     │
│       meaning, root_word, ... }]        │
└─────────────────────────────────────────┘
```

### Response Handling

```
┌─────────────────────────────────────────┐
│         LLM Response Pipeline           │
├─────────────────────────────────────────┤
│                                         │
│ 1. Receive Response                     │
│    ↓                                    │
│ 2. Parse JSON                           │
│    - Handle different structures        │
│    - Extract names array                │
│    ↓                                    │
│ 3. Validate Data                        │
│    - Check required fields              │
│    - Validate Arabic script             │
│    - Verify root words exist            │
│    ↓                                    │
│ 4. Enrich with DB Data                  │
│    - Add verse details                  │
│    - Add morphology info                │
│    - Link to root words table           │
│    ↓                                    │
│ 5. Filter by Preferences                │
│    - Remove disliked patterns           │
│    - Prioritize liked patterns          │
│    ↓                                    │
│ 6. Save to Database                     │
│    - Insert into name_suggestions       │
│    - Link to session                    │
│    ↓                                    │
│ 7. Return to Client                     │
└─────────────────────────────────────────┘
```

---

## 8. Deployment Architecture

### Development Environment

```
┌─────────────────────────────────────────┐
│        Developer Machine                │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  FastAPI (localhost:8000)        │  │
│  │  - Hot reload enabled            │  │
│  │  - Debug mode ON                 │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  PostgreSQL (localhost:5432)     │  │
│  │  - pgvector extension            │  │
│  │  - Development data              │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  Static Files (served by FastAPI)│  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Production Architecture (Recommended)

```
┌─────────────────────────────────────────────────────────┐
│                    Internet                              │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│               Load Balancer / CDN                        │
│                  (Cloudflare / AWS)                      │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│               Web Server (Nginx)                         │
│  - Serve static files                                    │
│  - Reverse proxy to FastAPI                              │
│  - SSL termination                                       │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│  FastAPI App 1   │          │  FastAPI App 2   │
│  (Gunicorn)      │          │  (Gunicorn)      │
│                  │          │                  │
│  Workers: 4      │          │  Workers: 4      │
└────────┬─────────┘          └────────┬─────────┘
         │                              │
         └──────────────┬───────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │  PostgreSQL + pgvector       │
         │  - Primary instance          │
         │  - Read replicas (optional)  │
         └──────────────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │  Redis (optional)            │
         │  - Cache LLM responses       │
         │  - Session storage           │
         └──────────────────────────────┘

External Services:
┌──────────────────────────────┐
│  OpenAI API                  │
│  - GPT-4o-mini               │
└──────────────────────────────┘
```

---

## 9. Tech Stack Summary

```
┌─────────────────────────────────────────┐
│           TECHNOLOGY STACK              │
├─────────────────────────────────────────┤
│                                         │
│ Frontend:                               │
│  ✓ HTML5                                │
│  ✓ CSS3 (Responsive)                    │
│  ✓ Vanilla JavaScript (ES6+)           │
│  ✓ Fetch API for HTTP requests         │
│                                         │
│ Backend:                                │
│  ✓ Python 3.11+                         │
│  ✓ FastAPI 0.104+                       │
│  ✓ SQLAlchemy 2.0+                      │
│  ✓ Alembic (migrations)                 │
│  ✓ Pydantic v2                          │
│                                         │
│ Database:                               │
│  ✓ PostgreSQL 15+                       │
│  ✓ pgvector 0.5.0+                      │
│                                         │
│ ML/AI:                                  │
│  ✓ sentence-transformers                │
│  ✓ thenlper/gte-large model            │
│  ✓ OpenAI GPT-4o-mini                   │
│  ✓ (or Anthropic Claude 3.5 Sonnet)    │
│                                         │
│ Development Tools:                      │
│  ✓ uvicorn (ASGI server)               │
│  ✓ pytest (testing)                     │
│  ✓ black (code formatting)              │
│                                         │
│ Production:                             │
│  ✓ Gunicorn (production server)         │
│  ✓ Nginx (reverse proxy)                │
│  ✓ Docker (containerization)            │
│  ✓ Redis (caching - optional)           │
└─────────────────────────────────────────┘
```

---

## 10. Security Architecture

### Authentication & Authorization

```
┌─────────────────────────────────────────┐
│     Session-Based Security              │
├─────────────────────────────────────────┤
│                                         │
│ Phase 1 (MVP):                          │
│  ✓ Anonymous sessions (UUID)            │
│  ✓ Browser-based session storage        │
│  ✓ No authentication required           │
│                                         │
│ Phase 2 (Future):                       │
│  ✓ Optional user accounts               │
│  ✓ OAuth2 (Google, Apple)               │
│  ✓ JWT tokens                           │
│  ✓ Rate limiting per user               │
└─────────────────────────────────────────┘
```

### Data Security

```
1. API Keys
   - Store in environment variables
   - Never commit to version control
   - Use .env files locally
   - Use secrets manager in production

2. Database
   - Use parameterized queries (SQLAlchemy)
   - No raw SQL strings
   - Connection pooling
   - SSL connections in production

3. LLM Integration
   - Rate limiting (100 requests/hour per session)
   - Input validation
   - Output sanitization
   - Cost monitoring

4. User Data
   - Session IDs are UUIDs
   - No PII collected (initially)
   - GDPR considerations for future
   - Data retention policies
```

---

## 11. Performance Considerations

### Optimization Strategy

```
┌─────────────────────────────────────────┐
│      Performance Optimizations          │
├─────────────────────────────────────────┤
│                                         │
│ 1. Vector Search                        │
│    - Index on embedding columns         │
│    - Limit results (default 20)         │
│    - Cache frequent queries             │
│    - Batch embedding generation         │
│                                         │
│ 2. LLM Calls                            │
│    - Cache responses (1 hour)           │
│    - Batch processing (5 roots)         │
│    - Async calls                        │
│    - Timeout handling                   │
│                                         │
│ 3. Database                             │
│    - Connection pooling                 │
│    - Query optimization                 │
│    - Proper indexing                    │
│    - Read replicas (future)             │
│                                         │
│ 4. Frontend                             │
│    - Lazy loading                       │
│    - Debounced search                   │
│    - Local state management             │
│    - Minimal DOM manipulation           │
│                                         │
│ 5. Caching Layers                       │
│    - Browser cache (static files)       │
│    - API response cache (Redis)         │
│    - LLM response cache (DB)            │
└─────────────────────────────────────────┘
```

### Expected Latency

```
Operation                  | Target Latency
---------------------------|---------------
Vector search              | < 100ms
LLM name generation        | 1-3 seconds
Save preference            | < 50ms
Load suggestions           | < 100ms
Full chat request          | 1.5-4 seconds
```

---

## 12. Monitoring & Observability

```
┌─────────────────────────────────────────┐
│          Monitoring Strategy            │
├─────────────────────────────────────────┤
│                                         │
│ Application Metrics:                    │
│  - Request count per endpoint           │
│  - Response times (p50, p95, p99)       │
│  - Error rates                          │
│  - LLM API calls & costs                │
│                                         │
│ Business Metrics:                       │
│  - Total sessions                       │
│  - Names generated                      │
│  - Like/dislike ratios                  │
│  - Average session duration             │
│                                         │
│ Infrastructure:                         │
│  - CPU/Memory usage                     │
│  - Database connections                 │
│  - Query performance                    │
│  - Disk usage                           │
│                                         │
│ Tools (Future):                         │
│  - FastAPI middleware for logging       │
│  - Prometheus for metrics               │
│  - Grafana for dashboards               │
│  - Sentry for error tracking            │
└─────────────────────────────────────────┘
```

---

## 13. Implementation Roadmap

```
Week 1: Foundation
├── Day 1: Database schema & migrations
├── Day 2: New API endpoints (basic)
├── Day 3: LLM integration service
└── Day 4: Testing & refinement

Week 2: Frontend
├── Day 1: Chat interface UI
├── Day 2: Name cards & preferences
├── Day 3: Integration with backend
└── Day 4: Polish & bug fixes

Week 3: Enhancement
├── Day 1: Performance optimization
├── Day 2: Better LLM prompts
├── Day 3: UI/UX improvements
└── Day 4: Testing & deployment prep

Week 4: Production
├── Day 1: Production setup
├── Day 2: Deployment
├── Day 3: Monitoring setup
└── Day 4: Documentation
```