"""Remove cohorts and assignments from active settings without deleting learning evidence."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("classes", "assignments"):
        op.add_column(table, sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    for table in ("assignments", "classes"):
        op.drop_column(table, "archived_at")
