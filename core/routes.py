"""HTTP routes: pages, auth API, account settings and the admin panel."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select

from core import auth
from core.db import (
    PLAN_LIMITS, UsageEvent, User, get_session, record_usage,
    usage_this_month,
)

log = logging.getLogger(__name__)
router = APIRouter()
STATIC = Path("static")
# The React app in web/ builds to here. Every page route returns the same shell;
# react-router decides what to render, and the redirects below keep the
# server-side gating we had when each page was its own file.
SPA_SHELL = STATIC / "build" / "index.html"


def spa() -> FileResponse:
    if not SPA_SHELL.exists():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The frontend has not been built. Run `npm run build` in web/.",
        )
    # The shell names hashed asset files, so it must not be cached itself.
    return FileResponse(SPA_SHELL, headers={"Cache-Control": "no-store"})


# ── Session helpers ──────────────────────────────────────────────────────────

def current_user(session_cookie: str | None = Cookie(default=None, alias=auth.COOKIE_NAME)):
    """Resolve the signed cookie to a user, or None when not signed in."""
    claims = auth.read_claims(session_cookie or "")
    if not claims or not claims.get("sub"):
        return None
    with get_session() as s:
        user = s.get(User, claims["sub"])
        if user and user.is_active and auth.token_is_current(claims, user):
            s.expunge(user)
            return user
    return None


def require_user(user=Depends(current_user)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required.")
    return user


def require_admin(user=Depends(require_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins only.")
    return user


def _set_cookie(resp: Response, user_id: str) -> None:
    resp.set_cookie(
        auth.COOKIE_NAME,
        auth.make_token(user_id),
        httponly=True,                 # unreachable from page JavaScript
        samesite="lax",                # survives top-level navigation, blocks CSRF POSTs
        secure=False,                  # flipped to True behind TLS in production
        max_age=int(auth.TOKEN_TTL.total_seconds()),
        path="/",
    )


# ── Pages ────────────────────────────────────────────────────────────────────

@router.get("/", include_in_schema=False)
async def landing(user=Depends(current_user)):
    if user:
        return RedirectResponse("/app", status_code=302)
    return spa()


@router.get("/login", include_in_schema=False)
async def login_page(user=Depends(current_user)):
    if user:
        return RedirectResponse("/app", status_code=302)
    return spa()


@router.get("/register", include_in_schema=False)
async def register_page(user=Depends(current_user)):
    if user:
        return RedirectResponse("/app", status_code=302)
    return spa()


@router.get("/app", include_in_schema=False)
async def app_page(user=Depends(current_user)):
    if not user:
        return RedirectResponse("/login", status_code=302)
    return spa()


@router.get("/admin", include_in_schema=False)
async def admin_page(user=Depends(current_user)):
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.is_admin:
        return RedirectResponse("/app", status_code=302)
    return spa()


# ── Auth API ─────────────────────────────────────────────────────────────────

class RegisterBody(BaseModel):
    email: str
    password: str
    wake_name: str = Field(default="Saira")
    display_name: str = ""


class LoginBody(BaseModel):
    email: str
    password: str


@router.post("/api/register")
async def api_register(body: RegisterBody):
    with get_session() as s:
        try:
            user = auth.register(s, body.email, body.password,
                                 body.wake_name, body.display_name)
        except auth.AuthError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
        payload = {"id": user.id, "email": user.email, "wake_name": user.wake_name,
                   "role": user.role}
    resp = JSONResponse(payload)
    _set_cookie(resp, payload["id"])
    return resp


@router.post("/api/login")
async def api_login(body: LoginBody):
    with get_session() as s:
        try:
            user = auth.authenticate(s, body.email, body.password)
        except auth.AuthError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc))
        payload = {"id": user.id, "email": user.email, "wake_name": user.wake_name,
                   "role": user.role}
    resp = JSONResponse(payload)
    _set_cookie(resp, payload["id"])
    return resp


@router.post("/api/logout")
async def api_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(auth.COOKIE_NAME, path="/")
    return resp


# ── Account ──────────────────────────────────────────────────────────────────

@router.get("/api/me")
async def api_me(user=Depends(require_user)):
    with get_session() as s:
        used = usage_this_month(s, user.id)
    return {
        "id": user.id, "email": user.email, "display_name": user.display_name,
        "wake_name": user.wake_name, "role": user.role, "plan": user.plan,
        "used": used, "limit": user.monthly_limit,
        "remaining": max(0, user.monthly_limit - used),
    }


class PasswordBody(BaseModel):
    current_password: str
    new_password: str


@router.post("/api/me/password")
async def api_change_password(body: PasswordBody, response: Response,
                              user=Depends(require_user)):
    with get_session() as s:
        row = s.get(User, user.id)
        try:
            auth.change_password(s, row, body.current_password, body.new_password)
        except auth.AuthError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    # Every session issued before now is void, this one included — hand back a
    # fresh cookie so the person who just changed it is not signed out too.
    _set_cookie(response, user.id)
    return {"ok": True}


class WakeNameBody(BaseModel):
    wake_name: str


@router.post("/api/me/wake-name")
async def api_set_wake_name(body: WakeNameBody, user=Depends(require_user)):
    try:
        name = auth.validate_wake_name(body.wake_name)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    with get_session() as s:
        row = s.get(User, user.id)
        row.wake_name = name
        s.commit()
    # Refresh the live session's cached context so the change applies at once.
    from core.userdata import get_context
    get_context(user.id, name).wake_name = name
    return {"wake_name": name}


# ── Admin ────────────────────────────────────────────────────────────────────

@router.get("/api/admin/users")
async def api_admin_users(admin=Depends(require_admin)):
    with get_session() as s:
        users = s.scalars(select(User).order_by(desc(User.created_at))).all()
        rows = []
        for u in users:
            used = usage_this_month(s, u.id)
            total = s.scalar(
                select(func.coalesce(func.sum(UsageEvent.amount), 0))
                .where(UsageEvent.user_id == u.id)) or 0
            rows.append({
                "id": u.id, "email": u.email, "display_name": u.display_name,
                "wake_name": u.wake_name, "role": u.role, "plan": u.plan,
                "is_active": u.is_active,
                "used": used, "limit": u.monthly_limit, "total": int(total),
                "custom_limit": u.custom_limit,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_seen_at": u.last_seen_at.isoformat() if u.last_seen_at else None,
            })
        stats = {
            "total_users": len(users),
            "active_users": sum(1 for u in users if u.is_active),
            "admins": sum(1 for u in users if u.is_admin),
            "conversations_this_month": sum(r["used"] for r in rows),
        }
    return {"stats": stats, "plans": PLAN_LIMITS, "users": rows}


class AdminUpdateBody(BaseModel):
    plan: str | None = None
    custom_limit: int | None = None
    is_active: bool | None = None
    wake_name: str | None = None
    role: str | None = None
    clear_custom_limit: bool = False


@router.post("/api/admin/users/{user_id}")
async def api_admin_update(user_id: str, body: AdminUpdateBody,
                           admin=Depends(require_admin)):
    with get_session() as s:
        u = s.get(User, user_id)
        if not u:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No such user.")

        if body.plan is not None:
            if body.plan not in PLAN_LIMITS:
                raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                    f"Unknown plan. Options: {', '.join(PLAN_LIMITS)}")
            u.plan = body.plan
        if body.clear_custom_limit:
            u.custom_limit = None
        elif body.custom_limit is not None:
            if body.custom_limit < 0:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Limit cannot be negative.")
            u.custom_limit = body.custom_limit
        if body.wake_name is not None:
            try:
                u.wake_name = auth.validate_wake_name(body.wake_name)
            except ValueError as exc:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
        if body.is_active is not None:
            if u.id == admin.id and not body.is_active:
                raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                    "You cannot disable your own account.")
            u.is_active = body.is_active
        if body.role is not None:
            if body.role not in ("user", "admin"):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Role must be user or admin.")
            # Refuse to remove the last admin, which would lock everyone out.
            if u.is_admin and body.role != "admin":
                remaining = s.scalar(select(func.count()).select_from(User)
                                     .where(User.role == "admin", User.id != u.id))
                if not remaining:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                        "This is the only admin — promote someone else first.")
            u.role = body.role

        s.commit()
        out = {"id": u.id, "plan": u.plan, "custom_limit": u.custom_limit,
               "limit": u.monthly_limit, "is_active": u.is_active,
               "wake_name": u.wake_name, "role": u.role}

    from core.userdata import get_context, drop_context
    if body.is_active is False:
        drop_context(user_id)          # stop serving cached data to a disabled account
    elif body.wake_name is not None:
        get_context(user_id, out["wake_name"]).wake_name = out["wake_name"]
    return out
