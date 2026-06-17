---
paths: ["backend/**/*.py"]
---

# Reglas del backend

- **Stack fijo:** FastAPI + SQLModel + SQLite. Nada más en el backend.

- **El backend no toca el dominio externo:** no importa `yfinance` ni `pandas`. Descargar precios
  y calcular indicadores es responsabilidad de `scripts/`. El backend es solo CRUD.

- **Datos de mercado vía subprocess:** las rutas que necesitan yfinance (`/mercado/actualizar`,
  `/mercado/{ticker}/historico`) lanzan scripts con `subprocess.run([sys.executable, "-m", ...])`
  y parsean su stdout JSON. El backend nunca importa yfinance ni pandas, ni siquiera para mercado.
  Validar los argumentos controlados por el usuario (el `ticker`) antes de pasarlos al subproceso.

- **Score técnico vía subprocess:** `POST /activos/{id}/analisis/tecnico` (en cartera, persiste el
  análisis) y `GET /mercado/{ticker}/tecnico` (fuera de cartera, no persiste) lanzan
  `scripts.score_tecnico` como subproceso; el backend no computa, y solo el primero guarda el
  resultado.

- **`openapi.yaml` primero:** si cambia un endpoint (path, schema, status code), se edita el
  `openapi.yaml` antes que el código. El backend deriva del contrato, nunca al revés.

- **Status codes:** `200` GET, `201` POST que creó, `204` DELETE sin body, `400` body inválido,
  `404` no existe, `500` error interno.

- **Errores con schema único:** siempre `HTTPException(status_code=..., detail={"message": "..."})`.

- **Sesión de DB por dependency injection** (`Depends`), nunca una sesión global.

- **`logging`, nunca `print()`.**

- **Ruta de la DB desde `DATABASE_URL`**, no hardcodeada.




