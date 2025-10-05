from sqlalchemy.orm import Session
import numpy as np
from app import models


def get_similar_words(db: Session, query_embedding: np.ndarray, limit: int = 10):
    """
    Queries the database to find the most similar words based on cosine distance.
    """
    # We join the tables to get all the info we need in one query
    similar_words = (
        db.query(
            models.Word.english_text,
            models.Sequence.sequence,
            models.Category.name.label("category"),
            models.Letter.letter,
        )
        .join(models.Sequence, models.Word.sequence_id == models.Sequence.id)
        .join(models.Category, models.Sequence.category_id == models.Category.id)
        .join(models.Letter, models.Sequence.letter_id == models.Letter.id)
        .order_by(models.Word.embedding.cosine_distance(query_embedding))
        .limit(limit)
        .all()
    )

    return similar_words
