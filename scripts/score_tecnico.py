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
