"""Pipeline stage orchestrator for the hand2notes processing pipeline.

Runs stages import → preprocess → detect_layout → recognize_text →
reconstruct_structure → generate_output in sequence. Emits progress via an
optional async callback so callers (e.g. WebSocket router) can stream events.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from hand2notes.core_models.enums import PipelineStage, SessionStatus
from hand2notes.core_models.models import Page, Session, VaultConfig
from hand2notes.storage import run_logger
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

ProgressCallback = Callable[[dict[str, Any]], None]


class PipelineError(Exception):
    """Raised when a pipeline stage fails unrecoverably."""


async def run_pipeline(
    db: AsyncSession,
    session: Session,
    pages: list[Page],
    config: VaultConfig,
    *,
    on_progress: ProgressCallback | None = None,
    cancelled: asyncio.Event | None = None,
) -> Session:
    """Run the full pipeline for a session and return the updated session.

    Progress events emitted via on_progress (if supplied):
      {"event": "stage_started", "stage": str}
      {"event": "stage_completed", "stage": str, "metrics": dict}
      {"event": "page_processed", "page_id": str, "stage": str}
      {"event": "run_completed", "session_id": str}

    Raises PipelineError on unrecoverable stage failure.
    """

    def _emit(event: dict) -> None:
        if on_progress:
            on_progress(event)

    def _check_cancel() -> None:
        if cancelled and cancelled.is_set():
            raise asyncio.CancelledError("Pipeline cancelled by user")

    stages = [
        (PipelineStage.IMPORT, _stage_import),
        (PipelineStage.PREPROCESS, _stage_preprocess),
        (PipelineStage.DETECT_LAYOUT, _stage_detect_layout),
        (PipelineStage.RECOGNIZE_TEXT, _stage_recognize_text),
        (PipelineStage.RECONSTRUCT_STRUCTURE, _stage_reconstruct_structure),
        (PipelineStage.GENERATE_OUTPUT, _stage_generate_output),
    ]

    for stage, stage_fn in stages:
        _check_cancel()
        _emit({"event": "stage_started", "stage": stage.value})

        run = await run_logger.start_run(db, session.id, stage)
        try:
            metrics = await stage_fn(session, pages, config)
            await run_logger.complete_run(db, run.id, metrics)
            _emit({"event": "stage_completed", "stage": stage.value, "metrics": metrics})
        except asyncio.CancelledError:
            await run_logger.cancel_run(db, run.id)
            raise
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            log.exception("Stage %s failed: %s", stage.value, error_msg)
            await run_logger.fail_run(db, run.id, error_msg)
            raise PipelineError(f"Stage {stage.value} failed: {error_msg}") from exc

    _emit({"event": "run_completed", "session_id": str(session.id)})
    return session


# ---------------------------------------------------------------------------
# Individual stage implementations
# ---------------------------------------------------------------------------

async def _stage_import(
    session: Session, pages: list[Page], config: VaultConfig
) -> dict[str, float]:
    from hand2notes.ingestion.importer import import_image

    for page in pages:
        reimported = import_image(page.source_path, session.id, page.sequence)
        page.width_px = reimported.width_px
        page.height_px = reimported.height_px

    return {"pages_imported": float(len(pages))}


async def _stage_preprocess(
    session: Session, pages: list[Page], config: VaultConfig
) -> dict[str, float]:
    from hand2notes.preprocessing.denoise import denoise_file
    from hand2notes.preprocessing.deskew import deskew_file

    corrected = 0
    for page in pages:
        work_dir = page.source_path.parent / "preprocessed"
        work_dir.mkdir(parents=True, exist_ok=True)

        deskewed_path = work_dir / f"{page.id}_deskewed.jpg"
        result = deskew_file(page.source_path, deskewed_path)

        denoised_path = work_dir / f"{page.id}_processed.jpg"
        denoise_file(deskewed_path, denoised_path)

        page.preprocessed_path = denoised_path
        page.pipeline_stage = PipelineStage.PREPROCESS
        if result.was_corrected:
            corrected += 1

    return {"pages_preprocessed": float(len(pages)), "deskew_corrections": float(corrected)}


async def _stage_detect_layout(
    session: Session, pages: list[Page], config: VaultConfig
) -> dict[str, float]:
    from hand2notes.layout.detector import detect_layout
    from hand2notes.layout.reading_order import assign_reading_order

    total_blocks = 0
    for page in pages:
        image_path = page.preprocessed_path or page.source_path
        blocks = detect_layout(image_path, page)
        blocks = assign_reading_order(blocks, page.width_px, page.height_px)
        page.blocks = blocks
        page.pipeline_stage = PipelineStage.DETECT_LAYOUT
        total_blocks += len(blocks)

    return {"total_blocks": float(total_blocks)}


async def _stage_recognize_text(
    session: Session, pages: list[Page], config: VaultConfig
) -> dict[str, float]:
    from hand2notes.ocr.orchestrator import run_ocr_on_page

    total_blocks = 0
    mean_conf_sum = 0.0
    for page in pages:
        image_path = page.preprocessed_path or page.source_path
        run_ocr_on_page(
            page,
            image_path,
            confidence_threshold=config.confidence_threshold,
            languages=config.ocr_languages,
        )
        page.pipeline_stage = PipelineStage.RECOGNIZE_TEXT
        if page.blocks:
            confs = [b.confidence for b in page.blocks]
            page.overall_confidence = sum(confs) / len(confs)
            mean_conf_sum += page.overall_confidence
            total_blocks += len(page.blocks)

    mean_conf = mean_conf_sum / len(pages) if pages else 0.0
    return {"blocks_recognized": float(total_blocks), "confidence_mean": mean_conf}


async def _stage_reconstruct_structure(
    session: Session, pages: list[Page], config: VaultConfig
) -> dict[str, float]:
    for page in pages:
        page.pipeline_stage = PipelineStage.RECONSTRUCT_STRUCTURE
    return {"pages_reconstructed": float(len(pages))}


async def _stage_generate_output(
    session: Session, pages: list[Page], config: VaultConfig
) -> dict[str, float]:
    from hand2notes.markdown_export.renderer import render_note
    from hand2notes.markdown_export.vault_writer import write_note

    if not config.vault_root:
        log.warning("vault_root not configured — skipping vault write")
        return {"notes_written": 0.0}

    markdown = render_note(session, pages, config)
    artifact = write_note(config, session, markdown)
    session.export_artifact = artifact
    session.status = SessionStatus.REVIEW

    return {"notes_written": 1.0}
