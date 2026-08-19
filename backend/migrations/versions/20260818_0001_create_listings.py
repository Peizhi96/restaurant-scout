"""Create the canonical listings table.

Revision ID: 20260818_0001
Revises:
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    status = sa.Enum(
        "NEW",
        "REVIEWING",
        "CONTACT_BROKER",
        "PASSED",
        "DUE_DILIGENCE",
        "REJECTED",
        "SOLD",
        "OFF_MARKET",
        name="listing_status",
        native_enum=False,
        create_constraint=True,
        length=32,
    )

    op.create_table(
        "listings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("business_name", sa.String(length=200), nullable=True),
        sa.Column("address", sa.String(length=300), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("zip", sa.String(length=10), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("asking_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("monthly_rent", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("size_sqft", sa.Integer(), nullable=True),
        sa.Column("seats", sa.Integer(), nullable=True),
        sa.Column("parking", sa.Boolean(), nullable=True),
        sa.Column("loading_access", sa.Boolean(), nullable=True),
        sa.Column("type1_hood", sa.Boolean(), nullable=True),
        sa.Column("hood_length", sa.Float(), nullable=True),
        sa.Column("grease_trap", sa.Boolean(), nullable=True),
        sa.Column("walk_in_cooler", sa.Boolean(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("status", status, server_default="NEW", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_listings_city", "listings", ["city"], unique=False)
    op.create_index("ix_listings_status", "listings", ["status"], unique=False)
    op.create_index("ix_listings_last_seen_at", "listings", ["last_seen_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_listings_last_seen_at", table_name="listings")
    op.drop_index("ix_listings_status", table_name="listings")
    op.drop_index("ix_listings_city", table_name="listings")
    op.drop_table("listings")
