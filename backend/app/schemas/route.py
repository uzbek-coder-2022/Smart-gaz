from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import RouteStatus
from .order import OrderOut


class RouteCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    driver_id: int
    mahalla_id: int
    allocated_cylinders: int = Field(..., ge=1, le=200)
    route_date: date


class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    driver_id: int
    mahalla_id: int
    allocated_cylinders: int
    delivered_count: int
    status: RouteStatus
    route_date: date
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class RouteDetail(RouteOut):
    orders: List[OrderOut] = []
