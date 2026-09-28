"""add_phase9_product_ledger_and_label_versions

Revision ID: a1b2c3d4e5f6
Revises: 9d1f3b2a5c8e
Create Date: 2026-09-23 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import app.core.database


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9d1f3b2a5c8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update label_versions table
    op.add_column('label_versions', sa.Column('version_fingerprint', sa.String(length=64), nullable=True))
    op.add_column('label_versions', sa.Column('source_inspection_id', app.core.database.GUID(), nullable=True))
    op.add_column('label_versions', sa.Column('evidence_snapshot_id', app.core.database.GUID(), nullable=True))
    op.add_column('label_versions', sa.Column('metadata_json', sa.JSON(), server_default='{}', nullable=False))

    op.create_index(op.f('ix_label_versions_version_fingerprint'), 'label_versions', ['version_fingerprint'], unique=False)
    op.create_index(op.f('ix_label_versions_source_inspection_id'), 'label_versions', ['source_inspection_id'], unique=False)
    op.create_index(op.f('ix_label_versions_evidence_snapshot_id'), 'label_versions', ['evidence_snapshot_id'], unique=False)

    op.create_foreign_key(
        'fk_label_versions_source_inspection_id',
        'label_versions', 'inspections',
        ['source_inspection_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_label_versions_evidence_snapshot_id',
        'label_versions', 'evidence_snapshots',
        ['evidence_snapshot_id'], ['id'],
        ondelete='SET NULL'
    )

    # 2. Update inspections table with label_version_id
    op.add_column('inspections', sa.Column('label_version_id', app.core.database.GUID(), nullable=True))
    op.create_index(op.f('ix_inspections_label_version_id'), 'inspections', ['label_version_id'], unique=False)
    op.create_foreign_key(
        'fk_inspections_label_version_id',
        'inspections', 'label_versions',
        ['label_version_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_inspections_label_version_id', 'inspections', type_='foreignkey')
    op.drop_index(op.f('ix_inspections_label_version_id'), table_name='inspections')
    op.drop_column('inspections', 'label_version_id')

    op.drop_constraint('fk_label_versions_evidence_snapshot_id', 'label_versions', type_='foreignkey')
    op.drop_constraint('fk_label_versions_source_inspection_id', 'label_versions', type_='foreignkey')
    op.drop_index(op.f('ix_label_versions_evidence_snapshot_id'), table_name='label_versions')
    op.drop_index(op.f('ix_label_versions_source_inspection_id'), table_name='label_versions')
    op.drop_index(op.f('ix_label_versions_version_fingerprint'), table_name='label_versions')
    op.drop_column('label_versions', 'metadata_json')
    op.drop_column('label_versions', 'evidence_snapshot_id')
    op.drop_column('label_versions', 'source_inspection_id')
    op.drop_column('label_versions', 'version_fingerprint')
