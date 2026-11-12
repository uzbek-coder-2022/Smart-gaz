# SmartGaz Backend

FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL backend for the SmartGaz gas-cylinder delivery platform.

## Tech stack

- Python 3.11+
- FastAPI (async)
- SQLAlchemy 2.0 (async) + Alembic migrations
- Pydantic v2
- PostgreSQL 16 (or SQLite for local dev)
- JWT auth (python-jose) + bcrypt
- Aiogram 3.x integration point (bot folder in progress)

## Quick start (local, SQLite)

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # uses SQLite by default
python seed.py              # create tables, admin, regions, sample driver
uvicorn app.main:app --reload --port 8000
```

Open docs: http://localhost:8000/docs

Seed credentials:
- Admin: +998900000001 / admin123
- Driver: +998900000002 / driver123

## Quick start (Postgres via Docker)

```bash
docker-compose up --build
```

This brings up Postgres + backend on port 8000 and runs the seed script automatically.

## Project layout

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py             # Auth/role dependencies
│   │   └── v1/                 # Versioned routes: auth, territory, households, orders, routes, tracking, admin
│   ├── core/
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── db.py               # Async engine + session
│   │   └── security.py         # Bcrypt + JWT
│   ├── models/
│   │   ├── enums.py            # Roles, statuses
│   │   └── models.py           # ORM entities (14 tables)
│   ├── schemas/                # Pydantic DTOs
│   ├── services/
│   │   ├── normalizer.py       # Address/phone normalization (antifraud)
│   │   ├── orders.py           # Queue + antifraud + delivery
│   │   ├── routes.py           # Route planning & lifecycle
│   │   └── tracking.py         # GPS tracking
│   └── main.py                 # FastAPI app factory
├── alembic/                    # Migrations
├── seed.py                     # Initial data loader
├── requirements.txt
├── Dockerfile
└── README.md
```

## Implemented business rules (TT §5)

- ✅ Address normalization → stable `household_key` (§5.1)
- ✅ Active order uniqueness + cooldown (N=20 days) antifraud (§5.2)
- ✅ Per-mahalla FIFO queue with monotonically increasing queue numbers (§5.3)
- ✅ Estimated delivery date formula: today + 1 + ⌊(position-1)/daily_capacity⌋ (§5.3)
- ✅ Route creation auto-pulls top-N pending orders; respects capacity (§5.4)
- ✅ Route start → orders move ON_WAY; route finish → undelivered orders return to PENDING preserving queue numbers (§5.4)
- ✅ Order state machine: PENDING → APPROVED → ON_WAY → DELIVERED; CANCELLED terminal (§5.5)
- ✅ Price auto-calc from kg × price_per_kg (§5.6)
- ✅ RBAC: citizen, driver, dispatcher, MFY, operator_head, inspector, admin (§3)
- ✅ GPS driver location every 30 s (§4.4)
- ✅ Citizen sees incoming driver location when ON_WAY (§4.2)
- ✅ Dispatcher stats endpoint (§4.5, §4.7)
- ✅ Audit-ready status changes; audit_logs table reserved (§6.1)

## API surface (v1)

| Method | Path | Description |
| --- | --- | --- |
| POST | /api/v1/auth/register | Register user (phone/password) |
| POST | /api/v1/auth/login | Obtain JWT |
| GET  | /api/v1/territory/regions | Region list (with districts) |
| GET  | /api/v1/territory/districts/{rid} | Districts in region |
| GET  | /api/v1/territory/mahallas/{did} | Mahallas in district |
| POST | /api/v1/households/ | Create (or attach to existing) household |
| GET  | /api/v1/households/me | Current user's household |
| POST | /api/v1/orders/create | Join queue (antifraud-checked) |
| GET  | /api/v1/orders/queue-status/me | Position + ETA |
| POST | /api/v1/orders/{id}/cancel | Cancel order |
| POST | /api/v1/orders/{id}/complete | Record delivery (driver/dispatcher) |
| POST | /api/v1/routes/admin | Dispatcher creates route |
| GET  | /api/v1/routes/today | Driver's today's route |
| POST | /api/v1/routes/{id}/start | Start route → ON_WAY |
| POST | /api/v1/routes/{id}/finish | Finish route |
| POST | /api/v1/tracking/update-location | Driver GPS update |
| GET  | /api/v1/tracking/driver/{id} | Last known driver location |
| GET  | /api/v1/tracking/me | Incoming driver for current user |
| GET  | /api/v1/admin/stats | Dashboard statistics |

Interactive Swagger docs: `/docs`, ReDoc: `/redoc`.

## Tests

Acceptance scenarios (TT §11.1 T1–T12) are covered by integration tests in `tests/`.

```bash
pytest
```
