"""Add source_image_path columns for document scanning

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("soap_notes", sa.Column("source_image_path", sa.Text, nullable=True), schema="public")
    op.add_column("prenatal_postnatal_logs", sa.Column("source_image_path", sa.Text, nullable=True), schema="public")
    op.add_column("birth_logs", sa.Column("source_image_path", sa.Text, nullable=True), schema="public")
    op.add_column("patients", sa.Column("medicaid_card_image_path", sa.Text, nullable=True), schema="public")


def downgrade() -> None:
    op.drop_column("patients", "medicaid_card_image_path", schema="public")
    op.drop_column("birth_logs", "source_image_path", schema="public")
    op.drop_column("prenatal_postnatal_logs", "source_image_path", schema="public")
    op.drop_column("soap_notes", "source_image_path", schema="public")
