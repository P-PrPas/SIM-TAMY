"""Consented feedback per completed training session.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pilot_feedback",
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("usefulness", sa.Integer(), nullable=False),
        sa.Column("realism", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "role IN ('learner','instructor','practitioner')", name=op.f("ck_pilot_feedback_role")
        ),
        sa.CheckConstraint("usefulness BETWEEN 1 AND 5", name=op.f("ck_pilot_feedback_usefulness")),
        sa.CheckConstraint("realism BETWEEN 1 AND 5", name=op.f("ck_pilot_feedback_realism")),
    )


def downgrade() -> None:
    op.drop_table("pilot_feedback")
