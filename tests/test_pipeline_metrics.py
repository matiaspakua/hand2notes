"""Unit tests for pipeline run-metrics aggregation."""

from hand2notes.pipeline.metrics import StageTiming, summarize_run


def test_summarize_empty_run():
    m = summarize_run([])
    assert m.total_elapsed_s == 0.0
    assert m.stage_count == 0
    assert m.slowest_stage is None
    assert m.to_event()["event"] == "run_metrics"


def test_summarize_identifies_slowest_and_total():
    timings = [
        StageTiming("import", 0.5),
        StageTiming("recognize_text", 12.0, {"blocks_recognized": 7}),
        StageTiming("generate_output", 0.2),
    ]
    m = summarize_run(timings)
    assert m.stage_count == 3
    assert m.slowest_stage == "recognize_text"
    assert m.slowest_stage_s == 12.0
    assert abs(m.total_elapsed_s - 12.7) < 1e-9


def test_to_event_payload_shape():
    m = summarize_run([StageTiming("preprocess", 1.234, {"pages": 2})])
    ev = m.to_event()
    assert ev["event"] == "run_metrics"
    assert ev["total_elapsed_s"] == 1.234
    assert ev["stages"][0]["stage"] == "preprocess"
    assert ev["stages"][0]["metrics"] == {"pages": 2}


def test_log_line_is_compact_and_lists_stages():
    line = summarize_run([StageTiming("import", 0.5), StageTiming("preprocess", 1.0)]).log_line()
    assert "total=1.50s" in line
    assert "import=0.50s" in line and "preprocess=1.00s" in line
