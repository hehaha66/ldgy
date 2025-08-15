"""Add foreign key constraints to models

Revision ID: 4302d349667d
Revises: 21c37eb56ac3
Create Date: 2025-08-13 14:19:45.948496

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4302d349667d'
down_revision: Union[str, None] = '21c37eb56ac3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
