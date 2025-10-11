from sqlalchemy.orm import Session
import numpy as np
from app import models


def get_similar_words(db: Session, query_embedding: np.ndarray, limit: int = 10, min_similarity: float = 0):
    """
    Find root word sequences with embeddings similar to the query using SQLAlchemy ORM.
    Returns list of dictionaries with sequence info and word occurrences.
    """
    # Convert minimum similarity percentage to maximum distance for cosine similarity
    max_distance = 1 - (min_similarity / 100)

    # Define the distance function using pgvector's cosine_distance
    distance = models.Embedding.embedding.cosine_distance(query_embedding).label("distance")

    # Build the query using the SQLAlchemy ORM
    results = (
        db.query(
            models.Word,
            models.Sequence.sequence,
            models.Category.name,
            models.Letter.letter,
            distance,
        )
        .join(models.Embedding, models.Word.id == models.Embedding.word_id)
        .join(models.Sequence, models.Word.sequence_id == models.Sequence.id)
        .join(models.Category, models.Sequence.category_id == models.Category.id)
        .join(models.Letter, models.Sequence.letter_id == models.Letter.id)
        .filter(distance <= max_distance)
        .order_by(distance)
        .limit(limit)
        .all()
    )

    # Group results by sequence
    sequence_groups = {}
    for result in results:
        word, sequence, category, letter, distance = result
        if sequence not in sequence_groups:
            sequence_groups[sequence] = {
                'sequence': sequence,
                'category': category,
                'letter': letter,
                'occurrences': [],
                'best_match_score': 0  # Will be updated as we process words
            }
        # Convert distance to similarity percentage (1 - distance)
        similarity = max(0, min(100, (1 - distance) * 100))
        similarity = round(similarity, 2)
        # Update best match score if this word has higher similarity
        sequence_groups[sequence]['best_match_score'] = max(
            sequence_groups[sequence]['best_match_score'],
            similarity
        )
        # Add word occurrence with its similarity score
        sequence_groups[sequence]['occurrences'].append({
            'arabic_word': word.arabic_word,
            'transliteration': word.transliteration,
            'english_text': word.english_text,
            'verse_reference': word.verse_reference,
            'quran_verse': word.quran_verse,
            # Accessing morphology_url through the relationship
            'morphology_url': word.sequence_relation.morphology_url,
            'similarity_score': similarity
        })
    # Sort occurrences by similarity score within each sequence
    for group in sequence_groups.values():
        group['occurrences'].sort(key=lambda x: x['similarity_score'], reverse=True)
    # Convert to list and sort by best match score
    result_list = list(sequence_groups.values())
    result_list.sort(key=lambda x: x['best_match_score'], reverse=True)
    return result_list
