"""
Tres agentes autonomos que se comunican via contexto compartido (dict).

- WatcherAgent: ejecuta y monitorea el pipeline
- AnalyzerAgent: analiza patrones de fallos y detecta flaky tests
- ReporterAgent: genera reportes legibles y sugiere mejoras
"""

from collections import Counter
from typing import Any

from pipeline_sim import PipelineResult, run_pipeline


class WatcherAgent:
    """Agente observador: dispara el pipeline y guarda resultados."""

    def __init__(self, context: dict[str, Any]) -> None:
        self.ctx = context

    def watch(self, run_id: int) -> PipelineResult:
        result = run_pipeline(run_id)
        history: list[PipelineResult] = self.ctx.setdefault("history", [])
        history.append(result)
        self.ctx["last_result"] = result
        return result


class AnalyzerAgent:
    """Agente analista: examina historial e identifica patrones de fallo."""

    def __init__(self, context: dict[str, Any]) -> None:
        self.ctx = context

    def analyze(self) -> dict[str, Any]:
        history: list[PipelineResult] = self.ctx.get("history", [])
        if not history:
            return {"verdict": "no_data"}

        failures = [r for r in history if not r.success]
        failure_rate = len(failures) / len(history)

        # Que etapa falla mas
        stage_counts: Counter[str] = Counter()
        errors: list[str] = []
        for r in failures:
            for s in r.failed_stages():
                stage_counts[s.name] += 1
                if s.error:
                    errors.append(s.error)

        most_flaky = stage_counts.most_common(1)
        is_flaky = (
            len(failures) > 0
            and len(history) >= 3
            and failure_rate < 0.5
        )

        analysis: dict[str, Any] = {
            "total_runs": len(history),
            "failures": len(failures),
            "success_rate": round((1 - failure_rate) * 100, 1),
            "most_problematic_stage": most_flaky[0][0] if most_flaky else None,
            "stage_fail_counts": dict(stage_counts),
            "common_errors": list(set(errors)),
            "is_flaky": is_flaky,
            "verdict": (
                "flaky_test"
                if is_flaky
                else ("systematic" if failure_rate > 0.7 else "stable")
            ),
        }

        self.ctx["analysis"] = analysis
        return analysis


class ReporterAgent:
    """Agente reportero: produce reporte humano-legible y sugerencias."""

    def __init__(self, context: dict[str, Any]) -> None:
        self.ctx = context

    def report(self) -> str:
        analysis = self.ctx.get("analysis", {})
        history: list[PipelineResult] = self.ctx.get("history", [])

        if not analysis or analysis.get("verdict") == "no_data":
            return "Sin datos de pipeline para reportar."

        lines = [
            "=" * 50,
            "       REPORTE DEL SQUAD DE MONITOREO CI/CD",
            "=" * 50,
            "",
            f"Ejecuciones totales: {analysis['total_runs']}",
            f"Exitos: {analysis['total_runs'] - analysis['failures']}  "
            f"({analysis['success_rate']}%)",
            f"Fallos: {analysis['failures']}",
            "",
        ]

        if analysis["most_problematic_stage"]:
            lines.append(
                f"Etapa mas problematica: {analysis['most_problematic_stage']}"
            )
            lines.append(
                f"  -> Fallo {analysis['stage_fail_counts'].get(analysis['most_problematic_stage'], 0)} veces"
            )

        if analysis["common_errors"]:
            lines.append("Errores detectados:")
            for e in analysis["common_errors"]:
                lines.append(f"  - {e}")

        verdict = analysis["verdict"]
        lines.append(f"\nDiagnostico: {verdict}")

        if verdict == "flaky_test":
            lines.append(
                "Sugerencia: reintentar tests fallidos automaticamente (retry) "
                "o aislar los tests no deterministicos."
            )
        elif verdict == "systematic":
            lines.append(
                "Sugerencia: hay un bug real. Revisar el codigo en "
                f"'{analysis['most_problematic_stage']}' y correr localmente."
            )
        else:
            lines.append("Sugerencia: el pipeline esta saludable.")

        lines.append(f"\nUltimo resultado (#{history[-1].run_id if history else '?'}):")
        lines.append(history[-1].logs if history else "N/A")
        lines.append("=" * 50)

        report = "\n".join(lines)
        self.ctx["report"] = report
        return report
