"""remove_unused_institution_tables

Revision ID: bec0131359c1
Revises: e454a92354a6
Create Date: 2025-08-30 22:53:30.766471

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bec0131359c1'
down_revision = 'e454a92354a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, remove the foreign key constraint from users table
    op.drop_constraint('users_institution_id_fkey', 'users', type_='foreignkey')
    
    # Remove the institution_id column from users table
    op.drop_column('users', 'institution_id')
    
    # Drop the institution_analytics table (has foreign key to institutions)
    op.drop_table('institution_analytics')
    
    # Drop the institutions table
    op.drop_table('institutions')


def downgrade() -> None:
    # Recreate institutions table
    op.create_table('institutions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=100), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_institutions_id'), 'institutions', ['id'], unique=False)
    
    # Recreate institution_analytics table
    op.create_table('institution_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('institution_id', sa.Integer(), nullable=False),
        sa.Column('total_students', sa.Integer(), nullable=True),
        sa.Column('active_students', sa.Integer(), nullable=True),
        sa.Column('average_readiness_score', sa.Float(), nullable=True),
        sa.Column('completion_rate', sa.Float(), nullable=True),
        sa.Column('report_date', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_institution_analytics_id'), 'institution_analytics', ['id'], unique=False)
    
    # Add back the institution_id column to users table
    op.add_column('users', sa.Column('institution_id', sa.Integer(), nullable=True))
    
    # Recreate the foreign key constraint
    op.create_foreign_key('users_institution_id_fkey', 'users', 'institutions', ['institution_id'], ['id'])