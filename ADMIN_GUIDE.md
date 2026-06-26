# DoulaShield Admin Guide

**v1.33.0 · Last updated 2026-06-26**

This guide covers everything admins can do that providers cannot. For day-to-day provider features (documenting visits, submitting claims, etc.) refer to `MANUAL.md`.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Managing Provider Accounts](#managing-provider-accounts)
   - [Onboarding New Providers (Demo Mode)](#onboarding-new-providers-demo-mode)
3. [PCB Enrollment Services](#pcb-enrollment-services)
4. [Billing & Escrow](#billing--escrow)
5. [Billing Providers (Group NPIs)](#billing-providers-group-npis)
6. [Admin-Only Settings](#admin-only-settings)
7. [Audit Logs](#audit-logs)
8. [Reference: Audit Action Types](#reference-audit-action-types)

---

## Introduction

Admin users share the provider interface (Clients, Visits, Claims) and have two additional sections in the sidebar: **Users** and **Audit Logs**. Admins are exempt from the $99 enrollment deposit, the $400 deferred balance, and the monthly subscription — their billing status is pre-cleared on account creation.

At the bottom of the sidebar, under the **Help** heading, admins see two documentation links: **User Manual** (provider-facing features) and **Admin Guide** (this document). Providers only see the User Manual link. The Admin Guide page is restricted to admin accounts and redirects anyone else to the dashboard.

---

## Managing Provider Accounts

### Creating a Provider Account

From **Users → + Add Provider**, fill in the email address and (optionally) the provider's full name. The modal offers two buttons:

**Create & Send Email** — Creates the account, generates a temporary password, creates a Stripe deposit link, and sends one combined email to the provider with their login credentials and a **Pay $99 Deposit →** button. The admin never sees the temporary password.

**Create Account Only** — Creates the account and generates a temporary password, but sends no email. The modal transitions to a **one-time credential panel** showing the email and password in a selectable monospace field. A **Copy Password** button copies it to the clipboard. Share the credentials with the provider by phone or secure message. Click **Done** to close — the password is not retrievable after this screen.

### The One-Time Credential Panel

After **Create Account Only**, the panel shows:

```
Account created for provider@example.com

  Email     provider@example.com
  Password  aB3!xKp9mNqZ7r

⚠ Save this password — it will not be shown again.

[Copy Password]                          [Done]
```

If the provider loses their credentials before logging in, use **Send Welcome Email** (below) to issue new ones.

### Sending or Resending the Welcome Email

A **Send Welcome Email** button appears on any row — provider or admin — where the user has **never signed in** (their account was created but they have not yet logged in for the first time). Clicking it:

1. Generates a new temporary password (the old one stops working)
2. For providers: creates a fresh Stripe Checkout link for the $99 deposit
3. Sends the welcome email to the user; admins receive role-appropriate copy without a deposit button
4. Shows a toast: "Welcome email sent to {email}"

Once a user signs in for the first time the button disappears automatically. This covers accounts created via **Create Account Only** who haven't been contacted yet, and any user who lost their credentials before their first login.

The **Last Emailed** column in the Users table shows the date the most recent welcome email was sent, so you can tell at a glance whether an account has been contacted and how recently. Accounts created via **Create Account Only** show "—" until a welcome email is sent.

### Role Toggle (Provider ↔ Admin)

Each row (except your own) has a **Make Admin** or **Make Provider** button. Clicking it immediately changes the user's role. The affected user sees the change on their next page load — admin nav links appear or disappear accordingly.

You cannot toggle your own role (self-lockout prevention). Your row shows no role or deactivation buttons.

### Deactivating and Reactivating Accounts

Each row has a **Deactivate** button (red outline). Deactivated providers receive a 401 on their next API call and are effectively locked out. The button changes to **Reactivate** (green outline) — click to restore access.

You cannot deactivate your own account.

### Self-Lockout Prevention

Your own row in the Users table has no Deactivate, Make Admin, or Make Provider buttons. This prevents an admin from accidentally locking themselves out or removing their own admin access.

---

### Impersonating Another User ("View As")

The **View as** button (amber outline) appears on any provider or admin row that is not your own account and that you are not currently impersonating someone else from. It lets you enter a fully-scoped impersonation session — every data fetch is filtered to that user's records, and their role is active for the duration.

**How to start:**

1. In the Users table, find the row for the provider or admin you want to view as.
2. Click **View as**.
3. An amber banner appears at the top of every page: *👁 Viewing as **Name** — admin impersonation session*.
4. You are redirected to the Dashboard. For provider impersonation all sidebar links, clients, visits, claims, and reports show only that provider's data. For admin impersonation, admin navigation (Users, Audit Logs) remains accessible.

**What changes during impersonation:**

- The access token is replaced with a short-lived JWT carrying the target user's role. All API calls use this token.
- When impersonating a **provider**: admin navigation links disappear; navigating directly to `/admin/users` redirects to `/dashboard`.
- When impersonating an **admin**: admin navigation links remain visible — you see the app exactly as that admin does.
- Your original admin session is held in memory and is never written to disk or storage.

**How to exit:**

Click **Exit** in the amber banner. This calls `POST /api/v1/auth/impersonate/end` to write the `IMPERSONATE_END` audit entry, then restores your admin token and user from memory — no re-login required.

**Page refresh during impersonation:**

Refreshing the page ends the impersonation session (in-memory state is cleared). Your admin session is restored automatically via your httpOnly refresh cookie. This is by design — impersonation is intentionally session-scoped.

**HIPAA audit trail:**

Every impersonation start writes an `IMPERSONATE_START` entry with your admin ID, the target user's ID, and their email address. Every exit writes `IMPERSONATE_END`. Both entries appear in the Audit Logs view.

**Limitations:**

- `billing_admin` accounts cannot be impersonated (their agency-scoped access does not transfer meaningfully to a session).
- You cannot impersonate your own account.
- You cannot start a nested impersonation session while already impersonating someone else — the **View as** button is hidden during an active impersonation.
- PHI you access during impersonation is logged under the target user's UUID, which is correct — you are accessing their records.

---

### Onboarding New Providers (Demo Mode)

New providers land on an empty dashboard and need to practice the full workflow — adding a client, documenting a visit, collecting an MA 91 signature, submitting a claim, and uploading an EOB — before they start billing real clients. Demo Mode lets them do this safely without sending any claims to Availity.

**Enabling Demo Mode:**

1. Find the provider's row in the Users table.
2. Click **Demo Off** (the gray toggle button). A confirmation modal explains that claim submissions will be simulated.
3. Click **Enable Demo Mode**. The button turns green and reads **Demo On**.

While demo mode is on, every claim submission the provider makes is intercepted: a `DEMO-XXXXXXXX` tracking ID is generated, the claim appears in Reports with status "Processing," and no data is sent to Availity. Status polls on demo claims also return immediately without contacting Availity. EOB upload and all other features (SOAP notes, MA 91 signatures, audit packets, ZipZign, CMS 1500 download) function normally.

**Disabling Demo Mode:**

Click **Demo On** → **Disable Demo Mode**. Two things happen automatically:

1. Real Availity submissions resume on the provider's next claim.
2. All clients the provider added while demo mode was on are **automatically deactivated** and disappear from their Clients list. Demo claims attached to those clients are also gone from view. No manual cleanup needed.

Demo clients are tracked by an internal flag set at creation time, so only clients created during demo mode are removed — any real clients the provider had before demo was enabled are unaffected.

**Sharing the Walkthrough Guide:**

When you enable demo mode, the walkthrough guide is **automatically emailed** to the provider. The email contains the six workflow steps, sample SOAP notes, and the 10 patient records — no manual forwarding needed.

You can also open the guide yourself at any time by clicking **Walkthrough Guide** on the provider's row. Screen-share it during onboarding or take a screenshot and send it. The card contains:

- **Six workflow steps** from adding a client through uploading an EOB remittance scan to close the claim as paid.
- **Sample SOAP notes** for a Prenatal 1 visit (Subjective / Objective / Assessment / Plan) that the provider can copy and adapt.
- **10 fake patients** with realistic names, 10-digit Medicaid IDs, all nine supported MCOs (including FFS for the manual billing path), dates of birth, Philadelphia-area addresses, and a recognizable placeholder NPI (`9999999999`).
- **Download Sample Remittance Advice (EOB)** — a realistic PA Medicaid remittance PDF showing five claim outcomes (two paid, one partially adjusted CO-45, two denied CO-4 and CO-96) with reason code explanations and recommended actions. The provider downloads it and uploads it in step 6 to complete the full EOB scan flow during practice.

The provider enters this data into the real UI themselves — walking through the entry process is part of the training.

The same guide is available to the provider directly: a green **Walkthrough Guide** link appears in their sidebar under the Help section while demo mode is on. They can open it at any time without needing to contact you.

---

## PCB Enrollment Services

DoulaShield can manage the full Pennsylvania Certification Board (PCB) credentialing process for a doula provider on behalf of the agency. Go to **Admin → Enrollment Services** to start and track credentialing applications.

### Choosing a Pathway

PCB offers two pathways. Select the one that fits the provider:

| Pathway | Who it's for | Requirements |
|---|---|---|
| **Education/Training** | Newly trained doulas | 24+ training hours, 1+ HIPAA hr, CPR cert, 3 client evals |
| **Experienced** | Currently practicing doulas | Proof of active practice, CPR cert, 3 client evals (last year), 3 recommendation letters (last year) |

When in doubt, use Education/Training — it is available to all applicants regardless of experience.

### Creating an Enrollment Service

1. Click **+ New Enrollment Service**.
2. Select the provider from the dropdown.
3. Choose the pathway (Education/Training or Experienced).
4. Click **Create Service** — the task checklist is generated automatically.

### Working Through the Tasks

Each task has an upload slot and an optional notes field. Click the task row to expand it:

- **Upload Document** — attach the relevant certificate or form (PDF, JPEG, PNG, up to 20 MB). Uploading a document automatically advances the task from "not started" to "in progress."
- **Training hours field** (Education/Training only) — enter the total documented hours when uploading training certificates. DoulaShield prevents the task from being marked complete if the total is under 24. A badge shows how many more hours are needed.
- **HIPAA hours field** (Education/Training only) — enter hours covering HIPAA/confidentiality specifically. Must be ≥ 1.
- **Mark Complete** — once a document is uploaded and any required hour counts are met, click this to mark the task done.

For step-by-step guidance on what to collect and verify for each task, see **Help → Enrollment Guide** in the sidebar.

### Submitting to PCB and Recording the Certificate

PCB has no API — once all tasks are complete, submit the application packet at **pacertboard.org/doula**. When the certificate arrives (typically 4–6 weeks):

1. Upload the certificate file as a document on the service.
2. Click **Mark PCB Certification Complete** and enter the issue date.
3. DoulaShield writes the certification date to the provider's profile (`pcb_last_certified_on`). The date appears in the provider's Settings page and is used as proof of credentials for subsequent steps (CAQH setup, MCO contracting).

---

## Billing & Escrow

The billing columns on the Users table show the financial status of each provider:

| Column | Values |
|---|---|
| **Deposit** | Green "✓ Paid" — deposit received; Amber "Pending" — Stripe customer exists but payment not confirmed; Gray "—" — no Stripe record yet |
| **Balance** | Dollar amount of deferred balance remaining (starts at $400.00, collected automatically from MCO remittances at 50% per check) |
| **Subscription** | Green "Active", Amber "Past Due", Gray "None" |

### Generating a Stripe Deposit Link ($99)

1. In the Users table, find the provider row.
2. Click **Send Deposit Email** in the actions area (visible when deposit is not yet paid).
3. DoulaShield creates a Stripe Checkout link and emails the provider the combined welcome + deposit message.
4. When the provider pays, the Stripe webhook fires automatically: `stripe_customer_id` is saved to the DB, `deposit_paid` is set to true, and the Deposit column turns green.

### Linking an Existing Stripe Customer Manually

If the $99 deposit was collected outside the app (cash, check, or a Stripe transaction you processed manually), click **Link Customer ID** on the provider row. Enter the `cus_...` Stripe customer ID from your Stripe Dashboard. This sets `deposit_paid = true` and links the card on file for future automatic charges.

### Starting a Monthly Subscription ($39/month)

1. Confirm the Deposit column shows "✓ Paid" (a saved payment method is required).
2. Click **Start Subscription** on the provider row.
3. DoulaShield creates a Stripe subscription using the saved card. The Subscription column updates to "Active."
4. Stripe charges $39 automatically on each billing cycle.

The **Start Subscription** button is disabled if the deposit has not been paid.

### Stripe Price ID Configuration

DoulaShield uses three Stripe price IDs, set as environment variables on the backend service (Railway → backend service → Variables):

| Variable | Used for |
|---|---|
| `STRIPE_DEPOSIT_PRICE_ID` | One-time $99 enrollment deposit for individual providers |
| `STRIPE_MONTHLY_PRICE_ID` | Recurring monthly subscription for individual providers |
| `STRIPE_AGENCY_MONTHLY_PRICE_ID` | Recurring monthly subscription for billing agencies (billing providers) |

Create each product and price in your Stripe Dashboard (Products → Add Product → Add Price), then copy the `price_1…` ID into the matching variable. If `STRIPE_AGENCY_MONTHLY_PRICE_ID` is left blank, agency subscriptions fall back to `STRIPE_MONTHLY_PRICE_ID`.

### Admin Billing Exemption

Admin accounts are created with `deposit_paid = true` and `escrow_balance_remaining = $0.00`. The Escrow & Billing section is hidden on the admin Settings page. Admins are never charged deposits, subscription fees, or escrow deductions.

---

## Billing Providers (Group NPIs)

PA Medicaid doula agencies employ multiple rendering providers (doulas) but submit all claims through a single billing entity with a group NPI. The Billing Providers section lets you register that entity once and assign it to any number of doulas.

### What Billing Providers Do

When a doula is linked to a billing provider:

- **Box 33 / Box 33a** on the CMS 1500 use the billing entity's name and group NPI.
- **Box 24J** keeps the doula's individual NPI (rendering provider).
- **Box 25** uses the billing entity's EIN (if configured) rather than the doula's SSN.
- The **Availity 837P** claim body includes a `billingProvider` object with the group NPI alongside the doula as the rendering provider.

Doulas with no billing provider assigned continue to use their own NPI for both Box 24J and Box 33a — no change from the current behavior.

### Managing Billing Providers

Go to **Billing Providers** in the admin sidebar (between **Users** and **Audit Logs**). The page lists all registered billing entities with their name, NPI, and the number of doulas currently assigned.

#### Adding a Billing Provider

Click **+ Add Billing Provider**. Fill in:

| Field | Required | Notes |
|---|---|---|
| **Name** | Yes | Legal entity name as registered in PROMISe |
| **NPI** | Yes | 10-digit group NPI |
| **Taxonomy Code** | No | Defaults to `374J00000X` if left blank |
| **Address** | No | Used in Box 33 of the CMS 1500 |
| **City / State / ZIP** | No | Same — Box 33 address fields |
| **Phone** | No | Box 33 phone |
| **Tax ID (EIN)** | No | Stored Fernet-encrypted; used in Box 25 when configured |

Click **Save**. The new entity appears in the list immediately.

#### Editing a Billing Provider

Click **Edit** on any row. All fields are editable. Changes take effect on the next claim generated or submitted — already-submitted claims are not retroactively updated.

#### Starting an Agency Subscription

Click **Start Sub** on the row. DoulaShield creates a Stripe subscription billed to the agency using the `STRIPE_AGENCY_MONTHLY_PRICE_ID` price (falls back to `STRIPE_MONTHLY_PRICE_ID` if not set). The Subscription column updates to "Active." The button only appears when the agency does not already have an active or trialing subscription, and requires at least one provider assigned to the agency (so a Stripe customer record can be created).

#### Deleting a Billing Provider

Click **Delete** on the row. Any doulas currently assigned to this entity will have `billing_provider_id` set to NULL automatically (ON DELETE SET NULL), reverting them to self-billing. Confirm the deletion in the prompt — it cannot be undone.

### Assigning a Billing Provider to a Doula

In the **Users** table, find the provider row. The **Billing Provider** column contains a dropdown listing all registered billing entities plus a "— None —" option. Select the appropriate billing entity. The change takes effect immediately — no save button required.

To remove an assignment, select **— None —** from the dropdown.

### Viewing the Assignment from the Provider's Side

Providers cannot change their own billing provider assignment. When a billing provider is assigned, the provider's **Settings** page shows a read-only green panel:

```
Billing through: Agency Name
NPI 1234567890 · Box 33a on CMS 1500
Your NPI (9876543210) appears in Box 24J as rendering provider.
```

If no billing provider is assigned, the panel shows a gray note: *No billing provider linked — your NPI used for both Box 24J and Box 33a.*

### Claim Review Queue

All claims from doulas assigned to an agency are routed to the agency review queue instead of being submitted to Availity directly. This lets the billing admin review and handle each claim before it reaches the payer — whether via Availity or through a manual channel (paper CMS 1500, MCO portal, phone).

**How it works:**
1. A doula assigned to the agency submits a claim from the visit form.
2. The claim is saved with status **Pending Review** (orange badge) and appears in the billing admin's **Agency Claims** page.
3. The billing admin clicks the row to expand it. The expanded panel loads a full claim review snapshot:
   - **Claim Details** — payer, procedure code, diagnosis code, billed amount, resubmit count, and MA 91 signature status (Signed ✓ or pending).
   - **Visit Notes** — the provider's SOAP note (subjective, objective, assessment, plan, entry, and birth notes). Unpopulated fields are omitted.
   - **Documents** — access and manage all documents related to the claim:
     - **Preview CMS 1500** — opens the completed CMS 1500 form in an inline modal (iframe on desktop, open-in-new-tab on mobile). Box 24J uses the doula's individual NPI; Box 33a uses the agency group NPI. A **Download PDF** button is available inside the modal.
     - **Audit Packet** — previews or downloads the full audit packet PDF (CMS 1500 + SOAP notes + eligibility + MA 91 + provider credentials).
     - **Source Image** — appears only when the provider scanned a source document (e.g., a handwritten SOAP note). Opens the image in a preview modal.
     - **Supporting Documents** — a list of documents the billing admin has uploaded to the claim. Each document shows its type label and a **Preview** button.
     - **Upload buttons** — `+ Prior Auth`, `+ Eligibility`, `+ EOB Received`, `+ Other`. Clicking any button opens a file picker (PDF, JPEG, or PNG, up to 20 MB). The file is stored and immediately appears in the supporting documents list.
   - **Submit to Availity ↗** — available when the claim is still in Pending Review. Submits electronically using the agency's shared Availity credentials.
   - **Log Manual Submission** — record that the claim was filed by another channel (paper, MCO portal, fax, phone). Choose Submitted / Paid / Denied, fill in paid amount or denial reason, and click **Save**. The claim status updates immediately.
4. The doula's visit page shows the updated status badge. Agency-assigned doulas cannot edit claim status themselves — all status changes go through the billing admin. They also cannot upload EOB remittance scans; that is handled exclusively by the billing admin.

The claim queue is active as soon as a doula is assigned to the agency, regardless of whether Availity credentials have been configured. Agencies that have not yet set up Availity can still handle claims manually using the **Log Manual Submission** action.

### Configuring Agency Availity Credentials

When a billing admin logs in, their sidebar shows **Agency Claims** and **Agency Settings**. The **Agency Settings** page (`/billing-admin/settings`) lets the billing admin enter:

- **Availity NPI** — the 10-digit NPI used in Box 33a of all agency claims
- **Client ID** — the agency's Availity OAuth client ID
- **Client Secret** — the agency's Availity OAuth client secret (write-only; stored encrypted)

Once all three are saved, a **Connected ✓** badge appears and the claim review queue activates for all doulas assigned to the agency.

The billing admin can reach this page from the **Agency Settings** link in their sidebar.

### Admin View of Billing Admin Pages

Platform admins can view any agency's claim queue and settings directly — without logging in as the billing admin user. On the **Billing Providers** page, each agency row has two action links:

- **View Claims** — opens `/billing-admin/claims?bp_id=<agency-uuid>` showing that agency's full claim queue, including pending-review claims and their Submit ↗ buttons. The admin can submit claims on behalf of the agency using the agency's Availity credentials.
- **Settings** — opens `/billing-admin/settings?bp_id=<agency-uuid>` showing the agency's Availity NPI, Connected status, and credential update form.

An amber "**Viewing as admin: Agency Name**" banner appears at the top of both pages when accessed via `bp_id`, so it is clear you are in a cross-agency view. All API calls automatically pass the `bp_id` so the correct agency data is returned.

### The Billing Admin Role

When creating a user who will manage a billing provider entity:
1. In **Create Provider Account**, set **Role** to **Billing Admin**.
2. After account creation, assign the user to the appropriate billing provider via the **Billing Provider** column on the Users page.

Billing admins see only their own agency's claims and settings — they cannot access provider client records or admin pages. Their sidebar shows:

- **Agency Claims** — review and submit queued claims
- **Agency Settings** — configure Availity credentials and view agency info

When a new billing provider entity is created, any billing admin already linked to it receives an **agency onboarding email** confirming the agency name, Group NPI, and links to the Agency Claims and Agency Settings pages.

---

## Admin-Only Settings

Two fields in **Settings** are visible only to admins:

**ZipZign API Key** — the shared API key for all telehealth MA 91 e-signature requests. Providers do not see this field. When saved, a **Connected ✓** badge appears on every provider's Settings page, and telehealth signature requests work for all providers automatically. Obtain the key from [zipzign.com](https://zipzign.com).

**Welcome email content** — the welcome email sent by **Create & Send Email** and **Send Welcome Email** uses a system template. The subject line automatically adjusts based on role:
- Provider accounts: "Welcome to DoulaShield — Your Account & Deposit Link"
- Admin accounts: "Welcome to DoulaShield — Your Account Details"

---

## Audit Logs

Go to **Audit Logs** in the sidebar. Every action that touches PHI, credentials, or system state is recorded here. Audit logs cannot be edited or deleted — the database enforces this at the rule level.

### What Is Logged

Every audit entry records: timestamp, user ID, action type, resource type, resource ID, IP address, and user agent. PHI never appears in the log body — only resource IDs (UUIDs).

Significant events include: login, MFA enrollment, patient record access, Medicaid ID reads, visit saves, signature collection, claim submission, claim resubmission, status checks, audit packet downloads, remittance fetches, password changes, escrow deductions, admin user management actions, and Stripe billing events.

### Medicaid Audit Packets

Each visit with a filed claim has a **📋 Download Audit Packet** button (visible to all users with access to the visit form). Clicking it downloads a single PDF assembling the cover/claim summary, member eligibility, full SOAP note, MA 91 signature, provider credentials, and the completed CMS 1500. Every download is logged as `GENERATE_AUDIT_PACKET`. When preparing for a PA Medicaid audit, you can pull the audit packet for any specific visit directly from the claim section of that visit's form.

### Filtering

Use the filter controls at the top of the Audit Logs page to narrow results by:
- **Action type** — e.g., `READ_MEDICAID_ID`, `SUBMIT_CLAIM`, `DEPOSIT_PAID`
- **User** — filter by provider email
- **Date range** — start and end date pickers

### Why Audit Logs Cannot Be Edited or Deleted

HIPAA requires an immutable audit trail. The database has a rule that blocks UPDATE and DELETE on the `audit_logs` table — even the service role cannot modify existing entries. Only INSERT is permitted. This means the log is a permanent record of every PHI access and system event.

---

## Reference: Audit Action Types

| Action | What triggered it | Resource type |
|---|---|---|
| `LOGIN` | Successful login | user |
| `MFA_ENROLL` | TOTP MFA enrolled | user |
| `REQUEST_PASSWORD_RESET` | Forgot-password flow initiated | user |
| `RESET_PASSWORD` | Password reset via email link | user |
| `UPDATE_PASSWORD` | Change-password form in Settings | user |
| `READ_MEDICAID_ID` | Provider viewed a patient's Medicaid ID | patient |
| `CREATE_PATIENT` | New client added | patient |
| `UPDATE_PATIENT` | Client profile edited | patient |
| `UPSERT_VISIT` | Visit form saved | visit |
| `SCAN_MEDICAID_CARD` | Medicaid card OCR scan | patient |
| `SCAN_HANDBOOK_PAGE` | Handbook page OCR scan | visit |
| `TRANSLATE_SOAP_NOTE` | AI clinical draft generated | patient |
| `SIGN_MA91_IN_PERSON` | In-person canvas signature saved | visit |
| `REQUEST_TELEHEALTH_MA91` | ZipZign signature request sent | visit |
| `MA91_WEBHOOK_RECEIVED` | ZipZign webhook (signed or declined) | visit |
| `SUBMIT_CLAIM` | Claim submitted to Availity | claim |
| `CHECK_CLAIM_STATUS` | Availity status refreshed | claim |
| `LOG_MANUAL_CLAIM` | Manual claim status recorded | claim |
| `GENERATE_CMS1500` | CMS 1500 PDF downloaded | claim |
| `FETCH_REMITTANCES` | Remittance fetch from Availity | user |
| `PARTNER_TRANSFER` | Stripe transfer to revenue-share partner | user |
| `CHECK_ELIGIBILITY` | Medicaid eligibility check via Availity | patient |
| `UPDATE_PROVIDER_SETTINGS` | Settings page saved | user |
| `DOWNLOAD_DOCUMENT_IMAGE` | Signed URL issued for stored image | patient |
| `CREATE_AND_INVITE_PROVIDER` | Admin created provider account and sent welcome email | user |
| `CREATE_PROVIDER_ACCOUNT_ONLY` | Admin created account without email | user |
| `SEND_WELCOME_EMAIL` | Admin resent welcome email | user |
| `START_SUBSCRIPTION` | Monthly subscription started | user |
| `DEPOSIT_PAID` | Stripe deposit webhook confirmed | user |
| `MANUAL_CUSTOMER_LINK` | Admin linked Stripe customer ID manually | user |
| `ESCROW_DEDUCTION` | Automatic escrow charge from remittance | user |
| `GENERATE_AUDIT_PACKET` | Medicaid audit packet PDF downloaded | claim |
| `RESUBMIT_CLAIM` | Denied claim resubmitted to Availity or status reset | claim |
| `CREATE_BILLING_PROVIDER` | Admin created a new billing provider entity | user |
| `UPDATE_BILLING_PROVIDER` | Admin updated a billing provider entity | user |
| `SUBMIT_CLAIM_TO_QUEUE` | Provider claim routed to agency pending-review queue | claim |
| `UPDATE_AGENCY_AVAILITY` | Billing admin saved agency Availity credentials | user |
| `SUBMIT_AGENCY_CLAIM` | Billing admin submitted a queued claim to Availity using agency credentials | claim |
| `ASSIGN_BILLING_PROVIDER` | Admin assigned a provider to a billing agency (individual subscription cancelled if active) | user |
| `ENROLLMENT_SERVICE_CREATED` | Admin created a PCB enrollment service for a provider | user |
| `PCB_CERTIFICATION_COMPLETE` | Admin recorded PCB certificate date; provider's pcb_last_certified_on updated | user |
