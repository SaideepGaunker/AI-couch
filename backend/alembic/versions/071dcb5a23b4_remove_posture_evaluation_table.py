"""remove_posture_evaluation_table

Revision ID: 071dcb5a23b4
Revises: 7c8b87a300f2
Create Date: 2025-08-17 00:35:10.546031

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '071dcb5a23b4'
down_revision = '7c8b87a300f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove the PostureEvaluation table
    op.drop_table('posture_evaluations')


def downgrade() -> None:
    # Recreate the PostureEvaluation table
    op.create_table('posture_evaluations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('interview_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('head_tilt_score', sa.Float(), nullable=True),
        sa.Column('back_straightness_score', sa.Float(), nullable=True),
        sa.Column('shoulder_alignment_score', sa.Float(), nullable=True),
        sa.Column('feedback_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['interview_id'], ['interview_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )