import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sqlmodel import Session, SQLModel, select

from backend.database import engine
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
        try:
            info = tk.info or {}
        except Exception:
            info = {}
        return fila_desde(entrada, round(precio, 2), var_pct, volumen, rsi_val, senal, info)
    except Exception as e:
        print(f"aviso: fallo {entrada['ticker_us']}: {e}", file=sys.stderr)
        return None


def persistir(filas: list[dict], actualizado_en: str) -> int:
    """Upsert por ticker_byma y borra los tickers que ya no estan en el lote, de modo que la
    tabla refleje exactamente el catalogo actual. Devuelve la cantidad de filas escritas."""
    SQLModel.metadata.create_all(engine)
    vigentes = {f["ticker_byma"] for f in filas}
    n = 0
    with Session(engine) as session:
        for existente in session.exec(select(MercadoCedear)).all():
            if existente.ticker_byma not in vigentes:
                session.delete(existente)
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
