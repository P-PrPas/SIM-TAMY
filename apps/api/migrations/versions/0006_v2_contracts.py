"""SIM-TAMY 2.0 shared schema (ADR-15): cohorts, assignments, family chat, debriefs, AI traces.

One additive migration for every 2.0 stream, so parallel work never forks the revision chain.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_TRACE = (
    "capability",
    "request_id",
    "prompt_version",
    "schema_version",
    "validation_status",
    "fallback_reason",
    "release_id",
)


def upgrade() -> None:
    op.add_column("classes", sa.Column("org_id", sa.Text()))
    op.create_table(
        "assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "class_id", sa.Uuid(), sa.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("story_id", sa.Text(), nullable=False),
        sa.Column("story_version", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
    )
    op.add_column(
        "family_rooms",
        sa.Column("assignment_id", sa.Uuid(), sa.ForeignKey("assignments.id", ondelete="SET NULL")),
    )
    for name in ("host_account_id", "partner_account_id", "release_id"):
        op.add_column("family_rooms", sa.Column(name, sa.Text()))
    op.create_table(
        "family_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "room_id",
            sa.Uuid(),
            sa.ForeignKey("family_rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("step_id", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("intent_code", sa.Text()),
        sa.Column("client_turn_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("room_id", "client_turn_id", name="uq_family_messages_client_turn_id"),
    )
    op.create_table(
        "family_debriefs",
        sa.Column(
            "room_id",
            sa.Uuid(),
            sa.ForeignKey("family_rooms.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("debrief_version", sa.Text(), primary_key=True),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    for name in _TRACE:
        op.add_column("llm_calls", sa.Column(name, sa.Text()))
    op.add_column("llm_calls", sa.Column("room_id", sa.Uuid()))


def downgrade() -> None:
    op.drop_column("llm_calls", "room_id")
    for name in reversed(_TRACE):
        op.drop_column("llm_calls", name)
    op.drop_table("family_debriefs")
    op.drop_table("family_messages")
    for name in ("release_id", "partner_account_id", "host_account_id", "assignment_id"):
        op.drop_column("family_rooms", name)
    op.drop_table("assignments")
    op.drop_column("classes", "org_id")
