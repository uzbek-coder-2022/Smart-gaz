"""Admin/dispatcher statistics and driver management."""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import require_roles
from ...core.db import get_db
from ...models.models import User, Driver, Order, Household, DeliveryRoute
from ...models.enums import UserRole, OrderStatus, RouteStatus

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db), _: User = Depends(require_roles(UserRole.DISPATCHER, UserRole.ADMIN, UserRole.OPERATOR_HEAD, UserRole.INSPECTOR))):
    total_households = (await db.execute(select(func.count(Household.id)))).scalar_one()
    in_queue = (await db.execute(select(func.count(Order.id)).where(Order.status == OrderStatus.PENDING))).scalar_one()
    on_way = (await db.execute(select(func.count(Order.id)).where(Order.status == OrderStatus.ON_WAY))).scalar_one()
    delivered_today = (await db.execute(
        select(func.count(Order.id)).where(Order.status == OrderStatus.DELIVERED, func.date(Order.delivered_at) == date.today())
    )).scalar_one()
    active_drivers = (await db.execute(select(func.count(Driver.id)).where(Driver.is_active == True))).scalar_one()
    active_routes = (await db.execute(select(func.count(DeliveryRoute.id)).where(DeliveryRoute.status == RouteStatus.IN_PROGRESS))).scalar_one()

    return {
        "households_total": int(total_households),
        "orders_pending": int(in_queue),
        "orders_on_way": int(on_way),
        "delivered_today": int(delivered_today),
        "active_drivers": int(active_drivers),
        "active_routes": int(active_routes),
    }
