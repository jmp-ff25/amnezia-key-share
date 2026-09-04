import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from app.models import AccessEntry, AccessKey
from app.repositories import AccessEntryRepository


class InvalidVpnKeyError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class KeyInput:
    display_name: str
    vpn_key: str


class AccessEntryService:
    def __init__(self, repository: AccessEntryRepository) -> None:
        self.repository = repository

    @staticmethod
    def token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def validate_key(vpn_key: str) -> str:
        clean = vpn_key.strip()
        if not clean.startswith("vpn://") or any(char.isspace() for char in clean):
            raise InvalidVpnKeyError("Ключ должен быть корректным URI, начинающимся с vpn://")
        return clean

    def validate_keys(self, keys: list[KeyInput]) -> list[AccessKey]:
        if not keys:
            raise InvalidVpnKeyError("Добавьте хотя бы один VPN-ключ")
        if len(keys) > 20:
            raise InvalidVpnKeyError("В одной группе может быть не более 20 ключей")
        result: list[AccessKey] = []
        for index, key in enumerate(keys):
            name = key.display_name.strip()
            if not name:
                raise InvalidVpnKeyError(f"Укажите название для ключа №{index + 1}")
            result.append(
                AccessKey(
                    display_name=name[:160],
                    vpn_key=self.validate_key(key.vpn_key),
                    sort_order=index,
                )
            )
        return result

    def create(
        self, display_name: str, description: str, keys: list[KeyInput]
    ) -> tuple[AccessEntry, str]:
        token = self.generate_token()
        entry = AccessEntry(
            display_name=display_name.strip(),
            description=description.strip() or None,
            public_token_hash=self.token_hash(token),
            public_token=token,
            keys=self.validate_keys(keys),
        )
        return self.repository.save(entry), token

    def update(
        self, entry: AccessEntry, display_name: str, description: str, keys: list[KeyInput]
    ) -> AccessEntry:
        entry.display_name = display_name.strip()
        entry.description = description.strip() or None
        entry.keys = self.validate_keys(keys)
        entry.updated_at = datetime.now(UTC)
        return self.repository.save(entry)

    def regenerate(self, entry: AccessEntry) -> str:
        token = self.generate_token()
        entry.public_token_hash = self.token_hash(token)
        entry.public_token = token
        entry.is_active = True
        self.repository.save(entry)
        return token

    def revoke(self, entry: AccessEntry) -> None:
        entry.public_token_hash = None
        entry.public_token = None
        entry.is_active = False
        self.repository.save(entry)

    def set_active(self, entry: AccessEntry, active: bool) -> None:
        entry.is_active = active
        self.repository.save(entry)
