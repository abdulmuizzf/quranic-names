# Quranic Name Finder - Implementation Plan (Based on Existing Project)

## Project Enhancement Overview
Add LLM-powered name generation to your existing semantic search app with user preference tracking.

---

## 1. Database Schema Updates

### New Tables to Add

```python
# Add to models.py

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(String, primary_key=True)  # UUID
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

class NameSuggestion(Base):
    __tablename__ = "name_suggestions"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey("user_sessions.id"))
    name_arabic = Column(String, nullable=False)
    name_transliteration = Column(String)
    name_meaning = Column(String)
    root_word = Column(String)  # The sequence/root
    gender = Column(String)  # 'male', 'female', 'unisex'
    verse_references = Column(JSON)  # Array of verse refs
    explanation = Column(Text)  # Why this name
    source = Column(String)  # 'llm' or 'direct' (from quran)
    created_at = Column(DateTime, default=datetime.utcnow)

class NamePreference(Base):
    __tablename__ = "name_preferences"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey("user_sessions.id"))
    suggestion_id = Column(Integer, ForeignKey("name_suggestions.id"))
    preference = Column(String)  # 'like', 'dislike', 'neutral'
    rating = Column(Integer)  # 1-5, optional
    is_active = Column(Boolean, default=True)  # for undo
    created_at = Column(DateTime, default=datetime.utcnow)
    
    suggestion = relationship("NameSuggestion")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey("user_sessions.id"))
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Migration Command
```bash
# Create migration
alembic revision --autogenerate -m "add name suggestions and preferences"

# Run migration
alembic upgrade head
```

---

## 2. New Pydantic Schemas

```python
# Add to schema.py

from typing import Optional, List
from pydantic import BaseModel

class NameSuggestionResponse(BaseModel):
    id: int
    name_arabic: str
    name_transliteration: str
    name_meaning: str
    root_word: str
    gender: str
    verse_references: List[str]
    explanation: str
    preference: Optional[str] = None  # user's preference if exists
    rating: Optional[int] = None
    
    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    session_id: str
    context: Optional[dict] = None  # optional metadata

class ChatResponse(BaseModel):
    message: str
    suggestions: List[NameSuggestionResponse]
    root_words: List[SearchResult]  # reuse existing schema

class PreferenceRequest(BaseModel):
    session_id: str
    suggestion_id: int
    preference: str  # 'like', 'dislike', 'neutral'
    rating: Optional[int] = None

class GenerateNamesRequest(BaseModel):
    root_words: List[str]  # max 5
    session_id: str
    user_preferences: Optional[dict] = None
```

---

## 3. New API Endpoints

```python
# Add to main.py or new routes/names.py

from openai import OpenAI  # or anthropic
import json

# Initialize LLM client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Main chat endpoint:
    1. Search for similar words using existing API
    2. Get user preferences
    3. Generate names from top 5 root words
    4. Return combined response
    """
    
    # 1. Use existing search logic
    search_results = get_similar_words(
        db=db,
        query=request.message,
        limit=20,
        min_similarity=0.3
    )
    
    # 2. Get user preferences
    preferences = get_user_preferences(db, request.session_id)
    
    # 3. Extract top root words
    root_words = list(set([
        result.arabic_word for result in search_results[:5]
    ]))
    
    # 4. Generate names from root words
    name_suggestions = await generate_names_from_roots(
        db=db,
        root_words=root_words,
        session_id=request.session_id,
        preferences=preferences,
        user_query=request.message
    )
    
    # 5. Save chat message
    save_chat_message(db, request.session_id, "user", request.message)
    
    # 6. Create response message
    response_message = create_response_message(name_suggestions, search_results)
    save_chat_message(db, request.session_id, "assistant", response_message)
    
    return ChatResponse(
        message=response_message,
        suggestions=name_suggestions,
        root_words=search_results[:10]
    )


@app.post("/api/generate-names", response_model=List[NameSuggestionResponse])
async def generate_names_endpoint(
    request: GenerateNamesRequest,
    db: Session = Depends(get_db)
):
    """
    Generate names from specific root words (max 5 at a time)
    This is the batched endpoint for long results
    """
    
    if len(request.root_words) > 5:
        raise HTTPException(400, "Maximum 5 root words per request")
    
    # Get full word data for these roots
    word_data = []
    for root in request.root_words:
        words = db.query(Word).filter(
            Word.arabic_word == root
        ).limit(5).all()
        word_data.extend(words)
    
    # Generate names
    suggestions = await generate_names_from_roots(
        db=db,
        root_words=request.root_words,
        session_id=request.session_id,
        preferences=request.user_preferences,
        word_data=word_data
    )
    
    return suggestions


@app.post("/api/preferences")
async def save_preference(
    request: PreferenceRequest,
    db: Session = Depends(get_db)
):
    """Save or update user preference for a name suggestion"""
    
    # Check if preference already exists
    existing = db.query(NamePreference).filter(
        NamePreference.session_id == request.session_id,
        NamePreference.suggestion_id == request.suggestion_id,
        NamePreference.is_active == True
    ).first()
    
    if existing:
        # Update existing
        existing.preference = request.preference
        existing.rating = request.rating
    else:
        # Create new
        new_pref = NamePreference(
            session_id=request.session_id,
            suggestion_id=request.suggestion_id,
            preference=request.preference,
            rating=request.rating
        )
        db.add(new_pref)
    
    db.commit()
    return {"status": "success"}


@app.delete("/api/preferences/{preference_id}")
async def undo_preference(
    preference_id: int,
    db: Session = Depends(get_db)
):
    """Undo a preference (soft delete)"""
    
    pref = db.query(NamePreference).filter(
        NamePreference.id == preference_id
    ).first()
    
    if not pref:
        raise HTTPException(404, "Preference not found")
    
    pref.is_active = False
    db.commit()
    
    return {"status": "success"}


@app.get("/api/preferences/{session_id}")
async def get_preferences(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get user's preference summary"""
    
    prefs = db.query(NamePreference).filter(
        NamePreference.session_id == session_id,
        NamePreference.is_active == True
    ).all()
    
    liked = []
    disliked = []
    
    for pref in prefs:
        if pref.preference == 'like':
            liked.append(pref.suggestion)
        elif pref.preference == 'dislike':
            disliked.append(pref.suggestion)
    
    return {
        "liked": liked,
        "disliked": disliked,
        "total_ratings": len(prefs)
    }


@app.get("/api/suggestions/{session_id}")
async def get_suggestions(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get all suggestions for a session, with preferences"""
    
    suggestions = db.query(NameSuggestion).filter(
        NameSuggestion.session_id == session_id
    ).all()
    
    # Get preferences
    prefs = {
        p.suggestion_id: p 
        for p in db.query(NamePreference).filter(
            NamePreference.session_id == session_id,
            NamePreference.is_active == True
        ).all()
    }
    
    # Combine
    results = []
    for suggestion in suggestions:
        pref = prefs.get(suggestion.id)
        result = NameSuggestionResponse.from_orm(suggestion)
        if pref:
            result.preference = pref.preference
            result.rating = pref.rating
        results.append(result)
    
    # Filter out disliked
    results = [r for r in results if r.preference != 'dislike']
    
    return results
```

---

## 4. LLM Integration Logic

```python
# Add to new file: services/llm_service.py

from openai import OpenAI
import json
from typing import List, Dict

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def generate_names_from_roots(
    db: Session,
    root_words: List[str],
    session_id: str,
    preferences: Dict = None,
    user_query: str = None,
    word_data: List = None
) -> List[NameSuggestionResponse]:
    """
    Generate name suggestions from root words using LLM
    
    Simple approach: Give LLM the data, ask for names
    """
    
    # Prepare data for LLM
    root_data = []
    for root in root_words:
        # Get words for this root
        words = word_data or db.query(Word).filter(
            Word.arabic_word == root
        ).limit(5).all()
        
        root_info = {
            "root": root,
            "meanings": [w.english_text for w in words],
            "transliterations": [w.transliteration for w in words],
            "verses": [
                {
                    "ref": w.verse_reference,
                    "text": w.quran_verse
                } for w in words[:2]  # limit verses
            ]
        }
        root_data.append(root_info)
    
    # Prepare user preferences context
    pref_context = ""
    if preferences:
        if preferences.get('liked'):
            liked_names = [n.name_arabic for n in preferences['liked'][:5]]
            pref_context += f"\nUser liked: {', '.join(liked_names)}"
        if preferences.get('disliked'):
            disliked_names = [n.name_arabic for n in preferences['disliked'][:5]]
            pref_context += f"\nUser disliked: {', '.join(disliked_names)}"
    
    # Build simple prompt
    prompt = f"""Based on these Quranic root words, generate Arabic name suggestions.

ROOT WORDS DATA:
{json.dumps(root_data, ensure_ascii=False, indent=2)}

USER QUERY: {user_query or 'General name suggestions'}
{pref_context}

For EACH root word, generate 2-4 possible Arabic names that could be derived from it.
Include both traditional names and potential modern variations.

Return a JSON array with this structure:
[
  {{
    "name_arabic": "سليم",
    "name_transliteration": "Salim",
    "name_meaning": "Safe, Sound, Complete",
    "root_word": "سلم",
    "gender": "male|female|unisex",
    "verse_references": ["37:84"],
    "explanation": "Brief explanation of the name's origin and meaning"
  }}
]

IMPORTANT:
- Only suggest names that are appropriate and have positive meanings
- Avoid names similar to those the user disliked
- Generate ONLY valid JSON, no additional text"""

    # Call LLM
    response = client.chat.completions.create(
        model="gpt-4o",  # or gpt-4o-mini for cheaper
        messages=[
            {
                "role": "system",
                "content": "You are an expert in Arabic names from the Quran. You generate appropriate, meaningful names with accurate linguistic information."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        response_format={"type": "json_object"}  # Force JSON
    )
    
    # Parse response
    try:
        llm_output = json.loads(response.choices[0].message.content)
        
        # Handle different JSON structures
        if isinstance(llm_output, dict) and 'names' in llm_output:
            names_list = llm_output['names']
        elif isinstance(llm_output, list):
            names_list = llm_output
        else:
            names_list = [llm_output]
        
    except json.JSONDecodeError:
        # Fallback if LLM doesn't return valid JSON
        names_list = []
    
    # Save suggestions to database
    suggestions = []
    for name_data in names_list:
        suggestion = NameSuggestion(
            session_id=session_id,
            name_arabic=name_data.get('name_arabic', ''),
            name_transliteration=name_data.get('name_transliteration', ''),
            name_meaning=name_data.get('name_meaning', ''),
            root_word=name_data.get('root_word', ''),
            gender=name_data.get('gender', 'unisex'),
            verse_references=name_data.get('verse_references', []),
            explanation=name_data.get('explanation', ''),
            source='llm'
        )
        db.add(suggestion)
        db.flush()  # Get ID
        
        suggestions.append(NameSuggestionResponse.from_orm(suggestion))
    
    db.commit()
    
    return suggestions


def get_user_preferences(db: Session, session_id: str) -> Dict:
    """Get user's liked/disliked names"""
    
    prefs = db.query(NamePreference).filter(
        NamePreference.session_id == session_id,
        NamePreference.is_active == True
    ).all()
    
    liked = []
    disliked = []
    
    for pref in prefs:
        if pref.preference == 'like':
            liked.append(pref.suggestion)
        elif pref.preference == 'dislike':
            disliked.append(pref.suggestion)
    
    return {
        "liked": liked,
        "disliked": disliked
    }


def create_response_message(
    suggestions: List[NameSuggestionResponse],
    search_results: List
) -> str:
    """Create a friendly chat response message"""
    
    root_words = list(set([r.arabic_word for r in search_results[:5]]))
    
    message = f"I found {len(suggestions)} name suggestions based on these Quranic roots: "
    message += ", ".join(root_words[:3])
    if len(root_words) > 3:
        message += f" and {len(root_words) - 3} more."
    
    return message


def save_chat_message(db: Session, session_id: str, role: str, content: str):
    """Save a chat message to history"""
    
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content
    )
    db.add(message)
    db.commit()
```

---

## 5. Frontend Updates

### Updated HTML Structure

```html
<!-- Add to index.html -->

<div class="container">
    <!-- Existing search box -->
    <div class="search-section">
        <input type="text" id="searchInput" placeholder="Enter English meaning...">
        <button onclick="search()">Search</button>
    </div>
    
    <!-- NEW: Chat Interface -->
    <div class="chat-section" style="display: none;" id="chatSection">
        <div class="chat-header">
            <h2>Name Suggestions</h2>
            <button onclick="toggleChat()">Close</button>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <!-- Messages will be inserted here -->
        </div>
        
        <div class="chat-input">
            <input type="text" id="chatInput" placeholder="Describe the name you're looking for...">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>
    
    <!-- Split view for results -->
    <div class="results-container">
        <!-- Left: Name Suggestions -->
        <div class="names-panel" id="namesPanel">
            <h3>Name Suggestions</h3>
            <div id="nameSuggestions"></div>
        </div>
        
        <!-- Right: Root Words (existing) -->
        <div class="roots-panel" id="rootsPanel">
            <h3>Root Words</h3>
            <div id="results"></div>
        </div>
    </div>
</div>
```

### Updated JavaScript

```javascript
// Add to script.js

let sessionId = generateSessionId();

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36);
}

async function search() {
    const query = document.getElementById('searchInput').value;
    if (!query) return;
    
    // Show chat interface
    document.getElementById('chatSection').style.display = 'block';
    
    // Call chat endpoint instead of direct search
    await sendMessage(query);
}

async function sendMessage(message) {
    const input = document.getElementById('chatInput');
    const query = message || input.value;
    
    if (!query) return;
    
    // Show user message
    addChatMessage('user', query);
    
    // Clear input
    if (input) input.value = '';
    
    // Show loading
    showLoading();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: query,
                session_id: sessionId
            })
        });
        
        const data = await response.json();
        
        // Show assistant message
        addChatMessage('assistant', data.message);
        
        // Display name suggestions
        displayNameSuggestions(data.suggestions);
        
        // Display root words (existing function)
        displayResults(data.root_words);
        
    } catch (error) {
        console.error('Error:', error);
        addChatMessage('assistant', 'Sorry, something went wrong.');
    } finally {
        hideLoading();
    }
}

function addChatMessage(role, content) {
    const messagesDiv = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    messageDiv.textContent = content;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function displayNameSuggestions(suggestions) {
    const panel = document.getElementById('nameSuggestions');
    panel.innerHTML = '';
    
    suggestions.forEach(suggestion => {
        const card = createNameCard(suggestion);
        panel.appendChild(card);
    });
}

function createNameCard(suggestion) {
    const card = document.createElement('div');
    card.className = 'name-card';
    
    // Check if user has a preference
    const hasLiked = suggestion.preference === 'like';
    const hasDisliked = suggestion.preference === 'dislike';
    
    card.innerHTML = `
        <div class="name-header">
            <div class="name-arabic">${suggestion.name_arabic}</div>
            <div class="name-trans">${suggestion.name_transliteration}</div>
        </div>
        
        <div class="name-details">
            <p><strong>Meaning:</strong> ${suggestion.name_meaning}</p>
            <p><strong>Root:</strong> ${suggestion.root_word}</p>
            <p><strong>Gender:</strong> ${suggestion.gender}</p>
            <p><strong>Verses:</strong> ${suggestion.verse_references.join(', ')}</p>
        </div>
        
        <div class="name-explanation">
            ${suggestion.explanation}
        </div>
        
        <div class="name-actions">
            <button 
                class="btn-like ${hasLiked ? 'active' : ''}" 
                onclick="setPreference(${suggestion.id}, 'like')">
                👍 Like
            </button>
            <button 
                class="btn-dislike ${hasDisliked ? 'active' : ''}" 
                onclick="setPreference(${suggestion.id}, 'dislike')">
                👎 Dislike
            </button>
            <select onchange="rateNam(${suggestion.id}, this.value)">
                <option value="">Rate...</option>
                <option value="1">⭐</option>
                <option value="2">⭐⭐</option>
                <option value="3">⭐⭐⭐</option>
                <option value="4">⭐⭐⭐⭐</option>
                <option value="5">⭐⭐⭐⭐⭐</option>
            </select>
        </div>
    `;
    
    return card;
}

async function setPreference(suggestionId, preference) {
    try {
        await fetch('/api/preferences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                suggestion_id: suggestionId,
                preference: preference
            })
        });
        
        // Update UI
        const card = event.target.closest('.name-card');
        if (preference === 'dislike') {
            card.style.opacity = '0.5';
            setTimeout(() => card.remove(), 500);
        } else {
            event.target.classList.add('active');
        }
        
    } catch (error) {
        console.error('Error saving preference:', error);
    }
}

async function rateName(suggestionId, rating) {
    await fetch('/api/preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: sessionId,
            suggestion_id: suggestionId,
            preference: 'neutral',
            rating: parseInt(rating)
        })
    });
}
```

### Updated CSS

```css
/* Add to style.css */

.results-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
    margin-top: 2rem;
}

.chat-section {
    background: white;
    border-radius: 8px;
    padding: 1rem;
    margin: 2rem 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.chat-messages {
    height: 200px;
    overflow-y: auto;
    padding: 1rem;
    background: #f5f5f5;
    border-radius: 4px;
    margin-bottom: 1rem;
}

.chat-message {
    margin: 0.5rem 0;
    padding: 0.5rem;
    border-radius: 4px;
}

.chat-message.user {
    background: #e3f2fd;
    text-align: right;
}

.chat-message.assistant {
    background: #f1f8e9;
}

.name-card {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
    transition: all 0.3s;
}

.name-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.name-arabic {
    font-size: 1.5rem;
    font-weight: bold;
    color: #2c3e50;
    direction: rtl;
}

.name-trans {
    color: #7f8c8d;
    font-style: italic;
}

.name-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
}

.btn-like, .btn-dislike {
    padding: 0.5rem 1rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: white;
    cursor: pointer;
    transition: all 0.2s;
}

.btn-like:hover {
    background: #c8e6c9;
}

.btn-dislike:hover {
    background: #ffcdd2;
}

.btn-like.active {
    background: #4caf50;
    color: white;
}

.btn-dislike.active {
    background: #f44336;
    color: white;
}
```

---

## 6. Environment Setup

```bash
# .env file
OPENAI_API_KEY=your_openai_key_here
# or
ANTHROPIC_API_KEY=your_anthropic_key_here

DATABASE_URL=postgresql://user:pass@localhost/quran_names
```

---

## 7. Implementation Steps

### Step 1: Database (Day 1)
```bash
# Add new models to models.py
# Create migration
alembic revision --autogenerate -m "add name suggestions"
alembic upgrade head
```

### Step 2: Backend API (Day 2-3)
```bash
# Install new dependencies
pip install openai  # or anthropic

# Add new endpoints to main.py
# Create llm_service.py
# Test with curl or Postman
```

### Step 3: Frontend (Day 4)
```bash
# Update HTML structure
# Add JavaScript functions
# Update CSS
# Test end-to-end
```

### Step 4: Testing & Refinement (Day 5)
```bash
# Test different queries
# Adjust LLM prompt if needed
# Test preference tracking
# Test undo functionality
```

---

## 8. Usage Flow

```
User: "I want a name meaning peace"
    ↓
Backend: 
  1. Search vector DB for "peace" → finds "سلم" roots
  2. Get user's past likes/dislikes
  3. Send to LLM: "Generate names from these roots..."
  4. LLM returns JSON with 8-12 name suggestions
  5. Save to database
    ↓
Frontend:
  - Left panel: Shows name cards with like/dislike
  - Right panel: Shows root words and verses
  - User clicks "👍 Like" on "Salim"
    ↓
Backend:
  - Saves preference to database
    ↓
User: "Show me more names like Salim"
    ↓
Backend:
  - Includes "User liked: Salim" in next LLM call
  - LLM suggests similar names
```

---

## 9. API Cost Estimation

Using GPT-4o:
- Input: ~500-1000 tokens per request (root data + preferences)
- Output: ~300-500 tokens (name suggestions JSON)
- Cost: ~$0.01-0.02 per request
- 100 requests = ~$1-2

Using GPT-4o-mini (cheaper):
- Same token counts
- Cost: ~$0.001-0.002 per request
- 100 requests = ~$0.10-0.20

**Recommendation:** Start with GPT-4o-mini, upgrade if quality isn't good enough.

---

## 10. Key Benefits of This Approach

✅ **Minimal Prompt Engineering**: Just feed data to LLM, let it work  
✅ **Builds on Existing System**: Uses your vector search as foundation  
✅ **Batched Processing**: Handle long results by processing 5 roots at a time  
✅ **User Preferences Tracked**: Likes/dislikes influence future suggestions  
✅ **Easy Undo**: Soft delete makes preferences reversible  
✅ **Session-Based**: No authentication needed initially  
✅ **Cost-Effective**: Cache results, batch requests

---

## Next Steps

1. **Choose LLM**: OpenAI GPT-4o-mini recommended for start
2. **Run migrations**: Add new tables
3. **Test LLM integration**: Try with 2-3 root words first
4. **Build frontend**: Start with basic chat UI
5. **Iterate on prompts**: Adjust if LLM output quality isn't good