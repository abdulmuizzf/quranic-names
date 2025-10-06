import os
import pandas as pd
from sentence_transformers import SentenceTransformer
import psycopg2
import numpy as np
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# --- Model Configuration ---
MODEL_NAME = "thenlper/gte-large"
VECTOR_DIMENSION = 1024


def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        return conn
    except psycopg2.OperationalError as e:
        print(f"❌ Could not connect to the database: {e}")
        return None


def ingest_core_data(conn, df):
    """
    Ingests the core textual data (categories, letters, sequences, words)
    into the database, avoiding duplicates.
    """
    print("➡️ Step 1: Ingesting core data (words, sequences, etc.)...")
    with conn.cursor() as cur:
        # Get all existing verse references to avoid re-inserting words
        cur.execute("SELECT verse_reference FROM words")
        existing_verses = {row[0] for row in cur.fetchall()}

        new_words_df = df[~df["verse_reference"].isin(existing_verses)]

        if new_words_df.empty:
            print("   Core data is already up-to-date.")
            return

        print(f"   Found {len(new_words_df)} new words to add.")

        # Use dictionaries to cache foreign keys and avoid repeated lookups
        letter_ids, category_ids, sequence_ids = {}, {}, {}

        for _, row in new_words_df.iterrows():
            # Categories
            category_name = row["category"]
            if category_name not in category_ids:
                cur.execute(
                    "INSERT INTO categories (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id;",
                    (category_name,),
                )
                category_ids[category_name] = cur.fetchone()[0]

            # Letters
            letter_char = row["letter"]
            if letter_char not in letter_ids:
                cur.execute(
                    "INSERT INTO letters (letter) VALUES (%s) ON CONFLICT (letter) DO UPDATE SET letter=EXCLUDED.letter RETURNING id;",
                    (letter_char,),
                )
                letter_ids[letter_char] = cur.fetchone()[0]

            # Sequences
            sequence_text = row["sequence"]
            sequence_key = (sequence_text, letter_ids[letter_char])
            if sequence_key not in sequence_ids:
                cur.execute(
                    "INSERT INTO sequences (sequence, morphology_url, letter_id, category_id) VALUES (%s, %s, %s, %s) ON CONFLICT (sequence, letter_id) DO UPDATE SET sequence=EXCLUDED.sequence RETURNING id;",
                    (sequence_text, row["morphology_url"], letter_ids[letter_char], category_ids[category_name]),
                )
                sequence_ids[sequence_key] = cur.fetchone()[0]

            # Words
            cur.execute(
                "INSERT INTO words (arabic_word, transliteration, english_text, verse_reference, quran_verse, sequence_id) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (verse_reference) DO NOTHING;",
                (
                    row["arabic_word"],
                    row["transliteration"],
                    row["english_text"],
                    row["verse_reference"],
                    row["quran_verse"],
                    sequence_ids[sequence_key],
                ),
            )
    conn.commit()
    print(f"✅ Successfully ingested {len(new_words_df)} new words.")


def ingest_embeddings(conn, df):
    """
    Generates and ingests embeddings for words that don't have them for the current model.
    """
    print("\n➡️ Step 2: Ingesting embeddings...")
    with conn.cursor() as cur:
        # Get or create the embedding model entry
        cur.execute(
            "INSERT INTO embedding_models (name, dimension) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id;",
            (MODEL_NAME, VECTOR_DIMENSION),
        )
        model_id = cur.fetchone()[0]
        print(f"   Using model '{MODEL_NAME}' (ID: {model_id}).")

        # Find all word IDs that already have an embedding for this model
        cur.execute("SELECT word_id FROM embeddings WHERE model_id = %s", (model_id,))
        words_with_embedding = {row[0] for row in cur.fetchall()}
        print(f"   Found {len(words_with_embedding)} words that already have an embedding for this model.")

        # Get all words from the DB, mapping verse_reference to word_id
        cur.execute("SELECT id, verse_reference FROM words")
        all_words_map = {row[1]: row[0] for row in cur.fetchall()}

        # Filter the dataframe to find words that need an embedding
        words_to_embed_df = df[df["verse_reference"].isin(all_words_map.keys())]
        # Further filter out words that already have an embedding for this model
        words_to_embed_df = words_to_embed_df[
            ~words_to_embed_df["verse_reference"].map(all_words_map).isin(words_with_embedding)
        ]

        if words_to_embed_df.empty:
            print("   All words are already embedded for this model.")
            return

        print(f"   Found {len(words_to_embed_df)} words that need a new embedding.")

        # Generate embeddings for the filtered list
        print("   Loading sentence transformer model...")
        model = SentenceTransformer(MODEL_NAME)
        print("   Generating embeddings (this may take a while)...")
        embeddings = model.encode(words_to_embed_df["english_text"].tolist(), show_progress_bar=True)

        # Insert new embeddings
        print("   Inserting new embeddings into the database...")
        for i, row in words_to_embed_df.iterrows():
            word_id = all_words_map[row["verse_reference"]]
            embedding_vector = np.array(embeddings[i])
            cur.execute(
                "INSERT INTO embeddings (word_id, model_id, embedding) VALUES (%s, %s, %s)",
                (word_id, model_id, embedding_vector),
            )
    conn.commit()
    print(f"✅ Successfully ingested {len(words_to_embed_df)} new embeddings.")


if __name__ == "__main__":
    print("--- Starting Data Ingestion Script ---")

    try:
        main_df = pd.read_csv("data/quran_words.csv").where(pd.notnull, None)
        # Perform a single, upfront drop of rows with critical missing data
        main_df.dropna(subset=["english_text", "sequence", "letter", "category", "verse_reference"], inplace=True)
    except FileNotFoundError:
        print("❌ Error: 'data/quran_words.csv' not found. Please run the scraper first.")
        exit()

    connection = get_db_connection()
    if connection:
        ingest_core_data(connection, main_df)
        ingest_embeddings(connection, main_df)
        connection.close()
        print("\n--- Ingestion Complete ---")
