from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from app.database import engine
from app.models import Category, Sequence, Word

# Create a new session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def get_category_details_to_file():
    """
    Queries the database and saves details for each category with a non-zero
    sequence count to a text file.
    """
    output_filename = "category_details.txt"
    try:
        print("Fetching category details from the database...")
        
        # Get all categories with a count of their sequences
        categories_with_counts = (
            db.query(
                Category.name,
                func.count(Sequence.id).label("sequence_count")
            )
            .outerjoin(Sequence, Category.id == Sequence.category_id)
            .group_by(Category.name)
            .having(func.count(Sequence.id) > 0)  # Filter for categories with sequences
            .order_by(Category.name)
            .all()
        )

        if not categories_with_counts:
            print("No categories with associated sequences found.")
            return

        with open(output_filename, "w", encoding="utf-8") as f:
            f.write("--- Category Details ---\n")
            for cat_name, count in categories_with_counts:
                f.write(f"\nCategory: {cat_name}\n")
                f.write(f"  Sequence Count: {count}\n")

                # Fetch a few example words for the category
                example_words = (
                    db.query(Word.english_text)
                    .join(Sequence, Word.sequence_id == Sequence.id)
                    .join(Category, Sequence.category_id == Category.id)
                    .filter(Category.name == cat_name)
                    .distinct()
                    .limit(4)
                    .all()
                )
                
                if example_words:
                    f.write("  Examples:\n")
                    for (text,) in example_words:
                        f.write(f"    - {text}\n")
            
            f.write("\n------------------------\n")
        
        print(f"\nSuccessfully saved category details to '{output_filename}'")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()
        print("Database session closed.")

if __name__ == "__main__":
    get_category_details_to_file()
