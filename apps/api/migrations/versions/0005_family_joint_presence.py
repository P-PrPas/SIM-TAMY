"""Joint votes, shared facts (event kind) and per-role presence for family rooms."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "family_events",
        sa.Column("kind", sa.Text(), server_default="decision", nullable=False),
    )
    op.add_column("family_rooms", sa.Column("host_seen_at", sa.TIMESTAMP(timezone=True)))
    op.add_column("family_rooms", sa.Column("partner_seen_at", sa.TIMESTAMP(timezone=True)))


def downgrade() -> None:
    op.drop_column("family_rooms", "partner_seen_at")
    op.drop_column("family_rooms", "host_seen_at")
    op.drop_column("family_events", "kind")
