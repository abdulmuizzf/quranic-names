import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from your_database_module import get_db_connection  # Adjust the import based on your project structure

# Define constants
MODEL_NAME = 'all-MiniLM-L6-v2'  # Example model name, adjust as needed
VECTOR_DIMENSION = 384  # This should match the dimension of the embeddings from your model

def setup_schema(conn):
    """Creates the normalized table structure and index if they don't exist."""
    with conn.cursor() as cur:
        print("--- Ensuring database schema is ready ---")

        # Check for tables and create if they don't exist
        cur.execute("CREATE TABLE IF NOT EXISTS categories (...);") # Simplified for brevity
        cur.execute("CREATE TABLE IF NOT EXISTS letters (...);")
        cur.execute("CREATE TABLE IF NOT EXISTS sequences (...);")
        cur.execute("CREATE TABLE IF NOT EXISTS words (...);")

        print("   Creating 'categories' table if not exists...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            );
        """)

        print("   Creating 'letters' table if not exists...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS letters (
                id SERIAL PRIMARY KEY,
                letter TEXT UNIQUE NOT NULL
            );
        """)

        print("   Creating 'sequences' table if not exists...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sequences (
                id SERIAL PRIMARY KEY,
                sequence TEXT NOT NULL,
                morphology_url TEXT,
                letter_id INTEGER REFERENCES letters(id),
                category_id INTEGER REFERENCES categories(id),
                UNIQUE (sequence, letter_id)
            );
        """)

        print("   Creating 'words' table if not exists...")
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS words (
                id SERIAL PRIMARY KEY,
                arabic_word TEXT,
                transliteration TEXT,
                english_text TEXT,
                verse_reference TEXT UNIQUE,
                quran_verse TEXT,
                sequence_id INTEGER REFERENCES sequences(id),
                embedding VECTOR({VECTOR_DIMENSION})
            );
        """)
        
        # Create index if it doesn't exist
        print("   Creating vector index if not exists...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS hnsw_index ON words 
            USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
        """)

    conn.commit()
    print("✅ Schema is ready.")


def ingest_data(conn):
    """Reads CSV, finds new data, generates embeddings, and inserts it."""
    print("\n--- Starting Data Ingestion ---")
    
    # Step 1: Get existing verse references from the DB
    print("➡️ Step 1: Checking for already ingested data...")
    with conn.cursor() as cur:
        cur.execute("SELECT verse_reference FROM words;")
        existing_verses = {row[0] for row in cur.fetchall()}
    print(f"   Found {len(existing_verses)} existing words in the database.")

    # Step 2: Read CSV and filter for new data
    print("➡️ Step 2: Reading CSV data...")
    try:
        df = pd.read_csv('quran_words.csv').where(pd.notnull, None)
        df.dropna(subset=['english_text', 'sequence', 'letter', 'category', 'verse_reference'], inplace=True)
        
        # Filter out rows that are already in the database
        new_data_df = df[~df['verse_reference'].isin(existing_verses)]
        
        if new_data_df.empty:
            print("   No new data to ingest. Database is already up-to-date.")
            print("--- Ingestion Complete ---")
            return
            
        print(f"   Found {len(new_data_df)} new rows to ingest.")

    except FileNotFoundError:
        print("❌ Error: quran_words.csv not found.")
        return

    # Step 3: Generate embeddings for new data only
    print(f"➡️ Step 3: Loading sentence transformer model '{MODEL_NAME}'...")
    model = SentenceTransformer(MODEL_NAME)

    print("➡️ Step 4: Generating embeddings for new data...")
    embeddings = model.encode(new_data_df['english_text'].tolist(), show_progress_bar=True)
    new_data_df['embedding'] = list(embeddings)

    # Step 5: Ingest the new data
    print("➡️ Step 5: Populating database with new data...")
    with conn.cursor() as cur:
        # Use dictionaries to cache foreign keys and avoid repeated lookups
        letter_ids = {}
        category_ids = {}
        sequence_ids = {}

        for _, row in new_data_df.iterrows():
            # --- Categories ---
            category_name = row['category']
            if category_name not in category_ids:
                cur.execute("INSERT INTO categories (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id;", (category_name,))
                category_ids[category_name] = cur.fetchone()[0]
            category_id = category_ids[category_name]

            # --- Letters ---
            letter_char = row['letter']
            if letter_char not in letter_ids:
                cur.execute("INSERT INTO letters (letter) VALUES (%s) ON CONFLICT (letter) DO UPDATE SET letter=EXCLUDED.letter RETURNING id;", (letter_char,))
                letter_ids[letter_char] = cur.fetchone()[0]
            letter_id = letter_ids[letter_char]

            # --- Sequences ---
            sequence_text = row['sequence']
            sequence_key = (sequence_text, letter_id)
            if sequence_key not in sequence_ids:
                cur.execute(
                    """
                    INSERT INTO sequences (sequence, morphology_url, letter_id, category_id)
                    VALUES (%s, %s, %s, %s) ON CONFLICT (sequence, letter_id) DO UPDATE SET sequence=EXCLUDED.sequence RETURNING id;
                    """,
                    (sequence_text, row['morphology_url'], letter_id, category_id)
                )
                sequence_ids[sequence_key] = cur.fetchone()[0]
            sequence_id = sequence_ids[sequence_key]

            # --- Words ---
            cur.execute(
                """
                INSERT INTO words (
                    arabic_word, transliteration, english_text, verse_reference,
                    quran_verse, sequence_id, embedding
                ) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (verse_reference) DO NOTHING;
                """,
                (
                    row['arabic_word'], row['transliteration'], row['english_text'],
                    row['verse_reference'], row['quran_verse'], sequence_id,
                    np.array(row['embedding'])
                )
            )
    conn.commit()
    print(f"✅ Successfully ingested {len(new_data_df)} new words.")
    print("--- Ingestion Complete ---")


if __name__ == "__main__":
    conn = get_db_connection()
    if conn:
        setup_schema(conn)
        ingest_data(conn)
        conn.close()