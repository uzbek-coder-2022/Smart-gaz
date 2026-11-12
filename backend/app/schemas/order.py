from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import OrderStatus, PaymentMethod


class OrderCreateRequest(BaseModel):
    """Citizen joins the queue."""
    model_config = ConfigDict(from_attributes=True)


class OrderCreateByCitizen(BaseModel):
    """Used when an operator/dispatcher places an order for a citizen."""
    household_id: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    household_id: int
    user_id: int
    route_id: Optional[int] = None
    status: OrderStatus
    queue_number: int
    mahalla_id: int
    requested_at: datetime
    approved_at: Optional[datetime] = None
    on_way_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    weight_kg: Optional[float] = None
    price_total: Optional[int] = None
    payment_type: Optional[PaymentMethod] = None


class QueueStatus(BaseModel):
    order_id: Optional[int] = None
    status: Optional[OrderStatus] = None
    queue_number: Optional[int] = None
    position: Optional[int] = None
    total_in_queue: int
    estimated_delivery_date: Optional[str] = None
    message: Optional[str] = None


class CompleteDeliveryRequest(BaseModel):
    weight_kg: float = Field(..., gt=0, le=100)
    payment_type: PaymentMethod = PaymentMethod.CASH
    price_total: Optional[int] = None


class CancelRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=400)
