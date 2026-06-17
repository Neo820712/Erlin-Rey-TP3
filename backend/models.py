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
    score: Optional[float] = None


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
    score: Optional[float] = None


class ActivoDetalle(ActivoBase):
    id: int
    senales_recientes: SenalesRecientes


# --- MercadoCedear ---
class MercadoCedearBase(SQLModel):
    ticker_byma: str
    ticker_us: str
    nombre: str
    precio_usd: Optional[float] = None
    var_pct: Optional[float] = None
    volumen: Optional[int] = None
    rsi: Optional[float] = None
    senal: Optional[Senal] = None
    pe: Optional[float] = None
    eps: Optional[float] = None
    market_cap: Optional[int] = None
    w52_high: Optional[float] = None
    w52_low: Optional[float] = None
    free_cash_flow: Optional[float] = None
    margen_neto: Optional[float] = None
    roe: Optional[float] = None
    price_to_book: Optional[float] = None
    dividend_yield: Optional[float] = None
    actualizado_en: str


class MercadoCedearCreate(MercadoCedearBase):
    pass


class MercadoCedear(MercadoCedearBase, table=True):
    __tablename__ = "mercado_cedears"
    id: Optional[int] = Field(default=None, primary_key=True)


# --- Precio (tabla interna de OHLC, fuente unica de precios) ---
class PrecioBase(SQLModel):
    ticker: str
    fecha: str
    open: float
    high: float
    low: float
    close: float
    volumen: Optional[int] = None


class Precio(PrecioBase, table=True):
    __tablename__ = "precios"
    id: Optional[int] = Field(default=None, primary_key=True)
