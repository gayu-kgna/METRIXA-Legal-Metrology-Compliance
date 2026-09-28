"""add_phase5_rule_engine_fields

Revision ID: 7a1e2f3d4c5b
Revises: f85dcfb84dde
Create Date: 2026-09-22 19:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.core.database


# revision identifiers, used by Alembic.
revision: str = '7a1e2f3d4c5b'
down_revision: Union[str, None] = 'f85dcfb84dde'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add NOT_APPLICABLE to ruleoutcome enum in PostgreSQL
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE ruleoutcome ADD VALUE IF NOT EXISTS 'NOT_APPLICABLE'")

    # 2. Add columns to rule_definitions
    op.add_column('rule_definitions', sa.Column('jurisdiction', sa.String(length=50), nullable=False, server_default='IN'))
    op.add_column('rule_definitions', sa.Column('category', sa.String(length=100), nullable=False, server_default='MANDATORY_DECLARATION'))
    op.add_column('rule_definitions', sa.Column('is_test_rule', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index(op.f('ix_rule_definitions_jurisdiction'), 'rule_definitions', ['jurisdiction'], unique=False)
    op.create_index(op.f('ix_rule_definitions_category'), 'rule_definitions', ['category'], unique=False)
    op.create_index(op.f('ix_rule_definitions_is_test_rule'), 'rule_definitions', ['is_test_rule'], unique=False)

    # 3. Add columns to rule_evaluations
    op.add_column('rule_evaluations', sa.Column('rule_version', sa.String(length=50), nullable=True))
    op.add_column('rule_evaluations', sa.Column('applicability_result', sa.JSON(), nullable=False, server_default='{}'))
    op.add_column('rule_evaluations', sa.Column('evaluation_run_id', app.core.database.GUID(), nullable=True))
    op.create_index(op.f('ix_rule_evaluations_evaluation_run_id'), 'rule_evaluations', ['evaluation_run_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_rule_evaluations_evaluation_run_id'), table_name='rule_evaluations')
    op.drop_column('rule_evaluations', 'evaluation_run_id')
    op.drop_column('rule_evaluations', 'applicability_result')
    op.drop_column('rule_evaluations', 'rule_version')

    op.drop_index(op.f('ix_rule_definitions_is_test_rule'), table_name='rule_definitions')
    op.drop_index(op.f('ix_rule_definitions_category'), table_name='rule_definitions')
    op.drop_index(op.f('ix_rule_definitions_jurisdiction'), table_name='rule_definitions')
    op.drop_column('rule_definitions', 'is_test_rule')
    op.drop_column('rule_definitions', 'category')
    op.drop_column('rule_definitions', 'jurisdiction')
