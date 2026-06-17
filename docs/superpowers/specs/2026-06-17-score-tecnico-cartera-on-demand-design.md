# Spec — Score técnico on-demand, cartera por checkbox y precios como fuente única

**Fecha:** 2026-06-17
**Rama:** `feature/score-tecnico-cartera-on-demand`
**Estado:** aprobado (brainstorm) — pendiente de plan de implementación

## 1. Objetivo

Cuatro cambios sobre el dashboard de análisis de activos, sin romper el contrato, los
entregables obligatorios ni revertir la arquitectura existente:

1. **Cartera por checkbox.** Gestionar los activos monitoreados con una casilla al final de
   cada fila de la tabla de mercado (tildar = `POST /activos`, destildar = `DELETE /activos/{id}`).
   Se elimina el formulario "Agregar activo".
2. **Reencuadre "cartera de inversión".** Los activos monitoreados pasan a llamarse "cartera"
   (solo labels).
3. **Score técnico 0-100 on-demand.** El análisis técnico calcula un score 0-100 con los
   indicadores existentes (RSI, MACD, SMA) mediante una fórmula ponderada. Dos disparadores
   persisten el `Analisis`: la skill `/generar-senal` y un botón "Analizar" en la tarjeta Técnico
   (vía un endpoint nuevo). Ambos comparten el cómputo en `scripts/`.
4. **Análisis on-demand, no automático.** La tabla de mercado del inicio deja de mostrar
   señal/score (solo datos de mercado). La señal/score aparecen únicamente en la tarjeta Técnico
   del detalle (tras pedir el análisis) y en las cards de la cartera (desde el último `Analisis`).

## 2. Principios de arquitectura (invariantes que se respetan)

- **`openapi.yaml` es la fuente de verdad:** todo cambio de endpoint/schema se edita en el YAML
  **antes** que el código. Los tres cambios de esta feature son **aditivos**.
- **El backend no calcula ni toca el dominio externo:** nada de yfinance/pandas en `backend/`.
  Todo cómputo y descarga vive en `scripts/`. El backend es solo CRUD; cuando necesita cómputo,
  lanza un subprocess de `scripts/` y persiste el resultado.
- **Cómputo único compartido:** la fórmula del score vive en `scripts/indicators.py::analizar()`
  y la usan la skill, el endpoint `/tecnico` y `/historico`.
- **GitHub Flow:** rama feature nueva, integración por PR. No se commitea sobre `main`.
- **No se rompe:** el recurso `Analisis` y sus endpoints, la skill `/generar-senal` (se mejora),
  `CLAUDE.md`, `.claude/rules/`, `.claude/settings.json`, los enums del dominio.

## 3. Disparadores del análisis (transversal)

Hay **dos** formas de crear un `Analisis` técnico, que comparten el cómputo en `scripts/`:

1. **Skill `/generar-senal`** (Claude Code) — requisito del TP, se mantiene y mejora.
2. **Botón "Analizar"** en la tarjeta Técnico del dashboard → `POST /activos/{id}/analisis/tecnico`.

La **cartera** y el **detalle** leen el **último `Analisis`** de la base (no recalculan en vivo).
Cuando cualquiera de los dos disparadores corre → se persiste un `Analisis` → cartera y detalle se
actualizan al refetch.

## 4. Fórmula del score (en `scripts/indicators.py::analizar()`)

```
score (0-100) = 0.40*RSI_s + 0.30*Tendencia_s + 0.30*MACD_s

RSI_s (desde el RSI):
  rsi <= 30        -> 90
  30 < rsi <= 45   -> 100
  45 < rsi <= 55   -> 70
  55 < rsi <= 65   -> 45
  65 < rsi <= 70   -> 25
  rsi > 70         -> 5

Tendencia_s (0 / 50 / 100):
  +50 si precio (ultimo close) > SMA50
  +50 si SMA20 > SMA50

MACD_s (base 50, clamp [0,100]):
  base 50
  +30 si histograma creciente (hist[-1] > hist[-2])
  -15 si histograma decreciente (hist[-1] < hist[-2])
  +20 si histograma > 0

senal <- banda:   score >= 66 -> compra ; 33-65 -> hold ; < 33 -> venta
confianza <- |score - 50| * 2 / 100   (fuerza de la senal; hold -> ~0, extremos -> ~1)
```

- `analizar()` agrega la clave `score` al dict que devuelve y **mantiene** las claves actuales
  (`rsi`, `macd`, `signal`, `sma20`, `sma50`, `senal`, `confianza`, `resumen`).
- Se reescribe `resumen` para nombrar el score y el desglose por sub-score. Ese `resumen` es lo
  que la tarjeta Técnico muestra como desglose de indicadores.
- Bordes definidos con intervalos semiabiertos (sin solapamiento). `confianza` redondeada a 2
  decimales.

## 5. Contrato — tres cambios aditivos (YAML primero)

### 5.1 `score` nullable en `Analisis` / `AnalisisCreate`

En `components.schemas.AnalisisCreate` y `Analisis` (vía el `allOf`):

```yaml
score: { type: [number, 'null'] }   # 0..100, opcional
```

No se agrega `score` a `Historico.indicadores`. El modelo SQLModel `Analisis` suma
`score: Optional[float] = None`.

### 5.2 Endpoint `POST /activos/{id}/analisis/tecnico`

```
POST /activos/{id}/analisis/tecnico
  entrada: id en el path (sin body)
  201: Analisis  (tipo=tecnico, con senal/confianza/resumen/score computados)
  404: { message } si el activo no existe
  400: { message } si no hay precios para el ticker
  500: { message } si falla el computo / subprocess
```

Convive con `DELETE /activos/{id}/analisis/{analisisId}` (distinto method, path literal `tecnico`
vs `{analisisId}`; sin colisión). Es un sub-recurso computado, aditivo.

### 5.3 `score` nullable en `SenalesRecientes`

Para mostrar el score junto al badge de señal en las **cards de la cartera** (no solo en el
detalle). En `components.schemas.SenalesRecientes`:

```yaml
score: { type: [number, 'null'] }   # 0..100; score del ultimo Analisis tecnico, null si no hay
```

Es el score del análisis técnico más reciente del activo. `GET /activos/{id}` ya devuelve
`senales_recientes`, así que las cards lo reciben sin fetches extra (`cargarActivos()` ya hace
`GET /activos/{id}` por activo). El modelo SQLModel `SenalesRecientes` suma
`score: Optional[float] = None`.

## 6. Backend (`backend/`)

- **`models.py`:** `Analisis` suma `score: Optional[float] = None`. `SenalesRecientes` suma
  `score: Optional[float] = None`. Nuevo modelo `Precio` (tabla interna, OHLCV). Definir el modelo
  no importa pandas/yfinance.
- **`main.py` — `detalle_activo` (`GET /activos/{id}`):** al tomar el último `Analisis` técnico
  para `senales_recientes.tecnico`, setea también `senales_recientes.score` con el `score` de ese
  análisis (null si no hay análisis técnico).
- **`main.py`:** handler de `POST /activos/{id}/analisis/tecnico`:
  1. Valida que el activo existe (404 si no) y toma su `ticker` (= ticker_byma).
  2. Lanza subprocess `python -m scripts.score_tecnico <ticker>` (mismo patrón que
     `/mercado/actualizar` y `/historico`) que lee `precios` de la DB, computa con `analizar()` y
     devuelve por stdout JSON `{senal, confianza, resumen, score}`. Si no hay precios -> el script
     sale con código/JSON de error mapeado a 400; otro fallo -> 500.
  3. El backend **solo persiste** el `Analisis` (CRUD), con `created_at` autogenerado, y responde
     201 con el `Analisis`.
- El backend nunca importa yfinance/pandas, ni lee `precios` con pandas: el cómputo es del
  subprocess; la persistencia del `Analisis` es CRUD con SQLModel.

## 7. Tabla `precios` (fuente única de OHLC)

- Modelo `Precio` en `backend/models.py`: `id`, `ticker`, `fecha`, `open`, `high`, `low`,
  `close`, `volumen`. Tabla interna (sin contrato).
- **Clave de consulta:** se almacena/consulta por el **mismo ticker que usa `/historico`**
  (ticker_byma). Actualizar conoce el mapeo byma <-> us (lo tiene cada entrada de `cedears.json`)
  y descarga por el ticker US.
- **Actualizar = único punto de red.** `POST /mercado/actualizar` baja 1 año de los ~30 CEDEARs y
  persiste: OHLC en `precios` + snapshot/fundamentales en `mercado_cedears`. Reescribe el snapshot
  completo (como hoy).
- Todo lo demas **lee de la base:** `/historico` (gráficas) y el cómputo del score leen de
  `precios`.

## 8. Scripts (`scripts/`)

- **`prices.py` (reescrito):** se elimina el caché CSV (`prices_cache/`). Queda:
  - función de **ingesta** (yfinance -> filas de `precios`), usada por Actualizar.
  - **`obtener_ohlc`** (nombre real actual) reescrita como **lectura** (`precios` -> DataFrame
    OHLCV), usada por histórico y score. Se elimina la función `obtener_precios` (close-only) y la
    cascada de caché CSV.
- **`indicators.py`:** `analizar()` con la fórmula del score (sección 4). Sin cambios de firma
  (recibe `close`); puede necesitar el histograma MACD (lo calcula internamente desde `close`).
- **`historico.py`:** lee OHLC de `precios` (vía la lectura de `prices.py`). **NO** agrega `score`
  a `indicadores`; mantiene `indicadores` como está (con `senal`/`confianza`) por estabilidad de
  contrato, aunque la tarjeta ya no lo use para la señal.
- **`mercado.py`:** no llama a `analizar()`; persiste OHLC en `precios` además del snapshot;
  filas de `mercado_cedears` con `rsi=None`/`senal=None`.
- **`score_tecnico.py` (nuevo):** helper `computar(ticker) -> dict` que lee `precios` + corre
  `analizar()` y devuelve `{senal, confianza, resumen, score}`, más un `main(argv)` CLI que imprime
  ese dict como JSON por stdout (lo invoca el subprocess del endpoint `/tecnico`, `python -m
  scripts.score_tecnico <ticker>`). `generar_senal.py` importa y usa `computar()` directamente.
  Evita duplicar "leer precios + computar".
- **`generar_senal.py`:** usa `score_tecnico.computar()` (lee de `precios`, computa) y persiste
  vía `POST /activos/{id}/analisis` con `score` incluido. Mantiene el ciclo ReAct.
- **`seed.py`:** ya no usa `obtener_precios` (se elimina). Lee de `precios` con la nueva
  `obtener_ohlc` (toma `Close`) si hay datos y cae a `HARDCODE` si no, manteniéndose offline-safe.
  El `Analisis` seedeado **contempla el campo `score`**: lo setea desde `analizar()` cuando hay
  precios, o lo deja en `null` (válido por ser opcional) en el camino `HARDCODE`. Así el seed no
  se rompe con el nuevo schema.

## 9. Frontend (`frontend/index.html`)

- **Eliminar** la sección `#alta-activo` completa: form, los 2 inputs, selects tipo/mercado, botón
  Agregar, el dropdown de autocompletado, sus estilos y eventos (`renderDropdown`,
  `seleccionarCedear`, `filtrarCedears`, listeners de submit y de `f-busqueda`). `state.cedears`
  se sigue cargando (`/mercado/catalogo`) pero ahora solo para resolver `tipo`/`mercado` del
  checkbox.
- **Mantener** el filtro de la tabla (`m-filtro`) y el botón `↻ Actualizar`.
- **Tabla de mercado:** quitar columnas `RSI(14)` y `Señal`. Queda: Ticker · Empresa · Precio ·
  Var% · Volumen · P/E · Market Cap · **☑ Cartera**.
- **Checkbox por fila:** tildado = ticker en la cartera (cruzado con `state.activos`). Al tildar ->
  `POST /activos` (con `tipo`/`mercado` desde `state.cedears` por `ticker_byma`); al destildar ->
  `DELETE /activos/{id}` (ticker -> id desde `state.activos`). `stopPropagation` para que tocar el
  checkbox no abra el detalle. Loading/error como el resto; tras la mutación, refetch `/activos`
  -> `render()`.
- **Cards de la cartera (`cardHTML`):** junto al badge de señal técnica, mostrar el `score`
  (`senales_recientes.score`) si no es null (p. ej. "Técnico: compra · 72"). Viene en la misma
  respuesta de `GET /activos/{id}` que ya consume `cargarActivos()`, sin fetches extra.
- **Tarjeta Técnico (detalle):**
  - Botón **"Analizar"** -> `POST /activos/{id}/analisis/tecnico` -> refetch `/activos` ->
    cartera + detalle actualizados (loading/error como el resto).
  - Muestra **score + senal + resumen** leídos del **último `Analisis`** del activo
    (`GET /activos/{id}/analisis`, último `tecnico`); el **gráfico** desde `/historico`.
  - El botón solo aplica a tickers en la cartera (sin `activo_id` no hay POST). Para los que no
    están, mostrar un hint: "agregalo a la cartera para analizar".
- **Tarjeta "Datos de la acción":** quitar la duplicación de señal (hoy muestra "Señal del
  sistema"/"Confianza"); la señal/score viven solo en la tarjeta Técnico.
- **Labels de cartera:** `Activos monitoreados` -> `Cartera de inversión`; contador
  `N activos` -> `N en cartera`; textos de vacío e historial ajustados a la narrativa de cartera.

## 10. CLAUDE.md

Actualizar (manteniéndolo ≤ ~200 líneas) para reflejar: fuente única en la base (yfinance solo en
Actualizar), tabla `precios` (reemplaza el caché CSV), snapshot sin `senal`/`rsi`, fórmula del
score, cartera por checkbox sin formulario, los dos disparadores del análisis (skill + endpoint/
botón) y el nuevo endpoint en la lista de rutas. Actualizar la estructura del proyecto
(`prices_cache/` -> tabla `precios`; nuevo `scripts/score_tecnico.py`).

## 11. Skill `/generar-senal`

Actualizar `SKILL.md` (sección Observe + ejemplo de salida) para reportar el **score 0-100** junto
a la señal y la confianza. Sigue siendo un disparador válido del análisis; ahora comparte el
cómputo con el endpoint vía `scripts/score_tecnico.py`.

## 12. Tests (`tests/`)

- **`test_indicators.py`:** nuevas expectativas de `senal`/`confianza` derivadas del score; casos
  de borde de `RSI_s`, `Tendencia_s`, `MACD_s`; presencia y rango de `score`.
- **`test_historico.py`:** `indicadores` **sin** `score`; lectura de OHLC desde `precios`.
- **Nuevo:** persistencia de `score` en `analisis` y endpoint `/tecnico` (201 + persiste el
  `Analisis` con `tipo=tecnico` y `score` no nulo).
- **`test_prices.py`:** ingesta/lectura desde `precios` (reemplaza los tests de caché CSV).
- **`test_mercado_script.py`:** filas con `rsi`/`senal` None + persistencia de OHLC en `precios`.
- **`test_api.py` / `test_mercado.py`:** ajustes por el `score` en `Analisis`; verificar que
  `GET /activos/{id}` devuelve `senales_recientes.score` (el del último análisis técnico, o null).

## 13. Demo / offline

El caché CSV ya estaba gitignored (no había demo offline versionada). Mover precios a la tabla
`precios` (también gitignored) no regresa ninguna garantía versionada: la demo se prepara corriendo
Actualizar antes (igual que hoy), que ahora puebla `precios` en vez de CSVs. `start.bat` no cambia.

## 14. Desvíos reportados (no rupturas)

- **Propuesta original** (`propuesta/planificacion-del-proyecto.md`): habla de "7 endpoints" y
  "señales simuladas / sin feeds reales". Eso ya quedó superado por la expansión previa de
  mercado/histórico (yfinance real). Esta feature suma el 8.º endpoint (`/tecnico`) y la tabla
  `precios`, continuando esa expansión. La propuesta es una "declaración de intención" ya
  extendida; el desvío se documenta en `CLAUDE.md`.
- **Decisión previa de brainstorm** ("solo mostrar, persistencia solo por la skill") queda
  **superada** por la decisión final: dos disparadores (skill + botón/endpoint), cartera y detalle
  leen el último `Analisis`.

## 15. Fuera de alcance

- Tarjeta Fundamental: queda como placeholder, a definir después.
- `tipo sentimiento`: sigue sin implementar (el script devuelve 400).
- Métricas/observabilidad más allá de logs en terminal.
- Edición de activos/análisis (sin PUT/PATCH).
