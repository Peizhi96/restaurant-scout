"""Add scan reconciliation audit state.

Revision ID: 20260819_0005
Revises: 20260819_0004
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0005"
down_revision: str | None = "20260819_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    source_market_status = sa.Enum(
        "UNKNOWN",
        "ACTIVE",
        "PENDING",
        "SOLD",
        "OFF_MARKET",
        name="source_market_status",
        native_enum=False,
        create_constraint=True,
        length=24,
    )

    with op.batch_alter_table("collection_runs") as batch_op:
        batch_op.add_column(
            sa.Column("reconciled_count", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.add_column(
            sa.Column("source_removed_count", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.add_column(
            sa.Column("listing_removed_count", sa.Integer(), server_default="0", nullable=False)
        )

    with op.batch_alter_table("listing_source_records") as batch_op:
        batch_op.add_column(
            sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("missed_scan_count", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.add_column(sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column(
                "market_status",
                source_market_status,
                server_default="UNKNOWN",
                nullable=False,
            )
        )
        batch_op.create_index(
            "ix_listing_source_records_removed_at", ["removed_at"]
        )
        batch_op.create_index(
            "ix_listing_source_records_market_status", ["market_status"]
        )


def downgrade() -> None:
    with op.batch_alter_table("listing_source_records") as batch_op:
        batch_op.drop_index("ix_listing_source_records_market_status")
        batch_op.drop_index("ix_listing_source_records_removed_at")
        batch_op.drop_constraint("source_market_status", type_="check")
        batch_op.drop_column("market_status")
        batch_op.drop_column("removed_at")
        batch_op.drop_column("missed_scan_count")
        batch_op.drop_column("last_checked_at")

    with op.batch_alter_table("collection_runs") as batch_op:
        batch_op.drop_column("listing_removed_count")
        batch_op.drop_column("source_removed_count")
        batch_op.drop_column("reconciled_count")
