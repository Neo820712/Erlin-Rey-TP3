---
name: generar-senal
description: Genera una señal de análisis técnico (RSI/MACD/SMA) para un activo del dashboard y la persiste vía la API. Usar cuando se invoca /generar-senal TICKER [tipo].
---

# /generar-senal

Genera un análisis técnico real para un activo monitoreado y lo persiste en la base, llamando a
la API del dashboard. Materializa el ciclo ReAct (think -> act -> observe).

## Interfaz

```
/generar-senal TICKER [tipo]
```

- `TICKER` — símbolo del activo (case-insensitive), debe existir en la base.
- `tipo` — `tecnico` (default) | `sentimiento`. `sentimiento` no está implementado: el script
  devuelve `400 - "tipo sentimiento no implementado en esta versión"`.

## Ejecución (delgada)

Toda la lógica determinística vive en `scripts/generar_senal.py`: verificar que el backend
responde, encontrar el activo por ticker, descargar precios (con caché/fallback), calcular los
indicadores, derivar la señal y hacer `POST /activos/{id}/analisis`. La skill orquesta y reporta;
no duplica esa lógica.

### Think
Leer `TICKER` y `tipo`. Tener presentes los modos de fallo que el script puede devolver: backend
caído, ticker inexistente, `tipo sentimiento` (400), red caída sin caché.

### Act
Ejecutar el script:

```bash
uv run python scripts/generar_senal.py TICKER [tipo]
```

El script descarga precios históricos, calcula RSI(14) / MACD(12,26,9) / SMA(20,50), deriva la
señal por voto de mayoría, y hace el `POST` del análisis.

### Observe
Leer la salida estructurada del script y reportar al usuario:

- Éxito (`201`): ticker, tipo, **señal**, confianza (como %), resumen, `id` del análisis creado, y
  la procedencia de los precios ("datos cacheados del &lt;fecha&gt;" si se usó caché).
- Error: la causa legible (backend caído / ticker no encontrado / sentimiento no implementado /
  red caída sin caché). No inventar un resultado: si el script falló, reportar el fallo.

## Ejemplo de salida esperada (éxito)

```
Análisis técnico generado para AAPL
  Señal:     venta
  Confianza: 67%  (2 de 3 indicadores coinciden)
  Resumen:   RSI 72.3 (venta), MACD 1.2 sobre señal 0.9 (compra),
             SMA20 188.4 < SMA50 190.1 (venta) -> venta por mayoría
  Análisis id: 12  (created_at 2026-06-13T14:05:22Z)
  Precios:   datos en vivo de yfinance
```
