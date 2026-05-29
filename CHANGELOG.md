# DoulaShield Changelog

All notable changes to this project are documented here.

Format: `## [version] — YYYY-MM-DD`. Changes accumulate under `[Unreleased]`; on each release that section is renamed to the new version and a fresh `[Unreleased]` stub is added above it.

Semver guide — **patch** (1.0.x): bug fixes, infra; **minor** (1.x.0): new features; **major** (x.0.0): breaking auth/schema changes.

---

## [Unreleased]

### Fixed
- Migration 0003: replaced `CREATE TYPE IF NOT EXISTS` (PostgreSQL 16+ only) with a `DO $$ BEGIN IF NOT EXISTS … END $$` pg_type check — Supabase runs PostgreSQL 15 which does not support the `IF NOT EXISTS` clause on `CREATE TYPE`
- ZipZign error messages now include the actual HTTP status and response body (401 → "API key rejected", 400 → ZipZign's error detail) instead of a generic message, making diagnosis possible without reading Railway logs

---

## [1.0.0] — 2026-05-29

First production release.

### Infrastructure
- HIPAA-compliant FastAPI backend on Railway; Next.js 15 frontend on Vercel; Supabase PostgreSQL with Row Level Security
- JWT auth (15-min access tokens in memory, 7-day refresh cookie); TOTP MFA; bcrypt(12) passwords
- Fernet symmetric encryption for Medicaid ID and provider credentials
- Immutable audit log (PostgreSQL rules block UPDATE/DELETE on `audit_logs`)
- Rate limiting on login (10 req/min, slowapi + Redis); session timeout 15 min with 60-sec modal
- Security headers: HSTS, CSP, X-Frame-Options; CORS locked to single origin
- Alembic migrations (0001–0009) made idempotent with `IF NOT EXISTS` guards
- Version number exposed in `GET /health` response and sidebar footer

### Patient & Visit Management
- Patient CRUD with soft-delete (admin only); Fernet-encrypted name and Medicaid ID
- 13-slot structured visit tracker (6 prenatal, 1 labor, 6 postnatal) with SOAP notes per visit
- Client address with Nominatim geocoding, address autocomplete, and geocode-verified indicator
- Date of birth field; eligibility status display
- Email field on client profile; `PATCH /patients/{id}` for profile updates

### Scanning & AI
- Image OCR via Claude Haiku 4.5 — Medicaid card and handwritten handbook page scanning; images stored in Supabase Storage (private bucket)
- MCO name normalised to 7 canonical Pennsylvania MCO names on scan
- AI-powered SOAP note clinical translation (plain language → Medicaid audit-ready clinical documentation); provider review required before saving

### Integibility & Claims (Availity)
- Per-provider Availity OAuth credentials (Fernet-encrypted); Redis token cache (55-min TTL)
- Eligibility verification (270/271); claims (837P); prior authorizations (278); remittance advice (835); document submission; provider directory search

### Telehealth & Signatures
- Per-visit location type toggle (in-person / telehealth); alternate location field when provider is >500 ft from client
- Telehealth meeting link in Settings; "Start Telehealth" opens doxy.me and fires a `mailto:` with the room link to the client
- MA 91 Pennsylvania Medicaid certification: canvas signature pad (in-person) and ZipZign e-signature (telehealth)
- ZipZign API key stored as admin-only shared credential

### Bug Fixes
- Added `psycopg2-binary` to fix Alembic startup crash on Railway
- Added `sslmode=require` to Alembic psycopg2 connection URL (Supabase requires SSL)
- Fixed ZipZign base URL (`api.zipzign.com` → `zipzign.com`), endpoint (`/api/documents`), request body, webhook event names, metadata parsing, and HMAC signature verification

---

## [2026-05-29] — Fix ZipZign API integration against live API docs

### Fixed
- **Correct endpoint**: changed from `POST {base}/requests` to `POST https://zipzign.com/api/documents`
- **Correct base URL**: `ZIPZIGN_BASE_URL` default changed from `https://zipzign.com/api/v1` to `https://zipzign.com`
- **Correct request body**: removed non-existent `document` wrapper, `title`, `sender`, `webhook_url` fields; replaced with `"type": "signable"` at top level; removed invalid `"role"` field on signers; added `notify_emails` so provider is emailed when patient signs; added patient-facing `message` in the invite email
- **Correct webhook event name**: handler now checks for `"document.signed"` (was `"signed"`); removed `"declined"` handler (ZipZign has no such event)
- **Correct webhook metadata parsing**: `metadata` is nested under `payload["document"]` as an array of `{key, value}` dicts, not a top-level flat dict
- **Correct webhook signature verification**: replaced naive string comparison with proper HMAC-SHA256 verification using `t=<unix_ms>,v1=<hex>` Stripe-style format; rejects events older than 5 minutes
- **Setup note**: ZipZign webhook URL (`https://{BACKEND_URL}/api/v1/signatures/webhook`) must be registered once in the ZipZign dashboard; the signing secret returned at registration goes into `ZIPZIGN_WEBHOOK_SECRET` env var

---

## [2026-05-29] — Fix Railway healthcheck: add sslmode=require for Alembic psycopg2 connection

### Fixed
- Added `sslmode=require` to the psycopg2 connection URL in `backend/alembic/env.py` when not already present — Supabase rejects all PostgreSQL connections without SSL; psycopg2 does not add it automatically, causing `alembic upgrade head` to hang/fail and preventing uvicorn from starting

---

## [2026-05-29] — Make all Alembic migrations idempotent

### Fixed
- Rewrote `upgrade()` in migrations 0002–0009 to use raw SQL with `ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`, `CREATE TYPE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, and `DO $$` guards for `CREATE POLICY` — prevents crashes when the DB schema is already ahead of Alembic's version table (which happens when SQL was applied manually but Alembic's `alembic_version` row was not updated)
- Also rewrote `downgrade()` functions to use `DROP … IF EXISTS` for symmetry

---

## [2026-05-29] — Fix Railway startup crash: add psycopg2-binary

### Fixed
- Added `psycopg2-binary==2.9.10` to `backend/requirements.txt` — Alembic's synchronous `create_engine` uses the `postgresql://` dialect which requires psycopg2; without it the `alembic upgrade head` step in the Dockerfile CMD failed immediately, preventing the server from ever starting

---

## [2026-05-29] — Client Email Field & Telehealth Room Link via Email

### Fixed
- ZipZign base URL corrected from non-existent `api.zipzign.com` to `zipzign.com/api/v1`; now configurable via `ZIPZIGN_BASE_URL` env var

### Added
- **Email field on client profile** — optional email address stored per client; shown in the profile header and editable via "Edit profile"
- **Email field on new client form** — providers can enter a client email when creating a new record
- **Telehealth room link sent to client automatically** — clicking "Start Telehealth" now opens doxy.me (so the provider can log in and start their room) and opens the provider's default email client with a pre-filled message containing the room link for the client to join; no backend email service required
- **No-email warning** — if no email is on file for the client, the telehealth panel shows an amber note prompting the provider to add one
- **MA 91 email pre-filled** — the patient email field in the MA 91 telehealth e-signature section is now pre-populated from the stored client email
- Migration 0009: adds nullable `email` (TEXT) column to `patients` table

---

## [2026-05-29] — ZipZign API Key Moved to Admin-Only Shared Credential

### Changed
- **ZipZign API key is now a single shared credential** — only the admin user enters it in Settings; all providers use the same key automatically. Per-provider `zipzign_api_key_encrypted` columns remain in the DB but are no longer written or read for non-admin users
- **Settings page** — ZipZign API key input is now hidden for provider-role users; the "✓ Connected" badge and contact email field remain visible for all roles
- `signature_service.py` — `request_telehealth_signature` now queries for any admin user with a configured key instead of using the requesting provider's key; error message updated accordingly
- `eligibility_service.py` — `zipzign_connected` in `ProviderSettingsRead` now reflects whether the admin has a key configured, not the current user's own key (applied to both `get_provider_settings` and `update_provider_settings`)

---

## [2026-05-29] — MA 91 Encounter Form Certification Signature

### Added
- **MA 91 signature section** on every visit form — displays the official Pennsylvania Medicaid certification text and collects patient signature before billing
- **In-person canvas signature pad** — patient draws signature directly on provider's phone/tablet using `signature_pad`; PNG saved to Supabase Storage (`clients/{patient_id}/ma91-{visit_id}.png`)
- **Telehealth e-signature via ZipZign** — generates a hosted MA 91 PDF from HTML, emails it to the patient; patient signs without creating an account; ZipZign webhook updates visit `ma91_status` to `signed` or `declined`
- **MA 91 status badges** — green "✓ Signed", amber "⏳ Signature request sent", red "✗ Patient declined" shown on visit form
- **Contact email + ZipZign API key** in Provider Settings — contact email used as From address; API key Fernet-encrypted at rest; "Connected ✓" badge shown when configured
- `POST /patients/{id}/visits/{type}/sign-in-person` — saves base64 PNG canvas signature to Supabase Storage; audits `SIGN_MA91_IN_PERSON`
- `POST /patients/{id}/visits/{type}/request-telehealth-signature` — calls ZipZign API to send e-signature request; audits `REQUEST_TELEHEALTH_MA91`
- `POST /signatures/webhook` — receives ZipZign signed/declined events; verifies shared secret; audits `MA91_WEBHOOK_RECEIVED`
- `signature_service.py` — handles storage upload, ZipZign HTTP call, webhook processing, and MA 91 HTML generation
- Migration 0008: adds `ma91_signed_at`, `ma91_signature_path`, `ma91_signed_by_name`, `ma91_zipzign_request_id`, `ma91_status` to `visits`; adds `contact_email`, `zipzign_api_key_encrypted` to `users`
- `BACKEND_URL` and `ZIPZIGN_WEBHOOK_SECRET` config vars for webhook verification

---

## [2026-05-28] — AI-Powered SOAP Note Clinical Translation

### Added
- **"Draft SOAP Note" button** on visit form — sends plain-language SOAP fields to Claude Haiku 4.5, which translates them into professional clinical documentation meeting Pennsylvania Medicaid Type 13 audit standards (T1032/T1033)
- **Guided placeholder text** on each SOAP textarea: specific questions prompt doulas on what to write (e.g., "How is the client feeling today? Did she report any specific concerns?")
- **AI draft review panel** — translated text is shown inline for provider review; "Apply to Form" populates the textareas; "Dismiss" discards without applying. No AI output is saved without provider review.
- `POST /ocr/soap-translate` endpoint — accepts the 4 SOAP fields, returns clinical translations, emits `TRANSLATE_SOAP_NOTE` audit log entry
- `translate_soap()` / `_run_soap_translate()` in `ocr_service.py` — same `asyncio.to_thread` pattern as OCR; `max_tokens=2048`; prompt enforces no hallucination, Z-codes only, T1032/T1033 justification

---

## [2026-05-28] — Visit Location Type: In-Person vs Telehealth

### Added
- **Location type toggle** on visit form — "In Person" or "Telehealth" buttons at top of each visit
- **Telehealth panel** — when Telehealth is selected, shows provider's configured meeting link; "Start Telehealth" opens link in new tab and records `visit_started_at`; prompts to configure link in Settings if not set
- **Alternate location field** — when provider is >500 ft from client on an in-person visit, amber warning now includes a text field to describe the actual meeting location (e.g., clinic, hospital); saved as `alternate_location`
- **Location icons on visit slot cards** — blue video icon for telehealth visits, grey pin icon for in-person; older records without `location_type` show no icon
- **Telehealth meeting link in Settings** — new "Telehealth" section; platform-agnostic URL field (Doxy.me recommended: free, HIPAA-compliant, no patient download required)

### Backend
- Migration 0007: adds `location_type` (varchar 20) and `alternate_location` (text) to `visits`; `telehealth_link` (text) to `users`
- `ProviderSettingsUpdate` / `ProviderSettingsRead` schemas include `telehealth_link`
- `eligibility_service.py` `get_provider_settings` / `update_provider_settings` handle `telehealth_link`

---

## [2026-05-28] — Availity API Expansion

### Added
- **`AvailityClient`** (`services/availity_client.py`) — shared async HTTP client with per-provider OAuth token caching (55-min Redis TTL); centralises `MCO_PAYER_IDS` mapping; exposes `get()`, `post()`, `post_multipart()`. Replaces duplicated HTTP boilerplate in `eligibility_service.py`.
- **Claims** (`POST /patients/{id}/claims`, `GET /patients/{id}/claims`, `POST /claims/{id}/status-check`) — submits 837P claims to Availity, tracks status; `claims` table with `availity_claim_id`, `status`, `billed_amount`, `paid_amount`, `raw_response`
- **Prior Authorization** (`POST /patients/{id}/prior-authorizations`, `GET`, `POST /{id}/status-check`) — submits and tracks 278 prior auth requests; `prior_authorizations` table
- **Remittance Advice** (`POST /remittances/fetch`, `GET /remittances`) — fetches 835 EOBs from Availity; upserts by `availity_remit_id`; `remittances` table
- **Document Submission** (`POST /documents/submit`) — multipart upload to Availity; supports PDF, JPEG, PNG, XML up to 10 MB
- **Provider Directory** (`GET /directory/search`) — searches Availity provider directory; no DB persistence; audits `DIRECTORY_SEARCH`
- Migration 0006: creates `claims`, `prior_authorizations`, `remittances` tables with RLS

### Changed
- `eligibility_service.py` now instantiates `AvailityClient` instead of managing its own HTTP/token logic

---

## [2026-05-28] — Date of Birth, Provider Settings & Eligibility Verification

### Added
- **Date of birth** field on patient profile — displayed in header, editable via "Edit profile", auto-populated from Medicaid card and prenatal page OCR scans
- **Eligibility check** on client profile — "Check eligibility" button calls Availity 270/271 API; shows green "Active" or red "Inactive" badge + last-checked date; "Re-check" refreshes
- **Provider Settings page** (`/settings`) — NPI field, Availity Client ID / Client Secret (write-only; shows "Connected ✓" badge), saves to `PATCH /api/v1/auth/me/provider-settings`
- `POST /patients/{id}/eligibility-check` endpoint — decrypts provider credentials, calls Availity, saves `eligibility_status` + `eligibility_checked_at` on patient, audits `CHECK_ELIGIBILITY`
- Migration 0005: adds `date_of_birth`, `eligibility_status`, `eligibility_checked_at` to `patients`; adds `npi`, `availity_client_id_encrypted`, `availity_client_secret_encrypted` to `users`

### Changed
- Medicaid card OCR prompt now extracts `date_of_birth`
- Prenatal page OCR prompt now extracts `date_of_birth` from page header

---

## [2026-05-28] — Medicaid Card Scanner in Edit Profile

### Added
- `ImageUploadScanner` added to the "Edit profile" inline form — scan a replacement Medicaid card to pre-fill name, MCO, address, and update `medicaid_card_image_path`

---

## [2026-05-28] — MCO Name Normalization

### Changed
- Medicaid card OCR prompt normalizes scanned MCO names to the 7 canonical Pennsylvania MCO names (AmeriHealth Caritas, UPMC For You, Geisinger Health Plan, Health Partners Plans, Aetna Better Health, UnitedHealthcare Community Plan, Highmark Wholecare) plus FFS. Maps known aliases: Keystone First → AmeriHealth Caritas, Gateway Health → Highmark Wholecare, HPP → Health Partners Plans.

---

## [2026-05-28] — Camera-Only Mobile Scan Button

### Changed
- `ImageUploadScanner` now uses `capture="environment"` on the file input — opens rear camera directly on mobile (iOS/Android) instead of showing the file picker. Desktop behavior unchanged. Button label updated to "Take photo".

---

## [2026-05-28] — Geocode Verified Indicator

### Added
- Green map-pin icon appears inside address input fields when the address has been geocoded (lat/lng confirmed)
- Green map-pin icon shown inline before the client's address in the profile header when coordinates are on file
- `geocoded` prop added to `AddressAutocomplete` component

---

## [2026-05-28] — Address Autocomplete

### Added
- `AddressAutocomplete` component — debounced Nominatim suggestions dropdown (≥3 chars, 400 ms delay, up to 5 results); `onMouseDown` selection fires before blur; click-outside closes dropdown
- `suggestAddresses()` in `lib/geo.ts` — queries Nominatim, returns `{ label, lat, lng }[]`
- Address fields on new-client form and edit-profile form now use autocomplete; selecting a suggestion sets `latitude`/`longitude` immediately; `geocodeAddress()` fallback still runs on submit if no suggestion was chosen

### Fixed
- CSP updated to allow `nominatim.openstreetmap.org`
- Address field properly registered with React Hook Form in edit profile

---

## [2026-05-28] — Start Visit, Client Address & Provider Location

### Added
- **Address field** on patient profile — stored plaintext; geocoded to lat/lng via Nominatim on save
- **"Edit profile" inline form** on client detail page — edit name, MCO, DOB, and address without leaving the page
- **"Start Visit" panel** on visit form — records provider GPS coordinates and timestamp; immediately PUTs `visit_started_at`, `provider_latitude`, `provider_longitude` to the visit record
- **Distance check** — Haversine distance between provider and client address shown on green banner; amber warning if >500 ft
- `haversineFeet()` and `geocodeAddress()` in `lib/geo.ts`
- Migration 0004: adds `address`, `latitude`, `longitude` to `patients`; adds `visit_started_at`, `provider_latitude`, `provider_longitude` to `visits`

### Fixed
- CORS allowlist updated to include `PUT` method for visits upsert

---

## [2026-05-28] — Structured 13-Visit Tracker

### Added
- **13-slot visit grid** replaces 3-card layout on client overview — 6 prenatal, 1 labor, 6 postnatal slots; completed slots show checkmark + visit date; pending slots are clearly actionable
- **Unified visit form** (`/clients/[id]/visits/[type]`) — single page handles prenatal, postnatal (entry + SOAP), and labor (birth details + SOAP) based on `slot.isLabor`
- `VISIT_SLOTS` / `VISIT_GROUPS` / `getSlotConfig()` in `lib/visit-config.ts` — single source of truth for visit metadata and OCR page type mapping
- `visits` table — `UNIQUE(patient_id, visit_type)` enforces one record per slot; PostgreSQL upsert via `INSERT ... ON CONFLICT DO UPDATE`
- `GET /patients/{id}/visits`, `GET /patients/{id}/visits/{type}`, `PUT /patients/{id}/visits/{type}` endpoints
- Migration 0003: creates `public.visits` table with RLS

---

## [2026-05-28] — Image OCR Scanning & Mobile Layout

### Added
- **Image OCR scanning** — providers photograph Medicaid cards and handwritten handbook pages; Claude Haiku 4.5 extracts structured data and pre-fills forms for review before saving
- **Document storage** — scanned images stored in Supabase Storage (`client-documents` bucket, private) and linked to each record for HIPAA audit documentation
- **`GET /ocr/image`** — returns a 60-second signed URL for stored images; access audited
- **Mobile-first responsive layout** — hamburger drawer navigation on phones/tablets; side-by-side sidebar on desktop (≥1024px)
- **Responsive form fixes** — birth log and prenatal log forms stack vertically on mobile
- `ImageUploadScanner` reusable component — multipart upload with inline spinner; no image preview (avoids rendering PHI in browser)
- Migration 0002: adds `source_image_path` to `soap_notes`, `prenatal_postnatal_logs`, `birth_logs`; adds `medicaid_card_image_path` to `patients`

### Infrastructure
- Add `ANTHROPIC_API_KEY` to Railway Variables
- Create `client-documents` private bucket in Supabase Storage

---

## [2026-05-28] — Initial Deployment

### Added
- HIPAA-compliant FastAPI backend deployed to Railway
- Next.js 15 frontend deployed to Vercel
- Supabase PostgreSQL database with Row Level Security
- JWT authentication with bcrypt password hashing
- TOTP-based MFA setup and enforcement
- Role-based access control (provider / admin)
- Fernet symmetric encryption for Medicaid ID field
- Immutable audit log (PostgreSQL rules block UPDATE/DELETE)
- Rate limiting on login endpoint (10 req/min via slowapi + Redis)
- Session timeout: 15-minute inactivity timer with 60-second warning modal
- Access tokens stored in memory (Zustand), never localStorage
- Security headers: HSTS, CSP, X-Frame-Options
- Patient CRUD with soft-delete (admin only)
- SOAP notes (create, list, update)
- Prenatal / postnatal log entries
- Birth log entries
- Admin: user management, audit log viewer
- Medicaid ID available only via separate privileged endpoint with dedicated audit entry
- Migration 0001: initial schema with all PHI tables and RLS policies
