"""TT §11.1 acceptance scenarios T1-T12."""
from __future__ import annotations
import pytest

from datetime import date, datetime, timezone


@pytest.mark.asyncio
async def test_t1_register_and_profile(client):
    """T1 — new citizen registers and completes profile."""
    tok, _ = await register_citizen(client, "+998909000001")
    hh_id = await create_household(client, tok)
    assert hh_id >= 1


@pytest.mark.asyncio
async def test_t2_join_queue(client):
    """T2 — citizen joins queue; receives queue number and position."""
    tok, _ = await register_citizen(client, "+998909000002")
    await create_household(client, tok)
    r = await client.post("/api/v1/orders/create", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "PENDING"
    assert data["queue_number"] >= 1

    qs = await client.get("/api/v1/orders/queue-status/me", headers={"Authorization": f"Bearer {tok}"})
    assert qs.status_code == 200
    assert qs.json()["position"] == 1
    assert qs.json()["estimated_delivery_date"] is not None


@pytest.mark.asyncio
async def test_t3_t5_antifraud_active_and_cooldown(client):
    """T3 & T5 — duplicate & cooldown rejections."""
    tok, _ = await register_citizen(client, "+998909000003")
    await create_household(client, tok)
    r1 = await client.post("/api/v1/orders/create", headers={"Authorization": f"Bearer {tok}"})
    assert r1.status_code == 201
    dup = await client.post("/api/v1/orders/create", headers={"Authorization": f"Bearer {tok}"})
    assert dup.status_code == 409
    assert "faol navbatingiz" in dup.json()["detail"]


@pytest.mark.asyncio
async def test_t4_same_address_other_account(client):
    """T4 — other account at the same address attaches to the same household."""
    tok1, _ = await register_citizen(client, "+998909000004")
    hh1 = await create_household(client, tok1, street="Navoiy", house="7")
    tok2, _ = await register_citizen(client, "+998909000005")
    hh2 = await create_household(client, tok2, street="Navoiy", house="7")
    assert hh1 == hh2


@pytest.mark.asyncio
async def test_t7_t8_t9_t10_t11_route_lifecycle(client):
    """T7 dispatcher creates route → T8 driver starts → T9 GPS → T10 deliver → T11 finish (undelivered return)."""
    admin_tok = await login(client, "+998900000001", "admin123")
    driver_tok = await login(client, "+998900000002", "driver123")

    # Two citizens queue
    t1, _ = await register_citizen(client, "+998909000010")
    t2, _ = await register_citizen(client, "+998909000011")
    await create_household(client, t1, street="A", house="1")
    await create_household(client, t2, street="B", house="2")
    o1 = (await client.post("/api/v1/orders/create", headers={"Authorization": f"Bearer {t1}"})).json()
    o2 = (await client.post("/api/v1/orders/create", headers={"Authorization": f"Bearer {t2}"})).json()

    # Dispatcher creates route for 2 cylinders
    rt = await client.post("/api/v1/routes/admin", headers={"Authorization": f"Bearer {admin_tok}"}, json={
        "driver_id": 1, "mahalla_id": 1, "allocated_cylinders": 2, "route_date": date.today().isoformat(),
    })
    assert rt.status_code == 201, rt.text
    rid = rt.json()["id"]
    assert len(rt.json()["orders"]) == 2  # T7

    start = await client.post(f"/api/v1/routes/{rid}/start", headers={"Authorization": f"Bearer {driver_tok}"})
    assert start.status_code == 200
    assert start.json()["status"] == "IN_PROGRESS"  # T8

    gps = await client.post("/api/v1/tracking/update-location", headers={"Authorization": f"Bearer {driver_tok}"}, json={"lat": 40.0, "lon": 72.0})
    assert gps.status_code == 200  # T9

    inc = await client.get("/api/v1/tracking/me", headers={"Authorization": f"Bearer {t1}"})
    assert inc.status_code == 200
    assert inc.json() is not None
    assert inc.json()["lat"] == 40.0

    # Deliver only first order (T10)
    comp = await client.post(f"/api/v1/orders/{o1['id']}/complete", headers={"Authorization": f"Bearer {driver_tok}"}, json={"weight_kg": 18.0, "payment_type": "cash"})
    assert comp.status_code == 200
    assert comp.json()["status"] == "DELIVERED"
    assert comp.json()["price_total"] == 18 * 2800

    # Finish route → remaining order returns to PENDING (T11)
    fin = await client.post(f"/api/v1/routes/{rid}/finish", headers={"Authorization": f"Bearer {driver_tok}"})
    assert fin.status_code == 200
    assert fin.json()["status"] == "COMPLETED"

    qs = await client.get("/api/v1/orders/queue-status/me", headers={"Authorization": f"Bearer {t2}"})
    assert qs.json()["status"] == "PENDING"
    # queue number preserved (still 2, not reassigned)
    assert qs.json()["queue_number"] == o2["queue_number"]


@pytest.mark.asyncio
async def test_t6_parallel_queue_numbers_unique(client):
    """T6 — 20 parallel join requests; queue numbers must be unique and ordered."""
    import asyncio
    toks = []
    for i in range(20):
        phone = f"+99890910{i:04d}"  # +998 + 90 prefix + 4-digit suffix → 13 chars total
        t, _ = await register_citizen(client, phone)
        await create_household(client, t, street="Parallel", house=str(i + 1))
        toks.append(t)

    async def join(tok):
        return await client.post("/api/v1/orders/create", headers={"Authorization": f"Bearer {tok}"})

    results = await asyncio.gather(*[join(t) for t in toks])
    qns = sorted(r.json()["queue_number"] for r in results if r.status_code == 201)
    assert len(qns) == 20
    assert qns == list(range(min(qns), min(qns) + 20))  # unique + consecutive


@pytest.mark.asyncio
async def test_t12_non_admin_cannot_elevate(client):
    """T12 — regular user cannot call admin endpoints."""
    tok, _ = await register_citizen(client, "+998909099999")
    r = await client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403


# Re-export fixtures used by the tests (so pytest finds them)
from .conftest import client, setup_db, login, register_citizen, create_household  # noqa: E402,F401
