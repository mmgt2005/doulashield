# DoulaShield Changelog

All notable changes to this project are documented here.

---

## [Unreleased]

### Added
- **Image OCR scanning** — providers can photograph Medicaid cards and handwritten handbook pages; Claude Haiku 4.5 extracts structured data and pre-fills forms for review before saving
- **Document storage** — scanned images are stored in Supabase Storage (`client-documents` bucket, private) and linked to each record for HIPAA audit documentation
- **`GET /ocr/image`** — returns a 60-second signed URL for stored images; access is audited
- **Mobile-first responsive layout** — hamburger drawer navigation on phones/tablets; side-by-side sidebar on desktop (≥1024px)
- **Responsive form fixes** — birth log and prenatal log forms stack vertically on mobile

### Changed
- `Patient`, `SOAPNote`, `PrenatalPostnatalLog`, `BirthLog` models and schemas updated to store `source_image_path` / `medicaid_card_image_path`
- App layout `p-6` padding reduced to `p-4` on mobile

### Infrastructure
- Add `ANTHROPIC_API_KEY` to Railway Variables
- Create `client-documents` private bucket in Supabase Storage
- Run migration 0002 to add image path columns

---

## [2026-05-28] — Initial deployment

### Added
- HIPAA-compliant FastAPI backend deployed to Railway
- Next.js 15 frontend deployed to Vercel
- Supabase PostgreSQL database with Row Level Security
- JWT authentication with bcrypt password hashing
- TOTP-based MFA setup flow
- Role-based access control (provider / admin)
- Fernet encryption for Medicaid ID field
- Immutable audit log (PostgreSQL rules block UPDATE/DELETE)
- Rate limiting on login endpoint (10 req/min via slowapi + Redis)
- Session timeout: 15-minute inactivity timer with 60-second warning modal
- Access tokens stored in memory (Zustand), never localStorage
- Security headers: HSTS, CSP, X-Frame-Options
- Patient CRUD with soft-delete (admin only)
- SOAP notes (create, list, update)
- Prenatal / postnatal log entries (immutable after creation)
- Birth log entries (immutable after creation)
- Admin: user management, audit log viewer
- Medicaid ID available only via separate privileged endpoint with dedicated audit entry
- Alembic migration 0001: initial schema with all PHI tables and RLS policies
