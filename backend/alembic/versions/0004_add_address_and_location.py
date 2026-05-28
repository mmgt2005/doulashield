"""Add address/location to patients and start-visit fields to visits

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("address", sa.Text, nullable=True), schema="public")
    op.add_column("patients", sa.Column("latitude", sa.Double, nullable=True), schema="public")
    op.add_column("patients", sa.Column("longitude", sa.Double, nullable=True), schema="public")

    op.add_column("visits", sa.Column("visit_started_at", sa.DateTime(timezone=True), nullable=True), schema="public")
    op.add_column("visits", sa.Column("provider_latitude", sa.Double, nullable=True), schema="public")
    op.add_column("visits", sa.Column("provider_longitude", sa.Double, nullable=True), schema="public")


def downgrade() -> None:
    op.drop_column("visits", "provider_longitude", schema="public")
    op.drop_column("visits", "provider_latitude", schema="public")
    op.drop_column("visits", "visit_started_at", schema="public")
    op.drop_column("patients", "longitude", schema="public")
    op.drop_column("patients", "latitude", schema="public")
    op.drop_column("patients", "address", schema="public")
