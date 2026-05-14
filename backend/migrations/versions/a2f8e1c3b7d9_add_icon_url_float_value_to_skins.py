"""add icon_url float_value to skins

Revision ID: a2f8e1c3b7d9
Revises: 540c2b5ba3ab
Create Date: 2026-05-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a2f8e1c3b7d9'
down_revision: Union[str, None] = '540c2b5ba3ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('skins', sa.Column('icon_url', sa.String(512), nullable=True))
    op.add_column('skins', sa.Column('float_value', sa.Numeric(10, 9), nullable=True))


def downgrade() -> None:
    op.drop_column('skins', 'float_value')
    op.drop_column('skins', 'icon_url')
