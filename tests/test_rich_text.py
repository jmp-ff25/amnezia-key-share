import html
import io
import re

from app.services.rich_text import clean_rich_text, render_rich_text
from tests.conftest import csrf


def test_group_and_key_instructions_render_separately(admin):
    response = admin.post(
        "/control-test/entries/new",
        data={
            "display_name": "Diana",
            "description": "<h2>О подключении</h2><p>Личный доступ.</p>",
            "key_name": ["Mac", "iPhone"],
            "vpn_key": ["vpn://mac-key", "vpn://iphone-key"],
            "key_comment": [
                "<p><strong>Для Mac:</strong> скачай Hiddify.</p>",
                "<ol><li>Установи Hiddify.</li><li>Скопируй ключ.</li></ol>",
            ],
            "csrf_token": csrf(admin, "/control-test/entries/new"),
        },
    )
    assert response.status_code == 200
    url = re.search(r'value="(http://testserver/access/[^\"]+)"', response.text).group(1)
    public = admin.get(url)
    assert "<h2>О подключении</h2>" in public.text
    assert "<strong>Для Mac:</strong>" in public.text
    assert "<ol><li>Установи Hiddify.</li>" in public.text
    assert public.text.index("Для Mac:") < public.text.index("vpn://mac-key")
    assert public.text.index("Скопируй ключ.") < public.text.index("vpn://iphone-key")


def test_rich_html_is_sanitized():
    value = (
        '<p onclick="alert(1)">Текст</p><script>alert(1)</script>'
        '<a href="javascript:alert(1)">ссылка</a>'
        '<img src="https://attacker.example/track.gif" onerror="alert(1)">'
        '<img src="/media/00000000000000000000000000000000.gif" alt="GIF">'
    )
    cleaned = clean_rich_text(value)
    assert "Текст" in cleaned
    assert "alert(1)" not in cleaned
    assert "javascript:" not in cleaned
    assert "attacker.example" not in cleaned
    assert 'src="/media/00000000000000000000000000000000.gif"' in cleaned
    styled = clean_rich_text(
        '<span style="color: #ff0000; font-family: Georgia; background-image: url(x)">цвет</span>'
    )
    assert "color:" in styled and "font-family:" in styled
    assert "background-image" not in styled


def test_legacy_plain_text_is_escaped_and_keeps_line_breaks():
    rendered = str(render_rich_text("О доступе\n<script>bad()</script>", "plain"))
    assert "О доступе<br>" in rendered
    assert "<script>" not in rendered
    assert html.escape("<script>bad()</script>") in rendered


def test_image_upload_is_private_to_admin_and_served_as_image(client, admin):
    gif = b"GIF89a" + bytes(32)
    no_csrf = admin.post(
        "/control-test/media",
        files={"image": ("picture.gif", io.BytesIO(gif), "image/gif")},
        data={"csrf_token": "wrong"},
    )
    assert no_csrf.status_code == 403
    response = admin.post(
        "/control-test/media",
        files={"image": ("picture.gif", io.BytesIO(gif), "image/gif")},
        data={"csrf_token": csrf(admin, "/control-test/entries/new")},
    )
    assert response.status_code == 200
    path = response.json()["url"]
    assert re.fullmatch(r"/media/[0-9a-f]{32}\.gif", path)
    served = client.get(path)
    assert served.content == gif
    assert served.headers["content-type"] == "image/gif"
    assert served.headers["x-content-type-options"] == "nosniff"
    assert client.get("/media/not-an-image.gif").status_code == 404
    client.cookies.clear()
    unauthorized = client.post(
        "/control-test/media",
        files={"image": ("picture.gif", io.BytesIO(gif), "image/gif")},
        data={"csrf_token": "wrong"},
    )
    assert unauthorized.status_code == 401


def test_image_upload_rejects_svg(admin):
    response = admin.post(
        "/control-test/media",
        files={"image": ("evil.svg", io.BytesIO(b"<svg></svg>"), "image/svg+xml")},
        data={"csrf_token": csrf(admin, "/control-test/entries/new")},
    )
    assert response.status_code == 415
