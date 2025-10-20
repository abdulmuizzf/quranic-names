# LLM-First Approach: Architecture with Strong Prompt Engineering

## Core Philosophy: Let LLM Curate, But with Strong Constraints

You're right - instead of manually curating, we can use the LLM as an intelligent filter that:
1. Takes raw Quranic word data
2. Identifies which words/roots can become valid names
3. Generates appropriate name suggestions
4. Validates against Islamic naming conventions

**Key insight:** The LLM becomes the curation layer, not just a generator.

---

## 🎯 Revised Architecture: LLM as Smart Filter

### System Flow

```
User Query: "peaceful names"
    ↓
Vector Search → Returns 20 Quranic words (including verbs, nouns, etc.)
    ↓
LLM Prompt (with strict constraints) →
    "From these Quranic words, identify ONLY those that can 
     become proper Islamic names. Filter out verbs, particles, 
     inappropriate terms..."
    ↓
LLM Returns → 5-8 validated name suggestions
    ↓
Save to database (for caching/learning)
    ↓
Show to user with preferences
```

---

## 🔒 The Critical Part: Bulletproof Prompt Engineering

### Master Prompt Template

```python
SYSTEM_PROMPT = """You are an Islamic naming expert with deep knowledge of:
- Arabic morphology and grammar
- Islamic naming conventions and restrictions
- Quranic context and meanings
- Gender-appropriate name patterns

Your task is to suggest ONLY appropriate Islamic names based on Quranic words.

CRITICAL RULES:
1. NEVER suggest names that are exclusive to Allah (Asma ul-Husna)
2. ONLY suggest names that are grammatically valid as proper nouns
3. Filter out: verbs, particles, prepositions, pronouns, conjunctions
4. Respect gender markers: -a/-ah (feminine), -i/-an (masculine)
5. ONLY suggest names with positive meanings
6. If a word/root cannot form a valid name, skip it
7. If you're uncertain about appropriateness, DO NOT suggest it

OUTPUT FORMAT: JSON only, no explanations outside the JSON structure.
"""

def build_prompt(query, quranic_words, preferences, gender=None):
    return f"""
TASK: Suggest appropriate Islamic names based on user request and Quranic data.

USER REQUEST: "{query}"
{f"GENDER PREFERENCE: {gender}" if gender else ""}

QURANIC WORDS FROM SEMANTIC SEARCH:
{json.dumps([
    {{
        "arabic": word.arabic_word,
        "transliteration": word.transliteration,
        "meaning": word.english_text,
        "category": word.category,
        "verse": word.verse_reference,
        "context": word.quran_verse[:100]  # First 100 chars
    }}
    for word in quranic_words[:15]  # Limit to prevent token overflow
], ensure_ascii=False, indent=2)}

{build_preference_context(preferences)}

INSTRUCTIONS:
1. Analyze each Quranic word above
2. For each word, determine:
   - Can it be used as a proper name? (YES/NO)
   - Is it grammatically appropriate? (must be noun/adjective, not verb/particle)
   - Is it Islamically appropriate? (positive meaning, not Allah-exclusive)
   - Does it match gender preference? (if specified)

3. For words that CAN become names:
   - Generate 1-2 name variations (e.g., from root س-ل-م: Salim, Salma)
   - Include proper Arabic script with diacritics
   - Provide accurate transliteration
   - Explain the name's meaning and Quranic connection

4. SKIP words that:
   - Are verbs in any tense
   - Are particles, prepositions, conjunctions
   - Have negative meanings
   - Are exclusive to Allah
   - Don't match gender (if specified)

5. Target: Suggest 5-8 HIGH-QUALITY names maximum
   Quality over quantity. Only certain, appropriate suggestions.

RETURN FORMAT (JSON only):
{{
  "names": [
    {{
      "name_arabic": "سليم",
      "name_transliteration": "Salim",
      "name_meaning": "Safe, sound, whole, complete",
      "gender": "male",
      "derived_from": "سلم",
      "quranic_root": "س-ل-م",
      "verse_references": ["37:84"],
      "explanation": "Derived from the Quranic root meaning peace and safety. Used in verse 37:84 describing Prophet Ibrahim's pure heart.",
      "confidence": "high",
      "name_type": "traditional"
    }}
  ],
  "filtered_out": [
    {{
      "word": "أسلم",
      "reason": "This is a verb form (he submitted), not suitable as a name"
    }}
  ]
}}

VALIDATION CHECKLIST before suggesting ANY name:
☐ Is it a noun or adjective (not verb/particle)?
☐ Does it have a positive meaning?
☐ Is it NOT exclusive to Allah?
☐ Is the gender appropriate (if specified)?
☐ Would this name be acceptable in Islamic culture?
☐ Can you verify its usage or derivation?

If you cannot confidently answer YES to all checks, DO NOT suggest the name.
"""

def build_preference_context(preferences):
    if not preferences or not preferences.get('liked'):
        return ""
    
    liked_patterns = analyze_liked_names(preferences['liked'])
    disliked_patterns = analyze_liked_names(preferences.get('disliked', []))
    
    context = "\nUSER PREFERENCES:\n"
    
    if liked_patterns:
        context += f"User liked names with these characteristics:\n"
        context += f"- Meanings: {', '.join(liked_patterns['meanings'][:3])}\n"
        context += f"- Sounds: {', '.join(liked_patterns['phonetic'][:3])}\n"
        context += f"- Examples: {', '.join([n.name_arabic for n in preferences['liked'][:3]])}\n"
    
    if disliked_patterns:
        context += f"\nUser disliked:\n"
        context += f"- {', '.join([n.name_arabic for n in preferences['disliked'][:3]])}\n"
        context += f"Avoid similar patterns.\n"
    
    return context
```

---

## 🛡️ Additional Safety Layers

### 1. Post-Processing Validation

```python
def validate_llm_suggestions(suggestions: List[Dict]) -> List[Dict]:
    """
    Additional validation layer after LLM response
    Even with good prompts, add safety checks
    """
    FORBIDDEN_NAMES = load_forbidden_names()  # Allah's names, inappropriate words
    REQUIRED_FIELDS = ['name_arabic', 'name_transliteration', 'name_meaning', 'gender']
    
    validated = []
    
    for suggestion in suggestions:
        # Check required fields
        if not all(field in suggestion for field in REQUIRED_FIELDS):
            continue
        
        # Check against forbidden list
        if suggestion['name_arabic'] in FORBIDDEN_NAMES:
            continue
        
        # Check gender markers match declared gender
        if not validate_gender_markers(suggestion['name_arabic'], suggestion['gender']):
            continue
        
        # Check Arabic script validity
        if not is_valid_arabic(suggestion['name_arabic']):
            continue
        
        # Check meaning is positive
        if has_negative_sentiment(suggestion['name_meaning']):
            continue
        
        validated.append(suggestion)
    
    return validated

FORBIDDEN_PATTERNS = {
    'allah_names': [
        'الرحمن', 'الرحيم', 'الملك', 'القدوس', 'السلام', 'المؤمن',
        'المهيمن', 'العزيز', 'الجبار', 'المتكبر', 'الخالق', 'البارئ',
        # ... all 99 names
    ],
    'negative_words': [
        'شيطان', 'إبليس', 'جهنم', 'عذاب', 'غضب'
    ],
    'verb_indicators': [
        'أ',  # first person past
        'ن',  # first person present
        'ت',  # second person
        'ي'   # third person (at start)
    ]
}

def validate_gender_markers(arabic_name: str, declared_gender: str) -> bool:
    """Check if gender markers match declared gender"""
    
    # Common feminine endings
    if arabic_name.endswith(('ة', 'اء', 'ى')):
        return declared_gender in ['female', 'unisex']
    
    # Common masculine patterns
    masculine_patterns = ['ان', 'ين', 'ون']
    if any(arabic_name.endswith(p) for p in masculine_patterns):
        return declared_gender in ['male', 'unisex']
    
    return True  # If unclear, allow but flag for review
```

---

## 📊 Improved Database Schema

### Keep it simple but add caching

```python
class NameSuggestion(Base):
    __tablename__ = "name_suggestions"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey("user_sessions.id"))
    
    # Name data
    name_arabic = Column(String, nullable=False)
    name_transliteration = Column(String)
    name_meaning = Column(Text)
    gender = Column(String)
    
    # Quranic connection
    derived_from = Column(String)  # The specific Quranic word
    quranic_root = Column(String)  # The trilateral root
    verse_references = Column(JSON)
    explanation = Column(Text)
    
    # LLM metadata
    confidence = Column(String)  # 'high', 'medium', 'low'
    name_type = Column(String)  # 'traditional', 'modern', 'rare'
    source_query = Column(Text)  # Original user query for caching
    
    # Validation
    is_validated = Column(Boolean, default=False)
    validation_passed = Column(Boolean)
    validation_notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class QueryCache(Base):
    """Cache LLM responses for identical queries"""
    __tablename__ = "query_cache"
    
    id = Column(Integer, primary_key=True)
    query_text = Column(String, unique=True, index=True)
    gender_filter = Column(String)
    quranic_words_hash = Column(String)  # Hash of input words
    
    llm_response = Column(JSON)  # Cached response
    suggestion_ids = Column(JSON)  # Array of generated suggestion IDs
    
    hit_count = Column(Integer, default=0)
    last_used = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## 🔄 Enhanced API Flow with Caching

```python
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Smart flow with caching and validation
    """
    
    # 1. Check cache first
    cache_key = generate_cache_key(request.message, request.gender)
    cached = check_query_cache(db, cache_key)
    
    if cached and is_cache_valid(cached):
        return build_response_from_cache(cached)
    
    # 2. Vector search (your existing logic)
    quranic_words = get_similar_words(
        db=db,
        query=request.message,
        limit=20
    )
    
    # 3. Get user preferences
    preferences = get_user_preferences(db, request.session_id)
    
    # 4. Build strong prompt
    prompt = build_prompt(
        query=request.message,
        quranic_words=quranic_words,
        preferences=preferences,
        gender=request.context.get('gender') if request.context else None
    )
    
    # 5. Call LLM
    try:
        llm_response = await call_llm_with_retry(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.3  # Lower temperature for more consistent filtering
        )
        
        # 6. Parse and validate
        suggestions_raw = parse_llm_response(llm_response)
        suggestions_validated = validate_llm_suggestions(suggestions_raw)
        
        # 7. Save to database
        saved_suggestions = []
        for suggestion in suggestions_validated:
            db_suggestion = NameSuggestion(
                session_id=request.session_id,
                source_query=request.message,
                **suggestion
            )
            db.add(db_suggestion)
            db.flush()
            saved_suggestions.append(db_suggestion)
        
        # 8. Cache the result
        cache_response(db, cache_key, saved_suggestions)
        
        db.commit()
        
        # 9. Return response
        return ChatResponse(
            message=create_response_message(saved_suggestions),
            suggestions=saved_suggestions,
            root_words=quranic_words[:10]
        )
        
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        # Fallback: return proper nouns from your data
        return fallback_response(db, quranic_words)


async def call_llm_with_retry(system_prompt: str, user_prompt: str, temperature: float):
    """Call LLM with retries and fallback"""
    
    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model="gpt-4o",  # Use GPT-4o for better Arabic understanding
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                response_format={"type": "json_object"},
                timeout=10
            )
            return response.choices[0].message.content
            
        except Exception as e:
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff


def fallback_response(db: Session, quranic_words: List) -> ChatResponse:
    """
    Fallback if LLM fails: return actual proper nouns from Quran
    """
    proper_nouns = [
        word for word in quranic_words 
        if word.category and 'Proper noun' in word.category
    ]
    
    # Create minimal suggestions from proper nouns
    suggestions = []
    for word in proper_nouns[:5]:
        suggestion = NameSuggestion(
            name_arabic=word.arabic_word,
            name_transliteration=word.transliteration,
            name_meaning=word.english_text,
            gender='unisex',
            derived_from=word.arabic_word,
            verse_references=[word.verse_reference],
            explanation=f"This is a name that appears in the Quran",
            confidence='high',
            source_query='fallback'
        )
        suggestions.append(suggestion)
    
    return ChatResponse(
        message="Here are some names from the Quran:",
        suggestions=suggestions,
        root_words=quranic_words[:10]
    )
```

---

## 🎨 Enhanced Frontend: Show LLM Confidence

```javascript
function createNameCard(suggestion) {
    const confidenceEmoji = {
        'high': '✅',
        'medium': '⚠️',
        'low': '❓'
    };
    
    const card = document.createElement('div');
    card.className = `name-card confidence-${suggestion.confidence}`;
    
    card.innerHTML = `
        <div class="name-header">
            <div class="name-arabic">${suggestion.name_arabic}</div>
            <div class="name-trans">${suggestion.name_transliteration}</div>
            <span class="confidence-badge" title="Confidence: ${suggestion.confidence}">
                ${confidenceEmoji[suggestion.confidence]}
            </span>
        </div>
        
        <div class="name-details">
            <p><strong>Meaning:</strong> ${suggestion.name_meaning}</p>
            <p><strong>Gender:</strong> ${suggestion.gender}</p>
            <p><strong>Root:</strong> ${suggestion.quranic_root || suggestion.derived_from}</p>
            <p><strong>Type:</strong> ${suggestion.name_type}</p>
            <p><strong>Verses:</strong> ${suggestion.verse_references.join(', ')}</p>
        </div>
        
        <div class="name-explanation">
            ${suggestion.explanation}
        </div>
        
        <div class="name-actions">
            <button class="btn-like" onclick="setPreference(${suggestion.id}, 'like')">
                👍 Like
            </button>
            <button class="btn-dislike" onclick="setPreference(${suggestion.id}, 'dislike')">
                👎 Dislike
            </button>
            <button class="btn-report" onclick="reportName(${suggestion.id})">
                🚩 Report Issue
            </button>
        </div>
    `;
    
    return card;
}

// Allow users to report inappropriate suggestions
async function reportName(suggestionId) {
    const reason = prompt('What is the issue with this name?');
    if (!reason) return;
    
    await fetch('/api/report-suggestion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            suggestion_id: suggestionId,
            reason: reason
        })
    });
    
    alert('Thank you for the feedback. This will help improve our suggestions.');
}
```

---

## 🔍 Monitoring & Continuous Improvement

```python
class SuggestionReport(Base):
    """Track user reports of inappropriate suggestions"""
    __tablename__ = "suggestion_reports"
    
    id = Column(Integer, primary_key=True)
    suggestion_id = Column(Integer, ForeignKey("name_suggestions.id"))
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    suggestion = relationship("NameSuggestion")


@app.post("/api/report-suggestion")
async def report_suggestion(
    suggestion_id: int,
    reason: str,
    db: Session = Depends(get_db)
):
    """Allow users to report inappropriate suggestions"""
    
    report = SuggestionReport(
        suggestion_id=suggestion_id,
        reason=reason
    )
    db.add(report)
    
    # Mark suggestion for review
    suggestion = db.query(NameSuggestion).get(suggestion_id)
    suggestion.validation_passed = False
    suggestion.validation_notes = f"User reported: {reason}"
    
    db.commit()
    
    return {"status": "reported"}


# Admin endpoint to review reports
@app.get("/api/admin/reported-suggestions")
async def get_reported_suggestions(db: Session = Depends(get_db)):
    """Get all reported suggestions for review"""
    
    reports = db.query(SuggestionReport).join(NameSuggestion).filter(
        NameSuggestion.validation_passed == False
    ).all()
    
    return reports


# Analyze which types of suggestions get reported
def analyze_suggestion_quality(db: Session):
    """
    Periodic analysis to improve prompts
    """
    
    # Get suggestions with high dislike rate
    problem_suggestions = db.query(
        NameSuggestion,
        func.count(NamePreference.id).label('dislike_count')
    ).join(NamePreference).filter(
        NamePreference.preference == 'dislike'
    ).group_by(NameSuggestion.id).having(
        func.count(NamePreference.id) > 3
    ).all()
    
    # Analyze patterns
    patterns = {
        'derived_from_verbs': [],
        'wrong_gender': [],
        'unclear_meaning': []
    }
    
    for suggestion, count in problem_suggestions:
        # Check if derived from verb category
        source_word = db.query(Word).filter(
            Word.arabic_word == suggestion.derived_from
        ).first()
        
        if source_word and 'verb' in source_word.category.lower():
            patterns['derived_from_verbs'].append(suggestion)
    
    return patterns
```

---

## 📈 Iterative Prompt Improvement

```python
class PromptVersion(Base):
    """Track different prompt versions and their performance"""
    __tablename__ = "prompt_versions"
    
    id = Column(Integer, primary_key=True)
    version = Column(String, unique=True)
    system_prompt = Column(Text)
    user_prompt_template = Column(Text)
    
    # Metrics
    suggestions_generated = Column(Integer, default=0)
    suggestions_liked = Column(Integer, default=0)
    suggestions_disliked = Column(Integer, default=0)
    suggestions_reported = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# A/B test different prompts
def get_active_prompt(db: Session, test_group: str = None):
    """
    Get active prompt, possibly for A/B testing
    """
    
    if test_group == 'experimental':
        prompt = db.query(PromptVersion).filter(
            PromptVersion.version == 'experimental_v2'
        ).first()
    else:
        prompt = db.query(PromptVersion).filter(
            PromptVersion.is_active == True
        ).first()
    
    return prompt or get_default_prompt()
```

---

## 🎯 Key Success Factors

### 1. **Strong System Prompt**
- Explicitly list what NOT to suggest
- Provide validation checklist
- Demand JSON output only
- Set temperature low (0.3)

### 2. **Post-LLM Validation**
- Check against forbidden names
- Validate gender markers
- Verify Arabic script
- Check sentiment

### 3. **Caching Strategy**
- Cache identical queries
- Cache validated suggestions
- Reduce LLM costs
- Faster responses

### 4. **User Feedback Loop**
- Report button on every suggestion
- Track like/dislike patterns
- Analyze problematic suggestions
- Iterate on prompts

### 5. **Fallback Mechanisms**
- If LLM fails, show proper nouns
- If LLM returns invalid JSON, retry
- If no valid suggestions, explain why
- Always have a working response

---

## 💰 Cost Optimization

```python
# Caching saves money
CACHE_STRATEGY = {
    'ttl': 7 * 24 * 3600,  # 1 week
    'eviction': 'lru',
    'max_size': 10000
}

# Batching reduces calls
BATCH_STRATEGY = {
    'process_roots': 5,  # 5 roots per call
    'max_suggestions_per_root': 2,
    'total_target': 10  # Total suggestions to show
}

# Estimated costs
COSTS = {
    'gpt-4o': {
        'input': 0.0025 / 1000,   # per token
        'output': 0.01 / 1000,    # per token
        'avg_input': 2000,        # tokens
        'avg_output': 800,        # tokens
        'cost_per_request': 0.013  # ~$0.013
    },
    'cache_hit_rate': 0.4,  # 40% of queries are cached
    'effective_cost': 0.008  # $0.008 per request with caching
}

# For 1000 users:
# - 5 searches each = 5000 searches
# - With 40% cache hit = 3000 LLM calls
# - 3000 × $0.013 = $39/month
```

---

## ✅ This Approach Works If:

1. **You're using GPT-4o** (or Claude 3.5 Sonnet)
   - Older models won't filter well
   - Arabic understanding is critical

2. **You implement all validation layers**
   - System prompt + post-processing + user reports
   - One layer isn't enough

3. **You iterate on prompts**
   - Monitor what gets reported
   - Refine constraints
   - A/B test improvements

4. **You cache aggressively**
   - Same queries are common
   - Reduces cost by 40-60%

5. **You're transparent with users**
   - Show confidence levels
   - Allow reporting
   - Explain it's AI-assisted

---

## 🚀 Implementation Order

```
Week 1: Core with Strong Prompts
- Implement robust system prompt
- Add post-processing validation
- Build basic caching
- Test with various queries

Week 2: User Feedback
- Add report functionality
- Implement preference tracking
- Build admin review panel
- Monitor suggestion quality

Week 3: Optimization
- Analyze reported suggestions
- Refine prompts based on data
- Improve caching strategy
- A/B test prompt variations

Week 4: Polish
- Better error handling
- Fallback mechanisms
- UI improvements
- Documentation
```

This approach respects your desire to not manually curate while adding necessary safety rails through intelligent prompting and validation.