"""add_hierarchical_roles_to_users_and_create_role_hierarchy

Revision ID: 315d9b61fef4
Revises: e0947561bd46
Create Date: 2025-08-23 03:37:06.556241

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '315d9b61fef4'
down_revision = 'e0947561bd46'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add hierarchical role columns to users table
    op.add_column('users', sa.Column('main_role', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('sub_role', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('specialization', sa.String(100), nullable=True))
    
    # Create role_hierarchy table
    op.create_table(
        'role_hierarchy',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('main_role', sa.String(100), nullable=False),
        sa.Column('sub_role', sa.String(100), nullable=True),
        sa.Column('specialization', sa.String(100), nullable=True),
        sa.Column('tech_stack', sa.JSON(), nullable=True),
        sa.Column('question_tags', sa.JSON(), nullable=True),
        sa.Column('version', sa.String(10), nullable=True, server_default='1.0'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_main_sub', 'main_role', 'sub_role'),
        sa.Index('idx_version_active', 'version', 'is_active')
    )
    
    # Add question_difficulty_tags to questions table
    op.add_column('questions', sa.Column('question_difficulty_tags', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('questions', 'question_difficulty_tags')
    op.drop_table('role_hierarchy')
    op.drop_column('users', 'specialization')
    op.drop_column('users', 'sub_role')
    op.drop_column('users', 'main_role')