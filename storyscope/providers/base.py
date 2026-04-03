"""
Abstract LLM provider interface and factory function.

Usage:
    config = load_config("config/models.yaml")
    provider = get_provider(config, stage="story_generation")
    text = provider.generate("Write a story about a cat.")
    data = provider.generate_json("Extract features as JSON.", schema={...})
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

import yaml


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str, max_tokens: int = 4096, **kwargs):
        self.model = model
        self.max_tokens = max_tokens
        self.kwargs = kwargs

    @abstractmethod
    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        """Generate text from a prompt. Returns the response text."""

    def generate_json(self, prompt: str, system: str = "", **kwargs) -> dict:
        """Generate structured JSON output. Default implementation parses text output."""
        text = self.generate(prompt, system=system, **kwargs)
        # Try to extract JSON from markdown code blocks
        m = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
        if m:
            text = m.group(1)
        return json.loads(text)


def load_config(config_path: str = "config/models.yaml") -> dict:
    """Load pipeline configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        # Try relative to package root
        pkg_root = Path(__file__).parent.parent.parent
        path = pkg_root / config_path
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(path) as f:
        return yaml.safe_load(f)


def get_provider(
    config: dict,
    stage: Optional[str] = None,
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    **overrides,
) -> LLMProvider:
    """
    Create an LLM provider instance from config.

    Args:
        config: Loaded config dict from models.yaml
        stage: Pipeline stage name (e.g., "story_generation") to read defaults from
        provider_name: Override the provider (openai, anthropic, vertex, huggingface)
        model: Override the model name
        **overrides: Additional kwargs passed to the provider

    Returns:
        An initialized LLMProvider instance
    """
    # Resolve stage defaults
    stage_config = {}
    if stage and "pipeline" in config:
        stage_config = config["pipeline"].get(stage, {})

    pname = provider_name or stage_config.get("provider", "openai")
    mname = model or stage_config.get("model", "gpt-4o")
    max_tokens = overrides.pop("max_tokens", stage_config.get("max_tokens", 4096))

    # Merge provider-level config
    provider_config = config.get("providers", {}).get(pname, {})

    if pname == "openai":
        from storyscope.providers.openai_provider import OpenAIProvider

        api_key = os.environ.get(provider_config.get("api_key_env", "OPENAI_API_KEY"), "")
        return OpenAIProvider(
            model=mname,
            max_tokens=max_tokens,
            api_key=api_key,
            **{**stage_config, **overrides},
        )
    elif pname == "anthropic":
        from storyscope.providers.anthropic_provider import AnthropicProvider

        api_key = os.environ.get(provider_config.get("api_key_env", "ANTHROPIC_API_KEY"), "")
        return AnthropicProvider(
            model=mname,
            max_tokens=max_tokens,
            api_key=api_key,
            **{**stage_config, **overrides},
        )
    elif pname == "vertex":
        from storyscope.providers.vertex_provider import VertexProvider

        return VertexProvider(
            model=mname,
            max_tokens=max_tokens,
            project=provider_config.get("project"),
            location=provider_config.get("location", "us-central1"),
            **{**stage_config, **overrides},
        )
    elif pname == "huggingface":
        from storyscope.providers.huggingface_provider import HuggingFaceProvider

        return HuggingFaceProvider(
            model=mname,
            max_tokens=max_tokens,
            device=provider_config.get("device", "auto"),
            **{**stage_config, **overrides},
        )
    else:
        raise ValueError(f"Unknown provider: {pname}. Use: openai, anthropic, vertex, huggingface")
