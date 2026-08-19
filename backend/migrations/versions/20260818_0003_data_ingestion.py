"""Add collection runs and persisted raw listings.

Revision ID: 20260818_0003
Revises: 20260818_0002
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_0003"
down_revision: str | None = "20260818_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    run_status = sa.Enum(
        "RUNNING",
        "COMPLETED",
        "PARTIAL",
        "FAILED",
        name="collection_run_status",
        native_enum=False,
        create_constraint=True,
        length=16,
    )
    raw_status = sa.Enum(
        "COLLECTED",
        "INGESTED",
        "FAILED",
        name="raw_listing_status",
        native_enum=False,
        create_constraint=True,
        length=16,
    )

    op.create_table(
        "collection_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("collector_name", sa.String(length=100), nullable=False),
        sa.Column("status", run_status, server_default="RUNNING", nullable=False),
        sa.Column("collected_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("succeeded_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_collection_runs_collector_name", "collection_runs", ["collector_name"])
    op.create_index("ix_collection_runs_status", "collection_runs", ["status"])
    op.create_index("ix_collection_runs_started_at", "collection_runs", ["started_at"])

    op.create_table(
        "raw_listings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", raw_status, server_default="COLLECTED", nullable=False),
        sa.Column("normalized_payload", sa.JSON(), nullable=True),
        sa.Column("listing_id", sa.Uuid(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["collection_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raw_listings_run_id", "raw_listings", ["run_id"])
    op.create_index("ix_raw_listings_source", "raw_listings", ["source"])
    op.create_index("ix_raw_listings_collected_at", "raw_listings", ["collected_at"])
    op.create_index("ix_raw_listings_status", "raw_listings", ["status"])
    op.create_index("ix_raw_listings_listing_id", "raw_listings", ["listing_id"])


def downgrade() -> None:
    op.drop_index("ix_raw_listings_listing_id", table_name="raw_listings")
    op.drop_index("ix_raw_listings_status", table_name="raw_listings")
    op.drop_index("ix_raw_listings_collected_at", table_name="raw_listings")
    op.drop_index("ix_raw_listings_source", table_name="raw_listings")
    op.drop_index("ix_raw_listings_run_id", table_name="raw_listings")
    op.drop_table("raw_listings")

    op.drop_index("ix_collection_runs_started_at", table_name="collection_runs")
    op.drop_index("ix_collection_runs_status", table_name="collection_runs")
    op.drop_index("ix_collection_runs_collector_name", table_name="collection_runs")
    op.drop_table("collection_runs")
