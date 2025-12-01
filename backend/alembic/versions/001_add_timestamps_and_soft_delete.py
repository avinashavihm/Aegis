"""Add timestamps and soft delete

Revision ID: 001_add_timestamps
Revises: 
Create Date: 2025-12-01 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = '001_add_timestamps'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to workflow table
    op.add_column('workflow', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('workflow', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    
    # Set updated_at to created_at for existing records
    op.execute("UPDATE workflow SET updated_at = created_at WHERE updated_at IS NULL")
    
    # Make updated_at NOT NULL after setting values
    op.alter_column('workflow', 'updated_at', nullable=False)
    
    # Add columns to agent table
    op.add_column('agent', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('agent', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('agent', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    
    # Set timestamps for existing agent records (use current time as fallback)
    op.execute("UPDATE agent SET created_at = datetime('now') WHERE created_at IS NULL")
    op.execute("UPDATE agent SET updated_at = datetime('now') WHERE updated_at IS NULL")
    
    # Make timestamps NOT NULL after setting values
    op.alter_column('agent', 'created_at', nullable=False)
    op.alter_column('agent', 'updated_at', nullable=False)
    
    # Create indexes
    op.create_index('idx_workflow_created_at', 'workflow', ['created_at'])
    op.create_index('idx_workflow_deleted_at', 'workflow', ['deleted_at'])
    op.create_index('idx_agent_workflow_id', 'agent', ['workflow_id'])
    op.create_index('idx_agent_role', 'agent', ['role'])
    op.create_index('idx_agent_deleted_at', 'agent', ['deleted_at'])
    op.create_index('idx_dependency_workflow_id', 'agent_dependency', ['workflow_id'])
    op.create_index('idx_dependency_agent_id', 'agent_dependency', ['agent_id'])
    op.create_index('idx_dependency_depends_on', 'agent_dependency', ['depends_on_agent_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_dependency_depends_on', table_name='agent_dependency')
    op.drop_index('idx_dependency_agent_id', table_name='agent_dependency')
    op.drop_index('idx_dependency_workflow_id', table_name='agent_dependency')
    op.drop_index('idx_agent_deleted_at', table_name='agent')
    op.drop_index('idx_agent_role', table_name='agent')
    op.drop_index('idx_agent_workflow_id', table_name='agent')
    op.drop_index('idx_workflow_deleted_at', table_name='workflow')
    op.drop_index('idx_workflow_created_at', table_name='workflow')
    
    # Drop columns from agent table
    op.drop_column('agent', 'deleted_at')
    op.drop_column('agent', 'updated_at')
    op.drop_column('agent', 'created_at')
    
    # Drop columns from workflow table
    op.drop_column('workflow', 'deleted_at')
    op.drop_column('workflow', 'updated_at')

