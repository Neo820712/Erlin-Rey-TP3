import logging
import os
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from backend.database import create_db, get_session
from backend.models import (
    Activo,
    ActivoCreate,
    ActivoDetalle,
    Analisis,
    AnalisisCreate,
    SenalesRecientes,
)

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


def _activo_o_404(activo_id: int, session: Session) -> Activo:
    activo = session.get(Activo, activo_id)
    if activo is None:
        raise HTTPException(status_code=404, detail={"message": "El activo solicitado no fue encontrado."})
    return activo


@app.exception_handler(HTTPException)
async def _http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=detail)


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
