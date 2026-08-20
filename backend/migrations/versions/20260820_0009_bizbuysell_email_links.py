"""Add automated BizBuySell email-alert link discovery.

Revision ID: 20260820_0009
Revises: 20260820_0008
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_0009"
down_revision: str | None = "20260820_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    discovery_method = sa.Enum(
        "MANUAL",
        "EMAIL_ALERT",
        name="external_lead_discovery_method",
        native_enum=False,
        create_constraint=True,
        length=24,
    )
    sync_status = sa.Enum(
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
        name="external_lead_sync_status",
        native_enum=False,
        create_constraint=True,
        length=24,
    )
    op.add_column(
        "external_leads",
        sa.Column(
            "discovery_method",
            discovery_method,
            server_default="MANUAL",
            nullable=False,
        ),
    )
    op.create_index(
        "ix_external_leads_discovery_method",
        "external_leads",
        ["discovery_method"],
    )
    op.create_table(
        "external_lead_sync_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "BIZBUYSELL",
                "LOOPNET",
                name="external_lead_source",
                native_enum=False,
                create_constraint=False,
                length=24,
            ),
            nullable=False,
        ),
        sa.Column("status", sync_status, server_default="RUNNING", nullable=False),
        sa.Column("messages_scanned", sa.Integer(), server_default="0", nullable=False),
        sa.Column("links_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("leads_created", sa.Integer(), server_default="0", nullable=False),
        sa.Column("leads_existing", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_lead_sync_runs_source", "external_lead_sync_runs", ["source"]
    )
    op.create_index(
        "ix_external_lead_sync_runs_started_at",
        "external_lead_sync_runs",
        ["started_at"],
    )
    op.create_index(
        "ix_external_lead_sync_runs_status", "external_lead_sync_runs", ["status"]
    )


def downgrade() -> None:
    op.drop_index("ix_external_lead_sync_runs_status", table_name="external_lead_sync_runs")
    op.drop_index(
        "ix_external_lead_sync_runs_started_at", table_name="external_lead_sync_runs"
    )
    op.drop_index("ix_external_lead_sync_runs_source", table_name="external_lead_sync_runs")
    op.drop_table("external_lead_sync_runs")
    op.drop_index("ix_external_leads_discovery_method", table_name="external_leads")
    op.drop_column("external_leads", "discovery_method")
