"""Domain entities. All tables mirror the conceptual model described in section 8 of the TT."""
from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Date, Text, ForeignKey, Numeric,
    UniqueConstraint, Index, BigInteger, Enum as SAEnum, SmallInteger, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..core.db import Base
from .enums import (
    UserRole, HouseholdStatus, OrderStatus, RouteStatus,
    PaymentMethod, PaymentStatus, ComplaintStatus, NotificationChannel,
)


# ---------------------------------------------------------------------------
# Territory reference tables
# ---------------------------------------------------------------------------
class Region(Base):
    __tablename__ = "regions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_uz: Mapped[str] = mapped_column(String(120), nullable=False)
    name_uz_cyr: Mapped[Optional[str]] = mapped_column(String(120))
    name_ru: Mapped[Optional[str]] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)

    districts: Mapped[List["District"]] = relationship(back_populates="region", cascade="all, delete-orphan")


class District(Base):
    __tablename__ = "districts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id", ondelete="CASCADE"), index=True)
    name_uz: Mapped[str] = mapped_column(String(120), nullable=False)
    name_uz_cyr: Mapped[Optional[str]] = mapped_column(String(120))
    name_ru: Mapped[Optional[str]] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)

    region: Mapped[Region] = relationship(back_populates="districts")
    mahallas: Mapped[List["Mahalla"]] = relationship(back_populates="district", cascade="all, delete-orphan")


class Mahalla(Base):
    __tablename__ = "mahallas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), index=True)
    name_uz: Mapped[str] = mapped_column(String(160), nullable=False)
    name_uz_cyr: Mapped[Optional[str]] = mapped_column(String(160))
    name_ru: Mapped[Optional[str]] = mapped_column(String(160))
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    daily_capacity: Mapped[int] = mapped_column(Integer, default=20)

    district: Mapped[District] = relationship(back_populates="mahallas")


# ---------------------------------------------------------------------------
# Operators, users, drivers, households
# ---------------------------------------------------------------------------
class Operator(Base):
    __tablename__ = "operators"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    stir: Mapped[Optional[str]] = mapped_column(String(20))
    service_region_id: Mapped[Optional[int]] = mapped_column(ForeignKey("regions.id"))
    price_per_kg: Mapped[int] = mapped_column(Integer, default=2800)
    cooldown_days: Mapped[int] = mapped_column(Integer, default=20)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    """All actors: citizens, drivers, dispatchers, MFY, admins."""
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(120))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role_enum"), default=UserRole.CITIZEN, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    operator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("operators.id"))
    household_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("households.id", use_alter=True, name="fk_users_household_id"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    household: Mapped[Optional["Household"]] = relationship(foreign_keys=[household_id], back_populates="members")


class Household(Base):
    """A gas-consuming dwelling unit. Queue and antifraud work at this level."""
    __tablename__ = "households"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"), index=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), index=True)
    mahalla_id: Mapped[int] = mapped_column(ForeignKey("mahallas.id"), index=True)
    street: Mapped[str] = mapped_column(String(200), nullable=False)
    house_number: Mapped[str] = mapped_column(String(40), nullable=False)
    apartment: Mapped[Optional[str]] = mapped_column(String(20))
    household_key: Mapped[str] = mapped_column(String(500), unique=True, index=True, nullable=False)
    kadastr_number: Mapped[Optional[str]] = mapped_column(String(50))
    lpg_card_id: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    family_size: Mapped[Optional[int]] = mapped_column(SmallInteger)
    status: Mapped[HouseholdStatus] = mapped_column(
        SAEnum(HouseholdStatus, name="household_status_enum"),
        default=HouseholdStatus.UNVERIFIED, nullable=False,
    )
    verified_by_mfy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    in_social_register: Mapped[bool] = mapped_column(Boolean, default=False)
    last_delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    members: Mapped[List[User]] = relationship(
        back_populates="household", foreign_keys="User.household_id",
    )

    __table_args__ = (
        Index("ix_households_addr", "region_id", "district_id", "mahalla_id", "street", "house_number"),
    )


class Driver(Base):
    """Additional profile for users with role=DRIVER."""
    __tablename__ = "drivers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"), index=True)
    car_number: Mapped[str] = mapped_column(String(20))
    car_model: Mapped[Optional[str]] = mapped_column(String(100))
    capacity: Mapped[int] = mapped_column(Integer, default=40)  # cylinder count
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_lat: Mapped[Optional[float]] = mapped_column(Float)
    last_lon: Mapped[Optional[float]] = mapped_column(Float)
    last_speed: Mapped[Optional[float]] = mapped_column(Float)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()


class DriverLocation(Base):
    __tablename__ = "driver_locations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id", ondelete="CASCADE"), index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    speed: Mapped[Optional[float]] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


# ---------------------------------------------------------------------------
# Orders & routes
# ---------------------------------------------------------------------------
class DeliveryRoute(Base):
    __tablename__ = "delivery_routes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), index=True)
    mahalla_id: Mapped[int] = mapped_column(ForeignKey("mahallas.id"), index=True)
    allocated_cylinders: Mapped[int] = mapped_column(Integer, nullable=False)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[RouteStatus] = mapped_column(
        SAEnum(RouteStatus, name="route_status_enum"), default=RouteStatus.PLANNED, nullable=False,
    )
    route_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    route_id: Mapped[Optional[int]] = mapped_column(ForeignKey("delivery_routes.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status_enum"), default=OrderStatus.PENDING, nullable=False, index=True,
    )
    queue_number: Mapped[int] = mapped_column(Integer, nullable=False)
    mahalla_id: Mapped[int] = mapped_column(ForeignKey("mahallas.id"), index=True, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    on_way_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    weight_kg: Mapped[Optional[float]] = mapped_column(Float)
    price_total: Mapped[Optional[int]] = mapped_column(Integer)
    payment_type: Mapped[Optional[PaymentMethod]] = mapped_column(SAEnum(PaymentMethod, name="payment_method_enum"))
    not_home_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    cancel_reason: Mapped[Optional[str]] = mapped_column(String(400))

    household: Mapped[Household] = relationship()
    user: Mapped[User] = relationship()

    __table_args__ = (
        # Guarantee one active order per household (PENDING/APPROVED/ON_WAY).
        # DELIVERED/CANCELLED are terminal so they must not be covered by a unique partial index.
        Index(
            "ix_orders_active_household",
            household_id,
            unique=True,
            postgresql_where=status.in_([OrderStatus.PENDING, OrderStatus.APPROVED, OrderStatus.ON_WAY]),
            sqlite_where=None,  # SQLite partial indexes have limited support; enforced in service layer.
        ),
        Index("ix_orders_mahalla_status_qn", mahalla_id, status, queue_number),
    )


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(SAEnum(PaymentMethod, name="payment_method_enum"))
    provider_txn_id: Mapped[Optional[str]] = mapped_column(String(120))
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status_enum"), default=PaymentStatus.PENDING,
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Complaint(Base):
    __tablename__ = "complaints"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), index=True)
    type: Mapped[str] = mapped_column(String(60))
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[ComplaintStatus] = mapped_column(
        SAEnum(ComplaintStatus, name="complaint_status_enum"), default=ComplaintStatus.NEW,
    )
    answer: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    channel: Mapped[NotificationChannel] = mapped_column(SAEnum(NotificationChannel, name="notif_channel_enum"))
    event: Mapped[str] = mapped_column(String(80), index=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Setting(Base):
    """Key-value configuration (cooldown_days, daily_capacity, price_per_kg, etc.)."""
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(String(300))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(80))
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    reason: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
