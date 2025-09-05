"""enhance_user_progress_table

Revision ID: f18c4b44c320
Revises: bec0131359c1
Create Date: 2025-08-30 23:05:05.272584

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f18c4b44c320'
down_revision = 'bec0131359c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to user_progress table for enhanced performance tracking
    op.add_column('user_progress', sa.Column('recommendations', sa.JSON(), nullable=True, default=lambda: []))
    op.add_column('user_progress', sa.Column('improvement_areas', sa.JSON(), nullable=True, default=lambda: []))
    op.add_column('user_progress', sa.Column('learning_suggestions', sa.JSON(), nullable=True, default=lambda: []))
    
    # Add indexes for better query performance
    op.create_index('idx_user_progress_user_date', 'user_progress', ['user_id', 'session_date'])
    op.create_index('idx_user_progress_metric_type', 'user_progress', ['metric_type'])


def downgrade() -> None:
    # Remove indexes
    op.drop_index('idx_user_progress_metric_type', 'user_progress')
    op.drop_index('idx_user_progress_user_date', 'user_progress')
    
    # Remove columns
    op.drop_column('user_progress', 'learning_suggestions')
    op.drop_column('user_progress', 'improvement_areas')
    op.drop_column('user_progress', 'recommendations')