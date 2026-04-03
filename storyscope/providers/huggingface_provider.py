"""HuggingFace local model provider for StoryScope pipeline."""

from __future__ import annotations

import json
import logging
import re

from storyscope.providers.base import LLMProvider

logger = logging.getLogger(__name__)

_pipeline = None


class HuggingFaceProvider(LLMProvider):
    """Provider using a local HuggingFace model via transformers."""

    def __init__(self, model: str, max_tokens: int = 4096, device: str = "auto", **kwargs):
        super().__init__(model=model, max_tokens=max_tokens, **kwargs)
        self.device = device
        self._pipe = None

    def _get_pipeline(self):
        if self._pipe is not None:
            return self._pipe

        import torch
        from transformers import pipeline

        device_map = self.device
        if device_map == "auto":
            device_map = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(f"Loading HuggingFace model: {self.model} on {device_map}")
        self._pipe = pipeline(
            "text-generation",
            model=self.model,
            device_map=device_map,
            torch_dtype=torch.float16 if device_map == "cuda" else torch.float32,
        )
        return self._pipe

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        pipe = self._get_pipeline()
        max_tokens = kwargs.get("max_tokens", self.max_tokens)

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        result = pipe(
            messages,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=kwargs.get("temperature", 0.2),
            return_full_text=False,
        )
        text = result[0]["generated_text"]
        if isinstance(text, list):
            text = text[-1].get("content", "") if text else ""
        return text.strip()

    def generate_json(self, prompt: str, system: str = "", **kwargs) -> dict:
        text = self.generate(prompt, system=system, **kwargs)
        m = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
        if m:
            text = m.group(1)
        return json.loads(text)
