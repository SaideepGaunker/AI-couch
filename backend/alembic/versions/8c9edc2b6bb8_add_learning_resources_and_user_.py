"""add_learning_resources_and_user_recommendations_tables

Revision ID: 8c9edc2b6bb8
Revises: 01453d80708f
Create Date: 2025-08-23 03:30:57.341610

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c9edc2b6bb8'
down_revision = '01453d80708f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create learning_resources table
    op.create_table(
        'learning_resources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category', sa.Enum('body_language', 'voice_analysis', 'content_quality', 'overall', name='resource_category'), nullable=False),
        sa.Column('type', sa.Enum('video', 'course', name='resource_type'), nullable=False),
        sa.Column('level', sa.Enum('beginner', 'intermediate', 'advanced', name='resource_level'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('provider', sa.String(100), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('ranking_weight', sa.DECIMAL(3, 2), nullable=True, server_default='1.00'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_category_level_type', 'category', 'level', 'type')
    )
    
    # Create user_recommendations table
    op.create_table(
        'user_recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=False),
        sa.Column('recommended_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('clicked', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('user_feedback', sa.Enum('liked', 'disliked', 'neutral', name='feedback_type'), nullable=True, server_default='neutral'),
        sa.Column('feedback_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['resource_id'], ['learning_resources.id']),
        sa.Index('idx_user_resource', 'user_id', 'resource_id')
    )


def downgrade() -> None:
    op.drop_table('user_recommendations')
    op.drop_table('learning_resources')
    
    # Drop the enums
    op.execute("DROP TYPE IF EXISTS resource_category")
    op.execute("DROP TYPE IF EXISTS resource_type") 
    op.execute("DROP TYPE IF EXISTS resource_level")
    op.execute("DROP TYPE IF EXISTS feedback_type")