"""Create all tables for MySQL

Revision ID: 186ac523c9b2
Revises: b8863d3adb5b
Create Date: 2025-08-13 11:12:41.294895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '186ac523c9b2'
down_revision: Union[str, None] = 'b8863d3adb5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
