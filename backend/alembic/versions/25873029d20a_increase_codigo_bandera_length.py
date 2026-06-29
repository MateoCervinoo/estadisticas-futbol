"""increase codigo_bandera length

Revision ID: 25873029d20a
Revises: 66275e4affc0
Create Date: 2026-06-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '25873029d20a'
down_revision: Union[str, Sequence[str], None] = '66275e4affc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('equipo', 'codigo_bandera', type_=sa.String(10), existing_type=sa.String(2))


def downgrade() -> None:
    op.alter_column('equipo', 'codigo_bandera', type_=sa.String(2), existing_type=sa.String(10))
