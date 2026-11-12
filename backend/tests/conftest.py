import os
import sys
import pytest
import pytest_asyncio

# Use a test database
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_smartgaz.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///./test_smartgaz.db"
os.environ["SECRET_KEY"] = "test-secret"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import Base, engine, AsyncSessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import models  # noqa: E402,F401
from app.core.security import hash_password  # noqa: E402
from app.models.models import (  # noqa: E402
    Region, District, Mahalla, Operator, User, Driver, Setting,
)
from app.models.enums import UserRole  # noqa: E402

from httpx import ASGITransport, AsyncClient  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        r = Region(name_uz="Andijon", code="AND")
        db.add(r)
        await db.flush()
        d = District(region_id=r.id, name_uz="Asaka tumani", code="AND-01")
        db.add(d)
        await db.flush()
        m = Mahalla(district_id=d.id, name_uz="O'zbekiston mahallasi", code="AND-01-001", daily_capacity=30)
        db.add(m)
        await db.flush()
        op = Operator(name="Test Operator", price_per_kg=2800, cooldown_days=20)
        db.add(op)
        await db.flush()
        admin = User(full_name="Admin", phone="+998900000001", role=UserRole.ADMIN, password_hash=hash_password("admin123"), operator_id=op.id)
        db.add(admin)
        await db.flush()
        du = User(full_name="Driver", phone="+998900000002", role=UserRole.DRIVER, password_hash=hash_password("driver123"), operator_id=op.id)
        db.add(du)
        await db.flush()
        db.add(Driver(user_id=du.id, operator_id=op.id, car_number="01A111AA", capacity=40))
        db.add(Setting(key="cooldown_days", value="20"))
        db.add(Setting(key="price_per_kg", value="2800"))
        db.add(Setting(key="gps_interval_sec", value="30"))
        await db.commit()
        yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def login(client, phone, password):
    r = await client.post("/api/v1/auth/login", json={"phone": phone, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def register_citizen(client, phone):
    r = await client.post("/api/v1/auth/register", json={"full_name": "Citizen", "phone": phone, "password": "pass1234", "role": "citizen"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"], r.json()["user"]["id"]


async def create_household(client, tok, mahalla_id=1, street="Mustakillik", house="1"):
    r = await client.post("/api/v1/households/", headers={"Authorization": f"Bearer {tok}"}, json={
        "region_id": 1, "district_id": 1, "mahalla_id": mahalla_id, "street": street, "house_number": house, "family_size": 4,
    })
    assert r.status_code == 201 or r.status_code == 200, r.text
    return r.json()["id"]
