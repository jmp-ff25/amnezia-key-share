# KeyPort

KeyPort — минимальный self-hosted сервис для публикации и мгновенного обновления ключей Amnezia VPN. Одна приватная ссылка может содержать как единственный именованный ключ, так и группу до 20 ключей для человека или семьи. Администратор управляет доступами в адаптивной панели, а пользователь копирует нужный актуальный ключ одним нажатием.

Группы автоматически отображаются сеткой на широком экране и одной колонкой на телефоне; пользователь может переключить сетку на компактный список. Публичную ссылку можно добавить на домашний экран как web app. На iPhone ссылку необходимо открыть именно в Safari, затем выбрать «Поделиться» → «На экран Домой»; встроенные браузеры мессенджеров могут не показывать эту команду. Manifest и service worker не кэшируют страницы или VPN-ключи.

## Архитектура

```text
Browser → Caddy (TLS, headers) → FastAPI/Jinja2 → SQLAlchemy → SQLite volume
```

FastAPI не публикуется на хосте. Caddy — единственная внешняя точка входа. Подробнее: [docs/architecture.md](docs/architecture.md).

## Локальный запуск

Локальный запуск требует `uv`. Установите его один раз от обычного пользователя (без `sudo`):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH="$HOME/.local/bin:$PATH" && uv --version
```

`uv` автоматически загрузит подходящий Python: проект требует Python 3.12+, отдельно
устанавливать его через системный пакетный менеджер не нужно.

```bash
cp .env.example .env
uv sync
uv run python -m app.cli hash-password
uv run python -m app.cli generate-admin-path
# вставьте hash и сгенерированный ADMIN_PATH в .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Откройте `<BASE_URL><ADMIN_PATH>/login`. Для локальной среды задайте `ENVIRONMENT=development`, `BASE_URL=http://localhost:8000`, `TRUSTED_HOSTS=localhost,127.0.0.1`.

## Развёртывание в Docker на Linux VPS

`uv` используется для локальной разработки и для безопасной генерации значений в `.env`.
Docker Compose нужен для production: он запускает приложение с отдельным SQLite volume,
Caddy с TLS и приватной сетью между Caddy и FastAPI. Не запускайте `uv run alembic` с
production `DATABASE_URL=sqlite:////data/keyport.db`: путь `/data` существует только
в контейнере и миграции выполняются автоматически при запуске `app`.

1. Установите Docker Engine с Compose plugin, `curl` и разрешите входящие TCP 80/443 в firewall.
2. Создайте DNS `A`/`AAAA` запись `keys.example.com`, направленную на VPS. Дождитесь распространения DNS.
3. Клонируйте репозиторий, установите `uv`, затем создайте production-конфигурацию:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   export PATH="$HOME/.local/bin:$PATH"
   cp .env.production.example .env
   uv sync
   openssl rand -hex 32
   ```

   Вставьте результат `openssl` в `APP_SECRET_KEY`, затем сгенерируйте пароль без его сохранения в plaintext:

   ```bash
   uv run python -m app.cli hash-password
   ```

   Вставьте выданный Argon2id hash в `ADMIN_PASSWORD_HASH`, обязательно заключив его в одинарные кавычки, чтобы Docker Compose не интерпретировал символы `$`:

   ```env
   ADMIN_PASSWORD_HASH='$argon2id$v=19$m=65536,t=3,p=4$...'
   ```

   Сгенерируйте непредсказуемый путь административной панели через `uv`:

   ```bash
   uv run python -m app.cli generate-admin-path
   ```

   Скопируйте результат целиком, включая начальный `/`:

   ```env
   ADMIN_PATH=/control-long-random-value
   ```

   Скрытый путь уменьшает автоматическое сканирование страницы входа, но не заменяет пароль, rate limiting, CSRF и session security. Не публикуйте его вместе с публичными ссылками.

5. Укажите один домен или публичный IP одинаково в `BASE_URL`, `TRUSTED_HOSTS` и `CADDY_DOMAIN`. Если домена нет, используйте публичный статический IPv4 VPS. `BASE_URL` содержит `https://`; в остальных двух переменных укажите только адрес, без схемы, пути и порта. Получить внешний IPv4 и сразу вывести три готовые строки можно командой:

   ```bash
   SERVER_IP="$(curl -4fsS https://api.ipify.org)" && printf 'BASE_URL=https://%s\nTRUSTED_HOSTS=%s\nCADDY_DOMAIN=%s\n' "$SERVER_IP" "$SERVER_IP" "$SERVER_IP"
   ```

   Скопируйте вывод в `.env`. Результат должен быть статическим публичным IP именно этого VPS.
6. Проверьте Caddyfile и Compose до запуска: `docker compose config --quiet` и `docker compose run --rm --no-deps caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile`.
7. Запустите `docker compose up -d --build`. Caddy автоматически получает и обновляет сертификат. Проверьте `docker compose ps`, `docker compose logs caddy`, `docker compose logs app` и `<BASE_URL>/health`.

Не публикуйте порт 8000 и не добавляйте его в `ports` сервиса `app`.

### Проверенный Caddyfile: домен или публичный IP

Репозиторий уже содержит этот Caddyfile; не подставляйте адрес вручную — он берётся из `CADDY_DOMAIN`:

```caddyfile
{
    # Нужен для клиентов, которые не отправляют SNI при обращении по IP.
    default_sni {$CADDY_DOMAIN}
}

{$CADDY_DOMAIN} {
    # Профиль shortlived обязателен для публичных IP-сертификатов Let's Encrypt
    # и также поддерживается для доменных сертификатов.
    tls {
        issuer acme https://acme-v02.api.letsencrypt.org/directory {
            profile shortlived
        }
    }

    encode zstd gzip
    reverse_proxy app:8000

    header {
        Strict-Transport-Security "max-age=31536000"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "no-referrer"
        Permissions-Policy "camera=(), microphone=(), geolocation=()"
        Content-Security-Policy "default-src 'self'; style-src 'self' https://cdn.jsdelivr.net; font-src 'self' https://cdn.jsdelivr.net; script-src 'self' https://cdn.jsdelivr.net; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        -Server
    }
}
```

### HTTPS по публичному IP без домена

Вместо примера `203.0.113.10` укажите реальный публичный статический IP VPS во всех настройках:

```env
BASE_URL=https://203.0.113.10
ENVIRONMENT=production
TRUSTED_HOSTS=203.0.113.10
CADDY_DOMAIN=203.0.113.10
```

Порты 80/443 должны быть доступны извне, а IP — статическим и действительно принадлежать VPS. Uvicorn остаётся только во внутренней Docker network. `default_sni` обязателен: без него часть браузеров получает `ERR_SSL_PROTOCOL_ERROR` при подключении по IP.

Для частного IP публичный Let’s Encrypt сертификат не выдаётся. Замените блок `tls { ... }` на `tls internal`; корневой сертификат Caddy потребуется установить как доверенный на каждом клиентском устройстве.

## Администратор

В MVP администратор один и задаётся `ADMIN_USERNAME` + `ADMIN_PASSWORD_HASH`. Адрес входа — `<BASE_URL><ADMIN_PATH>/login`. `create-admin` является безопасным интерактивным bootstrap: пароль читается без эха, проверяется и превращается в Argon2id hash. Изменение hash инвалидирует пароль, а активные cookie-сессии истекут максимум через 8 часов; для немедленной массовой инвалидации смените также `APP_SECRET_KEY` и перезапустите приложение.

## Резервное копирование и восстановление

SQLite использует Docker volume `keyport_data`. Делайте согласованную копию через SQLite backup API:

```bash
docker compose exec app python -c "import sqlite3; s=sqlite3.connect('/data/keyport.db'); d=sqlite3.connect('/data/keyport.backup.db'); s.backup(d); d.close(); s.close()"
docker compose cp app:/data/keyport.backup.db ./keyport-$(date +%F).db
```

Храните backup как секрет. Для восстановления остановите `app`, сохраните текущую БД, скопируйте проверенный backup в `/data/keyport.db`, затем запустите сервис и проверьте health/login. Не восстанавливайте поверх работающего процесса.

## Обновление

Сначала сделайте backup, затем:

```bash
git pull --ff-only
docker compose build --pull
docker compose up -d
docker compose ps
```

Контейнер выполняет `alembic upgrade head` перед стартом. Для отката приложения используйте прежний image/commit; downgrade схемы выполняйте только после проверки совместимости и с backup.

## Проверки качества

```bash
uv run pytest
uv run ruff check .
uv run mypy app
docker compose config --quiet
```

## Security considerations

- Публичный токен содержит 256 бит энтропии (`secrets.token_urlsafe(32)`), а lookup выполняется по SHA-256 hash. Для требуемого повторного копирования ссылки токен также хранится в SQLite. Это осознанный trade-off: утечка БД раскрывает ссылки, но эта же БД в MVP уже содержит более чувствительные VPN-ключи. Защищайте volume и backups; отзыв очищает и token, и hash. При добавлении encryption-at-rest следует шифровать оба поля.
- VPN-ключ сейчас хранится plaintext в SQLite: это упрощает надёжное восстановление MVP, но требует шифрования диска/volume, строгих прав и зашифрованных backup. Поле изолировано моделью и сервисным слоем, поэтому позже можно добавить envelope encryption (например, AES-GCM через KMS/secret key) без изменения маршрутов. При шифровании нужны ротация ключа, nonce на запись и тестируемая процедура восстановления.
- Публичные ответы имеют `Cache-Control: no-store`, `X-Robots-Tag` и robots meta. Ключ не передаётся в query string, JSON API или internal ID.
- Неизвестные адреса и невалидные публичные токены возвращают пустой `404` с `no-store/noindex`, без HTML, JSON и framework-details. Caddy обрывает соединения для стандартных `/admin` и `/admin/*` ещё до FastAPI; реальная панель существует только по случайному `ADMIN_PATH`.
- Cookie подписана, HttpOnly (Starlette), `SameSite=Lax`, а в production — `Secure`. Все изменяющие запросы защищены session-bound CSRF token.
- Login ограничен пятью ошибками на IP за пять минут в одном процессе. Текущий Compose запускает один Uvicorn worker. При горизонтальном масштабировании перенесите лимитер в Redis/Caddy/WAF.
- Caddy удаляет query из access log и не журналирует тела запросов. Не включайте debug/SQL echo и не подключайте body-capturing observability middleware.
- Bootstrap assets сейчас загружаются с jsDelivr и ограничены CSP/SRI. Для изолированной сети можно vendoring-ом положить точные версии в `static/vendor` и ужесточить CSP до `'self'`.

Никогда не коммитьте `.env`, production SQLite, backups или реальные VPN-ключи.
