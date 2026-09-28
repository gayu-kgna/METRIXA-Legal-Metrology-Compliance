"""add_phase6_evidence_and_reports

Revision ID: 8c2f1a9b3d4e
Revises: 7a1e2f3d4c5b
Create Date: 2026-09-22 20:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import app.core.database


# revision identifiers, used by Alembic.
revision: str = '8c2f1a9b3d4e'
down_revision: Union[str, None] = '7a1e2f3d4c5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create evidence_snapshots table
    op.create_table(
        'evidence_snapshots',
        sa.Column('id', app.core.database.GUID(), nullable=False),
        sa.Column('inspection_id', app.core.database.GUID(), nullable=False),
        sa.Column('evaluation_run_id', app.core.database.GUID(), nullable=True),
        sa.Column('created_by_id', app.core.database.GUID(), nullable=True),
        sa.Column('application_version', sa.String(length=50), nullable=False, server_default='1.0.0'),
        sa.Column('parser_version', sa.String(length=50), nullable=False, server_default='ENTITY-PARSER-v1'),
        sa.Column('normalizer_version', sa.String(length=50), nullable=False, server_default='NORMALIZER-v1'),
        sa.Column('ocr_provider_version', sa.String(length=100), nullable=False, server_default='Modular OCR Engine'),
        sa.Column('rule_versions', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('source_record_ids', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('manifest_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('integrity_hash', sa.String(length=64), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidence_snapshots_inspection_id'), 'evidence_snapshots', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_evidence_snapshots_evaluation_run_id'), 'evidence_snapshots', ['evaluation_run_id'], unique=False)
    op.create_index(op.f('ix_evidence_snapshots_integrity_hash'), 'evidence_snapshots', ['integrity_hash'], unique=False)

    # 2. Create inspection_reports table
    op.create_table(
        'inspection_reports',
        sa.Column('id', app.core.database.GUID(), nullable=False),
        sa.Column('inspection_id', app.core.database.GUID(), nullable=False),
        sa.Column('evidence_snapshot_id', app.core.database.GUID(), nullable=False),
        sa.Column('evaluation_run_id', app.core.database.GUID(), nullable=True),
        sa.Column('report_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='GENERATED'),
        sa.Column('generated_by_id', app.core.database.GUID(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_snapshot_id'], ['evidence_snapshots.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['generated_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inspection_reports_inspection_id'), 'inspection_reports', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_inspection_reports_evidence_snapshot_id'), 'inspection_reports', ['evidence_snapshot_id'], unique=False)
    op.create_index(op.f('ix_inspection_reports_evaluation_run_id'), 'inspection_reports', ['evaluation_run_id'], unique=False)
    op.create_index(op.f('ix_inspection_reports_sha256_hash'), 'inspection_reports', ['sha256_hash'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_inspection_reports_sha256_hash'), table_name='inspection_reports')
    op.drop_index(op.f('ix_inspection_reports_evaluation_run_id'), table_name='inspection_reports')
    op.drop_index(op.f('ix_inspection_reports_evidence_snapshot_id'), table_name='inspection_reports')
    op.drop_index(op.f('ix_inspection_reports_inspection_id'), table_name='inspection_reports')
    op.drop_table('inspection_reports')

    op.drop_index(op.f('ix_evidence_snapshots_integrity_hash'), table_name='evidence_snapshots')
    op.drop_index(op.f('ix_evidence_snapshots_evaluation_run_id'), table_name='evidence_snapshots')
    op.drop_index(op.f('ix_evidence_snapshots_inspection_id'), table_name='evidence_snapshots')
    op.drop_table('evidence_snapshots')
