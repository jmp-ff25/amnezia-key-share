"""Initial schema."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "access_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("vpn_key", sa.Text(), nullable=False),
        sa.Column("public_token_hash", sa.String(64), nullable=True),
        sa.Column("public_token", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("public_token_hash"),
        sa.UniqueConstraint("public_token"),
    )
    op.create_index("ix_access_entries_display_name", "access_entries", ["display_name"])
    op.create_index(
        "ix_access_entries_public_token_hash", "access_entries", ["public_token_hash"], unique=True
    )
    op.create_index("ix_access_entries_is_active", "access_entries", ["is_active"])


def downgrade() -> None:
    op.drop_table("access_entries")
