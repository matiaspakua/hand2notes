"""Config service: load/save VaultConfig from ~/.config/hand2notes/config.json."""

import json
import logging
from pathlib import Path

from hand2notes.core_models.models import VaultConfig

log = logging.getLogger(__name__)

_CONFIG_PATH = Path.home() / ".config" / "hand2notes" / "config.json"


def load_config() -> VaultConfig:
    """Load VaultConfig from disk; return defaults if not found or invalid."""
    if _CONFIG_PATH.exists():
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            return VaultConfig.model_validate(data)
        except Exception as exc:
            log.warning("Failed to parse config at %s: %s", _CONFIG_PATH, exc)
    return VaultConfig()


def save_config(config: VaultConfig) -> None:
    """Persist VaultConfig to disk as JSON."""
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(mode="json")
    _CONFIG_PATH.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def validate_vault_path(vault_root: Path | None) -> dict:
    """Check vault path existence, writeability, and note count."""
    if vault_root is None:
        return {"valid": False, "reason": "vault_root is not set"}
    p = Path(vault_root)
    if not p.exists():
        return {"valid": False, "reason": "path does not exist"}
    if not p.is_dir():
        return {"valid": False, "reason": "path is not a directory"}
    if not p.stat().st_mode & 0o200:
        return {"valid": False, "reason": "path is not writable"}
    md_count = len(list(p.rglob("*.md")))
    return {"valid": True, "md_file_count": md_count}


def check_vlm_status(config: VaultConfig) -> dict:
    """Check availability of the configured VLM runtime."""
    from hand2notes.core_models.enums import VLMRuntime

    if config.vlm_runtime == VLMRuntime.OLLAMA:
        try:
            import httpx
            resp = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
            available = resp.status_code == 200
            models = [m["name"] for m in resp.json().get("models", [])] if available else []
            return {"runtime": "ollama", "available": available, "models": models}
        except Exception as exc:
            return {"runtime": "ollama", "available": False, "error": str(exc)}
    else:
        try:
            import llama_cpp  # noqa: F401
            model_path = Path(config.vlm_model) if config.vlm_model else None
            model_exists = model_path.exists() if model_path else False
            return {
                "runtime": "llamacpp",
                "available": model_exists,
                "model_path": str(model_path) if model_path else None,
            }
        except ImportError:
            return {"runtime": "llamacpp", "available": False, "error": "llama-cpp-python not installed"}
