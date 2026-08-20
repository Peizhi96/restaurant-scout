"""Add AI analysis and email notification audit records.

Revision ID: 20260820_0008
Revises: 20260819_0007
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_0008"
down_revision: str | None = "20260819_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    ai_recommendation = sa.Enum(
        "STRONG_CANDIDATE",
        "REVIEW",
        "PASS",
        "INSUFFICIENT_DATA",
        name="ai_recommendation",
        native_enum=False,
        create_constraint=True,
        length=32,
    )
    notification_priority = sa.Enum(
        "NORMAL",
        "HIGH",
        name="notification_priority",
        native_enum=False,
        create_constraint=True,
        length=16,
    )
    notification_status = sa.Enum(
        "PENDING",
        "SENT",
        "FAILED",
        name="notification_status",
        native_enum=False,
        create_constraint=True,
        length=16,
    )
    op.create_table(
        "listing_ai_analyses",
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("recommendation", ai_recommendation, nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("missing_information", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=40), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("listing_id"),
    )
    op.create_index(
        "ix_listing_ai_analyses_input_fingerprint",
        "listing_ai_analyses",
        ["input_fingerprint"],
    )
    op.create_index(
        "ix_listing_ai_analyses_recommendation",
        "listing_ai_analyses",
        ["recommendation"],
    )
    op.create_table(
        "email_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("trigger_type", sa.String(length=40), nullable=False),
        sa.Column("priority", notification_priority, nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=300), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("deduplication_key", sa.String(length=180), nullable=False),
        sa.Column(
            "status", notification_status, server_default="PENDING", nullable=False
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["listing_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "deduplication_key", name="uq_email_notification_deduplication_key"
        ),
    )
    op.create_index(
        "ix_email_notifications_created_at", "email_notifications", ["created_at"]
    )
    op.create_index("ix_email_notifications_event_id", "email_notifications", ["event_id"])
    op.create_index(
        "ix_email_notifications_listing_id", "email_notifications", ["listing_id"]
    )
    op.create_index("ix_email_notifications_status", "email_notifications", ["status"])
    op.create_index(
        "ix_email_notifications_trigger_type", "email_notifications", ["trigger_type"]
    )


def downgrade() -> None:
    op.drop_index("ix_email_notifications_trigger_type", table_name="email_notifications")
    op.drop_index("ix_email_notifications_status", table_name="email_notifications")
    op.drop_index("ix_email_notifications_listing_id", table_name="email_notifications")
    op.drop_index("ix_email_notifications_event_id", table_name="email_notifications")
    op.drop_index("ix_email_notifications_created_at", table_name="email_notifications")
    op.drop_table("email_notifications")
    op.drop_index(
        "ix_listing_ai_analyses_recommendation", table_name="listing_ai_analyses"
    )
    op.drop_index(
        "ix_listing_ai_analyses_input_fingerprint", table_name="listing_ai_analyses"
    )
    op.drop_table("listing_ai_analyses")
