"""Add real-world resource availability and physical tool constraints.

Revision ID: 0002_realworld
Revises: 0001_initial
Create Date: 2026-11-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_realworld"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "resources",
        sa.Column("blackout_windows", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column("parts", sa.Column("tool_id", sa.String(length=80), nullable=True))
    op.create_index("ix_parts_tool_id", "parts", ["tool_id"])
    op.add_column("work_orders", sa.Column("locked_resource_id", sa.String(length=80), nullable=True))
    op.add_column(
        "work_orders",
        sa.Column("locked_until_hour", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("work_orders", "locked_until_hour")
    op.drop_column("work_orders", "locked_resource_id")
    op.drop_index("ix_parts_tool_id", table_name="parts")
    op.drop_column("parts", "tool_id")
    op.drop_column("resources", "blackout_windows")
