"""GPS tracking service."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.models import Driver, DriverLocation, Order, DeliveryRoute
from ..models.enums import OrderStatus, RouteStatus


async def update_location(db: AsyncSession, driver_id: int, lat: float, lon: float, speed: float | None = None) -> Driver:
    driver = await db.get(Driver, driver_id)
    if not driver:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Haydovchi topilmadi")
    driver.last_lat = lat
    driver.last_lon = lon
    driver.last_speed = speed
    driver.updated_at = datetime.now(timezone.utc)
    loc = DriverLocation(driver_id=driver_id, lat=lat, lon=lon, speed=speed, recorded_at=driver.updated_at)
    db.add(loc)
    await db.flush()
    return driver


async def get_driver_location(db: AsyncSession, driver_id: int) -> Optional[Driver]:
    return await db.get(Driver, driver_id)


async def get_incoming_driver_for_user(db: AsyncSession, user_id: int) -> Optional[dict]:
    """Return active driver (lat/lon) currently delivering to the citizen."""
    res = await db.execute(
        select(Order, DeliveryRoute, Driver)
        .join(DeliveryRoute, DeliveryRoute.id == Order.route_id)
        .join(Driver, Driver.id == DeliveryRoute.driver_id)
        .where(
            Order.user_id == user_id,
            Order.status == OrderStatus.ON_WAY,
            DeliveryRoute.status == RouteStatus.IN_PROGRESS,
        )
        .order_by(Order.id.desc())
        .limit(1)
    )
    row = res.first()
    if not row:
        return None
    order, route, driver = row
    if driver.last_lat is None or driver.last_lon is None:
        return None
    return {
        "driver_id": driver.id,
        "car_number": driver.car_number,
        "lat": driver.last_lat,
        "lon": driver.last_lon,
        "speed": driver.last_speed,
        "updated_at": driver.updated_at.isoformat() if driver.updated_at else None,
        "route_id": route.id,
        "order_id": order.id,
    }
