"""Add enrollment_services, enrollment_tasks, enrollment_documents tables

Revision ID: 0044
Revises: 0043
Create Date: 2026-06-26
"""
from __future__ import annotations

from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.enrollment_services (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            created_by UUID REFERENCES public.users(id),
            pcb_pathway VARCHAR(30),
            status VARCHAR(30) NOT NULL DEFAULT 'in_progress',
            intake_data JSONB,
            pcb_cert_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_enrollment_services_provider_id "
        "ON public.enrollment_services(provider_id)"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS public.enrollment_tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            service_id UUID NOT NULL REFERENCES public.enrollment_services(id) ON DELETE CASCADE,
            task_key VARCHAR(50) NOT NULL,
            required_pathway VARCHAR(30) NOT NULL DEFAULT 'all',
            label TEXT NOT NULL,
            description TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'not_started',
            task_data JSONB,
            notes TEXT,
            sort_order INT NOT NULL DEFAULT 0,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_enrollment_tasks_service_id "
        "ON public.enrollment_tasks(service_id)"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS public.enrollment_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            service_id UUID NOT NULL REFERENCES public.enrollment_services(id) ON DELETE CASCADE,
            task_id UUID REFERENCES public.enrollment_tasks(id),
            uploaded_by UUID REFERENCES public.users(id),
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            document_type VARCHAR(50),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_enrollment_documents_service_id "
        "ON public.enrollment_documents(service_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_enrollment_documents_task_id "
        "ON public.enrollment_documents(task_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.enrollment_documents")
    op.execute("DROP TABLE IF EXISTS public.enrollment_tasks")
    op.execute("DROP TABLE IF EXISTS public.enrollment_services")
