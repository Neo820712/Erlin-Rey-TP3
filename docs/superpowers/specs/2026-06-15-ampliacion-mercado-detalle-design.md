# Spec de diseño — Ampliación del dashboard: autocompletado, tabla de mercado y vista de detalle

**Materia:** Introducción al Desarrollo de Software Asistido por IA (CEIA — UBA)
**Entrega:** TP3 — Trabajo Final
**Documento base:** `propuesta/Ampliacion de funciones.md` (declaración de intención)
**Spec del núcleo:** `docs/superpowers/specs/2026-06-12-dashboard-activos-financieros-design.md`

> **Relación con lo existente.** El sistema actual (backend FastAPI CRUD con 7 endpoints,
> `scripts/` de análisis técnico real, frontend single-file con paleta Intel) sigue vigente y no
> se reescribe. Este spec agrega tres funcionalidades nuevas y formaliza los *deltas* acordados en
> el brainstorming. Donde este spec y `Ampliacion de funciones.md` difieran, **manda este spec**
> (las diferencias se listan en §10).

---

## 1. Resumen

Tres funcionalidades nuevas sobre el frontend, con el soporte de backend/scripts estrictamente
necesario:

1. **Autocompletado** en el formulario de alta: un único campo de búsqueda que filtra una lista de
   CEDEARs por ticker o por nombre y pre-llena los campos del alta.
2. **Tabla de mercado**: todos los CEDEARs del subconjunto con precio, variación, volumen, RSI,
   señal y fundamentales, persistidos en la DB y refrescados a demanda.
3. **Vista de detalle** estilo Finviz + TradingView: panel de métricas (técnico + fundamental),
   gráfico de velas con indicadores superpuestos (lightweight-charts), e historial de análisis.

**Principio rector:** la demo va blindada. Los datos de mercado se descargan **offline/a demanda**
(no en vivo automático) y se guardan en la DB; el gráfico reusa la caché de precios. El backend
**nunca** importa yfinance ni pandas — sigue siendo CRUD puro.

---

## 2. Alcance

### Dentro de alcance
- `data/cedears.json`: subconjunto curado (~30) de CEDEARs de **empresas US** (fundamentales
  completos y confiables en yfinance).
- Tabla `mercado_cedears` en SQLite + modelos SQLModel (convención de tres clases).
- 3 endpoints nuevos en `openapi.yaml` y backend: `GET /mercado/cedears`,
  `POST /mercado/actualizar`, `GET /mercado/{ticker}/historico`.
- `scripts/mercado.py` (descarga paralela → persiste a la DB) y `scripts/historico.py`
  (ticker+período → JSON por stdout).
- `obtener_ohlc` aditivo en `scripts/prices.py` (OHLC con caché); `obtener_precios` (Close) intacto.
- Frontend: autocompletado, tabla de mercado, vista de detalle con gráfico, navegación por vista.
- Tests de los endpoints nuevos (subprocess mockeado) y de `obtener_ohlc`.

### Fuera de alcance
- **Tiempo real / auto-refresh.** El mercado se actualiza solo cuando el usuario lo dispara.
- **Precios en ARS / ticker `.BA`.** Todo sale del ticker US; precios en **USD** (ver §10.3).
- Persistir el histórico OHLC completo en la DB (se obtiene a demanda con caché).
- Llamadas `.info` en vivo al abrir la vista de detalle (los fundamentales se leen del snapshot
  ya guardado en `state.mercado`).
- Tests automáticos de frontend (consistente con el estado actual del proyecto).
- Dependencias Python nuevas (todo es stdlib + lo ya presente en `pyproject.toml`).

---

## 3. Fundación de datos

### 3.1 `data/cedears.json`
Lista curada (~30) de CEDEARs de empresas US. Schema por entrada:

```json
{ "ticker_byma": "AAPL", "ticker_us": "AAPL",
  "nombre": "Apple Inc.", "mercado": "NASDAQ", "tipo": "accion" }
```

`ticker_us` es el ticker que se usa en **todas** las llamadas a yfinance. Para CEDEARs de empresas
US, `ticker_byma == ticker_us` en la práctica; se mantienen ambos campos por claridad semántica y
para soportar a futuro casos donde difieran.

### 3.2 Origen de cada dato (todo desde el ticker US, precios en USD)

| Dato | Fuente |
|---|---|
| Precio (USD), Var % (día), Volumen | `ticker_us` vía `.history` |
| RSI(14), Señal, Confianza | `indicators.py` sobre el histórico del `ticker_us` |
| P/E, EPS, Market Cap, 52w High/Low | `ticker_us` vía `.info` |
| OHLC (gráfico de detalle) | `ticker_us` vía `obtener_ohlc` (con caché) |

### 3.3 Curaduría
Un paso del plan corre `scripts/mercado.py` una vez sobre los ~30 tickers; los que no devuelvan el
set completo de datos se **sacan y reemplazan** por otro equivalente. Es una tarea de
implementación/validación, no lógica de runtime.

---

## 4. Backend, modelo de datos y API

### 4.1 Tabla `mercado_cedears`
Un registro por CEDEAR, **sobrescrito** en cada actualización (upsert por `ticker_byma`):

```
mercado_cedears
  id, ticker_byma, ticker_us, nombre,
  precio_usd, var_pct, volumen,
  rsi, senal,
  pe, eps, market_cap, w52_high, w52_low,
  actualizado_en
```

Modelos SQLModel con la convención de tres clases (`MercadoCedearBase` / `MercadoCedearCreate` /
`MercadoCedear(table=True)`). Los campos fundamentales (`pe`, `eps`, `market_cap`, `w52_high`,
`w52_low`) y los de mercado son `Optional` (aceptan `null` → la UI muestra "—"). `senal` reusa el
enum `Senal` existente.

### 4.2 Endpoints nuevos (al `openapi.yaml` primero)

| Método | Path | Rol |
|---|---|---|
| `GET` | `/mercado/cedears` | Lectura idempotente. Lee `mercado_cedears`; devuelve `{ cedears: [...], actualizado_en }`. Si la tabla está vacía: lista vacía y `actualizado_en: null`. Instantáneo. |
| `POST` | `/mercado/actualizar` | Acción con efecto. Lanza `scripts/mercado.py` como subproceso, bloquea hasta que termina (~15s), devuelve `{ actualizados: N, actualizado_en }`. |
| `GET` | `/mercado/{ticker}/historico?periodo=3m` | Lanza `scripts/historico.py TICKER PERIODO`; lee el JSON de stdout y lo devuelve tal cual. `periodo` ∈ `1m\|3m\|6m\|1y`, default `3m`. |

Routing **bajo `/mercado/`** (no `/activos/`): evita el choque con `/activos/{id}` (entero) y
funciona para cualquier CEDEAR aunque no esté guardado como activo. Errores con el schema único
`{ "message": "..." }` (400 período inválido, 404/500 según corresponda).

### 4.3 Pureza del backend (regla dura mantenida)
El backend **no importa yfinance ni pandas**. Las dos rutas que necesitan datos de red delegan en
scripts vía `subprocess.run([sys.executable, "-m", "scripts.<modulo>", ...])`:

- `POST /mercado/actualizar` → `scripts.mercado` (que persiste directo a la DB, ver §5.2).
- `GET /mercado/{ticker}/historico` → `scripts.historico` (que imprime JSON por stdout).

El backend solo orquesta el subproceso, parsea su salida/stdout y normaliza errores al schema
`{ message }`. Esto mantiene los GET sin efectos colaterales sobre datos de red (salvo el GET de
histórico, que es lectura a demanda y cacheada) y le da a la descarga su propio POST semántico.

---

## 5. Capa de scripts

### 5.1 `scripts/prices.py` — `obtener_ohlc` (aditivo)
Función nueva `obtener_ohlc(ticker, periodo="1y") -> (df_ohlcv, procedencia, fecha)`:
- Devuelve un DataFrame con columnas OHLCV.
- Caché propia en `data/prices_cache/<TICKER>_ohlc.csv` (no pisa el CSV Close-only existente).
- Misma cascada caché → red → none que `obtener_precios`.
- `obtener_precios` (Close) **queda intacto**: `generar_senal.py` y `seed.py` no se tocan.

### 5.2 `scripts/mercado.py` — descarga paralela y persistencia
- Lee `data/cedears.json`.
- Descarga con `ThreadPoolExecutor` (stdlib, 20–30 workers) en paralelo: por ticker, `.history`
  (precio/volumen/var%/serie para RSI) y `.info` (fundamentales).
- Calcula RSI/señal/confianza con `indicators.py`.
- **Persiste directo a la DB** vía `Session(engine)` (precedente: `seed.py`), haciendo upsert por
  `ticker_byma` y seteando `actualizado_en` (ISO 8601 UTC) común a la corrida.
- Robusto a fallos por ticker: un ticker que falle no aborta la corrida; se registra y se sigue.

### 5.3 `scripts/historico.py` — JSON para el gráfico
- Args: `TICKER PERIODO`.
- `obtener_ohlc` → OHLC; `indicators.py` → series e indicadores **recalculados para el período**.
- Imprime por stdout un JSON autocontenido:

```json
{
  "ohlc": [ { "time": "2026-01-02", "open": ..., "high": ..., "low": ..., "close": ... } ],
  "series": { "sma20": [...], "sma50": [...], "rsi": [...],
              "macd": [...], "signal": [...], "hist": [...] },
  "indicadores": { "rsi": 44.1, "macd": 2.30, "signal": 5.80, "sma20": 303.88,
                   "sma50": 285.36, "senal": "hold", "confianza": 0.33 }
}
```

Las series se alinean por fecha con `ohlc`. **No** incluye fundamentales (el panel fundamental los
lee de `state.mercado`, ver §6.4).

---

## 6. Frontend (`frontend/index.html`)

Mantiene el triángulo `state → render() → eventos`, single-file, paleta Intel en custom properties,
manejo de loading/éxito/error, y la regla anti-XSS (sin `innerHTML` con dato crudo del servidor).

### 6.1 Modelo de estado

```js
const state = {
  view: 'dashboard',         // 'dashboard' | 'detalle'
  activos: [],               // ActivoDetalle (cards)
  cedears: [],               // data/cedears.json (autocompletado), cargado una vez
  mercado: [],               // filas de GET /mercado/cedears
  mercadoActualizado: null,  // timestamp "última actualización"
  mercadoSort: { col: null, dir: 'asc' },
  mercadoFiltro: '',         // filtro client-side de la tabla
  detalle: null,             // payload de historico del ticker abierto
  detalleTicker: null,
  loading: false, error: null,
};
```

`render()` despacha según `state.view`: dashboard (form + tabla + grid) o vista de detalle. Sigue
siendo la única función que toca el DOM.

### 6.2 Función 1 — Autocompletado del alta
- El campo de ticker se reemplaza por un input de búsqueda.
- Al tipear, filtra `state.cedears` por `ticker_byma` **o** `nombre` (case-insensitive); muestra
  máx. 8 en un dropdown con scroll interno.
- Al seleccionar: pre-llena los inputs `ticker`/`nombre`/`tipo`/`mercado` (siguen existiendo y son
  editables) y cierra el dropdown. Click afuera cierra.
- `POST /activos` sin cambios.
- El dropdown se construye con elementos creados / `textContent`, nunca `innerHTML` con dato crudo.

### 6.3 Función 2 — Tabla de mercado (entre el form y el grid)
- Toolbar: input **Filtrar** (client-side sobre `state.mercado`, sin nueva request) + botón
  **Actualizar** + leyenda "Última actualización: \<fecha/hora\>".
- Al cargar la página: `GET /mercado/cedears` lee lo que haya en la DB. Si vacío: mensaje
  "Presioná Actualizar para cargar los datos de mercado".
- **Botón Actualizar:** `POST /mercado/actualizar`; durante la corrida muestra spinner + "Cargando…"
  y queda deshabilitado (evita requests paralelos). **Al resolver, refetch obligatorio**
  `GET /mercado/cedears` → muta `state.mercado` + `state.mercadoActualizado` → `render()`. (El plan
  debe explicitar este segundo fetch para que no se omita.)
- Columnas: Ticker, Empresa, Precio (USD), Var % (▲ verde / ▼ roja), Volumen (formato 42.1K / 1.2M),
  RSI(14) (verde <30 / rojo >70 / neutro entre medio), Señal (badges existentes), P/E,
  Market Cap (2.8T / 340B). "—" donde el valor sea null.
- Click en header ordena asc/desc con flecha ↑/↓ (header activo marcado). Click en fila abre la
  vista de detalle de ese ticker.

### 6.4 Función 3 — Vista de detalle (Finviz + TradingView)
Se abre desde una fila de la tabla **o** desde una card del grid (ambas hacen lo mismo; el historial
inline de las cards desaparece — todo vive en el detalle). Botón "← Volver" regresa al dashboard.

- **Panel de métricas** (grilla de dos columnas):
  - *Técnico:* RSI(14), MACD vs señal, SMA20, SMA50, Señal, Confianza — de `state.detalle.indicadores`.
  - *Fundamental:* P/E, EPS, Market Cap, Volumen, Var %, 52w High/Low — leídos de la fila del ticker
    en `state.mercado`. Si el ticker **no** está en el snapshot, muestran "—".
- **Gráfico de velas:** `lightweight-charts` v5 desde **CDN pineado**. Candlestick + SMA20 (azul
  `#4A90D9`) / SMA50 (naranja `#F5A623`); pane RSI con líneas 30/70; pane MACD (línea + señal +
  histograma). Botones de período 1M / 3M / 6M / 1Y (default 3M). Cambiar período **refetchea**
  `GET /mercado/{ticker}/historico?periodo=X` (el servidor recalcula con `indicators.py`; no se
  duplica el cálculo en JS). Interactividad nativa de la librería (zoom, crosshair, scroll).
- **Historial de análisis:** se busca el ticker en `state.activos`. Si es un activo guardado →
  `GET /activos/{id}/analisis` y se muestra con mejor jerarquía (cada análisis en una fila
  horizontal). Si **no** es un activo → CTA "Agregar al monitoreo".

### 6.5 Paleta
Todo reutiliza las custom properties Intel + colores de señal ya en `:root`. No se hardcodean hex.

---

## 7. Dependencias

- **Python: ninguna nueva.** `ThreadPoolExecutor`, `subprocess`, `json`, `urllib` son stdlib; el
  resto ya está en `pyproject.toml` (fastapi, sqlmodel, yfinance, pandas, etc.).
- **Frontend:** `lightweight-charts` v5 por **CDN, con versión pineada** (sin `node_modules`, sin
  build; mantiene el paradigma single-file). Única dependencia externa nueva.

---

## 8. Tests

`pytest` + `TestClient` (FastAPI) sobre SQLite en memoria, siguiendo el patrón existente:

- `GET /mercado/cedears`: tabla vacía → `{ cedears: [], actualizado_en: null }`; con filas
  sembradas → las devuelve.
- `POST /mercado/actualizar`: se **mockea `subprocess.run`** (no se baja de yfinance); se verifica
  que el endpoint lo invoca y devuelve el shape `{ actualizados, actualizado_en }`.
- `GET /mercado/{ticker}/historico`: `subprocess.run` mockeado devolviendo JSON canónico; se
  verifica el passthrough de stdout y el manejo de período inválido (400).
- `scripts/prices.py::obtener_ohlc`: con un CSV OHLC cacheado (sin red).
- Indicadores: ya cubiertos; sin cambios.
- Frontend: sin tests automáticos (consistente con el estado actual).

---

## 9. Orden de construcción (openapi-first)

1. `openapi.yaml` — los 3 endpoints + schemas (`MercadoCedear`, `Historico`).
2. `data/cedears.json` (~30 US).
3. `backend/models.py` — modelos `MercadoCedear`.
4. `backend/main.py` — los 3 endpoints (2 vía subproceso).
5. `scripts/prices.py` — `obtener_ohlc` (aditivo).
6. `scripts/mercado.py` — descarga ThreadPool → persiste a la DB. Corrida de validación/curaduría
   de `cedears.json`.
7. `scripts/historico.py` — ticker+período → JSON por stdout.
8. Tests (endpoints con subprocess mockeado; `obtener_ohlc`).
9. `frontend/index.html` — estado, autocompletado, tabla, detalle, gráfico.
10. `CLAUDE.md` + `.claude/rules/` — documentar scripts nuevos, tabla `mercado_cedears`, CDN de
    lightweight-charts.

---

## 10. Decisiones del brainstorming (deltas y su razón)

1. **Universo = subconjunto curado (~30) de empresas US**, no todo BYMA en vivo. *Razón:* descargar
   300+ tickers en vivo es inviable y frágil para una demo; las empresas US tienen fundamentales
   completos en yfinance.
2. **Datos de mercado persistidos en la DB**, no en caché CSV efímera. *Razón:* descarga
   offline/a demanda + lectura instantánea blindan la demo; el `GET` queda idempotente.
3. **Precios en USD desde el ticker US** (`AAPL`, no `AAPL.BA`). *Razón:* el `.BA` no devuelve
   fundamentales (P/E, market cap, EPS, 52w) y suma complejidad de FX; el ticker US trae todo y un
   solo ticker por entrada simplifica el modelo. (Override explícito a `Ampliacion de funciones.md`,
   que pedía ARS desde `.BA`.)
4. **`POST /mercado/actualizar` + `GET /mercado/cedears`**, separados. *Razón:* REST correcto — la
   acción con efecto tiene su POST; la lectura queda idempotente y rápida.
5. **Backend dispara scripts por `subprocess`**, nunca importa yfinance. *Razón:* mantiene la regla
   dura "backend solo CRUD"; el subproceso aísla yfinance del proceso del backend.
6. **Routing de histórico bajo `/mercado/{ticker}/...`**, no `/activos/`. *Razón:* evita el choque
   con `/activos/{id:int}` y funciona para CEDEARs que no son activos guardados.
7. **`historico.py` devuelve solo OHLC + series/indicadores; los fundamentales se leen de
   `state.mercado`.** *Razón:* evita una llamada `.info` lenta/throttleable por cada apertura de
   detalle; más robusto para la demo.
8. **Recalcular indicadores por período en el servidor** (refetch), no en JS. *Razón:* no duplicar
   `indicators.py` en JavaScript; el cálculo queda determinístico y testeable en Python.
9. **Click en card y en fila → misma vista de detalle; historial inline eliminado.** *Razón:* un
   único lugar (métricas + gráfico + historial) es más limpio y consistente.
10. **Sin dependencias Python nuevas; lightweight-charts por CDN pineado.** *Razón:* mantener el
    backend liviano y el frontend single-file sin build.
