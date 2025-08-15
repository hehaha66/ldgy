"""Final working version of all tables

Revision ID: 21c37eb56ac3
Revises: 186ac523c9b2
Create Date: 2025-08-13 13:04:17.915698

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21c37eb56ac3'
down_revision: Union[str, None] = '186ac523c9b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
