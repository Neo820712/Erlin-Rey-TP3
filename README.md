# Dashboard de Análisis de Activos Financieros

API REST + dashboard web para monitorear CEDEARs de EE.UU., ver señales de análisis técnico y
disparar análisis nuevos. Es una versión reducida del sistema de análisis de activos de la tesis
de grado: el usuario arma una cartera, consulta un snapshot de mercado y genera análisis técnicos
reales (RSI, MACD, SMA) sobre precios históricos.

## Características

- **Cartera de inversión** gestionada con un checkbox desde la tabla de mercado.
- **Snapshot de mercado** de CEDEARs (precio, variación, volumen y fundamentales).
- **Análisis técnico real** (RSI / MACD / SMA) con score 0-100, señal (compra / venta / hold) y
  nivel de confianza.
- **Gráfico histórico interactivo** (OHLC + indicadores) en la vista de detalle del activo.
- **Skill `/tecnico`** para generar y persistir análisis desde Claude Code.

## Stack

| Capa | Tecnología |
|---|---|
| Backend (API REST) | FastAPI + SQLModel |
| Base de datos | SQLite (`data/activos.db`) |
| Frontend | HTML/CSS/JS vanilla, single-file (`frontend/index.html`) |
| Análisis técnico | yfinance + pandas (en `scripts/`, fuera del backend) |
| Tooling | uv |
| Tests | pytest |

## Requisitos

- Python `>=3.12,<3.14`
- [uv](https://docs.astral.sh/uv/) para gestionar el entorno y las dependencias.

## Instalación

```bash
git clone <url-del-repo>
cd Erlin-Rey-TP3
uv sync
```

## Uso

### Levantar todo (demo)

En Windows, `start.bat` abre el backend en `:8000`, el frontend en `:3000` y el dashboard en el
navegador:

```bash
start.bat
```

### Levantar los servicios por separado

Backend (API + Swagger):

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

Frontend (desde la carpeta `frontend/`):

```bash
cd frontend
python -m http.server 3000
```

El frontend **debe** servirse en `http://localhost:3000`: el backend solo habilita CORS para ese
origen. Si se abre el `index.html` con `file://` las llamadas a la API fallan.

### Datos

Poblar la base con activos y análisis de ejemplo:

```bash
uv run python scripts/seed.py
```

Actualizar el mercado con datos online (correrlo antes de una demo; requiere conexión):

```bash
uv run python -m scripts.mercado
```

## API

El contrato de la API es `openapi.yaml`, que es la **fuente de verdad** del proyecto. La
documentación interactiva (Swagger) se autogenera y queda en
[http://localhost:8000/docs](http://localhost:8000/docs) con el backend corriendo.

Grupos de endpoints:

- **`/activos`** — alta, listado, detalle y borrado de los activos de la cartera.
- **`/activos/{id}/analisis`** — historial de análisis y creación de uno nuevo (incluye el
  `POST .../analisis/tecnico`, que computa y persiste el score técnico).
- **`/mercado/...`** — catálogo de CEDEARs, snapshot de mercado, actualización de datos online,
  fundamentales, histórico para el gráfico y score técnico sin persistir.

## Skill `/tecnico`

Desde Claude Code:

```
/tecnico TICKER
```

Genera y persiste un análisis técnico del activo (score 0-100, señal y confianza). El activo
**debe existir en la cartera primero**; el cálculo lee de precios históricos ya descargados, así
que conviene haber corrido la actualización de mercado antes.

## Arquitectura

- **Contrato primero:** `openapi.yaml` manda. Cualquier cambio de un endpoint se hace primero en el
  contrato y después en el código.
- **Backend solo CRUD:** `backend/` no importa yfinance ni pandas. Todo lo que toca red o calcula
  indicadores vive en `scripts/`, que el backend lanza como subprocesos.
- **SQLite como fuente única:** los precios se descargan una sola vez (`POST /mercado/actualizar`)
  y se persisten en la tabla `precios`; el histórico y el score técnico leen de ahí, nunca de red.

## Tests

```bash
uv run pytest
```

## Estructura del proyecto

```
backend/        app FastAPI (CRUD): main, models, database
scripts/        análisis: precios, indicadores, score técnico, ingesta de mercado, histórico
frontend/       dashboard single-file (index.html, servido en :3000)
tests/          tests de API, indicadores, mercado, precios e histórico
data/           SQLite (activos.db) y catálogo de CEDEARs (cedears.json)
openapi.yaml    contrato de la API (fuente de verdad)
CLAUDE.md       contexto para Claude Code
```
