"""Gemini LLM Client Adapter for the Ramayan Video Generator.

Implements the LLMClient Protocol using the google-genai SDK.
"""

import os
from typing import Dict, List, Optional

from google import genai
from google.genai import types


class GeminiLLMClient:
    """LLM client adapter wrapping the Google Gemini API (google-genai SDK).

    Implements the same interface as the LLMClient Protocol defined in
    src/script_engine.py, so it can be used as a drop-in replacement
    for OpenAILLMClient.

    Args:
        api_key: Gemini API key. If None, reads from GEMINI_API_KEY env var.
        model_override: Override the model name. Defaults to gemini-2.0-flash.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_override: str = "gemini-2.5-flash",
    ):
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError(
                "Gemini API key not provided. Set GEMINI_API_KEY env var or pass api_key."
            )

        self._client = genai.Client(api_key=key)
        self._model_override = model_override

    def chat_completions_create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
    ) -> str:
        """Send a chat completion request to Gemini and return the response.

        Maps the OpenAI-style messages format to Gemini's API format.

        Args:
            model: Ignored (uses model_override from __init__).
            messages: List of message dicts with 'role' and 'content'.
            temperature: Sampling temperature.

        Returns:
            The model's response text as a string.
        """
        # Extract system instruction and build contents
        system_instruction = None
        contents = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_instruction = content
            elif role == "user":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=content)],
                    )
                )
            elif role == "assistant":
                contents.append(
                    types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=content)],
                    )
                )

        # Build generation config
        generate_config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
        )

        # Call the API
        response = self._client.models.generate_content(
            model=self._model_override,
            contents=contents,
            config=generate_config,
        )

        return response.text
