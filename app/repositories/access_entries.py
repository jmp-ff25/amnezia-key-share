from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import AccessEntry


class AccessEntryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, query: str = "") -> list[AccessEntry]:
        stmt = select(AccessEntry).order_by(AccessEntry.updated_at.desc())
        if query:
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(AccessEntry.display_name.ilike(pattern), AccessEntry.description.ilike(pattern))
            )
        return list(self.db.scalars(stmt))

    def count(self) -> tuple[int, int]:
        total = self.db.scalar(select(func.count()).select_from(AccessEntry)) or 0
        active = (
            self.db.scalar(
                select(func.count()).select_from(AccessEntry).where(AccessEntry.is_active.is_(True))
            )
            or 0
        )
        return total, active

    def get(self, entry_id: int) -> AccessEntry | None:
        return self.db.get(AccessEntry, entry_id)

    def by_token_hash(self, token_hash: str) -> AccessEntry | None:
        return self.db.scalar(
            select(AccessEntry).where(AccessEntry.public_token_hash == token_hash)
        )

    def save(self, entry: AccessEntry) -> AccessEntry:
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def delete(self, entry: AccessEntry) -> None:
        self.db.delete(entry)
        self.db.commit()
