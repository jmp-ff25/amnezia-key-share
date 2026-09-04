import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories import AccessEntryRepository
from app.routes.helpers import templates
from app.services import AccessEntryService

router = APIRouter(include_in_schema=False)
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{40,64}$")
NO_STORE = {"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"}


@router.get("/access/{token}", response_class=HTMLResponse)
def public_access(request: Request, token: str, db: Session = Depends(get_db)) -> Response:
    entry = None
    if TOKEN_RE.fullmatch(token):
        entry = AccessEntryRepository(db).by_token_hash(AccessEntryService.token_hash(token))
    if entry is None or not entry.is_active:
        return templates.TemplateResponse(
            request,
            "public/not_found.html",
            {"request": request},
            status_code=404,
            headers=NO_STORE,
        )
    return templates.TemplateResponse(
        request, "public/access.html", {"request": request, "entry": entry}, headers=NO_STORE
    )
