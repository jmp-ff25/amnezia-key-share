import logging
import re

from tests.conftest import csrf


def test_login_and_session(client):
    assert client.get("/admin", follow_redirects=False).headers["location"] == "/admin/login"
    token = csrf(client)
    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "correct horse battery staple", "csrf_token": token},
    )
    assert response.status_code == 200 and "Обзор" in response.text


def test_wrong_login(client):
    response = client.post(
        "/admin/login", data={"username": "admin", "password": "wrong", "csrf_token": csrf(client)}
    )
    assert response.status_code == 401


def test_csrf_rejected(client):
    assert (
        client.post(
            "/admin/login", data={"username": "admin", "password": "x", "csrf_token": "bad"}
        ).status_code
        == 403
    )


def create_entry(admin):
    token = csrf(admin, "/admin/entries/new")
    response = admin.post(
        "/admin/entries/new",
        data={
            "display_name": "Alice",
            "description": "Phone",
            "vpn_key": "vpn://secret-key",
            "csrf_token": token,
        },
    )
    match = re.search(r'value="(http://testserver/access/[^\"]+)"', response.text)
    assert match
    return match.group(1)


def test_create_public_update_disable_and_invalid(admin):
    url = create_entry(admin)
    public = admin.get(url)
    assert public.status_code == 200 and "vpn://secret-key" in public.text
    assert public.headers["cache-control"] == "no-store"
    edit = admin.get("/admin/entries/1/edit")
    token = re.search(r'name="csrf_token" value="([^"]+)"', edit.text).group(1)
    admin.post(
        "/admin/entries/1/edit",
        data={
            "display_name": "Alice",
            "description": "Phone",
            "vpn_key": "vpn://new-key",
            "csrf_token": token,
        },
    )
    assert "vpn://new-key" in admin.get(url).text
    admin.post("/admin/entries/1/toggle", data={"csrf_token": token})
    assert admin.get(url).status_code == 404
    assert admin.get("/access/not-valid").status_code == 404


def test_regeneration_invalidates_old_token(admin):
    old = create_entry(admin)
    token = csrf(admin, "/admin/entries/1/edit")
    response = admin.post("/admin/entries/1/regenerate", data={"csrf_token": token})
    new = re.search(r'value="(http://testserver/access/[^\"]+)"', response.text).group(1)
    assert new != old and admin.get(old).status_code == 404 and admin.get(new).status_code == 200


def test_clipboard_fallback_present(admin):
    url = create_entry(admin)
    assert 'data-copy-target="vpn-key"' in admin.get(url).text
    script = admin.get("/static/js/app.js").text
    assert "navigator.clipboard" in script and "execCommand('copy')" in script


def test_vpn_key_not_logged(admin, caplog):
    caplog.set_level(logging.DEBUG)
    create_entry(admin)
    assert "vpn://secret-key" not in caplog.text
