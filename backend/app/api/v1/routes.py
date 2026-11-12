"""Delivery route endpoints for dispatchers and drivers."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import get_current_user, require_roles
from ...core.db import get_db
from ...models.models import DeliveryRoute, Order, User, Driver
from ...models.enums import UserRole
from ...schemas.route import RouteCreate, RouteOut, RouteDetail
from ...services import routes as route_svc

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("/admin", response_model=RouteDetail, status_code=201)
async def create_route(
    payload: RouteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DISPATCHER, UserRole.ADMIN, UserRole.OPERATOR_HEAD)),
):
    from ...schemas.order import OrderOut as OrderOutSchema
    route, _orders = await route_svc.create_route(
        db,
        driver_id=payload.driver_id,
        mahalla_id=payload.mahalla_id,
        allocated_cylinders=payload.allocated_cylinders,
        route_date=payload.route_date,
        created_by_id=current_user.id,
    )
    await db.commit()
    await db.refresh(route)
    res = await db.execute(select(Order).where(Order.route_id == route.id).order_by(Order.queue_number))
    orders = list(res.scalars().all())
    return RouteDetail(
        **RouteOut.model_validate(route).model_dump(),
        orders=[OrderOutSchema.model_validate(o) for o in orders],
    )


@router.get("/today", response_model=RouteDetail | None)
async def today_route(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(UserRole.DRIVER))):
    driver = (await db.execute(select(Driver).where(Driver.user_id == current_user.id))).scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=400, detail="Haydovchi profili topilmadi")
    route, orders = await route_svc.get_today_route(db, driver.id)
    if not route:
        return None
    from ...schemas.order import OrderOut
    return RouteDetail(
        **RouteOut.model_validate(route).model_dump(),
        orders=[OrderOut.model_validate(o) for o in orders],
    )


@router.post("/{route_id}/start", response_model=RouteOut)
async def start_route(route_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(UserRole.DRIVER))):
    route = await db.get(DeliveryRoute, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Marshrut topilmadi")
    driver = (await db.execute(select(Driver).where(Driver.user_id == current_user.id))).scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=400, detail="Haydovchi profili topilmadi")
    route = await route_svc.start_route(db, route, driver.id)
    await db.commit()
    await db.refresh(route)
    return RouteOut.model_validate(route)


@router.post("/{route_id}/finish", response_model=RouteOut)
async def finish_route(route_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(UserRole.DRIVER))):
    route = await db.get(DeliveryRoute, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Marshrut topilmadi")
    route = await route_svc.finish_route(db, route)
    await db.commit()
    await db.refresh(route)
    return RouteOut.model_validate(route)
