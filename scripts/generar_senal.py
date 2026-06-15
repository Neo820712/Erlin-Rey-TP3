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

    try:
        activos = _get("/activos")
    except urllib.error.URLError:
        print(f"Error: el backend no responde en {API_BASE}. Levantar el server primero.")
        return 1

    activo = next((a for a in activos if a["ticker"].upper() == ticker.upper()), None)
    if activo is None:
        print(f"Error: el ticker {ticker} no existe en la base. Crealo primero (formulario o seed).")
        return 1

    close, procedencia, fecha = obtener_precios(ticker)
    if procedencia == "none":
        print(f"Error: no se pudieron obtener precios de {ticker} (red caida y sin cache).")
        return 1

    try:
        res = analizar(close)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    estado, creado = _post(
        f"/activos/{activo['id']}/analisis",
        {"tipo": "tecnico", "senal": res["senal"], "confianza": res["confianza"], "resumen": res["resumen"]},
    )

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
