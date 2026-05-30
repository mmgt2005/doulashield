# DoulaShield Changelog

All notable changes to this project are documented here.

Format: `## [version] — YYYY-MM-DD`. Changes accumulate under `[Unreleased]`; on each release that section is renamed to the new version and a fresh `[Unreleased]` stub is added above it.

Semver guide — **patch** (1.0.x): bug fixes, infra; **minor** (1.x.0): new features; **major** (x.0.0): breaking auth/schema changes.

---

## [Unreleased]

### Added
- **MCO-Aware Claim Submission Routing**: claim submission now branches by MCO instead of routing everything through Availity; `MCO_SUBMISSION_CHANNEL` in `billing_constants.py` maps each of the 8 PA MCOs to one of three channels — `availity` (AmeriHealth Caritas, Keystone First, Geisinger, Highmark Wholecare, Aetna Better Health), `uhc` (UnitedHealthcare Community Plan — direct OAuth2 PKCE REST API), or `manual` (UPMC For You, Health Partners Plans, FFS — clearinghouse-only); the claims service raises a descriptive error for manual MCOs so providers know to download the CMS 1500 and use the payer portal; for UHC a new `UHCClient` class mirrors `AvailityClient` with OAuth2 PKCE (S256) token caching; `check_claim_status` also routes by channel; migration 0017 adds `uhc_client_id_encrypted` and `uhc_client_secret_encrypted` to the `users` table; Settings page adds a UHC API Credentials section with Client ID / Client Secret inputs and a "Connected ✓" badge; the visit form claim section shows the correct UI per channel: manual MCOs render a "Preview & Download CMS 1500" button plus a portal link (UPMC, HPP, FFS) instead of a submit button; UHC and Availity MCOs show "Submit to UnitedHealthcare" or "Submit to Availity" respectively in the modal; a warning is shown when UHC is the channel but credentials are not yet configured

- **CMS 1500 Block 17b — Referring Provider NPI**: `referring_provider_npi` column added to `patients` table (migration 0016, max 10 chars); same referring doctor applies to all visits for a given patient so it is stored per-patient and reused across all claims; the visit form claim section shows an inline NPI input that auto-saves to the patient record on blur and is pre-populated on every subsequent visit; a warning badge shows when the field is empty since missing Block 17b causes claim rejection; the client profile edit form includes the field as well so it can be corrected outside the visit form; the field is passed through the CMS 1500 PDF generator as `ref_physician` (AcroForm field name, Block 17b) and shown in the preview modal table
- **CMS 1500 Block 23 — Prior Authorization Number**: `prior_auth_number` column added to `visits` table (migration 0016); Geisinger Health Plan requires a prior auth number for reimbursement; the visit form claim section shows a Block 23 input that saves with each visit; the field is passed through the CMS 1500 PDF generator as `prior_auth` (Block 23) and shown in the preview modal table; the Geisinger prior auth input renders with an amber border when the MCO is Geisinger and the field is empty
- **MCO-specific billing warnings in claim section**: a contextual blue info panel appears in the claim section for UPMC For You (30-minute minimum reminder), AmeriHealth Caritas (MA 91 7-year retention reminder), and Geisinger Health Plan (prior auth Block 23 reminder)

### Fixed
- **CMS 1500 PDF embedded preview in modal**: clicking "Preview CMS 1500 & Submit" now fetches the authenticated PDF immediately and renders it in a 520 px iframe inside the modal, above the field summary table; spinner shown while loading; blob URL revoked on modal close to prevent memory leaks; "Download PDF" reuses the already-fetched blob when available; modal widened to `max-w-4xl` to better fit letter-sized layout; `frame-src 'self' blob:` added to the Content-Security-Policy in `next.config.js` so the browser permits `blob:` URLs inside iframes (previously blocked by the `default-src 'self'` fallback with a "This content is blocked" error)
- **CMS 1500 PDF download "Not authenticated" error**: replaced the `<a href>` direct-link approach (which never sends an Authorization header) with a `fetch()`-based download that attaches the Bearer token, converts the response to a blob, and triggers a programmatic download
- **Diagnosis codes showing two values**: `billing_constants.py` and the frontend `VISIT_BILLING` constant now use a single ICD-10 code per visit type — Z32.2 (prenatal), Z39.1 (postnatal), Z33.1 (labor), Z39.2 (crisis/loss) — matching the ICD-10 billing reference; `diag.join(', ')` in the CMS 1500 modal and the claim payload now shows one code
- **Patient city missing from CMS 1500 PDF**: `_parse_address()` in `cms1500_service.py` replaced with a robust parser that handles both the simple "Street, City, ST ZIP" format and the full Nominatim geocoder format ("Street, Neighborhood, City, County, State, ZIP, United States"); state full-name → abbreviation lookup table added so "Pennsylvania" correctly maps to "PA"

### Added
- **PA Medicaid claim submission with CMS 1500 PDF**: visit form now includes a "PA Medicaid Claim" section that shows procedure code, modifier, rate, and diagnosis codes — all auto-determined from visit type via `billing_constants.py` (T1032/U7/$100 prenatal, T1032/U8/$100 postnatal, T1033/$1,000 labor, T1032/U9/$175 crisis/loss); "Preview CMS 1500 & Submit" opens a modal listing all form box values; "Download PDF" generates and downloads the official CMS 1500 (02/12) AcroForm PDF filled with patient, visit, and provider data; "Submit to Availity" posts the claim via `POST /patients/{id}/claims`; after submission a status panel with claim ID and "Refresh status" replaces the submit UI; `GET /patients/{id}/visits/{vt}/cms1500.pdf` endpoint generates the filled PDF server-side using `pypdf` to fill the official blank form's named fields (insurance_type → Medicaid radio, sex, diagnosis1–4, service line dates/POS/CPT/modifier, charge, NPI, taxonomy 374J00000X); audit action `GENERATE_CMS1500` logged on each download
- **Billing constants module** (`backend/app/core/billing_constants.py`): single source of truth for procedure codes, modifiers, rates, default ICD-10 diagnosis codes, and clinical notes per visit type; imported by the claims service, CMS 1500 service, and mirrored in the frontend `VISIT_BILLING` constant
- **Patient gender field**: `patients.gender` column (migration 0015, server_default `'F'`) defaults to Female — appropriate since all doula clients are perinatal patients; editable in the new client form and the edit profile form (select: Female / Male / Unknown); used in CMS 1500 Box 3 sex checkbox and passed through the Availity claim body
- **Crisis / Bereavement Visits section**: client detail page now has a 4th section below postnatal showing "Crisis / Bereavement Visits (N of 2 used this year)"; an "Add Crisis/Loss Visit" button navigates to `crisis_loss_1` or `crisis_loss_2` (hidden once both are used); these visit types are added to the DB check constraint (migration 0015) and to the `VisitType` union and `VISIT_SLOTS` in the frontend; `getPrevSlotInGroup` correctly skips the crisis_loss group (no sequential enforcement)
- **ClaimCreate schema updated**: `visit_type` field drives all billing fields automatically — `billed_amount`, `diagnosis_codes`, and `procedure_codes` are auto-calculated from `billing_constants` if not explicitly overridden; `location_type` maps to place-of-service code 02 (telehealth) or 12 (home)

### Internal
- `backend/app/static/cms1500_blank.pdf`: official CMS 1500 (02/12) blank AcroForm PDF committed to the repo; `pypdf>=4.0.0` added to `requirements.txt`

- **SOAP field helper text always visible**: each SOAP field label now shows its guidance text inline (e.g., "Subjective — How is the client feeling today?…") so the hint remains readable while typing; the "Draft SOAP Note" button is placed immediately beside the "SOAP Note" heading rather than pushed to the far right
- **Forgot / reset password flow**: "Forgot password?" link on the login page opens `/forgot-password` (email input); backend generates a SHA-256-hashed single-use token stored in a new `password_reset_tokens` table (migration 0014) with a 1-hour expiry and sends a reset email via Resend; `/reset-password?token=...` validates the token, enforces existing password complexity rules, updates `password_hash`, and marks the token used; the forgot-password endpoint always returns 200 regardless of whether the email exists (prevents user enumeration); audit entries `REQUEST_PASSWORD_RESET` and `RESET_PASSWORD` logged on each action
- **Admin welcome email fix**: when a new admin account is created via "Create & Send Email", the email subject is now "Welcome to DoulaShield — Your Account Details" (not "...Deposit Link") and the body says "account" instead of "provider account"; achieved by adding a `role` parameter to `send_welcome_and_deposit()` in `email_service.py`
- **Role selector at account creation**: the "Create Account" modal now has a Provider / Admin toggle above the email field; selected role is passed to both the "Create Account Only" and "Create & Send Email" flows; admin accounts automatically skip Stripe deposit link generation; header button relabeled "+ Add User" and modal title updated to "Create Account"
- **Role toggle on admin users page**: each row (except the currently logged-in admin) now has a "Make Admin" / "Make Provider" button that calls `PATCH /api/v1/admin/users/{id}` with the new role; after toggle the row updates immediately and the provider's sidebar navigation changes on their next page load
- **Deactivate / Reactivate on admin users page**: each row (except the current admin) now has a "Deactivate" / "Reactivate" button; deactivated accounts receive a 401 on their next request; self-lockout is prevented by hiding both buttons on the logged-in admin's own row
- **Admin billing exemption**: new accounts created with `role="admin"` automatically receive `deposit_paid=True` and `escrow_balance_remaining=0.00` — admins are never prompted for the $99 deposit or the $400 escrow balance; the Escrow & Billing section on the Settings page is hidden entirely for admin users; existing admin accounts need a one-time SQL update: `UPDATE public.users SET deposit_paid = true, escrow_balance_remaining = 0 WHERE role = 'admin'`
- **Partner revenue split** (`STRIPE_PARTNER_ACCOUNT_ID` / `STRIPE_PARTNER_SHARE`): every deposit and subscription payment is automatically split via Stripe Connect transfers — 35% transferred to Partner B's connected account immediately after each `checkout.session.completed` (deposit) or `invoice.payment_succeeded` (subscription) webhook event; configurable share and account ID via env vars; transfer disabled gracefully when `STRIPE_PARTNER_ACCOUNT_ID` is empty; each transfer produces a `PARTNER_TRANSFER` audit log entry
- **Two-option Create Provider modal**: admin can now choose "Create Account Only" (account created, one-time credential panel shows the temp password for manual sharing) or "Create & Send Email" (existing flow — credentials delivered directly to the provider's inbox, admin never sees the password); both options generate a cryptographically secure 14-char temp password server-side
- **Send Welcome Email** table-row action (`POST /admin/billing/send-welcome-email`): generates a fresh temp password, updates the provider's `password_hash`, optionally creates a Stripe Checkout link, and sends the combined welcome + deposit email; available for any provider where deposit is not yet paid; functions as both a first-time send (for accounts created without email) and a password-reset + re-invite
- **Create Provider + send invite** (`POST /admin/billing/create-and-invite`): admin fills in email and optional full name; backend generates a cryptographically secure 14-char temp password, creates the provider account, generates a Stripe Checkout link (if configured), and sends one combined welcome email containing the login credentials and deposit payment button — the admin never handles or sees the password
- **Change Password** section on the Settings page: providers can update their own password after first login by entering their current password, new password, and confirmation; validated against the existing 12-char complexity rules; `POST /auth/me/change-password` endpoint with `CHANGE_PASSWORD` audit log entry

### Stripe billing integration: escrow agreement sign flow, automated $99 deposit collection, and $39/month subscription management
  - **Backend**: migration 0013 adds billing columns to `users` (`stripe_customer_id`, `escrow_agreed_at/version`, `deposit_paid/at`, `escrow_balance_remaining`, `stripe_subscription_id`, `subscription_status`) and creates `escrow_deductions` table; new `stripe_service`, `email_service`, and `billing` API router
  - **Deposit flow**: admin clicks "Send Deposit Email" → backend creates a Stripe Checkout session with `setup_future_usage=off_session` (saves card for future charges) and `metadata.user_id`, then sends the link via Resend; when the provider pays, `checkout.session.completed` webhook auto-links `stripe_customer_id` and sets `deposit_paid=True` — no manual copy-paste required
  - **Fallback**: "Link Customer ID" modal lets admins manually paste a `cus_…` ID for providers whose deposit was collected outside Stripe (cash/check)
  - **Subscriptions**: "Start Subscription" admin action creates a Stripe recurring subscription that auto-charges the saved card each month; disabled until deposit is paid
  - **Escrow deductions**: each new remittance automatically triggers an off-session Stripe charge — 50% of the remittance amount (or full remaining balance if remittance ≥ $400); deduction recorded in `escrow_deductions` table
  - **Webhook handler** (`POST /billing/webhook`): handles `checkout.session.completed`, `customer.subscription.*`, `invoice.payment_failed`, and `payment_intent.payment_failed`; all events produce audit log entries
  - **Settings page**: scrollable escrow agreement text with checkbox + "Sign Agreement" button; after signing, shows balance remaining, clearance status, and subscription badge
  - **Admin users page**: new Deposit / Balance / Subscription columns; per-row "Send Deposit Email", "Link Customer ID", and "Start Subscription" action buttons with green/amber/gray status badges

### Internal
- `frontend/tsconfig.json` and `frontend/next-env.d.ts` updated by `next build` (mandatory: jsx → react-jsx, target → ES2017, added `.next/dev/types` include path); subsequent build updated routes import path in `next-env.d.ts`

### Added
- PA HealthChoices zone and multi-county selector in Provider Settings — providers select their primary geographic zone (SE / SW / LC / NE / NW), then check one or more counties they serve within that zone from a scrollable checkbox list; an info panel shows the active MCOs for the selected zone; zone and counties list are persisted to the user profile (migrations 0011, 0012) as a JSON array in a TEXT column
- Visit date auto-populates from the start timestamp when "Start Visit" or "Start Telehealth" is tapped, eliminating the need to type the date manually; also falls back to the stored `visit_started_at` when reloading a visit that was started but never form-saved
- Sequential visit enforcement: within prenatal and postnatal groups, a provider cannot navigate to the next visit until the previous one has a recorded `visit_ended_at`; blocked slots show a lock icon and "Complete X first" message on the client overview and render a non-clickable `<div>` instead of a link; navigating directly to a blocked visit URL shows an amber warning with a link back to the previous visit
- Prenatal 1 in-person requirement: the Telehealth toggle is disabled (greyed out, tooltip "First prenatal visit must be in-person") on the Prenatal 1 visit form; stored `location_type` values are not applied on load for this visit type
- Visit slot 4-state display on client overview: complete (gray + green checkmark), in-progress (amber + clock icon + "In progress"), blocked (gray + lock icon + prev label), pending (blue + arrow)
- Visit end timestamp: "End Visit" button appears in the started banner (both in-person and telehealth) after a visit is started; tapping it records `visit_ended_at` immediately to the backend and displays end time + duration (e.g., "✓ Ended at 11:15 AM · Duration: 47m"); end time pre-populates on reload
- Live visit timer: after starting a visit, a ticking MM:SS stopwatch shows in amber with a "X min to 30" countdown until the Medicaid 30-minute minimum is met, then turns green; "End Visit" freezes the timer to the final duration
- 30-minute billing warning: if a visit is ended under 30 minutes, the duration displays in amber with ⚠ and a billing warning panel ("Medicaid requires at least 30 minutes for T1032/T1033 reimbursement") appears above the Save button (non-blocking)

### Fixed
- MA 91 telehealth e-signature document showed "N/A" for Date of Service — the signature request body only sent `patient_email` and `patient_name`; the backend fell back to the saved DB record which has no `visit_date` until the form is explicitly saved; fixed by passing `watch('visit_date')` from the live form so the date is always correct in the document
- Visit form "Save visit" returned "Failed to save visit" — `birth_time`, `visit_started_at`, and `visit_ended_at` send `""` when untouched; `z.string().optional()` passes them through Zod but the backend Pydantic schema types them as `time | None` / `datetime | None`, which reject `""` with a 422 ValidationError; fixed with `z.preprocess` to coerce `""` → `undefined` so those fields are omitted from the JSON body
- Visit form "Save visit" button did nothing — hidden inputs for `provider_latitude`, `provider_longitude`, and `location_type` initialize to `""` in the DOM when untouched; RHF passes those empty strings to Zod on submit, causing `z.number().optional()` and `z.enum([...])` to fail silently (no UI shows errors for hidden fields), so `onSubmit` was never called and no PUT was ever sent; fixed with `z.preprocess` to coerce `""` → `undefined` for numeric fields and `defaultValues: { location_type: 'in_person' }` on `useForm` so the enum field starts valid
- Alternate location (amber >500 ft panel) was not persisting on save — the visible input used `{...register('alternate_location')}` but lived outside the `<form>` tag, so RHF's uncontrolled ref never captured the typed value in the submitted payload; fixed by converting to a controlled pattern (`value`/`onChange` + `setValue`) and adding a matching `<input type="hidden" {...register('alternate_location')} />` inside the form
- No feedback after saving a visit — the form navigated immediately on success with no confirmation; now shows a green "✓ Visit saved successfully." banner for 1.5 s before navigating to the client overview
- Settings page called `useAuth()` in addition to the layout, causing two concurrent `/auth/refresh` requests; if the refresh token is single-use the second call triggered `logout()` (user=null), hiding the ZipZign API key field and role badge — settings page now reads from `useAuthStore()` directly and gates its data fetch on `isAuthenticated` so it only fires after the layout has hydrated the token
- Settings page stuck on "Loading…" indefinitely when auth resolved to unauthenticated — removed the settings-data loading gate; page now renders as soon as `authLoading` clears and settings data fills in asynchronously
- Role badge, ZipZign admin field, and settings data were invisible after login because the login page never called `setUser()` — it only stored the access token and relied on the layout's `useAuth()` hook to hydrate user/role via a `/refresh` round-trip; with `SameSite=Strict` on the refresh cookie that round-trip fails for cross-origin Vercel→Railway requests, leaving `user=null` for the entire session — login page now fetches `/auth/me` immediately after obtaining the access token and calls `setUser()` before navigating, so `isAuthenticated=true` and `user.role` are available instantly
- "Draft SOAP Note" button always returned "Translation failed" — the `_SOAP_TRANSLATE_PROMPT` template contained unescaped `{"subjective"}` etc. which Python's `.format()` interpreted as format placeholders, raising `KeyError: '"subjective"'` before the Claude call was ever made; fixed by doubling the literal JSON braces to `{{` / `}}`

---

## [1.0.1] — 2026-05-29

### Fixed
- Migration 0003: replaced `CREATE TYPE IF NOT EXISTS` (PostgreSQL 16+ only) with a `DO $$ BEGIN IF NOT EXISTS … END $$` pg_type check — Supabase runs PostgreSQL 15 which does not support the `IF NOT EXISTS` clause on `CREATE TYPE`
- ZipZign error messages now include the actual HTTP status and response body (401 → "API key rejected", 400 → ZipZign's error detail) instead of a generic message, making diagnosis possible without reading Railway logs
- Admin users could not see the ZipZign API key field in Settings because the auth store `user` was not hydrated before the component rendered — `useAuth()` is now called in the app layout so user + role are available on every page; Settings also gates on `authLoading` before rendering role-sensitive fields

### Added
- Role badge in the sidebar footer (purple "Admin" / blue "Provider") shown below the user's email address
- Role badge in the Settings page heading so users always know which role they are operating under
- ZipZign "Disconnect" button in Settings: when a key is saved, a red "Disconnect" link appears inline next to the label; clicking it immediately clears the stored key and removes the Connected badge
- ZipZign API key placeholder updated to "Enter a new key to replace the saved one" when connected, making it clear the field accepts updates

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
