# Score técnico on-demand, cartera por checkbox y precios como fuente única — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar un score técnico 0-100 calculado en `scripts/`, disparable on-demand (skill + endpoint/botón), gestionar la cartera con un checkbox por fila, y mover los precios a una tabla `precios` como fuente única — sin romper el contrato.

**Architecture:** El cómputo del score vive en `scripts/indicators.py::analizar()` y lo comparten la skill, un endpoint nuevo `POST /activos/{id}/analisis/tecnico` (backend solo persiste; el cálculo corre en un subprocess de `scripts/`) y `/historico`. Los precios OHLC se persisten en una tabla `precios` (poblada solo por Actualizar) y todo lo demás lee de ahí. El frontend gestiona la cartera con checkboxes y muestra señal/score solo on-demand.

**Tech Stack:** FastAPI + SQLModel + SQLite, pandas (solo en `scripts/`), pytest, frontend vanilla single-file.

## Global Constraints

- `openapi.yaml` es la fuente de verdad: se edita **antes** que el código. Los 3 cambios de esta feature son **aditivos**.
- El backend **no importa** yfinance ni pandas: el cómputo corre en subprocess de `scripts/`; el backend solo persiste (CRUD).
- Schema de error único: `HTTPException(status_code=..., detail={"message": "..."})`.
- Sin emojis en código ni comentarios. Comentarios solo los importantes. En correcciones, sin comentarios que narren el cambio.
- Status codes: 200 GET, 201 POST que creó, 204 DELETE, 400 body/entrada inválida, 404 no existe, 500 interno.
- `logging`, nunca `print()` en `backend/`.
- GitHub Flow: rama `feature/score-tecnico-cartera-on-demand` (ya creada). No commitear sobre `main`.
- **Ejecución de comandos:** los `pytest` los corre el executor del plan. Los scripts del dominio que tocan red/DB/backend (`scripts.mercado`, `scripts.seed`, `scripts.generar_senal`) y la verificación en el navegador **los corre el usuario** (regla "crear, no correr"): el plan los deja listos y marca esos pasos como manuales.
- Comando de test: `uv run pytest <ruta>::<test> -v` desde la raíz del repo.

---

### Task 1: Contrato — 3 cambios aditivos en `openapi.yaml`

**Files:**
- Modify: `openapi.yaml`

**Interfaces:**
- Produces: `score` nullable en `AnalisisCreate`/`Analisis` y `SenalesRecientes`; path `POST /activos/{id}/analisis/tecnico`.

- [ ] **Step 1: Agregar `score` a `AnalisisCreate`**

En `components.schemas.AnalisisCreate.properties` (después de `resumen`):

```yaml
        resumen: { type: string }
        score: { type: [number, 'null'] }
```

- [ ] **Step 2: Agregar `score` a `SenalesRecientes`**

En `components.schemas.SenalesRecientes.properties` (después de `sentimiento`):

```yaml
        sentimiento: { type: [string, 'null'], enum: [compra, venta, hold, null] }
        score: { type: [number, 'null'] }
```

- [ ] **Step 3: Agregar el path `POST /activos/{id}/analisis/tecnico`**

Insertar bajo `paths`, después del bloque `/activos/{id}/analisis/{analisisId}`:

```yaml
  /activos/{id}/analisis/tecnico:
    post:
      summary: Computa el score tecnico desde precios y persiste el analisis
      parameters:
        - { name: id, in: path, required: true, schema: { type: integer } }
      responses:
        '201':
          description: Analisis tecnico creado (senal/confianza/resumen/score computados)
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Analisis' }
        '400':
          description: No hay precios para el ticker (correr Actualizar primero)
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
        '404':
          description: El activo no existe
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
        '500':
          description: Fallo el computo del score
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
```

- [ ] **Step 4: Verificar que el YAML parsea**

Run: `uv run python -c "import yaml; yaml.safe_load(open('openapi.yaml', encoding='utf-8')); print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add openapi.yaml
git commit -m "docs(openapi): score nullable en Analisis/SenalesRecientes y endpoint /analisis/tecnico"
```

---

### Task 2: Modelos — `Analisis.score`, `SenalesRecientes.score`, tabla `Precio`

**Files:**
- Modify: `backend/models.py`
- Test: `tests/test_models.py` (crear)

**Interfaces:**
- Produces: `Analisis(score: Optional[float])`, `SenalesRecientes(score: Optional[float])`, `Precio(ticker, fecha, open, high, low, close, volumen)` tabla `precios`.

- [ ] **Step 1: Escribir el test (falla)**

Crear `tests/test_models.py`:

```python
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.models import Analisis, Precio, SenalesRecientes


def _engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    return eng


def test_analisis_guarda_score():
    eng = _engine()
    with Session(eng) as s:
        a = Analisis(activo_id=1, tipo="tecnico", senal="compra", confianza=0.6,
                     resumen="x", score=80.0, created_at="2026-06-17T00:00:00Z")
        s.add(a); s.commit(); s.refresh(a)
        assert a.id is not None and a.score == 80.0


def test_analisis_score_es_opcional():
    a = Analisis(activo_id=1, tipo="tecnico", senal="hold", confianza=0.0,
                 resumen="x", created_at="2026-06-17T00:00:00Z")
    assert a.score is None


def test_senales_recientes_tiene_score():
    sr = SenalesRecientes()
    assert sr.score is None


def test_precio_roundtrip():
    eng = _engine()
    with Session(eng) as s:
        s.add(Precio(ticker="AAPL", fecha="2026-01-02", open=1.0, high=2.0, low=0.5,
                     close=1.5, volumen=100))
        s.commit()
        filas = s.exec(select(Precio).where(Precio.ticker == "AAPL")).all()
        assert len(filas) == 1 and filas[0].close == 1.5 and filas[0].volumen == 100
```

- [ ] **Step 2: Correr el test (falla)**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL (`ImportError: cannot import name 'Precio'` / `score`)

- [ ] **Step 3: Implementar en `backend/models.py`**

Agregar `score` a `AnalisisBase` (después de `resumen`):

```python
class AnalisisBase(SQLModel):
    tipo: TipoAnalisis
    senal: Senal
    confianza: float = Field(ge=0.0, le=1.0)
    resumen: str
    score: Optional[float] = None
```

Agregar `score` a `SenalesRecientes`:

```python
class SenalesRecientes(SQLModel):
    tecnico: Optional[Senal] = None
    sentimiento: Optional[Senal] = None
    score: Optional[float] = None
```

Agregar al final del archivo el modelo `Precio`:

```python
# --- Precio (tabla interna de OHLC, fuente unica de precios) ---
class PrecioBase(SQLModel):
    ticker: str
    fecha: str
    open: float
    high: float
    low: float
    close: float
    volumen: Optional[int] = None


class Precio(PrecioBase, table=True):
    __tablename__ = "precios"
    id: Optional[int] = Field(default=None, primary_key=True)
```

- [ ] **Step 4: Correr el test (pasa)**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/models.py tests/test_models.py
git commit -m "feat(models): score en Analisis/SenalesRecientes y tabla precios"
```

---

### Task 3: Fórmula del score en `scripts/indicators.py`

**Files:**
- Modify: `scripts/indicators.py`
- Test: `tests/test_indicators.py`

**Interfaces:**
- Consumes: `rsi`, `macd`, `sma` (ya existen en el módulo).
- Produces: `analizar(close) -> dict` con clave `score` (float 0-100); `senal` por banda; `confianza = |score-50|*2/100`. Helpers puros `_score_rsi`, `_score_tendencia`, `_score_macd`, `_senal_desde_score`, `_confianza_desde_score`.

- [ ] **Step 1: Reescribir los tests (fallan)**

Reemplazar en `tests/test_indicators.py` los tests de voto (`test_analizar_mayoria_da_estructura_valida`, `test_voto_mayoria_*`) por los del score. Mantener `test_sma_*`, `test_rsi_*`, `test_macd_*`, `test_analizar_serie_corta_falla`. Quedando:

```python
import pandas as pd

from scripts.indicators import analizar, macd, rsi, sma


def test_sma_calcula_promedio_movil():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    assert sma(s, 3).iloc[-1] == 4.0


def test_rsi_sube_con_tendencia_alcista():
    s = pd.Series(range(1, 60), dtype=float)
    assert rsi(s, 14).iloc[-1] > 70


def test_rsi_baja_con_tendencia_bajista():
    s = pd.Series(range(60, 1, -1), dtype=float)
    assert rsi(s, 14).iloc[-1] < 30


def test_macd_linea_sobre_senal_en_tendencia_alcista():
    s = pd.Series(range(1, 60), dtype=float)
    macd_line, signal_line = macd(s)
    assert macd_line.iloc[-1] > signal_line.iloc[-1]


def test_score_rsi_buckets():
    from scripts.indicators import _score_rsi
    assert _score_rsi(20) == 90
    assert _score_rsi(40) == 100
    assert _score_rsi(50) == 70
    assert _score_rsi(60) == 45
    assert _score_rsi(68) == 25
    assert _score_rsi(80) == 5


def test_score_tendencia():
    from scripts.indicators import _score_tendencia
    assert _score_tendencia(110, 105, 100) == 100
    assert _score_tendencia(90, 95, 100) == 0
    assert _score_tendencia(110, 95, 100) == 50


def test_score_macd():
    from scripts.indicators import _score_macd
    assert _score_macd(1.0, 0.5) == 100   # crece (+30) y >0 (+20)
    assert _score_macd(-0.5, -0.2) == 35  # baja (-15), <0
    assert _score_macd(0.5, 0.5) == 70    # plano, >0 (+20)


def test_senal_desde_score():
    from scripts.indicators import _senal_desde_score
    assert _senal_desde_score(70) == "compra"
    assert _senal_desde_score(50) == "hold"
    assert _senal_desde_score(20) == "venta"


def test_confianza_desde_score():
    from scripts.indicators import _confianza_desde_score
    assert _confianza_desde_score(50) == 0.0
    assert _confianza_desde_score(100) == 1.0
    assert _confianza_desde_score(10) == 0.8


def test_analizar_incluye_score_y_coherencia():
    s = pd.Series(range(1, 80), dtype=float)
    r = analizar(s)
    assert 0 <= r["score"] <= 100
    assert r["senal"] in {"compra", "venta", "hold"}
    assert r["confianza"] == round(abs(r["score"] - 50) * 2 / 100, 2)
    assert "Score" in r["resumen"]
    for k in ("rsi", "macd", "signal", "sma20", "sma50"):
        assert k in r


def test_analizar_serie_corta_falla():
    import pytest
    s = pd.Series(range(1, 30), dtype=float)
    with pytest.raises(ValueError):
        analizar(s)
```

- [ ] **Step 2: Correr los tests (fallan)**

Run: `uv run pytest tests/test_indicators.py -v`
Expected: FAIL (`cannot import name '_score_rsi'`)

- [ ] **Step 3: Implementar en `scripts/indicators.py`**

Eliminar `from collections import Counter` y los helpers `_voto_rsi`, `_voto_macd`, `_voto_sma`, `_voto_mayoria`. Agregar los helpers del score y reescribir `analizar`:

```python
def _score_rsi(rsi_val: float) -> float:
    if rsi_val <= 30:
        return 90.0
    if rsi_val <= 45:
        return 100.0
    if rsi_val <= 55:
        return 70.0
    if rsi_val <= 65:
        return 45.0
    if rsi_val <= 70:
        return 25.0
    return 5.0


def _score_tendencia(precio: float, sma20: float, sma50: float) -> float:
    s = 0.0
    if precio > sma50:
        s += 50.0
    if sma20 > sma50:
        s += 50.0
    return s


def _score_macd(hist_actual: float, hist_previo: float) -> float:
    s = 50.0
    if hist_actual > hist_previo:
        s += 30.0
    elif hist_actual < hist_previo:
        s -= 15.0
    if hist_actual > 0:
        s += 20.0
    return max(0.0, min(100.0, s))


def _senal_desde_score(score: float) -> str:
    if score >= 66:
        return "compra"
    if score < 33:
        return "venta"
    return "hold"


def _confianza_desde_score(score: float) -> float:
    return round(abs(score - 50) * 2 / 100, 2)


def analizar(close: pd.Series) -> dict:
    close = close.dropna()
    if len(close) < 50:
        raise ValueError(
            f"serie de precios insuficiente: {len(close)} cierres (se requieren >= 50 para SMA50)"
        )
    rsi_val = float(rsi(close).iloc[-1])
    macd_line, signal_line = macd(close)
    macd_val = float(macd_line.iloc[-1])
    signal_val = float(signal_line.iloc[-1])
    hist = macd_line - signal_line
    hist_actual = float(hist.iloc[-1])
    hist_previo = float(hist.iloc[-2])
    sma20 = float(sma(close, 20).iloc[-1])
    sma50 = float(sma(close, 50).iloc[-1])
    precio = float(close.iloc[-1])

    s_rsi = _score_rsi(rsi_val)
    s_tend = _score_tendencia(precio, sma20, sma50)
    s_macd = _score_macd(hist_actual, hist_previo)
    score = round(0.40 * s_rsi + 0.30 * s_tend + 0.30 * s_macd, 1)
    senal = _senal_desde_score(score)
    confianza = _confianza_desde_score(score)

    tend_txt = "alcista" if s_tend >= 100 else "mixta" if s_tend == 50 else "bajista"
    hist_dir = "creciente" if hist_actual > hist_previo else "decreciente" if hist_actual < hist_previo else "plano"
    resumen = (
        f"Score {score:.0f}/100 ({senal}). "
        f"RSI {rsi_val:.1f} [{s_rsi:.0f}], "
        f"Tendencia {tend_txt} [{s_tend:.0f}], "
        f"MACD hist {hist_actual:+.2f} {hist_dir} [{s_macd:.0f}]"
    )
    return {
        "senal": senal,
        "confianza": confianza,
        "score": score,
        "resumen": resumen,
        "rsi": rsi_val,
        "macd": macd_val,
        "signal": signal_val,
        "sma20": sma20,
        "sma50": sma50,
    }
```

- [ ] **Step 4: Correr los tests (pasan)**

Run: `uv run pytest tests/test_indicators.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/indicators.py tests/test_indicators.py
git commit -m "feat(indicators): score tecnico 0-100 ponderado; senal por banda; confianza = fuerza"
```

---

### Task 4: `scripts/prices.py` — precios como fuente única (reemplaza el caché CSV)

**Files:**
- Modify: `scripts/prices.py` (reescritura)
- Modify: `.gitignore`
- Delete: `data/prices_cache/.gitkeep`
- Test: `tests/test_prices.py` (reescritura)

**Interfaces:**
- Consumes: `backend.models.Precio`, `backend.database.engine`.
- Produces: `obtener_ohlc(ticker, periodo="1y", eng=engine) -> (DataFrame[Open,High,Low,Close,Volume]|None, 'db'|'none', fecha|None)`; `filas_precio_desde_df(ticker, df) -> list[dict]`; `guardar_ohlc(filas, eng=engine) -> int`.

- [ ] **Step 1: Reescribir los tests (fallan)**

Reemplazar todo `tests/test_prices.py` por:

```python
import numpy as np
import pandas as pd
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from scripts import prices


def _engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    return eng


def _df(n=60):
    idx = pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")
    close = pd.Series(np.linspace(100, 160, n), index=idx)
    return pd.DataFrame(
        {"Open": close - 1, "High": close + 1, "Low": close - 2, "Close": close, "Volume": 1000},
        index=idx,
    )


def test_filas_precio_desde_df():
    filas = prices.filas_precio_desde_df("aapl", _df(3))
    assert len(filas) == 3
    assert filas[0]["ticker"] == "AAPL"
    assert set(filas[0].keys()) == {"ticker", "fecha", "open", "high", "low", "close", "volumen"}
    assert filas[0]["volumen"] == 1000


def test_guardar_y_obtener_ohlc_roundtrip():
    eng = _engine()
    filas = prices.filas_precio_desde_df("AAPL", _df(60))
    n = prices.guardar_ohlc(filas, eng=eng)
    assert n == 60
    df, procedencia, fecha = prices.obtener_ohlc("AAPL", eng=eng)
    assert procedencia == "db"
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(df) == 60
    assert fecha == "2025-03-01"  # 60 dias desde 2025-01-01


def test_guardar_ohlc_reescribe_todo():
    eng = _engine()
    prices.guardar_ohlc(prices.filas_precio_desde_df("AAPL", _df(60)), eng=eng)
    prices.guardar_ohlc(prices.filas_precio_desde_df("MSFT", _df(60)), eng=eng)
    df_aapl, proc_aapl, _ = prices.obtener_ohlc("AAPL", eng=eng)
    assert proc_aapl == "none"  # el segundo guardar reescribio todo
    df_msft, proc_msft, _ = prices.obtener_ohlc("MSFT", eng=eng)
    assert proc_msft == "db"


def test_obtener_ohlc_sin_datos_devuelve_none():
    eng = _engine()
    df, procedencia, fecha = prices.obtener_ohlc("ZZZZ", eng=eng)
    assert df is None and procedencia == "none" and fecha is None
```

- [ ] **Step 2: Correr los tests (fallan)**

Run: `uv run pytest tests/test_prices.py -v`
Expected: FAIL (`module 'scripts.prices' has no attribute 'filas_precio_desde_df'`)

- [ ] **Step 3: Reescribir `scripts/prices.py`**

Reemplazar todo el archivo por:

```python
import pandas as pd
from sqlmodel import Session, SQLModel, select

from backend.database import engine
from backend.models import Precio

_OHLC_COLS = ["Open", "High", "Low", "Close", "Volume"]


def filas_precio_desde_df(ticker: str, df: pd.DataFrame) -> list[dict]:
    """Convierte un DataFrame OHLCV (indexado por fecha) en filas para la tabla precios."""
    filas = []
    for fecha, row in df.iterrows():
        vol = row["Volume"]
        filas.append(
            {
                "ticker": ticker.upper(),
                "fecha": fecha.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volumen": None if pd.isna(vol) else int(vol),
            }
        )
    return filas


def guardar_ohlc(filas: list[dict], eng=engine) -> int:
    """Reescribe la tabla precios completa: la descarta, la recrea e inserta las filas dadas.
    Mismo patron de snapshot que mercado.persistir. Devuelve cuantas filas escribio."""
    Precio.__table__.drop(eng, checkfirst=True)
    SQLModel.metadata.create_all(eng)
    with Session(eng) as session:
        for f in filas:
            session.add(Precio(**f))
        session.commit()
    return len(filas)


def obtener_ohlc(ticker: str, periodo: str = "1y", eng=engine):
    """Devuelve (df_ohlcv, procedencia, fecha) leyendo de la tabla precios.
    procedencia 'db' si hay filas, 'none' si no. `periodo` se reserva para el recorte en el llamador."""
    with Session(eng) as session:
        filas = session.exec(
            select(Precio).where(Precio.ticker == ticker.upper()).order_by(Precio.fecha)
        ).all()
    if not filas:
        return None, "none", None
    df = pd.DataFrame(
        {
            "Open": [f.open for f in filas],
            "High": [f.high for f in filas],
            "Low": [f.low for f in filas],
            "Close": [f.close for f in filas],
            "Volume": [f.volumen for f in filas],
        },
        index=pd.to_datetime([f.fecha for f in filas], utc=True),
    )
    df.index.name = "Date"
    return df[_OHLC_COLS], "db", filas[-1].fecha
```

- [ ] **Step 4: Limpiar el caché CSV**

En `.gitignore`, eliminar las dos líneas del caché de precios:

```
# Precios cacheados por yfinance (la carpeta se versiona con data/prices_cache/.gitkeep)
data/prices_cache/*.csv
```

Eliminar el archivo versionado:

```bash
git rm data/prices_cache/.gitkeep
```

- [ ] **Step 5: Correr los tests (pasan)**

Run: `uv run pytest tests/test_prices.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add scripts/prices.py tests/test_prices.py .gitignore
git commit -m "feat(prices): tabla precios como fuente unica; elimina cache CSV"
```

---

### Task 5: `scripts/mercado.py` — no calcula señal; persiste OHLC en `precios`

**Files:**
- Modify: `scripts/mercado.py`
- Test: `tests/test_mercado_script.py`

**Interfaces:**
- Consumes: `prices.filas_precio_desde_df`, `prices.guardar_ohlc`.
- Produces: `_datos_de_ticker(entrada) -> {"fila": dict, "precios": list[dict]} | None` con `fila["rsi"]=None`, `fila["senal"]=None`.

- [ ] **Step 1: Escribir el test nuevo (falla)**

Agregar a `tests/test_mercado_script.py`:

```python
def test_datos_de_ticker_sin_senal_ni_rsi_y_con_ohlc(monkeypatch):
    import sys
    import types

    import pandas as pd

    fake = types.ModuleType("yfinance")
    idx = pd.date_range("2025-01-01", periods=60, freq="D", tz="UTC")
    df = pd.DataFrame(
        {"Open": 1.0, "High": 2.0, "Low": 0.5, "Close": 1.5, "Volume": 100}, index=idx
    )

    class FakeTk:
        def __init__(self, _t):
            pass

        def history(self, period="1y"):
            return df

        @property
        def info(self):
            return {"trailingPE": 10}

    fake.Ticker = FakeTk
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    r = mercado._datos_de_ticker({"ticker_byma": "AAPL", "ticker_us": "AAPL", "nombre": "Apple"})
    assert r["fila"]["rsi"] is None and r["fila"]["senal"] is None
    assert len(r["precios"]) == 60
    assert r["precios"][0]["ticker"] == "AAPL"
```

- [ ] **Step 2: Correr el test (falla)**

Run: `uv run pytest tests/test_mercado_script.py::test_datos_de_ticker_sin_senal_ni_rsi_y_con_ohlc -v`
Expected: FAIL (devuelve la fila vieja sin clave `precios`)

- [ ] **Step 3: Modificar `scripts/mercado.py`**

Eliminar `from scripts.indicators import analizar`. Agregar `from scripts.prices import filas_precio_desde_df, guardar_ohlc`.

Reescribir `_datos_de_ticker`:

```python
def _datos_de_ticker(entrada: dict) -> dict | None:
    """Descarga de red (yfinance) los datos de un ticker. Devuelve {fila, precios} o None si falla."""
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
            info = tk.info or {}
        except Exception:
            info = {}
        fila = fila_desde(entrada, round(precio, 2), var_pct, volumen, None, None, info)
        precios = filas_precio_desde_df(entrada["ticker_byma"], hist)
        return {"fila": fila, "precios": precios}
    except Exception as e:
        print(f"aviso: fallo {entrada['ticker_us']}: {e}", file=sys.stderr)
        return None
```

Reescribir `actualizar`:

```python
def actualizar() -> dict:
    with open(CEDEARS_PATH, encoding="utf-8") as fh:
        entradas = json.load(fh)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        resultados = list(pool.map(_datos_de_ticker, entradas))
    ok = [r for r in resultados if r is not None]
    filas = [r["fila"] for r in ok]
    precios = [p for r in ok for p in r["precios"]]
    ts = _ahora_iso()
    n = persistir(filas, ts)
    guardar_ohlc(precios)
    return {"actualizados": n, "actualizado_en": ts}
```

`fila_desde` y `persistir` quedan **sin cambios** (los tests existentes los siguen cubriendo).

- [ ] **Step 4: Correr toda la suite del script (pasa)**

Run: `uv run pytest tests/test_mercado_script.py -v`
Expected: PASS (todos, incluido el nuevo)

- [ ] **Step 5: Commit**

```bash
git add scripts/mercado.py tests/test_mercado_script.py
git commit -m "feat(mercado): snapshot sin senal/rsi; persiste OHLC en precios"
```

---

### Task 6: `scripts/historico.py` — lee de `precios`; sin `score` en indicadores

**Files:**
- Modify: `scripts/historico.py` (solo si hiciera falta; `obtener_ohlc` mantiene firma)
- Test: `tests/test_historico.py`

**Interfaces:**
- Consumes: `prices.obtener_ohlc` (ya importado).
- Produces: `main(argv)` imprime el JSON de histórico leyendo de `precios`; `construir_historico` **no** agrega `score` a `indicadores`.

- [ ] **Step 1: Escribir el test del main (falla si hubiera regresión)**

Agregar a `tests/test_historico.py` (agregar `import json` arriba):

```python
def test_main_lee_de_obtener_ohlc_y_sin_score_en_indicadores(monkeypatch, capsys):
    import json

    import scripts.historico as h

    df = _df_sintetico(120)
    monkeypatch.setattr(h, "obtener_ohlc", lambda t, p="1y": (df, "db", "2025-04-30"))
    rc = h.main(["historico.py", "AAPL", "3m"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert "ohlc" in out and "indicadores" in out
    assert "score" not in out["indicadores"]
    assert out["indicadores"]["senal"] in {"compra", "venta", "hold"}
```

- [ ] **Step 2: Correr los tests (verificar)**

Run: `uv run pytest tests/test_historico.py -v`
Expected: el test nuevo PASA tal cual (firma de `obtener_ohlc` intacta y `construir_historico` ya no incluye `score`). Si fallara por `procedencia`, ver Step 3.

- [ ] **Step 3: Confirmar `construir_historico` y `main`**

`construir_historico` ya arma `indicadores` sin `score` (toma solo `rsi/macd/signal/sma20/sma50/senal/confianza` del dict de `analizar`); **no agregar** `score`. `main` ya hace `df, procedencia, _ = obtener_ohlc(ticker, periodo)` y corta con `procedencia == "none"`. No requiere cambios de código salvo que algún test falle; en ese caso ajustar `main` para que el chequeo sea `if df is None or procedencia == "none":`.

- [ ] **Step 4: Correr toda la suite (pasa)**

Run: `uv run pytest tests/test_historico.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/historico.py tests/test_historico.py
git commit -m "test(historico): lee de precios; confirma indicadores sin score"
```

---

### Task 7: `scripts/score_tecnico.py` — cómputo compartido (helper + CLI)

**Files:**
- Create: `scripts/score_tecnico.py`
- Test: `tests/test_score_tecnico.py` (crear)

**Interfaces:**
- Consumes: `indicators.analizar`, `prices.obtener_ohlc`.
- Produces: `computar(ticker) -> {"senal","confianza","resumen","score"}` (levanta `ValueError` si no hay precios); `main(argv)` imprime ese dict JSON (rc 0; en error imprime `{"error": ...}` con rc 0 para que el backend lo mapee a 400).

- [ ] **Step 1: Escribir los tests (fallan)**

Crear `tests/test_score_tecnico.py`:

```python
import json

import numpy as np
import pandas as pd
import pytest

import scripts.score_tecnico as st


def _df(n=80):
    idx = pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")
    close = pd.Series(np.linspace(100, 160, n), index=idx)
    return pd.DataFrame(
        {"Open": close, "High": close, "Low": close, "Close": close, "Volume": 1}, index=idx
    )


def test_computar_devuelve_las_cuatro_claves(monkeypatch):
    monkeypatch.setattr(st, "obtener_ohlc", lambda t, p="1y": (_df(), "db", "x"))
    r = st.computar("AAPL")
    assert set(r) == {"senal", "confianza", "resumen", "score"}
    assert 0 <= r["score"] <= 100


def test_computar_sin_precios_levanta(monkeypatch):
    monkeypatch.setattr(st, "obtener_ohlc", lambda t, p="1y": (None, "none", None))
    with pytest.raises(ValueError):
        st.computar("ZZZ")


def test_main_sin_precios_imprime_error_rc0(monkeypatch, capsys):
    monkeypatch.setattr(st, "obtener_ohlc", lambda t, p="1y": (None, "none", None))
    rc = st.main(["score_tecnico.py", "ZZZ"])
    assert rc == 0
    assert "error" in json.loads(capsys.readouterr().out)


def test_main_ok_imprime_json(monkeypatch, capsys):
    monkeypatch.setattr(st, "obtener_ohlc", lambda t, p="1y": (_df(), "db", "x"))
    rc = st.main(["score_tecnico.py", "AAPL"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert "score" in out and out["senal"] in {"compra", "venta", "hold"}
```

- [ ] **Step 2: Correr los tests (fallan)**

Run: `uv run pytest tests/test_score_tecnico.py -v`
Expected: FAIL (`No module named 'scripts.score_tecnico'`)

- [ ] **Step 3: Crear `scripts/score_tecnico.py`**

```python
import json
import sys

from scripts.indicators import analizar
from scripts.prices import obtener_ohlc


def computar(ticker: str) -> dict:
    """Lee OHLC de la tabla precios y computa el analisis tecnico (senal/confianza/resumen/score).
    Levanta ValueError si no hay precios o la serie es insuficiente."""
    df, procedencia, _ = obtener_ohlc(ticker)
    if procedencia == "none":
        raise ValueError(f"sin precios para {ticker} (corre Actualizar primero)")
    res = analizar(df["Close"])
    return {
        "senal": res["senal"],
        "confianza": res["confianza"],
        "resumen": res["resumen"],
        "score": res["score"],
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(json.dumps({"error": "uso: score_tecnico.py TICKER"}))
        return 0
    try:
        print(json.dumps(computar(argv[1])))
        return 0
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Correr los tests (pasan)**

Run: `uv run pytest tests/test_score_tecnico.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/score_tecnico.py tests/test_score_tecnico.py
git commit -m "feat(score_tecnico): helper computar() + CLI compartidos por skill y endpoint"
```

---

### Task 8: `scripts/generar_senal.py` — usa `computar()` y persiste `score`

**Files:**
- Modify: `scripts/generar_senal.py`

**Interfaces:**
- Consumes: `score_tecnico.computar`.
- Produces: POST a `/activos/{id}/analisis` con `score` incluido; reporte con la línea de score.

- [ ] **Step 1: Modificar `scripts/generar_senal.py`**

Reemplazar el import `from scripts.indicators import analizar` y `from scripts.prices import obtener_precios` por:

```python
from scripts.score_tecnico import computar
```

Reemplazar el bloque de cómputo y POST dentro de `generar` (desde `close, procedencia, fecha = obtener_precios(ticker)` hasta el `return 0`) por:

```python
    try:
        res = computar(ticker)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    estado, creado = _post(
        f"/activos/{activo['id']}/analisis",
        {
            "tipo": "tecnico",
            "senal": res["senal"],
            "confianza": res["confianza"],
            "resumen": res["resumen"],
            "score": res["score"],
        },
    )

    if estado != 201:
        print(f"Error: la API devolvio {estado} al crear el analisis.")
        return 1
    print(f"Analisis tecnico generado para {ticker.upper()}")
    print(f"  Score:     {res['score']:.0f}/100")
    print(f"  Senal:     {creado['senal']}")
    print(f"  Confianza: {int(res['confianza'] * 100)}%")
    print(f"  Resumen:   {creado['resumen']}")
    print(f"  Analisis id: {creado['id']}  (created_at {creado['created_at']})")
    print("  Precios:   tabla precios (ultimo Actualizar)")
    return 0
```

- [ ] **Step 2: Verificar import/sintaxis**

Run: `uv run python -c "import scripts.generar_senal; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Verificación manual (la corre el usuario)**

Con el backend levantado y `AAPL` en la cartera y precios cargados (Actualizar):
`uv run python scripts/generar_senal.py AAPL`
Esperado: reporte con línea `Score: NN/100` y `Analisis id`. (No lo ejecuta el agente.)

- [ ] **Step 4: Commit**

```bash
git add scripts/generar_senal.py
git commit -m "feat(generar_senal): comparte computar() y persiste el score"
```

---

### Task 9: Backend — endpoint `/analisis/tecnico` y `score` en `senales_recientes`

**Files:**
- Modify: `backend/main.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `_correr_script` (subprocess), `_activo_o_404`, modelos `Analisis`/`SenalesRecientes`.
- Produces: `POST /activos/{id}/analisis/tecnico` (201/400/404/500); `GET /activos/{id}` con `senales_recientes.score`.

- [ ] **Step 1: Escribir los tests (fallan)**

Agregar a `tests/test_api.py`:

```python
def test_detalle_activo_incluye_score(client):
    aid = _crear_activo(client)
    client.post(
        f"/activos/{aid}/analisis",
        json={"tipo": "tecnico", "senal": "compra", "confianza": 0.6, "resumen": "x", "score": 72.0},
    )
    sr = client.get(f"/activos/{aid}").json()["senales_recientes"]
    assert sr["tecnico"] == "compra" and sr["score"] == 72.0


def test_crear_analisis_tecnico_persiste_201(client, monkeypatch):
    import json
    import subprocess

    aid = _crear_activo(client)
    salida = json.dumps(
        {"senal": "compra", "confianza": 0.8, "resumen": "Score 90/100 (compra).", "score": 90.0}
    )

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=0, stdout=salida, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    resp = client.post(f"/activos/{aid}/analisis/tecnico")
    assert resp.status_code == 201
    body = resp.json()
    assert body["tipo"] == "tecnico" and body["senal"] == "compra" and body["score"] == 90.0
    assert body["activo_id"] == aid and body["created_at"]


def test_crear_analisis_tecnico_sin_precios_devuelve_400(client, monkeypatch):
    import json
    import subprocess

    aid = _crear_activo(client)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, returncode=0, stdout=json.dumps({"error": "sin precios para AAPL"}), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    resp = client.post(f"/activos/{aid}/analisis/tecnico")
    assert resp.status_code == 400
    assert "message" in resp.json()


def test_crear_analisis_tecnico_activo_inexistente_devuelve_404(client):
    resp = client.post("/activos/999/analisis/tecnico")
    assert resp.status_code == 404
    assert "message" in resp.json()
```

- [ ] **Step 2: Correr los tests (fallan)**

Run: `uv run pytest tests/test_api.py -k "tecnico or score" -v`
Expected: FAIL (404 de ruta inexistente / falta `score` en `senales_recientes`)

- [ ] **Step 3: Modificar `detalle_activo` en `backend/main.py`**

Dentro del loop de `detalle_activo`, setear el score del último técnico:

```python
    for tipo in ("tecnico", "sentimiento"):
        ultimo = session.exec(
            select(Analisis)
            .where(Analisis.activo_id == activo_id, Analisis.tipo == tipo)
            .order_by(Analisis.created_at.desc(), Analisis.id.desc())
        ).first()
        if ultimo is not None:
            setattr(senales, tipo, ultimo.senal)
            if tipo == "tecnico":
                senales.score = ultimo.score
```

- [ ] **Step 4: Agregar el endpoint `/analisis/tecnico`**

Insertar después de `crear_analisis` (antes de `borrar_analisis`):

```python
@app.post(
    "/activos/{activo_id}/analisis/tecnico",
    response_model=Analisis,
    status_code=status.HTTP_201_CREATED,
)
def crear_analisis_tecnico(activo_id: int, session: Session = Depends(get_session)):
    activo = _activo_o_404(activo_id, session)
    stdout = _correr_script("scripts.score_tecnico", activo.ticker)
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        logger.error("salida no-JSON de scripts.score_tecnico: %r", stdout[:500])
        raise HTTPException(status_code=500, detail={"message": "Respuesta inválida del cálculo técnico."})
    if "error" in data:
        raise HTTPException(status_code=400, detail={"message": data["error"]})
    analisis = Analisis(
        tipo="tecnico",
        senal=data["senal"],
        confianza=data["confianza"],
        resumen=data["resumen"],
        score=data["score"],
        activo_id=activo_id,
        created_at=_ahora_iso(),
    )
    session.add(analisis)
    session.commit()
    session.refresh(analisis)
    logger.info("201 análisis técnico id=%s activo=%s score=%s", analisis.id, activo_id, analisis.score)
    return analisis
```

- [ ] **Step 5: Correr los tests (pasan)**

Run: `uv run pytest tests/test_api.py -v`
Expected: PASS (incluidos los 4 nuevos y los existentes)

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/test_api.py
git commit -m "feat(api): POST /analisis/tecnico (subprocess + persiste) y score en senales_recientes"
```

---

### Task 10: `scripts/seed.py` — lee de `precios` con fallback HARDCODE y `score`

**Files:**
- Modify: `scripts/seed.py`

**Interfaces:**
- Consumes: `prices.obtener_ohlc`, `indicators.analizar`.
- Produces: seed offline-safe; `Analisis` con `score` (computado o null).

- [ ] **Step 1: Modificar `scripts/seed.py`**

Reemplazar `from scripts.prices import obtener_precios` por `from scripts.prices import obtener_ohlc`.

Actualizar `HARDCODE` con `score` coherente (confianza = |score-50|*2/100):

```python
HARDCODE = {
    "AAPL": {"senal": "compra", "confianza": 0.6, "score": 80.0, "resumen": "Score 80/100 (compra). Estructura alcista de corto."},
    "GOOGL": {"senal": "hold", "confianza": 0.0, "score": 50.0, "resumen": "Score 50/100 (hold). Sin sesgo claro."},
    "MSFT": {"senal": "venta", "confianza": 0.6, "score": 20.0, "resumen": "Score 20/100 (venta). RSI alto y tendencia debil."},
}
```

Reescribir `_analisis_de`:

```python
def _analisis_de(ticker: str) -> dict:
    df, procedencia, _ = obtener_ohlc(ticker)
    if procedencia == "none":
        return HARDCODE[ticker]
    try:
        res = analizar(df["Close"])
    except ValueError:
        return HARDCODE[ticker]
    return {
        "senal": res["senal"],
        "confianza": res["confianza"],
        "score": res["score"],
        "resumen": res["resumen"],
    }
```

En `seed()`, agregar `score` al crear el `Analisis`:

```python
            analisis = Analisis(
                activo_id=activo.id,
                tipo="tecnico",
                senal=a["senal"],
                confianza=a["confianza"],
                resumen=a["resumen"],
                score=a.get("score"),
                created_at=_ahora_iso(),
            )
```

- [ ] **Step 2: Verificar import/sintaxis**

Run: `uv run python -c "import scripts.seed; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Verificación manual (la corre el usuario)**

`uv run python scripts/seed.py` → crea 3 activos con análisis técnico (con score si hay precios, o HARDCODE). (No lo ejecuta el agente.)

- [ ] **Step 4: Commit**

```bash
git add scripts/seed.py
git commit -m "feat(seed): lee de precios con fallback HARDCODE; analisis con score"
```

---

### Task 11: Frontend — cartera por checkbox y tabla 100% mercado

**Files:**
- Modify: `frontend/index.html`

**Interfaces:**
- Consumes: `POST /activos`, `DELETE /activos/{id}`, `state.cedears` (catálogo), `state.activos`.
- Produces: tabla sin RSI/Señal, con columna checkbox; sin sección "Agregar activo".

- [ ] **Step 1: Eliminar la sección HTML `#alta-activo`**

Borrar el bloque completo `<section id="alta-activo"> ... </section>` (líneas ~171-201).

- [ ] **Step 2: Eliminar el JS del formulario**

Borrar las funciones `filtrarCedears`, `renderDropdown`, `seleccionarCedear`, `altaActivo`; el listener `form-activo` submit, el listener `f-busqueda` input y el listener `document` click que cierra el dropdown. Quitar `seleccion: null,` de `state`. **Mantener** `cargarCedears()` (se usa para resolver tipo/mercado del checkbox).

- [ ] **Step 3: Quitar `alta-activo` del toggle de vistas en `render()`**

```javascript
      ['mercado', 'lista-activos'].forEach((id) => {
        document.getElementById(id).style.display = enDetalle ? 'none' : '';
      });
```

- [ ] **Step 4: Sacar columnas RSI y Señal y agregar la de cartera**

Reemplazar `COLS_MERCADO`:

```javascript
    const COLS_MERCADO = [
      { key: 'ticker_byma', label: 'Ticker' },
      { key: 'nombre', label: 'Empresa' },
      { key: 'precio_usd', label: 'Precio (USD)' },
      { key: 'var_pct', label: 'Var %' },
      { key: 'volumen', label: 'Volumen' },
      { key: 'pe', label: 'P/E' },
      { key: 'market_cap', label: 'Market Cap' },
      { key: 'cartera', label: 'Cartera' },
    ];
```

En `celdaMercado`, eliminar las ramas `if (key === 'rsi')` y `if (key === 'senal')`.

- [ ] **Step 5: Agregar la función `toggleCartera` y resolver tipo/mercado del catálogo**

```javascript
    function activoDeTicker(tickerByma) {
      return state.activos.find((a) => a.ticker === tickerByma) || null;
    }

    async function toggleCartera(cedear, agregar) {
      state.loading = true; state.error = null; render();
      try {
        if (agregar) {
          const cat = state.cedears.find((c) => c.ticker_byma === cedear.ticker_byma);
          await api('/activos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              ticker: cedear.ticker_byma,
              nombre: cedear.nombre,
              tipo: cat ? cat.tipo : 'accion',
              mercado: cat ? cat.mercado : 'NASDAQ',
            }),
          });
        } else {
          const activo = activoDeTicker(cedear.ticker_byma);
          if (activo) await api(`/activos/${activo.id}`, { method: 'DELETE' });
        }
        await cargarActivos();
      } catch (e) {
        state.error = `No se pudo actualizar la cartera: ${e.message}`;
        state.loading = false; render();
      }
    }
```

- [ ] **Step 6: Renderizar la celda checkbox en `renderMercado`**

Dentro del loop de filas, en el armado de cada `td`, antes del bloque `if (pill && c.senal)`, manejar la columna `cartera`:

```javascript
          for (const col of COLS_MERCADO) {
            const td = document.createElement('td');
            if (col.key === 'cartera') {
              const chk = document.createElement('input');
              chk.type = 'checkbox';
              chk.checked = !!activoDeTicker(c.ticker_byma);
              chk.addEventListener('click', (ev) => ev.stopPropagation());
              chk.addEventListener('change', (ev) => toggleCartera(c, ev.target.checked));
              td.appendChild(chk);
              tr.appendChild(td);
              continue;
            }
            const { texto, clase } = celdaMercado(c, col.key);
            td.textContent = texto;
            if (clase) td.className = clase;
            tr.appendChild(td);
          }
```

(El `pill` ya no aplica porque se quitó la columna `senal`; el bloque de celda queda sin la rama pill.)

- [ ] **Step 7: Verificación manual (la corre el usuario)**

Levantar `start.bat`, abrir el dashboard. Verificar: no hay sección "Agregar activo"; la tabla no muestra RSI ni Señal; cada fila tiene un checkbox; tildar agrega el activo a "Cartera" (aparece card) y destildar lo quita; el checkbox no abre el detalle.

- [ ] **Step 8: Commit**

```bash
git add frontend/index.html
git commit -m "feat(front): cartera por checkbox; tabla de mercado 100% datos; sin form de alta"
```

---

### Task 12: Frontend — tarjeta Técnico (botón Analizar + score) y labels de cartera

**Files:**
- Modify: `frontend/index.html`

**Interfaces:**
- Consumes: `POST /activos/{id}/analisis/tecnico`, `GET /activos/{id}/analisis`, `senales_recientes.score`.
- Produces: tarjeta Técnico con botón "Analizar" + score/senal/resumen del último Analisis; cards con score; labels de cartera.

- [ ] **Step 1: Guardar el último análisis técnico al abrir el detalle**

En `state`, agregar `detalleAnalisisTecnico: null,`. En `abrirDetalle`, después de setear `state.detalle`, cargar el último técnico si el ticker está en la cartera:

```javascript
        state.detalle = { ...hist, fundamentales: fund };
        const activo = state.activos.find((a) => a.ticker === ticker);
        state.detalleAnalisisTecnico = null;
        if (activo) {
          const lista = await api(`/activos/${activo.id}/analisis`).catch(() => []);
          state.detalleAnalisisTecnico = lista.find((a) => a.tipo === 'tecnico') || null;
        }
```

- [ ] **Step 2: Función para disparar el análisis técnico**

```javascript
    async function analizarTecnico(ticker) {
      const activo = state.activos.find((a) => a.ticker === ticker);
      if (!activo) return;
      state.loading = true; state.error = null; render();
      try {
        await api(`/activos/${activo.id}/analisis/tecnico`, { method: 'POST' });
        await cargarActivos();
        await abrirDetalle(ticker, state.detallePeriodo);
      } catch (e) {
        state.error = `No se pudo analizar ${ticker}: ${e.message}`;
        state.loading = false; render();
      }
    }
```

- [ ] **Step 3: Reescribir el panel Técnico en `renderPaneles`**

Reemplazar el bloque "Tarjeta 3: Indicadores técnicos" por uno que muestre score/senal/resumen del último Analisis + botón Analizar; y quitar de "Datos de la acción" las filas de señal/confianza:

```javascript
      // Tarjeta 1: Datos de la accion (sin senal/confianza)
      const acc = document.getElementById('panel-accion');
      acc.innerHTML = '';
      acc.appendChild(filaMetrica('Precio (USD)', fmtNum(m.precio_usd)));
      acc.appendChild(filaMetrica('Var % (dia)', m.var_pct != null ? `${fmtNum(m.var_pct)}%` : '—'));
      acc.appendChild(filaMetrica('Volumen', fmtAbrev(m.volumen)));
      acc.appendChild(filaMetrica('Market Cap', fmtAbrev(m.market_cap)));
      acc.appendChild(filaMetrica('52w High', fmtNum(m.w52_high)));
      acc.appendChild(filaMetrica('52w Low', fmtNum(m.w52_low)));

      // Tarjeta 3: Tecnico (on-demand, desde el ultimo Analisis)
      const tec = document.getElementById('panel-tecnico');
      tec.innerHTML = '';
      const enCartera = !!state.activos.find((a) => a.ticker === state.detalleTicker);
      const an = state.detalleAnalisisTecnico;
      if (!enCartera) {
        const p = document.createElement('p'); p.className = 'vacio';
        p.textContent = 'Agregalo a la cartera (checkbox) para analizar.';
        tec.appendChild(p);
      } else {
        if (an) {
          tec.appendChild(filaSenal('Senal', an.senal));
          tec.appendChild(filaMetrica('Score', an.score != null ? `${Math.round(an.score)}/100` : '—'));
          tec.appendChild(filaMetrica('Confianza', an.confianza != null ? `${Math.round(an.confianza * 100)}%` : '—'));
          const res = document.createElement('div'); res.className = 'resumen'; res.textContent = an.resumen;
          tec.appendChild(res);
        } else {
          const p = document.createElement('p'); p.className = 'vacio';
          p.textContent = 'Sin analisis tecnico todavia.';
          tec.appendChild(p);
        }
        const btn = document.createElement('button');
        btn.textContent = state.loading ? 'Analizando…' : 'Analizar';
        btn.disabled = state.loading;
        btn.addEventListener('click', () => analizarTecnico(state.detalleTicker));
        tec.appendChild(btn);
      }
```

- [ ] **Step 4: Mostrar el score en las cards de la cartera (`cardHTML`)**

Reemplazar el bloque `badges` para incluir el score junto al badge técnico:

```javascript
    function cardHTML(activo) {
      const sr = activo.senales_recientes || {};
      const scoreTxt = sr.score != null ? ` · ${Math.round(sr.score)}` : '';
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
            <span class="badge ${claseSenal(sr.tecnico)}"><span class="etq">Tecnico</span>${esc(sr.tecnico ? sr.tecnico + scoreTxt : 'sin datos')}</span>
            ${badgeHTML('Sentim.', sr.sentimiento)}
          </div>
        </div>`;
    }
```

- [ ] **Step 5: Labels de cartera**

- En el HTML, `<h2>Activos monitoreados</h2>` -> `<h2>Cartera de inversión</h2>`.
- En `render()`, el contador:

```javascript
      document.getElementById('contador').textContent =
        state.activos.length ? `${state.activos.length} en cartera` : '';
```

- En `render()`, el texto de grid vacío:

```javascript
        grid.innerHTML = `<p class="vacio">Tu cartera está vacía. Tildá un ticker en la tabla de mercado.</p>`;
```

- En `renderHistorialDetalle`, el texto de no-monitoreo:

```javascript
        p.textContent = 'Este ticker no está en tu cartera. Tildalo en la tabla para guardar análisis.';
```

- [ ] **Step 6: Verificación manual (la corre el usuario)**

Con backend + precios cargados: abrir el detalle de un ticker en cartera; la tarjeta Técnico muestra "Sin análisis técnico todavía" + botón Analizar; al presionar Analizar aparece senal+score+resumen y la card de la cartera muestra el score; un ticker fuera de cartera muestra el hint. "Datos de la acción" ya no muestra señal/confianza.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html
git commit -m "feat(front): tarjeta tecnico on-demand con score; score en cards; labels de cartera"
```

---

### Task 13: Docs — `CLAUDE.md` y la skill `/generar-senal`

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.claude/skills/generar-senal/SKILL.md`

**Interfaces:**
- Produces: documentación coherente con la nueva arquitectura.

- [ ] **Step 1: Actualizar `CLAUDE.md` (mantener ≤ ~200 líneas)**

- En la estructura del proyecto: agregar `scripts/score_tecnico.py` (cómputo compartido por skill y endpoint); reemplazar `data/prices_cache/` por la tabla `precios`; nota de que `prices.py` es ingesta/lectura de `precios`.
- En reglas de arquitectura: "fuente única en la base: yfinance solo corre en `POST /mercado/actualizar`, que persiste OHLC en `precios`; `/historico` y el score leen de `precios`".
- Mencionar el nuevo endpoint `POST /activos/{id}/analisis/tecnico` (backend persiste; cómputo en subprocess).
- En convenciones de frontend: cartera por checkbox (sin formulario de alta); snapshot de mercado sin senal/rsi.
- En la skill: ahora reporta el score y comparte cómputo con el endpoint vía `scripts/score_tecnico.py`.

- [ ] **Step 2: Actualizar `SKILL.md`**

En la sección Observe, agregar el **score 0-100** a lo que se reporta. Reemplazar el ejemplo de salida para que incluya la línea de score, por ejemplo:

```
Análisis técnico generado para AAPL
  Score:     72/100
  Señal:     hold
  Confianza: 44%
  Resumen:   Score 72/100 (hold). RSI 75.2 [5], Tendencia alcista [100], MACD hist +0.80 creciente [100]
  Análisis id: 12  (created_at 2026-06-13T14:05:22Z)
  Precios:   tabla precios (último Actualizar)
```

Aclarar que el cómputo vive en `scripts/score_tecnico.py` (compartido con `POST /activos/{id}/analisis/tecnico`).

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md .claude/skills/generar-senal/SKILL.md
git commit -m "docs: fuente unica de precios, score y endpoint /analisis/tecnico en CLAUDE.md y skill"
```

---

### Task 14: Verificación final de la suite

**Files:** (ninguno)

- [ ] **Step 1: Correr toda la suite**

Run: `uv run pytest -v`
Expected: PASS (todos los tests)

- [ ] **Step 2: Verificación manual end-to-end (la corre el usuario)**

`start.bat` -> Actualizar (puebla `precios` + snapshot) -> tildar tickers en cartera -> abrir detalle -> Analizar -> ver score en tarjeta y card. `/generar-senal AAPL` desde Claude Code persiste otro análisis con score.

---

## Self-Review

**Spec coverage:**
- §3 disparadores: skill (Task 8) + endpoint/botón (Task 9, 12). ✓
- §4 fórmula score: Task 3. ✓
- §5.1 score en Analisis/AnalisisCreate: Task 1 + 2. ✓
- §5.2 endpoint /tecnico: Task 1 + 9. ✓
- §5.3 score en SenalesRecientes: Task 1 + 2 + 9 (backend) + 12 (front cards). ✓
- §6 backend solo persiste (subprocess): Task 9. ✓
- §7 tabla precios fuente única: Task 2 (modelo) + 4 (prices) + 5 (mercado puebla). ✓
- §8 scripts: indicators (3), prices (4), mercado (5), historico (6), score_tecnico (7), generar_senal (8), seed (10). ✓
- §9 frontend: Task 11 + 12. ✓
- §10 CLAUDE.md: Task 13. ✓
- §11 skill: Task 13. ✓
- §12 tests: cubiertos en cada task + Task 14. ✓
- §13 demo/offline: seed offline-safe (Task 10); start.bat sin cambios. ✓

**Placeholder scan:** sin TBD/TODO; todo paso con código o comando concreto.

**Type consistency:** `obtener_ohlc(ticker, periodo, eng)` y `computar(ticker) -> {senal,confianza,resumen,score}` usados consistentemente en Tasks 4/6/7/8/9; `_datos_de_ticker -> {"fila","precios"}` en Task 5; `senales_recientes.score` en Tasks 9/12.

---

## Execution Handoff

Plan completo y guardado en `docs/superpowers/plans/2026-06-17-score-tecnico-cartera-on-demand.md`. Dos opciones de ejecución:

1. **Subagent-Driven (recomendada)** — despacho un subagente fresco por task, reviso entre tasks, iteración rápida.
2. **Inline Execution** — ejecuto las tasks en esta sesión con executing-plans, por lotes con checkpoints.

¿Cuál preferís?
