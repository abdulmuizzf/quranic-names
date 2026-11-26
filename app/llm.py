"""
This module handles the interaction with the configured Large Language Model (LLM),
including API calls, response parsing, and error handling.
"""

import os
import time
import json
import google.generativeai as genai
from typing import Dict, Any

# --- LLM Interaction ---

class LLMException(Exception):
    """Custom exception for LLM related errors."""
    pass


def _configure():
    """Reads GEMINI_API_KEY when a call is made, so search works without a key."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise LLMException("GEMINI_API_KEY is not set. Add it to .env to generate names.")
    genai.configure(api_key=api_key)

def call_llm_with_retry(
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 3,
    delay: int = 2,
) -> Dict[str, Any]:
    """
    Calls the Gemini API with a given prompt and handles retries.

    Args:
        system_prompt: The system prompt to guide the model's behavior.
        user_prompt: The user-specific prompt containing the query and data.
        max_retries: The maximum number of times to retry the API call.
        delay: The initial delay between retries, in seconds.

    Returns:
        A dictionary parsed from the LLM's JSON response.

    Raises:
        LLMException: If the API call fails after all retries or if the
                      response is not valid JSON.
    """
    _configure()
    generation_config = genai.types.GenerationConfig(
        temperature=0.2,  # Lower temperature for more predictable output
        top_p=0.9,
        top_k=20
    )

    model = genai.GenerativeModel(
        model_name='gemini-2.5-pro',
        system_instruction=system_prompt,
        generation_config=generation_config
    )

    for attempt in range(max_retries):
        try:
            print("Attempting to call the Gemini API...")
            response = model.generate_content(user_prompt)

            # Extract the JSON part of the response
            # The response might be wrapped in ```json ... ```
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()

            print("Successfully received response from LLM.")
            return json.loads(response_text)

        except json.JSONDecodeError as e:
            print(f"Error: Failed to decode JSON from LLM response: {response.text}")
            raise LLMException("LLM response was not valid JSON.") from e

        except Exception as e:
            print(f"API call failed on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay * (2 ** attempt))  # Exponential backoff
            else:
                raise LLMException(f"LLM API call failed after {max_retries} attempts.") from e

    raise LLMException("LLM API call failed after all retries.")
