"""Initial Phase 1 schema with PostGIS, enums, tables, and indexes

Revision ID: 001_initial_phase1_schema
Revises: 
Create Date: 2026-10-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geography

# revision identifiers, used by Alembic.
revision: str = '001_initial_phase1_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable PostGIS Extension if on PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 2. Enums
    user_role_enum = sa.Enum('CUSTOMER', 'SHOP_OWNER', 'ADMIN', name='user_role')
    print_job_status_enum = sa.Enum(
        'CREATED', 'WAITING', 'PRINTING', 'COMPLETED', 'CANCELLED', 'EXPIRED', 'FAILED',
        name='print_job_status'
    )

    # 3. Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('role', user_role_enum, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 4. Shops table
    loc_col = (
        sa.Column('location', Geography(geometry_type='POINT', srid=4326), nullable=False)
        if bind.dialect.name == "postgresql"
        else sa.Column('location', sa.String(255), nullable=False)
    )

    op.create_table(
        'shops',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('owner_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        loc_col,
        sa.Column('qr_token', sa.Uuid(), nullable=False),
        sa.Column('is_open', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_id'),
        sa.UniqueConstraint('qr_token')
    )
    op.create_index('ix_shops_qr_token', 'shops', ['qr_token'], unique=True)
    if bind.dialect.name == "postgresql":
        op.create_index('idx_shops_location', 'shops', ['location'], postgresql_using='gist')

    # 5. Documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('owner_id', sa.Uuid(), nullable=False),
        sa.Column('job_id', sa.Uuid(), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('storage_key', sa.Text(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('checksum_sha256', sa.CHAR(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('storage_key'),
        sa.UniqueConstraint('job_id')
    )
    op.create_index('idx_documents_owner', 'documents', ['owner_id'])

    # 6. Print Jobs table
    op.create_table(
        'print_jobs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=False),
        sa.Column('shop_id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.Column('copy_count', sa.SmallInteger(), nullable=False),
        sa.Column('status', print_job_status_enum, nullable=False),
        sa.Column('pickup_code', sa.String(length=6), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shop_id'], ['shops.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id')
    )
    op.create_index('idx_print_jobs_customer', 'print_jobs', ['customer_id'])
    op.create_index('idx_print_jobs_shop_status', 'print_jobs', ['shop_id', 'status'])
    op.create_index('idx_print_jobs_expires', 'print_jobs', ['expires_at'])

    # Add deferred Foreign Key from documents.job_id -> print_jobs.id
    op.create_foreign_key(
        'fk_documents_job_id',
        'documents',
        'print_jobs',
        ['job_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # 7. Audit Logs table
    ip_col = (
        sa.Column('ip_address', postgresql.INET(), nullable=True)
        if bind.dialect.name == "postgresql"
        else sa.Column('ip_address', sa.String(45), nullable=True)
    )
    meta_col = (
        sa.Column('metadata', postgresql.JSONB(), nullable=True)
        if bind.dialect.name == "postgresql"
        else sa.Column('metadata', sa.JSON(), nullable=True)
    )

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('actor_id', sa.Uuid(), nullable=True),
        sa.Column('job_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        ip_col,
        meta_col,
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['job_id'], ['print_jobs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_logs_job', 'audit_logs', ['job_id'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_constraint('fk_documents_job_id', 'documents', type_='foreignkey')
    op.drop_table('print_jobs')
    op.drop_table('documents')
    op.drop_table('shops')
    op.drop_table('users')

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS print_job_status;")
        op.execute("DROP TYPE IF EXISTS user_role;")
