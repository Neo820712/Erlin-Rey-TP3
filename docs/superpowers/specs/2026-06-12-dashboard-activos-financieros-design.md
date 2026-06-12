# Spec de diseño — Dashboard de Análisis de Activos Financieros (TP3)

**Materia:** Introducción al Desarrollo de Software Asistido por IA (CEIA — UBA)
**Entrega:** TP3 — Trabajo Final, demo en vivo en la clase 8
**Documento base:** `propuesta/planificacion-del-proyecto.md` (declaración de intención de diseño)

> **Relación con el documento base.** El `planificacion-del-proyecto.md` define el núcleo del
> sistema y sigue vigente: backend FastAPI + SQLModel + SQLite, los 7 endpoints, `openapi.yaml`
> como fuente de verdad, frontend single-file con paleta Intel, y los cuatro artefactos
> obligatorios de Claude Code. Este spec **integra ese núcleo** y formaliza los *deltas* acordados
> en el brainstorming, que mueven la skill `/generar-senal` de "señal simulada" a "análisis técnico
> real con datos de mercado". Donde este spec y el documento base difieren, **manda este spec**.

---

## 1. Resumen

Sistema full-stack que expone como API REST y dashboard web una versión reducida del sistema de
análisis de activos financieros de la tesis de grado. El usuario monitorea activos (acciones),
ve señales de análisis técnico, y dispara nuevos análisis desde Claude Code con un slash command
propio (`/generar-senal`).

El cambio central respecto del documento base: `/generar-senal` ahora calcula **indicadores
técnicos reales** (RSI, MACD, SMA) sobre precios históricos descargados con yfinance, y deriva la
señal por voto de mayoría. El "agente" hace trabajo genuino, no simulado.

---

## 2. Alcance

### Dentro de alcance
- Backend REST (FastAPI) con 7 endpoints, según los contratos del documento base §4.3.
- Persistencia SQLite con modelo relacional y foreign key con borrado en cascada.
- Frontend single-file (`frontend/index.html`) servido en `http://localhost:3000`.
- Análisis técnico **real** vía yfinance + pandas-ta (RSI, MACD, SMA) en `scripts/`.
- Caché local de precios como blindaje de la demo en vivo.
- Seed reproducible de 3 activos con análisis precargado.
- Los cuatro artefactos de Claude Code: `CLAUDE.md`, `.claude/rules/`, `.claude/settings.json`,
  skill `/generar-senal`.
- Tests automatizados (`pytest`) de los 7 endpoints y del cálculo de indicadores.

### Fuera de alcance (decisiones explícitas)
- Autenticación / autorización (401/403) y sesiones.
- Methods `PUT`/`PATCH` (activos y análisis no se editan).
- Métricas y traces de observabilidad (solo logs en terminal).
- Análisis de **sentimiento**: el `tipo sentimiento` queda definido en el enum y en el
  `openapi.yaml`, pero el script `generar_senal.py` devuelve `400 - "tipo sentimiento no
  implementado en esta versión"`. El endpoint `POST /activos/{id}/analisis` en sí **sigue
  aceptando** un análisis `sentimiento` si se postea directo — no se rompe el contrato; la
  restricción vive solo en el script.
- Tiempo real / websockets: yfinance se consulta a demanda (al correr la skill o el seed).

---

## 3. Arquitectura

### 3.1 Capas

```
Cliente (dashboard :3000 / curl / skill)
        │  HTTP (GET, POST, DELETE)
        ▼
Backend FastAPI :8000   ──►  SQLite  data/activos.db
  (solo CRUD)

scripts/  (capa de análisis, fuera del backend)
  prices.py      yfinance + caché + fallback
  indicators.py  cálculo puro RSI/MACD/SMA (sin red)
  generar_senal.py  orquesta: prices -> indicators -> POST /activos/{id}/analisis
  seed.py        prices -> indicators -> inserta activos + análisis en la DB
```

**Decisión de límites:** el backend queda **solo con CRUD** (`main.py`, `models.py`,
`database.py`) y no conoce yfinance ni pandas. Toda la lógica que toca la red financiera y el
cálculo de indicadores vive en `scripts/`. Esto mantiene el backend chico y testeable, y permite
calcular indicadores de forma determinística en código (no en el prompt de la skill).

### 3.2 Backend (sin cambios respecto del documento base)
- FastAPI + SQLModel + SQLite. Tres clases por recurso (`XxxBase` / `XxxCreate` / `Xxx(table=True)`).
- 7 endpoints exactamente como el documento base §4.3.
- Schema de error único `{ "message": "..." }` para 400/404/500 (documento base §4.5).
- `logging`, nunca `print()`.
- CORS habilitado para `http://localhost:3000`.

### 3.3 Cascade delete (delta)
SQLite no aplica foreign keys por defecto. El engine registra un event listener que emite
`PRAGMA foreign_keys=ON` en cada conexión, de modo que `DELETE /activos/{id}` borre en cascada
sus análisis y se rechace un análisis con `activo_id` inexistente. Se fija como regla en
`.claude/rules/backend.md`.

---

## 4. Capa de análisis (`scripts/`)

### 4.1 `scripts/prices.py` — adquisición de precios con caché y fallback (compartido)
Módulo compartido por `generar_senal.py` y `seed.py`. Expone una función que, dado un ticker,
devuelve una serie de precios históricos siguiendo esta cascada:

1. **Caché primero:** si existe `data/prices_cache/<TICKER>.csv`, lo lee y lo usa sin tocar la red.
2. **Red:** si no hay caché, descarga con yfinance (suficiente histórico para SMA(50): al menos
   ~6 meses diarios), guarda el CSV en `data/prices_cache/` y lo usa.
3. **Fallback:** si la red falla (timeout, rate limit) y no hay caché, señaliza la falla al
   llamador para que decida (el script de skill reporta error; el seed cae a hardcode).

Devuelve junto a la serie un indicador de **procedencia** (`cache` / `red` / `none`) y la fecha
del dato, para que el llamador pueda avisar "datos cacheados del <fecha>".

### 4.2 `scripts/indicators.py` — cálculo puro (sin red, testeable)
Funciones puras que reciben una serie de precios (cierres) y devuelven los indicadores y la señal.
Sin yfinance ni I/O: por eso son testeables con una serie conocida.

- **RSI(14)**, **MACD(12,26,9)**, **SMA(20,50)** calculados con **pandas-ta**.
- Voto de cada indicador:

  | Indicador | compra | venta | hold |
  |---|---|---|---|
  | RSI(14) | < 30 | > 70 | 30–70 |
  | MACD(12,26,9) | línea MACD **> señal** (estado actual) | línea < señal | (no aplica) |
  | SMA(20,50) | SMA20 > SMA50 | SMA20 < SMA50 | (no aplica) |

  MACD se evalúa por **estado** (posición relativa hoy), no por evento de cruce.

- **Señal final:** voto de mayoría entre los tres.
- **Confianza:** proporción de indicadores que coinciden con la señal final:
  `1/3 ≈ 0.33`, `2/3 ≈ 0.67`, `3/3 = 1.0`.
- **Empate a tres** (los tres votan distinto: compra / venta / hold): señal = `hold`,
  confianza = `0.33`.
- **Resumen:** texto que describe los valores calculados de cada indicador (p. ej.
  "RSI 72.3 (venta), MACD 1.2 sobre señal 0.9 (compra), SMA20 188.4 < SMA50 190.1 (venta) -> venta por mayoría").

### 4.3 `scripts/generar_senal.py` — orquestación de la skill
Ejecutado por la skill `/generar-senal` vía Bash. Flujo:

1. Parsear `TICKER` y `tipo` (default `tecnico`). Si `tipo == sentimiento`: devolver
   `400 - "tipo sentimiento no implementado en esta versión"` y terminar.
2. Verificar que el backend responde (`GET /activos`). Encontrar el activo por `ticker`
   (case-insensitive). Si no existe: informar y terminar.
3. `prices.py` -> serie de precios (con su procedencia). Si procedencia = `none`: reportar el
   fallo de red de forma legible y terminar.
4. `indicators.py` -> señal, confianza, resumen.
5. `POST /activos/{id}/analisis` con `tipo=tecnico`, `senal`, `confianza`, `resumen`.
6. Confirmar el `201` e informar ticker, tipo, señal, confianza, resumen, id creado y la
   procedencia de los precios ("datos cacheados del <fecha>" si aplica).

### 4.4 `scripts/seed.py` — datos iniciales reproducibles
Crea **AAPL, GOOGL, MSFT** (3 acciones US, `tipo=accion`, `mercado=NASDAQ`) y **un análisis
técnico precargado por activo**. Usa la misma cadena que la skill (`prices.py` -> `indicators.py`),
con la misma cascada caché → red → hardcode:

- Caché disponible: calcula sobre el CSV cacheado.
- Sin caché pero con red: descarga, cachea y calcula.
- Sin red ni caché: inserta valores **hardcodeados** plausibles para el análisis precargado.

**Idempotente en los tres escenarios:** antes de insertar, chequea si el ticker ya existe; si
está, no duplica. Re-correr el seed deja la DB igual.

---

## 5. Modelo de datos (sin cambios respecto del documento base §4.4)

```
activos
  id, ticker, nombre, tipo ('accion'|'ON'), mercado ('BYMA'|'NYSE'|'NASDAQ')

analisis
  id, activo_id (FK -> activos.id), tipo ('tecnico'|'sentimiento'),
  senal ('compra'|'venta'|'hold'), confianza (0.0..1.0), resumen, created_at (ISO 8601 UTC)
```

`confianza` validada en `[0,1]` por Pydantic. FK con borrado en cascada (§3.3). El campo
`senales_recientes` del endpoint 3 se resuelve tomando, por cada `tipo`, el análisis de
`created_at` máximo.

---

## 6. Frontend (delta de servido)

Igual al documento base §4.7 (HTML semántico, paleta Intel en custom properties, triángulo
`state`/`render()`/eventos, single-file, manejo de loading/éxito/error, sin `innerHTML` sin
sanitizar). **Único cambio:** se **sirve** en `http://localhost:3000`
(`python -m http.server 3000` desde `frontend/`), no se abre con `file://`. Así el `Origin`
coincide con el `CORS_ORIGINS` del backend. El documento base §3.3 se corrige en consecuencia.

---

## 7. Artefactos de Claude Code

Se construyen de forma interactiva (el asistente pregunta qué incluir antes de escribir cada uno),
según el documento base §5. Deltas:

- **`CLAUDE.md`:** incluye los comandos de servir frontend (`:3000`), correr el seed
  (`uv run python scripts/seed.py`), y correr la skill. ~200 líneas, sin `@import` del YAML.
- **`.claude/rules/backend.md`** (`paths: ["backend/**/*.py"]`): además de lo del documento base,
  fija el `PRAGMA foreign_keys=ON` vía event listener y que el backend **no** importa yfinance/pandas.
- **`.claude/rules/frontend.md`** (`paths: ["frontend/**/*.{html,js,css}"]`): sin cambios.
- **`.claude/settings.json`:** ya existe con `allow`/`deny`/`env`. Verificar que `allow` cubre lo
  necesario para `scripts/` (uv run python). `env` mantiene `DATABASE_URL`,
  `CORS_ORIGINS=http://localhost:3000`, `PYTHONPATH=.`.
- **Skill `/generar-senal`** (`.claude/skills/generar-senal/SKILL.md`): front matter + cuerpo con el
  ciclo ReAct que delega el cálculo a `scripts/generar_senal.py` (§4.3).

---

## 8. Tests

`pytest` + `TestClient` (FastAPI) sobre DB SQLite en memoria:

- **`tests/test_api.py`:** los 7 endpoints; status codes (200/201/204/400/404); validación de
  `confianza ∈ [0,1]` (un `1.5` devuelve 400); cascade delete (borrar un activo borra sus análisis);
  schema de error `{ "message" }`.
- **`tests/test_indicators.py`:** funciones puras de `indicators.py` con una serie de precios
  conocida — verifica que RSI/MACD/SMA y el voto de mayoría (incluido el empate a tres) dan el
  resultado esperado. Sin red.

---

## 9. Dependencias nuevas

Gestionadas con `uv` en `pyproject.toml`:

- `fastapi`, `uvicorn`, `sqlmodel` (núcleo backend).
- `yfinance` — descarga de precios históricos.
- `pandas` — manipulación de series (arrastrado por yfinance/pandas-ta).
- `pandas-ta` — cálculo de RSI/MACD/SMA.
- `pytest`, `httpx` — tests.

> **Riesgo a verificar en el plan:** `pandas-ta 0.3.x` falla con `numpy >= 2.0`
> (`from numpy import NaN`, removido en numpy 2). Mitigación probable: pinear `numpy < 2` o usar un
> fork parcheado. Se resuelve y verifica en la fase de implementación.

---

## 10. Estructura de archivos final

```
activos-dashboard/                ← raíz del repo
├── CLAUDE.md
├── openapi.yaml                  ← contrato, fuente de verdad (primer artefacto)
├── README.md
├── prompts.md                    ← registro de prompts del desarrollo
├── pyproject.toml                ← deps (uv)
├── .gitignore
├── .claude/
│   ├── settings.json
│   ├── rules/
│   │   ├── backend.md
│   │   └── frontend.md
│   └── skills/
│       └── generar-senal/
│           └── SKILL.md
├── backend/
│   ├── main.py                   ← app FastAPI, routes, CORS (solo CRUD)
│   ├── models.py                 ← SQLModel (Activo, Analisis + Create)
│   └── database.py               ← engine, Session dependency, PRAGMA FK, create_db()
├── scripts/
│   ├── prices.py                 ← yfinance + caché + fallback (compartido)
│   ├── indicators.py             ← RSI/MACD/SMA puro (testeable)
│   ├── generar_senal.py          ← orquesta skill: prices -> indicators -> POST
│   └── seed.py                   ← 3 activos + 1 análisis c/u (cascada caché/red/hardcode)
├── frontend/
│   └── index.html                ← dashboard single-file (servido en :3000)
├── tests/
│   ├── test_api.py
│   └── test_indicators.py
└── data/
    ├── .gitkeep                  ← carpeta versionada; activos.db en .gitignore
    └── prices_cache/
        └── .gitkeep              ← CSV de precios cacheados (en .gitignore)
```

---

## 11. Orden de construcción

El `openapi.yaml` se escribe **primero** (fuente de verdad). Luego:

1. `openapi.yaml` (contrato).
2. `pyproject.toml` + deps (verificar el pin de numpy/pandas-ta).
3. Backend: `models.py` -> `database.py` (con PRAGMA FK) -> `main.py` (7 endpoints).
4. `tests/test_api.py` (verde contra el contrato).
5. `scripts/indicators.py` + `tests/test_indicators.py`.
6. `scripts/prices.py` (caché + fallback).
7. `scripts/generar_senal.py` y `scripts/seed.py`.
8. Frontend `index.html`.
9. Artefactos Claude Code (`CLAUDE.md`, rules, skill) — interactivos.
10. `README.md`, `prompts.md`.

---

## 12. Checklist de entrega

### Código funcional
- [ ] Backend: `uv run uvicorn backend.main:app --reload --port 8000`.
- [ ] Frontend servido: `python -m http.server 3000` desde `frontend/`.
- [ ] Los 7 endpoints responden según `openapi.yaml`.
- [ ] SQLite persiste entre reinicios; FK con borrado en cascada.
- [ ] `uv run python scripts/seed.py` crea AAPL/GOOGL/MSFT con 1 análisis c/u (idempotente).
- [ ] `/generar-senal TICKER` calcula RSI/MACD/SMA reales y crea un análisis técnico.
- [ ] La skill usa caché si yfinance falla (demo blindada).
- [ ] `/generar-senal TICKER sentimiento` devuelve el 400 de "no implementado".
- [ ] Frontend muestra badges por señal; formulario de alta; click expande análisis.
- [ ] `pytest` en verde (API + indicadores).

### Configuración Claude Code
- [ ] `CLAUDE.md` ~200 líneas, sin `@import` del YAML.
- [ ] `.claude/rules/backend.md` y `frontend.md` con `paths:`.
- [ ] `.claude/settings.json` con allow/deny/env.
- [ ] Skill `/generar-senal` invocable.

### Repositorio GitHub
- [ ] Repo público; `openapi.yaml`, `README.md`, `prompts.md` commiteados.
- [ ] `data/activos.db` y `data/prices_cache/*.csv` en `.gitignore`.
- [ ] Trabajo en ramas, merge a `main` vía PR (GitHub Flow).

---

## 13. Decisiones tomadas en el brainstorming (deltas y su razón)

1. **Frontend servido en `:3000`** en vez de abierto con `file://`. *Razón:* `file://` manda
   `Origin: null`, que no matchea `CORS_ORIGINS=http://localhost:3000` y rompe todos los `fetch`.
2. **`/generar-senal` con análisis técnico real** (yfinance + pandas-ta) en vez de simulado.
   *Razón:* el agente hace trabajo genuino y conecta con el dominio de la tesis; vale el cambio de
   alcance respecto del documento base, asumiendo la mitigación de la dependencia de red.
3. **Cálculo en `scripts/` (no en el backend ni en el prompt).** *Razón:* determinismo y
   testeabilidad; el backend queda chico y libre de yfinance/pandas.
4. **pandas-ta** para los indicadores. *Razón:* más mantenida/documentada que `ta`; menos código
   propio de cálculo.
5. **Caché de precios + fallback** compartido (`prices.py`). *Razón:* blindar la demo en vivo ante
   caídas/rate-limit de Yahoo; consistencia entre seed y skill.
6. **Seed con cascada caché → red → hardcode, idempotente.** *Razón:* el repo arranca con datos y
   badges sin depender de la red, y re-correrlo no duplica.
7. **MACD por estado, empate a tres → hold/0.33.** *Razón:* el estado da señales vivas (el evento
   de cruce casi siempre daría hold); el empate necesitaba una regla explícita.
8. **`sentimiento` fuera de alcance vía 400 en el script** (no en el endpoint). *Razón:* mantener
   el enum y el contrato sin romperlos, restringiendo solo el camino de la skill.
9. **Tests con pytest** (API + indicadores). *Razón:* evidencia objetiva de que la implementación
   matchea el contrato y de que el cálculo es correcto; el documento base no los tenía.
10. **`seed.py` en `scripts/`** (no en `backend/`). *Razón:* todo lo que toca yfinance y cálculo
    vive junto; `backend/` queda solo con `main.py`, `models.py`, `database.py`.
```
