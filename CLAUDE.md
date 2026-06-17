# Dashboard de Análisis de Activos Financieros

API REST + dashboard web que expone una versión reducida del sistema de análisis de activos
de la tesis de grado. El usuario monitorea acciones, ve señales de análisis técnico y dispara
nuevos análisis desde Claude Code con el slash command `/tecnico`, que calcula indicadores
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
    tecnico/
      SKILL.md           slash command /tecnico (ReAct)
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

Invariantes cross-cutting. El detalle de backend vive en `rules/backend.md` y el de frontend en
`rules/frontend.md`.

- **`openapi.yaml` es la fuente de verdad.** Si cambia un endpoint (path, schema, status code), se
  edita primero el `openapi.yaml` y después el código — nunca al revés.
- **El backend es solo CRUD.** Nada de yfinance ni pandas en `backend/`; todo lo que descarga
  precios o calcula indicadores vive en `scripts/` (que el backend lanza como subprocesos).
- **Fuente única de precios:** yfinance solo corre en `POST /mercado/actualizar`, que persiste
  OHLC en la tabla `precios`. `/historico` y el score leen de `precios`, nunca de red.
- **CORS** habilitado solo para `http://localhost:3000` (origen del frontend). Por eso el frontend
  se **sirve** en ese puerto, no se abre con `file://`.


## Reglas de estructura y seguridad

- **Actualización documental:** al crear carpetas o módulos que cambien la arquitectura principal, actualiza la estructura en este archivo; ignora scripts menores o de prueba para evitar ruido.
- **Archivos excluidos:** queda prohibido leer, modificar o generar archivos `.env` o similares; los secretos se manejan de forma manual.
- **Archivos binarios:** no intentes leer archivos `.db` o `.sqlite` en texto plano; usa scripts de Python para inspeccionar los datos.
- **Prevención de pérdida:** no alteres el archivo `.gitignore` ni elimines archivos de código existentes sin validación previa.


## Comandos y Validación

- **Testing estricto:** Tras cualquier modificación en `backend/` o `scripts/`, debes ejecutar `uv run pytest` y leer la salida antes de dar la tarea por terminada.



## Skill `/tecnico`

`/tecnico TICKER`.

- Implementa el ciclo ReAct (think -> act -> observe) y **delega el cálculo a `scripts/`**: el cuerpo
de la skill orquesta, pero quien computa el score es `scripts/score_tecnico.py` (compartido con el
endpoint `POST /activos/{id}/analisis/tecnico`). El resultado incluye el score 0-100, la senal
derivada y la confianza.



## Flujo de trabajo (GitHub Flow)

- Se trabaja en ramas `feature/...`. **Nunca se commitea directo sobre `main`.**
- El trabajo terminado se integra a `main` **vía Pull Request**, no por merge local directo.

## Recordatorios

- **Mantener este archivo cerca de 200 líneas.** Archivos más largos pierden adherencia.
- **No usar `@import` del `openapi.yaml` en este `CLAUDE.md`:** insertaría el YAML completo en el
  contexto en cada sesión (~3000 tokens innecesarios). Que Claude Code lo lea cuando lo necesite.
