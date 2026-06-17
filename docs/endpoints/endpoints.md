### Gestión de cartera de activos

* **GET /activos**: recupera la lista de activos bajo monitoreo. Consumido por el frontend para poblar las tablas principales o el selector de la interfaz.
* **POST /activos**: inscribe un nuevo activo (acción, ON, CEDEAR) en la base de datos. Consumido por el frontend (formulario de alta) o por scripts de inicialización (seed.py).
* **GET /activos/{id}**: obtiene la información base de un activo junto con el resumen de sus señales de trading más recientes. Consumido por el frontend al abrir la vista de detalle.
* **DELETE /activos/{id}**: elimina el activo y purga en cascada todo su historial de análisis. Consumido por el frontend.

### Registro y generación de análisis

* **GET /activos/{id}/analisis**: lista el historial cronológico de los análisis (técnico o de sentimiento) aplicados a un activo. Consumido por el frontend para mostrar la bitácora de decisiones.
* **POST /activos/{id}/analisis**: recibe y persiste un análisis previamente calculado. Consumido principalmente por el script generar_senal.py (usado por el agente Claude Code) luego de procesar los indicadores.
* **DELETE /activos/{id}/analisis/{analisisId}**: borra un registro de análisis puntual. Consumido por el frontend.
* **POST /activos/{id}/analisis/tecnico**: dispara la ejecución del pipeline interno de análisis técnico para un activo y persiste el resultado automáticamente. Consumido por el frontend (botón de generar reporte) o tareas automatizadas.

### Integración de mercado y gráficos

* **GET /mercado/catalogo**: sirve la lista estática de CEDEARs disponibles desde data/cedears.json. Consumido por el frontend para el autocompletado del buscador.
* **GET /mercado/cedears**: devuelve la foto (snapshot) más reciente de precios y variaciones de la base de datos. Consumido por el frontend para renderizar el panel general del mercado.
* **POST /mercado/actualizar**: orquesta el motor de recolección de datos masivos. Llama al exterior (yfinance), descarga históricos, calcula indicadores al vuelo y reescribe la base de datos local. Consumido por el usuario a través del frontend (botón de actualización) o por un cron job.
* **GET /mercado/{ticker}/fundamentales**: devuelve métricas financieras (PE, EPS, Market Cap, etc.) cacheadas en la base para un ticker específico. Consumido por el frontend en la ficha técnica del activo.
* **GET /mercado/{ticker}/historico**: procesa y empaqueta las series temporales de precios (OHLC) y las curvas de los indicadores (SMA, RSI, MACD). Consumido estrictamente por la librería de gráficos (Lightweight Charts) en index.html.
* **GET /mercado/{ticker}/tecnico**: calcula el score técnico actual al vuelo, pero no lo guarda en la base de datos. Consumido por scripts externos o por el frontend para validaciones rápidas ("what-if" o visualizaciones previas a guardar un análisis).