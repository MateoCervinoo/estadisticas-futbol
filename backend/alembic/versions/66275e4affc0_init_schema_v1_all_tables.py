"""initial schema v1

Revision ID: 66275e4affc0
Revises: 
Create Date: 2026-06-29 20:07:55.251680

"""
from pathlib import Path
import sys
from typing import Sequence, Union

from alembic import op

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.models import SQLModel


# revision identifiers, used by Alembic.
revision: str = '66275e4affc0'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the full application schema on a clean database."""
    SQLModel.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    """Drop the full application schema."""
    SQLModel.metadata.drop_all(bind=op.get_bind())
