"""Household (xonadon) management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import get_current_user, require_roles
from ...core.db import get_db
from ...models.models import Household, User
from ...models.enums import UserRole, HouseholdStatus
from ...schemas.household import HouseholdCreate, HouseholdOut
from ...services.normalizer import make_household_key, normalize_phone

router = APIRouter(prefix="/households", tags=["households"])


@router.post("/", response_model=HouseholdOut, status_code=201)
async def create_household(
    payload: HouseholdCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a household and bind it to the current user."""
    if current_user.household_id:
        raise HTTPException(status_code=400, detail="Sizda allaqachon xonadon biriktirilgan")

    key = make_household_key(payload.region_id, payload.district_id, payload.mahalla_id, payload.street, payload.house_number, payload.apartment)
    existing = (await db.execute(select(Household).where(Household.household_key == key))).scalar_one_or_none()
    if existing:
        # Attach current user to existing household
        current_user.household_id = existing.id
        await db.commit()
        await db.refresh(existing)
        return HouseholdOut.model_validate(existing)

    household = Household(
        region_id=payload.region_id,
        district_id=payload.district_id,
        mahalla_id=payload.mahalla_id,
        street=payload.street.strip(),
        house_number=payload.house_number.strip(),
        apartment=payload.apartment,
        kadastr_number=payload.kadastr_number,
        lpg_card_id=payload.lpg_card_id,
        family_size=payload.family_size,
        household_key=key,
        status=HouseholdStatus.UNVERIFIED,
    )
    db.add(household)
    await db.flush()
    current_user.household_id = household.id
    await db.commit()
    await db.refresh(household)
    return HouseholdOut.model_validate(household)


@router.get("/me", response_model=HouseholdOut | None)
async def my_household(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.household_id:
        return None
    hh = await db.get(Household, current_user.household_id)
    return HouseholdOut.model_validate(hh) if hh else None
