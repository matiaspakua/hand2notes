"""Pipeline stage orchestrator for the hand2notes processing pipeline.

Runs stages import → preprocess → detect_layout → recognize_text →
reconstruct_structure → generate_output in sequence. Emits progress via an
optional async callback so callers (e.g. WebSocket router) can stream events.
"""

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from hand2notes.core_models.blocks import DiagramBlock
from hand2notes.core_models.enums import PipelineStage, SessionStatus
from hand2notes.core_models.models import Page, Session, VaultConfig
from hand2notes.storage import run_logger
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

ProgressCallback = Callable[[dict[str, Any]], None]


class PipelineError(Exception):
    """Raised when a pipeline stage fails unrecoverably."""


async def run_pipeline(
    db: AsyncSession | None,
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
        (PipelineStage.TEXT_CORRECTION, _stage_text_correction),
        (PipelineStage.RECONSTRUCT_STRUCTURE, _stage_reconstruct_structure),
        (PipelineStage.DETECT_DIAGRAMS, _stage_detect_diagrams),
        (PipelineStage.GENERATE_OUTPUT, _stage_generate_output),
    ]

    cumulative_elapsed = 0.0
    for stage, stage_fn in stages:
        _check_cancel()
        _emit({"event": "stage_started", "stage": stage.value})
        # Yield so any queued WebSocket sends can flush before the stage blocks.
        await asyncio.sleep(0)

        # Run audit logging is persisted only when a DB session is supplied.
        # Sessions/pages currently live in memory (DB wiring lands in Phase 5),
        # so logging is skipped rather than crashing on a None session.
        run_id = None
        stage_start = asyncio.get_event_loop().time()
        try:
            if db is not None:
                run = await run_logger.start_run(db, session.id, stage)
                run_id = run.id
            metrics = await stage_fn(session, pages, config)
            elapsed = asyncio.get_event_loop().time() - stage_start
            cumulative_elapsed += elapsed
            metrics = {**(metrics or {}), "elapsed_s": round(elapsed, 3)}
            if cumulative_elapsed > 90:
                log.warning("Pipeline cumulative time %.1fs exceeds 90s threshold", cumulative_elapsed)
            if db is not None and run_id is not None:
                await run_logger.complete_run(db, run_id, metrics)
            _emit({"event": "stage_completed", "stage": stage.value, "metrics": metrics})
            await asyncio.sleep(0)  # Let WebSocket flush stage_completed before next stage starts
            # Emit per-page progress events for batch sessions
            if len(pages) >= 20:
                for idx, page in enumerate(pages):
                    _emit({
                        "event": "page_processed",
                        "page_id": str(page.id),
                        "stage": stage.value,
                        "current_page": idx + 1,
                        "total_pages": len(pages),
                    })
        except asyncio.CancelledError:
            if db is not None and run_id is not None:
                await run_logger.cancel_run(db, run_id)
            raise
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            log.exception("Stage %s failed: %s", stage.value, error_msg)
            if db is not None and run_id is not None:
                await run_logger.fail_run(db, run_id, error_msg)
            raise PipelineError(f"Stage {stage.value} failed: {error_msg}") from exc

    _emit({"event": "run_completed", "session_id": str(session.id)})
    await asyncio.sleep(0)  # Let WebSocket send run_completed before the task finishes
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


_MAX_PREPROCESS_WIDTH = 1600  # Limit processed images for OCR/layout speed


def _resize_for_processing(src: Path, dst: Path, max_width: int = _MAX_PREPROCESS_WIDTH) -> None:
    """Resize an image so its width does not exceed max_width, preserving aspect ratio."""
    from PIL import Image as PILImage
    img = PILImage.open(src)
    w, h = img.size
    if w > max_width:
        new_h = int(h * max_width / w)
        img = img.resize((max_width, new_h), PILImage.LANCZOS)
    img.save(dst, "JPEG", quality=92)


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

        denoised_path = work_dir / f"{page.id}_denoised.jpg"
        denoise_file(deskewed_path, denoised_path)

        # Resize to max 1600px wide so downstream ML runs at practical speed
        processed_path = work_dir / f"{page.id}_processed.jpg"
        _resize_for_processing(denoised_path, processed_path)

        page.preprocessed_path = processed_path
        # Update page dimensions to match the resized image
        from PIL import Image as PILImage
        with PILImage.open(processed_path) as img:
            page.width_px, page.height_px = img.size

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

    # Sub-step: visual semantics (highlights, shapes, URL detection) per page
    urls_detected = 0
    for page in pages:
        urls_detected += _run_visual_semantics_for_page(page)

    return {
        "blocks_recognized": float(total_blocks),
        "confidence_mean": mean_conf,
        "urls_detected": float(urls_detected),
    }


def _run_visual_semantics_for_page(page: Page) -> int:
    """Run highlight/shape/URL detection on a page and map to blocks."""
    image_path = page.preprocessed_path or page.source_path
    urls_found = 0
    try:
        from hand2notes.layout.semantics_mapper import map_semantics
        from hand2notes.ocr.url_detector import detect_urls_in_blocks
        from hand2notes.preprocessing.highlight_detector import detect_highlights
        from hand2notes.preprocessing.shape_detector import detect_shapes

        highlights = detect_highlights(image_path)
        shapes = detect_shapes(image_path)
        map_semantics(page.blocks, highlights, shapes)
        before = sum(1 for b in page.blocks if b.block_type.value == "url_reference")
        detect_urls_in_blocks(page.blocks)
        after = sum(1 for b in page.blocks if b.block_type.value == "url_reference")
        urls_found = after - before
    except Exception as exc:
        log.warning("Visual semantics detection failed for page %s: %s", page.id, exc)
    return urls_found


async def _stage_text_correction(
    session: Session, pages: list[Page], config: VaultConfig
) -> dict[str, float]:
    """Post-OCR spell correction: Spanish + English dictionary lookup."""
    if not config.spell_correction_enabled:
        log.info("Spell correction disabled by config — skipping")
        return {"blocks_checked": 0.0, "blocks_corrected": 0.0, "words_corrected": 0.0}

    from hand2notes.text_correction.postprocessor import correct_page

    total_checked = 0
    total_corrected = 0
    total_words = 0
    for page in pages:
        metrics = correct_page(page, languages=config.spell_correction_languages)
        total_checked += metrics["blocks_checked"]
        total_corrected += metrics["blocks_corrected"]
        total_words += metrics["words_corrected"]

    return {
        "blocks_checked": float(total_checked),
        "blocks_corrected": float(total_corrected),
        "words_corrected": float(total_words),
    }


async def _stage_reconstruct_structure(
    session: Session, pages: list[Page], config: VaultConfig
) -> dict[str, float]:
    tables_processed = 0
    for page in pages:
        image_path = page.preprocessed_path or page.source_path
        tables_processed += _process_tables_in_page(page, image_path, config)
        page.pipeline_stage = PipelineStage.RECONSTRUCT_STRUCTURE
    return {"pages_reconstructed": float(len(pages)), "tables_processed": float(tables_processed)}


def _process_tables_in_page(page: Page, image_path, config: VaultConfig) -> int:
    """Run table cell extraction on all TABLE blocks in a page. Returns count."""
    from pathlib import Path as _Path

    from hand2notes.core_models.blocks import TableBlock
    from hand2notes.core_models.enums import FallbackType
    from hand2notes.tables.cell_extractor import extract_cells
    from hand2notes.tables.caption_detector import detect_caption

    # Determine assets directory
    if config.vault_root:
        try:
            from hand2notes.markdown_export.vault_writer import resolve_session_folder  # type: ignore
            # We don't have session here; use a temp path
            assets_dir = image_path.parent / "table_assets"
        except Exception:
            assets_dir = image_path.parent / "table_assets"
    else:
        assets_dir = image_path.parent / "table_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    table_index = 0
    processed = 0
    new_blocks = []
    for block in page.blocks:
        if isinstance(block, TableBlock):
            block = extract_cells(block, page, image_path)
            block.caption = detect_caption(block, page.blocks)

            if block.reconstruction_confidence < 0.5:
                # Pick CSV or image fallback
                if block.headers or block.rows:
                    from hand2notes.tables.csv_fallback import export_csv
                    export_csv(block, assets_dir, index=table_index)
                else:
                    from hand2notes.tables.image_fallback import export_image_crop
                    export_image_crop(block, page, assets_dir, index=table_index)
                table_index += 1

            processed += 1
        new_blocks.append(block)
    page.blocks = new_blocks
    return processed


async def _stage_recognize_text_extras(
    session: Session, pages: list[Page], config: VaultConfig
) -> dict[str, float]:
    """Sub-step: run URL detection on OCR output (called within recognize_text stage)."""
    from hand2notes.ocr.url_detector import detect_urls_in_blocks
    total_urls = 0
    for page in pages:
        before = sum(1 for b in page.blocks if b.block_type.value == "url_reference")
        detect_urls_in_blocks(page.blocks)
        after = sum(1 for b in page.blocks if b.block_type.value == "url_reference")
        total_urls += after - before
    return {"urls_detected": float(total_urls)}


async def _stage_detect_diagrams(
    session: Session, pages: list[Page], config: VaultConfig
) -> dict[str, float]:
    """Detect and interpret diagram blocks using the configured VLM runtime."""
    from pathlib import Path

    from hand2notes.core_models.blocks import DiagramBlock
    from hand2notes.core_models.enums import DiagramDecision, DiagramFormat, VLMRuntime
    from hand2notes.diagrams.crop_saver import save_crop
    from hand2notes.diagrams.vlm_validator import validate_vlm_response

    diagrams_found = 0
    diagrams_interpreted = 0

    for page in pages:
        if not config.vault_root:
            continue
        # Determine assets directory using resolve_session_folder if available
        try:
            from hand2notes.markdown_export.vault_writer import resolve_session_folder
            session_folder = resolve_session_folder(config, session)
        except Exception:
            session_folder = page.source_path.parent / "output" / str(session.id)
        assets_dir = session_folder / "assets"
        diagrams_dir = session_folder / "diagrams"
        diagrams_dir.mkdir(parents=True, exist_ok=True)

        for block in page.blocks:
            if not isinstance(block, DiagramBlock):
                continue
            diagrams_found += 1

            # Always save crop first (constitution III)
            save_crop(block, page, assets_dir)

            # Attempt VLM interpretation
            try:
                if config.vlm_runtime == VLMRuntime.OLLAMA:
                    from hand2notes.diagrams.vlm_client_ollama import interpret_diagram as ollama_interpret
                    raw = ollama_interpret(block.crop_path)
                else:
                    from hand2notes.diagrams.vlm_client_llamacpp import interpret_diagram as llama_interpret
                    if not config.vlm_model:
                        log.warning("vlm_model not configured; skipping VLM for block %s", block.id)
                        block.review_decision = DiagramDecision.PENDING
                        continue
                    raw = llama_interpret(block.crop_path, model_path=config.vlm_model)

                result = validate_vlm_response(raw)
                block.diagram_type = result.diagram_type
                block.nodes = result.nodes
                block.edges = result.edges
                block.vlm_json_raw = result.raw_json
                block.reconstruction_confidence = result.reconstruction_confidence

                if result.review_flag:
                    block.review_decision = DiagramDecision.PENDING
                else:
                    # Generate source file
                    _write_diagram_source(block, diagrams_dir)
                    diagrams_interpreted += 1

            except Exception as exc:
                log.warning("VLM interpretation failed for block %s: %s", block.id, exc)
                block.review_decision = DiagramDecision.PENDING

        page.pipeline_stage = PipelineStage.DETECT_DIAGRAMS

    return {
        "diagrams_found": float(diagrams_found),
        "diagrams_interpreted": float(diagrams_interpreted),
    }


def _write_diagram_source(block: DiagramBlock, diagrams_dir: Path) -> None:
    """Render and write PlantUML or draw.io source for a validated DiagramBlock."""
    from hand2notes.core_models.enums import DiagramFormat, DiagramType

    DRAWIO_TYPES = {DiagramType.ANNOTATED_SKETCH, DiagramType.GRAPH_NETWORK}

    if block.diagram_type in DRAWIO_TYPES:
        from hand2notes.diagrams.drawio_renderer import render_drawio
        content = render_drawio(block)
        ext = ".drawio"
        fmt = DiagramFormat.DRAWIO
    else:
        from hand2notes.diagrams.plantuml_renderer import render_plantuml
        content = render_plantuml(block)
        ext = ".puml"
        fmt = DiagramFormat.PLANTUML

    out_path = diagrams_dir / f"diagram_{block.id}{ext}"
    out_path.write_text(content, encoding="utf-8")
    block.generated_source_path = out_path
    block.generated_format = fmt


async def _stage_generate_output(
    session: Session, pages: list[Page], config: VaultConfig
) -> dict[str, float]:
    from hand2notes.markdown_export.renderer import render_note
    from hand2notes.markdown_export.vault_writer import write_note

    if not config.vault_root:
        log.warning("vault_root not configured — skipping vault write")
        return {"notes_written": 0.0}

    markdown = render_note(session, pages, config)
    artifacts = write_note(config, session, markdown, pages=pages)
    if artifacts:
        session.export_artifact = artifacts[0]
    session.status = SessionStatus.REVIEW

    return {"notes_written": 1.0, "artifacts_written": float(len(artifacts))}
