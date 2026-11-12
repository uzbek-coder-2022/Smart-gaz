"""Public territory reference: regions, districts, mahallas."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.db import get_db
from ...models.models import Region, District, Mahalla
from ...schemas.territory import RegionOut, DistrictOut, MahallaOut, RegionWithDistricts

router = APIRouter(prefix="/territory", tags=["territory"])


@router.get("/regions", response_model=list[RegionWithDistricts])
async def list_regions(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Region).options(selectinload(Region.districts)).order_by(Region.name_uz))
    return list(res.scalars().all())


@router.get("/districts/{region_id}", response_model=list[DistrictOut])
async def list_districts(region_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(District).where(District.region_id == region_id).order_by(District.name_uz))
    return list(res.scalars().all())


@router.get("/mahallas/{district_id}", response_model=list[MahallaOut])
async def list_mahallas(district_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Mahalla).where(Mahalla.district_id == district_id).order_by(Mahalla.name_uz))
    return list(res.scalars().all())
