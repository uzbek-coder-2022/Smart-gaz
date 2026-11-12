"""Orders / queue endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import get_current_user, require_roles
from ...core.db import get_db
from ...models.models import Order, User, Household
from ...models.enums import UserRole, OrderStatus
from ...schemas.order import OrderOut, QueueStatus, CompleteDeliveryRequest, CancelRequest
from ...services import orders as order_svc
from ...services.orders import AntifraudError

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/create", response_model=OrderOut, status_code=201)
async def create_order(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.household_id:
        raise HTTPException(status_code=400, detail="Avval xonadon profilini to'ldiring")
    try:
        order = await order_svc.create_order(db, current_user.id, current_user.household_id)
    except AntifraudError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=e.message, headers={"X-Error-Code": e.code})
    await db.commit()
    await db.refresh(order)
    return OrderOut.model_validate(order)


@router.get("/queue-status/me", response_model=QueueStatus)
async def my_queue_status(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.household_id:
        raise HTTPException(status_code=400, detail="Xonadon profili topilmadi")
    household = await db.get(Household, current_user.household_id)
    data = await order_svc.get_queue_status(db, household)
    return QueueStatus(**data)


@router.post("/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(
    order_id: int,
    payload: CancelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    if order.user_id != current_user.id and current_user.role not in (UserRole.DISPATCHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")
    order = await order_svc.cancel_order(db, order, reason=payload.reason, actor_user_id=current_user.id)
    await db.commit()
    await db.refresh(order)
    return OrderOut.model_validate(order)


@router.post("/{order_id}/complete", response_model=OrderOut)
async def complete(
    order_id: int,
    payload: CompleteDeliveryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DRIVER, UserRole.DISPATCHER, UserRole.ADMIN)),
):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    order = await order_svc.complete_delivery(
        db, order,
        weight_kg=payload.weight_kg,
        payment_type=payload.payment_type,
        price_total=payload.price_total,
    )
    await db.commit()
    await db.refresh(order)
    return OrderOut.model_validate(order)
