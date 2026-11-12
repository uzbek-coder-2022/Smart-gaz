"""GPS tracking endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import get_current_user, require_roles
from ...core.db import get_db
from ...models.models import Driver, User
from ...models.enums import UserRole
from ...schemas.tracking import LocationUpdate, DriverLocationOut
from ...services import tracking as tracking_svc

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.post("/update-location", response_model=DriverLocationOut)
async def update_location(
    payload: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DRIVER)),
):
    driver = (await db.execute(select(Driver).where(Driver.user_id == current_user.id))).scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=400, detail="Haydovchi profili topilmadi")
    driver = await tracking_svc.update_location(db, driver.id, payload.lat, payload.lon, payload.speed)
    await db.commit()
    return DriverLocationOut(
        driver_id=driver.id,
        lat=driver.last_lat,
        lon=driver.last_lon,
        speed=driver.last_speed,
        recorded_at=driver.updated_at,
    )


@router.get("/driver/{driver_id}", response_model=DriverLocationOut | None)
async def driver_location(
    driver_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    d = await tracking_svc.get_driver_location(db, driver_id)
    if not d or d.last_lat is None:
        return None
    return DriverLocationOut(driver_id=d.id, lat=d.last_lat, lon=d.last_lon, speed=d.last_speed, recorded_at=d.updated_at)


@router.get("/me")
async def incoming_driver_for_me(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await tracking_svc.get_incoming_driver_for_user(db, current_user.id)
