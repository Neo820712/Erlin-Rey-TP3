# Ampliación del dashboard (mercado + detalle) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar al dashboard tres funcionalidades — autocompletado en el alta, tabla de mercado persistida en la DB, y vista de detalle estilo Finviz + TradingView con gráfico de velas — sin que el backend toque yfinance.

**Architecture:** El backend sigue siendo CRUD puro: dos rutas nuevas delegan en scripts vía `subprocess` (que imprimen JSON por stdout), y una ruta lee una tabla nueva `mercado_cedears`. Los scripts (`mercado.py`, `historico.py`) usan yfinance + `indicators.py` y persisten/serializan. El frontend single-file gana un modelo de estado con `view` y una vista de detalle con lightweight-charts (CDN).

**Tech Stack:** FastAPI + SQLModel + SQLite (backend), Python stdlib `subprocess`/`concurrent.futures` + yfinance + pandas (scripts), HTML/CSS/JS vanilla single-file + lightweight-charts v5 por CDN (frontend), pytest + TestClient (tests).

**Contrato y convenciones de referencia:**
- Spec: `docs/superpowers/specs/2026-06-15-ampliacion-mercado-detalle-design.md`.
- `openapi.yaml` es la fuente de verdad: se edita **antes** que el código.
- Errores siempre con `HTTPException(status_code=..., detail={"message": "..."})`.
- Sin dependencias Python nuevas (todo stdlib + lo ya presente).
- Commits: GitHub Flow, en rama `feature/...`, nunca sobre `main`. Cada commit termina con el trailer
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. (El usuario controla cuándo se commitea;
  los pasos de commit documentan el punto de corte.)

**Preparación (antes de la Task 1):**

- [ ] Crear la rama de trabajo: `git checkout -b feature/ampliacion-mercado-detalle`
- [ ] Verificar baseline verde: `uv run pytest` → todos los tests actuales pasan.

---

### Task 1: Contrato OpenAPI de los 3 endpoints nuevos

**Files:**
- Modify: `openapi.yaml`

- [ ] **Step 1: Agregar los 3 paths nuevos**

En `openapi.yaml`, dentro de `paths:` (después del bloque `/activos/{id}/analisis/{analisisId}:` y antes de `components:`), agregar:

```yaml
  /mercado/cedears:
    get:
      summary: Snapshot de mercado de los CEDEARs (lee la DB)
      responses:
        '200':
          description: Filas de mercado y timestamp de última actualización
          content:
            application/json:
              schema: { $ref: '#/components/schemas/MercadoSnapshot' }
  /mercado/actualizar:
    post:
      summary: Dispara la descarga de datos de mercado y los persiste
      responses:
        '200':
          description: Resumen de la actualización
          content:
            application/json:
              schema: { $ref: '#/components/schemas/ActualizarResultado' }
        '500':
          description: Falló la descarga o la persistencia
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
  /mercado/{ticker}/historico:
    get:
      summary: OHLC e indicadores históricos para el gráfico de detalle
      parameters:
        - { name: ticker, in: path, required: true, schema: { type: string } }
        - name: periodo
          in: query
          required: false
          schema: { type: string, enum: [1m, 3m, 6m, 1y], default: 3m }
      responses:
        '200':
          description: OHLC + series e indicadores
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Historico' }
        '400':
          description: Período inválido
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
        '500':
          description: Falló la obtención de datos
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
```

- [ ] **Step 2: Agregar los schemas nuevos**

Dentro de `components: schemas:`, después de `Analisis:` y antes de `Error:`, agregar:

```yaml
    MercadoCedear:
      type: object
      required: [ticker_byma, ticker_us, nombre]
      properties:
        ticker_byma:  { type: string }
        ticker_us:    { type: string }
        nombre:       { type: string }
        precio_usd:   { type: [number, 'null'] }
        var_pct:      { type: [number, 'null'] }
        volumen:      { type: [integer, 'null'] }
        rsi:          { type: [number, 'null'] }
        senal:        { type: [string, 'null'], enum: [compra, venta, hold, null] }
        pe:           { type: [number, 'null'] }
        eps:          { type: [number, 'null'] }
        market_cap:   { type: [integer, 'null'] }
        w52_high:     { type: [number, 'null'] }
        w52_low:      { type: [number, 'null'] }
        actualizado_en: { type: [string, 'null'], format: date-time }
    MercadoSnapshot:
      type: object
      required: [cedears, actualizado_en]
      properties:
        cedears:
          type: array
          items: { $ref: '#/components/schemas/MercadoCedear' }
        actualizado_en: { type: [string, 'null'], format: date-time }
    ActualizarResultado:
      type: object
      required: [actualizados, actualizado_en]
      properties:
        actualizados:   { type: integer }
        actualizado_en: { type: string, format: date-time }
    Historico:
      type: object
      required: [ohlc, series, indicadores]
      properties:
        ohlc:
          type: array
          items:
            type: object
            required: [time, open, high, low, close]
            properties:
              time:  { type: string }
              open:  { type: number }
              high:  { type: number }
              low:   { type: number }
              close: { type: number }
        series:
          type: object
          properties:
            sma20:  { type: array, items: { type: [number, 'null'] } }
            sma50:  { type: array, items: { type: [number, 'null'] } }
            rsi:    { type: array, items: { type: [number, 'null'] } }
            macd:   { type: array, items: { type: [number, 'null'] } }
            signal: { type: array, items: { type: [number, 'null'] } }
            hist:   { type: array, items: { type: [number, 'null'] } }
        indicadores:
          type: object
          properties:
            rsi:       { type: [number, 'null'] }
            macd:      { type: [number, 'null'] }
            signal:    { type: [number, 'null'] }
            sma20:     { type: [number, 'null'] }
            sma50:     { type: [number, 'null'] }
            senal:     { type: [string, 'null'], enum: [compra, venta, hold, null] }
            confianza: { type: [number, 'null'] }
```

- [ ] **Step 3: Verificar que el YAML parsea**

Run: `uv run python -c "import yaml; yaml.safe_load(open('openapi.yaml', encoding='utf-8')); print('ok')"`
Expected: imprime `ok` (sin tracebacks).

- [ ] **Step 4: Commit**

```bash
git add openapi.yaml
git commit -m "feat: contrato de /mercado/cedears, /mercado/actualizar y /mercado/{ticker}/historico

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Lista curada `data/cedears.json`

**Files:**
- Create: `data/cedears.json`

- [ ] **Step 1: Crear el archivo con ~30 CEDEARs de empresas US**

Crear `data/cedears.json`. `ticker_byma == ticker_us` para empresas US; ambos campos presentes por claridad semántica. Lista inicial (se cura en la Task 11 con la corrida real):

```json
[
  { "ticker_byma": "AAPL",  "ticker_us": "AAPL",  "nombre": "Apple Inc.",                 "mercado": "NASDAQ", "tipo": "accion" },
  { "ticker_byma": "MSFT",  "ticker_us": "MSFT",  "nombre": "Microsoft Corp.",            "mercado": "NASDAQ", "tipo": "accion" },
  { "ticker_byma": "GOOGL", "ticker_us": "GOOGL", "nombre": "Alphabet Inc.",              "mercado": "NASDAQ", "tipo": "accion" },
  { "ticker_byma": "AMZN",  "ticker_us": "AMZN",  "nombre": "Amazon.com Inc.",            "mercado": "NASDAQ", "tipo": "accion" },
  { "ticker_byma": "META",  "ticker_us": "META",  "nombre": "Meta Platforms Inc.",        "mercado": "NASDAQ", "tipo": "accion" },
  { "ticker_byma": "NVDA",  "ticker_us": "NVDA",  "nombre": "NVIDIA Corp.",               "mercado": "NASDAQ", "tipo": "accion" },
  { "ticker_byma": "TSLA",  "ticker_us": "TSLA",  "nombre": "Tesla Inc.",                 "mercado": "NASDAQ", "tipo": "accion" },
  { "ticker_byma": "NFLX",  "ticker_us": "NFLX",  "nombre": "Netflix Inc.",               "mercado": "NASDAQ", "tipo": "accion" },
  { "ticker_byma": "AMD",   "ticker_us": "AMD",   "nombre": "Advanced Micro Devices Inc.","mercado": "NASDAQ", "tipo": "accion" },
  { "ticker_byma": "INTC",  "ticker_us": "INTC",  "nombre": "Intel Corp.",                "mercado": "NASDAQ", "tipo": "accion" },
  { "ticker_byma": "JPM",   "ticker_us": "JPM",   "nombre": "JPMorgan Chase & Co.",       "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "BAC",   "ticker_us": "BAC",   "nombre": "Bank of America Corp.",      "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "V",     "ticker_us": "V",     "nombre": "Visa Inc.",                  "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "MA",    "ticker_us": "MA",    "nombre": "Mastercard Inc.",            "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "KO",    "ticker_us": "KO",    "nombre": "Coca-Cola Co.",              "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "PEP",   "ticker_us": "PEP",   "nombre": "PepsiCo Inc.",               "mercado": "NASDAQ", "tipo": "accion" },
  { "ticker_byma": "MCD",   "ticker_us": "MCD",   "nombre": "McDonald's Corp.",           "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "DIS",   "ticker_us": "DIS",   "nombre": "Walt Disney Co.",            "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "NKE",   "ticker_us": "NKE",   "nombre": "Nike Inc.",                  "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "WMT",   "ticker_us": "WMT",   "nombre": "Walmart Inc.",               "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "JNJ",   "ticker_us": "JNJ",   "nombre": "Johnson & Johnson",          "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "PFE",   "ticker_us": "PFE",   "nombre": "Pfizer Inc.",                "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "XOM",   "ticker_us": "XOM",   "nombre": "Exxon Mobil Corp.",          "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "CVX",   "ticker_us": "CVX",   "nombre": "Chevron Corp.",              "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "BA",    "ticker_us": "BA",    "nombre": "Boeing Co.",                 "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "CAT",   "ticker_us": "CAT",   "nombre": "Caterpillar Inc.",           "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "IBM",   "ticker_us": "IBM",   "nombre": "IBM Corp.",                  "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "ORCL",  "ticker_us": "ORCL",  "nombre": "Oracle Corp.",               "mercado": "NYSE",   "tipo": "accion" },
  { "ticker_byma": "CSCO",  "ticker_us": "CSCO",  "nombre": "Cisco Systems Inc.",         "mercado": "NASDAQ", "tipo": "accion" },
  { "ticker_byma": "PYPL",  "ticker_us": "PYPL",  "nombre": "PayPal Holdings Inc.",       "mercado": "NASDAQ", "tipo": "accion" }
]
```

- [ ] **Step 2: Verificar que es JSON válido**

Run: `uv run python -c "import json; d=json.load(open('data/cedears.json', encoding='utf-8')); print(len(d), 'cedears')"`
Expected: imprime `30 cedears`.

- [ ] **Step 3: Commit**

```bash
git add data/cedears.json
git commit -m "feat: lista curada de CEDEARs US (data/cedears.json)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Modelos SQLModel de `mercado_cedears`

**Files:**
- Modify: `backend/models.py`
- Test: `tests/test_mercado.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_mercado.py`:

```python
def test_mercado_cedear_roundtrip(session):
    from backend.models import MercadoCedear

    fila = MercadoCedear(
        ticker_byma="AAPL", ticker_us="AAPL", nombre="Apple Inc.",
        precio_usd=190.5, var_pct=1.23, volumen=42100000,
        rsi=44.1, senal="hold",
        pe=28.4, eps=6.43, market_cap=2800000000000,
        w52_high=260.0, w52_low=164.0,
        actualizado_en="2026-06-15T12:00:00Z",
    )
    session.add(fila)
    session.commit()
    session.refresh(fila)
    assert fila.id is not None
    assert fila.senal == "hold"


def test_mercado_cedear_fundamentales_opcionales(session):
    from backend.models import MercadoCedear

    fila = MercadoCedear(
        ticker_byma="ZZZ", ticker_us="ZZZ", nombre="Sin fundamentales",
        precio_usd=10.0, var_pct=0.0, volumen=100, rsi=50.0, senal="hold",
        actualizado_en="2026-06-15T12:00:00Z",
    )
    session.add(fila)
    session.commit()
    session.refresh(fila)
    assert fila.pe is None and fila.market_cap is None and fila.w52_high is None
```

- [ ] **Step 2: Correr el test y verque falla**

Run: `uv run pytest tests/test_mercado.py -v`
Expected: FAIL con `ImportError` / `cannot import name 'MercadoCedear'`.

- [ ] **Step 3: Implementar los modelos**

En `backend/models.py`, al final del archivo, agregar:

```python
# --- MercadoCedear ---
class MercadoCedearBase(SQLModel):
    ticker_byma: str
    ticker_us: str
    nombre: str
    precio_usd: Optional[float] = None
    var_pct: Optional[float] = None
    volumen: Optional[int] = None
    rsi: Optional[float] = None
    senal: Optional[Senal] = None
    pe: Optional[float] = None
    eps: Optional[float] = None
    market_cap: Optional[int] = None
    w52_high: Optional[float] = None
    w52_low: Optional[float] = None
    actualizado_en: str


class MercadoCedearCreate(MercadoCedearBase):
    pass


class MercadoCedear(MercadoCedearBase, table=True):
    __tablename__ = "mercado_cedears"
    id: Optional[int] = Field(default=None, primary_key=True)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_mercado.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/models.py tests/test_mercado.py
git commit -m "feat: modelo MercadoCedear (snapshot de mercado en la DB)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Endpoint `GET /mercado/cedears`

**Files:**
- Modify: `backend/main.py`
- Test: `tests/test_mercado.py`

- [ ] **Step 1: Escribir el test que falla**

Agregar a `tests/test_mercado.py`:

```python
def _sembrar_fila(session, ticker="AAPL", actualizado="2026-06-15T12:00:00Z"):
    from backend.models import MercadoCedear
    fila = MercadoCedear(
        ticker_byma=ticker, ticker_us=ticker, nombre=f"{ticker} Inc.",
        precio_usd=100.0, var_pct=1.0, volumen=1000, rsi=50.0, senal="hold",
        actualizado_en=actualizado,
    )
    session.add(fila)
    session.commit()
    return fila


def test_get_mercado_vacio(client):
    resp = client.get("/mercado/cedears")
    assert resp.status_code == 200
    assert resp.json() == {"cedears": [], "actualizado_en": None}


def test_get_mercado_con_filas(client, session):
    _sembrar_fila(session, "AAPL")
    _sembrar_fila(session, "MSFT")
    resp = client.get("/mercado/cedears")
    assert resp.status_code == 200
    body = resp.json()
    assert {c["ticker_byma"] for c in body["cedears"]} == {"AAPL", "MSFT"}
    assert body["actualizado_en"] == "2026-06-15T12:00:00Z"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_mercado.py::test_get_mercado_vacio -v`
Expected: FAIL con 404 (la ruta no existe todavía).

- [ ] **Step 3: Implementar el endpoint**

En `backend/main.py`, agregar `MercadoCedear` al import desde `backend.models`:

```python
from backend.models import (
    Activo,
    ActivoCreate,
    ActivoDetalle,
    Analisis,
    AnalisisCreate,
    MercadoCedear,
    SenalesRecientes,
)
```

Y al final del archivo agregar:

```python
@app.get("/mercado/cedears")
def listar_mercado(session: Session = Depends(get_session)):
    filas = session.exec(select(MercadoCedear)).all()
    actualizado_en = filas[0].actualizado_en if filas else None
    return {"cedears": filas, "actualizado_en": actualizado_en}
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_mercado.py -v`
Expected: PASS (los nuevos + los de la Task 3).

- [ ] **Step 5: Commit**

```bash
git add backend/main.py tests/test_mercado.py
git commit -m "feat: GET /mercado/cedears (lee el snapshot de la DB)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Endpoint `POST /mercado/actualizar` (subprocess + stdout)

**Files:**
- Modify: `backend/main.py`
- Test: `tests/test_mercado.py`

El endpoint lanza `scripts/mercado.py` como subproceso; el script persiste a la DB e imprime por
stdout un JSON `{"actualizados": N, "actualizado_en": "..."}`. El backend devuelve ese JSON. En tests
se mockea `subprocess.run` para no tocar la red.

- [ ] **Step 1: Escribir el test que falla**

Agregar a `tests/test_mercado.py`:

```python
import json
import subprocess


def test_post_actualizar_devuelve_resumen(client, monkeypatch):
    salida = json.dumps({"actualizados": 30, "actualizado_en": "2026-06-15T12:00:00Z"})

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=0, stdout=salida, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    resp = client.post("/mercado/actualizar")
    assert resp.status_code == 200
    assert resp.json() == {"actualizados": 30, "actualizado_en": "2026-06-15T12:00:00Z"}


def test_post_actualizar_falla_devuelve_500(client, monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    resp = client.post("/mercado/actualizar")
    assert resp.status_code == 500
    assert "message" in resp.json()
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_mercado.py::test_post_actualizar_devuelve_resumen -v`
Expected: FAIL con 404 (la ruta no existe).

- [ ] **Step 3: Implementar el endpoint**

En `backend/main.py`, agregar a los imports del tope:

```python
import json
import subprocess
import sys
```

Y al final del archivo:

```python
def _correr_script(modulo: str, *args: str) -> str:
    """Corre `python -m scripts.<modulo> args...` y devuelve stdout. El backend no importa
    yfinance/pandas: delega en el subproceso. Lanza HTTPException(500) si el script falla."""
    cmd = [sys.executable, "-m", modulo, *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        logger.error("script %s falló (rc=%s): %s", modulo, proc.returncode, proc.stderr.strip())
        raise HTTPException(status_code=500, detail={"message": "Falló la actualización de datos de mercado."})
    return proc.stdout


@app.post("/mercado/actualizar")
def actualizar_mercado():
    stdout = _correr_script("scripts.mercado")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        logger.error("salida no-JSON de scripts.mercado: %r", stdout[:500])
        raise HTTPException(status_code=500, detail={"message": "Respuesta inválida del proceso de actualización."})
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_mercado.py -v`
Expected: PASS (incluidos los dos nuevos).

- [ ] **Step 5: Commit**

```bash
git add backend/main.py tests/test_mercado.py
git commit -m "feat: POST /mercado/actualizar (dispara scripts.mercado por subprocess)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Endpoint `GET /mercado/{ticker}/historico` (subprocess + validación)

**Files:**
- Modify: `backend/main.py`
- Test: `tests/test_mercado.py`

- [ ] **Step 1: Escribir el test que falla**

Agregar a `tests/test_mercado.py`:

```python
def test_get_historico_passthrough(client, monkeypatch):
    payload = {
        "ohlc": [{"time": "2026-01-02", "open": 1, "high": 2, "low": 0.5, "close": 1.5}],
        "series": {"sma20": [None], "sma50": [None], "rsi": [None], "macd": [None], "signal": [None], "hist": [None]},
        "indicadores": {"rsi": 44.1, "macd": 2.3, "signal": 5.8, "sma20": 1.0, "sma50": 1.0, "senal": "hold", "confianza": 0.33},
    }

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    resp = client.get("/mercado/AAPL/historico?periodo=3m")
    assert resp.status_code == 200
    assert resp.json() == payload


def test_get_historico_periodo_invalido_devuelve_400(client):
    resp = client.get("/mercado/AAPL/historico?periodo=5x")
    assert resp.status_code == 400
    assert "message" in resp.json()
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_mercado.py::test_get_historico_periodo_invalido_devuelve_400 -v`
Expected: FAIL con 404 (la ruta no existe).

- [ ] **Step 3: Implementar el endpoint**

En `backend/main.py`, al final del archivo:

```python
_PERIODOS_VALIDOS = {"1m", "3m", "6m", "1y"}


@app.get("/mercado/{ticker}/historico")
def historico_mercado(ticker: str, periodo: str = "3m"):
    if periodo not in _PERIODOS_VALIDOS:
        raise HTTPException(status_code=400, detail={"message": f"Período inválido: {periodo}."})
    stdout = _correr_script("scripts.historico", ticker, periodo)
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        logger.error("salida no-JSON de scripts.historico: %r", stdout[:500])
        raise HTTPException(status_code=500, detail={"message": "Respuesta inválida del proceso de histórico."})
```

Nota: `_correr_script` ya existe (Task 5). El mensaje de error 500 que emite menciona "actualización
de datos de mercado"; es aceptable como mensaje genérico para ambos endpoints.

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_mercado.py -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add backend/main.py tests/test_mercado.py
git commit -m "feat: GET /mercado/{ticker}/historico (delega en scripts.historico)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: `obtener_ohlc` en `scripts/prices.py`

**Files:**
- Modify: `scripts/prices.py`
- Test: `tests/test_prices.py`

Función aditiva: caché propia en `data/prices_cache/<TICKER>_ohlc.csv`, sin tocar `obtener_precios`.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_prices.py`:

```python
import os

import pandas as pd

from scripts import prices


def test_obtener_ohlc_lee_de_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path / "prices_cache"
    cache_dir.mkdir()
    monkeypatch.setattr(prices, "CACHE_DIR", str(cache_dir))

    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-02", "2026-01-03"], utc=True),
            "Open": [10.0, 11.0],
            "High": [12.0, 13.0],
            "Low": [9.0, 10.0],
            "Close": [11.0, 12.0],
            "Volume": [100, 200],
        }
    )
    df.to_csv(os.path.join(str(cache_dir), "AAPL_ohlc.csv"), index=False)

    ohlc, procedencia, fecha = prices.obtener_ohlc("AAPL")
    assert procedencia == "cache"
    assert list(ohlc.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(ohlc) == 2
    assert fecha == "2026-01-03"


def test_obtener_ohlc_sin_cache_ni_red_devuelve_none(tmp_path, monkeypatch):
    cache_dir = tmp_path / "prices_cache"
    cache_dir.mkdir()
    monkeypatch.setattr(prices, "CACHE_DIR", str(cache_dir))

    def fail(_ticker):
        raise RuntimeError("sin red")

    monkeypatch.setattr(prices, "_ohlc_desde_red", fail)
    ohlc, procedencia, fecha = prices.obtener_ohlc("ZZZZ")
    assert ohlc is None and procedencia == "none" and fecha is None
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_prices.py -v`
Expected: FAIL con `AttributeError: module 'scripts.prices' has no attribute 'obtener_ohlc'`.

- [ ] **Step 3: Implementar `obtener_ohlc`**

En `scripts/prices.py`, agregar al final del archivo:

```python
_OHLC_COLS = ["Open", "High", "Low", "Close", "Volume"]


def _ohlc_cache_path(ticker: str) -> str:
    if not _TICKER_VALIDO.fullmatch(ticker):
        raise ValueError(f"ticker invalido: {ticker!r}")
    return os.path.join(CACHE_DIR, f"{ticker.upper()}_ohlc.csv")


def _ohlc_desde_cache(ticker: str):
    path = _ohlc_cache_path(ticker)
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    if df.empty or "Date" not in df.columns or any(c not in df.columns for c in _OHLC_COLS):
        return None
    df["Date"] = pd.to_datetime(df["Date"], utc=True, errors="coerce")
    df = df.dropna(subset=["Date"]).set_index("Date")
    if df.empty:
        return None
    fecha = df.index[-1].strftime("%Y-%m-%d")
    return df[_OHLC_COLS], "cache", fecha


def _ohlc_desde_red(ticker: str):
    import yfinance as yf

    df = yf.Ticker(ticker).history(period="1y")
    if df is None or df.empty or any(c not in df.columns for c in _OHLC_COLS):
        return None
    os.makedirs(CACHE_DIR, exist_ok=True)
    salida = df[_OHLC_COLS].copy()
    salida.index.name = "Date"
    salida.to_csv(_ohlc_cache_path(ticker))
    fecha = df.index[-1].strftime("%Y-%m-%d")
    return df[_OHLC_COLS], "red", fecha


def obtener_ohlc(ticker: str, periodo: str = "1y"):
    """Devuelve (df_ohlcv: DataFrame[Open,High,Low,Close,Volume], procedencia, fecha).

    Cascada caché -> red -> none, análoga a obtener_precios pero con OHLCV completo y caché propia.
    El parámetro `periodo` se reserva para el recorte de la ventana en el llamador; la descarga
    siempre baja 1y para que los indicadores (SMA50) tengan historia suficiente.
    """
    cacheado = _ohlc_desde_cache(ticker)
    if cacheado is not None:
        return cacheado
    try:
        red = _ohlc_desde_red(ticker)
        if red is not None:
            return red
    except Exception as e:
        print(f"aviso: fallo al obtener OHLC de {ticker}: {e}", file=sys.stderr)
    return None, "none", None
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_prices.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/prices.py tests/test_prices.py
git commit -m "feat: obtener_ohlc en prices.py (OHLCV con caché propia)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: `scripts/historico.py` (JSON por stdout)

**Files:**
- Create: `scripts/historico.py`
- Test: `tests/test_historico.py`

El script arma el JSON del gráfico. Para que SMA50/RSI sean correctos incluso en ventanas cortas,
los indicadores se calculan sobre la serie **completa** y luego se recorta a la ventana del período.
La lógica de armado se aísla en `construir_historico(df, periodo)` (pura, testeable sin red).

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_historico.py`:

```python
import numpy as np
import pandas as pd

from scripts.historico import _ventana_dias, construir_historico


def _df_sintetico(n=120):
    idx = pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")
    close = pd.Series(np.linspace(100, 160, n), index=idx)
    return pd.DataFrame(
        {"Open": close - 1, "High": close + 1, "Low": close - 2, "Close": close, "Volume": 1000},
        index=idx,
    )


def test_ventana_dias_mapea_periodos():
    assert _ventana_dias("1m") == 22
    assert _ventana_dias("3m") == 66
    assert _ventana_dias("6m") == 126
    assert _ventana_dias("1y") == 252


def test_construir_historico_recorta_a_la_ventana():
    df = _df_sintetico(120)
    out = construir_historico(df, "1m")
    assert len(out["ohlc"]) == 22
    assert len(out["series"]["sma20"]) == 22
    assert set(out["ohlc"][0].keys()) == {"time", "open", "high", "low", "close"}


def test_construir_historico_indicadores_finales():
    df = _df_sintetico(120)
    out = construir_historico(df, "3m")
    ind = out["indicadores"]
    assert ind["senal"] in {"compra", "venta", "hold"}
    assert ind["sma20"] is not None and ind["sma50"] is not None
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_historico.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'scripts.historico'`.

- [ ] **Step 3: Implementar el script**

Crear `scripts/historico.py`:

```python
import json
import sys

import pandas as pd

from scripts.indicators import analizar, macd, rsi, sma
from scripts.prices import obtener_ohlc

_VENTANAS = {"1m": 22, "3m": 66, "6m": 126, "1y": 252}


def _ventana_dias(periodo: str) -> int:
    return _VENTANAS.get(periodo, _VENTANAS["3m"])


def _serie(valores: pd.Series) -> list:
    return [None if pd.isna(v) else round(float(v), 4) for v in valores]


def construir_historico(df: pd.DataFrame, periodo: str) -> dict:
    """Calcula indicadores sobre la serie completa y recorta la salida a la ventana del período.
    Pura: no toca la red. `df` indexado por fecha con columnas Open/High/Low/Close/Volume."""
    close = df["Close"]
    sma20 = sma(close, 20)
    sma50 = sma(close, 50)
    rsi14 = rsi(close, 14)
    macd_line, signal_line = macd(close)
    hist = macd_line - signal_line

    n = min(_ventana_dias(periodo), len(df))
    vista = df.iloc[-n:]
    idx = vista.index

    ohlc = [
        {
            "time": d.strftime("%Y-%m-%d"),
            "open": round(float(o), 4),
            "high": round(float(h), 4),
            "low": round(float(low), 4),
            "close": round(float(c), 4),
        }
        for d, o, h, low, c in zip(idx, vista["Open"], vista["High"], vista["Low"], vista["Close"])
    ]
    series = {
        "sma20": _serie(sma20.iloc[-n:]),
        "sma50": _serie(sma50.iloc[-n:]),
        "rsi": _serie(rsi14.iloc[-n:]),
        "macd": _serie(macd_line.iloc[-n:]),
        "signal": _serie(signal_line.iloc[-n:]),
        "hist": _serie(hist.iloc[-n:]),
    }
    ana = analizar(close)
    indicadores = {
        "rsi": round(ana["rsi"], 2),
        "macd": round(ana["macd"], 4),
        "signal": round(ana["signal"], 4),
        "sma20": round(ana["sma20"], 2),
        "sma50": round(ana["sma50"], 2),
        "senal": ana["senal"],
        "confianza": ana["confianza"],
    }
    return {"ohlc": ohlc, "series": series, "indicadores": indicadores}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(json.dumps({"error": "uso: historico.py TICKER [periodo]"}))
        return 2
    ticker = argv[1]
    periodo = argv[2] if len(argv) > 2 else "3m"
    df, procedencia, _ = obtener_ohlc(ticker, periodo)
    if procedencia == "none":
        print(json.dumps({"error": f"sin datos OHLC para {ticker}"}))
        return 1
    print(json.dumps(construir_historico(df, periodo)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_historico.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/historico.py tests/test_historico.py
git commit -m "feat: scripts/historico.py (OHLC + indicadores en JSON por stdout)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: `scripts/mercado.py` (descarga paralela → DB → resumen)

**Files:**
- Create: `scripts/mercado.py`
- Test: `tests/test_mercado_script.py`

La descarga de red queda aislada en `_datos_de_ticker(entrada)`; la lógica testeable es
`persistir(filas, actualizado_en)` (upsert por `ticker_byma` contra la DB) y `fila_desde(...)`
(arma el dict a partir de los datos crudos). El `main` orquesta con `ThreadPoolExecutor` e imprime
el resumen JSON.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_mercado_script.py`:

```python
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool

from backend.models import MercadoCedear
from scripts import mercado


def _engine_memoria():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    return eng


def test_fila_desde_arma_dict_completo():
    fila = mercado.fila_desde(
        entrada={"ticker_byma": "AAPL", "ticker_us": "AAPL", "nombre": "Apple Inc."},
        precio_usd=190.5, var_pct=1.23, volumen=42100000,
        rsi=44.1, senal="hold",
        info={"trailingPE": 28.4, "trailingEps": 6.43, "marketCap": 2800000000000,
              "fiftyTwoWeekHigh": 260.0, "fiftyTwoWeekLow": 164.0},
    )
    assert fila["ticker_byma"] == "AAPL"
    assert fila["pe"] == 28.4 and fila["market_cap"] == 2800000000000
    assert fila["w52_high"] == 260.0


def test_fila_desde_tolera_info_vacia():
    fila = mercado.fila_desde(
        entrada={"ticker_byma": "ZZZ", "ticker_us": "ZZZ", "nombre": "Z"},
        precio_usd=1.0, var_pct=0.0, volumen=1, rsi=50.0, senal="hold", info={},
    )
    assert fila["pe"] is None and fila["market_cap"] is None and fila["eps"] is None


def test_persistir_hace_upsert(monkeypatch):
    eng = _engine_memoria()
    monkeypatch.setattr(mercado, "engine", eng)

    filas_v1 = [{"ticker_byma": "AAPL", "ticker_us": "AAPL", "nombre": "Apple Inc.",
                 "precio_usd": 100.0, "var_pct": 1.0, "volumen": 10, "rsi": 50.0, "senal": "hold",
                 "pe": None, "eps": None, "market_cap": None, "w52_high": None, "w52_low": None}]
    mercado.persistir(filas_v1, "2026-06-15T12:00:00Z")

    filas_v2 = [{"ticker_byma": "AAPL", "ticker_us": "AAPL", "nombre": "Apple Inc.",
                 "precio_usd": 200.0, "var_pct": 2.0, "volumen": 20, "rsi": 60.0, "senal": "compra",
                 "pe": None, "eps": None, "market_cap": None, "w52_high": None, "w52_low": None}]
    mercado.persistir(filas_v2, "2026-06-15T13:00:00Z")

    with Session(eng) as s:
        todas = s.exec(select(MercadoCedear)).all()
        assert len(todas) == 1  # upsert, no duplica
        assert todas[0].precio_usd == 200.0
        assert todas[0].actualizado_en == "2026-06-15T13:00:00Z"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_mercado_script.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'scripts.mercado'`.

- [ ] **Step 3: Implementar el script**

Crear `scripts/mercado.py`:

```python
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sqlmodel import Session, select

from backend.database import create_db, engine
from backend.models import MercadoCedear
from scripts.indicators import analizar

CEDEARS_PATH = "data/cedears.json"
MAX_WORKERS = 25


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fila_desde(entrada, precio_usd, var_pct, volumen, rsi, senal, info) -> dict:
    """Arma el dict de una fila de mercado a partir de datos crudos + el .info de yfinance."""
    return {
        "ticker_byma": entrada["ticker_byma"],
        "ticker_us": entrada["ticker_us"],
        "nombre": entrada["nombre"],
        "precio_usd": precio_usd,
        "var_pct": var_pct,
        "volumen": volumen,
        "rsi": rsi,
        "senal": senal,
        "pe": info.get("trailingPE"),
        "eps": info.get("trailingEps"),
        "market_cap": info.get("marketCap"),
        "w52_high": info.get("fiftyTwoWeekHigh"),
        "w52_low": info.get("fiftyTwoWeekLow"),
    }


def _datos_de_ticker(entrada: dict) -> dict | None:
    """Descarga de red (yfinance) los datos de un ticker. Devuelve la fila o None si falla."""
    import yfinance as yf

    try:
        tk = yf.Ticker(entrada["ticker_us"])
        hist = tk.history(period="1y")
        if hist is None or hist.empty or "Close" not in hist.columns:
            return None
        close = hist["Close"].dropna()
        precio = float(close.iloc[-1])
        previo = float(close.iloc[-2]) if len(close) >= 2 else precio
        var_pct = round((precio - previo) / previo * 100, 2) if previo else 0.0
        volumen = int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else None
        try:
            ana = analizar(close)
            rsi_val, senal = round(ana["rsi"], 2), ana["senal"]
        except ValueError:
            rsi_val, senal = None, None
        info = {}
        try:
            info = tk.info or {}
        except Exception:
            info = {}
        return fila_desde(entrada, round(precio, 2), var_pct, volumen, rsi_val, senal, info)
    except Exception as e:
        print(f"aviso: fallo {entrada['ticker_us']}: {e}", file=sys.stderr)
        return None


def persistir(filas: list[dict], actualizado_en: str) -> int:
    """Upsert por ticker_byma. Devuelve la cantidad de filas escritas."""
    create_db()
    n = 0
    with Session(engine) as session:
        for f in filas:
            existente = session.exec(
                select(MercadoCedear).where(MercadoCedear.ticker_byma == f["ticker_byma"])
            ).first()
            if existente is None:
                existente = MercadoCedear(**f, actualizado_en=actualizado_en)
                session.add(existente)
            else:
                for k, v in f.items():
                    setattr(existente, k, v)
                existente.actualizado_en = actualizado_en
            n += 1
        session.commit()
    return n


def actualizar() -> dict:
    with open(CEDEARS_PATH, encoding="utf-8") as fh:
        entradas = json.load(fh)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        resultados = list(pool.map(_datos_de_ticker, entradas))
    filas = [r for r in resultados if r is not None]
    ts = _ahora_iso()
    n = persistir(filas, ts)
    return {"actualizados": n, "actualizado_en": ts}


def main() -> int:
    print(json.dumps(actualizar()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_mercado_script.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/mercado.py tests/test_mercado_script.py
git commit -m "feat: scripts/mercado.py (descarga paralela y persistencia con upsert)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Verificación end-to-end del backend (suite completa)

**Files:** (ninguno — verificación)

- [ ] **Step 1: Correr toda la suite**

Run: `uv run pytest -v`
Expected: PASS todos (los actuales + `test_mercado.py`, `test_prices.py`, `test_historico.py`, `test_mercado_script.py`).

- [ ] **Step 2: Verificar que el backend levanta y los endpoints existen en Swagger**

Run (en una terminal): `uv run uvicorn backend.main:app --port 8000`
Luego: abrir `http://localhost:8000/docs` y confirmar que aparecen `GET /mercado/cedears`,
`POST /mercado/actualizar` y `GET /mercado/{ticker}/historico`. Cortar el server (Ctrl-C).

Expected: los 3 endpoints listados, sin errores de arranque.

---

### Task 11: Corrida real de mercado + curaduría de `data/cedears.json`

**Files:**
- Modify (si hace falta): `data/cedears.json`

> Este paso toca la red (yfinance). Lo corre el usuario; no es automatizable en CI.

- [ ] **Step 1: Correr la descarga real una vez**

Run: `uv run python -m scripts.mercado`
Expected: imprime `{"actualizados": N, "actualizado_en": "..."}` con N cercano a 30 (~10-20s).

- [ ] **Step 2: Inspeccionar la calidad de los datos**

Run: `uv run python -c "import urllib.request,json; print(json.dumps(json.loads(urllib.request.urlopen('http://localhost:8000/mercado/cedears').read())['cedears'], indent=2, ensure_ascii=False))"`
(con el backend levantado), o consultar la tabla directamente.
Revisar qué tickers quedaron con `pe`, `market_cap`, `eps`, `w52_high`/`w52_low` en `null`.

- [ ] **Step 3: Curar la lista**

Sacar de `data/cedears.json` los tickers que no traen el set fundamental completo y reemplazarlos por
otras empresas US conocidas. Repetir Steps 1-2 hasta que los ~30 tengan datos completos.

- [ ] **Step 4: Commit (si cambió la lista)**

```bash
git add data/cedears.json
git commit -m "chore: curar data/cedears.json según la corrida real de yfinance

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Frontend — estilos, estado y andamiaje de la vista

**Files:**
- Modify: `frontend/index.html`

Esta task prepara el frontend: CSS nuevo, modelo de estado ampliado, carga de `cedears.json` y el
despacho de `render()` por `state.view`. Las funcionalidades concretas vienen en las Tasks 13-15.

- [ ] **Step 1: Agregar las custom properties y estilos nuevos**

En `frontend/index.html`, dentro de `:root` (después de `--radius: 8px;`), agregar colores del gráfico:

```css
      --chart-sma20: #4A90D9;
      --chart-sma50: #F5A623;
```

Antes de `footer { ... }` en el `<style>`, agregar los estilos de los componentes nuevos:

```css
    /* Autocompletado */
    .buscador { position: relative; }
    .dropdown {
      position: absolute; top: 100%; left: 0; right: 0; z-index: 10;
      background: var(--color-surface); border: 1px solid var(--color-border);
      border-radius: var(--radius); max-height: 240px; overflow-y: auto; margin-top: 2px;
    }
    .dropdown .opcion { padding: var(--space-sm); cursor: pointer; font-size: 0.85rem; }
    .dropdown .opcion:hover, .dropdown .opcion.activa { background: var(--color-bg); }
    .dropdown .opcion .tk { font-weight: 700; color: var(--color-primary-dark); margin-right: 6px; }

    /* Tabla de mercado */
    .toolbar { display: flex; align-items: center; gap: var(--space-md); flex-wrap: wrap; margin-bottom: var(--space-sm); }
    .toolbar .actualizado { color: var(--color-text-muted); font-size: 0.8rem; margin-left: auto; }
    .tabla-wrap { overflow-x: auto; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius); }
    table.mercado { border-collapse: collapse; width: 100%; font-size: 0.85rem; }
    table.mercado th, table.mercado td { padding: var(--space-sm); text-align: right; white-space: nowrap; border-bottom: 1px solid var(--color-border); }
    table.mercado th:nth-child(1), table.mercado td:nth-child(1),
    table.mercado th:nth-child(2), table.mercado td:nth-child(2) { text-align: left; }
    table.mercado th { cursor: pointer; color: var(--color-primary-dark); user-select: none; }
    table.mercado tbody tr { cursor: pointer; }
    table.mercado tbody tr:hover { background: var(--color-bg); }
    .var-pos { color: var(--color-compra); }
    .var-neg { color: var(--color-venta); }
    .rsi-bajo { color: var(--color-compra); }
    .rsi-alto { color: var(--color-venta); }

    /* Vista de detalle */
    .volver { background: none; color: var(--color-primary); padding: 0; margin-bottom: var(--space-md); }
    .volver:hover { background: none; text-decoration: underline; }
    .metricas { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); margin-bottom: var(--space-lg); }
    .metricas .panel { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius); padding: var(--space-md); }
    .metricas h3 { margin: 0 0 var(--space-sm); color: var(--color-primary-dark); font-size: 0.9rem; }
    .metricas .fila { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px dashed var(--color-border); font-size: 0.85rem; }
    .periodos { display: flex; gap: var(--space-sm); margin-bottom: var(--space-sm); }
    .periodos button.activo { background: var(--color-primary-dark); }
    #chart-velas, #chart-rsi, #chart-macd { width: 100%; }
    #chart-velas { height: 300px; } #chart-rsi { height: 90px; } #chart-macd { height: 90px; }
```

- [ ] **Step 2: Cargar lightweight-charts por CDN (versión pineada)**

En `<head>`, antes del `</head>`, agregar el script con **Subresource Integrity** (protege ante un
CDN comprometido):

```html
  <script src="https://unpkg.com/lightweight-charts@5.0.8/dist/lightweight-charts.standalone.production.js"
          integrity="sha384-REEMPLAZAR_POR_HASH_REAL" crossorigin="anonymous"></script>
```

Calcular el hash real una vez (no inventarlo): en bash,
`curl -s https://unpkg.com/lightweight-charts@5.0.8/dist/lightweight-charts.standalone.production.js | openssl dgst -sha384 -binary | openssl base64 -A`
y pegar el resultado como `sha384-<hash>` en `integrity`. Verificar en la consola del navegador que el
script carga sin error de integridad.

- [ ] **Step 3: Ampliar el modelo de estado**

Reemplazar el objeto `state` actual por:

```js
    const state = {
      view: 'dashboard',          // 'dashboard' | 'detalle'
      activos: [],
      cedears: [],                // data/cedears.json (autocompletado)
      mercado: [],                // filas de GET /mercado/cedears
      mercadoActualizado: null,   // timestamp
      mercadoSort: { col: null, dir: 'asc' },
      mercadoFiltro: '',
      detalle: null,              // payload de /historico del ticker abierto
      detalleTicker: null,
      detallePeriodo: '3m',
      seleccion: null,            // entrada de cedears elegida en el autocompletado
      loading: false,
      error: null,
    };
```

- [ ] **Step 4: Cargar `cedears.json` al iniciar**

Reemplazar la última línea del script (`cargarActivos();`) por:

```js
    async function cargarCedears() {
      try {
        const resp = await fetch('cedears.json');
        state.cedears = await resp.json();
      } catch (e) {
        state.cedears = [];  // el autocompletado queda vacío pero el alta manual sigue funcionando
      }
    }

    async function init() {
      await Promise.all([cargarActivos(), cargarCedears(), cargarMercado()]);
    }
    init();
```

(`cargarMercado` se define en la Task 14; hasta entonces el `init` fallará — está bien, las tasks de
frontend se ejecutan en orden y se verifican juntas en la Task 16.)

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat(front): estilos, estado ampliado y carga de cedears para la ampliación

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: Frontend — autocompletado del alta

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Reemplazar el campo ticker por el buscador en el HTML**

En el `<form id="form-activo">`, reemplazar el `<div class="campo">` del ticker (el primero) por:

```html
        <div class="campo buscador">
          <label for="f-busqueda">Buscar (ticker o empresa)</label>
          <input id="f-busqueda" autocomplete="off" placeholder="apple, AAPL…">
          <div id="dropdown"></div>
          <input id="f-ticker" name="ticker" type="hidden" required>
        </div>
```

- [ ] **Step 2: Renderizar el dropdown (sin innerHTML con dato crudo)**

Agregar estas funciones al script (antes de `function render()`):

```js
    function filtrarCedears(texto) {
      const q = texto.trim().toLowerCase();
      if (!q) return [];
      return state.cedears.filter((c) =>
        c.ticker_byma.toLowerCase().includes(q) || c.nombre.toLowerCase().includes(q)
      ).slice(0, 8);
    }

    function renderDropdown(texto) {
      const cont = document.getElementById('dropdown');
      cont.innerHTML = '';
      const opciones = filtrarCedears(texto);
      cont.className = opciones.length ? 'dropdown' : '';
      for (const c of opciones) {
        const div = document.createElement('div');
        div.className = 'opcion';
        const tk = document.createElement('span');
        tk.className = 'tk';
        tk.textContent = c.ticker_byma;            // textContent: a prueba de XSS
        div.appendChild(tk);
        div.appendChild(document.createTextNode(c.nombre));
        div.addEventListener('click', () => seleccionarCedear(c));
        cont.appendChild(div);
      }
    }

    function seleccionarCedear(c) {
      const f = document.getElementById('form-activo');
      document.getElementById('f-busqueda').value = `${c.ticker_byma} — ${c.nombre}`;
      f.ticker.value = c.ticker_byma;
      f.nombre.value = c.nombre;
      f.tipo.value = c.tipo;
      f.mercado.value = c.mercado;
      state.seleccion = c;
      document.getElementById('dropdown').innerHTML = '';
      document.getElementById('dropdown').className = '';
    }
```

- [ ] **Step 3: Cablear los eventos del buscador**

En la sección de `// --- eventos ---`, antes de `cargarActivos();`/`init();`, agregar:

```js
    document.getElementById('f-busqueda').addEventListener('input', (ev) => {
      renderDropdown(ev.target.value);
    });
    document.addEventListener('click', (ev) => {
      if (!ev.target.closest('.buscador')) {
        const d = document.getElementById('dropdown');
        d.innerHTML = ''; d.className = '';
      }
    });
```

- [ ] **Step 4: Ajustar el submit del form**

El handler de submit actual lee `f.ticker.value` (ahora hidden, llenado por la selección) — sigue
funcionando. Reemplazar el handler de submit por esta versión que también limpia el buscador:

```js
    document.getElementById('form-activo').addEventListener('submit', (ev) => {
      ev.preventDefault();
      const f = ev.target;
      altaActivo({
        ticker: f.ticker.value.trim(),
        nombre: f.nombre.value.trim(),
        tipo: f.tipo.value,
        mercado: f.mercado.value,
      });
      document.getElementById('f-busqueda').value = '';
      state.seleccion = null;
    });
```

- [ ] **Step 5: Verificación manual**

Servir el frontend (`python -m http.server 3000` desde `frontend/`) con el backend levantado.
Escribir "apple" en el buscador → aparece "AAPL — Apple Inc." en el dropdown; al clickearlo se
llenan los campos; "Agregar" crea el activo. Click fuera cierra el dropdown.

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html
git commit -m "feat(front): autocompletado de CEDEARs en el alta

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: Frontend — tabla de mercado

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Agregar la sección de la tabla al HTML**

Entre `</section>` del `#alta-activo` y `<section id="lista-activos">`, agregar:

```html
    <section id="mercado">
      <h2>Mercado (CEDEARs)</h2>
      <div class="toolbar">
        <input id="m-filtro" placeholder="🔍 Filtrar por ticker o empresa…" autocomplete="off">
        <button id="m-actualizar">↻ Actualizar</button>
        <span class="actualizado" id="m-actualizado"></span>
      </div>
      <div class="tabla-wrap"><table class="mercado" id="tabla-mercado"></table></div>
    </section>
```

- [ ] **Step 2: Helpers de formato y fetch de mercado**

Agregar al script (junto a las utilidades):

```js
    function fmtNum(v, dec = 2) {
      return v == null ? '—' : Number(v).toLocaleString('es-AR', { minimumFractionDigits: dec, maximumFractionDigits: dec });
    }
    function fmtAbrev(v) {
      if (v == null) return '—';
      const abs = Math.abs(v);
      if (abs >= 1e12) return (v / 1e12).toFixed(1) + 'T';
      if (abs >= 1e9) return (v / 1e9).toFixed(1) + 'B';
      if (abs >= 1e6) return (v / 1e6).toFixed(1) + 'M';
      if (abs >= 1e3) return (v / 1e3).toFixed(1) + 'K';
      return String(v);
    }

    async function cargarMercado() {
      try {
        const data = await api('/mercado/cedears');
        state.mercado = data.cedears || [];
        state.mercadoActualizado = data.actualizado_en;
      } catch (e) {
        state.error = `No se pudo cargar el mercado: ${e.message}`;
      }
      render();
    }

    async function actualizarMercado() {
      state.loading = true; state.error = null; render();
      try {
        await api('/mercado/actualizar', { method: 'POST' });
        await cargarMercado();   // refetch obligatorio: POST no devuelve las filas
      } catch (e) {
        state.error = `No se pudo actualizar el mercado: ${e.message}`;
      } finally {
        state.loading = false; render();
      }
    }
```

- [ ] **Step 3: Render de la tabla**

Agregar al script:

```js
    const COLS_MERCADO = [
      { key: 'ticker_byma', label: 'Ticker' },
      { key: 'nombre', label: 'Empresa' },
      { key: 'precio_usd', label: 'Precio (USD)' },
      { key: 'var_pct', label: 'Var %' },
      { key: 'volumen', label: 'Volumen' },
      { key: 'rsi', label: 'RSI(14)' },
      { key: 'senal', label: 'Señal' },
      { key: 'pe', label: 'P/E' },
      { key: 'market_cap', label: 'Market Cap' },
    ];

    function filasMercadoVisibles() {
      const q = state.mercadoFiltro.trim().toLowerCase();
      let filas = state.mercado.filter((c) =>
        !q || c.ticker_byma.toLowerCase().includes(q) || c.nombre.toLowerCase().includes(q));
      const { col, dir } = state.mercadoSort;
      if (col) {
        filas = [...filas].sort((a, b) => {
          const va = a[col], vb = b[col];
          if (va == null) return 1;
          if (vb == null) return -1;
          const cmp = typeof va === 'string' ? va.localeCompare(vb) : va - vb;
          return dir === 'asc' ? cmp : -cmp;
        });
      }
      return filas;
    }

    function celdaMercado(c, key) {
      if (key === 'var_pct') {
        if (c.var_pct == null) return { texto: '—', clase: '' };
        const flecha = c.var_pct >= 0 ? '▲' : '▼';
        return { texto: `${flecha} ${fmtNum(c.var_pct)}%`, clase: c.var_pct >= 0 ? 'var-pos' : 'var-neg' };
      }
      if (key === 'rsi') {
        if (c.rsi == null) return { texto: '—', clase: '' };
        const clase = c.rsi < 30 ? 'rsi-bajo' : c.rsi > 70 ? 'rsi-alto' : '';
        return { texto: fmtNum(c.rsi, 1), clase };
      }
      if (key === 'senal') return { texto: c.senal || '—', clase: '', pill: true };
      if (key === 'precio_usd') return { texto: fmtNum(c.precio_usd), clase: '' };
      if (key === 'pe') return { texto: fmtNum(c.pe), clase: '' };
      if (key === 'volumen') return { texto: fmtAbrev(c.volumen), clase: '' };
      if (key === 'market_cap') return { texto: fmtAbrev(c.market_cap), clase: '' };
      return { texto: c[key] == null ? '—' : String(c[key]), clase: '' };
    }

    function renderMercado() {
      const tabla = document.getElementById('tabla-mercado');
      if (!tabla) return;
      document.getElementById('m-actualizado').textContent =
        state.mercadoActualizado ? `Última actualización: ${state.mercadoActualizado}` : '';

      const filas = filasMercadoVisibles();
      const thead = document.createElement('thead');
      const trh = document.createElement('tr');
      for (const col of COLS_MERCADO) {
        const th = document.createElement('th');
        let marca = '';
        if (state.mercadoSort.col === col.key) marca = state.mercadoSort.dir === 'asc' ? ' ↑' : ' ↓';
        th.textContent = col.label + marca;
        th.addEventListener('click', () => {
          if (state.mercadoSort.col === col.key) {
            state.mercadoSort.dir = state.mercadoSort.dir === 'asc' ? 'desc' : 'asc';
          } else {
            state.mercadoSort = { col: col.key, dir: 'asc' };
          }
          render();
        });
        trh.appendChild(th);
      }
      thead.appendChild(trh);

      const tbody = document.createElement('tbody');
      if (!filas.length) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = COLS_MERCADO.length;
        td.style.textAlign = 'center';
        td.className = 'vacio';
        td.textContent = state.mercado.length
          ? 'Sin resultados para el filtro.'
          : 'Presioná Actualizar para cargar los datos de mercado.';
        tr.appendChild(td); tbody.appendChild(tr);
      } else {
        for (const c of filas) {
          const tr = document.createElement('tr');
          tr.addEventListener('click', () => abrirDetalle(c.ticker_byma));
          for (const col of COLS_MERCADO) {
            const td = document.createElement('td');
            const { texto, clase, pill } = celdaMercado(c, col.key);
            if (pill && c.senal) {
              const span = document.createElement('span');
              span.className = `pill ${claseSenal(c.senal)}`;
              span.textContent = c.senal;
              td.appendChild(span);
            } else {
              td.textContent = texto;
              if (clase) td.className = clase;
            }
            tr.appendChild(td);
          }
          tbody.appendChild(tr);
        }
      }
      tabla.innerHTML = '';
      tabla.appendChild(thead);
      tabla.appendChild(tbody);
    }
```

- [ ] **Step 4: Integrar `renderMercado` y el botón en `render()`**

Dentro de `function render()`, después de la línea que actualiza `#contador` (o al inicio del cuerpo),
agregar la llamada y el estado del botón:

```js
      renderMercado();
      const btnAct = document.getElementById('m-actualizar');
      if (btnAct) {
        btnAct.disabled = state.loading;
        btnAct.textContent = state.loading ? 'Cargando…' : '↻ Actualizar';
      }
```

Y en `// --- eventos ---` agregar:

```js
    document.getElementById('m-actualizar').addEventListener('click', actualizarMercado);
    document.getElementById('m-filtro').addEventListener('input', (ev) => {
      state.mercadoFiltro = ev.target.value; render();
    });
```

- [ ] **Step 5: Verificación manual**

Con backend levantado y datos ya descargados (Task 11): la tabla muestra las filas, "Última
actualización" con timestamp; filtrar reduce filas; click en header ordena (↑/↓); "Actualizar"
muestra "Cargando…", deshabilita el botón y al terminar refresca. Sin datos: muestra el mensaje
"Presioná Actualizar…".

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html
git commit -m "feat(front): tabla de mercado con filtro, orden y actualización

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 15: Frontend — vista de detalle con gráfico

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Contenedor de la vista de detalle en el HTML**

Después de `<section id="lista-activos">…</section>` (y antes de `</main>`), agregar:

```html
    <section id="detalle" style="display:none;">
      <button class="volver" id="btn-volver">← Volver</button>
      <h2 id="detalle-titulo"></h2>
      <div class="metricas">
        <div class="panel"><h3>Técnico</h3><div id="panel-tecnico"></div></div>
        <div class="panel"><h3>Fundamental</h3><div id="panel-fundamental"></div></div>
      </div>
      <div class="periodos" id="periodos"></div>
      <div id="chart-velas"></div>
      <div id="chart-rsi"></div>
      <div id="chart-macd"></div>
      <div id="detalle-historial"></div>
    </section>
```

- [ ] **Step 2: Despacho de vista en `render()`**

Al inicio de `function render()`, agregar el toggle de secciones:

```js
      const enDetalle = state.view === 'detalle';
      document.getElementById('detalle').style.display = enDetalle ? '' : 'none';
      ['alta-activo', 'mercado', 'lista-activos'].forEach((id) => {
        document.getElementById(id).style.display = enDetalle ? 'none' : '';
      });
      if (enDetalle) { renderDetalle(); return; }
```

- [ ] **Step 3: Abrir y cerrar el detalle**

Agregar al script:

```js
    async function abrirDetalle(ticker, periodo = '3m') {
      state.view = 'detalle';
      state.detalleTicker = ticker;
      state.detallePeriodo = periodo;
      state.detalle = null;
      state.loading = true; state.error = null; render();
      try {
        state.detalle = await api(`/mercado/${encodeURIComponent(ticker)}/historico?periodo=${periodo}`);
      } catch (e) {
        state.error = `No se pudo cargar el histórico de ${ticker}: ${e.message}`;
      } finally {
        state.loading = false; render();
      }
    }

    function volverDashboard() {
      state.view = 'dashboard';
      state.detalle = null; state.detalleTicker = null;
      render();
    }
```

- [ ] **Step 4: Render del detalle (paneles + historial + gráfico)**

Agregar al script:

```js
    function filaMetrica(label, valor) {
      const div = document.createElement('div');
      div.className = 'fila';
      const l = document.createElement('span'); l.textContent = label;
      const v = document.createElement('span'); v.textContent = valor;
      div.appendChild(l); div.appendChild(v);
      return div;
    }

    function renderPaneles() {
      const ind = (state.detalle && state.detalle.indicadores) || {};
      const m = state.mercado.find((c) => c.ticker_byma === state.detalleTicker) || {};

      const tec = document.getElementById('panel-tecnico');
      tec.innerHTML = '';
      tec.appendChild(filaMetrica('RSI (14)', ind.rsi != null ? fmtNum(ind.rsi, 1) : '—'));
      tec.appendChild(filaMetrica('MACD', ind.macd != null ? `${fmtNum(ind.macd)} vs ${fmtNum(ind.signal)}` : '—'));
      tec.appendChild(filaMetrica('SMA 20', ind.sma20 != null ? fmtNum(ind.sma20) : '—'));
      tec.appendChild(filaMetrica('SMA 50', ind.sma50 != null ? fmtNum(ind.sma50) : '—'));
      tec.appendChild(filaMetrica('Señal', ind.senal || '—'));
      tec.appendChild(filaMetrica('Confianza', ind.confianza != null ? `${Math.round(ind.confianza * 100)}%` : '—'));

      const fun = document.getElementById('panel-fundamental');
      fun.innerHTML = '';
      fun.appendChild(filaMetrica('P/E', fmtNum(m.pe)));
      fun.appendChild(filaMetrica('EPS (TTM)', fmtNum(m.eps)));
      fun.appendChild(filaMetrica('Market Cap', fmtAbrev(m.market_cap)));
      fun.appendChild(filaMetrica('Volumen', fmtAbrev(m.volumen)));
      fun.appendChild(filaMetrica('Var % (día)', m.var_pct != null ? `${fmtNum(m.var_pct)}%` : '—'));
      fun.appendChild(filaMetrica('52w High', fmtNum(m.w52_high)));
      fun.appendChild(filaMetrica('52w Low', fmtNum(m.w52_low)));
    }

    function renderPeriodos() {
      const cont = document.getElementById('periodos');
      cont.innerHTML = '';
      for (const p of ['1m', '3m', '6m', '1y']) {
        const b = document.createElement('button');
        b.textContent = p.toUpperCase();
        if (p === state.detallePeriodo) b.className = 'activo';
        b.addEventListener('click', () => abrirDetalle(state.detalleTicker, p));
        cont.appendChild(b);
      }
    }

    async function renderHistorialDetalle() {
      const cont = document.getElementById('detalle-historial');
      cont.innerHTML = '';
      const activo = state.activos.find((a) => a.ticker === state.detalleTicker);
      const h = document.createElement('h3'); h.textContent = 'Historial de análisis';
      cont.appendChild(h);
      if (!activo) {
        const p = document.createElement('p'); p.className = 'vacio';
        p.textContent = 'Este ticker no está en monitoreo. Agregalo desde el formulario para guardar análisis.';
        cont.appendChild(p);
        return;
      }
      try {
        const lista = await api(`/activos/${activo.id}/analisis`);
        if (!lista.length) {
          const p = document.createElement('p'); p.className = 'vacio'; p.textContent = 'Sin análisis todavía.';
          cont.appendChild(p); return;
        }
        for (const a of lista) {
          const item = document.createElement('div'); item.className = 'analisis-item';
          const l1 = document.createElement('div'); l1.className = 'linea1';
          const pill = document.createElement('span'); pill.className = `pill ${claseSenal(a.senal)}`; pill.textContent = a.senal;
          const meta = document.createElement('span'); meta.textContent = `${a.tipo} · ${Math.round((a.confianza || 0) * 100)}%`;
          const fecha = document.createElement('span'); fecha.className = 'fecha'; fecha.textContent = a.created_at;
          l1.append(pill, meta, fecha);
          const res = document.createElement('div'); res.className = 'resumen'; res.textContent = a.resumen;
          item.append(l1, res); cont.appendChild(item);
        }
      } catch (e) {
        const p = document.createElement('p'); p.className = 'estado error'; p.textContent = e.message;
        cont.appendChild(p);
      }
    }

    function renderDetalle() {
      document.getElementById('detalle-titulo').textContent = state.detalleTicker || '';
      renderPaneles();
      renderPeriodos();
      renderHistorialDetalle();
      dibujarGrafico();
    }
```

- [ ] **Step 5: Dibujar el gráfico con lightweight-charts**

Agregar al script:

```js
    function _puntos(series, ohlc) {
      // empareja cada valor con su fecha, descartando nulls (lightweight-charts no acepta null)
      return series.map((v, i) => (v == null ? null : { time: ohlc[i].time, value: v })).filter(Boolean);
    }

    function dibujarGrafico() {
      const cont = document.getElementById('chart-velas');
      const rsiCont = document.getElementById('chart-rsi');
      const macdCont = document.getElementById('chart-macd');
      cont.innerHTML = ''; rsiCont.innerHTML = ''; macdCont.innerHTML = '';
      if (!state.detalle || !state.detalle.ohlc || !window.LightweightCharts) return;
      const { ohlc, series } = state.detalle;

      const opts = { layout: { background: { color: '#fff' }, textColor: '#1a1a1a' }, height: cont.clientHeight,
        grid: { vertLines: { color: '#eef2f7' }, horzLines: { color: '#eef2f7' } } };

      const chart = LightweightCharts.createChart(cont, opts);
      const velas = chart.addCandlestickSeries({ upColor: '#1e7d34', downColor: '#c62828', borderVisible: false,
        wickUpColor: '#1e7d34', wickDownColor: '#c62828' });
      velas.setData(ohlc);
      chart.addLineSeries({ color: getCssVar('--chart-sma20'), lineWidth: 2 }).setData(_puntos(series.sma20, ohlc));
      chart.addLineSeries({ color: getCssVar('--chart-sma50'), lineWidth: 2 }).setData(_puntos(series.sma50, ohlc));
      chart.timeScale().fitContent();

      const rsiChart = LightweightCharts.createChart(rsiCont, { ...opts, height: rsiCont.clientHeight });
      rsiChart.addLineSeries({ color: '#0068b5', lineWidth: 1 }).setData(_puntos(series.rsi, ohlc));
      const rsiLine = rsiChart.addLineSeries({ color: '#0068b5' });
      rsiLine.createPriceLine({ price: 70, color: '#c62828', lineStyle: 2, lineWidth: 1 });
      rsiLine.createPriceLine({ price: 30, color: '#1e7d34', lineStyle: 2, lineWidth: 1 });
      rsiChart.timeScale().fitContent();

      const macdChart = LightweightCharts.createChart(macdCont, { ...opts, height: macdCont.clientHeight });
      macdChart.addHistogramSeries({ color: '#9aa5b1' }).setData(
        series.hist.map((v, i) => (v == null ? null : { time: ohlc[i].time, value: v,
          color: v >= 0 ? '#1e7d34' : '#c62828' })).filter(Boolean));
      macdChart.addLineSeries({ color: getCssVar('--chart-sma20'), lineWidth: 1 }).setData(_puntos(series.macd, ohlc));
      macdChart.addLineSeries({ color: getCssVar('--chart-sma50'), lineWidth: 1 }).setData(_puntos(series.signal, ohlc));
      macdChart.timeScale().fitContent();
    }

    function getCssVar(nombre) {
      return getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
    }
```

> Nota de compatibilidad: este código usa la API `addCandlestickSeries` / `addLineSeries` /
> `addHistogramSeries` de lightweight-charts v5.0.x (la versión pineada en el `<script>` del CDN). Si
> al verificar la consola del navegador muestra "addCandlestickSeries is not a function", confirmar
> que la URL del CDN apunta a `@5.0.8` y no a `latest`.

- [ ] **Step 6: Cablear "Volver" y el click en cards**

En `// --- eventos ---` agregar:

```js
    document.getElementById('btn-volver').addEventListener('click', volverDashboard);
```

Reemplazar el listener de click de las cards (dentro de `render()`, el bloque
`grid.querySelectorAll('.card').forEach(...)`) por:

```js
      grid.querySelectorAll('.card').forEach((el) => {
        el.addEventListener('click', () => abrirDetalle(el.dataset.ticker));
      });
```

Y en `cardHTML(activo)`, agregar `data-ticker` a la card y quitar el historial inline. Reemplazar la
función `cardHTML` por:

```js
    function cardHTML(activo) {
      const sr = activo.senales_recientes || {};
      return `
        <div class="card" data-id="${activo.id}" data-ticker="${esc(activo.ticker)}">
          <div class="card-top">
            <div>
              <div class="ticker">${esc(activo.ticker)}</div>
              <div class="nombre">${esc(activo.nombre)}</div>
            </div>
          </div>
          <div class="meta">${esc(activo.tipo)} · ${esc(activo.mercado)}</div>
          <div class="badges">
            ${badgeHTML('Técnico', sr.tecnico)}
            ${badgeHTML('Sentim.', sr.sentimiento)}
          </div>
        </div>`;
    }
```

(La función `historialHTML` y el estado `selectedActivoId`/`analisis` quedan sin uso; pueden
eliminarse en esta task. El historial ahora vive en la vista de detalle.)

- [ ] **Step 7: Verificación manual**

Con backend + datos: click en una fila de la tabla o en una card abre el detalle; paneles técnico y
fundamental con valores (fundamental "—" si el ticker no está en el snapshot); el gráfico de velas
con SMA20/SMA50 y los paneles RSI/MACD se dibujan; los botones de período recargan el gráfico;
"← Volver" regresa al dashboard. Revisar la consola del navegador sin errores.

- [ ] **Step 8: Commit**

```bash
git add frontend/index.html
git commit -m "feat(front): vista de detalle con métricas, gráfico de velas e historial

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 16: Documentación (CLAUDE.md y reglas)

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.claude/rules/backend.md`
- Modify: `.claude/rules/frontend.md`

- [ ] **Step 1: Actualizar la estructura del proyecto en `CLAUDE.md`**

En la sección "Estructura del proyecto" de `CLAUDE.md`, agregar bajo `scripts/`:

```
  mercado.py             descarga paralela de CEDEARs -> persiste en mercado_cedears
  historico.py           OHLC + indicadores para el grafico (JSON por stdout)
```

Y bajo `data/`:

```
  cedears.json           lista curada de CEDEARs US (autocompletado + tabla de mercado)
```

- [ ] **Step 2: Documentar los endpoints y la tabla nuevos en `CLAUDE.md`**

En la sección de comandos clave de `CLAUDE.md`, agregar:

```bash
# Descargar/actualizar el snapshot de mercado (offline, antes de la demo)
uv run python -m scripts.mercado
```

Y en "Reglas de arquitectura", agregar una línea:

```
- **El backend no descarga datos de mercado:** `POST /mercado/actualizar` y
  `GET /mercado/{ticker}/historico` lanzan `scripts/mercado.py` e `scripts/historico.py` como
  subprocesos (stdout JSON). La tabla `mercado_cedears` guarda el último snapshot.
```

- [ ] **Step 3: Actualizar las reglas**

En `.claude/rules/backend.md`, bajo la regla "El backend no toca el dominio externo", agregar:

```
- **Datos de mercado vía subprocess:** las rutas que necesitan yfinance (`/mercado/actualizar`,
  `/mercado/{ticker}/historico`) lanzan scripts con `subprocess.run([sys.executable, "-m", ...])`
  y parsean su stdout JSON. El backend nunca importa yfinance ni pandas, ni siquiera para mercado.
```

En `.claude/rules/frontend.md`, bajo "API base", agregar:

```
- **Gráfico:** lightweight-charts v5 por CDN pineado (no `node_modules`). Las series no aceptan
  `null`: filtrar los puntos nulos antes de `setData`.
- **Vista por `state.view`:** `render()` despacha entre dashboard y detalle; sigue siendo la única
  función que toca el DOM.
```

- [ ] **Step 4: Verificar el largo de `CLAUDE.md`**

Run: `uv run python -c "print(sum(1 for _ in open('CLAUDE.md', encoding='utf-8')), 'líneas')"`
Expected: cercano a 200 (si se pasó bastante, condensar; es un recordatorio del propio `CLAUDE.md`).

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md .claude/rules/backend.md .claude/rules/frontend.md
git commit -m "docs: documentar mercado/historico, tabla mercado_cedears y reglas de gráfico

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 17: Verificación final integral

**Files:** (ninguno — verificación)

- [ ] **Step 1: Suite completa verde**

Run: `uv run pytest -v`
Expected: PASS todos.

- [ ] **Step 2: Contrato vs implementación**

Levantar el backend y comparar `http://localhost:8000/docs` con `openapi.yaml`: los 3 endpoints
nuevos presentes, con los schemas `MercadoSnapshot`, `ActualizarResultado`, `Historico`.

- [ ] **Step 3: Recorrido manual de la demo**

Con backend + frontend servidos y datos descargados (Task 11):
1. Autocompletado: buscar y agregar un activo.
2. Tabla: filtrar, ordenar por una columna, "Actualizar" (refresca timestamp).
3. Detalle desde una fila y desde una card: paneles, gráfico (4 períodos), historial, "Volver".

Expected: todo funciona sin errores en la consola del navegador ni en el log del backend.

- [ ] **Step 4: Resumen de la rama**

Run: `git log --oneline feature/ampliacion-mercado-detalle ^main`
Expected: la secuencia de commits de las Tasks 1-16. Listo para PR (la integración a `main` la decide
el usuario, vía Pull Request — GitHub Flow).

---

## Self-Review (cobertura del spec)

- **§3 Fundación de datos** → Task 2 (`cedears.json`) + Task 11 (curaduría). Origen de datos: Task 9 (`mercado.py`) y Task 8 (`historico.py`).
- **§4 Backend/DB/API** → Task 1 (openapi), Task 3 (modelos), Tasks 4-6 (los 3 endpoints), pureza vía `_correr_script` (Task 5).
- **§5 Scripts** → Task 7 (`obtener_ohlc`), Task 9 (`mercado.py`), Task 8 (`historico.py`).
- **§6 Frontend** → Task 12 (estado/estilos), Task 13 (autocompletado), Task 14 (tabla, con refetch obligatorio en `actualizarMercado`), Task 15 (detalle + gráfico, fundamentales desde `state.mercado`, click card→detalle).
- **§7 Dependencias** → sin deps Python (verificado por ausencia de cambios en `pyproject.toml`); lightweight-charts CDN pineado (Task 12).
- **§8 Tests** → Tasks 3-9 (TDD; subprocess mockeado en Tasks 5-6; `obtener_ohlc` en Task 7).
- **§9 Orden de construcción** → el orden de las tasks lo respeta (openapi → datos → modelos → endpoints → scripts → tests → frontend → docs).
- **§10 Decisiones** → reflejadas en la arquitectura de cada task (subprocess, routing `/mercado/`, USD/ticker US, historico sin `.info`, recálculo server-side por período, card+fila→detalle).
