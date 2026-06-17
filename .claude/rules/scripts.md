---
paths: ["scripts/**/*.py"]
---

# Reglas de scripts (capa de dominio)

`scripts/` es la capa que toca red y cálculo: todo lo que el backend (solo CRUD) no puede hacer
vive aquí, y el backend la invoca como subproceso.

- **Aquí vive el dominio externo:** yfinance y pandas se usan en esta capa, nunca en `backend/`.
  yfinance se importa de forma diferida dentro de la función que lo necesita (ver
  `mercado._datos_de_ticker`), no a nivel de módulo.
- **Contrato de subproceso: un único JSON por stdout.** Los scripts que el backend lanza
  (`score_tecnico`, `historico`, `mercado`) imprimen exactamente un objeto JSON en stdout y nada
  más; el backend parsea esa salida. Los errores esperados se devuelven también como JSON
  (`{"error": "..."}`) con `return 0`, no como excepción ni texto suelto.
- **Diagnóstico por stderr, nunca contaminar stdout:** avisos y trazas van a `stderr`
  (`print(..., file=sys.stderr)`, ver `mercado.py`). Cualquier print de debug en stdout rompe el
  parse del subproceso.
- **Scripts de CLI (no subproceso):** `seed.py` y `generar_senal.py` los corre un humano y sí
  imprimen texto legible en stdout; no están sujetos al contrato JSON porque el backend no los parsea.
- **Separar red de cálculo puro:**
  - `indicators.py` y `historico.construir_historico` son puros: reciben serie/DataFrame, calculan,
    y no tocan red ni DB.
  - `prices.py` lee/escribe la tabla `precios` (DB, sin red).
  - La red (yfinance) vive solo en `mercado.py`. El score y el histórico leen de `precios`, nunca
    descargan.
- **No crear conexión propia a la DB:** reusar `engine` de `backend.database`
  (`from backend.database import engine`); no instanciar otro engine ni hardcodear la ruta.
- **`score_tecnico.computar(ticker)` es la fuente única del score** que se persiste: compartido por
  la skill `/tecnico` y el endpoint `POST /activos/{id}/analisis/tecnico`. No reimplementar el
  cálculo del score en otro script (los demás llaman a `indicators.analizar` sobre series puras).
- **Patrón snapshot al persistir:** `mercado.persistir` y `prices.guardar_ohlc` descartan la tabla
  y la recrean antes de insertar (así se aplican columnas nuevas del modelo). Mantener ese patrón.
- **Imports absolutos `scripts.` y `backend.`:** funcionan por `PYTHONPATH=.` (en `settings.json`),
  sin instalar el proyecto como paquete.
- **Tras tocar `scripts/`: `uv run pytest`** y leer la salida antes de dar la tarea por terminada.