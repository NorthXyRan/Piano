from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = Path(__file__).resolve().parent / "configs"
DEFAULT_LOCAL_CONFIG = CONFIG_DIR / "llm.local.json"
DEFAULT_EXAMPLE_CONFIG = CONFIG_DIR / "llm.example.json"


@dataclass(frozen=True)
class LlmProfile:
    name: str
    provider: str
    base_url: str | None
    api_key: str | None
    api_key_source: str
    models: dict[str, str]
    api_method: str
    config_path: Path | None

    def model_for(self, role: str, override: str | None = None) -> str:
        if override and override.strip():
            return override.strip()
        return self.models.get(role) or self.models.get("default") or "gpt-4o-mini"

    def redacted(self, role: str = "synthesis", model_override: str | None = None) -> dict[str, Any]:
        return {
            "profile": self.name,
            "provider": self.provider,
            "base_url": self.base_url,
            "api_key_source": self.api_key_source,
            "api_key_configured": bool(self.api_key),
            "model": self.model_for(role, model_override),
            "api_method": self.api_method,
            "config_path": str(self.config_path) if self.config_path else None,
        }


def resolve_config_path(config_path: str | Path | None) -> Path | None:
    if config_path:
        path = Path(config_path)
        if not path.is_absolute():
            path = ROOT / path
        return path
    if DEFAULT_LOCAL_CONFIG.exists():
        return DEFAULT_LOCAL_CONFIG
    if DEFAULT_EXAMPLE_CONFIG.exists():
        return DEFAULT_EXAMPLE_CONFIG
    return None


def load_llm_profile(
    config_path: str | Path | None = None,
    profile_name: str | None = None,
) -> LlmProfile:
    path = resolve_config_path(config_path)
    if config_path and (path is None or not path.exists()):
        raise FileNotFoundError(f"LLM config file not found: {path}")
    if path is None or not path.exists():
        return LlmProfile(
            name=profile_name or "env_openai",
            provider="openai",
            base_url=None,
            api_key=os.environ.get("OPENAI_API_KEY"),
            api_key_source="env:OPENAI_API_KEY",
            models={"synthesis": "gpt-4o-mini"},
            api_method="auto",
            config_path=None,
        )

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    profiles = data.get("profiles") or {}
    selected_name = profile_name or data.get("default_profile")
    if not selected_name:
        raise ValueError(f"No default_profile configured in {path}")
    if selected_name not in profiles:
        available = ", ".join(sorted(profiles)) or "(none)"
        raise ValueError(f"LLM profile '{selected_name}' not found in {path}. Available: {available}")

    raw = profiles[selected_name] or {}
    api_key_literal = str(raw.get("api_key") or "").strip()
    api_key_env = str(raw.get("api_key_env") or "").strip()
    if api_key_literal:
        api_key = api_key_literal
        api_key_source = "config:api_key"
    elif api_key_env:
        api_key = os.environ.get(api_key_env)
        api_key_source = f"env:{api_key_env}"
    else:
        api_key = None
        api_key_source = "not_configured"

    models = raw.get("models") or {}
    if not isinstance(models, dict):
        raise ValueError(f"LLM profile '{selected_name}' has invalid 'models' field; expected object.")

    return LlmProfile(
        name=selected_name,
        provider=str(raw.get("provider") or "openai"),
        base_url=str(raw["base_url"]).strip() if raw.get("base_url") else None,
        api_key=api_key,
        api_key_source=api_key_source,
        models={str(key): str(value) for key, value in models.items()},
        api_method=str(raw.get("api_method") or "auto").strip(),
        config_path=path,
    )
