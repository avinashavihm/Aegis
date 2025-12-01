"""Add Phase 0 capabilities and execution enhancements

Revision ID: 002_phase0_capabilities
Revises: 001_add_timestamps
Create Date: 2025-12-01 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '002_phase0_capabilities'
down_revision: Union[str, None] = '001_add_timestamps'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add capability and configuration fields to agent table
    op.add_column('agent', sa.Column('capability_config', sqlite.JSON(), nullable=True))
    op.add_column('agent', sa.Column('resource_limits', sqlite.JSON(), nullable=True))
    op.add_column('agent', sa.Column('input_schema', sqlite.JSON(), nullable=True))
    op.add_column('agent', sa.Column('output_schema', sqlite.JSON(), nullable=True))
    
    # Add execution mode and context fields to workflow_execution table
    # SQLite doesn't support ALTER COLUMN, so we use server_default for defaults
    op.add_column('workflow_execution', sa.Column('execution_mode', sa.Text(), nullable=False, server_default='synchronous'))
    op.add_column('workflow_execution', sa.Column('execution_context', sqlite.JSON(), nullable=True))
    op.add_column('workflow_execution', sa.Column('retry_policy', sqlite.JSON(), nullable=True))
    op.add_column('workflow_execution', sa.Column('max_retries', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('workflow_execution', sa.Column('retry_delay', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('workflow_execution', sa.Column('next_retry_at', sa.DateTime(), nullable=True))
    op.add_column('workflow_execution', sa.Column('scheduled_at', sa.DateTime(), nullable=True))
    op.add_column('workflow_execution', sa.Column('cron_expression', sa.Text(), nullable=True))
    op.add_column('workflow_execution', sa.Column('loop_config', sqlite.JSON(), nullable=True))
    op.add_column('workflow_execution', sa.Column('conditional_config', sqlite.JSON(), nullable=True))
    op.add_column('workflow_execution', sa.Column('parent_execution_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_workflow_execution_parent_execution_id'), 'workflow_execution', ['parent_execution_id'], unique=False)
    op.create_foreign_key(op.f('fk_workflow_execution_parent_execution_id_workflow_execution'), 'workflow_execution', 'workflow_execution', ['parent_execution_id'], ['id'])
    
    # Add error details to agent_execution table
    op.add_column('agent_execution', sa.Column('error_details', sqlite.JSON(), nullable=True))


def downgrade() -> None:
    # Drop foreign key and indexes
    op.drop_constraint(op.f('fk_workflow_execution_parent_execution_id_workflow_execution'), 'workflow_execution', type_='foreignkey')
    op.drop_index(op.f('ix_workflow_execution_parent_execution_id'), table_name='workflow_execution')
    
    # Drop columns from agent_execution table
    op.drop_column('agent_execution', 'error_details')
    
    # Drop columns from workflow_execution table
    op.drop_column('workflow_execution', 'parent_execution_id')
    op.drop_column('workflow_execution', 'conditional_config')
    op.drop_column('workflow_execution', 'loop_config')
    op.drop_column('workflow_execution', 'cron_expression')
    op.drop_column('workflow_execution', 'scheduled_at')
    op.drop_column('workflow_execution', 'next_retry_at')
    op.drop_column('workflow_execution', 'retry_delay')
    op.drop_column('workflow_execution', 'max_retries')
    op.drop_column('workflow_execution', 'retry_policy')
    op.drop_column('workflow_execution', 'execution_context')
    op.drop_column('workflow_execution', 'execution_mode')
    
    # Drop columns from agent table
    op.drop_column('agent', 'output_schema')
    op.drop_column('agent', 'input_schema')
    op.drop_column('agent', 'resource_limits')
    op.drop_column('agent', 'capability_config')

