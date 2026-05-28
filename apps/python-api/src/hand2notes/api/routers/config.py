"""Config API router: GET/PUT/PATCH vault config, vault validation, VLM status."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from hand2notes.core_models.models import VaultConfig
from pydantic import BaseModel

from hand2notes.api.config_service import (
    check_vlm_status,
    load_config,
    save_config,
    validate_vault_path,
)

router = APIRouter(prefix="/config", tags=["config"])


class ConfigPatch(BaseModel):
    vault_root: str | None = None
    folder_template: str | None = None
    export_mode: str | None = None
    default_notebook: str | None = None
    vlm_runtime: str | None = None
    vlm_model: str | None = None
    confidence_threshold: float | None = None
    spell_correction_enabled: bool | None = None
    spell_correction_languages: list[str] | None = None


@router.get("", response_model=dict)
async def get_config() -> dict:
    """Return the current VaultConfig as a JSON-serializable dict."""
    config = load_config()
    return config.model_dump(mode="json")


@router.put("", response_model=dict, status_code=status.HTTP_200_OK)
async def put_config(body: VaultConfig) -> dict:
    """Replace the entire VaultConfig."""
    save_config(body)
    return body.model_dump(mode="json")


@router.patch("", response_model=dict)
async def patch_config(body: ConfigPatch) -> dict:
    """Partially update VaultConfig fields."""
    config = load_config()
    update_data = body.model_dump(exclude_none=True)

    if "vault_root" in update_data:
        config.vault_root = Path(update_data["vault_root"]) if update_data["vault_root"] else None
    if "folder_template" in update_data:
        config.folder_template = update_data["folder_template"]
    if "export_mode" in update_data:
        from hand2notes.core_models.enums import ExportMode
        try:
            config.export_mode = ExportMode(update_data["export_mode"])
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid export_mode value")
    if "default_notebook" in update_data:
        config.default_notebook = update_data["default_notebook"]
    if "vlm_runtime" in update_data:
        from hand2notes.core_models.enums import VLMRuntime
        try:
            config.vlm_runtime = VLMRuntime(update_data["vlm_runtime"])
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid vlm_runtime value")
    if "vlm_model" in update_data:
        config.vlm_model = update_data["vlm_model"]
    if "confidence_threshold" in update_data:
        config.confidence_threshold = update_data["confidence_threshold"]
    if "spell_correction_enabled" in update_data:
        config.spell_correction_enabled = update_data["spell_correction_enabled"]
    if "spell_correction_languages" in update_data:
        config.spell_correction_languages = update_data["spell_correction_languages"]

    save_config(config)
    return config.model_dump(mode="json")


@router.get("/vault/validate", response_model=dict)
async def validate_vault() -> dict:
    """Validate the configured vault path."""
    config = load_config()
    return validate_vault_path(config.vault_root)


@router.get("/vlm/status", response_model=dict)
async def vlm_status() -> dict:
    """Check whether the configured VLM runtime is available."""
    config = load_config()
    return check_vlm_status(config)
