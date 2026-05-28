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

    log.info(
        "Pipeline starting: session=%s name=%r page_count=%d stages=%d",
        session.id, session.name, len(pages), len(stages),
    )

    cumulative_elapsed = 0.0
    for stage, stage_fn in stages:
        _check_cancel()
        log.info("Stage starting: session=%s stage=%s", session.id, stage.value)
        _emit({"event": "stage_started", "stage": stage.value})
        # Yield so any queued WebSocket sends can flush before the stage blocks.
        await asyncio.sleep(0)

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
                log.warning(
                    "Pipeline running slow: session=%s cumulative=%.1fs exceeds 90s threshold",
                    session.id, cumulative_elapsed,
                )
            log.info(
                "Stage completed: session=%s stage=%s elapsed=%.2fs metrics=%s",
                session.id, stage.value, elapsed, metrics,
            )
            if db is not None and run_id is not None:
                await run_logger.complete_run(db, run_id, metrics)
            _emit({"event": "stage_completed", "stage": stage.value, "metrics": metrics})
            await asyncio.sleep(0)  # flush stage_completed before next stage starts

            # After layout detection: emit per-page block data for the canvas overlay
            if stage == PipelineStage.DETECT_LAYOUT:
                for idx, page in enumerate(pages):
                    _emit({
                        "event": "page_layout_detected",
                        "page_id": str(page.id),
                        "page_index": idx,
                        "total_pages": len(pages),
                        "page_width": page.width_px,
                        "page_height": page.height_px,
                        "blocks": [
                            {
                                "block_type": b.block_type.value,
                                "bbox": {
                                    "x": b.bbox.x,
                                    "y": b.bbox.y,
                                    "width": b.bbox.width,
                                    "height": b.bbox.height,
                                },
                                "confidence": round(b.confidence, 3),
                            }
                            for b in page.blocks
                        ],
                    })
                    await asyncio.sleep(0)

            # Emit per-page progress for large batches
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
            log.info("Stage cancelled: session=%s stage=%s", session.id, stage.value)
            if db is not None and run_id is not None:
                await run_logger.cancel_run(db, run_id)
            raise
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            log.exception(
                "Stage failed: session=%s stage=%s error=%s",
                session.id, stage.value, error_msg,
            )
            if db is not None and run_id is not None:
                await run_logger.fail_run(db, run_id, error_msg)
            raise PipelineError(f"Stage {stage.value} failed: {error_msg}") from exc

    log.info(
        "Pipeline completed: session=%s total_elapsed=%.2fs",
        session.id, cumulative_elapsed,
    )
    _emit({"event": "run_completed", "session_id": str(session.id)})
    await asyncio.sleep(0)  # flush run_completed before task finishes
    return session


# ---------------------------------------------------------------------------
# Individual stage implementations
# ---------------------------------------------------------------------------

async def _stage_import(
    session: Session, pages: list[Page], config: VaultConfig
) -> dict[str, float]:
    from hand2notes.ingestion.importer import import_image

    log.info("Importing %d page(s) for session %s", len(pages), session.id)
    for page in pages:
        reimported = import_image(page.source_path, session.id, page.sequence)
        page.width_px = reimported.width_px
        page.height_px = reimported.height_px
        log.debug(
            "Page %d imported: %s (%dx%d px)",
            page.sequence, page.source_path.name, page.width_px, page.height_px,
        )

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

    log.info("Preprocessing %d page(s): deskew → denoise → resize", len(pages))
    corrected = 0
    for page in pages:
        work_dir = page.source_path.parent / "preprocessed"
        work_dir.mkdir(parents=True, exist_ok=True)

        deskewed_path = work_dir / f"{page.id}_deskewed.jpg"
        result = deskew_file(page.source_path, deskewed_path)
        if result.was_corrected:
            log.info("Page %d: deskew correction applied", page.sequence)
            corrected += 1

        denoised_path = work_dir / f"{page.id}_denoised.jpg"
        denoise_file(deskewed_path, denoised_path)

        processed_path = work_dir / f"{page.id}_processed.jpg"
        _resize_for_processing(denoised_path, processed_path)

        page.preprocessed_path = processed_path
        from PIL import Image as PILImage
        with PILImage.open(processed_path) as img:
            page.width_px, page.height_px = img.size

        page.pipeline_stage = PipelineStage.PREPROCESS
        log.debug(
            "Page %d preprocessed: output=%s final_size=%dx%d",
            page.sequence, processed_path.name, page.width_px, page.height_px,
        )

    log.info(
        "Preprocess complete: %d page(s) processed, %d deskew correction(s) applied",
        len(pages), corrected,
    )
    return {"pages_preprocessed": float(len(pages)), "deskew_corrections": float(corrected)}


async def _stage_detect_layout(
    session: Session, pages: list[Page], config: VaultConfig
) -> dict[str, float]:
    from hand2notes.layout.detector import detect_layout
    from hand2notes.layout.reading_order import assign_reading_order

    log.info("Layout detection starting: %d page(s)", len(pages))
    total_blocks = 0
    for page in pages:
        image_path = page.preprocessed_path or page.source_path
        blocks = detect_layout(image_path, page)
        blocks = assign_reading_order(blocks, page.width_px, page.height_px)
        page.blocks = blocks
        page.pipeline_stage = PipelineStage.DETECT_LAYOUT
        total_blocks += len(blocks)

        # Log per-page block type distribution for observability
        type_counts: dict[str, int] = {}
        for b in blocks:
            type_counts[b.block_type.value] = type_counts.get(b.block_type.value, 0) + 1
        log.info(
            "Page %d layout detected: %d block(s) — %s",
            page.sequence, len(blocks),
            ", ".join(f"{k}={v}" for k, v in sorted(type_counts.items())),
        )
        if not blocks:
            log.warning(
                "Page %d returned no layout blocks — image may be blank or unreadable: %s",
                page.sequence, image_path.name,
            )

    log.info(
        "Layout detection complete: %d total blocks across %d page(s) (avg %.1f/page)",
        total_blocks, len(pages), total_blocks / max(len(pages), 1),
    )
    return {"total_blocks": float(total_blocks)}


async def _stage_recognize_text(
    session: Session, pages: list[Page], config: VaultConfig
) -> dict[str, float]:
    from hand2notes.ocr.orchestrator import run_ocr_on_page

    log.info(
        "OCR starting: %d page(s), languages=%s, confidence_threshold=%.2f",
        len(pages), config.ocr_languages, config.confidence_threshold,
    )
    total_blocks = 0
    mean_conf_sum = 0.0
    for page in pages:
        image_path = page.preprocessed_path or page.source_path
        vlm_model = (
            config.vlm_transcription_model
            if config.vlm_transcription_enabled
            else None
        )
        log.info(
            "OCR running on page %d: %s (vlm=%s)",
            page.sequence, image_path.name, vlm_model or "disabled",
        )
        run_ocr_on_page(
            page,
            image_path,
            confidence_threshold=config.confidence_threshold,
            languages=config.ocr_languages,
            vlm_model=vlm_model,
        )
        page.pipeline_stage = PipelineStage.RECOGNIZE_TEXT
        if page.blocks:
            confs = [b.confidence for b in page.blocks]
            page.overall_confidence = sum(confs) / len(confs)
            mean_conf_sum += page.overall_confidence
            total_blocks += len(page.blocks)
            flagged = sum(1 for b in page.blocks if b.review_flag)
            log.info(
                "Page %d OCR complete: %d block(s), confidence=%.2f, flagged=%d",
                page.sequence, len(page.blocks), page.overall_confidence, flagged,
            )
            if page.overall_confidence < config.confidence_threshold:
                log.warning(
                    "Page %d low overall confidence (%.2f < threshold %.2f) — "
                    "review recommended",
                    page.sequence, page.overall_confidence, config.confidence_threshold,
                )

    mean_conf = mean_conf_sum / len(pages) if pages else 0.0

    # Sub-step: visual semantics (highlights, shapes, URL detection) per page
    urls_detected = 0
    for page in pages:
        urls_detected += _run_visual_semantics_for_page(page)

    if urls_detected:
        log.info("Visual semantics: %d URL reference(s) detected across all pages", urls_detected)

    log.info(
        "OCR complete: %d block(s) total, mean_confidence=%.2f across %d page(s)",
        total_blocks, mean_conf, len(pages),
    )
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
            # Skip re-extraction for VLM-transcribed tables (confidence >= 0.9).
            # Their headers/rows are already populated from the VLM output.
            if block.reconstruction_confidence < 0.9:
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

    if not config.vault_root:
        log.warning(
            "Diagram detection skipped: vault_root not configured — "
            "set vault_root via PUT /api/v1/config to enable diagram export"
        )
        return {"diagrams_found": 0.0, "diagrams_interpreted": 0.0}

    log.info(
        "Diagram detection starting: vlm_runtime=%s model=%s",
        config.vlm_runtime, config.vlm_model,
    )
    diagrams_found = 0
    diagrams_interpreted = 0

    for page in pages:
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
            log.info(
                "Diagram block found: page=%d block=%s — saving crop and running VLM",
                page.sequence, block.id,
            )

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
                        log.warning(
                            "vlm_model path not set — skipping VLM for diagram block %s on page %d",
                            block.id, page.sequence,
                        )
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
                    log.info(
                        "Diagram block %s flagged for review (confidence=%.2f)",
                        block.id, result.reconstruction_confidence,
                    )
                    block.review_decision = DiagramDecision.PENDING
                else:
                    _write_diagram_source(block, diagrams_dir)
                    log.info(
                        "Diagram block %s interpreted: type=%s confidence=%.2f format=%s",
                        block.id, result.diagram_type, result.reconstruction_confidence,
                        block.generated_format,
                    )
                    diagrams_interpreted += 1

            except Exception as exc:
                log.warning(
                    "VLM interpretation failed for diagram block %s on page %d: %s",
                    block.id, page.sequence, exc,
                )
                block.review_decision = DiagramDecision.PENDING

        page.pipeline_stage = PipelineStage.DETECT_DIAGRAMS

    log.info(
        "Diagram detection complete: %d found, %d interpreted, %d pending review",
        diagrams_found, diagrams_interpreted, diagrams_found - diagrams_interpreted,
    )
    return {
        "diagrams_found": float(diagrams_found),
        "diagrams_interpreted": float(diagrams_interpreted),
    }


def _write_diagram_source(block: DiagramBlock, diagrams_dir: Path) -> None:
    """Render and write PlantUML or draw.io source for a validated DiagramBlock.

    Attempts to export a companion PNG via the plantuml / drawio CLI.
    If the CLI is not installed, the source file is still written and a warning is logged.
    """
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
    log.info(
        "Diagram source written: %s (%s, %d bytes)", out_path.name, fmt, out_path.stat().st_size
    )

    # Attempt PNG export — degrades gracefully if CLI not available
    try:
        from hand2notes.diagrams.png_exporter import export_drawio_png, export_plantuml_png
        if fmt == DiagramFormat.PLANTUML:
            png_path = export_plantuml_png(out_path)
        else:
            png_path = export_drawio_png(out_path)
        if png_path:
            block.generated_png_path = png_path
    except Exception as exc:
        log.warning("PNG export raised an unexpected error for %s: %s", out_path.name, exc)


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
