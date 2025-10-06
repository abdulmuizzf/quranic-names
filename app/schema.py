from pydantic import BaseModel


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
