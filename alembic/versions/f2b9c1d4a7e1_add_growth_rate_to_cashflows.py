"""Add growth_rate to cashflows

Revision ID: f2b9c1d4a7e1
Revises: 85fca8df120a
Create Date: 2026-03-18 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2b9c1d4a7e1"
down_revision: Union[str, None] = "85fca8df120a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cashflows", sa.Column("growth_rate", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("cashflows", "growth_rate")

