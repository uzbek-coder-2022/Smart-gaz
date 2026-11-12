"""Frontend (Jinja2) page routes — public pages + role-based panels."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.db import get_db
from ..core.security import decode_access_token
from ..models.models import User
from ..models.enums import UserRole

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
TEMPLATES_DIR = BASE_DIR.parent / "backend" / "templates"
STATIC_DIR = BASE_DIR.parent / "backend" / "static"

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


_PUBLIC_PATHS = {"/", "/how", "/queue", "/login", "/register"}


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return request.cookies.get("sg_token")


async def _current_user_from_cookie_or_header(request: Request, db: AsyncSession):
    token = _extract_token(request)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    uid = payload.get("sub")
    if not uid:
        return None
    r = await db.execute(select(User).where(User.id == int(uid)))
    return r.scalar_one_or_none()


# Cookie-based login endpoint so SSR can identify the user on page reload
from fastapi.responses import JSONResponse
from ..core.security import verify_password
from pydantic import BaseModel


class LoginForm(BaseModel):
    phone: str
    password: str


@router.post("/auth/cookie-login")
async def cookie_login(payload: LoginForm, db: AsyncSession = Depends(get_db)):
    """Login that returns a short-lived HttpOnly cookie in addition to JSON.
    Used by the frontend JS after obtaining a token to keep server-rendered
    pages aware of the logged-in user across reloads.
    """
    r = await db.execute(select(User).where(User.phone == payload.phone))
    user = r.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Telefon yoki parol noto'g'ri")
    from ..core.security import create_access_token
    from ..schemas.user import UserOut
    token = create_access_token(user.id, extra={"role": user.role.value})
    resp = JSONResponse({"access_token": token, "user": UserOut.model_validate(user).model_dump()})
    resp.set_cookie(
        key="sg_token", value=token, httponly=True, samesite="lax",
        max_age=60 * 60 * 24, path="/",
    )
    return resp


@router.post("/auth/logout")
async def cookie_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("sg_token", path="/")
    return resp


def _page_context(request: Request, user: User | None):
    return {"request": request, "user": user}


# Mount static files — called from main.py
def mount_static(app):
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _current_user_from_cookie_or_header(request, db)
    return templates.TemplateResponse("pages/home.html", _page_context(request, user))


@router.get("/how", response_class=HTMLResponse)
async def how(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _current_user_from_cookie_or_header(request, db)
    return templates.TemplateResponse("pages/how.html", _page_context(request, user))


@router.get("/queue", response_class=HTMLResponse)
async def queue_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _current_user_from_cookie_or_header(request, db)
    return templates.TemplateResponse("pages/queue.html", _page_context(request, user))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _current_user_from_cookie_or_header(request, db)
    if user:
        return RedirectResponse(url="/cabinet", status_code=303)
    return templates.TemplateResponse("pages/login.html", _page_context(request, user))


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _current_user_from_cookie_or_header(request, db)
    if user:
        return RedirectResponse(url="/cabinet", status_code=303)
    return templates.TemplateResponse("pages/register.html", _page_context(request, user))


# ---------- Role-based panels ----------
ROLE_PANELS = {
    UserRole.CITIZEN: "/cabinet",
    UserRole.DRIVER: "/driver",
    UserRole.DISPATCHER: "/dispatcher",
    UserRole.MFY: "/mfy",
    UserRole.OPERATOR_HEAD: "/admin",
    UserRole.INSPECTOR: "/admin",
    UserRole.ADMIN: "/admin",
}


def _render_panel(request, user, template_name):
    return templates.TemplateResponse(template_name, {"request": request, "user": user})


@router.get("/cabinet", response_class=HTMLResponse)
async def cabinet(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _current_user_from_cookie_or_header(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/cabinet", status_code=303)
    return _render_panel(request, user, "pages/cabinet.html")


@router.get("/driver", response_class=HTMLResponse)
async def driver_panel(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _current_user_from_cookie_or_header(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/driver", status_code=303)
    if user.role not in (UserRole.DRIVER, UserRole.ADMIN, UserRole.DISPATCHER, UserRole.OPERATOR_HEAD):
        raise HTTPException(403, "Ruxsat yo'q")
    return _render_panel(request, user, "pages/driver.html")


@router.get("/dispatcher", response_class=HTMLResponse)
async def dispatcher_panel(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _current_user_from_cookie_or_header(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/dispatcher", status_code=303)
    if user.role not in (UserRole.DISPATCHER, UserRole.ADMIN, UserRole.OPERATOR_HEAD, UserRole.INSPECTOR):
        raise HTTPException(403, "Ruxsat yo'q")
    return _render_panel(request, user, "pages/dispatcher.html")


@router.get("/mfy", response_class=HTMLResponse)
async def mfy_panel(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _current_user_from_cookie_or_header(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/mfy", status_code=303)
    if user.role not in (UserRole.MFY, UserRole.ADMIN):
        raise HTTPException(403, "Ruxsat yo'q")
    return _render_panel(request, user, "pages/mfy.html")


@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _current_user_from_cookie_or_header(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/admin", status_code=303)
    if user.role not in (UserRole.ADMIN, UserRole.OPERATOR_HEAD, UserRole.INSPECTOR, UserRole.DISPATCHER):
        raise HTTPException(403, "Ruxsat yo'q")
    return _render_panel(request, user, "pages/admin.html")
