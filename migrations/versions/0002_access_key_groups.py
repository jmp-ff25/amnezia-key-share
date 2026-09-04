"""Add named key groups while preserving all existing public links."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "access_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "access_entry_id",
            sa.Integer(),
            sa.ForeignKey("access_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("vpn_key", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_access_keys_access_entry_id", "access_keys", ["access_entry_id"])
    op.execute(
        sa.text(
            """
            INSERT INTO access_keys
                (access_entry_id, display_name, vpn_key, sort_order, created_at, updated_at)
            SELECT id, 'Основной ключ', vpn_key, 0, created_at, updated_at
            FROM access_entries
            """
        )
    )
    with op.batch_alter_table("access_entries") as batch:
        batch.drop_column("vpn_key")


def downgrade() -> None:
    with op.batch_alter_table("access_entries") as batch:
        batch.add_column(sa.Column("vpn_key", sa.Text(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE access_entries
            SET vpn_key = (
                SELECT access_keys.vpn_key FROM access_keys
                WHERE access_keys.access_entry_id = access_entries.id
                ORDER BY access_keys.sort_order, access_keys.id LIMIT 1
            )
            """
        )
    )
    with op.batch_alter_table("access_entries") as batch:
        batch.alter_column("vpn_key", nullable=False)
    op.drop_index("ix_access_keys_access_entry_id", table_name="access_keys")
    op.drop_table("access_keys")
