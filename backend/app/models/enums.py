"""Shared enumerations used across models."""
from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    CITIZEN = "citizen"        # Fuqaro
    DRIVER = "driver"          # Haydovchi
    DISPATCHER = "dispatcher"  # Dispecher
    MFY = "mfy"                # MFY vakili
    OPERATOR_HEAD = "operator_head"
    INSPECTOR = "inspector"
    ADMIN = "admin"


class HouseholdStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    BLOCKED = "blocked"


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"        # Navbatda
    APPROVED = "APPROVED"      # Marshrutda
    ON_WAY = "ON_WAY"          # Yo'lda
    DELIVERED = "DELIVERED"    # Topshirildi
    CANCELLED = "CANCELLED"    # Bekor qilindi


class RouteStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    LPG_CARD = "lpg_card"
    ONLINE = "online"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class ComplaintStatus(str, enum.Enum):
    NEW = "new"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class NotificationChannel(str, enum.Enum):
    TELEGRAM = "telegram"
    SMS = "sms"
    IN_APP = "in_app"
