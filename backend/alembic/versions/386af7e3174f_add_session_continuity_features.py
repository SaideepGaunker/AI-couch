"""add_session_continuity_features

Revision ID: 386af7e3174f
Revises: 315d9b61fef4
Create Date: 2025-08-23 03:37:27.184177

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '386af7e3174f'
down_revision = '315d9b61fef4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add session continuity columns to interview_sessions
    op.add_column('interview_sessions', sa.Column('parent_session_id', sa.Integer(), nullable=True))
    op.add_column('interview_sessions', sa.Column('session_mode', sa.Enum('new', 'practice_again', 'continued', name='session_mode'), nullable=True, server_default='new'))
    op.add_column('interview_sessions', sa.Column('resume_state', sa.JSON(), nullable=True))
    
    # Add foreign key constraint for parent_session_id
    op.create_foreign_key(
        'fk_interview_sessions_parent_session_id',
        'interview_sessions', 'interview_sessions',
        ['parent_session_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_interview_sessions_parent_session_id', 'interview_sessions', type_='foreignkey')
    op.drop_column('interview_sessions', 'resume_state')
    op.drop_column('interview_sessions', 'session_mode')
    op.drop_column('interview_sessions', 'parent_session_id')
    op.execute("DROP TYPE IF EXISTS session_mode")