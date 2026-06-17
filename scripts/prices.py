import os
import re
import sys

import pandas as pd

CACHE_DIR = os.path.join("data", "prices_cache")
_TICKER_VALIDO = re.compile(r"[A-Za-z0-9.\-]+")


def _cache_path(ticker: str) -> str:
    if not _TICKER_VALIDO.fullmatch(ticker):
        raise ValueError(f"ticker invalido: {ticker!r}")
    return os.path.join(CACHE_DIR, f"{ticker.upper()}.csv")


def _desde_cache(ticker: str):
    path = _cache_path(ticker)
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    if df.empty or "Close" not in df.columns or "Date" not in df.columns:
        return None
    df["Date"] = pd.to_datetime(df["Date"], utc=True, errors="coerce")
    df = df.dropna(subset=["Date"]).set_index("Date")
    if df.empty:
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
    except Exception as e:
        print(f"aviso: fallo al obtener precios de {ticker}: {e}", file=sys.stderr)
    return None, "none", None


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

    Cascada cache -> red -> none, analoga a obtener_precios pero con OHLCV completo y cache propia.
    El parametro `periodo` se reserva para el recorte de la ventana en el llamador; la descarga
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
