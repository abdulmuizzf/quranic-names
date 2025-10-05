from sentence_transformers import SentenceTransformer, util
import numpy as np
import time
import spacy

# Try to load spaCy
try:
    nlp = spacy.load("en_core_web_lg")
    spacy_available = True
except:
    print("⚠️  spaCy en_core_web_lg not found. Install with: python -m spacy download en_core_web_lg\n")
    spacy_available = False

# Models to test (only worth exploring based on analysis)
MODELS = [
    ("BAAI/bge-small-en-v1.5", "BGE Small (384d)"),
    ("all-mpnet-base-v2", "MPNet Base (768d)"),
    ("nomic-ai/nomic-embed-text-v1.5", "Nomic Embed (768d)"),
    ("BAAI/bge-large-en-v1.5", "BGE Large (1024d)"),
    ("thenlper/gte-large", "GTE Large (1024d)"),
]

# Test data sets
ABSTRACT_QUERIES = [
    "justice and fairness",
    "divine mercy and compassion",
    "wisdom and insight",
    "courage and bravery",
    "loyalty and faithfulness",
    "peace and tranquility",
    "pride and arrogance",
    "envy and jealousy",
    "repentance and remorse",
    "certainty and conviction",
]

ABSTRACT_MEANINGS = [
    "equity, righteousness, impartial judgment",
    "forgiveness, kindness, clemency",
    "understanding, knowledge, discernment",
    "valor, boldness, fearlessness",
    "devotion, allegiance, steadfastness",
    "calmness, serenity, harmony",
    "haughtiness, conceit, self-importance",
    "covetousness, resentment, desiring others' possessions",
    "contrition, regret, turning back from sin",
    "assurance, firm belief, lack of doubt",
]

CONCRETE_QUERIES = [
    "a book for reading",
    "water and rain",
    "mountain and hill",
    "sun and moon",
    "tree with leaves",
    "hand and fingers",
    "house and dwelling",
    "sword and weapon",
    "food and eating",
    "path and road",
]

CONCRETE_MEANINGS = [
    "written text, scripture, pages bound together",
    "liquid, precipitation, moisture from sky",
    "elevated land, peak, high ground",
    "celestial bodies, day star and night orb",
    "plant with trunk, branches, foliage",
    "body part, palm, digits for grasping",
    "shelter, residence, home building",
    "blade, instrument for combat, armament",
    "nourishment, consumption, meals",
    "route, way, trail for travel",
]

MIXED_QUERIES = [
    "prayer and worship",
    "charity and giving",
    "fasting and abstaining",
    "travel and journey",
    "speaking and speech",
    "seeing and vision",
    "hearing and listening",
    "writing and recording",
    "fighting and battle",
    "building and construction",
]

MIXED_MEANINGS = [
    "devotion, supplication, ritual communication with divine",
    "almsgiving, donation, helping the needy",
    "self-restraint, going without food, spiritual discipline",
    "migration, movement, expedition",
    "utterance, declaration, verbal expression",
    "perceiving with eyes, observation, sight",
    "auditory perception, attentiveness to sound",
    "inscription, documentation, putting words to paper",
    "combat, warfare, armed conflict",
    "erecting, constructing, assembling structures",
]

# Wrong matches for testing separation
WRONG_MEANINGS = [
    "darkness, ignorance, confusion",
    "anger, wrath, punishment, vengeance",
    "foolishness, stupidity, lack of understanding",
]


def spacy_similarity(nlp, texts1, texts2):
    """Calculate pairwise similarities for spaCy"""
    docs1 = list(nlp.pipe(texts1))
    docs2 = list(nlp.pipe(texts2))

    similarities = np.zeros((len(docs1), len(docs2)))
    for i, doc1 in enumerate(docs1):
        for j, doc2 in enumerate(docs2):
            similarities[i][j] = doc1.similarity(doc2)

    return similarities


def test_model(model_name, display_name, test_sets):
    """Test a single model across all test sets"""
    print(f"\n{'=' * 90}")
    print(f"MODEL: {display_name}")
    print(f"{'=' * 90}")

    try:
        model = SentenceTransformer(model_name)

        # Speed test on abstract queries
        start = time.time()
        _ = model.encode(ABSTRACT_QUERIES)
        encode_time = (time.time() - start) * 1000

        # Get dimensions
        sample_emb = model.encode(["test"])
        dimensions = len(sample_emb[0])

        results = {"model": display_name, "dimensions": dimensions, "encode_time_ms": encode_time, "categories": {}}

        # Test each category
        for category, queries, meanings in test_sets:
            q_emb = model.encode(queries)
            m_emb = model.encode(meanings)
            w_emb = model.encode(WRONG_MEANINGS)

            similarities = util.cos_sim(q_emb, m_emb)
            wrong_sims = util.cos_sim(q_emb[:5], w_emb)

            # Get correct matches (diagonal)
            correct_scores = [similarities[i][i].item() for i in range(len(queries))]

            # Calculate metrics
            avg_score = np.mean(correct_scores)
            min_score = np.min(correct_scores)
            max_score = np.max(correct_scores)
            std_dev = np.std(correct_scores)
            avg_wrong = wrong_sims.mean().item()
            separation = avg_score - avg_wrong

            # Use capitalized category name as key
            results["categories"][category.capitalize()] = {
                "avg": avg_score,
                "min": min_score,
                "max": max_score,
                "std": std_dev,
                "separation": separation,
            }

            print(f"\n--- {category.upper()} CONCEPTS ---")
            print(f"Average score: {avg_score:.4f}")
            print(f"Min score:     {min_score:.4f}")
            print(f"Max score:     {max_score:.4f}")
            print(f"Std dev:       {std_dev:.4f}")
            print(f"Separation:    {separation:.4f}")

            # Show top 3 and bottom 3
            scores_with_queries = list(zip(queries, correct_scores))
            scores_with_queries.sort(key=lambda x: x[1], reverse=True)

            print(f"\nTop 3:")
            for q, s in scores_with_queries[:3]:
                print(f"  {q:40} → {s:.4f}")

            print(f"Bottom 3:")
            for q, s in scores_with_queries[-3:]:
                print(f"  {q:40} → {s:.4f}")

        # Print model stats
        print(f"\n--- MODEL STATISTICS ---")
        print(f"Dimensions:        {dimensions}")
        print(f"Encoding time:     {encode_time:.1f}ms for {len(ABSTRACT_QUERIES)} texts")
        print(f"Time per text:     {encode_time / len(ABSTRACT_QUERIES):.2f}ms")
        print(f"Storage (100k):    ~{dimensions * 4 * 100000 / 1024 / 1024:.0f}MB")

        return results

    except Exception as e:
        print(f"❌ Error loading {model_name}: {str(e)}")
        return None


def test_spacy(test_sets):
    """Test spaCy model"""
    if not spacy_available:
        return None

    print(f"\n{'=' * 90}")
    print(f"MODEL: spaCy en_core_web_lg (300d)")
    print(f"{'=' * 90}")

    # Speed test
    start = time.time()
    _ = list(nlp.pipe(ABSTRACT_QUERIES))
    encode_time = (time.time() - start) * 1000

    results = {"model": "spaCy en_core_web_lg", "dimensions": 300, "encode_time_ms": encode_time, "categories": {}}

    for category, queries, meanings in test_sets:
        similarities = spacy_similarity(nlp, queries, meanings)
        wrong_sims = spacy_similarity(nlp, queries[:5], WRONG_MEANINGS)

        correct_scores = [similarities[i][i] for i in range(len(queries))]

        avg_score = np.mean(correct_scores)
        min_score = np.min(correct_scores)
        max_score = np.max(correct_scores)
        std_dev = np.std(correct_scores)
        avg_wrong = np.mean(wrong_sims)
        separation = avg_score - avg_wrong

        # Use capitalized category name as key
        results["categories"][category.capitalize()] = {
            "avg": avg_score,
            "min": min_score,
            "max": max_score,
            "std": std_dev,
            "separation": separation,
        }

        print(f"\n--- {category.upper()} CONCEPTS ---")
        print(f"Average score: {avg_score:.4f}")
        print(f"Min score:     {min_score:.4f}")
        print(f"Max score:     {max_score:.4f}")
        print(f"Std dev:       {std_dev:.4f}")
        print(f"Separation:    {separation:.4f}")

        scores_with_queries = list(zip(queries, correct_scores))
        scores_with_queries.sort(key=lambda x: x[1], reverse=True)

        print(f"\nTop 3:")
        for q, s in scores_with_queries[:3]:
            print(f"  {q:40} → {s:.4f}")

        print(f"Bottom 3:")
        for q, s in scores_with_queries[-3:]:
            print(f"  {q:40} → {s:.4f}")

    print(f"\n--- MODEL STATISTICS ---")
    print(f"Dimensions:        300")
    print(f"Encoding time:     {encode_time:.1f}ms for {len(ABSTRACT_QUERIES)} texts")
    print(f"Time per text:     {encode_time / len(ABSTRACT_QUERIES):.2f}ms")
    print(f"Storage (100k):    ~{300 * 4 * 100000 / 1024 / 1024:.0f}MB")

    return results


def print_summary(all_results):
    """Print comprehensive summary table"""
    print("\n" + "=" * 110)
    print("COMPREHENSIVE SUMMARY")
    print("=" * 110)

    # Sort by overall average
    ranked = []
    for result in all_results:
        if result:
            cats = result["categories"]
            overall_avg = np.mean([cats[cat]["avg"] for cat in cats])
            ranked.append((result, overall_avg))

    ranked.sort(key=lambda x: x[1], reverse=True)

    # Performance table
    print("\n{:<30} {:>12} {:>12} {:>12} {:>12}".format("Model", "Abstract", "Concrete", "Mixed", "Overall"))
    print("-" * 110)

    for result, overall in ranked:
        cats = result["categories"]
        print(
            "{:<30} {:>12.4f} {:>12.4f} {:>12.4f} {:>12.4f}".format(
                result["model"][:28], cats["Abstract"]["avg"], cats["Concrete"]["avg"], cats["Mixed"]["avg"], overall
            )
        )

    # Resource table
    print(
        "\n{:<30} {:>12} {:>15} {:>15} {:>15}".format(
            "Model", "Dimensions", "Speed (ms)", "Per Text (ms)", "Storage (100k)"
        )
    )
    print("-" * 110)

    for result, _ in ranked:
        storage_mb = result["dimensions"] * 4 * 100000 / 1024 / 1024
        per_text = result["encode_time_ms"] / len(ABSTRACT_QUERIES)
        print(
            "{:<30} {:>12} {:>15.1f} {:>15.2f} {:>13.0f}MB".format(
                result["model"][:28], result["dimensions"], result["encode_time_ms"], per_text, storage_mb
            )
        )

    # Consistency table (std dev - lower is better)
    print("\n{:<30} {:>12} {:>12} {:>12} {:>12}".format("Model", "Abstract σ", "Concrete σ", "Mixed σ", "Avg σ"))
    print("-" * 110)

    for result, _ in ranked:
        cats = result["categories"]
        avg_std = np.mean([cats[cat]["std"] for cat in cats])
        print(
            "{:<30} {:>12.4f} {:>12.4f} {:>12.4f} {:>12.4f}".format(
                result["model"][:28], cats["Abstract"]["std"], cats["Concrete"]["std"], cats["Mixed"]["std"], avg_std
            )
        )

    # Separation table (higher is better)
    print("\n{:<30} {:>12} {:>12} {:>12}".format("Model", "Abstract Δ", "Concrete Δ", "Mixed Δ"))
    print("-" * 80)

    for result, _ in ranked:
        cats = result["categories"]
        print(
            "{:<30} {:>12.4f} {:>12.4f} {:>12.4f}".format(
                result["model"][:28],
                cats["Abstract"]["separation"],
                cats["Concrete"]["separation"],
                cats["Mixed"]["separation"],
            )
        )

    # Recommendations
    print("\n" + "=" * 110)
    print("RECOMMENDATIONS")
    print("=" * 110)

    best_overall = ranked[0][0]
    best_speed = min([r for r in all_results if r], key=lambda x: x["encode_time_ms"])
    best_storage = min([r for r in all_results if r], key=lambda x: x["dimensions"])

    print(f"\n🏆 Best Overall Performance: {best_overall['model']}")
    print(f"   → Highest accuracy across all categories")
    print(f"   → Overall score: {ranked[0][1]:.4f}")

    print(f"\n⚡ Fastest Encoding: {best_speed['model']}")
    print(f"   → {best_speed['encode_time_ms']:.1f}ms for {len(ABSTRACT_QUERIES)} texts")
    print(f"   → {best_speed['encode_time_ms'] / len(ABSTRACT_QUERIES):.2f}ms per text")

    print(f"\n💾 Most Storage Efficient: {best_storage['model']}")
    print(f"   → {best_storage['dimensions']} dimensions")
    print(f"   → ~{best_storage['dimensions'] * 4 * 100000 / 1024 / 1024:.0f}MB for 100k vectors")

    print("\n📊 For Your Use Case (Arabic root word semantic search):")
    print("   → Prioritize: Accuracy on abstract concepts")
    print("   → Consider: Balance of accuracy, speed, and storage")
    print(f"   → Recommended: {ranked[0][0]['model']}")
    if ranked[0][0]["model"] != best_speed["model"]:
        cats_best = ranked[0][0]["categories"]
        cats_fast = best_speed["categories"]
        overall_best = ranked[0][1]
        overall_fast = np.mean([cats_fast[cat]["avg"] for cat in cats_fast])
        acc_diff = ((overall_best - overall_fast) / overall_fast) * 100
        speed_ratio = best_speed["encode_time_ms"] / ranked[0][0]["encode_time_ms"]
        print(f"   → Alternative (faster): {best_speed['model']}")
        print(f"     • {speed_ratio:.1f}x faster, but {acc_diff:.1f}% less accurate")


def main():
    print("=" * 110)
    print("COMPREHENSIVE EMBEDDING MODEL COMPARISON")
    print("Testing models on abstract, concrete, and mixed concepts")
    print("=" * 110)

    test_sets = [
        ("Abstract", ABSTRACT_QUERIES, ABSTRACT_MEANINGS),
        ("Concrete", CONCRETE_QUERIES, CONCRETE_MEANINGS),
        ("Mixed", MIXED_QUERIES, MIXED_MEANINGS),
    ]

    all_results = []

    # Test spaCy first
    if spacy_available:
        spacy_result = test_spacy(test_sets)
        if spacy_result:
            all_results.append(spacy_result)

    # Test sentence transformers
    for model_name, display_name in MODELS:
        result = test_model(model_name, display_name, test_sets)
        if result:
            all_results.append(result)

    # Print summary
    if all_results:
        print_summary(all_results)
    else:
        print("\n❌ No models were successfully tested!")

    print("\n" + "=" * 110)
    print("Testing complete!")
    print("=" * 110)


if __name__ == "__main__":
    main()
