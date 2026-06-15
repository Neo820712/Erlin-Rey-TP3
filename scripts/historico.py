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
    """Calcula indicadores sobre la serie completa y recorta la salida a la ventana del periodo.
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
