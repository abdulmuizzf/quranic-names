import os
import pandas as pd
from sentence_transformers import SentenceTransformer
import psycopg2
import psycopg2.extras
import numpy as np
from dotenv import load_dotenv
from collections import defaultdict

# --- Load Environment Variables ---
load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# --- Model Configuration ---
# Using the model you selected after testing
MODEL_NAME = "BAAI/bge-small-en-v1.5"
# BGE models have a dimension of 384
VECTOR_DIMENSION = 384


def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        return conn
    except psycopg2.OperationalError as e:
        print(f"❌ Could not connect to the database.")
        print(f"   Please ensure PostgreSQL is running and your .env settings are correct.")
        print(f"   Error: {e}")
        return None


def create_tables(conn):
    """Creates the normalized table structure."""
    with conn.cursor() as cur:
        print("--- Setting up database schema ---")

        # Drop tables in reverse order of dependency to avoid errors
        print("   Dropping existing tables (if any)...")
        cur.execute("DROP TABLE IF EXISTS words, sequences, letters, categories CASCADE;")

        print("   Creating 'categories' table...")
        cur.execute("""
            CREATE TABLE categories (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            );
        """)

        print("   Creating 'letters' table...")
        cur.execute("""
            CREATE TABLE letters (
                id SERIAL PRIMARY KEY,
                letter TEXT UNIQUE NOT NULL
            );
        """)

        print("   Creating 'sequences' table...")
        cur.execute("""
            CREATE TABLE sequences (
                id SERIAL PRIMARY KEY,
                sequence TEXT NOT NULL,
                morphology_url TEXT,
                letter_id INTEGER REFERENCES letters(id),
                category_id INTEGER REFERENCES categories(id),
                UNIQUE (sequence, letter_id)
            );
        """)

        print("   Creating 'words' table...")
        cur.execute(f"""
            CREATE TABLE words (
                id SERIAL PRIMARY KEY,
                arabic_word TEXT,
                transliteration TEXT,
                english_text TEXT,
                verse_reference TEXT,
                quran_verse TEXT,
                sequence_id INTEGER REFERENCES sequences(id),
                embedding VECTOR({VECTOR_DIMENSION})
            );
        """)
    conn.commit()
    print("✅ Schema is ready.")


def ingest_data(conn):
    """Reads CSV, generates embeddings, and inserts into the normalized tables."""
    print("\n--- Starting Data Ingestion ---")
    print("➡️ Step 1: Reading CSV data...")
    try:
        df = pd.read_csv("quran_words.csv").where(pd.notnull, None)
        df.dropna(subset=["english_text", "sequence", "letter", "category"], inplace=True)
        print(f"   Found {len(df)} valid rows to process.")
    except FileNotFoundError:
        print("❌ Error: quran_words.csv not found.")
        return

    print(f"➡️ Step 2: Loading sentence transformer model '{MODEL_NAME}'...")
    model = SentenceTransformer(MODEL_NAME)

    print("➡️ Step 3: Generating embeddings...")
    embeddings = model.encode(df["english_text"].tolist(), show_progress_bar=True)
    df["embedding"] = list(embeddings)

    print("➡️ Step 4: Populating database tables...")
    with conn.cursor() as cur:
        # Use dictionaries to cache foreign keys and avoid repeated lookups
        letter_ids = {}
        category_ids = {}
        sequence_ids = {}

        for _, row in df.iterrows():
            # --- Categories ---
            category_name = row["category"]
            if category_name not in category_ids:
                cur.execute(
                    "INSERT INTO categories (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id;",
                    (category_name,),
                )
                category_ids[category_name] = cur.fetchone()[0]
            category_id = category_ids[category_name]

            # --- Letters ---
            letter_char = row["letter"]
            if letter_char not in letter_ids:
                cur.execute(
                    "INSERT INTO letters (letter) VALUES (%s) ON CONFLICT (letter) DO UPDATE SET letter=EXCLUDED.letter RETURNING id;",
                    (letter_char,),
                )
                letter_ids[letter_char] = cur.fetchone()[0]
            letter_id = letter_ids[letter_char]

            # --- Sequences ---
            sequence_text = row["sequence"]
            sequence_key = (sequence_text, letter_id)
            if sequence_key not in sequence_ids:
                cur.execute(
                    """
                    INSERT INTO sequences (sequence, morphology_url, letter_id, category_id)
                    VALUES (%s, %s, %s, %s) ON CONFLICT (sequence, letter_id) DO UPDATE SET sequence=EXCLUDED.sequence RETURNING id;
                    """,
                    (sequence_text, row["morphology_url"], letter_id, category_id),
                )
                sequence_ids[sequence_key] = cur.fetchone()[0]
            sequence_id = sequence_ids[sequence_key]

            # --- Words ---
            cur.execute(
                """
                INSERT INTO words (
                    arabic_word, transliteration, english_text, verse_reference,
                    quran_verse, sequence_id, embedding
                ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    row["arabic_word"],
                    row["transliteration"],
                    row["english_text"],
                    row["verse_reference"],
                    row["quran_verse"],
                    sequence_id,
                    np.array(row["embedding"]),
                ),
            )
    conn.commit()
    print(f"✅ Successfully ingested {len(df)} words.")


def create_index(conn):
    """Creates a high-performance index on the embedding column."""
    print("\n--- Creating Vector Index ---")
    with conn.cursor() as cur:
        # Check how many rows we have to determine the best lists value
        cur.execute("SELECT count(*) FROM words;")
        num_rows = cur.fetchone()[0]

        # These are good defaults for HNSW index creation
        # lists should be ~rows/1000 for up to 1M rows
        lists = max(10, min(1000, num_rows // 1000))

        print(f"   Using {lists} lists for the HNSW index on {num_rows} words.")
        print("   This may take a few minutes...")

        # Using cosine distance as it's good for semantic similarity
        cur.execute(
            f"CREATE INDEX ON words USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
        )

    conn.commit()
    print("✅ Index created successfully.")
    print("--- Database is Ready ---")


if __name__ == "__main__":
    conn = get_db_connection()
    if conn:
        create_tables(conn)
        ingest_data(conn)
        create_index(conn)
        conn.close()
