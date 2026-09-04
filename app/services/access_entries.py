import hashlib
import secrets

from app.models import AccessEntry
from app.repositories import AccessEntryRepository


class InvalidVpnKeyError(ValueError):
    pass


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

    def create(self, display_name: str, description: str, vpn_key: str) -> tuple[AccessEntry, str]:
        token = self.generate_token()
        entry = AccessEntry(
            display_name=display_name.strip(),
            description=description.strip() or None,
            vpn_key=self.validate_key(vpn_key),
            public_token_hash=self.token_hash(token),
            public_token=token,
        )
        return self.repository.save(entry), token

    def update(
        self, entry: AccessEntry, display_name: str, description: str, vpn_key: str
    ) -> AccessEntry:
        entry.display_name = display_name.strip()
        entry.description = description.strip() or None
        entry.vpn_key = self.validate_key(vpn_key)
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
