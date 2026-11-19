"""Assign each work order to a planning plant.

Revision ID: 0004_work_order_plant
Revises: 0003_process_routes
Create Date: 2026-11-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_work_order_plant"
down_revision: Union[str, None] = "0003_process_routes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("work_orders", sa.Column("plant", sa.String(length=32), nullable=True))
    op.create_index("ix_work_orders_plant", "work_orders", ["plant"])


def downgrade() -> None:
    op.drop_index("ix_work_orders_plant", table_name="work_orders")
    op.drop_column("work_orders", "plant")
