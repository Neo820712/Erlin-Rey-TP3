from enum import Enum
from typing import Optional

from sqlalchemy import Column, ForeignKey, Integer
from sqlmodel import Field, SQLModel


class TipoActivo(str, Enum):
    accion = "accion"
    ON = "ON"


class Mercado(str, Enum):
    BYMA = "BYMA"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"


class TipoAnalisis(str, Enum):
    tecnico = "tecnico"
    sentimiento = "sentimiento"


class Senal(str, Enum):
    compra = "compra"
    venta = "venta"
    hold = "hold"


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
