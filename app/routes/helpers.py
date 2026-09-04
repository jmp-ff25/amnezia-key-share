from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.auth.security import ensure_csrf
from app.config import get_settings

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


def context(request: Request, **values: Any) -> dict[str, Any]:
    return {
        "request": request,
        "csrf_token": ensure_csrf(request),
        "admin_path": get_settings().admin_path,
        **values,
    }
