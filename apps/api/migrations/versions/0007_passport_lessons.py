"""Learning Passport lesson completion per mock account and knowledge unit (LP-03)."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "passport_lessons",
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("unit_id", sa.Text(), nullable=False),
        sa.Column(
            "completed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("account_id", "unit_id", name="pk_passport_lessons"),
    )


def downgrade() -> None:
    op.drop_table("passport_lessons")
