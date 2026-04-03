"""Google Vertex AI (Gemini) provider for StoryScope pipeline."""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from storyscope.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class VertexProvider(LLMProvider):
    """Provider using Google Vertex AI for Gemini models."""

    def __init__(
        self,
        model: str,
        max_tokens: int = 8192,
        project: Optional[str] = None,
        location: str = "us-central1",
        **kwargs,
    ):
        super().__init__(model=model, max_tokens=max_tokens, **kwargs)
        from google import genai
        from google.genai.types import HttpOptions

        if not project:
            import os
            project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
            if not project:
                raise ValueError(
                    "Vertex AI project not set. Set 'project' in config/models.yaml "
                    "or export GOOGLE_CLOUD_PROJECT."
                )

        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
            http_options=HttpOptions(api_version="v1"),
        )

    def _safety_settings(self):
        from google.genai.types import SafetySetting

        return [
            SafetySetting(category=cat, threshold="OFF")
            for cat in [
                "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_DANGEROUS_CONTENT",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "HARM_CATEGORY_HARASSMENT",
            ]
        ]

    def generate(self, prompt: str, system: str = "", retries: int = 4, **kwargs) -> str:
        from google.genai.types import GenerateContentConfig

        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", 0.2)

        config = GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            safety_settings=self._safety_settings(),
        )
        if system:
            config.system_instruction = system

        last_error = None
        for attempt in range(retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                text = response.text
                if not text or not text.strip():
                    raise ValueError("Empty response from Gemini")
                return text.strip()

            except Exception as e:
                last_error = e
                err_str = str(e)
                retryable = any(code in err_str for code in ("429", "500", "503", "RESOURCE_EXHAUSTED"))
                if retryable and attempt < retries - 1:
                    wait = (2 ** attempt) * 2
                    logger.warning(f"Gemini error (attempt {attempt + 1}): {e}. Retrying in {wait}s...")
                    time.sleep(wait)
                elif attempt < retries - 1:
                    time.sleep(2)
                else:
                    break

        raise last_error

    def generate_json(self, prompt: str, system: str = "", **kwargs) -> dict:
        from google.genai.types import GenerateContentConfig

        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", 0.1)

        config = GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            response_mime_type="application/json",
            safety_settings=self._safety_settings(),
        )
        if system:
            config.system_instruction = system

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return json.loads(response.text)
