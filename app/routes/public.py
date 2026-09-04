import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
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
        return Response(status_code=404, headers=NO_STORE)
    return templates.TemplateResponse(
        request,
        "public/access.html",
        {"request": request, "entry": entry, "public_token": token},
        headers=NO_STORE,
    )


@router.get("/access/{token}/manifest.webmanifest")
def access_manifest(token: str, db: Session = Depends(get_db)) -> Response:
    entry = None
    if TOKEN_RE.fullmatch(token):
        entry = AccessEntryRepository(db).by_token_hash(AccessEntryService.token_hash(token))
    if entry is None or not entry.is_active:
        return JSONResponse({"detail": "Not found"}, status_code=404, headers=NO_STORE)
    return JSONResponse(
        {
            "id": f"/access/{token}",
            "name": f"KeyPort · {entry.display_name}",
            "short_name": entry.display_name[:24],
            "start_url": f"/access/{token}",
            "scope": f"/access/{token}",
            "display": "standalone",
            "background_color": "#f7f8fc",
            "theme_color": "#635bff",
            "icons": [
                {
                    "src": "/static/icons/keyport-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable",
                }
            ],
        },
        media_type="application/manifest+json",
        headers=NO_STORE,
    )


@router.get("/service-worker.js", include_in_schema=False)
def service_worker() -> Response:
    return FileResponse(
        "app/static/js/service-worker.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-store", "Service-Worker-Allowed": "/"},
    )
