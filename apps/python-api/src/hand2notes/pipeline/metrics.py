"""Pipeline run metrics — lightweight observability for the staged pipeline.

Aggregates per-stage timings collected during a run into a compact summary that is
logged (structured key=value) and emitted to the UI as a ``run_metrics`` event so the
processing screen can render an honest timing breakdown chart.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StageTiming:
    stage: str
    elapsed_s: float
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class RunMetrics:
    total_elapsed_s: float
    stage_count: int
    slowest_stage: str | None
    slowest_stage_s: float
    stages: list[StageTiming]

    def to_event(self) -> dict:
        """Serialise to the ``run_metrics`` progress-event payload."""
        return {
            "event": "run_metrics",
            "total_elapsed_s": round(self.total_elapsed_s, 3),
            "stage_count": self.stage_count,
            "slowest_stage": self.slowest_stage,
            "slowest_stage_s": round(self.slowest_stage_s, 3),
            "stages": [
                {"stage": s.stage, "elapsed_s": round(s.elapsed_s, 3), "metrics": s.metrics}
                for s in self.stages
            ],
        }

    def log_line(self) -> str:
        """Compact structured one-liner for logs."""
        parts = " ".join(f"{s.stage}={s.elapsed_s:.2f}s" for s in self.stages)
        return (
            f"total={self.total_elapsed_s:.2f}s stages={self.stage_count} "
            f"slowest={self.slowest_stage}@{self.slowest_stage_s:.2f}s | {parts}"
        )


def summarize_run(timings: list[StageTiming]) -> RunMetrics:
    """Build a RunMetrics summary from the per-stage timings of a single run."""
    total = sum(t.elapsed_s for t in timings)
    slowest = max(timings, key=lambda t: t.elapsed_s, default=None)
    return RunMetrics(
        total_elapsed_s=total,
        stage_count=len(timings),
        slowest_stage=slowest.stage if slowest else None,
        slowest_stage_s=slowest.elapsed_s if slowest else 0.0,
        stages=list(timings),
    )
