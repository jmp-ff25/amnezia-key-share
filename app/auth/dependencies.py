from fastapi import Request


def require_admin(request: Request) -> bool:
    return request.session.get("authenticated") is True
