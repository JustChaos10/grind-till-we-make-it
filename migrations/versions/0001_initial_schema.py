"""Initial IndoFlow schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("plant", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("capacity_units", sa.Integer(), nullable=False),
        sa.Column("alloy_compatibility", sa.JSON(), nullable=False),
        sa.Column("recipe_compatibility", sa.JSON(), nullable=False),
        sa.Column("setup_changeover_mins", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_resources_name", "resources", ["name"], unique=True)
    op.create_index("ix_resources_plant", "resources", ["plant"])
    op.create_index("ix_resources_stage", "resources", ["stage"])
    op.create_index("ix_resources_status", "resources", ["status"])

    op.create_table(
        "parts",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("sku_code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("segment", sa.String(length=32), nullable=False),
        sa.Column("alloy_family", sa.String(length=48), nullable=False),
        sa.Column("sintering_recipe_id", sa.String(length=64), nullable=False),
        sa.Column("cycle_times_mins", sa.JSON(), nullable=False),
        sa.Column("requires_machining", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("sku_code"),
    )
    op.create_index("ix_parts_sku_code", "parts", ["sku_code"], unique=True)
    op.create_index("ix_parts_segment", "parts", ["segment"])
    op.create_index("ix_parts_alloy_family", "parts", ["alloy_family"])
    op.create_index("ix_parts_sintering_recipe_id", "parts", ["sintering_recipe_id"])

    op.create_table(
        "work_orders",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("wo_number", sa.String(length=40), nullable=False),
        sa.Column("part_id", sa.String(length=80), sa.ForeignKey("parts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("due_date_hours", sa.Float(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("current_stage", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("wip_age_hours", sa.Float(), nullable=False),
        sa.UniqueConstraint("wo_number"),
    )
    op.create_index("ix_work_orders_wo_number", "work_orders", ["wo_number"], unique=True)
    op.create_index("ix_work_orders_part_id", "work_orders", ["part_id"])
    op.create_index("ix_work_orders_current_stage", "work_orders", ["current_stage"])
    op.create_index("ix_work_orders_status", "work_orders", ["status"])
    op.create_index("ix_work_orders_status_due", "work_orders", ["status", "due_date_hours"])

    op.create_table(
        "schedule_versions",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("total_late_orders", sa.Integer(), nullable=False),
        sa.Column("avg_wip_age_hours", sa.Float(), nullable=False),
        sa.Column("bottleneck_resource_id", sa.String(length=80), sa.ForeignKey("resources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("summary_metrics", sa.JSON(), nullable=False),
    )
    op.create_index("ix_schedule_versions_mode", "schedule_versions", ["mode"])

    op.create_table(
        "scheduled_operations",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("schedule_version_id", sa.String(length=80), sa.ForeignKey("schedule_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_order_id", sa.String(length=80), sa.ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_id", sa.String(length=80), sa.ForeignKey("resources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("start_hour", sa.Float(), nullable=False),
        sa.Column("end_hour", sa.Float(), nullable=False),
        sa.Column("batch_id", sa.String(length=100), nullable=True),
        sa.Column("is_late", sa.Boolean(), nullable=False),
        sa.Column("delay_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_scheduled_operations_schedule_version_id", "scheduled_operations", ["schedule_version_id"])
    op.create_index("ix_scheduled_operations_work_order_id", "scheduled_operations", ["work_order_id"])
    op.create_index("ix_scheduled_operations_resource_id", "scheduled_operations", ["resource_id"])
    op.create_index("ix_scheduled_operations_stage", "scheduled_operations", ["stage"])
    op.create_index("ix_scheduled_operations_batch_id", "scheduled_operations", ["batch_id"])
    op.create_index("ix_scheduled_operations_version", "scheduled_operations", ["schedule_version_id"])
    op.create_index("ix_scheduled_operations_work_order", "scheduled_operations", ["work_order_id"])


def downgrade() -> None:
    op.drop_table("scheduled_operations")
    op.drop_table("schedule_versions")
    op.drop_table("work_orders")
    op.drop_table("parts")
    op.drop_table("resources")
