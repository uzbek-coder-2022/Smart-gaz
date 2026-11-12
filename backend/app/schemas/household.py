from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from ..models.enums import HouseholdStatus


class HouseholdCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region_id: int
    district_id: int
    mahalla_id: int
    street: str = Field(..., min_length=1, max_length=200)
    house_number: str = Field(..., min_length=1, max_length=40)
    apartment: Optional[str] = None
    kadastr_number: Optional[str] = None
    lpg_card_id: Optional[str] = None
    family_size: Optional[int] = Field(None, ge=1, le=50)


class HouseholdOut(HouseholdCreate):
    id: int
    household_key: str
    status: HouseholdStatus
    in_social_register: bool
    last_delivered_at: Optional[str] = None
