"""
Orquestador del squad multi-agente.

Ciclo principal: Watcher -> Analyzer -> Reporter
Por defecto ejecuta 10 ciclos del pipeline.
"""

from typing import Any

from agents import AnalyzerAgent, ReporterAgent, WatcherAgent


def main(cycles: int = 10) -> None:
    context: dict[str, Any] = {}

    watcher = WatcherAgent(context)
    analyzer = AnalyzerAgent(context)
    reporter = ReporterAgent(context)

    print("Iniciando squad de monitoreo CI/CD...")
    print(f"Ciclos a ejecutar: {cycles}\n")

    for i in range(1, cycles + 1):
        print(f"[Ciclo {i}/{cycles}] Ejecutando pipeline...", end=" ", flush=True)
        result = watcher.watch(run_id=i)
        status = "EXITO" if result.success else "FALLO"
        print(f"{status} ({sum(s.duration for s in result.stages):.2f}s)")

        analyzer.analyze()
        print(f"  -> Analisis: {context.get('analysis', {}).get('verdict', '?')}")

    print()
    print(reporter.report())


if __name__ == "__main__":
    main()
