"""Add protected financial due diligence workflow.

Revision ID: 20260819_0004
Revises: 20260818_0003
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0004"
down_revision: str | None = "20260818_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    access_method = sa.Enum(
        "UNKNOWN",
        "EXTERNAL_NDA",
        "BROKER_CONTACT",
        name="due_diligence_access_method",
        native_enum=False,
        create_constraint=True,
        length=24,
    )
    access_status = sa.Enum(
        "UNKNOWN",
        "NDA_REQUIRED",
        "REQUESTED",
        "RECEIVED_UNVERIFIED",
        "VERIFIED",
        "NOT_PROVIDED",
        name="confidential_data_status",
        native_enum=False,
        create_constraint=True,
        length=32,
    )
    metric_type = sa.Enum(
        "GROSS_REVENUE",
        "CASH_FLOW",
        "SDE",
        "EBITDA",
        "INVENTORY_VALUE",
        "FFE_VALUE",
        name="financial_metric_type",
        native_enum=False,
        create_constraint=True,
        length=32,
    )
    verification_status = sa.Enum(
        "UNVERIFIED",
        "VERIFIED",
        name="financial_verification_status",
        native_enum=False,
        create_constraint=True,
        length=16,
    )
    event_type = sa.Enum(
        "PROFILE_CREATED",
        "PROFILE_UPDATED",
        "METRIC_CREATED",
        "METRIC_UPDATED",
        name="due_diligence_event_type",
        native_enum=False,
        create_constraint=True,
        length=24,
    )

    op.create_table(
        "listing_due_diligence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("access_method", access_method, server_default="UNKNOWN", nullable=False),
        sa.Column("access_status", access_status, server_default="UNKNOWN", nullable=False),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("broker_contact_name", sa.String(length=200), nullable=True),
        sa.Column("broker_contact_email", sa.String(length=320), nullable=True),
        sa.Column("broker_contact_phone", sa.String(length=50), nullable=True),
        sa.Column("inventory_included", sa.Boolean(), nullable=True),
        sa.Column("ffe_included", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("updated_by", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_listing_due_diligence_listing_id",
        "listing_due_diligence",
        ["listing_id"],
        unique=True,
    )
    op.create_index(
        "ix_listing_due_diligence_access_status",
        "listing_due_diligence",
        ["access_status"],
    )

    op.create_table(
        "financial_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("metric_type", metric_type, nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column(
            "verification_status",
            verification_status,
            server_default="UNVERIFIED",
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("updated_by", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_financial_metrics_listing_id", "financial_metrics", ["listing_id"])
    op.create_index("ix_financial_metrics_metric_type", "financial_metrics", ["metric_type"])
    op.create_index(
        "ix_financial_metrics_verification_status",
        "financial_metrics",
        ["verification_status"],
    )

    op.create_table(
        "due_diligence_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("actor", sa.String(length=200), nullable=False),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_due_diligence_events_listing_id", "due_diligence_events", ["listing_id"]
    )
    op.create_index(
        "ix_due_diligence_events_event_type", "due_diligence_events", ["event_type"]
    )
    op.create_index(
        "ix_due_diligence_events_created_at", "due_diligence_events", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_due_diligence_events_created_at", table_name="due_diligence_events")
    op.drop_index("ix_due_diligence_events_event_type", table_name="due_diligence_events")
    op.drop_index("ix_due_diligence_events_listing_id", table_name="due_diligence_events")
    op.drop_table("due_diligence_events")

    op.drop_index(
        "ix_financial_metrics_verification_status", table_name="financial_metrics"
    )
    op.drop_index("ix_financial_metrics_metric_type", table_name="financial_metrics")
    op.drop_index("ix_financial_metrics_listing_id", table_name="financial_metrics")
    op.drop_table("financial_metrics")

    op.drop_index(
        "ix_listing_due_diligence_access_status", table_name="listing_due_diligence"
    )
    op.drop_index("ix_listing_due_diligence_listing_id", table_name="listing_due_diligence")
    op.drop_table("listing_due_diligence")
