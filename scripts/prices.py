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
