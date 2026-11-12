from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LocationUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    speed: Optional[float] = None


class DriverLocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    driver_id: int
    lat: float
    lon: float
    speed: Optional[float] = None
    recorded_at: datetime
