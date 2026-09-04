import os

os.environ.update(
    {
        "APP_SECRET_KEY": "test-secret-key-that-is-at-least-32-bytes",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PATH": "/control-test",
        "ADMIN_PASSWORD_HASH": "$argon2id$v=19$m=65536,t=3,p=4$F96R/hhDS8ox+elpalLE8Q$rPymbemA+YOxdTgYsaz7BTDF81xvm1Ih5hjN8hy0Hn4",
        "DATABASE_URL": "sqlite:///./test-keyport.db",
        "BASE_URL": "http://testserver",
        "ENVIRONMENT": "test",
        "TRUSTED_HOSTS": "testserver,localhost,127.0.0.1",
    }
)

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine
from app.main import app


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value


def csrf(client: TestClient, path: str = "/control-test/login") -> str:
    import re

    response = client.get(path)
    return re.search(r'name="csrf_token" value="([^"]+)"', response.text).group(1)


@pytest.fixture
def admin(client):
    token = csrf(client)
    response = client.post(
        "/control-test/login",
        data={"username": "admin", "password": "correct horse battery staple", "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return client
