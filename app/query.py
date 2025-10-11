from sqlalchemy.orm import Session
import numpy as np
from app import models


from sqlalchemy import text

def get_similar_words(db: Session, query_embedding: np.ndarray, limit: int = 10, min_similarity: float = 0):
    """
    Find root word sequences with embeddings similar to the query.
    Returns list of dictionaries with sequence info and word occurrences.
    """
    # Convert numpy array to list for database query
    query_vector = query_embedding.tolist()

    # Convert minimum similarity percentage to maximum distance
    # similarity = 1 - distance, so max_distance = 1 - min_similarity/100
    max_distance = 1 - (min_similarity / 100)

    # Query using pgvector's cosine similarity operator (<->)
    sql = text("""
        SELECT 
            w.*,
            seq.sequence,
            cat.name as category,
            l.letter,
            (e.embedding <=> :query_vector::vector) as distance
        FROM words w
        JOIN sequences seq ON w.sequence_id = seq.id
        JOIN letters l ON seq.letter_id = l.id
        JOIN categories cat ON seq.category_id = cat.id
        JOIN embeddings e ON e.word_id = w.id
        WHERE distance <= :max_distance
        ORDER BY distance ASC
        LIMIT :limit
    """)
    
    results = db.execute(
        sql,
        {
            "query_vector": query_vector,
            "max_distance": max_distance,
            "limit": limit
        }
    ).fetchall()

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
