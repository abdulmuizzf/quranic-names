from sentence_transformers import SentenceTransformer, util
import numpy as np
import spacy

# Load spaCy large model (needs: python -m spacy download en_core_web_lg)
try:
    nlp = spacy.load("en_core_web_lg")
    spacy_available = True
except:
    print("spaCy en_core_web_lg not found. Install with: python -m spacy download en_core_web_lg")
    spacy_available = False

models_to_test = [
    'all-mpnet-base-v2',
    'BAAI/bge-small-en-v1.5'
]

# Helper function for spaCy similarity
def spacy_similarity(nlp, texts1, texts2):
    """Calculate pairwise similarities between two lists of texts"""
    docs1 = list(nlp.pipe(texts1))
    docs2 = list(nlp.pipe(texts2))
    
    similarities = np.zeros((len(docs1), len(docs2)))
    for i, doc1 in enumerate(docs1):
        for j, doc2 in enumerate(docs2):
            similarities[i][j] = doc1.similarity(doc2)
    
    return similarities

# Test data
abstract_queries = [
    "justice and fairness",
    "divine mercy and compassion",
    "wisdom and insight",
    "courage and bravery",
    "loyalty and faithfulness",
    "peace and tranquility",
    "pride and arrogance",
    "envy and jealousy",
    "repentance and remorse",
    "certainty and conviction"
]

abstract_meanings = [
    "equity, righteousness, impartial judgment",
    "forgiveness, kindness, clemency",
    "understanding, knowledge, discernment",
    "valor, boldness, fearlessness",
    "devotion, allegiance, steadfastness",
    "calmness, serenity, harmony",
    "haughtiness, conceit, self-importance",
    "covetousness, resentment, desiring others' possessions",
    "contrition, regret, turning back from sin",
    "assurance, firm belief, lack of doubt"
]

concrete_queries = [
    "a book for reading",
    "water and rain",
    "mountain and hill",
    "sun and moon",
    "tree with leaves",
    "hand and fingers",
    "house and dwelling",
    "sword and weapon",
    "food and eating",
    "path and road"
]

concrete_meanings = [
    "written text, scripture, pages bound together",
    "liquid, precipitation, moisture from sky",
    "elevated land, peak, high ground",
    "celestial bodies, day star and night orb",
    "plant with trunk, branches, foliage",
    "body part, palm, digits for grasping",
    "shelter, residence, home building",
    "blade, instrument for combat, armament",
    "nourishment, consumption, meals",
    "route, way, trail for travel"
]

print("=" * 90)
print("SPACY vs SENTENCE TRANSFORMERS COMPARISON")
print("=" * 90)

all_results = {}

# Test spaCy if available
if spacy_available:
    print(f"\n{'='*90}")
    print(f"MODEL: spaCy en_core_web_lg")
    print(f"{'='*90}")
    
    for category, queries, meanings in [
        ("ABSTRACT", abstract_queries, abstract_meanings),
        ("CONCRETE", concrete_queries, concrete_meanings)
    ]:
        similarities = spacy_similarity(nlp, queries, meanings)
        correct_scores = [similarities[i][i] for i in range(len(queries))]
        
        print(f"\n--- {category} CONCEPTS ---")
        print(f"Average score: {np.mean(correct_scores):.4f}")
        print(f"Min score:     {np.min(correct_scores):.4f}")
        print(f"Max score:     {np.max(correct_scores):.4f}")
        print(f"Std dev:       {np.std(correct_scores):.4f}")
        
        scores_with_queries = list(zip(queries, correct_scores))
        scores_with_queries.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\nTop 3:")
        for q, s in scores_with_queries[:3]:
            print(f"  {q:35} → {s:.4f}")
        
        print(f"Bottom 3:")
        for q, s in scores_with_queries[-3:]:
            print(f"  {q:35} → {s:.4f}")
    
    # Store results
    all_results['spaCy en_core_web_lg'] = {
        'ABSTRACT': np.mean([spacy_similarity(nlp, abstract_queries, abstract_meanings)[i][i] 
                            for i in range(len(abstract_queries))]),
        'CONCRETE': np.mean([spacy_similarity(nlp, concrete_queries, concrete_meanings)[i][i] 
                            for i in range(len(concrete_queries))])
    }

# Test sentence transformers
for model_name in models_to_test:
    print(f"\n{'='*90}")
    print(f"MODEL: {model_name}")
    print(f"{'='*90}")
    
    model = SentenceTransformer(model_name)
    all_results[model_name] = {}
    
    for category, queries, meanings in [
        ("ABSTRACT", abstract_queries, abstract_meanings),
        ("CONCRETE", concrete_queries, concrete_meanings)
    ]:
        q_emb = model.encode(queries)
        m_emb = model.encode(meanings)
        similarities = util.cos_sim(q_emb, m_emb)
        correct_scores = [similarities[i][i].item() for i in range(len(queries))]
        
        print(f"\n--- {category} CONCEPTS ---")
        print(f"Average score: {np.mean(correct_scores):.4f}")
        print(f"Min score:     {np.min(correct_scores):.4f}")
        print(f"Max score:     {np.max(correct_scores):.4f}")
        print(f"Std dev:       {np.std(correct_scores):.4f}")
        
        scores_with_queries = list(zip(queries, correct_scores))
        scores_with_queries.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\nTop 3:")
        for q, s in scores_with_queries[:3]:
            print(f"  {q:35} → {s:.4f}")
        
        print(f"Bottom 3:")
        for q, s in scores_with_queries[-3:]:
            print(f"  {q:35} → {s:.4f}")
        
        # Store for summary
        all_results[model_name][category] = np.mean(correct_scores)

# Summary table
print("\n" + "="*90)
print("SUMMARY COMPARISON")
print("="*90)
print("\n{:<30} {:>15} {:>15} {:>15}".format("Model", "Abstract", "Concrete", "Average"))
print("-" * 80)

for model_name in all_results:
    abstract = all_results[model_name]['ABSTRACT']
    concrete = all_results[model_name]['CONCRETE']
    avg = (abstract + concrete) / 2
    display_name = model_name.split('/')[-1] if '/' in model_name else model_name
    print("{:<30} {:>15.4f} {:>15.4f} {:>15.4f}".format(
        display_name, abstract, concrete, avg
    ))

print("\n" + "="*90)
print("KEY DIFFERENCES:")
print("="*90)
print("• spaCy: Uses averaged word vectors (GloVe-style), optimized for NER/parsing")
print("• Sentence Transformers: Trained specifically for semantic similarity")
print("• spaCy is faster but less accurate for semantic search tasks")
print("• spaCy vectors are 300-dim, BGE is 384-dim, mpnet is 768-dim")