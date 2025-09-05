"""merge_heads

Revision ID: e454a92354a6
Revises: 386af7e3174f, add_performance_indexes, optimize_indexes_001
Create Date: 2025-08-30 22:53:21.342676

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e454a92354a6'
down_revision = ('386af7e3174f', 'add_performance_indexes', 'optimize_indexes_001')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass