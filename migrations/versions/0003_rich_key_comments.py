"""Keep old descriptions as plain text and add formatted comments per key."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "access_entries",
        sa.Column("description_format", sa.String(8), nullable=False, server_default="plain"),
    )
    op.add_column("access_keys", sa.Column("comment_html", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("access_keys", "comment_html")
    op.drop_column("access_entries", "description_format")
