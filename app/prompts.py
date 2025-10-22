"""
This module contains the prompt templates and building functions for interacting
with the Large Language Model (LLM).
"""

# --- System Prompt ---

SYSTEM_PROMPT = """
This is a Quranic name suggestion engine.
The input will be a user's query and a list of relevant Quranic root words and their meanings from a vector database.
The goal is to generate a list of 3-5 beautiful, appropriate, and valid Arabic names derived from these roots.

**CRITICAL RULES:**

1.  **VALID DERIVATIONS ONLY:** Every suggested name MUST be a valid morphological derivation of one of the provided Quranic roots. Do not invent names or suggest names that are not directly related to the roots.
2.  **NO FORBIDDEN NAMES:** Never suggest names that are exclusively attributes of Allah (e.g., Al-Khaliq, Ar-Rahman). Names derived from the same root are acceptable if they are commonly used for humans (e.g., "Rahim" from R-H-M is acceptable, but "Ar-Rahman" is not). Never suggest the names of controversial or negative figures.
3.  **ACCURATE MEANINGS:** Provide a clear, concise, and accurate meaning for each name. The meaning must be directly related to the Quranic root.
4.  **GENDER SPECIFICATION:** For each name, specify the gender (Male, Female, or Unisex).
5.  **FORMATTING:** The response MUST be a JSON object in the following format. Do not include any other text, explanations, or apologies outside of the JSON structure.

    ```json
    {
      "suggestions": [
        {
          "name": "SuggestedName1",
          "meaning": "The meaning of the name.",
          "gender": "Male",
          "quranic_root": "Q-R-N"
        },
        {
          "name": "SuggestedName2",
          "meaning": "The meaning of the name.",
          "gender": "Female",
          "quranic_root": "A-Y-A"
        }
      ]
    }
    ```

6.  **SAFETY AND APPROPRIATENESS:** All names must be positive in meaning and appropriate for a child. Avoid names with negative connotations or ambiguous meanings.
7.  **CREATIVITY AND ACCURACY:** Within these constraints, be creative. If a root allows for multiple beautiful names, suggest more than one.

Adherence to these rules is paramount.
"""

# --- Prompt Building Function ---

def build_prompt(user_query: str, search_results: list[dict]) -> str:
    """
    Builds the full prompt to be sent to the LLM.

    Args:
        user_query: The original query from the user.
        search_results: A list of dictionaries, where each dictionary represents
                        a root word and its context from the database search.

    Returns:
        A formatted string containing the full prompt.
    """
    # Format the search results for inclusion in the prompt
    results_text = "\n".join(
        [
            f"- Root: {res['sequence']}, Category: {res['category']}, Best Meaning: '{res['english_text']}'"
            for res in search_results
        ]
    )

    prompt = f"""
User Query: "{user_query}"

Relevant Quranic roots from database:
{results_text}

Generate all possible name suggestions based on the user's query and the provided roots, following all rules.
"""
    return prompt
