"""Add deterministic listing scores.

Revision ID: 20260819_0006
Revises: 20260819_0005
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0006"
down_revision: str | None = "20260819_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "listing_scores",
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("corporate_catering_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("restaurant_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("overall_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("corporate_completeness", sa.Numeric(5, 2), nullable=False),
        sa.Column("restaurant_completeness", sa.Numeric(5, 2), nullable=False),
        sa.Column("corporate_factors", sa.JSON(), nullable=False),
        sa.Column("restaurant_factors", sa.JSON(), nullable=False),
        sa.Column("missing_information", sa.JSON(), nullable=False),
        sa.Column("config_version", sa.String(length=40), nullable=False),
        sa.Column(
            "calculated_at",
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
        sa.PrimaryKeyConstraint("listing_id"),
    )
    op.create_index(
        "ix_listing_scores_overall_score", "listing_scores", ["overall_score"]
    )


def downgrade() -> None:
    op.drop_index("ix_listing_scores_overall_score", table_name="listing_scores")
    op.drop_table("listing_scores")
