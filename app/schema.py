from pydantic import BaseModel
from typing import List


class WordOccurrence(BaseModel):
    arabic_word: str
    transliteration: str
    english_text: str
    verse_reference: str
    quran_verse: str | None = None
    morphology_url: str | None = None
    similarity_score: float  # Match percentage for this specific word

    class Config:
        from_attributes = True

class SearchResult(BaseModel):
    sequence: str
    category: str
    letter: str
    occurrences: list[WordOccurrence]  # All occurrences of this root word, sorted by similarity
    best_match_score: float  # Highest similarity score among occurrences

    class Config:
        from_attributes = True


# --- Pydantic Models for MCP Tools ---

class RootInfo(BaseModel):
    sequence: str
    transliteration: str
    category: str
    english_text: str
    best_match_score: float


# --- Pydantic Models for Chat Endpoint ---

class NameSuggestion(BaseModel):
    name: str
    meaning: str
    gender: str | None = None
    root: str | None = None

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    query: str
    session_token: str | None = None


class RootWordInfo(BaseModel):
    sequence: str
    transliteration: str
    category: str
    english_text: str

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    session_token: str
    suggestions: list[NameSuggestion]
    unsuccessful_roots: list[RootWordInfo] = []


class AllRootWordsResponse(BaseModel):
    root_words: List[RootWordInfo]
    total: int


class GenerateNamesRequest(BaseModel):
    root_words: List[RootWordInfo]
