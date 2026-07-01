# DoulaShield Changelog

All notable changes to this project are documented here.

Format: `## [version] — YYYY-MM-DD`. Changes accumulate under `[Unreleased]`; on each release that section is renamed to the new version and a fresh `[Unreleased]` stub is added above it.

Semver guide — **patch** (1.0.x): bug fixes, infra; **minor** (1.x.0): new features; **major** (x.0.0): breaking auth/schema changes.

---

## [Unreleased]

---

## [1.52.2] — 2026-07-01

### Fixed
- **Weekly compliance email used wrong CAQH attestation cycle**: `weekly_compliance.py` calculated CAQH expiry at 90 days while every other part of the system (dashboard, billing admin roster, reminder emails) uses the correct 120-day cycle. Corrected `_CAQH_CYCLE = 120` so the Monday digest shows accurate days-to-renew for CAQH.

---

## [1.52.1] — 2026-06-30

### Added
- **Billing admin can remove a provider from their roster**: Expanding a provider row in My Providers now shows a "Remove from roster" link at the bottom. Clicking it reveals a confirmation prompt with a description of what happens (account stays active, agency access removed). Confirming calls the new `POST /billing-admin/roster/remove-provider` endpoint, removes the provider from the list, and decrements the Stripe seat count. Account deactivation and deletion remain admin-only.

---

## [1.52.0] — 2026-06-30

### Added
- **"How It Works" guide on all major screens**: A consistent modal guide — matching the pattern on the admin Enrollment Services page — now appears on five additional pages via a "How It Works" button in each page header:
  - **Admin › Billing Providers**: Explains agency setup, subscription model, enrollment tier, CSV bulk import, and compliance emails
  - **Admin › Leads**: Covers lead sources, the New → Converted status pipeline, follow-up scheduling, and the lead conversion workflow
  - **Billing Admin › My Providers**: Documents the roster, enrollment tier tasks, auto-expand for assigned services, document download/remove, and seat billing
  - **Billing Admin › Agency Claims**: Explains the claim status flow, Availity submission, manual status logging, and audit packet downloads
  - **Provider › My Credentialing Status**: Walks providers through the authorization agreement, four-stage pipeline, task indicators, document uploads, secure info storage, and the PCB application form

---

## [1.51.0] — 2026-06-30

### Added
- **Billing admin can download and remove enrollment documents**: Agencies using the Enrollment Tier can now download provider-uploaded documents directly from My Providers, and remove incorrectly uploaded files. Two new backend endpoints mirror the admin equivalents: `GET /billing-admin/enrollment/services/{id}/documents/{doc_id}/url` for signed download links and `DELETE /billing-admin/enrollment/services/{id}/documents/{doc_id}` for removal. Each task card in the enrollment panel shows uploaded documents as clickable download links with a "Remove" button alongside.

---

## [1.50.9] — 2026-06-30

### Fixed
- **Remove document button now clearly visible**: The × delete button on document rows was rendered in `text-gray-300` (nearly white), making it invisible against the light background. Replaced with a labelled "Remove" button using red border and text so it is immediately findable.

---

## [1.50.8] — 2026-06-30

### Fixed
- **App startup crash on Railway**: FastAPI raises an `AssertionError` at import time when a `DELETE` endpoint declares `status_code=204` alongside a `-> None` return annotation — HTTP 204 forbids a response body, but FastAPI's internal validation treats the combination as ambiguous and aborts. Fixed by adding `response_class=Response` to the decorator and removing the return annotation. This was the root cause of the healthcheck never receiving a response.

---

## [1.50.7] — 2026-06-30

### Fixed
- **CORS now permits DELETE requests**: The CORS middleware was explicitly blocking DELETE — the document-deletion endpoint added in 1.50.6 would have been rejected by browsers with a preflight 403. `DELETE` is now included in `allow_methods`.
- **CAQH re-attestation reminder emails now use the correct 120-day cycle**: The scheduled job was computing expiry at 90 days (matching the old billing roster bug fixed earlier), causing reminders to fire a month early. Now consistent with the CAQH 120-day attestation cycle.

---

## [1.50.6] — 2026-06-30

### Added
- **Remove document from enrollment task**: Admins can now delete a wrongly uploaded document. Each document row shows a × button that prompts for confirmation, deletes the file from Supabase Storage, and removes the record from the database. The task card updates immediately without a page reload.

---

## [1.50.5] — 2026-06-30

### Added
- **Document download buttons on admin enrollment services**: Documents uploaded by providers now appear as clickable links in each task card. Clicking fetches a signed URL from the backend and opens the file — admins can download and re-upload to CMS, CAQH, or PROMISe™ without navigating to Supabase.
- **Provider info copy bar on enrollment detail**: When a service is expanded, a compact bar shows the provider's name, email, and NPI (if on file) as one-click copy buttons. Clicking any chip copies the value to the clipboard — useful when filling in external portals without switching tabs.
- **Copy button on task notes**: Each task's notes field now shows a small clipboard icon when a value is present. Clicking copies the recorded value (ATN, CAQH ID, NPI, etc.) directly to the clipboard.
- **NPI included in enrollment service detail API response**: `GET /admin/enrollment/services/{id}` now returns `provider_npi` alongside `provider_name` and `provider_email`.

---

## [1.50.4] — 2026-06-30

### Changed
- **PROMISe™ task descriptions rewritten with Stage & Share workflow**: Both `promise_type13` and `promise_type130` task descriptions now document the complete operational process: NPI taxonomy prerequisite (374J00000X must be active in NPPES before starting), portal URL (provider.ipx.pa.gov), Type 13/Specialty 130 classification, ZIP+4 lookup for service location code accuracy, PCB credential entry requirements, W-9 legal entity name matching rule, employment gap explanation requirement, and the critical legal constraint that the provider must personally attest and click Submit. Admin builds the full application then does a live screen-share hand-off for attestation. ATN capture instructions and 30–60 day processing timeline added.
- **Admin Guide Stage 2 PROMISe™ section expanded**: Added "Stage & Share method" subsection covering all key rules, common kickback causes (W-9 mismatch, employment gaps), and the live hand-off attestation requirement.

---

## [1.50.3] — 2026-06-30

### Changed
- **CAQH enrollment redesigned — 3-task Practice Manager workflow**: The single `caqh_pv_enrollment` task has been replaced with three tasks reflecting the actual CAQH DataSpring/Practice Manager workflow: (1) **Request Practice Manager Access** — admin searches provider by NPI and submits an access request; (2) **Provider Authorizes DoulaShield** — provider logs into their CAQH account and approves DoulaShield under the Authorizations tab; (3) **Complete CAQH Profile & Provider Attests** — admin fills the 12-section profile via Practice Manager and provider attests. New Stage 2 services will have 8 tasks (was 6).
- **CAQH authorization task has a doxy.me screen-share button**: The "Provider Authorizes DoulaShield in CAQH" task card now shows a **Start doxy.me Screen-Share** button (same pattern as the NPPES I&A task). Clicking it sends the provider a CAQH-specific invitation email explaining the authorization steps and opens doxy.me for the admin.
- **CAQH attestation expiry corrected to 120 days**: The billing admin roster credential chip was calculating CAQH expiry at 90 days; corrected to 120 days (the actual CAQH attestation cycle). Providers will no longer show premature credential warnings.
- **Admin Guide updated**: Stage 2 section now reflects 8 tasks, documents the one-time CAQH Practice Manager agency setup steps, and explains the per-provider CAQH workflow including the authorization blocker. Credential monitoring table updated to show 120 days for CAQH Attestation.

---

## [1.50.2] — 2026-06-30

### Changed
- **Assign to Agency auto-enables enrollment tier**: Clicking **Assign to Agency** on an enrollment service now automatically sets `enrollment_tier_enabled = true` on the billing provider if it is not already enabled. This means the billing admin gains immediate access to the assigned service in their My Providers panel without requiring a separate admin step to enable the tier. Unassigning does not disable the tier. The audit log records whether the tier was newly enabled as part of the assignment.

---

## [1.50.1] — 2026-06-30

### Fixed
- **Enrollment services visible without enrollment tier**: Assigned enrollment services (flagged `assigned_to_billing_admin = true` by a DoulaShield admin) are now always visible to billing admins regardless of whether the agency has the paid Enrollment Tier enabled. Previously, the entire Enrollment Services section was hidden when the tier was off, so billing admins could not see tasks the admin had assigned to them. Now: the section always renders and shows assigned services; the `+ Start Service` button and new-service form still require the Enrollment Tier. Backend `GET/billing-admin/enrollment/services`, `GET /billing-admin/enrollment/services/{id}`, and `PATCH /billing-admin/enrollment/tasks/{id}` are now gated by `get_managed_billing_provider` (billing admin identity check) rather than `require_billing_enrollment_tier`; only `POST /billing-admin/enrollment/services` (creating new services) retains the tier gate.

---

## [1.50.0] — 2026-06-30

### Added
- **Auto-expand assigned enrollment tasks on My Providers**: When DoulaShield assigns an enrollment service to a billing agency (`assigned_to_billing_admin = true`), the billing admin no longer needs three clicks to reach the task list. Opening the provider row now automatically expands the assigned service and shows all tasks immediately. Task details for assigned services are pre-fetched in parallel on page load so there is no loading spinner on first open. Providers with no assigned services are unaffected.

---

## [1.49.1] — 2026-06-30

### Fixed
- **Auto-expand after Assign to Agency**: Clicking "Assign to Agency" on the admin Enrollment Services page now immediately expands the service row and loads the task list, so the admin can see the PCB (or other stage) tasks without needing a second click.

---

## [1.49.0] — 2026-06-30

### Added
- **Assign enrollment service to billing agency**: Platform admins can now hand off an enrollment service they created to the provider's billing agency with one click. On the admin Enrollment Services page, each service row has an "Assign to Agency" button (outside the expand toggle to avoid accidental clicks). Clicking it sets `assigned_to_billing_admin = true` on the service and shows a filled indigo "✓ Assigned to Agency" badge. Clicking again unassigns. The backend validates that the provider is actually assigned to a billing agency before toggling. On the billing-admin My Providers page, assigned-by-DoulaShield services now show an "Assigned by DoulaShield" indigo badge in their service row, making the handoff visible to the billing admin.
- **Migration 0050**: Adds `assigned_to_billing_admin BOOLEAN NOT NULL DEFAULT false` to `enrollment_services`.

---

## [1.48.1] — 2026-06-30

### Fixed
- **Duplicate enrollment service guard**: Starting an enrollment service from the billing-admin My Providers panel now returns a clear 409 error ("An active PCB Certification service already exists for this provider…") instead of silently creating a second service at the same stage. This was the cause of "Failed to start service" errors when a platform admin had already started the same stage via the admin enrollment panel.
- **Enrollment error messages**: Pydantic 422 validation errors (e.g. "pcb_pathway is required") now surface in the toast notification instead of showing the generic "Failed to start service" fallback. Same fix applied to the task toggle error handler.

---

## [1.48.0] — 2026-06-30

### Added
- **Billing-admin enrollment management**: Agencies with the Enrollment Tier enabled now see a full enrollment panel on each provider row in "My Providers". Billing admins can start new enrollment services (PCB Certification, NPPES/NPI Setup, PROMISe Enrollment, MCO Contracting), expand services to view their task list, mark tasks complete/incomplete with a checkbox, and save per-task notes — all scoped to their own agency's providers. Backend: new `enrollment_billing_admin` router with 4 endpoints (`GET/POST /billing-admin/enrollment/services`, `GET /billing-admin/enrollment/services/{id}`, `PATCH /billing-admin/enrollment/tasks/{id}`) gated by `require_billing_enrollment_tier` dependency which verifies both billing_admin role and `enrollment_tier_enabled` on the agency's BillingProvider record.

---

## [1.47.2] — 2026-06-29

### Added
- **Subscription confirmation email to billing agencies**: When an admin clicks "Start Sub", DoulaShield now sends a branded email to the agency's billing admin(s) (falling back to the first assigned provider if no billing admin is set) confirming the subscription, showing seat count and monthly total, and including a "Manage Billing →" button linking to the Stripe Customer Portal where they can add a payment method and pay the first invoice. If the Stripe portal is not yet configured, the email instructs them to follow the Stripe invoice email instead.

---

## [1.47.1] — 2026-06-29

### Fixed
- **Billing provider "Start Sub" crash**: Stripe rejected subscription creation with 400 `resource_missing` when the agency customer had no attached payment method. Fixed by switching billing provider subscriptions to `collection_method='send_invoice'` with `days_until_due=30` — Stripe now emails the invoice directly to the agency and no card is required at subscription creation time.

---

## [1.47.0] — 2026-06-29

### Added
- **doxy.me screen-share invite for NPPES I&A account setup**: Admin can now one-click start the recommended 10-minute RIDP screen-share session directly from the "Create I&A System Account" task on the enrollment services page.
  - **Backend**: `POST /admin/enrollment/tasks/{task_id}/screenshare-invite` looks up the task's service and provider, then sends a branded invitation email (via Resend) containing the admin's personal doxy.me room link.
  - **`email_service.send_screenshare_invite()`**: New branded HTML email explaining the RIDP session, what to have ready, and a "Join Screen-Share →" button linking to the admin's doxy.me room.
  - **Frontend**: "Start doxy.me Screen-Share" button on the `nppes_ia_account` task card (hidden once the task is complete). Fetches the admin's own `telehealth_link` from `GET /auth/me/provider-settings`; if unset, prompts the admin to add it in Settings first. On click, sends the invite and opens doxy.me in a new tab — mirroring the existing pattern on the visits page.

---

## [1.46.0] — 2026-06-29

### Added
- **Enrollment Tier add-on for billing providers**: DoulaShield admin can now enable a per-seat monthly enrollment tier on any billing provider's subscription, giving that agency self-service access to the credentialing workflow for their assigned providers.
  - **Stripe**: Enrollment tier is a second `SubscriptionItem` on the agency's existing subscription (`STRIPE_ENROLLMENT_TIER_PRICE_ID`), priced per unit at the same quantity as the seat line. Both items scale together when providers are added or removed. Disabling removes the item with a prorated credit.
  - **Database migration** (`0049`): Two new columns on `billing_providers` — `enrollment_tier_enabled` (boolean, default false) and `enrollment_tier_stripe_item_id` (text, stores the Stripe item ID for syncing).
  - **Backend**: `POST /admin/billing-providers/{bp_id}/enable-enrollment-tier` and `POST .../disable-enrollment-tier` — require active subscription, audit-logged.
  - **Stripe service fix**: `update_billing_provider_seat_quantity` now finds the seat item by price ID instead of positional index, preventing incorrect item modification when the enrollment tier item is also present. Also syncs the enrollment tier item quantity on every provider add/remove.
  - **Frontend**: "Enable Enroll Tier" / "Disable Enroll Tier" button on each billing provider row (visible only when subscription is active). Purple when off, amber when on.
  - **`BillingProviderRead` schema** and **`BillingProvider` TypeScript interface** updated with `enrollment_tier_enabled`.
  - **`.env.example`**: Documents `STRIPE_ENROLLMENT_TIER_PRICE_ID`.

---

## [1.45.1] — 2026-06-29

### Changed
- **CMS Surrogate Workflow — Pathway A added**: The NPPES enrollment stage now includes an optional Pathway A task (electronic approval) between the surrogate link request and Pathway B. Providers who have an active I&A account can approve the link in 24 hours without any paper. Pathway B task description updated with exact portal steps (Tracking ID → Optional Surrogacy Confirmation → Add a Document). Confirm task shifts to sort order 11. Stage now has 11 tasks total.

---

## [1.45.0] — 2026-06-29

### Added
- **CMS Surrogate Workflow — Pathway A & B**: Four new tasks added to the NPPES / NPI Setup enrollment stage covering the CMS I&A surrogate connection process.
  - **Link DoulaShield as CMS Surrogate** (sort 8): Admin logs into DoulaShield's CMS I&A account → My Connections → Add Provider, selects PECOS + NPPES functions, and submits the link request.
  - **Pathway A — Electronic Approval** (sort 9, optional): Provider logs into their own I&A account and clicks Approve — fastest route, activates within 24 hours. Skip Pathway B if complete.
  - **Pathway B — Paper Surrogacy Approval Form** (sort 10): For providers who cannot approve electronically — admin opens the provider's Tracking ID in My Connections → prints the "Optional Surrogacy Confirmation" form → both AO and provider sign → admin uploads via "Add a Document" in the I&A portal. EUS manual processing 5–10 business days.
  - **Confirm Surrogacy Active in CMS** (sort 11): Admin verifies the My Connections status shows Linked (not Pending), enabling DoulaShield to manage the provider's NPPES record and PECOS submissions without provider portal access.
- **ADMIN_GUIDE.md**: Added one-time agency setup section for NPPES / NPI Setup stage — steps to create the DoulaShield I&A account, register the business entity with EIN, and submit the IRS CP575 to EUS. Updated the per-provider task table from 7 to 11 tasks.

---

## [1.44.1] — 2026-06-29

### Fixed
- **Deposit not clearing for agency-assigned providers**: When a provider is assigned to a billing provider (agency), their `deposit_paid` flag is now set to `True` automatically. Previously, agency providers had no path to pay the individual $99 deposit since no deposit link was sent, leaving them permanently locked out. Fix applies to both new providers created via bulk invite / CSV import (`_run_bulk_invite`) and existing providers manually assigned via `POST /admin/billing-providers/{bp_id}/assign-provider`.

---

## [1.44.0] — 2026-06-29

### Added
- **Import provider list from CSV**: Agency directors can upload a spreadsheet of provider data instead of entering it row by row.
  - **"Upload CSV" tab** added to the Invite Providers modal (admin Billing Providers page) and to the Invite New Providers section (billing admin My Providers page). The existing manual row-entry form is unchanged under the "Enter Manually" tab.
  - **CSV columns**: `name` (required), `email` (required), `npi`, `doula_type`, `mco_1`–`mco_9`, `mco_1_date`–`mco_9_date`. Extra columns are ignored.
  - **Client-side parsing** with Papa Parse — no file upload to the server; the CSV is read in-browser and displayed as a preview table before any accounts are created.
  - **Preview table** shows Name, Email, NPI, Doula Type, MCOs, and a per-row status: ✓ ready / ⚠ warning (invalid NPI format or unrecognised MCO name) / ✗ error (missing name or email). Rows with errors are excluded from the import; rows with warnings are importable.
  - **Expandable column guide** lists all valid doula types and MCO names directly in the UI — no need to look them up separately.
  - **Download template CSV** button generates a ready-to-fill template in-browser.
  - **Backend**: `_BulkInviteEntry` extended with `npi` and `mco_contracts` (optional). `_run_bulk_invite` pre-populates `npi`, `billing_provider_name` (set to the agency name automatically), and `mco_contracts_json` on each created account so provider Settings are pre-filled on first login.

### Changed
- **Welcome email for agency-assigned providers**: Providers created via bulk invite or CSV import no longer receive a deposit link — their billing is handled through the agency. Subject line is now "Welcome to DoulaShield — Your Account Details" (was "Your Account & Deposit Link") whenever no checkout URL is present.

---

## [1.43.1] — 2026-06-28

### Added
- **Send Weekly Compliance Email button** on the admin Billing Providers page. Clicking the button runs a dry-run preview (showing how many billing admins will receive an email and how many are skipped), then prompts to confirm before sending. Result panel confirms emails sent and admins skipped. No email is sent during the preview step.

---

## [1.43.0] — 2026-06-28

### Added
- **Weekly compliance summary email for billing admins**: Every Monday morning, each billing admin receives a digest of actionable credential and enrollment items across their provider roster.
  - **Email format**: Subject "Weekly Compliance Summary — Week of [date]" with a color-coded bullet list. Red = expired, orange = critical (< 25% of threshold), amber = warning, blue = action needed. Sorted urgency-first so the most pressing items appear at the top.
  - **Credential thresholds**: CAQH < 60 days, PCB cert < 180 days, PROMISe™ < 365 days, liability insurance < 90 days. No email is sent if all providers are current.
  - **Enrollment stage items**: Any stage with a non-complete status ("NPIs update pending", "PCB certification in progress", etc.) appears as an "Action needed" item.
  - **New function** `send_weekly_compliance_summary()` in `email_service.py` — matches existing 480px HTML template pattern.
  - **New job module** `backend/app/jobs/weekly_compliance.py` — callable both as `run_weekly_compliance(db)` from an endpoint and standalone via `python -m app.jobs.weekly_compliance [--dry-run]`.
  - **Manual trigger** `POST /admin/jobs/send-weekly-compliance` (admin auth, `?dry_run=true` supported) for ad-hoc testing from the admin panel.
  - **Cron trigger** `POST /internal/send-weekly-compliance` (X-Internal-Secret header) for Railway cron: `0 8 * * 1` — Monday 08:00 UTC.

---

## [1.42.2] — 2026-06-28

### Fixed
- **Backend startup crash**: Missing `from pydantic import BaseModel` in `billing.py` caused a `NameError` at module load time when the bulk-invite Pydantic models were added in v1.42.0. The app could not start and all health checks failed.

---

## [1.42.1] — 2026-06-28

### Added
- **Billing admin enrollment & credential visibility**: The **My Providers** page now shows enrollment stage progress and credential expiry for every assigned provider.
  - Each provider row shows a compact stage summary (PCB / NPPES / Enrollment / MCO) with color-coded badges and a "Ready to bill / In progress / Not started" pill.
  - Clicking a row expands it to show full stage cards and credential expiry countdown for PCB cert (2-year cycle), PROMISe™ re-enrollment (5-year), CAQH attestation (90-day), and liability insurance.
  - Rows with any credential expiring within 60 days show an amber "credential expiring" warning inline.
  - Deposit-not-paid warning shown in the expanded panel.
  - Backend: `GET /billing-admin/providers` extended to include `enrollment_stages` and `credentials` fields via a single additional query (no N+1).

---

## [1.42.0] — 2026-06-28

### Added
- **Agency provider roster & bulk invite**: Agencies and admins can now invite multiple providers at once rather than creating accounts one-by-one.
  - **Admin bulk invite** (`POST /admin/billing-providers/{bp_id}/bulk-invite-providers`): Admin opens "Invite Providers" on any billing provider row, enters a table of Name / Email / Doula Type rows, and clicks Send. Each row creates a provider account, assigns it to the agency, and sends a welcome email with a temporary password and deposit link. Rows with an email already in the system are skipped and reported. Stripe seat quantity updates automatically for agencies with an active subscription.
  - **Billing admin self-service** (`POST /billing-admin/roster/invite`): Billing admins can invite providers directly to their own agency from the new **My Providers** page (`/billing-admin/providers`) without going through DoulaShield admin.
  - **My Providers page** (`/billing-admin/providers`): Shows the current provider roster (name, email, NPI) and hosts the invite form. Added to the billing admin sidebar as the first navigation item.

---

## [1.41.2] — 2026-06-28

### Fixed
- **Enrollment status TypeScript build error**: Removed dead `maxLength` property access on `PCB_FORM_FIELDS` map after `ssn_last4` (the only field that carried `maxLength`) was moved to the encrypted Secure Information section. Fixes Vercel build failure introduced in v1.41.1.

---

## [1.41.1] — 2026-06-28

### Added
- **Encrypted sensitive enrollment data**: SSN, date of birth, and tax ID entered during PCB enrollment are now stored encrypted at rest using Fernet (same key used for CMS 1500 SSN).
  - **Database migration** (`0048_enrollment_sensitive_fields.py`): Adds `provider_dob_encrypted TEXT` and `enrollment_tax_id_encrypted TEXT` columns to `public.users`.
  - **Backend endpoints** (`/enrollment/me/sensitive-profile`): `GET` returns masked SSN last-4, DOB, and `has_*` flags. `PATCH` accepts `ssn` (4 or 9 digits), `dob` (YYYY-MM-DD), and `tax_id`; encrypts each before saving. Both actions are audit-logged with actions `READ_ENROLLMENT_SENSITIVE` and `WRITE_ENROLLMENT_SENSITIVE`.
  - **PCB pre-fill PDF**: Now reads DOB and SSN last-4 from the encrypted user fields instead of plaintext `task_data` JSONB. SSN last-4 is derived at PDF generation time — the raw SSN is never written to logs or unencrypted storage.
  - **Frontend** (`/enrollment-status`): Removed `dob` and `ssn_last4` from the plaintext PCB application form. Replaced with an amber-highlighted "Secure Information" section using `type="password"` inputs that call the new endpoint separately. Existing `has_*` flags surface confirmation that data is saved without revealing it.

---

## [1.41.0] — 2026-06-28

### Added
- **Lead Capture & CRM**: Full lead management system for tracking prospective providers and agencies.
  - **Backend public API** (`/api/v1/public/leads`): Three no-auth, rate-limited endpoints for capturing leads from the marketing site — `POST /webinar`, `POST /quiz`, `POST /contact`. Each creates a lead in the new `leads` table and fires an admin notification email.
  - **Backend admin API** (`/api/v1/admin/leads`): Authenticated CRUD endpoints for admin lead management — `GET /` (with filters: source, status, provider_type, search, date range), `POST /` (manual entry), `GET /:id`, `PATCH /:id` (update status, notes, follow-up date, etc.), `POST /:id/convert` (creates provider account via `AdminService.create_user()`, sends welcome + deposit email, links `converted_user_id`), `GET /stats` (total, new this week, converted count, conversion rate).
  - **Database migration** (`0047_leads.py`): New `leads` table with source, status, contact fields, JSONB `lead_data`, notes, follow-up timestamp, and FK links to `users` for assigned admin and converted user.
  - **Admin Leads dashboard** (`/admin/leads`): Full-featured React page with stats bar, filterable table (source/status/type/search), inline edit slide-out panel, and "Convert → Create Account" button for qualified/demo-scheduled leads.
  - **Config additions**: `ADMIN_NOTIFICATION_EMAIL` (receives new-lead notification emails), `CORS_EXTRA_ORIGINS` (comma-separated extra CORS origins for the separate marketing site).
  - **Sidebar**: Added "Leads" link to the admin navigation.
- **Landing page integration notes**: The marketing site (plain HTML, hosted separately on Netlify/Vercel/GitHub Pages) submits forms via vanilla `fetch` to `/api/v1/public/leads/*`. Set `CORS_EXTRA_ORIGINS` in `.env` to your marketing site domain once deployed.

---

## [1.40.2] — 2026-06-26

### Fixed
- **USPS Enhanced Addresses API compatibility (July 12 cutover)**: The new USPS Enhanced Addresses API (v3.3.1) requires the `addresses` OAuth2 scope in the client-credentials token request. Added `"scope": "addresses"` to the token POST in `usps_service.py`. The base URL, endpoint path, request parameters, and response fields DoulaShield uses (`address.ZIPCode`, `address.ZIPPlus4`) are unchanged — no other code updates needed. **Account action still required**: sign the new license agreement and set up an Enterprise Payment Account in the USPS Business Portal before June 25.

---

## [1.40.1] — 2026-06-26

### Added
- **Monthly cost column on Billing Providers table**: The admin Billing Providers screen now shows a "Monthly" column displaying seat count and calculated monthly total (e.g. "4 seats / $220/mo") for agencies with an active or trialing subscription. Computed client-side as `max(3, provider_count) × $55`. Shows "—" for agencies without an active subscription.

---

## [1.40.0] — 2026-06-26

### Added
- **Per-seat billing for billing providers**: Agency subscriptions now use a quantity-based Stripe price (`STRIPE_BILLING_PROVIDER_SEAT_PRICE_ID`) at $55/seat/month with a 3-seat minimum ($165/month floor). When an admin assigns a provider to an agency that already has an active subscription, the subscription quantity is updated immediately via `stripe.SubscriptionItem.modify`. Stripe handles prorated charges for mid-cycle additions automatically.
- **Remove provider from billing provider** (`POST /admin/billing-providers/{bp_id}/remove-provider`): New admin endpoint to unassign a doula from an agency. Decrements the subscription seat quantity (flooring at 3) and records the action in the audit log.
- **`STRIPE_BILLING_PROVIDER_SEAT_PRICE_ID`** config var: set to a Stripe recurring $55/unit price. Falls back to the legacy `STRIPE_AGENCY_MONTHLY_PRICE_ID` flat price if left blank, so existing deployments are unaffected until they opt into per-seat billing.

### How it works
- **Starting a subscription** for an agency with N providers: Stripe creates the subscription at `max(3, N)` seats → minimum charge $165/month.
- **Assigning a 4th+ provider**: seat quantity auto-increments; Stripe bills the prorated difference immediately.
- **Removing a provider**: seat quantity decrements, never below 3.
- The `monthly_total_cents` (seats × 5500) is returned in the assign/remove/start-subscription API response so the admin UI can display the new monthly total.

---

## [1.39.4] — 2026-06-26

### Added
- **PCB Client Evaluation form download link**: A "Download PCB Client Evaluation Form →" link now appears on each of the three client evaluation tasks (`pcb_client_eval_1/2/3`) in the enrollment status page, linking directly to the hosted PDF at `/docs/pcb-client-evaluation.pdf`.
- **Recommendation letter template**: A "Download Recommendation Letter Template →" link now appears on each of the three letter of recommendation tasks (`pcb_ref_letter_1/2/3`) in the enrollment status page. The template PDF (`/docs/pcb-recommendation-letter-template.pdf`) is a printable fill-in form providers can hand to clients, covering: client name, doula name, dates of service, free-form recommendation space, and a signature/date line.

### Changed
- Removed the now-redundant plain-text "Download the official PCB evaluation form at pacertboard.org/doula" sentence from the `pcb_client_eval_1` task description — the downloadable link in the UI replaces it.

---

## [1.39.3] — 2026-06-26

### Fixed
- **Provider enrollment status page crashes with AttributeError**: `CurrentUser` in this codebase only exposes `.id` and `.role` — not `.email` or `.full_name`. Two endpoints in `enrollment_provider.py` referenced `current_user.email` and `current_user.full_name` directly, causing an `AttributeError` whenever a provider (or admin impersonating a provider) loaded the enrollment status page or downloaded the PCB pre-fill PDF. Fixed by querying the `User` model from the database using `current_user.id` before constructing the response, following the same pattern already used by the agreement endpoints.

---

## [1.39.2] — 2026-06-26

### Fixed
- **Provider enrollment status page fails to load**: reportlab was imported at module level in `enrollment_provider.py`. If the library was not yet available in a freshly started container, the entire module failed to load — causing `GET /enrollment/me` to 500 for all providers. Moved reportlab imports inside `_build_pcb_prefill_pdf()` so a missing reportlab only breaks the PDF download endpoint, not the rest of the provider enrollment routes.

---

## [1.39.1] — 2026-06-26

### Fixed
- **Enrollment service creation error**: `AuditLogger.log()` was called with incorrect keyword arguments (`details=`, `request=`) across all five enrollment audit calls. Fixed to use the correct signature (`ip_address=`, `user_agent=`, `extra_context=`) and added missing `get_client_ip`/`get_user_agent` imports. Creating an enrollment service now succeeds without a 500 error.

---

## [1.39.0] — 2026-06-26

### Added
- **PCB application integration**: Providers can now fill in their PCB application personal info, demographics, and doula type directly in the enrollment status page (task #1 of the PCB stage). Clicking "Download Pre-filled Application" generates a formatted PDF with pages 6–8 pre-populated and a live checklist of task statuses — ready to print, sign, and submit.
- **PCB application PDF**: The official PCB Certified Perinatal Doula application (January 2024) is hosted at `/docs/pcb-doula-application.pdf` and linked from the enrollment status page for provider reference.
- **Notarized Acknowledgements & Release task**: Added `pcb_notarized_ar` task (page 14 of the PCB application must be physically notarized before submission) to both PCB pathways. Includes guidance on finding a notary.
- **Submit Application + $50 Fee task**: Added `pcb_application_submit` task covering PDF assembly, email submission to info@pacertboard.org, and the $50 application fee.
- **Improved client evaluation guidance**: All three client evaluation tasks now specify the required consent form, the 9 PCB competency dimensions, the within-last-12-months requirement, and the Pennsylvania client rule for non-PA-resident providers.
- **Improved training certificate guidance**: Training hours and HIPAA certificate tasks now list the exact fields PCB requires on each certificate (name, title, dates, hours, org name) and explicitly state that sign-in sheets are not accepted.
- **Experienced pathway experience documentation**: Replaced the vague "Proof of Active Practice" task with two specific tasks: `pcb_experience_current` (current position on letterhead with required fields) and `pcb_experience_previous` (previous positions for applicants needing additional hours, letterhead only — no resumes).
- New backend endpoint `PATCH /enrollment/me/{service_id}/tasks/{task_id}/data` — provider saves form data to task_data without changing task status.
- New backend endpoint `GET /enrollment/me/{service_id}/pcb-prefill.pdf` — generates a PDF pre-fill sheet using reportlab.

---

## [1.38.0] — 2026-06-26

### Added
- **Enrollment Services walkthrough guide**: A "How It Works" button on the Admin → Enrollment Services page opens a visual modal covering the full four-stage pipeline. Each stage section shows its task list, gate prerequisite, and a numbered step-by-step admin action guide. A "Key Rules & Reminders" panel covers stage gating enforcement, provider visibility, NPI bypass, and CAQH re-attestation cadence. The guide is available at any time without leaving the page.

---

## [1.37.1] — 2026-06-26

### Fixed
- **Sidebar sign-out hidden for admin**: The sign-out button and user footer were pushed off-screen for admin users because their sidebar has 9 nav links + 3 help links, overflowing the available height. Adding `overflow-y-auto` and `min-h-0` to the nav element makes it scroll internally while keeping the sign-out footer always visible.

---

## [1.37.0] — 2026-06-26

### Added
- **Surrogate Authorization Agreement gate**: Providers must read and electronically sign the Authorized Delegate and NPI Surrogate Authorization Agreement before accessing their Enrollment Status page. The agreement covers the agency's authority to act on the provider's behalf in NPPES, CMS I&A, CAQH ProView, and PROMISe™, data accuracy attestation, privacy commitments, limitation of liability, and revocation rights. Signature timestamp is recorded to the database; providers who have already signed see a confirmation note in the page header. Admins bypass the gate.
- **New endpoints**: `GET /api/v1/enrollment/me/agreement` (check whether the authenticated provider has signed) and `POST /api/v1/enrollment/me/sign-agreement` (record the electronic signature).
- **DB column** `surrogate_auth_signed_at` (migration 0046): nullable timestamptz on `users` tracking when each provider signed the surrogate authorization.

---

## [1.36.0] — 2026-06-26

### Added
- **Enrollment Status page** (`/enrollment-status`): Providers can now see their full credentialing checklist for every stage. Each task shows its label, full description, status badge, and any already-uploaded documents. Providers can upload documents (PDF/JPEG/PNG, up to 20 MB) directly to any incomplete task — uploading auto-advances a task from "not started" to "in progress". Admins retain sole control over marking tasks complete.
- **Credentialing Status dashboard card**: When a provider has at least one active enrollment service, a compact status card appears on the Dashboard showing the current stage, task completion count, and a four-stage pipeline pill row (✓ complete · ● in progress · ○ not started), with a link to the Enrollment Status page.
- **Enrollment Status sidebar link**: "Enrollment Status" now appears in the provider sidebar navigation between Reports and Settings.
- **Provider-facing API** (`GET /api/v1/enrollment/me`, `POST /api/v1/enrollment/me/{service_id}/tasks/{task_id}/documents`, `GET /api/v1/enrollment/me/{service_id}/documents/{doc_id}/url`): New endpoints scoped to the authenticated provider's own services. Document uploads reuse the same `store_image` / `get_signed_url` utilities as the admin enrollment upload.

---

## [1.35.0] — 2026-06-26

### Added
- **NPPES / NPI Setup stage**: A new stage between PCB Certification and Stage 2 (Enrollment) that tracks the full 7-step federal NPI application workflow. Auto-generates tasks for: creating an I&A System account (with surrogate tip), starting the NPI application (Type 1 Individual), completing the provider profile (exact legal name match required), entering business addresses (mailing vs. practice location rules), assigning taxonomy code 374J00000X (Doula), filling in the contact person and identifiers, and attesting/submitting. When all tasks are done the admin records the issued 10-digit NPI — DoulaShield writes it to the provider's profile.
- **NPPES tab**: The Enrollment Services admin page now shows four tabs — PCB Certification, NPPES / NPI Setup, Enrollment (Stage 2), and MCO Contracting (Stage 3).
- **Stage gate — NPPES requires PCB cert**: Creating an NPPES service is blocked (422) if `pcb_last_certified_on` is not set on the provider.
- **Stage gate — Stage 2 requires NPI**: Creating a Stage 2 enrollment service is now blocked (422) if the provider does not have an NPI on file. Providers who already have an NPI recorded can proceed without going through the NPPES service.
- **`complete-nppes` API endpoint**: `POST /admin/enrollment/services/{id}/complete-nppes` validates the NPI is exactly 10 digits, writes it to `user.npi`, and marks the service complete.

---

## [1.34.0] — 2026-06-26

### Added
- **Stage 2 — Enrollment**: Admins can now create an Enrollment (Stage 2) service for a provider who has a PCB certification date on record. Six tasks are auto-generated: W-9 Form, Government-Issued Photo ID, Liability Insurance Face Sheet, PROMISe™ Type 13 Application (Medicaid), PROMISe™ Type 130 Application (CHIP), and CAQH ProView Enrollment. The "Mark Enrollment Complete" modal records the PROMISe™ enrollment date, PROMISe ID/ATN, CAQH ProView ID, and liability insurance expiry — writing `promise_last_enrolled_on` and `liability_insurance_expires_on` back to the provider's profile.
- **Stage 3 — MCO Contracting**: Admins can create an MCO Contracting (Stage 3) service once Stage 2 is complete. Ten tasks are auto-generated: 5-Year Work History, Resume/CV, and one application+LOI task for each of the 8 PA Medicaid MCOs (AmeriHealth Caritas, Keystone First, UPMC For You, Geisinger Health Plan, Highmark Wholecare, UnitedHealthcare Community Plan, Aetna Better Health, Health Partners Plans). Each MCO task has a "Contract signed" date field to record when the individual contract is returned.
- **Stage filter tabs**: The Enrollment Services admin page now shows three tabs — PCB Certification, Enrollment (Stage 2), and MCO Contracting (Stage 3) — with a per-tab service count. Services are filtered to the active tab.
- **Stage badges**: Each enrollment service row now shows a colored stage badge (PCB in gray, Stage 2 in blue, Stage 3 in purple) alongside the existing status badge.
- **Stage gates**: Stage 2 requires `pcb_last_certified_on` to be set on the provider. Stage 3 requires a completed Stage 2 enrollment service for the same provider. The API returns a clear 422 error if the prerequisite is not met.
- **Enrollment Admin Guide — Stage 2 & 3 sections**: The Enrollment Admin Guide (`/enrollment-admin-guide`) now includes task-by-task instructions for both Stage 2 (what each document is, how to navigate PROMISe™ and CAQH ProView, what the liability face sheet must show) and Stage 3 (work history format, LOI guidance, MCO-specific notes, expected credentialing timeline).
- **New DB column**: `stage` VARCHAR(30) added to `enrollment_services` (migration 0045, default `'pcb'`).

---

## [1.33.0] — 2026-06-26

### Added
- **PCB Enrollment Service (dual-pathway)**: Admins can now manage the full Pennsylvania Certification Board (PCB) credentialing process for doula providers through a new Enrollment Services section in the admin sidebar. Two pathways are supported:
  - **Education/Training** (newly trained doulas): Collects training certificates (≥ 24 hours), HIPAA/confidentiality training certificate (≥ 1 hour), CPR certification, and 3 client evaluations. DoulaShield validates that training hours meet the 24-hour minimum before a task can be marked complete.
  - **Experienced** (currently practicing doulas): Collects proof of active practice, CPR certification, 3 client evaluations (within last year), and 3 letters of recommendation (within last year).
- **Enrollment Admin Guide**: A new reference guide (`/enrollment-admin-guide`) is available in the sidebar under Help for admin users. It covers task-by-task instructions for both pathways — what to collect, what to verify, how to handle common edge cases, and how to submit to PCB. Also includes a pre-submission checklist and guidance for recording the PCB certificate once received.
- **Automatic task seeding**: When an admin creates an enrollment service and selects a pathway, DoulaShield automatically generates the correct task checklist (6 tasks for Education/Training, 8 tasks for Experienced). No manual setup required.
- **Document upload per task**: Each task supports document uploads (PDF, JPEG, PNG, up to 20 MB). Uploading a document automatically advances a "not started" task to "in progress."
- **Profile write-back on completion**: When the admin records the PCB certificate date, DoulaShield writes `pcb_last_certified_on` to the provider's profile — the date that downstream credentialing steps (CAQH setup, MCO contracting) reference.
- **Hours validation**: Training hours and HIPAA hours are validated server-side — tasks requiring minimum hours cannot be marked complete if the threshold is not met.
- **New DB tables**: `enrollment_services`, `enrollment_tasks`, `enrollment_documents` (migration 0044).

---

## [1.32.1] — 2026-06-24

### Fixed
- **Aetna Better Health payer ID corrected**: DoulaShield was using `"AETNB"` as the EDI payer ID for Aetna Better Health of Pennsylvania, which is not a valid payer identifier in any clearinghouse directory. The correct EDI payer ID is **23228** (per Aetna's own Quick Reference Guide, which lists "Emdeon Payer ID: 23228"). Claims submitted via Availity's API now use the correct payer ID, preventing routing failures. Updated in `backend/app/services/availity_client.py`.
- **Documentation updated**: MANUAL.md MCO reference table corrected to show payer ID 23228 and notes the Office Ally portal fallback (Availity portal → "Medicaid Claim Submission – Office Ally"). BILLING_ADMIN_GUIDE.md updated with Aetna-specific submission guidance and paper mail address.

---

## [1.32.0] — 2026-06-24

### Fixed
- **Demo patient claims excluded from billing admin queue**: Claims belonging to patients flagged as `is_demo=True` (created while a provider has demo mode on) no longer appear in the billing admin's Agency Claims page. The backend `GET /billing-admin/claims` query now joins the Patient table and filters out demo patients, so billing admins only see real claims requiring action.

### Added
- **Billing Admin Guide**: A new reference guide is available from the sidebar under Help → "Billing Admin Guide" for all `billing_admin` users. The guide covers the full billing admin workflow: configuring Availity credentials, reviewing claims (SOAP notes, CMS 1500, audit packet), submitting to Availity, logging manual submissions, uploading supporting documents, and tracking paid/denied outcomes. Accessible at `/billing-admin-guide`; restricted to `billing_admin` and `admin` roles.

---

## [1.31.0] — 2026-06-24

### Added
- **Sample Remittance Advice PDF in Walkthrough Guide**: A downloadable `sample-remittance-advice.pdf` is now linked inside the Walkthrough Guide modal (both the admin Users page version and the provider Sidebar version). The PDF is a realistic PA Medicaid Provider Remittance Advice showing five sample claim outcomes — two paid in full, one partially adjusted (CO-45), and two denied (CO-4, CO-96) — with adjustment/denial reason codes, recommended actions, and a payment summary. Providers can download it and use it in step 6 to practice the EOB upload flow without waiting for a real remittance.

---

## [1.30.2] — 2026-06-23

### Fixed
- **Retroactive demo-patient flagging could delete real clients**: When demo mode was enabled, the previous logic marked every active patient for the provider as `is_demo = true` — including any real clients added before demo was turned on. Those would have been incorrectly deactivated on demo disable. Reverted to creation-time flagging only: `is_demo` is set at the moment a patient is created, based on whether the provider has demo mode on at that instant. Existing patients are never touched on enable.
- **`is_demo` now settable via `PATCH /patients/{id}`**: Added `is_demo` to `PatientUpdate` so an admin (or support) can explicitly mark a specific patient as `is_demo = true` when needed — for example, a patient created before migration 0043 deployed.

---

## [1.30.1] — 2026-06-23

### Fixed
- **Existing patients not flagged as demo on enable**: When an admin enables demo mode for a provider, all of that provider's currently-active patients are now marked `is_demo = true` — even if they were created before demo mode was turned on (or before migration 0043 added the flag). This means disabling demo mode will correctly clean them up. Previously, only patients created *after* demo was enabled carried the flag.

---

## [1.30.0] — 2026-06-23

### Added
- **Demo clients auto-removed when demo mode is disabled**: Clients created while a provider has demo mode on are now flagged with `is_demo = true`. When an admin disables demo mode, all of that provider's demo clients are automatically deactivated — they disappear from the Clients list without any manual cleanup. The provider's real clients are unaffected.
- **"Demo" badge on demo clients**: While demo mode is on, each demo client in the provider's Clients list shows a green "Demo" pill so the provider can visually distinguish them from real clients.
- **DB migration 0043**: adds `is_demo BOOLEAN NOT NULL DEFAULT false` column to `public.patients`.

---

## [1.29.2] — 2026-06-23

### Fixed
- **CMS 1500 missing from all audit packets**: `cms1500_service.generate_pdf()` called `claim_data.get()` unconditionally in the Box 22 resubmission-code block (lines 501–502). `audit_packet_service` called `generate_pdf()` without forwarding `claim_data`, so `claim_data` arrived as `None`, raised `AttributeError`, and was silently caught — `cms_bytes` was set to `None` and the CMS 1500 was never appended to the PDF. Fixed by (1) guarding the two Box 22 lines with `if claim_data`, (2) passing `claim_data` through from `generate_audit_packet()` so Box 22 and Box 29 are now filled correctly, and (3) replacing the bare `except` with `log.exception` so future failures appear in logs.

---

## [1.29.1] — 2026-06-23

### Fixed
- **Add Client form blocked by browser date validation**: The date-of-birth field (`<input type="date">`) could block form submission entirely if the user typed a date in MM/DD/YYYY format rather than using the date picker widget. The browser's native validation error appeared silently and prevented the React submit handler from running. Added `noValidate` to the form so all validation is handled by Zod and the backend. Also updated both walkthrough guide tables to label DOB as optional and note that the Referring NPI column does not correspond to an Add Client field.

---

## [1.29.0] — 2026-06-23

### Added
- **Provider Demo Mode**: Admins can now toggle a "Demo Mode" flag on any provider account from the Users page. While demo mode is on, claim submissions for that provider are simulated — a realistic `DEMO-XXXXXXXX` claim ID is generated and the claim appears as "Processing" in Reports, but nothing is sent to Availity. Status checks on demo claims are also intercepted. Disable demo mode when the provider is ready for live billing; their existing data is unaffected and real Availity submissions resume immediately.
- **Walkthrough Guide modal**: A "Walkthrough Guide" button on each provider row opens a reference card the admin can share (screen-share or screenshot) with a new provider. It contains six numbered workflow steps, a set of sample SOAP notes for a Prenatal 1 visit, and a table of 10 fake patients with realistic names, Medicaid IDs, MCOs (all nine options including FFS), dates of birth, addresses, and a placeholder NPI — enough to walk through the full workflow from adding a client to uploading an EOB.
- **Provider sidebar link**: While demo mode is on, a green "Walkthrough Guide" link appears in the provider's sidebar under the Help section. Clicking it opens the same reference card modal inline — so the provider always has the cheat sheet within reach without needing the admin to re-share it.
- **Auto-email on demo enable**: When an admin enables demo mode for a provider, the walkthrough guide is automatically emailed to the provider (via Resend). The email contains the same six workflow steps, SOAP notes, and patient table as the in-app modal.
- **DB migration 0042**: adds `is_demo BOOLEAN NOT NULL DEFAULT false` column to `public.users`.

---

## [1.28.9] — 2026-06-16

### Added
- **Admin "View As" between admin accounts**: Admins can now use the "View As" button to impersonate other admin accounts (not just providers). The impersonation banner shows correctly, and the impersonated session carries the `admin` role so admin pages load without redirect. `billing_admin` accounts remain non-impersonatable. Self-impersonation and nested impersonation (starting a second "View As" while already impersonating) are blocked.

---

## [1.28.8] — 2026-06-15

### Added
- **Reports page resubmission indicator**: A "↺ Resubmitted" row now appears below the Claim Pipeline tiles when any claims have been resubmitted, showing the count of affected claims and total resubmission attempts. Previously resubmitted claims were invisible in the aggregate view.

### Fixed
- **Settings save errors now show the actual server message**: The "Failed to save" and "Failed to save signature" error handlers previously swallowed all errors with a generic message, making it impossible to diagnose the failure. They now display the backend's error detail (e.g., "Storage failed: …" for Supabase issues). A 401 response redirects to the login page instead of showing a confusing error.

---

## [1.28.7] — 2026-06-15

### Fixed
- **CMS 1500 Box 29 amount format**: Paid amount was rendered as `100.00` (dollar-decimal). Now formatted as cents without a decimal point (`10000`), matching the Box 24F and Box 28 convention where the form pre-prints the decimal separator.

---

## [1.28.6] — 2026-06-15

### Changed
- **MCO field is now a dropdown on Add Client and Edit Client screens**: Replaced the free-text MCO input with a `<select>` listing all PA Medicaid MCOs (AmeriHealth Caritas, Keystone First, UPMC For You, Geisinger Health Plan, Health Partners Plans, Aetna Better Health, UnitedHealthcare Community Plan, Highmark Wholecare, FFS). OCR card scanning continues to populate the field via `setValue`.

---

## [1.28.5] — 2026-06-15

### Fixed
- **In-app Admin Guide and User Manual were out of date**: The static docs served at `/docs/admin-guide.md` and `/docs/manual.md` were behind the root source files by 35 and 6 lines respectively, missing agency claim queue and status update content added in v1.27.0–v1.28.0. Both files are now synced. Version headers in all four files updated to match the current app version.
- **User Manual missing agency EOB restriction note**: Added a callout to the Scanning Paper Remittances section explaining that agency-assigned providers do not have access to EOB scan features — their billing agency handles remittance processing.

---

## [1.28.4] — 2026-06-15

### Fixed
- **TypeScript build error in reports page**: The `axios.get` call for `/auth/me/provider-settings` was typed to only include `mco_contracts`, causing a type error when reading `billing_provider` from the response. Added `billing_provider: unknown | null` to the response type.

---

## [1.28.3] — 2026-06-15

### Fixed
- **CMS 1500 Box 33 shows doula's address instead of billing agency address**: Both the provider and billing-admin CMS 1500 endpoints were computing `billing_npi`/`billing_name` but not passing `billing_provider_data` to `generate_pdf()`. The service fell through to the `else` branch and used the doula's home address for Box 33. Both call sites now pass a `billing_provider_data` dict (name, address, city, state, zip, phone, NPI) when a `BillingProvider` is assigned, so Box 33 shows the agency's address.
- **EOB Remittance scanner visible for agency-assigned providers on Reports page**: The Reports page now reads `billing_provider` from the `/auth/me/provider-settings` response and hides the "Remittance / EOB Scan" section when the provider is assigned to a billing agency. This matches the existing frontend guard on the visit page and the backend 403 guard added in v1.28.0.

---

## [1.28.2] — 2026-06-14

### Fixed
- **Black boxes in CMS 1500 signature fields (Box 12 and Box 31)**: ReportLab renders RGBA transparent pixels as black when overlaying a PNG signature image onto the PDF. The signature is now composited onto a white RGB background using its alpha channel as a mask before being drawn, so transparent areas appear white on the form instead of as black blocks.

---

## [1.28.1] — 2026-06-14

### Fixed
- **TypeScript build error in `FilePreviewModal`**: Axios `content-type` header has a union type that includes non-string values. Cast via `String()` to satisfy the type checker.

---

## [1.28.0] — 2026-06-14

### Added
- **Comprehensive billing admin claim review panel**: Expanding a claim row now fetches a full review snapshot (`GET /billing-admin/claims/{claim_id}/review`) with three collapsible sections:
  - **Claim Details** — payer, procedure code, diagnosis code, billed amount, resubmit count, MA 91 signature status.
  - **Visit Notes** — the provider's full SOAP note (subjective, objective, assessment, plan, entry, birth notes).
  - **Documents** — buttons to preview/download the CMS 1500 PDF, the audit packet PDF, and the source document image (if the provider scanned one); a list of billing-admin-uploaded supporting files; and upload buttons for Prior Auth, Eligibility, EOB Received, and Other document types.
- **Billing admin audit packet**: New `GET /billing-admin/claims/{claim_id}/audit-packet.pdf` endpoint generates the full audit packet (CMS 1500 + SOAP notes + eligibility + MA 91 PDF + credential summary) scoped to the calling agency, accessible from the expanded claim row.
- **Billing admin document upload**: New `POST /billing-admin/claims/{claim_id}/documents` endpoint (multipart/form-data) stores supporting documents in Supabase Storage and records them in the new `claim_documents` table. New `GET /billing-admin/claims/{claim_id}/documents/{doc_id}/file` endpoint returns a short-lived presigned URL for previewing uploaded documents.
- **Generic `FilePreviewModal` component**: `frontend/src/components/ui/FilePreviewModal.tsx` — handles both PDF (iframe) and image (img tag) previews, supports both authenticated-blob fetch (`fetchUrl`) and direct presigned URLs (`directUrl`), with download button.
- **New `claim_documents` table** (`0041_claim_documents.py`): stores billing-admin-uploaded files per claim with foreign keys to `claims` and `users`.
- **EOB remittance backend guard**: `POST /ocr/handbook` with `page_type='remittance_eob'` now returns 403 for any provider assigned to a billing agency, adding backend defense-in-depth to the existing frontend restriction.

---

## [1.27.1] — 2026-06-14

### Added
- **CMS 1500 preview modal for billing admin**: The "Download CMS 1500 (PDF)" button in the expanded claim row is replaced by "Preview CMS 1500", which opens an inline modal showing the completed form in an iframe. A "Download PDF" button inside the modal saves the file (no second network request — uses the same blob). Box 12 (MA 91 patient signature) and Box 31 (provider signature) are both embedded in the preview exactly as they would appear on the submitted form. The new `CMS1500PreviewModal` component (`frontend/src/components/ui/CMS1500PreviewModal.tsx`) is reusable for future contexts.

---

## [1.27.0] — 2026-06-14

### Changed
- **Agency claims routing**: Providers assigned to a billing agency now always have their claims routed to the agency review queue (`pending_billing_review`), even when the agency has not yet configured Availity credentials. The billing admin decides whether to submit via Availity or log a manual submission.
- **Billing admin manual submission**: The Agency Claims page now supports logging a manual submission (marking a claim as submitted/paid/denied without going through Availity), for cases where the agency submitted via paper, MCO portal, or phone. Rows are also now expandable inline to see claim details and download the CMS 1500 PDF before acting.
- **Billing admin CMS 1500 download**: Billing admins can download the CMS 1500 PDF for any claim in their queue via a new `GET /billing-admin/claims/{claim_id}/cms1500.pdf` endpoint. The PDF is generated using the provider's NPI and the agency's group NPI.
- **Provider manual status updates blocked for agency providers**: Providers assigned to a billing agency can no longer use the manual "Update status" form on the visit page. Their claims are managed entirely by the billing admin once submitted for review.

---

## [1.26.1] — 2026-06-13

### Fixed
- **Admin client scoping corrected**: v1.26.0 incorrectly blocked admins from managing their own clients entirely. Admins can now create and view their own clients (scoped to their user ID). During impersonation, created clients are still scoped to the provider's user ID as intended. The patient list/search endpoints now consistently use `list_for_provider(current_user.id)` for all roles — admin's own clients have `provider_id = admin.id`, and during impersonation `current_user.id = provider.id` via JWT, so isolation is automatic with no role branching.
- **Admin sidebar restored**: Admins again see both provider nav links (Dashboard, Clients, Reports, Settings) and admin nav links (Users, Billing Providers, Audit Logs) outside of impersonation sessions.

---

## [1.26.0] — 2026-06-13

### Changed
- **Admin impersonation — clients scoped to provider only**: When an admin uses "View as" to impersonate a provider and creates a client, that client is now exclusively under the provider and not visible to the admin outside of impersonation.
  - Backend: `GET /api/v1/patients`, `POST /api/v1/patients`, and `POST /api/v1/patients/search` now return 403 when called with an admin token. Admins can only access patient data through an active impersonation session (where their token role is "provider").
  - Frontend: The admin sidebar no longer includes provider navigation links (Clients, Dashboard, Reports, Settings). Admins see only admin links outside of impersonation; provider links are shown during an impersonation session as before.

---

## [1.25.9] — 2026-06-12

### Fixed
- **CMS 1500 Box 33a shows rendering provider NPI instead of billing agency NPI**: When a provider is assigned to a billing agency, the CMS 1500 service was falling back to the rendering provider's NPI for Box 33a because `billing_provider_data` is not passed at the call sites. The call sites already supply `billing_group_npi` (the agency group NPI) inside `provider_data`; the service now reads that field as the source for Box 33a, falling back to the rendering NPI only when no agency is assigned.

---

## [1.25.8] — 2026-06-12

### Fixed
- **CMS 1500 Box 24J shows agency NPI instead of provider NPI**: Both the CMS 1500 preview/download and the audit packet were passing `billing_npi` (the agency group NPI) as `provider_data["npi"]`, which the PDF service writes to Box 24J (rendering provider NPI). Box 24J must always contain the individual rendering provider's NPI. Fixed both call sites to use `user.npi` for `provider_data["npi"]`; `billing_npi` continues to flow to Box 33a via `billing_group_npi` as intended.

---

## [1.25.7] — 2026-06-12

### Changed
- **Agency-aware claims UI for providers**: Providers assigned to a billing agency with Availity credentials configured now see context-appropriate UI on visit pages.
  - Pre-submission button reads "Preview CMS 1500 & Submit for Review" instead of "Preview CMS 1500 & Submit".
  - Inside the CMS 1500 modal, the submit button reads "Send to Agency Review" and an orange notice explains the claim will go to the agency queue first.
  - Claims in `pending_billing_review` status display an "Pending Agency Review" badge (orange) and show an explanatory message instead of the "Refresh status" button (which was meaningless before the agency admin submits to Availity).
  - Providers not assigned to an agency, or assigned to an agency without Availity credentials, see no change.

---

## [1.25.6] — 2026-06-12

### Added
- **`STRIPE_AGENCY_MONTHLY_PRICE_ID` environment variable**: Billing agencies (billing providers) can now be billed at a different Stripe price than individual providers. Set this variable in your Railway environment to the `price_1…` ID of your agency subscription product. If left blank, the system falls back to `STRIPE_MONTHLY_PRICE_ID` so existing deployments are unaffected.

---

## [1.25.5] — 2026-06-12

### Fixed
- **"View as" button missing from Users page**: The button and its `handleViewAs` handler were accidentally dropped in the v1.21.0 billing provider commit. Restored: admins can again click "View as" on any provider row to enter an impersonation session scoped to that provider's data, with the amber banner and "Exit" button appearing on all pages.

---

## [1.25.4] — 2026-06-12

### Fixed
- **"View Claims" and "Settings" buttons on Billing Providers page cause app to close**: These links used plain `<a>` tags instead of Next.js `Link`, triggering a full browser reload. On reload the in-memory Zustand auth store is reset to `isAuthenticated: false`; if the subsequent token-refresh cookie exchange fails (CORS edge cases, timing), the app calls `logout()` and redirects to `/login`, appearing as if the app closed. Replaced both `<a>` tags with `Link` for client-side navigation so the auth state is preserved.

---

## [1.25.3] — 2026-06-11

### Fixed
- **Billing admin agency not linked via "Create & Send Email"**: The `create_and_invite` endpoint accepted `managed_billing_provider_id` in the request body but silently discarded it, so billing admins created through "Create & Send Email" had no linked agency. Every subsequent visit to the Agency Settings page returned 404 → "Failed to load agency settings." The fix applies the same `managed_billing_provider_id` assignment that already existed in `create_account_only`.

---

## [1.25.2] — 2026-06-11

### Fixed
- **Agency settings / billing-admin endpoints crash**: All five billing-admin endpoints (`GET /billing-admin/claims`, `GET /billing-admin/providers`, `GET /billing-admin/agency-settings`, `PATCH /billing-admin/agency-settings`, `POST /billing-admin/claims/{id}/submit`) were referencing `current_user.managed_billing_provider_id`, which does not exist on the `CurrentUser` object (JWT only carries `id` and `role`). Added `_get_managed_bp_id(user_id, db)` helper that queries the column from the database; all five endpoints now use an `await` DB lookup instead of the non-existent attribute.

---

## [1.25.1] — 2026-06-11

### Fixed
- **`billing_admin` role constraint (CRITICAL)**: Creating a user with `role: "billing_admin"` triggered `asyncpg.exceptions.CheckViolationError` because the PostgreSQL check constraint on `public.users.role` only permitted `('provider', 'admin')`. Alembic migration 0040 drops and recreates the constraint to include `'billing_admin'`.
- **Admin view of billing-admin pages**: All billing-admin API endpoints (`GET /billing-admin/claims`, `GET /billing-admin/providers`, `GET/PATCH /billing-admin/agency-settings`, `POST /billing-admin/claims/{id}/submit`) now accept an optional `?bp_id=<uuid>` query param. When a platform admin provides this param, they see that agency's data without needing to log in as the billing admin. The admin billing-providers page gains "View Claims" and "Settings" action links for each agency row.
- **Individual subscription cancelled on agency assignment**: When a provider is assigned to a billing agency via `PUT /admin/billing/assign-provider`, their individual Stripe subscription is automatically cancelled (if active/trialing and Stripe is configured). Cancellation result is recorded in the audit log.

### Docs
- **Admin Guide**: Added "Billing Admin Role", "Shared Availity Credentials and the Claim Review Queue", "Configuring Agency Availity Credentials", and "Admin View of Billing Admin Pages" sections. Added `SUBMIT_CLAIM_TO_QUEUE`, `UPDATE_AGENCY_AVAILITY`, `SUBMIT_AGENCY_CLAIM`, and `ASSIGN_BILLING_PROVIDER` to the audit action types reference table.

---

## [1.25.0] — 2026-06-11

### Added
- **Agency onboarding email**: When a new `BillingProvider` record is created, the linked billing admin automatically receives a setup confirmation email with the agency name, Group NPI, and links to the claims queue and Agency Settings page.
- **`billing_admin` role creation fix**: `create_and_invite` endpoint no longer downgrades `billing_admin` role to `provider`; all three roles (`provider`, `admin`, `billing_admin`) are now accepted correctly.
- **Shared Availity credentials on BillingProvider**: `availity_client_id_encrypted`, `availity_client_secret_encrypted`, and `availity_npi` columns added to the `billing_providers` table (Alembic migration 0039). Billing admins store agency-level credentials used to submit on behalf of all their providers.
- **Agency claim review queue**: When a provider assigned to a billing agency submits a claim, it enters `pending_billing_review` status instead of going directly to Availity — provided the agency has Availity credentials configured. If no agency credentials are set, the individual provider's credentials are used as before (backward compatible).
- **`GET /billing-admin/agency-settings`** + **`PATCH /billing-admin/agency-settings`**: Billing admins can view and update their agency's Availity Client ID, Client Secret (write-only, stored encrypted), and NPI. Returns `availity_connected` boolean and `availity_npi`.
- **`POST /billing-admin/claims/{claim_id}/submit`**: Billing admin submits a queued claim to Availity using agency credentials. Verifies claim ownership (provider must belong to the billing admin's agency), constructs the Availity request from stored `claim_data`, and updates claim status.
- **Agency Settings page** (`/billing-admin/settings`): New frontend page with agency info (read-only), Availity NPI input, Client ID and Client Secret fields (write-only with "Connected ✓" badge), and an explanation of how the agency claim queue works.
- **"Submit ↗" button on agency claims**: Claims page now shows an amber "Pending Review" badge and a "Submit ↗" action button for queued claims; "pending_billing_review" added to the status filter dropdown.
- **Sidebar "Agency Settings" link** for billing-admin role.
- **`ClaimsService._make_agency_client()`**: Service-level helper mirroring `_make_client()` but using `BillingProvider` Availity credentials and scoping the Redis token cache to the billing provider ID.

### Fixed
- **BillingProvider claim body field names**: Corrected `billing_provider.npi` → `group_npi` and `billing_provider.zip_code` → `zip` in the claim submission body builder to match the actual model columns.

---

## [1.24.1] — 2026-06-11

### Fixed
- **Backend startup crash** — `AssertionError: Status code 204 must not have a response body` on the `DELETE /admin/billing-providers/{bp_id}` endpoint. With `from __future__ import annotations` active, FastAPI 0.115 cannot correctly resolve `-> None` return types on endpoints that use complex `Annotated[..., Depends()]` parameters, causing the route registration to treat the 204 as having a body. Fixed by using `response_class=Response` and returning `Response(status_code=204)` explicitly.

---

## [1.24.0] — 2026-06-11

### Added
- **Admin Billing Providers page** (`/admin/billing-providers`): Full CRUD UI for billing agencies — create/edit modal with Group NPI, address, city, state, ZIP, phone; stats cards showing provider count, billed/paid totals, denial rate; per-row start-subscription, edit, and delete actions.
- **Agency Claims page** (`/billing-admin/claims`): Billing admin role now has a dedicated `/billing-admin/claims` page showing all claims across their managed agency's providers, with provider and status filters and aggregate stats cards.
- **Admin Users page** agency assignment: "Agency" column in the users table, "Assign Agency" per-row action with billing-provider dropdown modal; `billing_admin` option in Create User modal with managed-agency selector.
- **Role badge in sidebar**: Each role now shows a coloured pill badge (purple=Admin, teal=Billing Admin, blue=Provider) under the sign-out button.
- **`require_billing_admin` RBAC guard**: New FastAPI dependency that verifies the requesting user is a `billing_admin` and has a `managed_billing_provider_id`; used on all `/billing-admin/*` routes.
- **Alembic migration 0038** (`reconcile_billing_providers`): Idempotent `ADD COLUMN IF NOT EXISTS` guard for `managed_billing_provider_id` on the users table, ensuring clean `alembic upgrade head` on any environment.

---

## [1.23.2] — 2026-06-11

### Fixed
- **Startup crash (healthcheck failure)**: `billing_provider_id` was defined twice in the `User` SQLAlchemy model — once before `managed_billing_provider_id` and again after it. The duplicate triggered a mapper configuration error at import time, preventing uvicorn from ever binding and causing all Railway healthchecks to fail. Removed the redundant definition.
- **Vercel build failure (TypeScript)**: The admin impersonation handler (`handleViewAs`) constructed an inline `User` object missing the `managed_billing_provider_id` field, which is required by the `User` interface. Added `managed_billing_provider_id: null` to the object literal to fix the type error.
- **Alembic revision collision (second fix)**: Two migration files claimed revision `"0034"` and two claimed revision `"0035"`, producing multiple heads and causing `alembic upgrade head` to fail before uvicorn could start. Removed the superseded old-schema `0035_billing_providers.py` and renumbered the newer billing-providers, billing-admin-role, and claim-filing-deadline migrations to `0035`/`0036`/`0037` respectively, restoring a clean linear chain: `0034 → 0035 → 0036 → 0037`.
- **Startup crash (idempotent migrations)**: Migrations 0035/0036/0037 used `op.create_table()` and `op.add_column()` which fail if the DB objects already exist (created earlier via manual Supabase SQL). Converted all three to raw `op.execute()` calls with `CREATE TABLE IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` so `alembic upgrade head` succeeds regardless of prior manual schema changes.

---

## [1.23.1] — 2026-06-11

### Added
- **Admin guide synced to v1.23.1**: `frontend/public/docs/admin-guide.md` updated from v1.13.0 to v1.23.1, documenting all features added since v1.13.0 including billing agencies, billing admin accounts, billing provider reporting, and claim filing deadline reminders.

### Fixed
- **Alembic migration revision collision**: Two migration files both claimed revision `"0034"`. This caused `alembic upgrade head` to fail with a "multiple heads" error at container startup. Resolved by re-sequencing the billing providers migrations to `0034`/`0035`/`0036` with a clean linear chain.

---

## [1.23.0] — 2026-06-11

### Added
- **Billing provider reporting** (`GET /api/v1/admin/stats/billing-providers`): Returns per-agency aggregates — provider count, total claims, billed/paid amounts, and denial rate. Stats cards displayed on the Billing Providers admin page.
- **Claim filing deadline reminders**: Every new claim (Availity or manual) automatically gets a `filing_deadline_date` set to service_date + 365 days. A new `days_until_filing_deadline` computed field is returned on `ClaimRead`. A coloured deadline chip appears in the visit form claim panel (gray > 30 days, amber 8–30 days, red ≤ 7 days or overdue). Automated emails are sent at 30, 14, 7, 3, 1, and 0 days before the deadline. Migration `0036`.

---

## [1.22.0] — 2026-06-11

### Added
- **`billing_admin` role**: New user role for billing agency staff. Billing admins log in with a restricted sidebar (Agency Claims + Settings only) and can view and update EOB outcomes for claims from their managed billing provider's doulas. New endpoints `GET /billing-admin/claims` and `PUT /billing-admin/patients/{id}/visits/{type}/claims/manual`. Migration `0035` adds `managed_billing_provider_id` to users.
- **Admin Impersonation ("View As User")**: Admins can click "View as" on any provider row in the Users table to enter a fully-scoped impersonation session. Every data fetch is automatically filtered to that provider's records. A persistent amber banner at the top of every page makes the impersonation session impossible to miss. One click on "Exit" restores the admin session without re-login. Page refresh naturally ends impersonation (in-memory only — nothing persisted). Full HIPAA audit trail: `IMPERSONATE_START` and `IMPERSONATE_END` events with admin ID, target ID, and target email in `extra_context`.
  - Backend: `POST /api/v1/admin/users/{user_id}/impersonate` (admin-only) returns a short-lived provider JWT with `imp` extra claim
  - Backend: `POST /api/v1/auth/impersonate/end` records the audit end event
  - Frontend: `priorSession` Zustand state holds the admin token in memory; `startImpersonation` / `exitImpersonation` swap tokens seamlessly
  - Frontend: `ImpersonationBanner` — fixed amber bar with provider name and Exit button
  - Sidebar admin links auto-hide during impersonation (provider role is active)
  - Admin routes redirect impersonated sessions to `/dashboard` (existing role guard)

---

## [1.21.7] — 2026-06-08

### Added
- **Favicon** (`favicon.ico` + `favicon.png`): dedicated shield-mark icon for browser tabs and Apple touch icon, replacing the scaled-down full logo. `favicon.ico` includes 16/32/48 px sizes for crisp rendering across all browsers.

---

## [1.21.6] — 2026-06-08

### Changed
- **Logo replaced with original brand asset**: swapped the SVG-generated approximation for the professionally designed DoulaShield PNG — clean line-art shield, correct doula+baby figure, proper magenta/orange typography, and HIPAA tagline.

---

## [1.21.5] — 2026-06-08

### Added
- **DoulaShield logo** (`frontend/public/logo.png` + `logo.svg`): the brand logo now displays in the sidebar, mobile top bar, login page, forgot-password page, reset-password page, and browser favicon/tab icon.

---

## [1.21.4] — 2026-06-06

### Fixed
- **Vercel build failure — `visitDate` not in scope**: The claim deadline inline warning in the visit form referenced `visitDate`, which was a local variable inside `handleSubmitClaim()` and not accessible at JSX render scope. Replaced with `watch('visit_date')` called inline, which is valid at any render depth.

---

## [1.21.3] — 2026-06-05

### Fixed
- **In-app manual pages showed v1.13.0 content**: `frontend/public/docs/manual.md` and `frontend/public/docs/admin-guide.md` are the files the app fetches at runtime to render the User Manual and Admin Guide pages. These copies had not been updated since v1.13.0 while the repo-root originals were already at v1.21.0. Synced both copies so the in-app pages now show current content.

---

## [1.21.2] — 2026-06-05

### Fixed
- **MOD-U8 error code description wrong**: The seeded description incorrectly said "Labor & Delivery (T1033) did not include the U8 modifier" — T1033 has no modifier; U8 belongs to T1032 postnatal claims. Description and fix instructions corrected.
- **MANUAL.md inline deadline warning thresholds**: Blue banner description said "more than 30 days since service" but code fires at exactly 30 days; corrected to "30 or more days." Red banner corrected to "within 7 days of the deadline or already overdue."
- **MANUAL.md CAQH dashboard vs. email threshold**: Email reminders start at 30 days remaining; the dashboard banner does not appear until 14 or fewer days remain. Added explicit callout.

---

## [1.21.1] — 2026-06-05

### Fixed
- **ADMIN_GUIDE.md audit action type errors**: Two action strings in the Reference table were incorrect — `MFA_SETUP` (real: `MFA_ENROLL`) and `CREATE_PROVIDER_ACCOUNT` (real: `CREATE_AND_INVITE_PROVIDER`).
- **ADMIN_GUIDE.md missing audit actions**: `GENERATE_AUDIT_PACKET` (v1.17.0) and `RESUBMIT_CLAIM` (v1.20.0) were absent from the reference table.
- **ADMIN_GUIDE.md version header stale**: Updated to `v1.21.0` with a Medicaid Audit Packets section added to the Audit Logs chapter.
- **MANUAL.md missing Dashboard section**: New "Understanding the Dashboard" subsection lists all banners with trigger thresholds and required actions.
- **MANUAL.md missing Box 22 documentation**: Resubmitted claims automatically set CMS 1500 Box 22 to code 7 with the original Availity claim ID.
- **MANUAL.md Claims & Billing section order**: Reordered to Submit → Track Status → Denial/Resubmit → Audit Packet → EOB Scan → Deadlines.
- **MANUAL.md TOC missing sub-entries**: Added indented sub-section links under Claims & Billing and Settings.

---

## [1.21.0] — 2026-06-11

### Added
- **BillingProvider entity** (`billing_providers` table): Billing agencies are now a first-class entity with their own Stripe subscription, group NPI, and contact details. Doulas can be assigned to a billing provider; when assigned, CMS 1500 Box 33/33a uses the agency name and group NPI, and the Stripe subscription is charged to the agency rather than the individual doula. New admin page at `/admin/billing-providers`. Migration `0034`.
- **Billing provider CRUD endpoints** (`GET/POST/PUT/DELETE /admin/billing-providers`, `assign-provider`, `start-subscription`).
- **Claim remittance matching is unaffected** — `_update_claims_from_remittance()` continues to match by `availity_claim_id` (Availity's control number), independent of Box 33a NPI.
- **Sample EOB PDFs and generator script** (`sample_eob.pdf`, `sample_eob_denial.pdf`, `generate_sample_eob.py`): Test remittance files matching DB patient names for EOB scanner testing.

---

---

## [1.20.1] — 2026-06-05

### Fixed
- **Resubmitted Availity claims were landing as duplicates**: `resubmit_claim()` was re-posting the original claim body verbatim, so Availity treated it as a new claim and triggered DUP-CLAIM on the second attempt. The payload now injects `claimFrequencyTypeCode: "7"` (837P replacement indicator) and `originalClaimId` (the prior Availity claim control number) so Availity correctly processes it as a corrected resubmission rather than a duplicate.
- **CMS 1500 Box 22 not populated on resubmissions**: Box 22 (Resubmission Code + Original Ref. No.) was always blank. It now fills with code `7` and the original Availity claim ID when `resubmit_count > 0`; original claims get code `1`.

---

## [1.20.0] — 2026-06-05

### Added
- **Claim error codes with auto-detection**: New `claim_error_codes` table seeds four predefined PA Medicaid error codes — MOD-U8 (Modifier Conflict), SIG-MISS (Missing Signature), DT-RANGE (Date Invalid), DUP-CLAIM (Potential Duplicate). When a claim is denied, the denial reason text is automatically scanned using keyword matching to assign the appropriate code. Unknown X12 adjustment codes (e.g. CO-45) are extracted via regex and auto-created in the DB as custom entries (`is_custom=true`) for future reference.
- **Claim resubmission**: Denied claims now show a "↺ Resubmit Claim" button. For Availity claims, the original claim payload stored in `claim_data` is re-posted to Availity and the same record is updated with the new submission ID. For manual MCO claims, the status is reset to `submitted` so the provider can track the new outcome. Each resubmission increments `resubmit_count` for audit visibility.
- **Error code detail card in denied claim UI**: When a matched error code exists, the visit form claim panel shows a colour-coded detail card with the code title, description, clinical risk level, and step-by-step fix instructions — giving providers immediate actionable guidance without leaving the page.
- **`GET /api/v1/claim-error-codes`**: New endpoint returns all error codes (predefined and auto-discovered custom codes) for reference.
- **`POST /api/v1/patients/{patient_id}/visits/{visit_type}/claims/resubmit`**: New resubmit endpoint; returns the updated `ClaimRead` after resubmission.

### Changed
- `ClaimRead` schema now includes `error_code: str | null`, `resubmit_count: int`, `denial_reason: str | null`, and `remittance_id: uuid | null`.
- `ManualClaimUpsert` accepts an optional `denial_reason` field so providers logging a denied paper EOB can record the reason.

---

## [1.19.3] — 2026-06-05

### Fixed
- **Timer and End Visit button hidden behind amber location warning**: When a provider started a visit more than 500 ft from the client's address, the amber distance-warning panel was shown as a mutually exclusive branch of a ternary, completely hiding the elapsed-time timer and End Visit button. Restructured the in-person panel so the amber warning and the green timer/End Visit panel are both rendered when the visit is started — the amber block now appears above the green panel rather than replacing it.

---

## [1.19.2] — 2026-06-05

### Fixed
- **EOB PDF upload — "This page couldn't load" crash**: The Reports page EOB scanner does not supply a `patient_id` (not applicable for a provider-level remittance scan). The `scan_handbook` endpoint had `patient_id` as a required form field, so FastAPI returned a 422 whose `detail` is an array of validation-error objects. `ImageUploadScanner` passed that array to `setError`, React threw "Objects are not valid as a React child", and Next.js replaced the page with its error screen. Fixed by making `patient_id` optional (`= None`) in `scan_handbook` and updating `ImageUploadScanner` to only use `detail` as the error string when it is actually a plain string — FastAPI validation arrays are silently ignored and fall back to the generic user-facing message.

---

## [1.19.1] — 2026-06-05

### Fixed
- **EOB PDF scanning — switched from Anthropic PDF beta API to pypdf text extraction**: The Anthropic PDF document beta (`betas=["pdfs-2024-09-25"]`) is not supported by `claude-haiku-4-5-20251001`, causing a 422 error on every PDF upload. Replaced with pypdf text extraction: `PdfReader` pulls text from all pages and sends it as a standard text prompt — cheaper, model-agnostic, and no beta flags required. Works for all digitally-generated EOBs from MCO portals. Scanned-image PDFs (which produce no extractable text) now surface a clear user-facing message instead of a generic error.
- **EOB scan error messages**: Frontend now shows the specific detail from the backend (e.g. "This PDF appears to be a scanned image — please photograph the paper remittance instead") rather than a generic "Could not read" fallback.

---

## [1.19.0] — 2026-06-05

### Added
- **EOB / Remittance scan — PDF upload support**: Providers can now upload a digital EOB PDF directly instead of photographing a paper remittance. The `ImageUploadScanner` component gains an `acceptPdf` prop; when enabled it shows two buttons: "Take photo" (camera, mobile-optimised) and "Upload PDF / image" (file picker, accepts JPEG, PNG, PDF). Both EOB scan entry points — the central scanner on the Reports page and the per-visit scanner on manual-MCO claim sections — now accept PDFs. Maximum upload size increased to 20 MB.

---

## [1.18.5] — 2026-06-05

### Fixed
- **Audit Packet — ZipZign signed MA 91 PDF inserted at page 7 instead of page 5**: The ZipZign pages were appended after all six narrative sections. Fixed the assembly order to split the narrative at the MA 91 section boundary (page index 3) and insert the ZipZign pages immediately after, so the executed signature document follows directly after the MA 91 Certification section before Provider Credentials and Billing Record.

---

## [1.18.4] — 2026-06-05

### Fixed
- **Audit Packet — ZipZign signed MA 91 PDF still 404**: The download URL was wrong. ZipZign's PDF-serve endpoint is `GET /pdf/:id` (not `/api/documents/:id/download`). The document ID alone provides security (128-bit unguessable); no Authorization header is required. Fixed the URL and removed the auth header from the fetch call.

---

## [1.18.3] — 2026-06-05

### Fixed
- **CMS 1500 — Box 24A service date year shown as 4 digits**: Changed `svc_yy` formatting from `%Y` (2026) to `%y` (26) so both the "From" and "To" year fields in Box 24A render as 2-digit years, matching the CMS 1500 standard. Both the `date` and string-split code paths are corrected. DOB fields (Box 3, Box 11a) remain 4-digit.

---

## [1.18.2] — 2026-06-04

### Fixed
- **CMS 1500 — Radio buttons (Box 1, 3, 11a) not visually rendering in browser PDF viewer**: Switched from relying solely on AcroForm `/AS` + `NeedAppearances` (which Chrome's PDFium renderer does not always honour) to drawing explicit filled dots at the exact widget center coordinates using a reportlab overlay. The overlay is applied after all AcroForm writes and signature overlays, so radio selections are painted as real PDF graphics that render in every viewer unconditionally.
- **CMS 1500 — Text fields (Box 24A and others) not rendering without NeedAppearances support**: Changed `auto_regenerate=False` → `auto_regenerate=True` in the pypdf field-fill call so proper `/AP /N` appearance streams are generated for every text field. Fields are now visible in viewers that ignore `NeedAppearances`.
- **Audit Packet — ZipZign-signed MA 91 PDF missing even when patient has signed**: Removed the `ma91_status == "signed"` guard from the ZipZign download in the audit packet endpoint. The download is now attempted whenever `ma91_zipzign_request_id` is set, because the webhook that flips the status to "signed" may not have fired if `BACKEND_URL` was misconfigured at the time of signing. The PDF is included only if the API returns valid PDF bytes. Structured `log.info`/`log.warning` messages are emitted so failures are diagnosable in Railway logs.

---

## [1.18.1] — 2026-06-04

### Fixed
- **CMS 1500 — Radio buttons (Box 1 Medicaid, Box 3 Sex, Box 11a Insured Sex) not rendering in PDF viewers**: Added `NeedAppearances=True` to the AcroForm after all field writes. Without this flag, viewers like Chrome's built-in PDF renderer use pre-built appearance streams (which are blank in the form template) rather than regenerating visuals from the stored `/V` and `/AS` values. This is the root cause of radio buttons writing correctly at the byte level (confirmed) but not displaying visually.
- **CMS 1500 — Box 24A "To" date year blank**: Root cause was also `NeedAppearances` — the field value was being written correctly but not rendered. Resolved by the same fix above.
- **CMS 1500 — Box 29 (Amount Paid) never populated**: Added `amt_paid` to `generate_pdf`'s `text_fields` dict, sourced from a new `claim_data` parameter. The `download_cms1500` endpoint now fetches the claim record for the visit and passes the paid amount; when a claim is paid the amount appears in Box 29.
- **Audit Packet — ZipZign signed MA 91 PDF not included**: Status comparison is now case-insensitive (`ma91_status.lower() == "signed"`) to handle both `"signed"` and `"Signed"` from the webhook. The `%PDF` header check now scans the first 10 bytes (`b"%PDF" in resp.content[:10]`) to tolerate any leading BOM or whitespace.

---

## [1.18.0] — 2026-06-04

### Added
- **CMS 1500 — Box 3 & Box 11a sex radio buttons now render correctly**: Rewrote `_set_radio` to walk `writer.pages[0]/Annots` directly instead of the AcroForm `/Fields` tree. After `writer.append()`, the AcroForm field-tree objects are copies that are disconnected from the widget annotations the PDF viewer actually renders. Walking the page annotations directly sets `/AS` on the objects that matter. The AcroForm `/V` is still updated for form-aware readers. Fixes persistent "sex not selected" issue on both Box 3 and Box 11a.
- **Audit Packet — ZipZign signed MA 91 PDF appended**: When a telehealth visit has a ZipZign e-signature with status `signed`, the actual signed PDF is fetched from the ZipZign API and inserted into the audit packet after the MA 91 certification section. Auditors receive the full executed document, not just the request ID.
- **Client profile — Medicaid card scan indicator**: When a patient's Medicaid card has been previously scanned, a small "Card scanned" badge with a camera icon now appears next to the MCO line in the client profile header, so providers can confirm at a glance that the card is on file.

---

## [1.17.3] — 2026-06-04

### Fixed
- **Audit Packet — Provider Legal Name still shows "Admin"**: Changed `audit_packet_service` to prefer `billing_provider_name` over `full_name` when populating the provider name in the packet. The `billing_provider_name` field (set in provider Settings) is the formal legal name; `full_name` is a login display name and may be "Admin" for admin accounts.
- **CMS 1500 — Box 11a (Insured Sex) still not selected**: Corrected the `ins_sex` AcroForm radio on-state values. A prior fix incorrectly changed them from `/FEMALE`/`/MALE` to `/F`/`/M`. Inspection of the actual PDF AcroForm confirmed: `sex` (Box 3) uses `/F`/`/M`, but `ins_sex` (Box 11a) uses `/FEMALE`/`/MALE`. Reverted to the correct values.

---

## [1.17.2] — 2026-06-04

### Fixed
- **Audit Packet — "Signed At" blank in Section 3**: `ma91_signed_at` was placed in `patient_data` by the endpoint but `audit_packet_service` was reading it from `visit_data`. Fixed by reading from the correct dict (`patient_data`). Same fix applied to `ma91_signature_bytes`.
- **Audit Packet — Provider Legal Name shows "Admin"**: The `download_audit_packet` endpoint was fetching provider credentials using `current_user.id` (the requesting user). When an admin downloads the packet, "Admin" appeared as the provider name. Fixed to use `patient.provider_id` so the patient's actual assigned provider is always shown.
- **CMS 1500 — Box 11a (Insured Sex) not selected**: `_set_radio` was called with `/FEMALE`/`/MALE` for the `ins_sex` field, but the AcroForm states use `/F`/`/M` (same as Box 3's `sex` field). Fixed to use `/F`/`/M`.
- **Audit Packet — CMS 1500 page 2 appearing merged**: `audit_packet_service` was appending all pages of the CMS 1500 PDF (front + back/instructions). Only the front (page 0) is now appended.
- **Audit Packet — No Medicaid card note when none scanned**: When a patient has no Medicaid card image on file, Section 1 showed nothing. Now shows "No Medicaid card scan on file for this patient."

---

## [1.17.1] — 2026-06-04

### Fixed
- **Audit Packet button placement**: The "📋 Download Audit Packet" button was inside the CMS 1500 preview modal, which is not shown once a claim has been submitted. Moved it to the claim status panel (alongside "Refresh status" / "Update status") so it is always accessible whenever a claim record exists.

---

## [1.17.0] — 2026-06-04

### Added
- **Medicaid Audit Packet PDF**: A new "📋 Audit Packet ↓" button appears in the CMS 1500 modal when a claim exists. Clicking it downloads a comprehensive PDF audit packet containing: Cover/Claim Summary, Member Information & Eligibility Verification (with Medicaid card image), Service Documentation (SOAP notes, visit times, location), MA 91 Patient Certification (with signature image), Provider Credentials (CAQH/PROMISe™/PCB/liability/MCO contracts with expiry calculations), and Billing Record — with the CMS 1500 appended as final pages. Audit log action `GENERATE_AUDIT_PACKET` recorded on every generation.

---

## [1.16.2] — 2026-06-04

### Fixed
- **App crash at startup**: `npi.py` imported `CurrentUser` from `app.schemas.auth` where it is not defined (correct source is `app.dependencies`). This `ImportError` prevented uvicorn from starting, causing every Railway health check to fail since the 1.16.0 deployment.

---

## [1.16.1] — 2026-06-03

### Fixed
- **Deployment startup failure**: Alembic migrations 0030, 0031, and 0032 used `op.add_column` which raises an error if the column already exists (e.g. after a manual Supabase SQL run). Replaced with `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` so migrations are idempotent and the service starts correctly regardless of prior schema state.

---

## [1.16.0] — 2026-06-03

### Added
- **PCB Perinatal Certification alert**: providers can record their last PCB certification date in Settings (2-year/730-day cycle). Dashboard shows amber banner when ≤60 days remain, red when overdue. Automated email reminders at 60, 30, 14, 7, 0, and daily for 7 days overdue (scheduler job at 07:55 UTC). Alembic migration 0030 adds `pcb_last_certified_on` to `users`.
- **Liability Insurance expiry alert**: providers record their insurance expiry date directly in Settings. Dashboard shows amber banner when ≤30 days remain, red when expired. Automated email reminders at 30, 14, 7, 0, and daily for 7 days after expiry (scheduler job at 08:00 UTC). Alembic migration 0031 adds `liability_insurance_expires_on` to `users`.
- **MA 589 in-app flag and email reminder**: per-patient `ma589_signed_date` field (migration 0032, `patients` table). When a patient has a Prenatal 1 visit started but no MA 589 signed date, an amber "MA 589 not signed" badge appears on the client overview page. The scheduler (08:05 UTC) emails the provider for each patient in this state daily.

### Changed
- **MA 89 → MA 589**: renamed throughout — OCR prompt key (`ma_89` → `ma_589`), visit form section label, scan button label, and all documentation references updated to the correct Pennsylvania form number.

---

## [1.15.1] — 2026-06-03

### Fixed
- **TOC anchor links in User Manual and Admin Guide**: clicking a table-of-contents entry did nothing because `marked` v10+ no longer emits `id` attributes on headings by default. The rendered HTML is now post-processed to inject GitHub-style slug IDs (e.g. "Billing & Escrow" → `id="billing--escrow"`), so every TOC bookmark scrolls to the correct heading.

---

## [1.15.0] — 2026-06-03

### Added
- **NPPES NPI lookup on client profile**: a "Verify NPI" button now appears below the Referring Provider NPI field in the client edit form. A successful lookup auto-fills the Referring Provider Name field (CMS 1500 Box 17) from NPPES — no manual name entry needed.

---

## [1.14.1] — 2026-06-03

### Fixed
- **NPI lookup CORS error**: direct browser requests to `npiregistry.cms.hhs.gov` were blocked by CORS. Moved the lookup to a backend proxy (`GET /api/v1/npi/lookup?number=`) that calls NPPES server-side via httpx and returns the parsed name and taxonomy.

---

## [1.14.0] — 2026-06-03

### Added
- **NPPES NPI lookup**: a "Verify NPI" button now appears below the NPI field on the Settings page and below the Referring Provider NPI field on the visit claim form. Clicking it queries the public NPPES Read API and displays the provider's registered name and primary taxonomy as confirmation. On the visit form, a successful lookup also auto-saves the referring doctor's name to the patient record, populating CMS 1500 Box 17 without manual entry.

---

## [1.13.1] — 2026-06-03

### Fixed
- **"Failed to load clients" on page load**: eliminated a race condition where page-level `useEffect` hooks fired before the auth refresh completed, causing `getAccessToken()` to return `null` and all API calls to 401. The app layout now waits for the auth store's `isLoading` flag to clear before rendering child pages, ensuring every page receives a valid token on first render.

---

## [1.13.0] — 2026-06-03

### Added
- **In-app User Manual and Admin Guide**: a **Help** section now appears at the bottom of the sidebar for all users. Providers see a **User Manual** link; admins also see an **Admin Guide** link. Both open as styled, scrollable pages inside the app. The admin-guide page redirects non-admin users to the dashboard. Markdown files are served from `public/docs/` and rendered with `marked` + Tailwind Typography.

---

## [1.12.4] — 2026-06-03

### Fixed
- **Admin welcome email incorrectly included $99 deposit link**: the `send-welcome-email` endpoint created a Stripe Checkout link for all users regardless of role. Added a `provider.role == "provider"` guard so admin accounts never receive a deposit link when their welcome email is resent.

---

## [1.12.3] — 2026-06-03

### Fixed
- **Railway healthcheck failure (idempotent migrations)**: migrations 0026–0028 used `op.add_column()` which raises "column already exists" when those columns were pre-created via manual Supabase SQL, causing `alembic upgrade head` to exit non-zero and uvicorn to never start. All three migrations now use raw `ALTER TABLE … ADD COLUMN IF NOT EXISTS` so they succeed regardless of current DB state. Added migration 0029 to formalise the `welcome_email_sent_at` column in the Alembic chain (column already exists in DB from prior manual SQL).

---

## [1.12.2] — 2026-06-03

### Fixed
- **"Error undefined" on Send Welcome Email**: when Resend reported a delivery failure the backend threw an unhandled exception that returned a non-JSON response, causing the frontend toast to show "Error: undefined". The email-send call in the `send-welcome-email` endpoint is now wrapped in a try/except that returns HTTP 502 with a readable detail message. The `welcome_email_sent_at` timestamp update is wrapped in its own try/except so a DB commit failure never breaks the endpoint. The frontend error handler now falls back to a static string when `detail` is absent from the response, preventing the "undefined" display.

---

## [1.12.1] — 2026-06-03

### Added
- **Last Emailed column in admin Users table**: a new **Last Emailed** column shows the date a welcome email was most recently sent to each user, or "—" if no email has ever been sent (e.g. accounts created via **Create Account Only**). The timestamp is set automatically when **Create & Send Email** or **Send Welcome Email** is used. New DB column `users.welcome_email_sent_at` (added via migration 0029 SQL).

---

## [1.12.0] — 2026-06-03

### Added
- **Send Welcome Email for any first-time user**: the **Send Welcome Email** button in the admin Users table now appears for any user — provider or admin — whose `last_sign_in_at` is null (i.e. they have never logged in). Previously it only appeared for providers without a paid deposit. Admin welcome emails continue to use role-appropriate copy (no "provider account" language). New DB column `users.last_sign_in_at` (migration 0028) is set automatically on every successful login.

---

## [1.11.1] — 2026-06-03

### Fixed
- **PROMISe™ portal URL**: corrected link from `promise.dpw.state.pa.us` (old domain) to `promise.dhs.pa.gov` in the Settings page, dashboard banner, reminder email CTA button, and MANUAL.md.

---

## [1.11.0] — 2026-06-03

### Added
- **PROMISe™ 5-year re-enrollment reminder**: providers can record their last PA DHS PROMISe™ enrollment date in Settings. A live expiry preview shows the next due date in green (>90 days), amber (1–90 days), or red (overdue). The dashboard shows an amber or red banner when re-enrollment is due within 90 days or overdue. A daily APScheduler job (07:45 UTC) sends automated email reminders at 365, 180, 90, 30, 14, 7, and 0 days before expiry and daily for the first 7 days overdue. New DB column `users.promise_last_enrolled_on` (migration 0027); `GET` and `PATCH /api/v1/auth/me/provider-settings` now include `promise_last_enrolled_on` and `promise_days_remaining`.

---

## [1.10.0] — 2026-06-03

### Added
- **CAQH 90-day attestation reminder**: providers can record their last CAQH ProView attestation date in Settings. A live expiry preview shows the next due date in green (>14 days), amber (1–14 days), or red (overdue). The dashboard shows an amber or red banner when attestation is due within 14 days or overdue. A daily APScheduler job (07:30 UTC) sends automated email reminders at 30, 14, 7, and 0 days before expiry and daily for the first 7 days overdue. New DB column `users.caqh_last_attested_on` (migration 0026); `GET` and `PATCH /api/v1/auth/me/provider-settings` now include `caqh_last_attested_on` and `caqh_days_remaining`.

---

## [1.9.0] — 2026-06-03

### Added
- **Audit log filters**: four filter controls on the Audit Logs page — action type (exact match), user email (partial match), from date, and to date. Logs are no longer auto-loaded on mount; the admin applies filters first. Shows entry count and a "limit reached" notice at 200 entries. Backend adds `action`, `user_email`, `start_date`, `end_date` query params to `GET /admin/audit-logs`; email filter uses case-insensitive partial match via `ilike`; date range is inclusive on both ends.

---

## [1.8.1] — 2026-06-03

### Added
- **MANUAL.md**: provider-facing user manual covering all features through v1.8.0 — getting started, managing clients, documenting visits, MA 91 signatures, claims & billing, reports dashboard, settings, and reference tables for billing codes, MCO submission channels, and PA HealthChoices zones
- **ADMIN_GUIDE.md**: admin-only guide covering account management, billing/escrow, admin-only settings (ZipZign API key), audit logs, and a full reference table of audit action types
- **Auto-update hook**: PostToolUse reminder now includes instructions (3) to update MANUAL.md and ADMIN_GUIDE.md when new provider-facing or admin-facing features are shipped

### Fixed
- **Audit log blank page**: the audit log page now shows an error message if the API call fails (previously failed silently, showing an empty table with no explanation) and a "No entries yet" message when the log is genuinely empty
- **INET column rejecting non-IP strings**: `audit_logs.ip_address` changed from PostgreSQL INET to TEXT (migration 0025); the `get_client_ip` fallback no longer returns the string `"unknown"` (returns NULL instead), and the daily remittance sync no longer passes `"scheduler"` as an IP address — both would have caused silent insert failures on any request where the real client IP was unavailable

---

## [1.8.0] — 2026-06-02

### Added
- **Central EOB scanner on Reports page**: providers can scan a full paper remittance once from `/reports` and see all extracted claim lines matched against their entire client roster; highlighted rows link to the matched client, with "Apply ↓" buttons to update claim status in bulk without visiting each client individually
- **Provider-level claims endpoint**: `GET /api/v1/claims` returns all claims for the authenticated provider (no patient-id filter), used by the central EOB scanner to cross-reference service dates against existing claim records

---

## [1.7.0] — 2026-06-02

### Changed
- **Multi-claim EOB scan**: the `remittance_eob` OCR prompt now extracts every claim line on a remittance page as an array (patient name, service date, procedure code, billed/paid amounts, status, denial reason, plus check number and payment date at the header level) — previously only one claim per scan
- **EOB review panel**: instead of auto-applying the single extracted claim, the visit form now shows a review table listing all N extracted claims; rows matching the current patient are highlighted and can be applied individually; rows for other patients show an "other patient" label with a note to navigate to their visit page
- **Auto-apply**: when exactly one EOB row matches the current patient by name, it is still applied automatically (preserving the fast path for single-patient EOBs)
- **Backward compat**: if the OCR response is in the old single-claim format, it is applied directly with no review step

---

## [1.6.0] — 2026-06-02

### Added
- **Daily Availity remittance sync**: APScheduler job runs at 07:00 UTC (≈ 02:00 ET) daily, fetches 30-day rolling remittances for all providers with Availity credentials, parses claim payment lines, and updates matched claim records with paid amount, normalized status, and denial reason codes
- **Manual EOB scan**: providers can photograph paper remittances from manual MCOs (UPMC, HPP, FFS); Claude OCR extracts status, paid amount, and denial reason, auto-updating the manual claim record
- **Denial reason visibility**: denial reason (e.g. "CO-45: Charge exceeds fee schedule") now displays in the claim status panel for both Availity and manual claims
- **Internal trigger endpoint**: `POST /internal/trigger-remittance-sync` with `X-Internal-Secret` header for ops/testing
- **`remittance_eob` OCR page type**: new OCR prompt for scanning insurance EOBs and remittance advice documents

### Changed
- `ManualClaimUpsert` accepts optional `denial_reason` field for paper EOB updates

### Migration
- **0024**: adds `denial_reason TEXT NULL` and `remittance_id UUID NULL FK` to `claims`

---

## [1.5.2] — 2026-06-02

### Added
- **Reports card on dashboard**: dashboard now shows a "Reports" card alongside "Clients", linking to `/reports` with a short description

---

## [1.5.1] — 2026-06-02

### Fixed
- **Manual claim billed amount**: when a provider logs a manual claim status (UPMC For You, Health Partners Plans, etc.), `billed_amount` is now automatically derived from the visit type's billing rate (`$100` prenatal/postnatal, `$1,000` labor, `$175` crisis/loss) instead of being left `null`; existing manual claims with a `null` billed amount are also backfilled on the next status update

---

## [1.5.0] — 2026-06-02

### Added
- **Provider Stats & Reports dashboard** (`/reports`): new page showing total active clients, visits completed vs. documented, claim pipeline tiles (Submitted/Processing/Paid/Denied with counts and amounts), revenue summary with collection rate, and a per-MCO breakdown table
- **`GET /api/v1/stats/summary`**: server-side aggregation endpoint — no PHI returned; counts are derived from `patients`, `visits`, and `claims` tables in a single set of SQL queries
- **MCO breakdown table**: merges claim data with `mco_contracts` from provider settings; contracted MCOs always appear (even with zero claims) with a green ✓ badge and contract date; uncontracted MCOs that appear in claims data are also shown without the badge
- **Reports nav link**: "Reports" added to the provider sidebar between Clients and Settings

---

## [1.4.0] — 2026-06-02

### Added
- **ACCESS card fallback scan**: when scanning an MCO card that doesn't include the Medicaid recipient ID, an amber prompt appears directing the provider to scan the client's Pennsylvania ACCESS card; scanning the ACCESS card populates the Medicaid ID field and dismisses the prompt — applies to both the new-client form and the edit-profile form
- **ACCESS card OCR prompt**: new `access_card` page type extracts `medicaid_id` and `name` from the PA DHS EBT-style ACCESS card; accepted by the `/ocr/handbook` endpoint
- **Medicaid ID in edit-profile scan**: the edit-profile MCO card scan handler now also captures `medicaid_id` when present (previously ignored), and includes it in the PATCH body

---

## [1.3.0] — 2026-06-02

### Added
- **Claim status visibility — color-coded badges on visit form**: existing Availity claims now show a colored pill badge (amber=Submitted, blue=Processing, green=Paid, red=Denied) with claim ID, paid amount when present, and submission/last-checked dates; replaces the plain green box
- **Manual claim status logging**: for manual MCOs (UPMC For You, Health Partners Plans, Highmark Wholecare, FFS), a "Log claim status" form on the visit page lets providers record Submitted / Paid / Denied with date and optional paid amount; saving is idempotent (update, not duplicate)
- **Claim status dots on client overview cards**: visit cards in the client overview show a small colored dot when a claim exists for that visit slot (green=paid, amber=submitted, blue=processing, red=denied); no dot means no claim yet
- **Migration 0023**: adds `visit_type VARCHAR(30)` and `is_manual BOOLEAN` columns to the `claims` table; `visit_type` links each claim back to its visit slot for accurate per-visit display

### Fixed
- **Claim matched by visit_type**: the visit form now filters claims by `visit_type` instead of taking the first claim returned; providers with multiple patients or visits no longer see the wrong claim status

---

## [1.2.3] — 2026-06-02

### Added
- **Show/hide toggle on login password field**: eye icon button inside the password input reveals or masks the entered password

---

## [1.2.2] — 2026-06-02

### Fixed
- **CMS 1500 Box 11c blank for FFS patients**: FFS (Fee-for-Service) has no MCO plan name; field now left blank instead of showing "Medicaid"

### Added
- **Keystone First in MCO Contracts section**: providers can now record a Keystone First contract separately from AmeriHealth Caritas (they have different payer IDs: 23284 vs 22248)

---

## [1.2.1] — 2026-06-02

### Fixed
- **Highmark Wholecare claim channel corrected to `manual`**: was incorrectly routed through Availity REST API; Highmark Wholecare uses NaviNet for claims, not Availity
- **UHC Community Plan channel corrected to `availity`**: dedicated `uhc_client.py` with PKCE OAuth2 removed; UHC Community Plan accepts Availity EDI clearinghouse (payer ID `04567`)
- **Keystone First payer ID `23284` added**: was entirely absent from `MCO_PAYER_IDS`, breaking eligibility checks and claim submission for all Keystone First patients
- **UHC Community Plan payer ID corrected to `04567`**: was `87726` (commercial UHC only); `04567` is the correct Medicaid Community Plan EDI payer ID
- **Geisinger Health Plan payer ID corrected to `75273`**: was unverified alphabetic code `GEISP`
- **Highmark Wholecare payer ID corrected to `25169`**: was unverified alphabetic code `HMKWC`
- **UPMC For You and Health Partners Plans removed from `MCO_PAYER_IDS`**: these MCOs are `manual` channel — no Availity payer ID needed or valid
- **UPMC For You portal URL corrected** to `https://www.upmchealthplan.com/providers/online`
- **Health Partners Plans portal URL corrected** to `https://www.healthpartnersplans.com/home/providers/claims-and-billing/claim-submissions/` (old URL was a dead domain)
- **Highmark Wholecare portal entry added** to `MCO_PORTAL_LINKS` (needed now that channel is `manual`)
- **OCR Medicaid card scan**: Keystone First is now recognized as a separate MCO from AmeriHealth Caritas; removed the alias that incorrectly collapsed "Keystone First" → "AmeriHealth Caritas"
- **Settings page UHC credentials section removed**: UHC no longer requires separate API credentials; section was presenting providers with unnecessary configuration

---

## [1.2.0] — 2026-06-02

### Added
- **MCO Contracts section on Settings page**: providers can now check off each PA Medicaid MCO they are contracted with and optionally record the contract effective date; data stored as a JSON array in a new `mco_contracts_json` column on `users` (migration 0022); section appears in the Settings form between PA HealthChoices Zone and Availity Credentials

---

## [1.1.0] — 2026-06-02

### Fixed
- **CMS 1500 all radio buttons (Box 11a sex, Box 1 Medicaid, Box 3 sex, Box 27 assignment) blank when any signature overlay was applied**: `_overlay_signature()` was constructing a new `PdfWriter()` and adding only the page via `add_page()`, which discards the AcroForm document catalog stored in the PDF `/Root` object; radio buttons rely on `/AS` appearance state referencing `/AP/N/<state>` entries that require the AcroForm in the catalog — without it, all radio button widget appearances are absent; text fields were unaffected because `update_page_form_field_values` bakes their appearance directly into each widget's `/AP/N` stream; fixed by using `writer.append(base_reader)` (preserves the full document catalog) followed by `writer.pages[0].merge_page(overlay_page)` (merges only the overlay content stream) — identical final visual result, catalog intact
- **CMS 1500 Box 33 billing provider name configurable in Settings**: added `billing_provider_name` field (migration 0021) so the exact name as registered in PROMISe can be stored separately from the account full name; Box 33 (`doc_name`) uses this field with a fallback to `full_name`; Settings page "Billing provider information" section has a new input with help text "Must match exactly as registered in the PROMISe provider portal"
- **CMS 1500 Box 11c insurance plan name not appearing in PDF**: code was writing to `insurance_name` (a field near the top of the form, y≈753pt) instead of `ins_plan_name` (the actual Box 11c field, y≈482pt); also map MCO value "FFS" to "Medicaid" since Fee-for-Service patients are covered by PA Medicaid directly with no MCO intermediary
- **CMS 1500 Box 26 now carries internal visit identifier**: changed from last-8-chars of Medicaid ID to first 8 hex characters of the visit UUID (e.g. `A1B2C3D4`); the MCO echoes this field back on the 835 remittance so claims can be matched to specific visits in the database; falls back to last 8 of Medicaid ID when no visit record exists
- **CMS 1500 claim preview blocked on iOS ("This content is blocked")**: iOS Safari does not render PDFs inside `<iframe>` elements — the browser shows a blocked-content error; on mobile (`< md` breakpoint) the iframe is now hidden and replaced with an "Open PDF ↗" link that opens the blob URL in a new tab where iOS handles it natively
- **CMS 1500 Box 24F and Box 28 charge amounts format corrected**: the form has a pre-printed decimal separator so the value must be entered in cents (e.g. $100.00 → "10000", $1000.00 → "100000"); was incorrectly entering integer dollars ("100") then "100.00" before that
- **CMS 1500 Box 11a and Box 3 sex blank for pre-migration patients**: `patient_data.get("gender", "F")` returns `None` when the key exists with a null value — patients created before migration 0015 may have `NULL` gender since `server_default` only applies to new rows; changed to `patient_data.get("gender") or "F"` so `None` and empty string both fall back to Female
- **CMS 1500 Box 12 date mismatched Box 31**: `pt_date` was populated from the MA 91 signing timestamp while `physician_date` (Box 31) uses the service/visit date; since both boxes now carry the provider signature they should show the same date — `pt_date` now uses the service date
- **CMS 1500 signature boxes reassigned**: Box 12 and Box 31 now both carry the provider signature image; Box 13 carries the client MA 91 signature image; updated text-field clearing logic to match (`pt_signature` clears when provider image present, `ins_signature` clears when MA 91 image present); Box 13 overlay uses AcroForm field rect coordinates x=412, y=410, w=173, h=25
- **CMS 1500 signature images placed outside Box 12 and Box 31**: `_overlay_signature()` was called with hardcoded coordinates (x=27, y=257 and x=27, y=182) that placed both images in the middle of the form body; corrected to the exact AcroForm field rect positions extracted from the blank PDF — Box 12 `pt_signature` at x=56, y=410 (w=180, h=25 pts) and Box 31 `physician_signature` at x=20, y=50 (w=156, h=25 pts)
- **CMS 1500 signature images never appearing**: three bugs combined to prevent actual signatures from rendering — (1) `reportlab` was missing from `requirements.txt`, causing `_overlay_signature()` to silently catch the `ImportError` and return the unchanged PDF on every call; (2) AcroForm text fields (`pt_signature`, `physician_signature`) render as PDF annotations on top of the page content stream, hiding the image overlay beneath them — fixed by clearing those fields to `""` when real signature bytes are available so the widget renders blank and the underlying image shows through; (3) overlay height was 18 pts (≈¼ inch) — too small for a readable signature, increased to 30 pts with width widened to 200 pts; also added `log.warning()` to `_overlay_signature` so future failures are visible in Railway logs instead of swallowed silently

### Added
- **Policy group number extracted from Medicaid card scan**: the `medicaid_card` OCR prompt now extracts `policy_group` (group/plan number printed on the card); stored in a new `policy_group VARCHAR NULL` column on `patients` (migration 0020); CMS 1500 Box 11 (Insured's Policy/Group Number) uses the extracted group number when available and falls back to the Medicaid ID when the card has no separate group field; `policy_group` is surfaced in `PatientCreate`, `PatientUpdate`, and `PatientRead` schemas and handled in the new-client scan, edit-profile scan, and PATCH body on both frontend pages; client profile header displays "Policy / Group: …" when set; edit form includes a labeled text input so providers can view and correct the value
- **USPS ZIP+4 lookup as authoritative fallback**: new `usps_service.py` calls the USPS v3 REST API (`apis.usps.com/addresses/v3/address`) using OAuth2 client credentials; `_enrich_zip4()` in `claims.py` tries Radar first and falls back to USPS when Radar has no ZIP+4 for an address; OAuth token is cached in-process for up to 8 hours; requires `USPS_CLIENT_ID` and `USPS_CLIENT_SECRET` Railway variables (Consumer Key / Secret from an app created at developers.usps.com)
- **`GET /api/v1/addresses/zip4` endpoint**: authenticated endpoint that accepts an `address` query parameter and returns `{"address": "<enriched>"}` with ZIP+4 appended when available; uses the same Radar → USPS pipeline as PDF generation; used by the address autocomplete for real-time enrichment after suggestion selection
- **Address autocomplete enriches via backend ZIP+4 endpoint**: after the user selects a suggestion, `AddressAutocomplete.tsx` calls the new backend endpoint (server-side Radar secret key + USPS fallback) instead of the previous frontend-only Radar forward geocode; coordinates are unchanged, only the ZIP+4 suffix is added; requires no additional frontend environment variables

### Fixed
- **CMS 1500 Box 24J NPI in wrong sub-row**: the rendering provider NPI was written to `local1a` (the upper shaded qualifier sub-row) instead of `local1` (the lower main data sub-row where the actual NPI number belongs); also added qualifier `"1"` (NPI type) to `local1a` per CMS 1500 instructions
- **`_enrich_zip4` no-ZIP+4 case now logs INFO**: when Radar returns 200 but has no ZIP+4 for the address, an INFO log now explains the address must be updated manually with the full 9-digit ZIP; previously the fallback was silent
- **CMS 1500 Box 5 ZIP truncated to 5 digits**: `_parse_address()` had `[:5]` on all three ZIP extraction branches, stripping the `+4` extension from nine-digit ZIP codes; removed the truncation so addresses stored with ZIP+4 now flow through to Box 5 intact
- **ZIP+4 never obtained from Radar.io**: Radar's autocomplete endpoint returns only 5-digit ZIP in suggestions; after the user selects a suggestion `AddressAutocomplete` now calls `geocodeAddress` (Radar forward geocode, rooftop-level) in the background and updates the stored address label with the ZIP+4 value when available; `geocodeAddress` also returns a `label` field so the same enrichment applies at form-submit time for manually typed addresses
- **CMS 1500 Box 5/33 still showing 5-digit ZIP for existing patients**: frontend enrichment only applies to newly entered addresses; added server-side `_enrich_zip4()` in `download_cms1500` that calls Radar forward geocode (backend `RADAR_API_KEY`) immediately before `generate_pdf()` so both patient address (Box 5) and provider address (Box 33) receive ZIP+4 on every PDF regardless of what is stored in the database; falls back silently when key is absent
- **Radar ZIP+4 enrichment silently failing with 403**: `_enrich_zip4()` was catching all exceptions without logging so a 403 "Host not in allowlist" error from Radar (caused by using the publishable key instead of the secret key) appeared as a no-op; added explicit HTTP status check with a `log.warning()` that explains the key type requirement (`prj_live_sk_…` secret key required, not the publishable key); also switched to using Radar's `formattedAddress` field directly rather than rebuilding the string from components
- **CMS 1500 Box 11 always blank**: `ins_policy` (Insured's Policy/Group Number) was never included in the text fields dict; for PA Medicaid the Medicaid ID serves as the policy number and is now written to Box 11 on every generated PDF; Box 11a DOB/sex fields were already correct when patient DOB is stored

### Added
- **CMS 1500 multi-box update**: fills significantly more boxes on the generated PDF — Box 7 (insured address mirrors patient), Box 11a (insured DOB/sex mirrors patient), Box 11c (MCO name), Box 11d (other insurance YES/NO radio), Box 12 (MA 91 patient signature image + date), Box 13 ("Signature on File"), Box 17 (referring provider name — was previously empty), Box 17b (referring provider NPI — was swapped with Box 17), Box 25 (provider SSN with SSN radio checked; stored encrypted, never returned in API), Box 26 (last 8 of Medicaid ID as patient account number), Box 31 (provider signature image overlaid via reportlab+PIL), Box 32 (alternate location from visit if set), Box 33 phone split into area code and number; signature images for Box 12 (MA 91 canvas) and Box 31 (provider signature) are fetched from Supabase Storage and embedded as overlay layers on the AcroForm PDF
- **Referring provider name field on patient profile**: `referring_provider_name` column (migration 0019, VARCHAR 100) added to `patients`; editable in new client form and edit profile form; displayed in the client profile header; passed to CMS 1500 Box 17
- **Other insurance flag on patient profile**: `has_other_insurance` boolean column (migration 0019, default false) added to `patients`; toggle checkbox in new client form and edit profile form; controls Box 11d YES/NO radio in the CMS 1500 PDF
- **Provider SSN (Box 25)**: `provider_ssn_encrypted` column (migration 0019) added to `users`; entered as a password field in Settings "Billing Credentials" section; stored using Fernet encryption, never returned after save; a "●●●●●●●●● saved" placeholder and green badge confirm when set; passed to Box 25 of the CMS 1500 PDF
- **Provider signature (Box 31)**: `provider_signature_path` column (migration 0019) added to `users`; drawn on a 400×120 px `SignaturePad` canvas in Settings; saved via `POST /api/v1/auth/me/provider-signature` which uploads PNG to Supabase Storage and persists the path; fetched and overlaid on CMS 1500 Box 31 at PDF generation time
- **MA 89 OCR scan on prenatal_1 visit**: when `visitType === 'prenatal_1'` an indigo-highlighted "MA 89 — Physician Certification Form" scan section appears above the SOAP section; Claude Haiku extracts `referring_provider_name` and `referring_provider_npi` and immediately PATCHes the patient record via `handleMa89Scanned`; a confirmation line shows the saved doctor name and NPI; the `ma_89` page type added to `ocr_service.py` prompts and the OCR endpoint validation
- **CMS 1500 preview modal expanded**: the preview table now shows Boxes 7, 11a, 11c, 11d, 12, 13, 17, 17b, 25, 26, 31, 32 with live data, green/amber status indicators for provider SSN and signature, and a red warning when Box 17b (referring NPI) is missing

### Changed
- **Address autocomplete switched from Photon to Radar.io (with Photon fallback)**: `geocodeAddress()` and `suggestAddresses()` in `geo.ts` now use Radar.io when `NEXT_PUBLIC_RADAR_API_KEY` is set (100k free requests/month, structured `stateCode` field, no state-name lookup table needed); when the key is absent both functions automatically fall back to Photon (komoot.io, no key required) so autocomplete works in all environments out of the box; CSP `connect-src` allows both `api.radar.io` and `photon.komoot.io`; `NEXT_PUBLIC_RADAR_API_KEY` added to `.env.example`

### Fixed
- **CMS 1500 Box 1 — Medicaid checkbox never checked**: `_set_radio()` was iterating over page `/Annots` looking for the radio-group parent by `/T` field name, but in this PDF's AcroForm the parent (carrying `/T`) lives in the `/AcroForm/Fields` array while the page annotations are the child widgets (which have no `/T`); the loop always found nothing; rewrote to walk the AcroForm fields tree directly and removed the unused `page_idx` parameter; all four radio groups (`insurance_type`, `sex`, `rel_to_ins`, `assignment`) now set correctly
- **CMS 1500 Box 5 — city/state/zip not separated**: `_parse_address()` handled "Street, City, ST ZIP" but failed when city and state had no comma between them (e.g. "Philadelphia PA 19103" as a single comma-part); added a "City ST ZIP" combined-pattern match before the existing "ST ZIP" check so city is extracted into `pt_city` regardless of whether the stored address includes a comma before the state abbreviation
- **Address autocomplete silently broken after Radar.io switch**: `suggestAddresses` and `geocodeAddress` returned immediately when `NEXT_PUBLIC_RADAR_API_KEY` was not set, leaving the dropdown blank on Settings and client profile pages; fixed by falling back to Photon when no Radar key is configured
- **Provider address field cut off in Settings**: `AddressAutocomplete` in the "Billing provider information" section was missing the `inputClassName` prop, so the input rendered unstyled and too narrow; added `w-full` class so the address field spans the full column width

### Fixed
- **Address autocomplete dropdown not appearing**: CSP `connect-src` still listed `nominatim.openstreetmap.org` after switching to Photon, causing the browser to silently block every autocomplete fetch; replaced with `photon.komoot.io` in `next.config.js`

### Added
- **Provider billing address and phone in Settings**: providers can now enter their practice address (with autocomplete, green geocoded-pin indicator) and phone number in Provider Settings; these fields are stored per-user in new `provider_address` and `provider_phone` columns (migration 0018); the address auto-populates CMS 1500 Box 33 (billing provider street/city/state/ZIP) and the phone populates the Box 33 phone field, replacing the previous placeholder "NPI: xxx Taxonomy: xxx" text in that field

### Fixed
- **CMS 1500 Box 33 always blank**: billing provider address and phone were never passed to the PDF generator; Box 33 `doc_street` was hardcoded to empty string and `doc_location` was overloaded with NPI/taxonomy text; now uses provider's stored address (parsed via the existing `_parse_address()` helper) and phone number
- **Autocomplete suggestions missing city**: `suggestAddresses()` in `geo.ts` now filters out Nominatim results that have no `city`, `town`, `village`, `hamlet`, or `municipality` component, guaranteeing every suggestion shown to the user produces a complete "Street, City, ST ZIP" label that `_parse_address()` can parse into a valid CMS 1500 city field

### Fixed
- **MCO portal URLs corrected to official submission sites**: UPMC For You now links to `provider.upmc.com`, Health Partners Plans to `hppserve.com`, and FFS to `promise.dhs.pa.gov/portal/provider` (was previously linking to generic provider-info pages rather than the actual claim submission portals)

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
