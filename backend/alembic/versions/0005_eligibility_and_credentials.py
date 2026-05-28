"""Add eligibility fields to patients and Availity credential fields to users

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("date_of_birth", sa.Date, nullable=True), schema="public")
    op.add_column("patients", sa.Column("eligibility_status", sa.String(50), nullable=True), schema="public")
    op.add_column("patients", sa.Column("eligibility_checked_at", sa.DateTime(timezone=True), nullable=True), schema="public")

    op.add_column("users", sa.Column("npi", sa.String(10), nullable=True), schema="public")
    op.add_column("users", sa.Column("availity_client_id_encrypted", sa.Text, nullable=True), schema="public")
    op.add_column("users", sa.Column("availity_client_secret_encrypted", sa.Text, nullable=True), schema="public")


def downgrade() -> None:
    op.drop_column("users", "availity_client_secret_encrypted", schema="public")
    op.drop_column("users", "availity_client_id_encrypted", schema="public")
    op.drop_column("users", "npi", schema="public")

    op.drop_column("patients", "eligibility_checked_at", schema="public")
    op.drop_column("patients", "eligibility_status", schema="public")
    op.drop_column("patients", "date_of_birth", schema="public")
