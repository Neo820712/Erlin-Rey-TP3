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
- **`openapi.yaml` primero:** si cambia un endpoint (path, schema, status code), se edita el
  `openapi.yaml` antes que el código. El backend deriva del contrato, nunca al revés.
- **Status codes:** `200` GET, `201` POST que creó, `204` DELETE sin body, `400` body inválido,
  `404` no existe, `500` error interno.
- **Errores con schema único:** siempre `HTTPException(status_code=..., detail={"message": "..."})`.
- **Sesión de DB por dependency injection** (`Depends`), nunca una sesión global.
- **`logging`, nunca `print()`.**
- **Ruta de la DB desde `DATABASE_URL`**, no hardcodeada.

## Tres modelos por recurso

`Base` (campos comunes) / `Create` (body del POST, sin `id`) / tabla (`table=True`, con `id`):

```python
class ActivoBase(SQLModel):
    ticker: str
    nombre: str
    tipo: str
    mercado: str

class ActivoCreate(ActivoBase):
    pass

class Activo(ActivoBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
```

## Foreign key con borrado en cascada

SQLite no aplica FK por defecto: hay que emitir `PRAGMA foreign_keys=ON` por conexión, vía un
event listener en el engine:

```python
from sqlalchemy import event

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```
