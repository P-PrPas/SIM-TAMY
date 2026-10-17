"""Persistent two-player family rooms and append-only decisions."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "family_rooms",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("story", postgresql.JSONB(), nullable=False),
        sa.Column("host_role", sa.Text(), nullable=False),
        sa.Column("host_hash", sa.Text(), nullable=False),
        sa.Column("partner_hash", sa.Text()),
        sa.Column("invite_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "family_events",
        sa.Column(
            "room_id",
            sa.Uuid(),
            sa.ForeignKey("family_rooms.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("idx", sa.Integer(), primary_key=True),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("choice_id", sa.Text(), nullable=False),
        sa.Column("client_turn_id", sa.Uuid(), nullable=False),
        sa.UniqueConstraint("room_id", "client_turn_id", name="uq_family_events_client_turn_id"),
    )


def downgrade() -> None:
    op.drop_table("family_events")
    op.drop_table("family_rooms")
