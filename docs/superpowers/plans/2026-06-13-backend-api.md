# Backend API Implementation Plan (Plan 1 de 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el contrato OpenAPI y el backend REST (FastAPI + SQLModel + SQLite) con los 7 endpoints, validación, manejo de errores uniforme y tests automatizados que verifican el contrato.

**Architecture:** Backend solo CRUD. `openapi.yaml` se escribe primero como fuente de verdad. `models.py` define tres clases por recurso (Base/Create/tabla); `database.py` el engine con `PRAGMA foreign_keys=ON` y la sesión por dependency injection; `main.py` las rutas, CORS y los handlers de error que devuelven `{ "message" }`. Los tests usan `TestClient` sobre SQLite en memoria.

**Tech Stack:** Python 3.12, uv, FastAPI, SQLModel (Pydantic v2 + SQLAlchemy), SQLite, pytest, httpx.

**Alcance de este plan:** subsistema A (contrato + backend + tests). NO incluye `scripts/` (Plan 2) ni el frontend (Plan 3). El backend acepta análisis `tecnico` y `sentimiento` (el enum es válido); la restricción de `sentimiento` vive en el Plan 2 (skill), no acá.

**Contexto de referencia:** spec en `docs/superpowers/specs/2026-06-13-dashboard-activos-financieros-design.md` y el documento base `propuesta/planificacion-del-proyecto.md` (§4.3 contratos, §4.4 modelo de datos).

**Convenciones que asume el código:**
- Host `http://localhost:8000`, sin prefijo de versión.
- Claves del JSON en ASCII: `senal`, `senales_recientes` (sin ñ).
- Enums: activo `tipo` {`accion`, `ON`}, `mercado` {`BYMA`, `NYSE`, `NASDAQ`}; análisis `tipo` {`tecnico`, `sentimiento`}, `senal` {`compra`, `venta`, `hold`}.
- Error único `{ "message": "..." }` para 400, 404 y 500.
- `created_at` en ISO 8601 UTC con sufijo `Z`.

---

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `pyproject.toml` | Dependencias y config de pytest (gestionado por uv) |
| `openapi.yaml` | Contrato de la API (fuente de verdad) |
| `backend/__init__.py` | Marca `backend` como paquete |
| `backend/models.py` | SQLModel: `Activo`/`Analisis` (Base/Create/tabla) + `ActivoDetalle` + `SenalesRecientes` |
| `backend/database.py` | Engine, `PRAGMA foreign_keys=ON`, `get_session`, `create_db` |
| `backend/main.py` | App FastAPI, CORS, exception handlers, los 7 endpoints |
| `tests/__init__.py` | Marca `tests` como paquete |
| `tests/conftest.py` | Fixture `client` con SQLite en memoria y override de `get_session` |
| `tests/test_api.py` | Tests de los 7 endpoints, validación, errores y cascade |

---

## Task 0: Bootstrap del proyecto

**Files:**
- Create: `pyproject.toml`
- Create: `backend/__init__.py` (vacío)
- Create: `tests/__init__.py` (vacío)
- Create: `data/.gitkeep` (vacío)

- [ ] **Step 1: Crear `pyproject.toml`**

```toml
[project]
name = "activos-dashboard"
version = "0.1.0"
description = "Dashboard de análisis de activos financieros (TP3)"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlmodel>=0.0.22",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "httpx>=0.27",
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Crear los archivos marcadores**

`backend/__init__.py`, `tests/__init__.py` y `data/.gitkeep` vacíos.

- [ ] **Step 3: Instalar dependencias**

Run: `uv sync`
Expected: crea `.venv`, instala fastapi/uvicorn/sqlmodel/pytest/httpx, genera `uv.lock`.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock backend/__init__.py tests/__init__.py data/.gitkeep
git commit -m "chore: bootstrap del proyecto (pyproject, deps, estructura)"
```

---

## Task 1: Contrato `openapi.yaml`

El contrato se escribe primero. FastAPI generará su propio `/openapi.json`; este archivo es la fuente de verdad versionada contra la que se compara.

**Files:**
- Create: `openapi.yaml`

- [ ] **Step 1: Escribir `openapi.yaml`**

```yaml
openapi: 3.1.0
info:
  title: Dashboard de Análisis de Activos Financieros
  version: 0.1.0
servers:
  - url: http://localhost:8000
paths:
  /activos:
    get:
      summary: Listar activos
      responses:
        '200':
          description: Lista de activos (puede ser vacía)
          content:
            application/json:
              schema:
                type: array
                items: { $ref: '#/components/schemas/Activo' }
    post:
      summary: Crear un activo
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/ActivoCreate' }
      responses:
        '201':
          description: Activo creado
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Activo' }
        '400':
          description: Body inválido
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
  /activos/{id}:
    get:
      summary: Detalle de un activo con sus señales recientes
      parameters:
        - { name: id, in: path, required: true, schema: { type: integer } }
      responses:
        '200':
          description: Activo con senales_recientes
          content:
            application/json:
              schema: { $ref: '#/components/schemas/ActivoDetalle' }
        '404':
          description: El activo no existe
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
    delete:
      summary: Borrar un activo (cascada sobre sus análisis)
      parameters:
        - { name: id, in: path, required: true, schema: { type: integer } }
      responses:
        '204': { description: Borrado, sin body }
        '404':
          description: El activo no existe
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
  /activos/{id}/analisis:
    get:
      summary: Historial de análisis de un activo
      parameters:
        - { name: id, in: path, required: true, schema: { type: integer } }
      responses:
        '200':
          description: Lista de análisis (orden descendente por created_at)
          content:
            application/json:
              schema:
                type: array
                items: { $ref: '#/components/schemas/Analisis' }
        '404':
          description: El activo no existe
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
    post:
      summary: Crear un análisis sobre un activo
      parameters:
        - { name: id, in: path, required: true, schema: { type: integer } }
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/AnalisisCreate' }
      responses:
        '201':
          description: Análisis creado
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Analisis' }
        '400':
          description: Body inválido
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
        '404':
          description: El activo no existe
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
  /activos/{id}/analisis/{analisisId}:
    delete:
      summary: Borrar un análisis puntual
      parameters:
        - { name: id, in: path, required: true, schema: { type: integer } }
        - { name: analisisId, in: path, required: true, schema: { type: integer } }
      responses:
        '204': { description: Borrado, sin body }
        '404':
          description: El activo o el análisis no existen
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
components:
  schemas:
    ActivoCreate:
      type: object
      required: [ticker, nombre, tipo, mercado]
      properties:
        ticker: { type: string }
        nombre: { type: string }
        tipo: { type: string, enum: [accion, ON] }
        mercado: { type: string, enum: [BYMA, NYSE, NASDAQ] }
    Activo:
      allOf:
        - $ref: '#/components/schemas/ActivoCreate'
        - type: object
          required: [id]
          properties:
            id: { type: integer }
    SenalesRecientes:
      type: object
      properties:
        tecnico: { type: [string, 'null'], enum: [compra, venta, hold, null] }
        sentimiento: { type: [string, 'null'], enum: [compra, venta, hold, null] }
    ActivoDetalle:
      allOf:
        - $ref: '#/components/schemas/Activo'
        - type: object
          required: [senales_recientes]
          properties:
            senales_recientes: { $ref: '#/components/schemas/SenalesRecientes' }
    AnalisisCreate:
      type: object
      required: [tipo, senal, confianza, resumen]
      properties:
        tipo: { type: string, enum: [tecnico, sentimiento] }
        senal: { type: string, enum: [compra, venta, hold] }
        confianza: { type: number, minimum: 0, maximum: 1 }
        resumen: { type: string }
    Analisis:
      allOf:
        - $ref: '#/components/schemas/AnalisisCreate'
        - type: object
          required: [id, activo_id, created_at]
          properties:
            id: { type: integer }
            activo_id: { type: integer }
            created_at: { type: string, format: date-time }
    Error:
      type: object
      required: [message]
      properties:
        message: { type: string }
```

- [ ] **Step 2: Validar que es YAML bien formado**

Run: `uv run python -c "import yaml; yaml.safe_load(open('openapi.yaml', encoding='utf-8')); print('OK')"`
Expected: `OK` (si `yaml` no está instalado, usar `python -c "import json,sys; ..."` no aplica; instalar no es necesario — alternativamente abrir el archivo y revisar a ojo la indentación).

- [ ] **Step 3: Commit**

```bash
git add openapi.yaml
git commit -m "feat: openapi.yaml como contrato fuente de verdad"
```

---

## Task 2: Modelos SQLModel

**Files:**
- Create: `backend/models.py`

- [ ] **Step 1: Escribir `backend/models.py`**

```python
from typing import Literal, Optional

from sqlalchemy import Column, ForeignKey, Integer
from sqlmodel import Field, SQLModel

TipoActivo = Literal["accion", "ON"]
Mercado = Literal["BYMA", "NYSE", "NASDAQ"]
TipoAnalisis = Literal["tecnico", "sentimiento"]
Senal = Literal["compra", "venta", "hold"]


# --- Activo ---
class ActivoBase(SQLModel):
    ticker: str
    nombre: str
    tipo: TipoActivo
    mercado: Mercado


class ActivoCreate(ActivoBase):
    pass


class Activo(ActivoBase, table=True):
    __tablename__ = "activos"
    id: Optional[int] = Field(default=None, primary_key=True)


# --- Analisis ---
class AnalisisBase(SQLModel):
    tipo: TipoAnalisis
    senal: Senal
    confianza: float = Field(ge=0.0, le=1.0)
    resumen: str


class AnalisisCreate(AnalisisBase):
    pass


class Analisis(AnalisisBase, table=True):
    __tablename__ = "analisis"
    id: Optional[int] = Field(default=None, primary_key=True)
    activo_id: int = Field(
        sa_column=Column(Integer, ForeignKey("activos.id", ondelete="CASCADE"), nullable=False)
    )
    created_at: str


# --- Schemas de salida que no son tablas ---
class SenalesRecientes(SQLModel):
    tecnico: Optional[Senal] = None
    sentimiento: Optional[Senal] = None


class ActivoDetalle(ActivoBase):
    id: int
    senales_recientes: SenalesRecientes
```

- [ ] **Step 2: Verificar que importa sin errores**

Run: `uv run python -c "from backend.models import Activo, Analisis, ActivoDetalle, SenalesRecientes; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/models.py
git commit -m "feat: modelos SQLModel (Activo, Analisis, ActivoDetalle)"
```

---

## Task 3: Capa de base de datos

**Files:**
- Create: `backend/database.py`

- [ ] **Step 1: Escribir `backend/database.py`**

```python
import os

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/activos.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
```

- [ ] **Step 2: Verificar import**

Run: `uv run python -c "from backend.database import engine, get_session, create_db; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/database.py
git commit -m "feat: engine SQLite con PRAGMA FK y sesión por DI"
```

---

## Task 4: Fixture de tests

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Escribir `tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.database import get_session
from backend.main import app


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
```

(El test crea su propio engine en memoria con `StaticPool` para que la misma conexión persista entre requests, y reactiva el PRAGMA FK para validar el cascade.)

- [ ] **Step 2: Commit** (todavía no corre nada; `backend/main.py` no existe aún)

```bash
git add tests/conftest.py
git commit -m "test: fixture client con SQLite en memoria y override de sesión"
```

---

## Task 5: App + endpoints de colección de activos (GET /activos, POST /activos)

TDD: tests primero, luego la implementación mínima que los hace pasar.

**Files:**
- Create: `tests/test_api.py`
- Create: `backend/main.py`

- [ ] **Step 1: Escribir los tests de `/activos`**

```python
# tests/test_api.py
def _activo_payload(ticker="AAPL"):
    return {"ticker": ticker, "nombre": "Apple Inc.", "tipo": "accion", "mercado": "NASDAQ"}


def test_listar_activos_vacio(client):
    resp = client.get("/activos")
    assert resp.status_code == 200
    assert resp.json() == []


def test_crear_activo_devuelve_201_con_id(client):
    resp = client.post("/activos", json=_activo_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] is not None
    assert body["ticker"] == "AAPL"
    assert body["mercado"] == "NASDAQ"


def test_listar_activos_devuelve_los_creados(client):
    client.post("/activos", json=_activo_payload("AAPL"))
    client.post("/activos", json=_activo_payload("MSFT"))
    resp = client.get("/activos")
    assert resp.status_code == 200
    tickers = {a["ticker"] for a in resp.json()}
    assert tickers == {"AAPL", "MSFT"}


def test_crear_activo_body_invalido_devuelve_400(client):
    resp = client.post("/activos", json={"ticker": "AAPL"})  # faltan campos
    assert resp.status_code == 400
    assert "message" in resp.json()


def test_crear_activo_enum_invalido_devuelve_400(client):
    payload = _activo_payload()
    payload["mercado"] = "LONDON"  # fuera del enum
    resp = client.post("/activos", json=payload)
    assert resp.status_code == 400
    assert "message" in resp.json()
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL — `ImportError`/`ModuleNotFoundError` sobre `backend.main` (todavía no existe).

- [ ] **Step 3: Escribir `backend/main.py` (mínimo para estos tests)**

```python
import logging
import os

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from backend.database import create_db, get_session
from backend.models import Activo, ActivoCreate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("activos")

app = FastAPI(title="Dashboard de Análisis de Activos Financieros", version="0.1.0")

_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    create_db()


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError):
    logger.info("400 body inválido en %s %s", request.method, request.url.path)
    return JSONResponse(status_code=400, content={"message": "El body del request es inválido."})


@app.get("/activos", response_model=list[Activo])
def listar_activos(session: Session = Depends(get_session)):
    return session.exec(select(Activo)).all()


@app.post("/activos", response_model=Activo, status_code=status.HTTP_201_CREATED)
def crear_activo(data: ActivoCreate, session: Session = Depends(get_session)):
    activo = Activo.model_validate(data)
    session.add(activo)
    session.commit()
    session.refresh(activo)
    logger.info("201 activo creado id=%s ticker=%s", activo.id, activo.ticker)
    return activo
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_api.py -v`
Expected: PASS (5 tests de `/activos`).

- [ ] **Step 5: Commit**

```bash
git add backend/main.py tests/test_api.py
git commit -m "feat: GET/POST /activos con validación 400 uniforme"
```

---

## Task 6: Detalle y borrado de activo (GET /activos/{id}, DELETE /activos/{id})

`GET /activos/{id}` devuelve `ActivoDetalle` con `senales_recientes`: la `senal` del análisis más reciente (máximo `created_at`) por cada `tipo`.

**Files:**
- Modify: `tests/test_api.py` (agregar tests)
- Modify: `backend/main.py` (agregar endpoints + helper)

- [ ] **Step 1: Agregar tests de detalle y borrado**

```python
# tests/test_api.py  (agregar al final)
def _crear_activo(client, ticker="AAPL"):
    return client.post("/activos", json=_activo_payload(ticker)).json()["id"]


def _analisis_payload(tipo="tecnico", senal="compra", confianza=0.67, resumen="ok"):
    return {"tipo": tipo, "senal": senal, "confianza": confianza, "resumen": resumen}


def test_detalle_activo_sin_analisis(client):
    aid = _crear_activo(client)
    resp = client.get(f"/activos/{aid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == aid
    assert body["senales_recientes"] == {"tecnico": None, "sentimiento": None}


def test_detalle_activo_toma_la_senal_mas_reciente_por_tipo(client):
    aid = _crear_activo(client)
    client.post(f"/activos/{aid}/analisis", json=_analisis_payload("tecnico", "compra"))
    client.post(f"/activos/{aid}/analisis", json=_analisis_payload("tecnico", "venta"))
    client.post(f"/activos/{aid}/analisis", json=_analisis_payload("sentimiento", "hold"))
    resp = client.get(f"/activos/{aid}")
    assert resp.status_code == 200
    sr = resp.json()["senales_recientes"]
    assert sr["tecnico"] == "venta"       # el segundo técnico, más reciente
    assert sr["sentimiento"] == "hold"


def test_detalle_activo_inexistente_devuelve_404(client):
    resp = client.get("/activos/999")
    assert resp.status_code == 404
    assert "message" in resp.json()


def test_borrar_activo_devuelve_204(client):
    aid = _crear_activo(client)
    resp = client.delete(f"/activos/{aid}")
    assert resp.status_code == 204
    assert client.get(f"/activos/{aid}").status_code == 404


def test_borrar_activo_inexistente_devuelve_404(client):
    resp = client.delete("/activos/999")
    assert resp.status_code == 404
    assert "message" in resp.json()
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL — los nuevos tests dan 404/405 o error porque los endpoints `/activos/{id}` y `/activos/{id}/analisis` aún no existen.

- [ ] **Step 3: Agregar a `backend/main.py` el helper de error, el import y los endpoints**

Agregar el import:

```python
from fastapi import HTTPException
from backend.models import Activo, ActivoCreate, ActivoDetalle, Analisis, SenalesRecientes
```

Helper de 404 (debajo de los handlers de error):

```python
def _activo_o_404(activo_id: int, session: Session) -> Activo:
    activo = session.get(Activo, activo_id)
    if activo is None:
        raise HTTPException(status_code=404, detail={"message": "El activo solicitado no fue encontrado."})
    return activo


@app.exception_handler(HTTPException)
async def _http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=detail)
```

Endpoints:

```python
@app.get("/activos/{activo_id}", response_model=ActivoDetalle)
def detalle_activo(activo_id: int, session: Session = Depends(get_session)):
    activo = _activo_o_404(activo_id, session)
    senales = SenalesRecientes()
    for tipo in ("tecnico", "sentimiento"):
        ultimo = session.exec(
            select(Analisis)
            .where(Analisis.activo_id == activo_id, Analisis.tipo == tipo)
            .order_by(Analisis.created_at.desc())
        ).first()
        if ultimo is not None:
            setattr(senales, tipo, ultimo.senal)
    return ActivoDetalle(**activo.model_dump(), senales_recientes=senales)


@app.delete("/activos/{activo_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_activo(activo_id: int, session: Session = Depends(get_session)):
    activo = _activo_o_404(activo_id, session)
    session.delete(activo)
    session.commit()
    logger.info("204 activo borrado id=%s", activo_id)
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/test_api.py -v`
Expected: PASS (los tests de detalle/borrado, además de los anteriores). Los de `/analisis` dentro de Step 1 (`_analisis_payload` vía POST) dependen del Task 7; si fallan por el POST de análisis, completar Task 7 y volver a correr. Para aislar ahora: `uv run pytest tests/test_api.py -k "detalle or borrar" -v`.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py tests/test_api.py
git commit -m "feat: GET/DELETE /activos/{id} con senales_recientes y 404 uniforme"
```

---

## Task 7: Análisis de un activo (GET y POST /activos/{id}/analisis)

**Files:**
- Modify: `tests/test_api.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Agregar tests**

```python
# tests/test_api.py  (agregar al final)
def test_crear_analisis_devuelve_201(client):
    aid = _crear_activo(client)
    resp = client.post(f"/activos/{aid}/analisis", json=_analisis_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] is not None
    assert body["activo_id"] == aid
    assert body["created_at"]  # no vacío
    assert body["senal"] == "compra"


def test_listar_analisis_orden_descendente(client):
    aid = _crear_activo(client)
    client.post(f"/activos/{aid}/analisis", json=_analisis_payload("tecnico", "compra"))
    client.post(f"/activos/{aid}/analisis", json=_analisis_payload("tecnico", "venta"))
    resp = client.get(f"/activos/{aid}/analisis")
    assert resp.status_code == 200
    senales = [a["senal"] for a in resp.json()]
    assert senales == ["venta", "compra"]  # más reciente primero


def test_crear_analisis_confianza_fuera_de_rango_devuelve_400(client):
    aid = _crear_activo(client)
    resp = client.post(f"/activos/{aid}/analisis", json=_analisis_payload(confianza=1.5))
    assert resp.status_code == 400
    assert "message" in resp.json()


def test_crear_analisis_en_activo_inexistente_devuelve_404(client):
    resp = client.post("/activos/999/analisis", json=_analisis_payload())
    assert resp.status_code == 404
    assert "message" in resp.json()


def test_listar_analisis_de_activo_inexistente_devuelve_404(client):
    resp = client.get("/activos/999/analisis")
    assert resp.status_code == 404
    assert "message" in resp.json()
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/test_api.py -k "analisis" -v`
Expected: FAIL — los endpoints de `/activos/{id}/analisis` no existen.

- [ ] **Step 3: Agregar a `backend/main.py` el import y los endpoints**

Agregar import:

```python
from datetime import datetime, timezone
from backend.models import AnalisisCreate
```

Helper para `created_at` y los endpoints:

```python
def _ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@app.get("/activos/{activo_id}/analisis", response_model=list[Analisis])
def listar_analisis(activo_id: int, session: Session = Depends(get_session)):
    _activo_o_404(activo_id, session)
    return session.exec(
        select(Analisis)
        .where(Analisis.activo_id == activo_id)
        .order_by(Analisis.created_at.desc(), Analisis.id.desc())
    ).all()


@app.post(
    "/activos/{activo_id}/analisis",
    response_model=Analisis,
    status_code=status.HTTP_201_CREATED,
)
def crear_analisis(activo_id: int, data: AnalisisCreate, session: Session = Depends(get_session)):
    _activo_o_404(activo_id, session)
    analisis = Analisis(**data.model_dump(), activo_id=activo_id, created_at=_ahora_iso())
    session.add(analisis)
    session.commit()
    session.refresh(analisis)
    logger.info("201 análisis creado id=%s activo=%s senal=%s", analisis.id, activo_id, analisis.senal)
    return analisis
```

(El `order_by` incluye `id.desc()` como desempate: dos análisis creados en el mismo segundo comparten `created_at`, y el `id` mayor es el más nuevo. Esto hace determinísticos los tests de orden y de `senales_recientes`.)

- [ ] **Step 4: Actualizar el helper de `senales_recientes` para el desempate por id**

En `detalle_activo`, cambiar el `order_by` a:

```python
            .order_by(Analisis.created_at.desc(), Analisis.id.desc())
```

- [ ] **Step 5: Correr toda la suite**

Run: `uv run pytest tests/test_api.py -v`
Expected: PASS (todos, incluidos los de Task 6 que usaban POST de análisis).

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/test_api.py
git commit -m "feat: GET/POST /activos/{id}/analisis con orden y validación de confianza"
```

---

## Task 8: Borrado de un análisis (DELETE /activos/{id}/analisis/{analisisId})

**Files:**
- Modify: `tests/test_api.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Agregar tests**

```python
# tests/test_api.py  (agregar al final)
def test_borrar_analisis_devuelve_204(client):
    aid = _crear_activo(client)
    anid = client.post(f"/activos/{aid}/analisis", json=_analisis_payload()).json()["id"]
    resp = client.delete(f"/activos/{aid}/analisis/{anid}")
    assert resp.status_code == 204
    assert client.get(f"/activos/{aid}/analisis").json() == []


def test_borrar_analisis_inexistente_devuelve_404(client):
    aid = _crear_activo(client)
    resp = client.delete(f"/activos/{aid}/analisis/999")
    assert resp.status_code == 404
    assert "message" in resp.json()


def test_borrar_analisis_de_activo_inexistente_devuelve_404(client):
    resp = client.delete("/activos/999/analisis/1")
    assert resp.status_code == 404
    assert "message" in resp.json()
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/test_api.py -k "borrar_analisis" -v`
Expected: FAIL — el endpoint no existe (405/404 inesperado).

- [ ] **Step 3: Agregar el endpoint a `backend/main.py`**

```python
@app.delete(
    "/activos/{activo_id}/analisis/{analisis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def borrar_analisis(activo_id: int, analisis_id: int, session: Session = Depends(get_session)):
    _activo_o_404(activo_id, session)
    analisis = session.get(Analisis, analisis_id)
    if analisis is None or analisis.activo_id != activo_id:
        raise HTTPException(status_code=404, detail={"message": "El análisis solicitado no fue encontrado."})
    session.delete(analisis)
    session.commit()
    logger.info("204 análisis borrado id=%s activo=%s", analisis_id, activo_id)
```

- [ ] **Step 4: Correr toda la suite**

Run: `uv run pytest tests/test_api.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py tests/test_api.py
git commit -m "feat: DELETE /activos/{id}/analisis/{analisisId}"
```

---

## Task 9: Borrado en cascada (test de integridad)

Verifica que borrar un activo borra sus análisis (PRAGMA FK + ondelete CASCADE).

**Files:**
- Modify: `tests/test_api.py`

- [ ] **Step 1: Agregar el test de cascada**

```python
# tests/test_api.py  (agregar al final)
def test_borrar_activo_borra_sus_analisis_en_cascada(client, session):
    from backend.models import Analisis

    aid = _crear_activo(client)
    client.post(f"/activos/{aid}/analisis", json=_analisis_payload("tecnico", "compra"))
    client.post(f"/activos/{aid}/analisis", json=_analisis_payload("sentimiento", "hold"))

    from sqlmodel import select
    assert len(session.exec(select(Analisis).where(Analisis.activo_id == aid)).all()) == 2

    assert client.delete(f"/activos/{aid}").status_code == 204

    session.expire_all()
    assert session.exec(select(Analisis).where(Analisis.activo_id == aid)).all() == []
```

- [ ] **Step 2: Correr el test**

Run: `uv run pytest tests/test_api.py::test_borrar_activo_borra_sus_analisis_en_cascada -v`
Expected: PASS. Si FALLA (los análisis sobreviven), el `ondelete="CASCADE"` o el PRAGMA no están activos — revisar Task 2 (`ForeignKey(..., ondelete="CASCADE")`) y el listener del PRAGMA en `tests/conftest.py`.

- [ ] **Step 3: Correr toda la suite una vez más**

Run: `uv run pytest -v`
Expected: PASS (todos los tests del proyecto).

- [ ] **Step 4: Commit**

```bash
git add tests/test_api.py
git commit -m "test: borrado en cascada de análisis al borrar un activo"
```

---

## Task 10: Verificación manual del servidor

Confirma que el backend levanta y `/docs` refleja el contrato.

**Files:** ninguno (verificación).

- [ ] **Step 1: Levantar el servidor**

Run: `uv run uvicorn backend.main:app --reload --port 8000`
Expected: arranca sin error; crea `data/activos.db` al inicializar.

- [ ] **Step 2: Probar endpoints con curl** (en otra terminal)

```bash
curl http://localhost:8000/activos
# Expected: []
curl -X POST http://localhost:8000/activos -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","nombre":"Apple Inc.","tipo":"accion","mercado":"NASDAQ"}'
# Expected: 201 con el activo y su id
```

- [ ] **Step 3: Revisar `/docs`**

Abrir http://localhost:8000/docs y verificar que los 7 endpoints aparecen con sus schemas y status codes, coincidiendo con `openapi.yaml`.

- [ ] **Step 4: Frenar el servidor** (Ctrl+C). Sin commit (no hubo cambios de código).

---

## Self-Review (completado por el autor del plan)

**Cobertura del spec (subsistema A):**
- 7 endpoints (§4.3): Tasks 5-8. ✓
- Modelo relacional + FK cascada (§4.4): Tasks 2, 3, 9. ✓
- Tres modelos por recurso (§4.4): Task 2. ✓
- `senales_recientes` = señal más reciente por tipo (endpoint 3): Task 6 (con desempate por id en Task 7). ✓
- Schema de error único `{message}` (§4.5): handlers en Tasks 5-6. ✓
- Status codes 200/201/204/400/404 (§4.1): cubiertos por tests en cada task. ✓
- Validación de `confianza ∈ [0,1]` (§4.3): Task 7. ✓
- `openapi.yaml` fuente de verdad (§4.6): Task 1. ✓
- CORS `:3000` (§4.3): Task 5. ✓
- `logging` no `print()` (§4.5): en todos los handlers. ✓
- Tests pytest de los 7 endpoints + cascade (§8 del spec): Tasks 5-9. ✓
- `DATABASE_URL` por env (§5.2): Task 3. ✓
- Fuera de alcance de este plan: `scripts/` (Plan 2), frontend (Plan 3), `seed.py` (Plan 2). El backend acepta `sentimiento` (la restricción es de la skill). ✓

**Notas de consistencia de tipos:**
- Nombres de path param: el código usa `activo_id`/`analisis_id`; el `openapi.yaml` usa `{id}`/`{analisisId}`. FastAPI mapea por posición, no por nombre — no afecta el contrato funcional, pero al comparar `/docs` con `openapi.yaml` los nombres de parámetros diferirán (cosmético). Si se quiere paridad exacta de nombres, renombrar en el YAML a `{activo_id}`/`{analisis_id}` (decisión menor, no bloquea).
- `created_at` es `str` ISO 8601 con `Z`; el orden lexicográfico coincide con el cronológico (mismo formato y zona), por eso `order_by(created_at.desc())` es correcto; el desempate por `id.desc()` cubre el mismo segundo.

**Decisión `on_event("startup")`:** FastAPI marca `on_event` como deprecado a favor de `lifespan`. Se usa `on_event` por simplicidad y porque funciona en la versión pineada; si el engineer ve el warning, es esperado y no bloquea. Migrar a `lifespan` es opcional.

---

## Próximos planes (no incluidos acá)

- **Plan 2 — Capa de análisis (`scripts/`):** `indicators.py` (RSI/MACD/SMA puros + tests), `prices.py` (yfinance + caché + fallback), `generar_senal.py` (orquestación + POST + 400 de `sentimiento`), `seed.py` (3 activos + análisis precargado, cascada caché/red/hardcode). Verificar el pin `numpy<2` por pandas-ta.
- **Plan 3 — Frontend:** `frontend/index.html` single-file (grid de cards, formulario de alta, card expandida, paleta Intel, `state`/`render()`).
