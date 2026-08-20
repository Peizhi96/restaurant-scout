"""Add link-only external leads.

Revision ID: 20260819_0007
Revises: 20260819_0006
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0007"
down_revision: str | None = "20260819_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    external_lead_source = sa.Enum(
        "BIZBUYSELL",
        "LOOPNET",
        name="external_lead_source",
        native_enum=False,
        create_constraint=True,
        length=24,
    )
    external_lead_status = sa.Enum(
        "NEW",
        "REVIEWING",
        "CONTACT_BROKER",
        "PASSED",
        name="external_lead_status",
        native_enum=False,
        create_constraint=True,
        length=24,
    )
    op.create_table(
        "external_leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", external_lead_source, nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.String(length=1000), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column(
            "status", external_lead_status, server_default="NEW", nullable=False
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_leads_canonical_url",
        "external_leads",
        ["canonical_url"],
        unique=True,
    )
    op.create_index("ix_external_leads_city", "external_leads", ["city"])
    op.create_index(
        "ix_external_leads_discovered_at", "external_leads", ["discovered_at"]
    )
    op.create_index("ix_external_leads_source", "external_leads", ["source"])
    op.create_index("ix_external_leads_status", "external_leads", ["status"])


def downgrade() -> None:
    op.drop_index("ix_external_leads_status", table_name="external_leads")
    op.drop_index("ix_external_leads_source", table_name="external_leads")
    op.drop_index("ix_external_leads_discovered_at", table_name="external_leads")
    op.drop_index("ix_external_leads_city", table_name="external_leads")
    op.drop_index("ix_external_leads_canonical_url", table_name="external_leads")
    op.drop_table("external_leads")
