"""Initial seed script: creates admin user, default operator, and a sample region/district/mahalla."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.core.db import AsyncSessionLocal, Base, engine
from app.core.security import hash_password
from app.models.models import Region, District, Mahalla, Operator, User, Driver, Setting
from app.models.enums import UserRole
from app.core.config import settings


UZBEKISTAN_REGIONS = [
    ("Toshkent shahri", "Тошкент шаҳри", "г. Ташкент", "TSH"),
    ("Toshkent viloyati", "Тошкент вилояти", "Ташкентская обл.", "TVL"),
    ("Andijon", "Андижон", "Андижан", "AND"),
    ("Buxoro", "Бухоро", "Бухара", "BUK"),
    ("Farg'ona", "Фарғона", "Фергана", "FAR"),
    ("Jizzax", "Жиззах", "Джизак", "JIZ"),
    ("Xorazm", "Хоразм", "Хорезм", "XOR"),
    ("Namangan", "Наманган", "Наманган", "NAM"),
    ("Navoiy", "Навоий", "Навои", "NAV"),
    ("Qashqadaryo", "Қашқадарё", "Кашкадарья", "QAS"),
    ("Qoraqalpog'iston", "Қорақалпоғистон", "Каракалпакстан", "KAR"),
    ("Samarqand", "Самарқанд", "Самарканд", "SAM"),
    ("Sirdaryo", "Сирдарё", "Сырдарья", "SIR"),
    ("Surxondaryo", "Сурхондарё", "Сурхандарья", "SUR"),
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # 1. Settings
        defaults = {
            "cooldown_days": str(settings.DEFAULT_COOLDOWN_DAYS),
            "price_per_kg": str(settings.DEFAULT_PRICE_PER_KG),
            "gps_interval_sec": str(settings.DEFAULT_GPS_INTERVAL_SEC),
        }
        for k, v in defaults.items():
            existing = await db.get(Setting, k)
            if not existing:
                db.add(Setting(key=k, value=v))

        # 2. Regions
        reg_objs = {}
        for name_uz, name_cyr, name_ru, code in UZBEKISTAN_REGIONS:
            existing = (await db.execute(select(Region).where(Region.code == code))).scalar_one_or_none()
            if not existing:
                r = Region(name_uz=name_uz, name_uz_cyr=name_cyr, name_ru=name_ru, code=code)
                db.add(r)
                reg_objs[code] = r
            else:
                reg_objs[code] = existing
        await db.flush()

        # 3. Sample districts/mahallas in Andijon to test with
        andijon = reg_objs["AND"]
        existing_dist = (await db.execute(select(District).where(District.code == "AND-01"))).scalar_one_or_none()
        if not existing_dist:
            asaka = District(region_id=andijon.id, name_uz="Asaka tumani", name_uz_cyr="Асака тумани", name_ru="Асакинский р-н", code="AND-01")
            db.add(asaka)
            await db.flush()
            db.add(Mahalla(district_id=asaka.id, name_uz="O'zbekiston mahallasi", name_uz_cyr="Ўзбекистон маҳалласи", code="AND-01-001", daily_capacity=30))
            db.add(Mahalla(district_id=asaka.id, name_uz="Navbahor mahallasi", name_uz_cyr="Навбаҳор маҳалласи", code="AND-01-002", daily_capacity=25))

        # 4. Default operator
        op = (await db.execute(select(Operator).where(Operator.name == "LPG-Trade Andijon"))).scalar_one_or_none()
        if not op:
            op = Operator(name="LPG-Trade Andijon", price_per_kg=settings.DEFAULT_PRICE_PER_KG, cooldown_days=settings.DEFAULT_COOLDOWN_DAYS)
            db.add(op)
            await db.flush()

        # 5. Admin user
        admin = (await db.execute(select(User).where(User.phone == "+998900000001"))).scalar_one_or_none()
        if not admin:
            admin = User(
                full_name="Admin",
                phone="+998900000001",
                role=UserRole.ADMIN,
                password_hash=hash_password("admin123"),
                operator_id=op.id,
            )
            db.add(admin)

        # 6. Sample driver
        driver_user = (await db.execute(select(User).where(User.phone == "+998900000002"))).scalar_one_or_none()
        if not driver_user:
            du = User(
                full_name="Haydovchi Botir",
                phone="+998900000002",
                role=UserRole.DRIVER,
                password_hash=hash_password("driver123"),
                operator_id=op.id,
            )
            db.add(du)
            await db.flush()
            db.add(Driver(user_id=du.id, operator_id=op.id, car_number="01A777AA", car_model="Isuzu", capacity=40))

        await db.commit()
        print("✅ Seed complete. Admin: +998900000001 / admin123 ; Driver: +998900000002 / driver123")


if __name__ == "__main__":
    asyncio.run(seed())
