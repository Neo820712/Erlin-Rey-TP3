import json
import os
import sys
import urllib.request

from scripts.score_tecnico import computar

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


def generar(ticker: str) -> int:
    try:
        activos = _get("/activos")
    except OSError:
        print(f"Error: el backend no responde en {API_BASE}. Levantar el server primero.")
        return 1

    activo = next((a for a in activos if a["ticker"].upper() == ticker.upper()), None)
    if activo is None:
        print(f"Error: el ticker {ticker} no existe en la base. Crealo primero (formulario o seed).")
        return 1

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


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Uso: generar_senal.py TICKER")
        return 2
    ticker = argv[1]
    return generar(ticker)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
