"""claim error codes table and error_code column on claims

Revision ID: 0033
Revises: 0032
Create Date: 2026-06-05
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "claim_error_codes",
        sa.Column("code", sa.String(20), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("risk", sa.Text(), nullable=False),
        sa.Column("fix_instructions", sa.Text(), nullable=False),
        sa.Column("is_custom", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="public",
    )
    op.execute("ALTER TABLE public.claim_error_codes ENABLE ROW LEVEL SECURITY")

    # Seed the 4 predefined codes
    op.execute("""
        INSERT INTO public.claim_error_codes (code, title, description, risk, fix_instructions) VALUES
        (
            'MOD-U8',
            'Modifier Conflict',
            'You billed for Labor & Delivery (T1033) but did not include the U8 modifier.',
            'Instant claim rejection by PA Medicaid.',
            'Go back to your physical Handbook. Ensure the U8 box is clearly marked. Re-scan the page. The AI will detect the change and clear the flag.'
        ),
        (
            'SIG-MISS',
            'Missing Signature',
            'The AI cannot detect a signature in the Provider or Client box.',
            'Compliance Red Flag. Unsigned visits are considered fraudulent during a state audit.',
            'Ensure you are using dark blue or black ink. If the signature is present but not detected, adjust your lighting to remove shadows and re-scan.'
        ),
        (
            'DT-RANGE',
            'Date Invalid',
            'The Date of Service is either in the future or exceeds the 365-day timely filing limit.',
            'Non-reimbursable claim.',
            'Check your handwriting. Is your "7" being read as a "1"? Use Block Numbers and re-verify the date in the Edit screen.'
        ),
        (
            'DUP-CLAIM',
            'Potential Duplicate',
            'This Client ID and Date of Service already exist in your Master Vault.',
            'Duplicate billing triggers a fraud investigation.',
            'Verify if this is a follow-up visit on the same day. If so, apply the appropriate U7 (Second Visit) modifier in the App settings.'
        )
    """)

    op.add_column(
        "claims",
        sa.Column(
            "error_code",
            sa.String(20),
            sa.ForeignKey("public.claim_error_codes.code", ondelete="SET NULL"),
            nullable=True,
        ),
        schema="public",
    )
    op.add_column(
        "claims",
        sa.Column("resubmit_count", sa.Integer(), server_default="0", nullable=False),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("claims", "resubmit_count", schema="public")
    op.drop_column("claims", "error_code", schema="public")
    op.drop_table("claim_error_codes", schema="public")
