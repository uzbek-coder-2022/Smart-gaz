# SmartGaz

**Qishloq hududlarida aholini suyultirilgan gaz ballonlari bilan ta'minlash uchun "SmartGaz" web-platformasi va Telegram-boti.**

Maishiy gaz ballonlarini elektron navbat asosida yetkazib berish, antifrod nazorati va gaz tashuvchi transportni GPS orqali monitoring qilish tizimi.

To'liq texnik topshiriq (TT): `SmartGaz_Texnik_Topshiriq.md`.

## Holat: 1-bosqich — Backend asosi (FastAPI)

✅ Bajarilgan (ushbu bosqich):

- **Python 3.11 + FastAPI + SQLAlchemy 2.0 (async)** backend skeleti
- **14 ta ma'lumotlar jadvali**: users, households, regions, districts, mahallas, operators, drivers, driver_locations, orders, delivery_routes, payments, complaints, notifications, settings, audit_logs
- **RBAC rollari**: citizen, driver, dispatcher, mfy, operator_head, inspector, admin
- **JWT autentifikatsiya** (bcrypt parol xeshlash)
- **Hudud spravochniklari** (14 viloyat + tuman/mahalla)
- **Manzil normalizatsiyasi** (antifrod uchun yagona household_key)
- **Elektron navbat (FIFO)**:
  - Har bir mahalla uchun alohida, monoton o'sib boruvchi navbat raqamlari
  - Parallel so'rovlar uchun per-mahalla lock (TT §5.2 T6 testi o'tadi)
  - O'rin va taxminiy yetkazish sanasini hisoblash (1 + ⌊(pos-1)/daily_cap⌋)
- **Antifrod qoidalari** (TT §5.2):
  - Faol buyurtma borida yangisini rad etish
  - 20 kunlik kooldown (sozlanadi), keyingi ruxsat sanasini ko'rsatish
  - Bir xonadonga turli akkauntlardan navbat ololmaslik (household_key orqali)
- **Marshrut lifecycle** (TT §5.4-5.5):
  - Dispecher marshrut yaratadi → FIFO bo'yicha N ta buyurtma APPROVED ga o'tadi
  - Haydovchi boshlaydi → ON_WAY, avto-xabarnoma uchun joy
  - Haydovchi yakunlaydi → topshirilmaganlar PENDING ga qaytadi (navbat raqami saqlanadi)
- **GPS tracking** (30 soniyada nuqta yozish, haydovchi lokatsiyasi, fuqaroga kelayotgan mashina)
- **Yetkazishni qayd etish** (og'irlik, to'lov turi, narx avto-hisob)
- **Admin/dispecher dashboard statistikasi**
- **Alembic migratsiyalari** konfiguratsiyasi
- **Docker + docker-compose** (Postgres 16 + backend)
- **7 ta integratsion test** (TT §11.1 T1–T12 ssenariylari)
- **Swagger/OpenAPI hujjati** avtomatik: `/docs`

## Tez ishga tushirish (lokal)

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python seed.py              # jadvallar, admin, viloyatlar, namunaviy haydovchi
uvicorn app.main:app --reload --port 8000
```

Docs: http://localhost:8000/docs  
Test akkauntlar:
- Admin: `+998900000001` / `admin123`
- Haydovchi: `+998900000002` / `driver123`

### Docker orqali (PostgreSQL + backend)

```bash
docker-compose up --build
```

### Testlar

```bash
cd backend && . .venv/bin/activate && pytest
```

## Loyihaning tuzilishi

```
Smart-gaz/
├── backend/                    # FastAPI backend (joriy bosqich)
│   ├── app/
│   │   ├── api/v1/             # REST endpoints: auth, territory, households, orders, routes, tracking, admin
│   │   ├── core/               # config, db, security
│   │   ├── models/             # SQLAlchemy ORM (15 ta jadval)
│   │   ├── schemas/            # Pydantic DTOlar
│   │   ├── services/           # biznes-logika: orders, routes, tracking, normalizer
│   │   └── main.py             # FastAPI ilovasi
│   ├── alembic/                # migratsiyalar
│   ├── tests/                  # qabul testlari (TT §11.1)
│   ├── seed.py                 # boshlang'ich ma'lumotlar
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
└── SmartGaz_Texnik_Topshiriq.md
```

## Keyingi bosqichlar (navbat bo'yicha)

Reja bo'yicha quyidagilar amalga oshiriladi:

1. **2-bosqich (davomi)**:
   - Telegram-bot (Aiogram 3.x) — FSM ro'yxatdan o'tish, navbat, holat, lokatsiya
   - Web-frontend (ommaviy qism + fuqaro kabineti, mobile-first)
2. **3-bosqich**: Haydovchi PWA (mobil web), oflayn GPS bufer, xarita (Leaflet/Yandex/OpenStreetMap)
3. **4-bosqich**: Integratsiyalar — SMS (Eskiz/PlayMobile), OneID, E-gaz, to'lov (Click/Payme)
4. **5-bosqich**: Dispecher paneli (kengaytirilgan), MFY kabineti, Excel/PDF hisobotlar, audit
5. **6-bosqich**: Xavfsizlik va yuklama testlari
6. **7-bosqich**: Pilot va joriy etish

## Texnik stack

| Qatlam | Texnologiya |
| --- | --- |
| Backend | Python 3.11, FastAPI (async), SQLAlchemy 2.0 (async), Pydantic v2 |
| Ma'lumotlar bazasi | PostgreSQL 16 (ishlab chiqish) / SQLite (lokal dev) |
| Autentifikatsiya | JWT + bcrypt; keyinchalik SMS OTP va OneID (OAuth2/OIDC) |
| Telegram-bot | Aiogram 3.x (keyingi bosqich) |
| Migratsiyalar | Alembic |
| Konteynerlashtirish | Docker + docker-compose |
| Testlar | pytest + pytest-asyncio + httpx |
