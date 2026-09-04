import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import get_settings
from app.db.session import engine
from app.routes import admin_router, public_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if settings.is_production and not settings.admin_password_hash:
        raise RuntimeError("ADMIN_PASSWORD_HASH must be configured in production")
    yield
    engine.dispose()


app = FastAPI(title="KeyPort", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.hosts)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.app_secret_key,
    session_cookie="keyport_session",
    max_age=28800,
    same_site="lax",
    https_only=settings.is_production,
)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.include_router(admin_router)
app.include_router(public_router)


@app.get("/health", include_in_schema=False)
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            record.args = (
                tuple(
                    "[redacted]" if isinstance(value, str) and value.startswith("vpn://") else value
                    for value in record.args
                )
                if isinstance(record.args, tuple)
                else record.args
            )
        return True


for logger_name in ("uvicorn", "uvicorn.error", "app"):
    logging.getLogger(logger_name).addFilter(SensitiveDataFilter())
