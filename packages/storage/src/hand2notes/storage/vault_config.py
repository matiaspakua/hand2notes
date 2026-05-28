"""VaultConfig persistence: load/save to ~/.config/hand2notes/config.json."""

import json
import logging
from pathlib import Path

from hand2notes.core_models.models import VaultConfig

log = logging.getLogger(__name__)

_CONFIG_PATH = Path.home() / ".config" / "hand2notes" / "config.json"


def load_vault_config(path: Path | None = None) -> VaultConfig:
    """Load VaultConfig from disk; return defaults if file not found or invalid."""
    config_path = path or _CONFIG_PATH
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return VaultConfig.model_validate(data)
        except Exception as exc:
            log.warning("Failed to parse vault config at %s: %s", config_path, exc)
    return VaultConfig()


def save_vault_config(config: VaultConfig, path: Path | None = None) -> None:
    """Persist VaultConfig to disk as JSON."""
    config_path = path or _CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(mode="json")
    config_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
