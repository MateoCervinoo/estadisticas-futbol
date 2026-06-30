"""add tipo_dato to partido

Revision ID: 8f2a4b6c9d10
Revises: 66275e4affc0
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "8f2a4b6c9d10"
down_revision: Union[str, Sequence[str], None] = "66275e4affc0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("partido")}
    if "tipo_dato" not in columns:
        op.add_column(
            "partido",
            sa.Column("tipo_dato", sa.String(length=20), nullable=False, server_default="historico"),
        )
    op.execute(
        """
        UPDATE partido
        SET tipo_dato = CASE
            WHEN fuente_origen = 'api_football_data' AND estado IN ('NS', 'TIMED') THEN 'fixture'
            WHEN fuente_origen = 'api_football_data' THEN 'api_sync'
            ELSE 'historico'
        END
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("partido")}
    if "tipo_dato" in columns:
        op.drop_column("partido", "tipo_dato")
