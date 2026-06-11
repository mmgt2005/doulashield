# DoulaShield Admin Guide

**v1.23.1 · Last updated 2026-06-11**

This guide covers everything admins can do that providers cannot. For day-to-day provider features (documenting visits, submitting claims, etc.) refer to `MANUAL.md`.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Managing Provider Accounts](#managing-provider-accounts)
3. [Billing & Escrow](#billing--escrow)
4. [Billing Agencies (Billing Providers)](#billing-agencies-billing-providers)
5. [Billing Admin Accounts](#billing-admin-accounts)
6. [Billing Provider Reporting](#billing-provider-reporting)
7. [Claim Filing Deadline Reminders](#claim-filing-deadline-reminders)
8. [Admin-Only Settings](#admin-only-settings)
9. [Audit Logs](#audit-logs)
10. [Reference: Audit Action Types](#reference-audit-action-types)

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

### Impersonating a Provider ("View As")

The **View as** button (amber outline) appears on any active provider row that is not your own account. It lets you enter a fully-scoped impersonation session where every data fetch is automatically filtered to that provider's records — exactly as if you had logged in as them.

**How to start:**

1. In the Users table, find the provider row.
2. Click **View as**.
3. An amber banner appears at the top of every page: *👁 Viewing as **Provider Name** — admin impersonation session*.
4. You are redirected to the provider's Dashboard. All sidebar links, clients, visits, claims, and reports show only that provider's data.

**What changes during impersonation:**

- The access token is replaced with a short-lived provider JWT. All API calls use this token.
- Admin navigation links (Users, Audit Logs) disappear — the provider role is active.
- Navigating directly to `/admin/users` redirects to `/dashboard`.
- Your admin session is held in memory and is never written to disk or storage.

**How to exit:**

Click **Exit** in the amber banner. This calls `POST /api/v1/auth/impersonate/end` to write the `IMPERSONATE_END` audit entry, then restores your admin token and user from memory — no re-login required.

**Page refresh during impersonation:**

Refreshing the page ends the impersonation session (in-memory state is cleared). Your admin session is restored automatically via your httpOnly refresh cookie. This is by design — impersonation is intentionally session-scoped.

**HIPAA audit trail:**

Every impersonation start writes an `IMPERSONATE_START` entry with your admin ID, the target provider's ID, and their email address. Every exit writes `IMPERSONATE_END`. Both entries appear in the Audit Logs view.

**Limitations:**

- You can only impersonate users with the `provider` role (not other admins).
- You cannot impersonate your own account.
- PHI you access during impersonation is logged under the provider's UUID, which is correct — you are accessing their records.

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

### Admin Billing Exemption

Admin accounts are created with `deposit_paid = true` and `escrow_balance_remaining = $0.00`. The Escrow & Billing section is hidden on the admin Settings page. Admins are never charged deposits, subscription fees, or escrow deductions.

---

## Billing Agencies (Billing Providers)

Some doulas bill through a third-party billing agency rather than under their own NPI. DoulaShield models these as **Billing Provider** entities — separate from individual user accounts.

### What Billing Providers Change

When a doula is assigned to a billing provider:
- **CMS 1500 Box 33** (Billing Provider Name) uses the agency name instead of the doula's name.
- **CMS 1500 Box 33a** (Billing Provider NPI) uses the agency's Group NPI instead of the doula's personal NPI.
- **Stripe subscription** is charged to the billing provider entity, not the individual doula.
- The doula's own Subscription column in the Users table still shows their individual status; the agency's subscription is managed on the Billing Providers page.

Claim remittance matching is **not affected** — Availity assigns a control number at submission time which is stored as `availity_claim_id`. Remittance 835 files reference this same number regardless of which NPI appeared in Box 33a.

### Creating a Billing Agency

Navigate to **Billing Providers** in the admin sidebar.

1. Click **+ Add Agency**.
2. Fill in Agency Name (required), Group NPI, address, phone.
3. Click **Create Agency**. The agency appears in the table.

### Assigning a Doula to an Agency

Use the API or the assign-provider action on the Billing Providers page (`POST /admin/billing-providers/{id}/assign-provider` with `{ "provider_user_id": "..." }`). The doula's CMS 1500 forms immediately reflect the agency NPI and name.

### Starting a Subscription for an Agency

1. Ensure at least one provider is assigned to the agency.
2. Click **Start Sub** in the agency row.
3. DoulaShield creates a Stripe subscription on the agency's customer record. The Subscription column updates to "Active."

### Editing or Deleting an Agency

- **Edit** — click the Edit button on any row to update name, NPI, or contact details inline.
- **Delete** — only available when the agency has zero assigned providers. The button does not appear when providers are assigned.

---

## Billing Admin Accounts

Billing agency staff who need to update EOB/claim outcomes for the doulas they manage can be granted the **Billing Admin** role. Billing admins have a restricted interface — they see only **Agency Claims** and **Settings** in the sidebar, and cannot access admin pages.

### Creating a Billing Admin Account

On the Users page, click **+ Add User**, select **Billing Admin** as the role, and choose the managed agency from the dropdown. The account is created with `managed_billing_provider_id` set to the selected agency.

### What Billing Admins Can Do

- View all claims from providers assigned to their managed agency (`GET /billing-admin/claims`)
- Scan paper EOBs and update manual claim outcomes for any of their agency's providers
- View and update their own Settings

### What Billing Admins Cannot Do

- Access the admin Users, Billing Providers, or Audit Logs pages
- View or modify patients, visits, or claims from providers outside their agency
- Start subscriptions or manage Stripe billing

---

## Billing Provider Reporting

The Billing Providers page shows per-agency aggregate stats pulled from `GET /admin/stats/billing-providers`:

| Column | Description |
|---|---|
| **Providers** | Number of doulas assigned to the agency |
| **Claims** | Total claims filed by the agency's providers |
| **Billed** | Sum of `billed_amount` across all claims |
| **Paid** | Sum of `paid_amount` across all claims |
| **Denial %** | Percentage of claims with status `denied` |

A summary row above the table aggregates totals across all agencies.

---

## Claim Filing Deadline Reminders

PA Medicaid MCOs enforce a **365-day timely-filing window** from the date of service. DoulaShield automatically tracks this for every claim.

### Deadline Chip on Visit Pages

When a claim exists on a visit, the claim panel shows a colored deadline chip:

| Color | Meaning |
|---|---|
| Gray | More than 30 days until deadline |
| Amber | 8–30 days until deadline |
| Red | 0–7 days until deadline or overdue |

### Email Reminders

Providers receive automated reminder emails at **30, 14, 7, 3, 1, and 0 days** before the filing deadline for any open (not yet paid or denied) claim. Emails include a direct link to the visit page to take action.

Reminders run daily at **08:15 UTC**. No reminder is sent for claims that are already `paid` or `denied`.

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
| `CREATE_BILLING_PROVIDER` | Admin created a billing agency | billing_provider |
| `ASSIGN_BILLING_PROVIDER` | Admin assigned a provider to an agency | user |
| `START_BILLING_PROVIDER_SUBSCRIPTION` | Admin started subscription for a billing agency | billing_provider |
| `GENERATE_AUDIT_PACKET` | Medicaid audit packet PDF downloaded | patient |
| `ESCROW_DEDUCTION` | Automatic escrow charge from remittance | user |
| `GENERATE_AUDIT_PACKET` | Medicaid audit packet PDF downloaded | claim |
| `RESUBMIT_CLAIM` | Denied claim resubmitted to Availity or status reset | claim |
