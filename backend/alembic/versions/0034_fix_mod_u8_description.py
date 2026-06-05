"""fix MOD-U8 error code: description incorrectly referenced T1033 Labor

Revision ID: 0034
Revises: 0033
Create Date: 2026-06-05
"""
from __future__ import annotations

from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE public.claim_error_codes
        SET
            description     = 'Missing or incorrect modifier. Most often: U8 modifier absent on a postnatal visit (T1032-U8), or a modifier present on a Labor & Delivery claim (T1033 requires no modifier).',
            fix_instructions = 'Check the billing code for this visit type. Postnatal visits (T1032) require the U8 modifier. Labor (T1033) requires no modifier. Crisis/bereavement (T1032) requires U9. Correct the modifier in the claim section and resubmit.'
        WHERE code = 'MOD-U8'
          AND is_custom = false
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE public.claim_error_codes
        SET
            description     = 'You billed for Labor & Delivery (T1033) but did not include the U8 modifier.',
            fix_instructions = 'Go back to your physical Handbook. Ensure the U8 box is clearly marked. Re-scan the page. The AI will detect the change and clear the flag.'
        WHERE code = 'MOD-U8'
          AND is_custom = false
    """)
