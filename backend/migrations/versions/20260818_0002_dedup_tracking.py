"""Add deduplication, source, snapshot, and event tracking.

Revision ID: 20260818_0002
Revises: 20260818_0001
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_0002"
down_revision: str | None = "20260818_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    market_status = sa.Enum(
        "UNKNOWN",
        "ACTIVE",
        "PENDING",
        "SOLD",
        "OFF_MARKET",
        name="market_status",
        native_enum=False,
        create_constraint=True,
        length=24,
    )
    snapshot_market_status = sa.Enum(
        "UNKNOWN",
        "ACTIVE",
        "PENDING",
        "SOLD",
        "OFF_MARKET",
        name="snapshot_market_status",
        native_enum=False,
        create_constraint=True,
        length=24,
    )
    event_type = sa.Enum(
        "NEW_LISTING",
        "PRICE_DROP",
        "PRICE_INCREASE",
        "RENT_CHANGE",
        "STATUS_CHANGE",
        "BACK_ON_MARKET",
        "LISTING_REMOVED",
        name="listing_event_type",
        native_enum=False,
        create_constraint=True,
        length=32,
    )
    duplicate_status = sa.Enum(
        "PENDING",
        "MERGED",
        "DISTINCT",
        name="duplicate_review_status",
        native_enum=False,
        create_constraint=True,
        length=16,
    )

    with op.batch_alter_table("listings") as batch_op:
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("normalized_address", sa.String(length=300), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "market_status", market_status, server_default="UNKNOWN", nullable=False
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_duplicate", sa.Boolean(), server_default=sa.false(), nullable=False
            )
        )
        batch_op.add_column(sa.Column("merged_into_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_listings_merged_into_id",
            "listings",
            ["merged_into_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_listings_normalized_address", ["normalized_address"]
        )
        batch_op.create_index("ix_listings_market_status", ["market_status"])
        batch_op.create_index("ix_listings_merged_into_id", ["merged_into_id"])

    op.create_table(
        "listing_source_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.String(length=1000), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_source_external_id"),
    )
    op.create_index(
        "ix_listing_source_records_canonical_url",
        "listing_source_records",
        ["canonical_url"],
        unique=True,
    )
    op.create_index("ix_listing_source_records_listing_id", "listing_source_records", ["listing_id"])
    op.create_index("ix_listing_source_records_last_seen_at", "listing_source_records", ["last_seen_at"])

    op.create_table(
        "listing_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("source_record_id", sa.Uuid(), nullable=True),
        sa.Column("asking_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("monthly_rent", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("market_status", snapshot_market_status, server_default="UNKNOWN", nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_record_id"], ["listing_source_records.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_listing_snapshots_listing_id", "listing_snapshots", ["listing_id"])
    op.create_index("ix_listing_snapshots_captured_at", "listing_snapshots", ["captured_at"])

    op.create_table(
        "listing_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["listing_snapshots.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_listing_events_listing_id", "listing_events", ["listing_id"])
    op.create_index("ix_listing_events_event_type", "listing_events", ["event_type"])
    op.create_index("ix_listing_events_detected_at", "listing_events", ["detected_at"])

    op.create_table(
        "possible_duplicates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_listing_id", sa.Uuid(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("match_reasons", sa.JSON(), nullable=False),
        sa.Column("status", duplicate_status, server_default="PENDING", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["candidate_listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("listing_id", "candidate_listing_id", name="uq_possible_duplicate_pair"),
    )
    op.create_index("ix_possible_duplicates_listing_id", "possible_duplicates", ["listing_id"])
    op.create_index("ix_possible_duplicates_candidate_listing_id", "possible_duplicates", ["candidate_listing_id"])
    op.create_index("ix_possible_duplicates_status", "possible_duplicates", ["status"])


def downgrade() -> None:
    op.drop_index("ix_possible_duplicates_status", table_name="possible_duplicates")
    op.drop_index("ix_possible_duplicates_candidate_listing_id", table_name="possible_duplicates")
    op.drop_index("ix_possible_duplicates_listing_id", table_name="possible_duplicates")
    op.drop_table("possible_duplicates")

    op.drop_index("ix_listing_events_detected_at", table_name="listing_events")
    op.drop_index("ix_listing_events_event_type", table_name="listing_events")
    op.drop_index("ix_listing_events_listing_id", table_name="listing_events")
    op.drop_table("listing_events")

    op.drop_index("ix_listing_snapshots_captured_at", table_name="listing_snapshots")
    op.drop_index("ix_listing_snapshots_listing_id", table_name="listing_snapshots")
    op.drop_table("listing_snapshots")

    op.drop_index("ix_listing_source_records_last_seen_at", table_name="listing_source_records")
    op.drop_index("ix_listing_source_records_listing_id", table_name="listing_source_records")
    op.drop_index("ix_listing_source_records_canonical_url", table_name="listing_source_records")
    op.drop_table("listing_source_records")

    with op.batch_alter_table("listings") as batch_op:
        batch_op.drop_index("ix_listings_merged_into_id")
        batch_op.drop_index("ix_listings_market_status")
        batch_op.drop_index("ix_listings_normalized_address")
        batch_op.drop_constraint("fk_listings_merged_into_id", type_="foreignkey")
        batch_op.drop_constraint("market_status", type_="check")
        batch_op.drop_column("merged_into_id")
        batch_op.drop_column("is_duplicate")
        batch_op.drop_column("market_status")
        batch_op.drop_column("normalized_address")
        batch_op.drop_column("description")
