import secrets
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.auth.rate_limit import login_limiter
from app.auth.security import validate_csrf, verify_password
from app.config import Settings, get_settings
from app.db import get_db
from app.models import AccessEntry
from app.repositories import AccessEntryRepository
from app.routes.helpers import context, templates
from app.services import AccessEntryService
from app.services.access_entries import InvalidVpnKeyError, KeyInput

settings = get_settings()
router = APIRouter(prefix=settings.admin_path, include_in_schema=False)


def admin_url(suffix: str = "") -> str:
    return f"{settings.admin_path}{suffix}"


def key_inputs(names: list[str], values: list[str]) -> list[KeyInput]:
    if len(names) != len(values):
        raise InvalidVpnKeyError("Некорректный набор ключей")
    return [KeyInput(name, value) for name, value in zip(names, values, strict=True)]


def redirect(path: str, message: str | None = None) -> RedirectResponse:
    target = path if message is None else f"{path}?message={quote(message)}"
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/login")
def login_page(request: Request, settings: Settings = Depends(get_settings)) -> Response:
    if require_admin(request):
        return redirect(admin_url())
    return templates.TemplateResponse(
        request,
        "admin/login.html",
        context(request, title="Вход", configured=bool(settings.admin_password_hash)),
    )


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    settings: Settings = Depends(get_settings),
) -> Response:
    validate_csrf(request, csrf_token)
    key = client_key(request)
    if not login_limiter.allowed(key):
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            context(request, title="Вход", error="Слишком много попыток. Повторите через 5 минут."),
            status_code=429,
        )
    password_valid = verify_password(settings.admin_password_hash, password)
    valid = secrets.compare_digest(username, settings.admin_username) and password_valid
    if not valid:
        login_limiter.fail(key)
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            context(request, title="Вход", error="Неверное имя пользователя или пароль."),
            status_code=401,
        )
    login_limiter.reset(key)
    request.session.clear()
    request.session["authenticated"] = True
    request.session["csrf"] = secrets.token_urlsafe(32)
    return redirect(admin_url())


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form(...)) -> Response:
    validate_csrf(request, csrf_token)
    request.session.clear()
    return redirect(admin_url("/login"))


def admin_guard(request: Request) -> Response | None:
    if not require_admin(request):
        return redirect(admin_url("/login"))
    return None


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db)) -> Response:
    if guard := admin_guard(request):
        return guard
    repo = AccessEntryRepository(db)
    total, active = repo.count()
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        context(request, title="Обзор", total=total, active=active, recent=repo.list()[:5]),
    )


@router.get("/entries")
def entries(request: Request, q: str = "", db: Session = Depends(get_db)) -> Response:
    if guard := admin_guard(request):
        return guard
    return templates.TemplateResponse(
        request,
        "admin/entries.html",
        context(request, title="Доступы", entries=AccessEntryRepository(db).list(q), q=q),
    )


@router.get("/entries/new")
def new_entry(request: Request) -> Response:
    if guard := admin_guard(request):
        return guard
    return templates.TemplateResponse(
        request,
        "admin/form.html",
        context(
            request,
            title="Новый доступ",
            entry=None,
            key_rows=[{"display_name": "Основной ключ", "vpn_key": ""}],
        ),
    )


@router.post("/entries/new")
def create_entry(
    request: Request,
    display_name: str = Form(...),
    description: str = Form(""),
    key_name: list[str] = Form(...),
    vpn_key: list[str] = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    if guard := admin_guard(request):
        return guard
    validate_csrf(request, csrf_token)
    try:
        entry, token = AccessEntryService(AccessEntryRepository(db)).create(
            display_name, description, key_inputs(key_name, vpn_key)
        )
    except InvalidVpnKeyError as exc:
        return templates.TemplateResponse(
            request,
            "admin/form.html",
            context(
                request,
                title="Новый доступ",
                entry=None,
                error=str(exc),
                values={
                    "display_name": display_name,
                    "description": description,
                },
                key_rows=[
                    {"display_name": name, "vpn_key": value}
                    for name, value in zip(key_name, vpn_key, strict=False)
                ],
            ),
            status_code=422,
        )
    request.session["fresh_url"] = f"{settings.base_url}/access/{token}"
    return redirect(
        admin_url(f"/entries/{entry.id}/edit"), "Доступ создан. Сохраните публичную ссылку."
    )


def get_entry_or_404(db: Session, entry_id: int) -> AccessEntry:
    entry = AccessEntryRepository(db).get(entry_id)
    if entry is None:
        raise HTTPException(404)
    return entry


@router.get("/entries/{entry_id}/edit")
def edit_entry(request: Request, entry_id: int, db: Session = Depends(get_db)) -> Response:
    if guard := admin_guard(request):
        return guard
    fresh_url = request.session.pop("fresh_url", None)
    entry = get_entry_or_404(db, entry_id)
    public_url = (
        f"{get_settings().base_url}/access/{entry.public_token}" if entry.public_token else None
    )
    return templates.TemplateResponse(
        request,
        "admin/form.html",
        context(
            request,
            title="Редактирование",
            entry=entry,
            fresh_url=fresh_url,
            public_url=public_url,
            key_rows=entry.keys,
        ),
    )


@router.post("/entries/{entry_id}/edit")
def update_entry(
    request: Request,
    entry_id: int,
    display_name: str = Form(...),
    description: str = Form(""),
    key_name: list[str] = Form(...),
    vpn_key: list[str] = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
) -> Response:
    if guard := admin_guard(request):
        return guard
    validate_csrf(request, csrf_token)
    entry = get_entry_or_404(db, entry_id)
    try:
        AccessEntryService(AccessEntryRepository(db)).update(
            entry, display_name, description, key_inputs(key_name, vpn_key)
        )
    except InvalidVpnKeyError as exc:
        return templates.TemplateResponse(
            request,
            "admin/form.html",
            context(
                request,
                title="Редактирование",
                entry=entry,
                error=str(exc),
                key_rows=[
                    {"display_name": name, "vpn_key": value}
                    for name, value in zip(key_name, vpn_key, strict=False)
                ],
            ),
            status_code=422,
        )
    return redirect(admin_url(f"/entries/{entry_id}/edit"), "Изменения сохранены.")


@router.post("/entries/{entry_id}/toggle")
def toggle(
    request: Request, entry_id: int, csrf_token: str = Form(...), db: Session = Depends(get_db)
) -> Response:
    if guard := admin_guard(request):
        return guard
    validate_csrf(request, csrf_token)
    entry = get_entry_or_404(db, entry_id)
    if entry.public_token_hash is None:
        return redirect(admin_url("/entries"), "Отозванную ссылку сначала нужно регенерировать.")
    AccessEntryService(AccessEntryRepository(db)).set_active(entry, not entry.is_active)
    return redirect(admin_url("/entries"), "Статус ссылки изменён.")


@router.post("/entries/{entry_id}/revoke")
def revoke(
    request: Request, entry_id: int, csrf_token: str = Form(...), db: Session = Depends(get_db)
) -> Response:
    if guard := admin_guard(request):
        return guard
    validate_csrf(request, csrf_token)
    AccessEntryService(AccessEntryRepository(db)).revoke(get_entry_or_404(db, entry_id))
    return redirect(admin_url("/entries"), "Ссылка безвозвратно отозвана.")


@router.post("/entries/{entry_id}/regenerate")
def regenerate(
    request: Request,
    entry_id: int,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    if guard := admin_guard(request):
        return guard
    validate_csrf(request, csrf_token)
    token = AccessEntryService(AccessEntryRepository(db)).regenerate(get_entry_or_404(db, entry_id))
    request.session["fresh_url"] = f"{settings.base_url}/access/{token}"
    return redirect(
        admin_url(f"/entries/{entry_id}/edit"),
        "Создана новая ссылка; старая больше не работает.",
    )


@router.post("/entries/{entry_id}/delete")
def delete(
    request: Request, entry_id: int, csrf_token: str = Form(...), db: Session = Depends(get_db)
) -> Response:
    if guard := admin_guard(request):
        return guard
    validate_csrf(request, csrf_token)
    repo = AccessEntryRepository(db)
    repo.delete(get_entry_or_404(db, entry_id))
    return redirect(admin_url("/entries"), "Запись удалена.")
