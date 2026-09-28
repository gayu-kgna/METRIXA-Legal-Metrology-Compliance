"""add_phase8_adjudication

Revision ID: 9d1f3b2a5c8e
Revises: 8c2f1a9b3d4e
Create Date: 2026-09-23 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.core.database


# revision identifiers, used by Alembic.
revision: str = '9d1f3b2a5c8e'
down_revision: Union[str, None] = '8c2f1a9b3d4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute("ALTER TYPE observationstatus ADD VALUE IF NOT EXISTS 'REJECTED'")
        op.execute("ALTER TYPE observationstatus ADD VALUE IF NOT EXISTS 'UNCERTAIN'")
        op.execute("""
            DO $$
            BEGIN
                CREATE TYPE correctiontype AS ENUM (
                    'TEXT_CORRECTION',
                    'BOUNDING_BOX_CORRECTION',
                    'REGION_CREATED',
                    'REGION_REJECTED',
                    'REGION_SPLIT',
                    'REGION_MERGED',
                    'MANUAL_DECLARATION'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)

    # Create ocr_adjudications table
    op.create_table(
        'ocr_adjudications',
        sa.Column('id', app.core.database.GUID(), nullable=False),
        sa.Column('inspection_id', app.core.database.GUID(), nullable=False),
        sa.Column('surface_id', app.core.database.GUID(), nullable=False),
        sa.Column('ocr_run_id', app.core.database.GUID(), nullable=True),
        sa.Column('ocr_region_id', app.core.database.GUID(), nullable=True),
        sa.Column('parent_adjudication_id', app.core.database.GUID(), nullable=True),
        sa.Column(
            'correction_type',
            postgresql.ENUM(
                'TEXT_CORRECTION',
                'BOUNDING_BOX_CORRECTION',
                'REGION_CREATED',
                'REGION_REJECTED',
                'REGION_SPLIT',
                'REGION_MERGED',
                'MANUAL_DECLARATION',
                name='correctiontype',
                create_type=False
            ),
            nullable=False
        ),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='CORRECTED'),
        sa.Column('original_text', sa.Text(), nullable=True),
        sa.Column('corrected_text', sa.Text(), nullable=True),
        sa.Column('original_bounding_box', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('corrected_bounding_box', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('original_confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_by_id', app.core.database.GUID(), nullable=True),
        sa.Column('revision', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('adjudicated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['surface_id'], ['inspection_surfaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ocr_run_id'], ['ocr_runs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['ocr_region_id'], ['ocr_regions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_adjudication_id'], ['ocr_adjudications.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ocr_adjudications_inspection_id'), 'ocr_adjudications', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_ocr_adjudications_surface_id'), 'ocr_adjudications', ['surface_id'], unique=False)
    op.create_index(op.f('ix_ocr_adjudications_ocr_run_id'), 'ocr_adjudications', ['ocr_run_id'], unique=False)
    op.create_index(op.f('ix_ocr_adjudications_ocr_region_id'), 'ocr_adjudications', ['ocr_region_id'], unique=False)
    op.create_index(op.f('ix_ocr_adjudications_status'), 'ocr_adjudications', ['status'], unique=False)
    op.create_index(op.f('ix_ocr_adjudications_is_active'), 'ocr_adjudications', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ocr_adjudications_is_active'), table_name='ocr_adjudications')
    op.drop_index(op.f('ix_ocr_adjudications_status'), table_name='ocr_adjudications')
    op.drop_index(op.f('ix_ocr_adjudications_ocr_region_id'), table_name='ocr_adjudications')
    op.drop_index(op.f('ix_ocr_adjudications_ocr_run_id'), table_name='ocr_adjudications')
    op.drop_index(op.f('ix_ocr_adjudications_surface_id'), table_name='ocr_adjudications')
    op.drop_index(op.f('ix_ocr_adjudications_inspection_id'), table_name='ocr_adjudications')
    op.drop_table('ocr_adjudications')
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute("DROP TYPE IF EXISTS correctiontype")
