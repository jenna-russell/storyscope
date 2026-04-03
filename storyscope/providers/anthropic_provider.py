"""Anthropic API provider for StoryScope pipeline."""

from __future__ import annotations

import json
import logging
import re
import time

from storyscope.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Provider using the Anthropic API (Claude models)."""

    def __init__(self, model: str, max_tokens: int = 4096, api_key: str = "", **kwargs):
        super().__init__(model=model, max_tokens=max_tokens, **kwargs)
        from anthropic import Anthropic

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set. Export it or set it in config/models.yaml.")
        self.client = Anthropic(api_key=api_key)

    def generate(self, prompt: str, system: str = "", retries: int = 3, **kwargs) -> str:
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        last_error = None

        for attempt in range(retries):
            try:
                call_kwargs = dict(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                if system:
                    call_kwargs["system"] = system

                response = self.client.messages.create(**call_kwargs)
                text = response.content[0].text
                if not text or not text.strip():
                    raise ValueError("Empty response from Anthropic")
                return text.strip()

            except Exception as e:
                last_error = e
                err_str = str(e)
                if any(code in err_str for code in ("429", "500", "529")) and attempt < retries - 1:
                    wait = (2 ** attempt) * 2
                    logger.warning(f"Anthropic error (attempt {attempt + 1}): {e}. Retrying in {wait}s...")
                    time.sleep(wait)
                elif attempt < retries - 1:
                    time.sleep(2)
                else:
                    break

        raise last_error

    def generate_json(self, prompt: str, system: str = "", **kwargs) -> dict:
        text = self.generate(prompt, system=system, **kwargs)
        # Try to extract JSON from code blocks
        m = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
        if m:
            text = m.group(1)
        return json.loads(text)
