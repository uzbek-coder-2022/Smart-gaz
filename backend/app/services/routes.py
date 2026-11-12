"""Route planning service: dispatcher creates routes, driver starts/finishes them."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.models import DeliveryRoute, Order, Driver, Mahalla
from ..models.enums import RouteStatus, OrderStatus


async def create_route(db: AsyncSession, driver_id: int, mahalla_id: int, allocated_cylinders: int, route_date, created_by_id: int | None = None) -> tuple[DeliveryRoute, List[Order]]:
    # 1. Validate
    driver = await db.get(Driver, driver_id)
    if not driver or not driver.is_active:
        raise HTTPException(status_code=400, detail="Haydovchi topilmadi yoki nofaol")
    mahalla = await db.get(Mahalla, mahalla_id)
    if not mahalla:
        raise HTTPException(status_code=400, detail="Mahalla topilmadi")
    if allocated_cylinders > driver.capacity:
        raise HTTPException(status_code=400, detail=f"Ajratilgan ballon soni mashina sig'imidan ({driver.capacity}) oshmasligi kerak")

    # 2. Select top N PENDING orders FIFO
    # NOTE: select ... for update skip locked is Postgres-only; on SQLite we
    # fall back to a plain select (service-layer serialisation is sufficient
    # for single-worker dev deployments).
    stmt = (
        select(Order)
        .where(Order.mahalla_id == mahalla_id, Order.status == OrderStatus.PENDING)
        .order_by(Order.queue_number.asc())
        .limit(allocated_cylinders)
    )
    if not db.bind.dialect.name == "sqlite":
        stmt = stmt.with_for_update(skip_locked=True)
    res = await db.execute(stmt)
    orders = list(res.scalars().all())
    if not orders:
        raise HTTPException(status_code=400, detail="Bu mahallada navbatda turgan xonadonlar yo'q")

    route = DeliveryRoute(
        driver_id=driver_id,
        mahalla_id=mahalla_id,
        allocated_cylinders=allocated_cylinders,
        delivered_count=0,
        status=RouteStatus.PLANNED,
        route_date=route_date,
        created_by_id=created_by_id,
    )
    db.add(route)
    await db.flush()

    now = datetime.now(timezone.utc)
    for o in orders:
        o.route_id = route.id
        o.status = OrderStatus.APPROVED
        o.approved_at = now

    await db.flush()
    await db.refresh(route)
    return route, orders


async def start_route(db: AsyncSession, route: DeliveryRoute, driver_id: int) -> DeliveryRoute:
    if route.driver_id != driver_id:
        raise HTTPException(status_code=403, detail="Bu marshrut sizga biriktirilmagan")
    if route.status != RouteStatus.PLANNED:
        raise HTTPException(status_code=400, detail="Marshrut allaqachon boshlangan yoki tugallangan")
    route.status = RouteStatus.IN_PROGRESS
    route.started_at = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)
    await db.execute(
        update(Order)
        .where(Order.route_id == route.id, Order.status == OrderStatus.APPROVED)
        .values(status=OrderStatus.ON_WAY, on_way_at=now)
    )
    await db.flush()
    await db.refresh(route)
    return route


async def finish_route(db: AsyncSession, route: DeliveryRoute) -> DeliveryRoute:
    if route.status != RouteStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Marshrut davom etmayapti")
    route.status = RouteStatus.COMPLETED
    route.finished_at = datetime.now(timezone.utc)

    # Return undelivered orders to PENDING, preserving queue number
    await db.execute(
        update(Order)
        .where(Order.route_id == route.id, Order.status.in_((OrderStatus.APPROVED, OrderStatus.ON_WAY)))
        .values(
            route_id=None,
            status=OrderStatus.PENDING,
            on_way_at=None,
            approved_at=None,
        )
    )
    await db.flush()
    await db.refresh(route)
    return route


async def get_today_route(db: AsyncSession, driver_id: int) -> tuple[DeliveryRoute | None, List[Order]]:
    from datetime import date
    res = await db.execute(
        select(DeliveryRoute)
        .where(DeliveryRoute.driver_id == driver_id, DeliveryRoute.route_date == date.today())
        .order_by(DeliveryRoute.id.desc())
        .limit(1)
    )
    route = res.scalar_one_or_none()
    if not route:
        return None, []
    res = await db.execute(
        select(Order)
        .where(Order.route_id == route.id)
        .order_by(Order.queue_number.asc())
    )
    orders = list(res.scalars().all())
    return route, orders
