"""add_performance_and_difficulty_to_interview_sessions

Revision ID: e0947561bd46
Revises: 8c9edc2b6bb8
Create Date: 2025-08-23 03:35:44.324258

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e0947561bd46'
down_revision = '8c9edc2b6bb8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add performance_score and difficulty_level to interview_sessions
    op.add_column('interview_sessions', sa.Column('performance_score', sa.DECIMAL(5, 2), nullable=True, server_default='0.00'))
    op.add_column('interview_sessions', sa.Column('difficulty_level', sa.Enum('easy', 'medium', 'hard', 'expert', name='difficulty_level'), nullable=True, server_default='medium'))


def downgrade() -> None:
    op.drop_column('interview_sessions', 'difficulty_level')
    op.drop_column('interview_sessions', 'performance_score')
    op.execute("DROP TYPE IF EXISTS difficulty_level")