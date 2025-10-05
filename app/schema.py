from pydantic import BaseModel


class SearchResult(BaseModel):
    sequence: str
    category: str
    letter: str
    # This field shows an example of an English meaning that caused the match
    sample_meaning: str

    class Config:
        from_attributes = True
