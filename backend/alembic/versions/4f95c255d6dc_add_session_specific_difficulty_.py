"""add_session_specific_difficulty_tracking_fields

Revision ID: 4f95c255d6dc
Revises: c6ecad687cbd
Create Date: 2025-09-02 23:38:16.569352

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f95c255d6dc'
down_revision = 'c6ecad687cbd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add session-specific difficulty tracking fields
    op.add_column('interview_sessions', sa.Column('initial_difficulty_level', sa.String(50), nullable=True))
    op.add_column('interview_sessions', sa.Column('current_difficulty_level', sa.String(50), nullable=True))
    op.add_column('interview_sessions', sa.Column('final_difficulty_level', sa.String(50), nullable=True))
    op.add_column('interview_sessions', sa.Column('difficulty_changes_count', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('interview_sessions', sa.Column('difficulty_state_json', sa.JSON(), nullable=True))
    
    # Populate existing sessions with current difficulty_level as initial_difficulty_level
    # and current_difficulty_level
    op.execute("""
        UPDATE interview_sessions 
        SET initial_difficulty_level = difficulty_level,
            current_difficulty_level = difficulty_level
        WHERE difficulty_level IS NOT NULL
    """)
    
    # Set default values for sessions without difficulty_level
    op.execute("""
        UPDATE interview_sessions 
        SET initial_difficulty_level = 'medium',
            current_difficulty_level = 'medium'
        WHERE difficulty_level IS NULL
    """)


def downgrade() -> None:
    # Remove session-specific difficulty tracking fields
    op.drop_column('interview_sessions', 'difficulty_state_json')
    op.drop_column('interview_sessions', 'difficulty_changes_count')
    op.drop_column('interview_sessions', 'final_difficulty_level')
    op.drop_column('interview_sessions', 'current_difficulty_level')
    op.drop_column('interview_sessions', 'initial_difficulty_level')