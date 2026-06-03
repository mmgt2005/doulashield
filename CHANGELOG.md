# DoulaShield Changelog

All notable changes to this project are documented here.

Format: `## [version] — YYYY-MM-DD`. Changes accumulate under `[Unreleased]`; on each release that section is renamed to the new version and a fresh `[Unreleased]` stub is added above it.

Semver guide — **patch** (1.0.x): bug fixes, infra; **minor** (1.x.0): new features; **major** (x.0.0): breaking auth/schema changes.

---

## [Unreleased]

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
