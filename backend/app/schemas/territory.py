from __future__ import annotations

from typing import Optional, List
from .common import AppModel


class RegionOut(AppModel):
    id: int
    name_uz: str
    name_uz_cyr: Optional[str] = None
    name_ru: Optional[str] = None
    code: str


class DistrictOut(AppModel):
    id: int
    region_id: int
    name_uz: str
    code: str


class MahallaOut(AppModel):
    id: int
    district_id: int
    name_uz: str
    code: str
    daily_capacity: int


class RegionWithDistricts(RegionOut):
    districts: List[DistrictOut] = []
