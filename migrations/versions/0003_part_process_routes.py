"""Allow product-specific process routes.

Revision ID: 0003_process_routes
Revises: 0002_realworld
Create Date: 2026-11-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_process_routes"
down_revision: Union[str, None] = "0002_realworld"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("parts", sa.Column("process_route", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("parts", "process_route")
