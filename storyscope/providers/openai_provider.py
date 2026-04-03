"""OpenAI API provider for StoryScope pipeline."""

from __future__ import annotations

import json
import logging
import time

from storyscope.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """Provider using the OpenAI API (GPT models)."""

    def __init__(self, model: str, max_tokens: int = 4096, api_key: str = "", **kwargs):
        super().__init__(model=model, max_tokens=max_tokens, **kwargs)
        from openai import OpenAI

        if not api_key:
            raise ValueError("OPENAI_API_KEY not set. Export it or set it in config/models.yaml.")
        self.client = OpenAI(api_key=api_key)
        self.reasoning_effort = kwargs.get("reasoning_effort")

    def generate(self, prompt: str, system: str = "", retries: int = 3, **kwargs) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        last_error = None

        for attempt in range(retries):
            try:
                call_kwargs = dict(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                )
                if self.reasoning_effort:
                    call_kwargs["reasoning_effort"] = self.reasoning_effort

                response = self.client.chat.completions.create(**call_kwargs)
                text = response.choices[0].message.content
                if not text or not text.strip():
                    raise ValueError("Empty response from OpenAI")
                return text.strip()

            except Exception as e:
                last_error = e
                err_str = str(e)
                if any(code in err_str for code in ("429", "500", "503")) and attempt < retries - 1:
                    wait = (2 ** attempt) * 2
                    logger.warning(f"OpenAI error (attempt {attempt + 1}): {e}. Retrying in {wait}s...")
                    time.sleep(wait)
                elif attempt < retries - 1:
                    time.sleep(2)
                else:
                    break

        raise last_error

    def generate_json(self, prompt: str, system: str = "", **kwargs) -> dict:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        max_tokens = kwargs.get("max_tokens", self.max_tokens)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content
        return json.loads(text)
