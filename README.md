# KeyPort

KeyPort — минимальный self-hosted менеджер приватных ссылок для хранения и передачи именованных записей вида «ключ: значение». Одна приватная ссылка может содержать как единственную запись, так и группу до 20 записей для человека, семьи или команды. Администратор управляет доступами в адаптивной панели, а получатель копирует нужное актуальное значение одним нажатием.

Группы автоматически отображаются сеткой на широком экране и одной колонкой на телефоне; получатель может переключить сетку на компактный список. Публичную ссылку можно добавить на домашний экран как web app. На iPhone ссылку необходимо открыть именно в Safari, затем выбрать «Поделиться» → «На экран Домой»; встроенные браузеры мессенджеров могут не показывать эту команду. Manifest и service worker не кэшируют страницы или значения записей.

## Архитектура

```text
Browser → Caddy (TLS, headers) → FastAPI/Jinja2 → SQLAlchemy → SQLite volume
```

FastAPI не публикуется на хосте. Caddy — единственная внешняя точка входа. Подробнее: [docs/architecture.md](docs/architecture.md).

## Подготовка репозитория

Выполняйте команды ниже из каталога проекта. При новом клонировании:

```bash
git clone https://github.com/jmp-ff25/amnezia-key-share.git keyport
cd keyport
```

## Настройка `.env`

Этот блок выполняется до локального запуска или Docker-развёртывания.

1. Установите `uv` один раз от обычного пользователя, без `sudo`:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH="$HOME/.local/bin:$PATH" && uv --version
   ```

   `uv` автоматически загрузит подходящий Python: проект требует Python 3.12+, отдельно устанавливать его через системный пакетный менеджер не нужно.

2. Выберите один шаблон и создайте `.env`:

   ```bash
   # Локальный запуск
   cp .env.example .env

   # Или Docker-развёртывание на VPS
   cp .env.production.example .env
   ```

3. Для Docker-развёртывания сразу заполните публичный адрес в `.env`. Если есть домен, укажите его во всех трёх переменных:

   ```env
   BASE_URL=https://keys.example.com
   TRUSTED_HOSTS=keys.example.com
   CADDY_DOMAIN=keys.example.com
   ```

   Если домена нет, выполните на самом VPS команду: она получит публичный IPv4 и выведет три готовые строки.

   ```bash
   SERVER_IP="$(curl -4fsS https://api.ipify.org)" && printf 'BASE_URL=https://%s\nTRUSTED_HOSTS=%s\nCADDY_DOMAIN=%s\n' "$SERVER_IP" "$SERVER_IP" "$SERVER_IP"
   ```

   Скопируйте вывод в `.env`. В `BASE_URL` нужен `https://`; в `TRUSTED_HOSTS` и `CADDY_DOMAIN` укажите только домен или IP, без схемы, пути и порта. IPv4 должен быть статическим публичным адресом именно этого VPS. Для локального шаблона оставьте значения `localhost` как есть.

4. Сгенерируйте секрет и вставьте вывод в `APP_SECRET_KEY`:

   ```bash
   openssl rand -hex 32
   ```

5. Сгенерируйте hash пароля и путь администратора, затем вставьте оба результата в `.env`:

   ```bash
   uv run python -m app.cli hash-password
   uv run python -m app.cli generate-admin-path
   ```

   При Docker-развёртывании обрамите Argon2id hash в `ADMIN_PASSWORD_HASH` обычными одинарными кавычками `'...'`: Compose оставит значение и символы `$` неизменными. Не используйте обратные кавычки `` `...` `` — это Markdown-разметка, а не кавычки для `.env`.

   ```env
   ADMIN_PASSWORD_HASH='$argon2id$v=19$m=65536,t=3,p=4$...'
   ADMIN_PATH=/control-long-random-value
   ```

   Скрытый `ADMIN_PATH` снижает шум автоматического сканирования, но не заменяет пароль, rate limiting, CSRF и session security. Не публикуйте его вместе с приватными ссылками.

## Локальный запуск

Шаблон `.env.example` уже настроен для SQLite-файла в каталоге проекта.

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Откройте `<BASE_URL><ADMIN_PATH>/login`.

## Развёртывание в Docker на Linux VPS

Docker Compose нужен для production: он запускает приложение с отдельным SQLite volume, Caddy с TLS и приватной сетью между Caddy и FastAPI. Не запускайте `uv run alembic` с production `DATABASE_URL=sqlite:////data/keyport.db`: путь `/data` существует только в контейнере и миграции выполняются автоматически при запуске `app`.

1. Установите Docker Engine с Compose plugin и разрешите входящие TCP 80/443 в firewall.
2. Если используете домен, создайте DNS `A`/`AAAA` запись на VPS и дождитесь распространения DNS. Для варианта с IP убедитесь, что он статический и публичный.
3. После настройки `.env` проверьте Caddyfile и Compose:

   ```bash
   docker compose config --quiet
   docker compose run --rm --no-deps caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
   ```

4. Запустите сервис и проверьте его состояние:

   ```bash
   docker compose up -d --build
   docker compose ps
   docker compose logs caddy
   docker compose logs app
   ```

   Затем откройте `<BASE_URL>/health`. Не публикуйте порт 8000 и не добавляйте его в `ports` сервиса `app`.

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

- Публичный токен содержит 256 бит энтропии (`secrets.token_urlsafe(32)`), а lookup выполняется по SHA-256 hash. Для требуемого повторного копирования ссылки токен также хранится в SQLite. Это осознанный trade-off: утечка БД раскрывает ссылки, но эта же БД в MVP уже содержит более чувствительные значения записей. Защищайте volume и backups; отзыв очищает и token, и hash. При добавлении encryption-at-rest следует шифровать оба поля.
- Значение записи сейчас хранится plaintext в SQLite: это упрощает надёжное восстановление MVP, но требует шифрования диска/volume, строгих прав и зашифрованных backup. Поле изолировано моделью и сервисным слоем, поэтому позже можно добавить envelope encryption (например, AES-GCM через KMS/secret key) без изменения маршрутов. При шифровании нужны ротация ключа, nonce на запись и тестируемая процедура восстановления.
- Публичные ответы имеют `Cache-Control: no-store`, `X-Robots-Tag` и robots meta. Ключ не передаётся в query string, JSON API или internal ID.
- Неизвестные адреса и невалидные публичные токены возвращают пустой `404` с `no-store/noindex`, без HTML, JSON и framework-details. Caddy обрывает соединения для стандартных `/admin` и `/admin/*` ещё до FastAPI; реальная панель существует только по случайному `ADMIN_PATH`.
- Cookie подписана, HttpOnly (Starlette), `SameSite=Lax`, а в production — `Secure`. Все изменяющие запросы защищены session-bound CSRF token.
- Login ограничен пятью ошибками на IP за пять минут в одном процессе. Текущий Compose запускает один Uvicorn worker. При горизонтальном масштабировании перенесите лимитер в Redis/Caddy/WAF.
- Caddy удаляет query из access log и не журналирует тела запросов. Не включайте debug/SQL echo и не подключайте body-capturing observability middleware.
- Bootstrap assets сейчас загружаются с jsDelivr и ограничены CSP/SRI. Для изолированной сети можно vendoring-ом положить точные версии в `static/vendor` и ужесточить CSP до `'self'`.

Никогда не коммитьте `.env`, production SQLite, backups или реальные значения записей.
