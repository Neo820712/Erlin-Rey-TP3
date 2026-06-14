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
