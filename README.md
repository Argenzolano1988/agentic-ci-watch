# Construye un Squad de Agentes para Monitorear tu CI/CD

Un proyecto educativo que te enseña a construir un **squad multi-agente** autónomo
capaz de monitorear, diagnosticar y reportar el estado de un pipeline de CI/CD.
Todo en Python puro, sin dependencias externas.

---

## Indice

1. [Arquitectura Multi-Agente](#arquitectura-multi-agente)
2. [Requisitos e Instalacion](#requisitos-e-instalacion)
3. [El Simulador de Pipeline](#el-simulador-de-pipeline)
4. [Los Tres Agentes](#los-tres-agentes)
5. [El Orquestador](#el-orquestador)
6. [Comunicacion entre Agentes](#comunicacion-entre-agentes)
7. [Ejecucion y Salida de Ejemplo](#ejecucion-y-salida-de-ejemplo)
8. [Como Extender el Proyecto](#como-extender-el-proyecto)

---

## Arquitectura Multi-Agente

En lugar de un script monolotico, usamos **tres agentes especializados** que
colaboran a traves de un **contexto compartido** (un diccionario de Python).
Este patron se llama **blackboard architecture**: cada agente lee y escribe en
una pizarra comun, sin acoplarse directamente entre si.

```
┌──────────────────────────────────────────────┐
│                 CONTEXTO (dict)               │
│  history[], last_result, analysis, report     │
└────┬──────────────────┬──────────────────┬────┘
     │                  │                  │
┌────▼─────┐      ┌─────▼────┐      ┌─────▼─────┐
│ Watcher  │ ───▶ │ Analyzer │ ───▶ │ Reporter  │
│ (observa)│      │ (analiza)│      │ (reporta) │
└──────────┘      └──────────┘      └───────────┘
     │                                      │
     │  Ejecuta pipeline_sim                │  Genera reporte
     │  Guarda resultado en history[]       │  Sugiere fixes
     │                                      │
```

**Ventajas del diseno multi-agente:**

- **Separacion de responsabilidades**: cada agente hace una sola cosa bien.
- **Facil de extender**: agregas un agente sin tocar los demas.
- **Facil de probar**: cada agente se prueba aislado con un dict de contexto.
- **Paralelizable**: en produccion, cada agente podria ser un proceso separado.

---

## Requisitos e Instalacion

Solo necesitas **Python 3.10 o superior**. No hay dependencias externas.

```bash
# Clona o copia los archivos del proyecto
cd agentic-ci-watch

# Ejecuta
python main.py
```

Archivos del proyecto:

| Archivo             | Proposito                                      |
|---------------------|------------------------------------------------|
| `pipeline_sim.py`   | Simulador del pipeline CI/CD                   |
| `agents.py`         | Las 3 clases de agentes (Watcher, Analyzer, Reporter) |
| `main.py`           | Orquestador que ejecuta el ciclo               |
| `requirements.txt`  | Vacio — sin dependencias externas              |

---

## El Simulador de Pipeline

`pipeline_sim.py` simula un pipeline estilo **GitHub Actions** o **Jenkins**
con 5 etapas secuenciales:

1. **Build** — compilacion del proyecto
2. **Unit Tests** — tests unitarios
3. **Integration Tests** — tests de integracion (30% probabilidad de fallo flaky)
4. **Lint** — analisis estatico
5. **Deploy** — despliegue a produccion

La etapa **Integration Tests** falla aleatoriamente el 30% de las veces para
simular el problema real de **tests flaky** (tests que pasan y fallan sin que
el codigo cambie). Cuando una etapa falla, el pipeline se aborta (las etapas
posteriores no se ejecutan), igual que en un pipeline real.

Cada ejecucion retorna un `PipelineResult` estructurado:

```python
@dataclass
class PipelineResult:
    success: bool           # True si todas las etapas pasaron
    stages: list[StageResult]  # resultado de cada etapa ejecutada
    logs: str               # log en texto plano
    run_id: int             # numero de ejecucion
```

Ejemplo de uso aislado:

```python
from pipeline_sim import run_pipeline

result = run_pipeline(run_id=1)
print(result.logs)
# --- Pipeline Run #1 ---
# [PASS] Build (1.23s)
# [PASS] Unit Tests (0.89s)
# [FAIL] Integration Tests (1.45s) — Flaky integration test assertion failed
# --- Pipeline FAILURE (3.57s total) ---
```

---

## Los Tres Agentes

### 1. WatcherAgent — El Observador

```python
class WatcherAgent:
    def watch(self, run_id: int) -> PipelineResult:
```

**Responsabilidad unica**: ejecutar el pipeline y registrar el resultado.

- Llama a `run_pipeline(run_id)`
- Agrega el resultado a `context["history"]`
- Guarda el ultimo resultado en `context["last_result"]`

Es el unico agente que interactua directamente con el pipeline. Los demas
leen del contexto.

---

### 2. AnalyzerAgent — El Analista

```python
class AnalyzerAgent:
    def analyze(self) -> dict[str, Any]:
```

**Responsabilidad unica**: examinar el historial y detectar patrones.

Logica de analisis:

1. Cuenta ejecuciones totales vs fallidas
2. Identifica que etapa falla mas (usa `Counter`)
3. Agrupa mensajes de error comunes
4. Clasifica el fallo:
   - **`flaky_test`**: hay fallos pero la tasa es < 50% y hay suficientes datos (>= 3 runs)
   - **`systematic`**: tasa de fallo > 70%, probable bug real
   - **`stable`**: pipeline saludable

Resultado guardado en `context["analysis"]`.

---

### 3. ReporterAgent — El Reportero

```python
class ReporterAgent:
    def report(self) -> str:
```

**Responsabilidad unica**: producir un reporte humano-legible con sugerencias.

Genera un reporte con:

- Resumen de ejecuciones y tasa de exito
- Etapa mas problematica
- Errores comunes detectados
- **Diagnostico** y **sugerencia accionable**:
  - `flaky_test` → reintentar tests, aislar no-deterministicos
  - `systematic` → revisar codigo, correr localmente
  - `stable` → pipeline saludable

---

## El Orquestador

`main.py` es el **orquestador** que coordina al squad:

```python
def main(cycles: int = 10) -> None:
    context = {}
    watcher = WatcherAgent(context)
    analyzer = AnalyzerAgent(context)
    reporter = ReporterAgent(context)

    for i in range(1, cycles + 1):
        watcher.watch(run_id=i)   # 1. Observar
        analyzer.analyze()         # 2. Analizar
        # (el reporte solo se imprime al final)

    print(reporter.report())      # 3. Reportar
```

El ciclo es: **Watcher → Analyzer → Reporter**. Cada ciclo ejecuta el pipeline
una vez. Al final de todos los ciclos, el Reporter genera el informe consolidado.

---

## Comunicacion entre Agentes

Los agentes no se llaman entre si directamente. Toda la comunicacion ocurre
a traves del **contexto compartido**:

```
Watcher escribe  → context["history"]      (lista de PipelineResult)
Watcher escribe  → context["last_result"]  (ultimo PipelineResult)
Analyzer lee     → context["history"]
Analyzer escribe → context["analysis"]     (dict con diagnostico)
Reporter lee     → context["analysis"]
Reporter lee     → context["history"]
Reporter escribe → context["report"]       (string del reporte)
```

Este patron se conoce como **blackboard pattern**. Ventajas:

- **Desacoplamiento total**: podes reemplazar el Analyzer sin tocar el Watcher.
- **Debugging simple**: el contexto es un dict inspeccionable.
- **Auditabilidad**: el historial completo queda en `history` para trazabilidad.

En sistemas de produccion, este contexto suele ser una base de datos, Redis,
o un message broker como Kafka o RabbitMQ. Aca usamos un dict para mantenerlo
simple y educativo.

---

## Ejecucion y Salida de Ejemplo

```bash
$ python main.py
```

Salida tipica:

```
Iniciando squad de monitoreo CI/CD...
Ciclos a ejecutar: 10

[Ciclo 1/10] Ejecutando pipeline... EXITO (4.52s)
  -> Analisis: stable
[Ciclo 2/10] Ejecutando pipeline... FALLO (2.88s)
  -> Analisis: flaky_test
[Ciclo 3/10] Ejecutando pipeline... EXITO (4.21s)
  -> Analisis: flaky_test
...
[Ciclo 10/10] Ejecutando pipeline... EXITO (4.67s)
  -> Analisis: flaky_test

==================================================
       REPORTE DEL SQUAD DE MONITOREO CI/CD
==================================================

Ejecuciones totales: 10
Exitos: 7  (70.0%)
Fallos: 3

Etapa mas problematica: Integration Tests
  -> Fallo 3 veces
Errores detectados:
  - Flaky integration test assertion failed

Diagnostico: flaky_test
Sugerencia: reintentar tests fallidos automaticamente (retry)
            o aislar los tests no deterministicos.

Ultimo resultado (#10):
--- Pipeline Run #10 ---
[PASS] Build (1.34s)
[PASS] Unit Tests (0.67s)
[PASS] Integration Tests (1.22s)
[PASS] Lint (0.52s)
[PASS] Deploy (0.92s)
--- Pipeline SUCCESS (4.67s total) ---
==================================================
```

---

## Como Extender el Proyecto

### Nuevo agente: NotifierAgent

Queres que el squad envie una notificacion a Slack cuando el pipeline falla?
Agrega un agente nuevo sin tocar los existentes:

```python
class NotifierAgent:
    def __init__(self, context):
        self.ctx = context

    def notify(self):
        last = self.ctx.get("last_result")
        if last and not last.success:
            # Aca llamarias a la API de Slack/Discord
            print(f"[NOTIFY] Pipeline #{last.run_id} fallo!")
```

Y en `main.py`:

```python
notifier = NotifierAgent(context)
# ...
result = watcher.watch(run_id=i)
notifier.notify()
```

### Pipeline real en vez de simulador

Reemplaza `run_pipeline()` con llamadas reales a la API de GitHub Actions,
Jenkins, o GitLab CI. El resto del codigo no cambia porque los agentes solo
consumen `PipelineResult`.

### Persistencia del contexto

En vez de un dict volatil, usa SQLite o Redis para que el squad sobreviva
reinicios:

```python
import json, sqlite3

class PersistentContext:
    def __getitem__(self, key):
        # leer de DB
    def __setitem__(self, key, value):
        # escribir en DB
```

### Mas inteligencia en el Analyzer

El Analyzer actual detecta flaky tests por heuristica simple. Podrias mejorarlo
con:
- **Media movil** de la tasa de fallo para detectar degradaciones graduales
- **Deteccion de anomalias** en la duracion de cada etapa
- **Correlacion** entre cambios de codigo (commits) y fallos
- Integracion con un LLM para analisis de logs

### Ejecutar agentes en paralelo

Los agentes no dependen entre si si el contexto ya tiene datos. Podes usar
`threading` o `asyncio`:

```python
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.submit(analyzer.analyze)
    executor.submit(reporter.report)
```

---

## Conceptos Clave Aprendidos

Al completar este proyecto entendiste:

1. **Patron Blackboard**: agentes que colaboran via memoria compartida
2. **Separacion de responsabilidades**: cada agente hace una sola tarea
3. **Orquestacion declarativa**: el orquestador coordina sin conocer detalles internos
4. **Tests flaky**: problema real de CI/CD y como detectarlos
5. **Extensibilidad**: agregar funcionalidad sin modificar codigo existente

---

## Licencia

MIT — usa este codigo como base para tus propios experimentos con agentes.
