# Dashboard de Análisis de Activos Financieros

API REST + dashboard web que expone una versión reducida del sistema de análisis de activos
de la tesis de grado. El usuario monitorea acciones, ve señales de análisis técnico y dispara
nuevos análisis desde Claude Code con el slash command `/generar-senal`, que calcula indicadores
técnicos reales (RSI, MACD, SMA) sobre precios históricos.

## Stack

| Capa | Tecnología |
|---|---|
| Backend (API REST) | FastAPI + SQLModel |
| Base de datos | SQLite (`data/activos.db`) |
| Frontend | HTML/CSS/JS vanilla, single-file (`frontend/index.html`) |
| Análisis técnico | yfinance + pandas (en `scripts/`, fuera del backend) |
| Tooling | uv |
| Tests | pytest |

## Comandos clave

```bash
# Demo: levanta backend + frontend y abre el dashboard (doble click en Windows)
start.bat

# Backend (API en http://localhost:8000)
uv run uvicorn backend.main:app --reload --port 8000

# Frontend (dashboard en http://localhost:3000), desde la carpeta frontend/
python -m http.server 3000

# Poblar la base con activos y análisis de ejemplo (idempotente)
uv run python scripts/seed.py

# Descargar/actualizar el snapshot de mercado (offline, antes de la demo)
uv run python -m scripts.mercado

# Tests
uv run pytest
```

Documentación Swagger autogenerada: http://localhost:8000/docs (sirve para verificar que la
implementación matchea el `openapi.yaml`).

## Estructura del proyecto

```
CLAUDE.md                contexto para Claude Code (este archivo)
openapi.yaml             contrato de la API, fuente de verdad
README.md                documentación del proyecto
prompts.md               registro de prompts del desarrollo
pyproject.toml           dependencias (uv)
.claude/
  settings.json          permisos del harness (allow/deny/env)
  rules/
    backend.md           reglas para backend/**/*.py
    frontend.md          reglas para frontend/**
  skills/
    generar-senal/
      SKILL.md           slash command /generar-senal (ReAct)
backend/                 SOLO CRUD, no importa yfinance/pandas
  main.py                app FastAPI, routes, CORS
  models.py              SQLModel (Activo, Analisis + variantes Create)
  database.py            engine, Session dependency, PRAGMA FK, create_db()
scripts/                 capa de análisis (todo lo que toca red/cálculo)
  prices.py              ingesta/lectura de la tabla precios (sin red)
  indicators.py          cálculo puro RSI/MACD/SMA + score 0-100 (sin red)
  score_tecnico.py       computar(ticker): prices -> indicators; compartido por skill y endpoint
  generar_senal.py       orquesta: score_tecnico -> POST /activos/{id}/analisis
  seed.py                inserta activos + análisis (cascada red/hardcode)
  mercado.py             descarga paralela de CEDEARs -> mercado_cedears + tabla precios
  historico.py           OHLC + indicadores para el gráfico (JSON por stdout)
frontend/
  index.html             dashboard single-file (servido en :3000)
tests/
  test_api.py            los 7 endpoints
  test_indicators.py     cálculo de indicadores
  test_mercado.py        endpoints /mercado y modelo MercadoCedear
  test_prices.py         obtener_ohlc (lectura de la tabla precios)
  test_historico.py      armado del JSON de histórico (puro)
  test_mercado_script.py upsert y armado de filas de mercado.py
data/
  activos.db             base SQLite (en .gitignore); incluye tabla precios (OHLC)
  cedears.json           lista curada de CEDEARs US (autocompletado + tabla de mercado)
```

## Reglas de arquitectura

- **`openapi.yaml` es la fuente de verdad.** Si hay que cambiar un endpoint (path, schema, status
  code), **se edita primero el `openapi.yaml` y después el código** — nunca al revés. El backend
  deriva del contrato, no lo contrario.
- **Schema de error único** en todo el sistema: `{ "message": "..." }` para 400, 404 y 500. Se
  emite con `HTTPException(status_code=..., detail={"message": "..."})`.
- **CORS** habilitado solo para `http://localhost:3000` (origen del frontend). Por eso el frontend
  se **sirve** en ese puerto, no se abre con `file://`.
- **El backend no toca el dominio financiero externo.** Nada de yfinance ni pandas en `backend/`;
  todo lo que descarga precios o calcula indicadores vive en `scripts/`. El backend es solo CRUD.
- **Fuente unica de precios:** yfinance solo corre en `POST /mercado/actualizar`, que persiste
  OHLC en la tabla `precios`. `/historico` y el score leen de `precios`, nunca de red.
- **El backend no descarga datos de mercado:** `POST /mercado/actualizar` y
  `GET /mercado/{ticker}/historico` lanzan `scripts/mercado.py` e `scripts/historico.py` como
  subprocesos (stdout JSON). La tabla `mercado_cedears` guarda el snapshot sin senal/rsi
  (esos campos son `None`). `POST /activos/{id}/analisis/tecnico` (en cartera, persiste) y
  `GET /mercado/{ticker}/tecnico` (fuera de cartera, sin persistir) lanzan
  `scripts.score_tecnico` como subproceso; el backend no computa, solo el primero guarda.
- **Foreign key con borrado en cascada.** SQLite no aplica FK por defecto: el engine emite
  `PRAGMA foreign_keys=ON` por conexión. Borrar un activo borra sus análisis.

## Convenciones de backend

- **Tres modelos por recurso:** `XxxBase` (campos comunes), `XxxCreate(XxxBase)` (body del POST,
  sin `id`), `Xxx(XxxBase, table=True)` (tabla, con `id`).
- **Status codes:** `200` GET, `201` POST que creó, `204` DELETE sin body, `400` body inválido,
  `404` no existe, `500` error interno.
- **Errores** siempre con `HTTPException` y el schema `{ "message" }`.
- **Sesión de DB por dependency injection** (`Depends`), nunca una sesión global.
- **`logging`, nunca `print()`.** Cada request relevante deja una línea; los errores de integridad
  muestran la causa.
- **La ruta de la DB no se hardcodea:** se lee de `DATABASE_URL` (definida en el `env` del
  `settings.json`).
- **`PYTHONPATH=.` ya está en el `env` del `settings.json`,** así los imports de `scripts/` y
  `backend/` funcionan sin instalar el proyecto como paquete.

## Convenciones de frontend

- Vanilla JS, **single-file** (`frontend/index.html`): HTML + `<style>` + `<script>` juntos. Sin
  frameworks, sin build, sin `node_modules`.
- **Triángulo `state` -> `render()` -> eventos:** el `state` es la única fuente de verdad; tras
  cualquier mutación de `state` se llama a `render()` (única función que toca el DOM).
- Todo `fetch` maneja **loading, éxito y error** con `try/catch/finally`; el error se muestra al
  usuario, nunca se traga en silencio.
- **Custom properties para todos los colores** (paleta Intel + colores de señal en `:root`); no
  hardcodear hex en las reglas.
- **Flexbox/Grid** para el layout, nunca `float`.
- **No usar `innerHTML` con datos del servidor sin sanitizar** (riesgo XSS).
- **Cartera por checkbox:** el usuario marca/desmarca activos desde la tabla de mercado; no hay
  formulario de alta independiente.

## Skill `/generar-senal`

`/generar-senal TICKER [tipo]` — `tipo` = `tecnico` (default) | `sentimiento`.

Implementa el ciclo ReAct (think -> act -> observe) y **delega el cálculo a `scripts/`**: el cuerpo
de la skill orquesta, pero quien computa el score es `scripts/score_tecnico.py` (compartido con el
endpoint `POST /activos/{id}/analisis/tecnico`). El resultado incluye el score 0-100, la senal
derivada y la confianza.

`tipo sentimiento` **no está implementado**: el script devuelve `400 - "tipo sentimiento no
implementado en esta versión"`. El enum y el `openapi.yaml` igual lo contemplan; la restricción
vive solo en el script.

## Flujo de trabajo (GitHub Flow)

- Se trabaja en ramas `feature/...`. **Nunca se commitea directo sobre `main`.**
- El trabajo terminado se integra a `main` **vía Pull Request**, no por merge local directo.

## Recordatorios

- **Mantener este archivo cerca de 200 líneas.** Archivos más largos pierden adherencia.
- **No usar `@import` del `openapi.yaml` en este `CLAUDE.md`:** insertaría el YAML completo en el
  contexto en cada sesión (~3000 tokens innecesarios). Que Claude Code lo lea cuando lo necesite.
