# Capa de Análisis (scripts/) Implementation Plan (Plan 2 de 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir la capa de análisis en `scripts/`: cálculo de indicadores técnicos reales (RSI/MACD/SMA), adquisición de precios con caché y fallback, la orquestación de `/generar-senal`, y el seed reproducible — todo fuera del backend.

**Architecture:** Cuatro módulos. `indicators.py` son funciones puras (sin red, testeables). `prices.py` trae precios de yfinance con caché en `data/prices_cache/` y fallback. `generar_senal.py` orquesta (precios → indicadores → POST a la API) y es lo que invoca la skill. `seed.py` inserta activos + análisis directo en la DB (misma cadena, con hardcode como último recurso). El backend NO se toca.

**Tech Stack:** Python 3.13, uv, pandas, yfinance. Cliente HTTP: `urllib` (stdlib). DB en el seed: SQLModel (reusa `backend/`).

> **DECISIÓN DE DEPENDENCIAS — leer y confirmar antes de ejecutar.** El spec original eligió
> `pandas-ta`. Durante el Plan 1 se pineó Python a 3.13 (por la incompatibilidad de SQLModel con
> `Literal`). `pandas-ta` (release `0.3.14b0` de PyPI) hace `from numpy import NaN`, removido en
> numpy 2; y numpy<2 no tiene wheels para Python 3.13. Resultado: `pandas-ta` no instala limpio en
> este toolchain. **Este plan calcula los indicadores a mano con `pandas`** (`rolling`/`ewm`),
> matemáticamente equivalente, con deps mínimas (`yfinance` + `pandas`). Si se prefiere `pandas-ta`,
> habría que despinear Python (revivir el problema de SQLModel) o usar un fork de git — no
> recomendado. Esta es la desviación principal vs. el spec; el resultado externo (señal, confianza,
> resumen) es idéntico.

**Contexto de referencia:** spec `docs/superpowers/specs/2026-06-13-dashboard-activos-financieros-design.md` (§4.1-4.4), y el backend ya implementado (`backend/main.py`, endpoint `POST /activos/{id}/analisis`).

**Reglas del dominio (del spec §4.2):**
- Indicadores: RSI(14), MACD(12,26,9), SMA(20,50).
- Voto por indicador: RSI `<30` compra, `>70` venta, `30-70` hold; MACD línea **>** señal compra, `<` venta (estado, no cruce); SMA20 `>` SMA50 compra, `<` venta.
- Señal final = voto de mayoría. Confianza = proporción que coincide (`0.33`/`0.67`/`1.0`).
- Empate a tres (los tres votan distinto) → `hold`, confianza `0.33`.
- `tipo sentimiento`: el script devuelve `400 - "tipo sentimiento no implementado en esta versión"`.

**Convenciones:** Español, sin emojis, comentarios solo los importantes. `API_BASE` por env (default `http://localhost:8000`). El seed crea AAPL, GOOGL, MSFT (`accion`, `NASDAQ`) con 1 análisis técnico cada uno; idempotente.

---

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `scripts/__init__.py` | Marca `scripts` como paquete |
| `scripts/indicators.py` | Funciones puras: `sma`, `rsi`, `macd`, y `analizar(close)` que devuelve señal/confianza/resumen |
| `scripts/prices.py` | `obtener_precios(ticker)` → (serie Close, procedencia, fecha) con caché + fallback |
| `scripts/generar_senal.py` | CLI/orquestación: args → precios → indicadores → POST; reporte |
| `scripts/seed.py` | Inserta 3 activos + 1 análisis técnico c/u en la DB (idempotente) |
| `tests/test_indicators.py` | Tests de los indicadores y del voto de mayoría (incluye empate) |
| `pyproject.toml` | Agregar deps `yfinance`, `pandas` (editar a mano + `uv sync`) |

> **Nota sobre `uv add`:** el `settings.json` endurecido deniega `uv add` (y patrones `http*`).
> Para agregar deps, **editar `pyproject.toml` a mano y correr `uv sync`** (permitido), no `uv add`.

---

## Task 0: Dependencias y paquete scripts

**Files:**
- Modify: `pyproject.toml`
- Create: `scripts/__init__.py` (vacío)

- [ ] **Step 1: Agregar deps en `pyproject.toml`**

En la lista `dependencies`, agregar `pandas` y `yfinance`:

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlmodel>=0.0.22",
    "pandas>=2.2",
    "yfinance>=0.2.40",
]
```

- [ ] **Step 2: Crear `scripts/__init__.py` vacío**

- [ ] **Step 3: Sincronizar**

Run: `uv sync`
Expected: instala pandas, yfinance (y sus deps: numpy, requests, etc.) sin errores.

- [ ] **Step 4: Verificar imports de las libs**

Run: `uv run python -c "import pandas, yfinance; print('deps OK')"`
Expected: `deps OK`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock scripts/__init__.py
git commit -m "chore: deps de analisis (pandas, yfinance) y paquete scripts"
```

---

## Task 1: Indicadores puros (TDD)

`indicators.py` no toca la red: recibe una serie de cierres (`pd.Series`) y devuelve los indicadores y la señal. Por eso se testea con series conocidas.

**Files:**
- Create: `tests/test_indicators.py`
- Create: `scripts/indicators.py`

- [ ] **Step 1: Escribir los tests**

```python
# tests/test_indicators.py
import pandas as pd

from scripts.indicators import analizar, macd, rsi, sma


def test_sma_calcula_promedio_movil():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    assert sma(s, 3).iloc[-1] == 4.0  # (3+4+5)/3


def test_rsi_sube_con_tendencia_alcista():
    # serie monotónica creciente -> RSI alto (cerca de 100)
    s = pd.Series(range(1, 60), dtype=float)
    assert rsi(s, 14).iloc[-1] > 70


def test_rsi_baja_con_tendencia_bajista():
    s = pd.Series(range(60, 1, -1), dtype=float)
    assert rsi(s, 14).iloc[-1] < 30


def test_macd_linea_sobre_senal_en_tendencia_alcista():
    s = pd.Series(range(1, 60), dtype=float)
    macd_line, signal_line = macd(s)
    assert macd_line.iloc[-1] > signal_line.iloc[-1]


def test_analizar_mayoria_compra_da_confianza_dos_tercios():
    # Tendencia alcista clara: RSI alto (venta) pero MACD y SMA en compra -> 2 compra / 1 venta
    s = pd.Series(range(1, 80), dtype=float)
    r = analizar(s)
    assert r["senal"] in {"compra", "venta", "hold"}
    assert r["confianza"] in {0.33, 0.67, 1.0}
    assert isinstance(r["resumen"], str) and r["resumen"]


def test_analizar_empate_a_tres_da_hold_033():
    # votos forzados manualmente a través de la función interna de voto de mayoría
    from scripts.indicators import _voto_mayoria
    senal, confianza = _voto_mayoria(["compra", "venta", "hold"])
    assert senal == "hold"
    assert confianza == 0.33


def test_analizar_unanimidad_da_confianza_uno():
    from scripts.indicators import _voto_mayoria
    senal, confianza = _voto_mayoria(["compra", "compra", "compra"])
    assert senal == "compra"
    assert confianza == 1.0
```

- [ ] **Step 2: Correr y ver fallar**

Run: `uv run pytest tests/test_indicators.py -v`
Expected: FAIL (ModuleNotFoundError `scripts.indicators`).

- [ ] **Step 3: Escribir `scripts/indicators.py`**

```python
from collections import Counter

import pandas as pd


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(window=period).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def _voto_rsi(valor: float) -> str:
    if valor < 30:
        return "compra"
    if valor > 70:
        return "venta"
    return "hold"


def _voto_macd(macd_val: float, signal_val: float) -> str:
    if macd_val > signal_val:
        return "compra"
    if macd_val < signal_val:
        return "venta"
    return "hold"


def _voto_sma(sma_corta: float, sma_larga: float) -> str:
    if sma_corta > sma_larga:
        return "compra"
    if sma_corta < sma_larga:
        return "venta"
    return "hold"


def _voto_mayoria(votos: list[str]) -> tuple[str, float]:
    conteo = Counter(votos)
    senal, n = conteo.most_common(1)[0]
    if n == 1:  # los tres votan distinto: sin mayoría
        return "hold", 0.33
    return senal, round(n / 3, 2)


def analizar(close: pd.Series) -> dict:
    rsi_val = float(rsi(close).iloc[-1])
    macd_line, signal_line = macd(close)
    macd_val = float(macd_line.iloc[-1])
    signal_val = float(signal_line.iloc[-1])
    sma20 = float(sma(close, 20).iloc[-1])
    sma50 = float(sma(close, 50).iloc[-1])

    v_rsi = _voto_rsi(rsi_val)
    v_macd = _voto_macd(macd_val, signal_val)
    v_sma = _voto_sma(sma20, sma50)
    senal, confianza = _voto_mayoria([v_rsi, v_macd, v_sma])

    rel = ">" if sma20 > sma50 else "<" if sma20 < sma50 else "="
    resumen = (
        f"RSI {rsi_val:.1f} ({v_rsi}), "
        f"MACD {macd_val:.2f} vs senal {signal_val:.2f} ({v_macd}), "
        f"SMA20 {sma20:.2f} {rel} SMA50 {sma50:.2f} ({v_sma}) "
        f"-> {senal} por mayoria"
    )
    return {
        "senal": senal,
        "confianza": confianza,
        "resumen": resumen,
        "rsi": rsi_val,
        "macd": macd_val,
        "signal": signal_val,
        "sma20": sma20,
        "sma50": sma50,
    }
```

- [ ] **Step 4: Correr y ver pasar**

Run: `uv run pytest tests/test_indicators.py -v`
Expected: PASS (7 tests). El test de unanimidad (`range(1,80)` creciente) puede dar `compra` 0.67 o 1.0 según RSI; el test solo verifica que `confianza ∈ {0.33,0.67,1.0}` y que hay resumen — no fija la señal exacta de ese caso para no acoplarse a los valores numéricos.

- [ ] **Step 5: Commit**

```bash
git add scripts/indicators.py tests/test_indicators.py
git commit -m "feat: indicadores RSI/MACD/SMA y voto de mayoria (calculo con pandas)"
```

---

## Task 2: Precios con caché y fallback

`prices.py` trae cierres históricos con la cascada: caché → red (yfinance) → none. Compartido por `generar_senal.py` y `seed.py`.

**Files:**
- Create: `scripts/prices.py`

- [ ] **Step 1: Escribir `scripts/prices.py`**

```python
import os

import pandas as pd

CACHE_DIR = os.path.join("data", "prices_cache")


def _cache_path(ticker: str) -> str:
    return os.path.join(CACHE_DIR, f"{ticker.upper()}.csv")


def _desde_cache(ticker: str):
    path = _cache_path(ticker)
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, parse_dates=["Date"]).set_index("Date")
    if df.empty or "Close" not in df.columns:
        return None
    fecha = df.index[-1].strftime("%Y-%m-%d")
    return df["Close"], "cache", fecha


def _desde_red(ticker: str):
    import yfinance as yf

    df = yf.Ticker(ticker).history(period="1y")
    if df is None or df.empty or "Close" not in df.columns:
        return None
    os.makedirs(CACHE_DIR, exist_ok=True)
    salida = df[["Close"]].copy()
    salida.index.name = "Date"
    salida.to_csv(_cache_path(ticker))
    fecha = df.index[-1].strftime("%Y-%m-%d")
    return df["Close"], "red", fecha


def obtener_precios(ticker: str):
    """Devuelve (close: pd.Series, procedencia: 'cache'|'red'|'none', fecha: str|None).

    Cascada: usa el CSV cacheado si existe; si no, baja de yfinance y lo cachea;
    si la red falla, devuelve (None, 'none', None).
    """
    cacheado = _desde_cache(ticker)
    if cacheado is not None:
        return cacheado
    try:
        red = _desde_red(ticker)
        if red is not None:
            return red
    except Exception:
        pass
    return None, "none", None
```

- [ ] **Step 2: Verificar que importa y que el caché-miss sin red no rompe**

Run: `uv run python -c "from scripts.prices import obtener_precios, _cache_path; print(_cache_path('aapl'))"`
Expected: imprime `data\prices_cache\AAPL.csv` (o con `/` según OS). Sin tocar la red.

- [ ] **Step 3: Commit**

```bash
git add scripts/prices.py
git commit -m "feat: precios con cache local y fallback (yfinance)"
```

(El comportamiento de red real se valida al correr el seed/skill en la verificación manual, Task 5 — no en tests automáticos, para no depender de yfinance en CI.)

---

## Task 3: Orquestación /generar-senal

`generar_senal.py` es lo que corre la skill. Usa `urllib` (stdlib) para hablar con la API — así no agrega un cliente HTTP como dependencia y evita el patrón `uv add http*` denegado.

**Files:**
- Create: `scripts/generar_senal.py`

- [ ] **Step 1: Escribir `scripts/generar_senal.py`**

```python
import json
import os
import sys
import urllib.error
import urllib.request

from scripts.indicators import analizar
from scripts.prices import obtener_precios

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")


def _get(path: str):
    with urllib.request.urlopen(f"{API_BASE}{path}", timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post(path: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}{path}", data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def generar(ticker: str, tipo: str = "tecnico") -> int:
    if tipo == "sentimiento":
        print("400 - tipo sentimiento no implementado en esta version")
        return 2
    if tipo != "tecnico":
        print(f"400 - tipo invalido: {tipo} (use tecnico)")
        return 2

    # Think: backend vivo + activo existe
    try:
        activos = _get("/activos")
    except urllib.error.URLError:
        print(f"Error: el backend no responde en {API_BASE}. Levantar el server primero.")
        return 1

    activo = next((a for a in activos if a["ticker"].upper() == ticker.upper()), None)
    if activo is None:
        print(f"Error: el ticker {ticker} no existe en la base. Crealo primero (formulario o seed).")
        return 1

    # Act: precios -> indicadores
    close, procedencia, fecha = obtener_precios(ticker)
    if procedencia == "none":
        print(f"Error: no se pudieron obtener precios de {ticker} (red caida y sin cache).")
        return 1

    res = analizar(close)
    estado, creado = _post(
        f"/activos/{activo['id']}/analisis",
        {"tipo": "tecnico", "senal": res["senal"], "confianza": res["confianza"], "resumen": res["resumen"]},
    )

    # Observe
    if estado != 201:
        print(f"Error: la API devolvio {estado} al crear el analisis.")
        return 1
    origen = "datos en vivo de yfinance" if procedencia == "red" else f"datos cacheados del {fecha}"
    print(f"Analisis tecnico generado para {ticker.upper()}")
    print(f"  Senal:     {creado['senal']}")
    print(f"  Confianza: {int(res['confianza'] * 100)}%")
    print(f"  Resumen:   {creado['resumen']}")
    print(f"  Analisis id: {creado['id']}  (created_at {creado['created_at']})")
    print(f"  Precios:   {origen}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Uso: generar_senal.py TICKER [tipo]")
        return 2
    ticker = argv[1]
    tipo = argv[2] if len(argv) > 2 else "tecnico"
    return generar(ticker, tipo)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 2: Verificar el camino de `sentimiento` sin backend**

Run: `uv run python scripts/generar_senal.py AAPL sentimiento`
Expected: imprime `400 - tipo sentimiento no implementado en esta version` y termina con código 2. (No toca la red ni el backend.)

- [ ] **Step 3: Commit**

```bash
git add scripts/generar_senal.py
git commit -m "feat: orquestacion /generar-senal (ReAct, urllib, 400 de sentimiento)"
```

---

## Task 4: Seed reproducible

`seed.py` inserta AAPL, GOOGL, MSFT con 1 análisis técnico cada uno, directo en la DB (no por la API). Misma cadena de precios; si la red falla y no hay caché, usa un análisis hardcodeado. Idempotente.

**Files:**
- Create: `scripts/seed.py`

- [ ] **Step 1: Escribir `scripts/seed.py`**

```python
from datetime import datetime, timezone

from sqlmodel import Session, select

from backend.database import create_db, engine
from backend.models import Activo, Analisis
from scripts.indicators import analizar
from scripts.prices import obtener_precios

ACTIVOS = [
    {"ticker": "AAPL", "nombre": "Apple Inc.", "tipo": "accion", "mercado": "NASDAQ"},
    {"ticker": "GOOGL", "nombre": "Alphabet Inc.", "tipo": "accion", "mercado": "NASDAQ"},
    {"ticker": "MSFT", "nombre": "Microsoft Corp.", "tipo": "accion", "mercado": "NASDAQ"},
]

# Análisis técnico de respaldo si no hay red ni caché (señal/confianza/resumen plausibles).
HARDCODE = {
    "AAPL": {"senal": "compra", "confianza": 0.67, "resumen": "RSI 45.0 (hold), MACD positivo (compra), SMA20 > SMA50 (compra) -> compra por mayoria"},
    "GOOGL": {"senal": "hold", "confianza": 0.33, "resumen": "RSI 55.0 (hold), MACD ~0 (hold), SMA20 ~ SMA50 (hold) -> hold"},
    "MSFT": {"senal": "venta", "confianza": 0.67, "resumen": "RSI 72.0 (venta), MACD negativo (venta), SMA20 < SMA50 (venta) -> venta por mayoria"},
}


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _analisis_de(ticker: str) -> dict:
    close, procedencia, _ = obtener_precios(ticker)
    if procedencia == "none":
        return HARDCODE[ticker]
    res = analizar(close)
    return {"senal": res["senal"], "confianza": res["confianza"], "resumen": res["resumen"]}


def seed() -> None:
    create_db()
    with Session(engine) as session:
        for datos in ACTIVOS:
            existe = session.exec(select(Activo).where(Activo.ticker == datos["ticker"])).first()
            if existe is not None:
                print(f"{datos['ticker']}: ya existe, se omite")
                continue
            activo = Activo(**datos)
            session.add(activo)
            session.commit()
            session.refresh(activo)

            a = _analisis_de(datos["ticker"])
            analisis = Analisis(
                activo_id=activo.id,
                tipo="tecnico",
                senal=a["senal"],
                confianza=a["confianza"],
                resumen=a["resumen"],
                created_at=_ahora_iso(),
            )
            session.add(analisis)
            session.commit()
            print(f"{datos['ticker']}: creado con analisis tecnico ({a['senal']})")


if __name__ == "__main__":
    seed()
```

- [ ] **Step 2: Verificar idempotencia con la DB real** (esta SÍ toca la DB local; la red puede o no estar)

Run: `uv run python scripts/seed.py`
Expected: primera corrida crea AAPL/GOOGL/MSFT con su análisis (usando red, caché o hardcode). 

Run de nuevo: `uv run python scripts/seed.py`
Expected: imprime "ya existe, se omite" para los tres — no duplica.

(Si preferís no correrlo vos en este punto, dejá la verificación para la Task 5 manual.)

- [ ] **Step 3: Commit**

```bash
git add scripts/seed.py
git commit -m "feat: seed idempotente (3 activos + analisis, cascada cache/red/hardcode)"
```

---

## Task 5: Verificación manual end-to-end (la hace el humano)

**Files:** ninguno (verificación). Requiere el backend corriendo.

- [ ] **Step 1:** Levantar el backend: `uv run uvicorn backend.main:app --reload --port 8000`
- [ ] **Step 2:** Sembrar: `uv run python scripts/seed.py` → 3 activos con análisis.
- [ ] **Step 3:** Generar una señal real: `uv run python scripts/generar_senal.py AAPL` → descarga precios, calcula, postea, e imprime el reporte con señal/confianza/resumen/id y la procedencia de los precios.
- [ ] **Step 4:** Probar el fallback de caché: cortar internet y correr de nuevo `generar_senal.py AAPL` → debe usar `data/prices_cache/AAPL.csv` e indicar "datos cacheados del <fecha>".
- [ ] **Step 5:** Probar `generar_senal.py AAPL sentimiento` → el 400 de no implementado.

---

## Self-Review (autor del plan)

**Cobertura del spec (subsistema B):**
- `indicators.py` puro con RSI/MACD/SMA + voto mayoría + empate→hold/0.33 (§4.2): Task 1. ✓
- `prices.py` con caché + fallback compartido (§4.1, §4.3): Task 2. ✓
- `generar_senal.py` ReAct (think/act/observe) + 400 de sentimiento (§4.3, §5.4): Task 3. ✓
- `seed.py` 3 activos + análisis técnico, cascada caché/red/hardcode, idempotente (§4.4): Task 4. ✓
- `test_indicators.py` (§8 del spec): Task 1. ✓
- Backend intacto (solo CRUD): ningún task lo modifica. ✓

**Consistencia de tipos/nombres:**
- `analizar(close)` devuelve dict con `senal`/`confianza`/`resumen` (+ valores crudos); `generar_senal` y `seed` consumen esas tres claves. ✓
- `obtener_precios` devuelve `(close, procedencia, fecha)` con `procedencia ∈ {cache, red, none}`; ambos consumidores chequean `== "none"`. ✓
- El POST arma `{tipo, senal, confianza, resumen}`, que matchea `AnalisisCreate` del backend. ✓

**Desviaciones declaradas:**
- `pandas` a mano en vez de `pandas-ta` (incompatibilidad con Python 3.13) — ver callout del header.
- `urllib` en vez de `httpx`/`requests` como cliente del script (cero deps extra + evita el deny de `uv add http*`).
- Los tests de indicadores no fijan la señal exacta de series reales (solo invariantes), para no acoplarse a valores numéricos; el voto de mayoría y el empate sí se testean de forma determinística vía `_voto_mayoria`.
