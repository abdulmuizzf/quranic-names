import os
import pickle
import psycopg2
import numpy as np
from dotenv import load_dotenv
from tqdm import tqdm

# --- Load Environment Variables ---
load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"❌ Could not connect to the database: {e}")
        return None

def save_embeddings_to_db():
    """Load embeddings from pickle and save to database"""
    print("--- Starting Database Import ---")

    if not os.path.exists("data/embeddings.pkl"):
        print("❌ No embeddings file found. Run generate_embeddings.py first.")
        return

    try:
        # Load embeddings from pickle
        print("Loading embeddings from pickle file...")
        with open("data/embeddings.pkl", "rb") as f:
            data = pickle.load(f)
        
        embeddings = data["embeddings"]
        verse_refs = data["verse_references"]
        model_name = data["model_name"]
        dimension = data["dimension"]

        print(f"Loaded {len(embeddings)} embeddings")

        # Connect to database
        conn = get_db_connection()
        if not conn:
            return

        with conn.cursor() as cur:
            # Get or create the embedding model entry
            cur.execute(
                """
                INSERT INTO embedding_models (name, dimension)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name
                RETURNING id;
                """,
                (model_name, dimension)
            )
            model_id = cur.fetchone()[0]

            # Get mapping of verse_reference to word_id
            cur.execute("SELECT id, verse_reference FROM words")
            word_id_map = {row[1]: row[0] for row in cur}

            # Get existing embeddings to avoid duplicates
            cur.execute(
                "SELECT w.verse_reference FROM embeddings e JOIN words w ON e.word_id = w.id WHERE e.model_id = %s",
                (model_id,)
            )
            existing_refs = {row[0] for row in cur.fetchall()}

            # Prepare data for insertion
            print("Preparing data for database insertion...")
            to_insert = []
            for verse_ref, embedding in zip(verse_refs, embeddings):
                if verse_ref not in existing_refs and verse_ref in word_id_map:
                    to_insert.append((
                        word_id_map[verse_ref],
                        model_id,
                        embedding.astype(np.float32).tolist()
                    ))

            if not to_insert:
                print("✅ All embeddings are already in the database!")
                return

            # Insert in batches
            batch_size = 100
            print(f"Inserting {len(to_insert)} embeddings into database...")
            for i in tqdm(range(0, len(to_insert), batch_size), desc="Saving to database"):
                batch = to_insert[i:i + batch_size]
                cur.executemany(
                    """
                    INSERT INTO embeddings (word_id, model_id, embedding)
                    VALUES (%s, %s, %s::vector)
                    ON CONFLICT (word_id, model_id) DO NOTHING
                    """,
                    batch
                )
                conn.commit()

        print("✅ Successfully saved all embeddings to database")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    save_embeddings_to_db()