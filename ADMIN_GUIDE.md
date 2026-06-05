# DoulaShield Admin Guide

**v1.21.0 · Last updated 2026-06-05**

This guide covers everything admins can do that providers cannot. For day-to-day provider features (documenting visits, submitting claims, etc.) refer to `MANUAL.md`.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Managing Provider Accounts](#managing-provider-accounts)
3. [Billing & Escrow](#billing--escrow)
4. [Admin-Only Settings](#admin-only-settings)
5. [Audit Logs](#audit-logs)
6. [Reference: Audit Action Types](#reference-audit-action-types)

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
