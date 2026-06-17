# Ampliación del dashboard de activos financieros — input para brainstorming

El sistema actual tiene un backend FastAPI con 7 endpoints REST, scripts de análisis
técnico real (RSI/MACD/SMA con pandas sobre datos de yfinance), y un frontend single-file
`frontend/index.html` que muestra un grid de cards con badges de señal, un formulario
de alta y un historial de análisis por activo. Quiero ampliar el frontend con tres
funcionalidades nuevas que lo conviertan en una herramienta de análisis real,
sin tocar el backend ni los scripts existentes salvo que sea estrictamente necesario.
El esquema de colores Intel que ya tengo se mantiene en todo lo nuevo.

---

## 1. Autocompletado en el formulario de alta

El formulario actual tiene dos campos de texto separados: uno para el ticker y otro
para el nombre de la empresa. El usuario tiene que escribir los dos de memoria.
Quiero reemplazar eso por un único campo de búsqueda que filtre en tiempo real
mientras el usuario escribe, buscando simultáneamente por ticker y por nombre
de empresa. Por ejemplo, escribir "apple" o "AAPL" tiene que mostrar el mismo
resultado: "AAPL — Apple Inc.".

La fuente de datos para el autocompletado es una lista completa de todos los CEDEARs
disponibles en BYMA, que incluye tickers de empresas norteamericanas (NYSE/NASDAQ),
brasileñas y ETFs. Esta lista vive como un archivo JSON estático en el repositorio
(`data/cedears.json`) con la siguiente estructura por entrada:

```json
{ "ticker_byma": "AAPL", "ticker_yfinance": "AAPL.BA",
  "nombre": "Apple Inc.", "mercado": "NASDAQ", "tipo": "accion" }
```

Cuando el usuario selecciona un resultado de la lista desplegable, los campos
`ticker`, `nombre`, `tipo` y `mercado` del formulario se completan automáticamente
con los valores del JSON. El usuario no tiene que escribir nada más — solo confirma
con el botón "Agregar". La lista desplegable se renderiza debajo del campo de búsqueda,
muestra máximo 8 resultados al mismo tiempo con scroll interno, y desaparece al
hacer click fuera o al seleccionar.

El campo de búsqueda reemplaza visualmente al campo de ticker actual en el formulario.
Los campos `ticker`, `nombre`, `tipo` y `mercado` siguen existiendo como campos del
formulario pero se pre-llenan desde la selección — el usuario puede editarlos si quiere
antes de confirmar. El `POST /activos` no cambia.

---

## 2. Tabla de mercado con todos los CEDEARs de BYMA

Quiero una tabla debajo del formulario de alta, antes del grid de cards, que muestre
todos los CEDEARs de BYMA con sus datos de mercado. La tabla tiene el siguiente
layout en HTML:

```
┌─────────────────────────────────────────────────────────────┐
│  [🔍 Filtrar por ticker o empresa...]        [↻ Actualizar] │
├──────┬────────────────┬─────────┬──────────┬────────┬───────┤
│Ticker│Empresa         │Precio   │Var %     │Volumen │RSI(14)│
│      │                │(ARS)    │(día)     │        │       │
├──────┼────────────────┼─────────┼──────────┼────────┼───────┤
│AAPL  │Apple Inc.      │ 9.250,00│ ▲ +1.23% │ 42.100 │  44.1 │
│GOOGL │Alphabet Inc.   │48.300,00│ ▼ -0.87% │  8.200 │  38.6 │
│...   │...             │...      │...       │...     │...    │
└──────┴────────────────┴─────────┴──────────┴────────┴───────┘
```

**Columnas:**
- **Ticker** — ticker BYMA (ej: AAPL, GOOGL)
- **Empresa** — nombre completo
- **Precio (ARS)** — último precio en pesos, formateado con separador de miles
- **Var % (día)** — variación porcentual del día, con ▲ verde si positiva, ▼ roja si negativa
- **Volumen** — volumen del día formateado (ej: 42.1K, 1.2M)
- **RSI(14)** — valor numérico calculado con `indicators.py` existente; coloreado:
  verde si < 30 (sobreventa), rojo si > 70 (sobrecompra), blanco si entre 30–70
- **Señal** — compra / venta / hold con el mismo sistema de badges de color que
  ya usa el dashboard (verde/rojo/amarillo)
- **P/E** — ratio precio/ganancias si yfinance lo devuelve para el ticker `.BA`;
  celda vacía con "—" si no está disponible
- **Market Cap** — capitalización de mercado si yfinance lo devuelve; abreviado
  (ej: 2.8T, 340B); "—" si no disponible

**Comportamiento:**
- Al cargar la página, la tabla aparece vacía con el mensaje
  "Presioná Actualizar para cargar los datos de mercado".
- El botón **Actualizar** descarga los datos frescos de yfinance para todos los
  CEDEARs de BYMA y los muestra. Mientras descarga, el botón muestra un spinner
  y el texto "Cargando..." y se deshabilita para evitar requests paralelos.
- El campo **Filtrar** filtra las filas en tiempo real por ticker o nombre de empresa
  (client-side, sin nueva request).
- Click en cualquier **header de columna** ordena la tabla por esa columna;
  click de nuevo invierte el orden. El header activo muestra una flecha ↑ o ↓.
- Click en una **fila** abre la vista de análisis detallado de ese ticker
  (funcionalidad 3).

Los datos de la tabla los calcula un nuevo script `scripts/mercado.py` que reutiliza
`prices.py` e `indicators.py` existentes. El backend expone un nuevo endpoint
`GET /mercado/cedears` que corre el script y devuelve el JSON con todos los datos.
Este endpoint se agrega al `openapi.yaml`.

---

## 3. Vista de análisis detallado al estilo Finviz + TradingView

Cuando el usuario hace click en una fila de la tabla de mercado o en una card
del grid existente, la vista principal se reemplaza por una pantalla de detalle
del activo seleccionado. Un botón "← Volver" en la parte superior izquierda
regresa al dashboard principal.

### Panel de métricas al estilo Finviz

En la parte superior de la vista de detalle, un panel de métricas organizadas
en una grilla compacta de dos columnas (izquierda: técnico, derecha: fundamental),
similar al panel de datos de Finviz:

```
┌─────────────────────────────────┬─────────────────────────────────┐
│ TÉCNICO                         │ FUNDAMENTAL                     │
├──────────────┬──────────────────┼──────────────┬──────────────────┤
│ RSI (14)     │ 44.1  [hold]     │ P/E          │ 28.4             │
│ MACD         │ 2.30 vs 5.80     │ EPS (TTM)    │ 6.43             │
│ SMA 20       │ 303.88           │ Market Cap   │ 2.8T             │
│ SMA 50       │ 285.36           │ Volumen      │ 42.1K            │
│ Señal        │ ● HOLD           │ Var % (día)  │ ▲ +1.23%         │
│ Confianza    │ 33%              │ 52w High     │ 390.00           │
│              │                  │ 52w Low      │ 164.00           │
└──────────────┴──────────────────┴──────────────┴──────────────────┘
```

Los valores de la columna técnica vienen de `indicators.py`. Los de la columna
fundamental vienen de yfinance (P/E, EPS TTM, Market Cap, 52w High/Low);
si yfinance no los devuelve para el ticker `.BA`, la celda muestra "—".
La señal usa el mismo color que los badges del dashboard: verde/rojo/amarillo.

### Gráfico de velas al estilo TradingView

Debajo del panel de métricas, un gráfico de velas japonesas (candlestick) con los
precios históricos del activo y los indicadores técnicos superpuestos, con este layout:

```
┌─────────────────────────────────────────────────────────────┐
│  [1M]  [3M]  [6M]  [1Y]                                    │
│                                                             │
│  Gráfico de velas — precio + SMA20 (línea azul) +          │
│  SMA50 (línea naranja)                     altura: ~300px   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Panel RSI(14) — línea + bandas en 30 y 70    altura: ~80px │
├─────────────────────────────────────────────────────────────┤
│  Panel MACD — línea MACD + señal + histograma altura: ~80px │
└─────────────────────────────────────────────────────────────┘
```

**Especificaciones del gráfico:**
- **Librería:** `lightweight-charts` de TradingView, cargada desde CDN
  (`https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js`).
  Es la misma librería que usa TradingView internamente, tiene soporte nativo para
  candlestick, es vanilla JS puro (sin dependencias), pesa ~45KB gzipped y carga
  sin build steps — compatible con el paradigma single-file existente.
- **Velas:** OHLC (open/high/low/close) del histórico de yfinance.
- **SMA20 y SMA50** superpuestas sobre las velas como `LineSeries`:
  SMA20 en azul (`#4A90D9`), SMA50 en naranja (`#F5A623`).
- **Panel RSI:** `LineSeries` en un panel separado debajo, con dos `PriceLine`
  horizontales en 30 (verde, punteada) y 70 (roja, punteada).
- **Panel MACD:** línea MACD (`#4A90D9`), línea señal (`#F5A623`) e histograma
  (`HistogramSeries`, verde si positivo, rojo si negativo) en un tercer panel.
- **Períodos:** botones 1M / 3M / 6M / 1Y arriba del gráfico. Por defecto: 3M.
  Al cambiar el período, el gráfico se actualiza recalculando los indicadores
  sobre el subconjunto de datos correspondiente.
- **Interactividad:** zoom con scroll del mouse, crosshair que muestra OHLC
  y valor de indicadores al hover. El usuario puede scrollear horizontalmente
  en el tiempo.
- **Datos:** los precios históricos vienen de `prices.py` existente (con caché);
  los indicadores se calculan con `indicators.py` existente.

El backend expone un nuevo endpoint `GET /activos/{ticker}/historico?periodo=3m`
que devuelve el OHLC histórico y los valores de RSI/MACD/SMA calculados por
`indicators.py`. Este endpoint se agrega al `openapi.yaml`.

### Historial de análisis guardados

Debajo del gráfico, el historial de análisis guardados en la DB para ese activo,
igual a como se muestra hoy en las cards expandidas (pill de color, tipo, confianza %,
fecha, resumen) pero con mejor jerarquía visual — cada análisis en una fila horizontal,
no en lista vertical comprimida.