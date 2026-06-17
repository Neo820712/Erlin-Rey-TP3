import json
import logging
import os
import re
import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.database import create_db, get_session
from backend.models import (
    Activo,
    ActivoCreate,
    ActivoDetalle,
    Analisis,
    AnalisisCreate,
    MercadoCedear,
    SenalesRecientes,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("activos")

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    yield


app = FastAPI(
    title="Dashboard de Análisis de Activos Financieros",
    version="0.1.0",
    lifespan=lifespan,
)

_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError):
    logger.info("400 body inválido en %s %s", request.method, request.url.path)
    return JSONResponse(status_code=400, content={"message": "El body del request es inválido."})


def _activo_o_404(activo_id: int, session: Session) -> Activo:
    activo = session.get(Activo, activo_id)
    if activo is None:
        raise HTTPException(status_code=404, detail={"message": "El activo solicitado no fue encontrado."})
    return activo


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Se registra en la clase base de Starlette para capturar tanto los HTTPException
    # propios (detail dict) como los del framework (p. ej. 404 de ruta inexistente, con
    # detail string), y normalizar todo al schema {message}.
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=detail)


@app.get("/activos", response_model=list[Activo])
def listar_activos(session: Session = Depends(get_session)):
    return session.exec(select(Activo)).all()


@app.post("/activos", response_model=Activo, status_code=status.HTTP_201_CREATED)
def crear_activo(data: ActivoCreate, response: Response, session: Session = Depends(get_session)):
    existente = session.exec(select(Activo).where(Activo.ticker == data.ticker)).first()
    if existente is not None:
        response.status_code = status.HTTP_200_OK
        logger.info("200 activo ya existía id=%s ticker=%s", existente.id, existente.ticker)
        return existente
    activo = Activo.model_validate(data)
    session.add(activo)
    session.commit()
    session.refresh(activo)
    logger.info("201 activo creado id=%s ticker=%s", activo.id, activo.ticker)
    return activo


@app.get("/activos/{activo_id}", response_model=ActivoDetalle)
def detalle_activo(activo_id: int, session: Session = Depends(get_session)):
    activo = _activo_o_404(activo_id, session)
    senales = SenalesRecientes()
    for tipo in ("tecnico", "sentimiento"):
        ultimo = session.exec(
            select(Analisis)
            .where(Analisis.activo_id == activo_id, Analisis.tipo == tipo)
            .order_by(Analisis.created_at.desc(), Analisis.id.desc())
        ).first()
        if ultimo is not None:
            setattr(senales, tipo, ultimo.senal)
            if tipo == "tecnico":
                senales.score = ultimo.score
    return ActivoDetalle(**activo.model_dump(), senales_recientes=senales)


@app.delete("/activos/{activo_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_activo(activo_id: int, session: Session = Depends(get_session)):
    activo = _activo_o_404(activo_id, session)
    session.delete(activo)
    session.commit()
    logger.info("204 activo borrado id=%s", activo_id)


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


@app.post(
    "/activos/{activo_id}/analisis/tecnico",
    response_model=Analisis,
    status_code=status.HTTP_201_CREATED,
)
def crear_analisis_tecnico(activo_id: int, session: Session = Depends(get_session)):
    activo = _activo_o_404(activo_id, session)
    if not _TICKER_VALIDO.fullmatch(activo.ticker):
        raise HTTPException(status_code=400, detail={"message": "Ticker inválido."})
    stdout = _correr_script("scripts.score_tecnico", activo.ticker)
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        logger.error("salida no-JSON de scripts.score_tecnico: %r", stdout[:500])
        raise HTTPException(status_code=500, detail={"message": "Respuesta inválida del cálculo técnico."})
    if "error" in data:
        raise HTTPException(status_code=400, detail={"message": data["error"]})
    analisis = Analisis(
        tipo="tecnico",
        senal=data["senal"],
        confianza=data["confianza"],
        resumen=data["resumen"],
        score=data["score"],
        activo_id=activo_id,
        created_at=_ahora_iso(),
    )
    session.add(analisis)
    session.commit()
    session.refresh(analisis)
    logger.info("201 análisis técnico id=%s activo=%s score=%s", analisis.id, activo_id, analisis.score)
    return analisis


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


_CATALOGO_PATH = os.environ.get("CEDEARS_PATH", "data/cedears.json")


@app.get("/mercado/catalogo")
def catalogo_cedears():
    try:
        with open(_CATALOGO_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        logger.error("no se pudo leer el catálogo %s: %s", _CATALOGO_PATH, e)
        raise HTTPException(status_code=500, detail={"message": "No se pudo leer el catálogo de CEDEARs."})


@app.get("/mercado/cedears")
def listar_mercado(session: Session = Depends(get_session)):
    filas = session.exec(select(MercadoCedear)).all()
    actualizado_en = filas[0].actualizado_en if filas else None
    return {"cedears": filas, "actualizado_en": actualizado_en}


def _correr_script(modulo: str, *args: str) -> str:
    """Corre `python -m scripts.<modulo> args...` y devuelve stdout. El backend no importa
    yfinance/pandas: delega en el subproceso. Lanza HTTPException(500) si el script falla."""
    cmd = [sys.executable, "-m", modulo, *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        logger.error("script %s falló (rc=%s): %s", modulo, proc.returncode, proc.stderr.strip())
        raise HTTPException(status_code=500, detail={"message": "Falló la actualización de datos de mercado."})
    return proc.stdout


@app.post("/mercado/actualizar")
def actualizar_mercado():
    stdout = _correr_script("scripts.mercado")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        logger.error("salida no-JSON de scripts.mercado: %r", stdout[:500])
        raise HTTPException(status_code=500, detail={"message": "Respuesta inválida del proceso de actualización."})


_PERIODOS_VALIDOS = {"1m", "3m", "6m", "1y"}
_TICKER_VALIDO = re.compile(r"[A-Za-z0-9.][A-Za-z0-9.\-]{0,11}")


@app.get("/mercado/{ticker}/historico")
def historico_mercado(ticker: str, periodo: str = "3m"):
    if periodo not in _PERIODOS_VALIDOS:
        raise HTTPException(status_code=400, detail={"message": f"Período inválido: {periodo}."})
    if not _TICKER_VALIDO.fullmatch(ticker):
        raise HTTPException(status_code=400, detail={"message": "Ticker inválido."})
    stdout = _correr_script("scripts.historico", ticker, periodo)
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        logger.error("salida no-JSON de scripts.historico: %r", stdout[:500])
        raise HTTPException(status_code=500, detail={"message": "Respuesta inválida del proceso de histórico."})
    if "error" in data:
        raise HTTPException(status_code=400, detail={"message": f"No hay precios para {ticker}. Corré Actualizar primero."})
    return data


@app.get("/mercado/{ticker}/tecnico")
def tecnico_mercado(ticker: str):
    if not _TICKER_VALIDO.fullmatch(ticker):
        raise HTTPException(status_code=400, detail={"message": "Ticker inválido."})
    stdout = _correr_script("scripts.score_tecnico", ticker)
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        logger.error("salida no-JSON de scripts.score_tecnico: %r", stdout[:500])
        raise HTTPException(status_code=500, detail={"message": "Respuesta inválida del cálculo técnico."})
    if "error" in data:
        raise HTTPException(status_code=400, detail={"message": f"No hay precios para {ticker}. Corré Actualizar primero."})
    return data


@app.get("/mercado/{ticker}/fundamentales", response_model=MercadoCedear)
def fundamentales_mercado(ticker: str, session: Session = Depends(get_session)):
    if not _TICKER_VALIDO.fullmatch(ticker):
        raise HTTPException(status_code=400, detail={"message": "Ticker inválido."})
    fila = session.exec(
        select(MercadoCedear).where(MercadoCedear.ticker_byma == ticker.upper())
    ).first()
    if fila is None:
        raise HTTPException(status_code=404, detail={"message": "El ticker no está en el snapshot de mercado."})
    return fila
