---
name: tecnico
description: Genera y persiste un análisis técnico (RSI/MACD/SMA, score 0-100) para un activo de la cartera vía la API. Usar cuando se invoca /tecnico TICKER.
---

# /tecnico

Genera un análisis técnico real para un activo monitoreado y lo persiste en la base, llamando a
la API del dashboard. Materializa el ciclo ReAct (think -> act -> observe).

## Interfaz

```
/tecnico TICKER
```

- `TICKER` — símbolo del activo (case-insensitive), debe existir en la base.

## Ejecución (delgada)

Toda la lógica determinística vive en `scripts/generar_senal.py`: verificar que el backend
responde, encontrar el activo por ticker, y hacer `POST /activos/{id}/analisis`. El cómputo del
score y la señal vive en `scripts/score_tecnico.py` (compartido con el endpoint
`POST /activos/{id}/analisis/tecnico`). La skill orquesta y reporta; no duplica esa lógica.

### Think
Leer `TICKER`. Tener presentes los modos de fallo que el script puede devolver: backend caído,
ticker inexistente, sin precios en la tabla precios.

### Act
Ejecutar el script:

```bash
uv run python scripts/generar_senal.py TICKER
```

El script lee precios de la tabla `precios` (persistidos por Actualizar), calcula RSI(14) /
MACD(12,26,9) / SMA(20,50), deriva el score 0-100 y la señal, y hace el `POST` del análisis.

### Observe
Leer la salida estructurada del script y reportar al usuario:

- Éxito (`201`): ticker, tipo, **score** (0-100), **señal**, confianza (como %), resumen,
  `id` del análisis creado, y la procedencia de los precios (tabla `precios`, ultimo Actualizar).
- Error: la causa legible (backend caído / ticker no encontrado / sin precios). No inventar un
  resultado: si el script falló, reportar el fallo.

El cómputo vive en `scripts/score_tecnico.py` (compartido con `POST /activos/{id}/analisis/tecnico`).

## Ejemplo de salida esperada (éxito)

```
Análisis técnico generado para AAPL
  Score:     72/100
  Señal:     hold
  Confianza: 44%
  Resumen:   Score 72/100 (hold). RSI 75.2 [5], Tendencia alcista [100], MACD hist +0.80 creciente [100]
  Análisis id: 12  (created_at 2026-06-13T14:05:22Z)
  Precios:   tabla precios (último Actualizar)
```
