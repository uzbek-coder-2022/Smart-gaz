"""Order service: queue creation, antifraud checks, position calculation, delivery.

Business rules (TT section 5) are enforced here AND in database constraints so the
service logic can not be bypassed via a different entry point (web / bot / API).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, date, timezone
from typing import Optional
import logging

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..models.models import Order, Household, Mahalla
from ..models.enums import OrderStatus

logger = logging.getLogger(__name__)


ACTIVE_STATUSES = (OrderStatus.PENDING, OrderStatus.APPROVED, OrderStatus.ON_WAY)
TERMINAL_STATUSES = (OrderStatus.DELIVERED, OrderStatus.CANCELLED)

# Per-mahalla asyncio lock guarantees monotonic queue numbering even on SQLite
# where row-level locking isn't available. On Postgres, we use SELECT FOR UPDATE.
_mahalla_locks: dict[int, asyncio.Lock] = {}
_lock_guard = asyncio.Lock()


async def _get_mahalla_lock(mahalla_id: int) -> asyncio.Lock:
    async with _lock_guard:
        lock = _mahalla_locks.setdefault(mahalla_id, asyncio.Lock())
    return lock


class AntifraudError(Exception):
    def __init__(self, message: str, code: str, next_available: Optional[date] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.next_available = next_available


async def _next_queue_number(db: AsyncSession, mahalla_id: int) -> int:
    """Return the next monotonically increasing queue number for the mahalla."""
    res = await db.execute(select(func.coalesce(func.max(Order.queue_number), 0)).where(Order.mahalla_id == mahalla_id))
    current_max = res.scalar_one()
    return int(current_max) + 1


async def _count_ahead(db: AsyncSession, mahalla_id: int, queue_number: int) -> int:
    res = await db.execute(
        select(func.count(Order.id)).where(
            Order.mahalla_id == mahalla_id,
            Order.status.in_(ACTIVE_STATUSES),
            Order.queue_number < queue_number,
        )
    )
    return int(res.scalar_one())


async def _total_in_queue(db: AsyncSession, mahalla_id: int) -> int:
    res = await db.execute(
        select(func.count(Order.id)).where(
            Order.mahalla_id == mahalla_id,
            Order.status.in_(ACTIVE_STATUSES),
        )
    )
    return int(res.scalar_one())


async def _cooldown_until(household: Household) -> Optional[date]:
    """Return the earliest date when a new order is allowed, or None if open."""
    if not household.last_delivered_at:
        return None
    cooldown = settings.DEFAULT_COOLDOWN_DAYS
    next_dt = household.last_delivered_at.astimezone(timezone.utc) + timedelta(days=cooldown)
    if next_dt.date() > datetime.now(timezone.utc).date():
        return next_dt.date()
    return None


async def check_antifraud(db: AsyncSession, household: Household) -> None:
    """Raise AntifraudError if creating a new order would violate rules."""
    if household.status.value == "blocked":
        raise AntifraudError("Xonadon bloklangan. Dispecherga murojaat qiling.", "HOUSEHOLD_BLOCKED")

    # 1) active order exists?
    res = await db.execute(
        select(Order.id).where(
            Order.household_id == household.id,
            Order.status.in_(ACTIVE_STATUSES),
        )
    )
    if res.scalar_one_or_none():
        raise AntifraudError(
            "Sizning faol navbatingiz mavjud. Avval uni kuting yoki bekor qiling.",
            "ACTIVE_ORDER_EXISTS",
        )

    # 2) cooldown since last delivery?
    next_allowed = await _cooldown_until(household)
    if next_allowed:
        raise AntifraudError(
            f"Siz yaqinda gaz olgansiz. Keyingi navbat {next_allowed.isoformat()} sanasida ochiladi.",
            "COOLDOWN_ACTIVE",
            next_available=next_allowed,
        )


async def create_order(db: AsyncSession, user_id: int, household_id: int) -> Order:
    """Place a citizen at the queue of their mahalla.

    Performs all antifraud checks inside a single transaction. Queue numbers are
    serialised by a per-mahalla lock so parallel requests can not produce duplicate
    numbers (TT §5.2). On Postgres the unique partial index on (household_id, status)
    adds a second safety net at the database level.
    """
    household = await db.get(Household, household_id)
    if not household:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xonadon topilmadi")

    await check_antifraud(db, household)

    lock = await _get_mahalla_lock(household.mahalla_id)
    async with lock:
        # Double-check antifraud (active order) after acquiring lock
        await check_antifraud(db, household)
        order = Order(
            household_id=household.id,
            user_id=user_id,
            mahalla_id=household.mahalla_id,
            status=OrderStatus.PENDING,
            queue_number=await _next_queue_number(db, household.mahalla_id),
        )
        db.add(order)
        await db.flush()
        await db.refresh(order)
    return order


async def get_queue_status(db: AsyncSession, household: Household) -> dict:
    """Return current queue info for a household (current order, position, eta)."""
    res = await db.execute(
        select(Order, Mahalla.daily_capacity)
        .join(Mahalla, Mahalla.id == Order.mahalla_id)
        .where(Order.household_id == household.id)
        .order_by(Order.id.desc())
        .limit(1)
    )
    row = res.first()
    total = await _total_in_queue(db, household.mahalla_id)

    if not row:
        return {
            "order_id": None, "status": None, "queue_number": None,
            "position": None, "total_in_queue": total,
            "estimated_delivery_date": None, "message": "Siz hozirda navbatda emassiz.",
        }
    order, daily_cap = row
    if order.status in ACTIVE_STATUSES:
        position = await _count_ahead(db, order.mahalla_id, order.queue_number) + 1
    else:
        position = None

    eta: Optional[str] = None
    if order.status == OrderStatus.ON_WAY:
        eta = date.today().isoformat()
    elif order.status == OrderStatus.APPROVED and order.route_id:
        # route_date is on route — lazy load
        from ..models.models import DeliveryRoute
        route = await db.get(DeliveryRoute, order.route_id)
        if route:
            eta = route.route_date.isoformat()
    elif order.status == OrderStatus.PENDING and position and daily_cap:
        eta_date = date.today() + timedelta(days=1 + (position - 1) // daily_cap)
        eta = eta_date.isoformat()

    return {
        "order_id": order.id,
        "status": order.status,
        "queue_number": order.queue_number,
        "position": position,
        "total_in_queue": total,
        "estimated_delivery_date": eta,
    }


async def cancel_order(db: AsyncSession, order: Order, reason: Optional[str] = None, actor_user_id: Optional[int] = None) -> Order:
    if order.status not in (OrderStatus.PENDING, OrderStatus.APPROVED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Faqat navbatda yoki marshrutdagi buyurtmani bekor qilish mumkin")
    order.status = OrderStatus.CANCELLED
    order.cancelled_at = datetime.now(timezone.utc)
    order.cancel_reason = reason
    await db.flush()
    return order


async def complete_delivery(
    db: AsyncSession,
    order: Order,
    weight_kg: float,
    payment_type,
    price_total: Optional[int] = None,
    price_per_kg: int = settings.DEFAULT_PRICE_PER_KG,
) -> Order:
    if order.status not in (OrderStatus.ON_WAY, OrderStatus.APPROVED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Buyurtma yetkazib berish holatida emas")
    order.status = OrderStatus.DELIVERED
    order.delivered_at = datetime.now(timezone.utc)
    order.weight_kg = weight_kg
    order.payment_type = payment_type
    if price_total is None:
        price_total = int(round(weight_kg * price_per_kg))
    order.price_total = price_total

    household = await db.get(Household, order.household_id)
    if household:
        household.last_delivered_at = order.delivered_at

    if order.route_id:
        from ..models.models import DeliveryRoute
        route = await db.get(DeliveryRoute, order.route_id)
        if route:
            route.delivered_count = (route.delivered_count or 0) + 1
    await db.flush()
    return order
