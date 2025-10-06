import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle
import os
from tqdm import tqdm

# --- Model Configuration ---
MODEL_NAME = "thenlper/gte-large"
VECTOR_DIMENSION = 1024
BATCH_SIZE = 32  # Smaller batch size to avoid memory issues

def generate_embeddings():
    """Generate embeddings and save to pickle file"""
    print("--- Starting Embeddings Generation ---")

    try:
        # Load the CSV file
        print("Loading CSV data...")
        df = pd.read_csv("data/quran_words.csv").where(pd.notnull, None)
        df.dropna(subset=["english_text"], inplace=True)
        
        # Check if embeddings file already exists
        if os.path.exists("data/embeddings.pkl"):
            print("⚠️ Embeddings file already exists. Loading existing embeddings...")
            with open("data/embeddings.pkl", "rb") as f:
                saved_data = pickle.load(f)
                existing_embeddings = saved_data["embeddings"]
                existing_refs = saved_data["verse_references"]
                
            # Find which verse references we still need to process
            all_refs = df["verse_reference"].tolist()
            refs_to_process = list(set(all_refs) - set(existing_refs))
            if not refs_to_process:
                print("✅ All embeddings are already generated!")
                return
            
            df = df[df["verse_reference"].isin(refs_to_process)]
        else:
            existing_embeddings = []
            existing_refs = []

        print(f"Generating embeddings for {len(df)} texts...")
        
        # Load the model
        print("Loading sentence transformer model...")
        model = SentenceTransformer(MODEL_NAME)
        
        # Generate embeddings in batches
        embeddings = []
        verse_refs = []
        
        for i in tqdm(range(0, len(df), BATCH_SIZE), desc="Generating embeddings"):
            batch_df = df.iloc[i:i + BATCH_SIZE]
            batch_embeddings = model.encode(
                batch_df["english_text"].tolist(),
                show_progress_bar=False
            )
            embeddings.extend(batch_embeddings)
            verse_refs.extend(batch_df["verse_reference"].tolist())

        # Combine with existing embeddings if any
        if existing_embeddings:
            embeddings = existing_embeddings + embeddings
            verse_refs = existing_refs + verse_refs

        # Save to pickle file
        print("\nSaving embeddings to pickle file...")
        with open("data/embeddings.pkl", "wb") as f:
            pickle.dump({
                "embeddings": embeddings,
                "verse_references": verse_refs,
                "model_name": MODEL_NAME,
                "dimension": VECTOR_DIMENSION
            }, f)
        
        print(f"✅ Successfully generated and saved {len(embeddings)} embeddings")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise

if __name__ == "__main__":
    generate_embeddings()