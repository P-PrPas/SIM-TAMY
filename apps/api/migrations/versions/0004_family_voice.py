"""Persist the validated grandmother wording with its append-only decision."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("family_events", sa.Column("reply_th", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("family_events", "reply_th")
