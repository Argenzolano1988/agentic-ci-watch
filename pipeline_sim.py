"""
Simulador de pipeline CI/CD estilo GitHub Actions / Jenkins.

5 etapas: Build, Unit Tests, Integration Tests, Lint, Deploy.
Integration Tests falla aleatoriamente ~30% del tiempo (tests flaky).
"""

import random
import time
from dataclasses import dataclass, field
from typing import Any


STAGES = ["Build", "Unit Tests", "Integration Tests", "Lint", "Deploy"]
FLAKY_STAGE = "Integration Tests"
FLAKY_FAILURE_RATE = 0.30


@dataclass
class StageResult:
    name: str
    duration: float
    passed: bool
    error: str | None = None


@dataclass
class PipelineResult:
    success: bool
    stages: list[StageResult] = field(default_factory=list)
    logs: str = ""
    run_id: int = 0

    def failed_stages(self) -> list[StageResult]:
        return [s for s in self.stages if not s.passed]


def run_pipeline(run_id: int = 0) -> PipelineResult:
    """Ejecuta una simulacion del pipeline y retorna resultados estructurados."""

    log_lines: list[str] = [f"--- Pipeline Run #{run_id} ---"]
    stages: list[StageResult] = []
    aborted = False

    for stage_name in STAGES:
        # Simular duracion de la etapa
        duration = round(random.uniform(0.5, 2.0), 2)
        time.sleep(duration * 0.1)  # escalado para demo rapida

        # Determinar si falla
        if stage_name == FLAKY_STAGE and random.random() < FLAKY_FAILURE_RATE:
            passed = False
            error = "Flaky integration test assertion failed"
            log_lines.append(
                f"[FAIL] {stage_name} ({duration}s) — {error}"
            )
            stages.append(StageResult(stage_name, duration, passed, error))
            aborted = True
            break
        else:
            passed = True
            log_lines.append(f"[PASS] {stage_name} ({duration}s)")
            stages.append(StageResult(stage_name, duration, passed))

    success = not aborted
    status = "SUCCESS" if success else "FAILURE"
    log_lines.append(
        f"--- Pipeline {status} ({sum(s.duration for s in stages):.2f}s total) ---"
    )

    return PipelineResult(
        success=success,
        stages=stages,
        logs="\n".join(log_lines),
        run_id=run_id,
    )
