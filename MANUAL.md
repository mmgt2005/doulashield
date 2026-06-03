# DoulaShield User Manual

**v1.13.0 · Last updated 2026-06-03**

This manual covers every provider-facing feature in DoulaShield. Read it start to finish once, then use the headings as a reference when you need a quick reminder.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Managing Clients](#managing-clients)
3. [Documenting Visits](#documenting-visits)
4. [MA 91 Patient Signatures](#ma-91-patient-signatures)
5. [Claims & Billing](#claims--billing)
6. [Reports Dashboard](#reports-dashboard)
7. [Settings](#settings)
8. [Reference: Billing Codes](#reference-billing-codes)
9. [Reference: MCO Submission Channels](#reference-mco-submission-channels)
10. [Reference: PA HealthChoices Zones](#reference-pa-healthchoices-zones)

---

## Getting Started

### Finding This Manual Inside the App

This manual is always one click away inside DoulaShield. At the bottom of the left sidebar, under the **Help** heading, click **User Manual** to open it as a styled page without leaving the app.

### First Login & MFA Setup

When your account is created, you receive a welcome email with your email address and a temporary password. On first login:

1. Go to the DoulaShield login page and sign in with the credentials from the email.
2. You will be prompted to set up multi-factor authentication (MFA). Open an authenticator app (Google Authenticator, Authy, or any TOTP app) and scan the QR code shown.
3. Enter the 6-digit code from your app to confirm setup. MFA is required on every login going forward.

If your temporary password no longer works, use **Forgot password?** on the login page to request a reset link.

### Setting Up Your Provider Profile

Before submitting any claims, complete your provider profile in **Settings** (sidebar). You need:

- **NPI** — your individual 10-digit National Provider Identifier
- **Billing name** — the name that will appear on Box 33 of the CMS 1500
- **Billing address** — used for Boxes 32 and 33
- **Phone number** — used for Box 33 phone field
- **PA HealthChoices Zone** and **counties served** — used for internal routing and reports
- **MCO contracts** — check each MCO you are enrolled with and add the contract date
- **Provider signature** — drawn once in Settings; embedded as Box 31 on every CMS 1500
- **SSN** — stored encrypted; used as Box 25 Tax ID on CMS 1500 (sole proprietor)

None of this is required to explore the app, but a claim PDF will be incomplete until all fields are filled.

### Connecting Availity Credentials

DoulaShield submits claims electronically through Availity for most MCOs. Each provider connects their own free Availity account:

1. Create a free account at availity.com using your individual NPI.
2. Apply for Availity API access (free developer program).
3. In DoulaShield **Settings → Availity**, enter your **Client ID** and **Client Secret**.
4. A **Connected ✓** badge appears once the credentials are saved.

Without Availity credentials, you can still download CMS 1500 PDFs and submit manually.

### Setting Your Telehealth Meeting Link

In **Settings → Telehealth**, paste your personal meeting room URL. DoulaShield works with any HIPAA-compliant platform. Recommended free option: [Doxy.me](https://doxy.me) — create a free account, navigate to your room, and copy the URL.

Once saved, the **Start Telehealth** button on every visit form will open your room and send the link to the client automatically (if the client has an email on file).

---

## Managing Clients

### Adding a New Client

From the sidebar, click **Clients → + New Client**.

**Option A — Scan a Medicaid card:**
Click **Scan Medicaid Card**, point your phone camera at the card. DoulaShield extracts the client's name, Medicaid ID, MCO, and address automatically. Review the pre-filled fields and correct anything the scan missed.

If the scan does not find a Medicaid ID, an amber prompt will appear asking you to also scan the client's PA ACCESS card (the EBT-style card that always shows the recipient number).

**Option B — Manual entry:**
Fill in all fields manually:
- Full name
- Medicaid ID
- MCO (select from the dropdown — normalized to standard PA MCO names)
- Date of birth
- Gender (defaults to Female)
- Email (optional — used to send telehealth links)
- Address (type 3+ characters to see geocoded suggestions; select one to save coordinates for GPS distance checks)
- Referring Provider NPI and name (required for Box 17 / 17b on CMS 1500)
- "Patient has other insurance" checkbox (Box 11d)

Click **Create Client** to save.

### Editing a Client Profile

Open any client from the **Clients** list and click **Edit profile**. You can update all fields including re-scanning a new Medicaid card. Changes to the address re-geocode coordinates automatically.

### Checking Medicaid Eligibility

On any client's overview page, the eligibility row shows the last checked status (**Active** or **Inactive**) and date. Click **Check eligibility** to query the MCO in real time through Availity.

Requirements: Availity credentials connected in Settings, client has an MCO and date of birth on file.

### Adding a Referring Provider

The referring physician's NPI (Box 17b) and name (Box 17) are required on every claim. Enter them in the client profile under **Referring Provider NPI** and **Referring Provider Name**. These fields are shared across all visits for that client — enter them once and they auto-fill every CMS 1500.

On a **Prenatal 1** visit, you can scan the MA 89 physician certification form to auto-fill both fields:

1. Open the Prenatal 1 visit form.
2. In the **Scan MA 89** section, photograph the form.
3. DoulaShield extracts the referring physician's name and NPI and saves them to the client profile.

### Understanding the Client Overview

The client overview shows three grids: **Prenatal Visits** (6 slots), **Labor** (1 slot), and **Postnatal Visits** (6 slots). Below those is a **Crisis / Bereavement Visits** section.

- **White card with blue border** → visit not yet started; click to begin
- **Amber card** → visit started but not ended
- **Gray card with checkmark** → visit completed; click to view or edit
- **Lock icon** → you must end the previous visit in the same group first
- **Small colored dot** on a completed card → claim status (green = paid, amber = submitted, blue = processing, red = denied)
- **Video icon** → visit was telehealth; **pin icon** → in-person

---

## Documenting Visits

### The 13-Visit Schedule

Pennsylvania Medicaid covers exactly 13 visits per client:

| Group | Slots | Notes |
|---|---|---|
| Prenatal | 1–6 | Visit 1 must be in-person |
| Labor | 1 | One per pregnancy |
| Postnatal | 1–6 | — |

Crisis and bereavement visits are separate — capped at 2 per year — and billed at a different rate (see Reference section).

### Starting a Visit

**In-person:**
Open the visit form and click **Start Visit**. The app records a timestamp and your GPS coordinates. If you are more than 500 feet from the client's address, an amber warning appears. You can still proceed — the warning is informational only. If you are meeting at a different location (clinic, hospital), enter the location in the text box that appears.

**Telehealth:**
Select **Telehealth** at the top of the visit form, then click **Start Telehealth**. Your meeting room opens in a new tab, and the client receives an email with the join link (requires a client email on file).

> **Prenatal 1 must be in-person.** The Telehealth button is disabled for that visit.

### Writing SOAP Notes

Each visit form has four SOAP fields: Subjective, Objective, Assessment, and Plan. Write in plain language — you do not need to use clinical jargon.

**AI Clinical Draft:**
Click **✨ Draft SOAP Note** to send your plain-language entries to Claude for translation into professional clinical documentation suitable for Medicaid audit. A draft panel appears with all four fields rewritten. Click **Apply to Form** to copy the draft into the textareas, then review and edit as needed. Nothing is saved until you click **Save visit** — the AI output is always a starting point for your review.

### The 30-Minute Billing Timer

Once a visit is started, a live timer appears next to the **End Visit** button. The timer shows in amber while under 30 minutes, with a countdown ("3 min to 30"). It turns green once you reach 30 minutes.

Pennsylvania Medicaid (T1032/T1033) requires a minimum 30-minute encounter for reimbursement. If you click **End Visit** before 30 minutes, the duration line turns amber and a billing warning appears above the Save button. You can still save the visit — the warning does not block submission.

### Ending a Visit

Click **End Visit** (appears after clicking Start Visit). The app records the end timestamp and shows the total duration. End the visit before saving the form for a complete record.

### Crisis / Bereavement Visits

Scroll to the **Crisis / Bereavement Visits** section at the bottom of a client's overview. Click **+ Add Crisis/Loss Visit** to open a new visit form for that type. The counter shows how many are used this year (cap: 2 per year). The **Add** button is hidden once 2 have been used.

These visits bill at a different rate (T1032 / U9 / $175 — see Reference section).

### Sequential Visit Rules

Within the prenatal group and within the postnatal group, visits must be completed in order. You cannot start Prenatal 2 until Prenatal 1 is ended. Locked slots show a padlock icon and "Complete [previous visit] first" with a link.

The Labor slot has no prerequisite. Postnatal 1 is not blocked by Labor.

---

## MA 91 Patient Signatures

Pennsylvania Medicaid requires a signed MA 91 certification on every visit. The MA 91 statement reads:

> *"My signature certifies that I received a service or item on the date listed above. I understand that payment for this service will be from Federal and State funds, and that any false claims or concealment of material may be prosecuted under Federal and State laws."*

The MA 91 section is at the bottom of every visit form, below the SOAP note fields.

### Collecting a Signature In Person

1. Enter the patient's name in the **Patient name** field.
2. Hand your phone or tablet to the client.
3. They draw their signature on the canvas pad.
4. Click **Save Signature**. A green **✓ Signed** banner replaces the pad.

The signature image is stored securely and linked to the visit.

### Sending a Signature Request by Email (Telehealth)

When the visit is set to Telehealth, the canvas pad is replaced with an email form:

1. Enter the patient's name and email address.
2. Click **Send MA 91 via Email**. ZipZign sends the client a hosted signature request with the MA 91 text.
3. The status changes to **⏳ Signature request sent**.

When the client signs, the status automatically updates to **✓ Signed** (via webhook). If they decline, it shows **✗ Patient declined**.

ZipZign must be configured by your admin before telehealth signatures work. If you see "Configure ZipZign in Settings," contact your administrator.

### Checking Signature Status

The MA 91 status banner appears on every visit form reload — signed/pending/declined states persist. The visit can be saved at any time regardless of signature status; billing workflows enforce MA 91 completion separately.

---

## Claims & Billing

### Submitting a Claim

The **PA Medicaid Claim** section appears at the bottom of each visit form (below the MA 91 section). It shows the billing code, modifier, rate, and diagnosis code for the visit type — all pre-filled automatically.

**MCO routing** determines how the claim is submitted:

| Submission Method | MCOs |
|---|---|
| **Availity (electronic)** | AmeriHealth Caritas, Keystone First, Geisinger Health Plan, Aetna Better Health, UnitedHealthcare Community Plan |
| **Manual portal** | UPMC For You, Health Partners Plans, Highmark Wholecare, FFS |

**Before submitting:**
- Enter the **Referring Provider NPI** (Box 17b) — required; the claim will be rejected without it. After typing the 10-digit NPI, click **Verify NPI** to look it up in the NPPES registry. If found, the referring doctor's name is displayed for confirmation and automatically saved to the client's profile (populating CMS 1500 Box 17).
- Geisinger Health Plan may require a **Prior Authorization Number** (Box 23). If Geisinger is your patient's MCO, an amber-bordered field appears; enter the auth number if you have one.

**Availity MCOs:**
Click **Preview CMS 1500 & Submit**. A preview modal shows all claim boxes filled with your data. Review it, then click **Submit to Availity**. The claim is transmitted electronically and a status badge appears.

**Manual MCOs:**
Click **Preview & Download CMS 1500** to download the completed PDF. Then click the portal link next to the button to open the MCO's submission portal in a new tab. Upload the PDF through their portal.

### Tracking Claim Status

The claim status badge uses four colors:

| Color | Meaning |
|---|---|
| **Amber — Submitted** | Sent to Availity; awaiting acknowledgment |
| **Blue — Processing** | Availity accepted; payer is processing |
| **Green — Paid** | Payment confirmed; paid amount shown |
| **Red — Denied** | Claim denied; denial reason shown below the badge |

**For Availity claims:** Click **Refresh status** to query Availity for the latest 277CA acknowledgment. Status and paid amount update automatically.

**For manual MCO claims:** Use the **Log claim status** form in the claim section to record what the portal or paper EOB shows. Select the status (Submitted / Paid / Denied), date, and paid amount. Click **Save status** — the badge updates immediately.

### Scanning Paper Remittances (EOBs)

**From a single visit page (one patient):**
Open the visit, scroll to the claim section, and click **Scan Remittance / EOB**. Photograph the paper EOB. DoulaShield extracts the status, paid amount, and denial reason for this visit's claim line and updates the record automatically.

**From the Reports page (full remittance, all patients at once):**
Go to **Reports → Remittance / EOB Scan** at the bottom of the page. Photograph the full multi-patient EOB. DoulaShield extracts every claim line and matches each one to a client in your roster by patient name. A review table appears showing:

- Each claim line from the EOB
- The matched client (linked to their profile), or "no match" in gray
- Service date, status, and paid amount
- An **Apply ↓** button for each matched line

Click **Apply ↓** on a row to update that visit's claim status. Rows showing "no claim" mean the visit exists in your roster but no claim has been submitted yet — go to that visit page to submit first. Click **Dismiss** to close the review table.

---

## Reports Dashboard

Go to **Reports** in the sidebar for an at-a-glance view of your practice performance.

### Stats Cards

Three cards at the top:
- **Clients** — total active clients
- **Visits** — completed visits (ended) and total documented
- **Claims** — total claims across all statuses

### Claim Pipeline Tiles

Four colored tiles showing claim counts and amounts by status:

| Tile | What it shows |
|---|---|
| Amber — Submitted | Count + billed amount |
| Blue — Processing | Count + billed amount |
| Green — Paid | Count + amount collected |
| Red — Denied | Count + billed amount |

### Revenue Summary

- **Total Billed** — sum of all billed amounts
- **Total Collected** — sum of paid amounts
- **Collection Rate** — Total Collected ÷ Total Billed × 100 (shown when billed > $0)

### MCO Breakdown Table

One row per MCO. Columns: MCO | Contracted | Patients | Claims | Billed | Paid | Collection %.

- **Contracted** — green "✓ {date}" if you checked that MCO in Settings → MCO Contracts; gray "—" if not
- Contracted MCOs appear first in the table, then others with claim data
- MCOs with no claims yet still appear if you have them checked in Settings

---

## Settings

Access Settings from the sidebar. Changes save when you click **Save settings**.

| Section | Fields |
|---|---|
| **CAQH Attestation** | Last attested on (date); live 90-day expiry countdown; link to CAQH ProView |
| **PROMISe™ Re-enrollment** | Last enrolled on (date); live 5-year expiry countdown; link to PROMISe™ Portal |
| **Provider Identity** | NPI, billing provider name, billing address, phone. After entering your NPI, click **Verify NPI** to confirm it against the NPPES registry — your registered name and taxonomy are shown as confirmation. |
| **Escrow & Billing** | Shows your escrow agreement status and deferred balance (collected from MCO remittances) |
| **PA HealthChoices** | Zone (Southeast, Southwest, Lehigh/Capital, Northeast/Northwest) and counties served (checkbox list) |
| **MCO Contracts** | Checkboxes for all 8 MCOs + FFS; optional contract effective date for each |
| **Availity** | Client ID + Client Secret (write-only after save); Connected ✓ badge |
| **Telehealth** | Meeting room URL (any HIPAA-compliant platform) |
| **Signatures** | Contact email (ZipZign From address); ZipZign API key (write-only after save) |
| **Provider Signature** | Draw your signature on the canvas — embedded as Box 31 on CMS 1500 |
| **SSN (Box 25)** | 9-digit SSN stored encrypted; used as Tax ID on CMS 1500 |
| **Change Password** | Current password + new password (12+ chars, upper, lower, number, special character) |

### CAQH ProView Attestation

CAQH ProView is the credential database used by all PA MCOs to verify provider enrollment. You must re-attest your profile every 90 days. Missing the deadline risks removal from MCO directories, which blocks reimbursement.

**Workflow:**
1. Log in at [proview.caqh.org](https://proview.caqh.org) and complete re-attestation.
2. Return to DoulaShield **Settings → CAQH Attestation** and update **Last attested on** to today's date.
3. The expiry preview updates immediately — green means you have more than 14 days, amber means 14 days or fewer, red means overdue.

**Reminders:** DoulaShield automatically emails you at 30, 14, 7, and 0 days before expiry, and daily for the first 7 days after expiry. If the dashboard shows an amber or red banner, act immediately to avoid billing disruption.

### PROMISe™ Re-enrollment

PA DHS requires every enrolled provider to re-enroll in PROMISe™ every **5 years** (1,825 days). Missing the deadline can suspend your fee-for-service (FFS) billing privileges until re-enrollment is processed.

**Workflow:**
1. Log in at [promise.dhs.pa.gov](https://promise.dhs.pa.gov) and complete the re-enrollment application.
2. Return to DoulaShield **Settings → PROMISe™ Re-enrollment** and update **Last enrolled on** to the date you submitted your re-enrollment.
3. The expiry preview updates immediately — green means more than 90 days remaining, amber means 90 days or fewer, red means overdue.

**Reminders:** DoulaShield automatically emails you at 365, 180, 90, 30, 14, 7, and 0 days before expiry, and daily for the first 7 days after expiry. The 1-year and 6-month reminders give you lead time to gather documentation, since the PA DHS review process can take several weeks. If the dashboard shows an amber or red PROMISe™ banner, begin the re-enrollment process immediately to avoid FFS billing disruption.

---

## Reference: Billing Codes

All billing codes are pre-filled automatically based on visit type. This table is for reference only.

| Visit Type | Procedure Code | Modifier | Rate | Default Diagnosis |
|---|---|---|---|---|
| Prenatal 1–6 | T1032 | U7 | $100.00 | Z32.2 |
| Labor | T1033 | *(none)* | $1,000.00 | Z33.1 |
| Postnatal 1–6 | T1032 | U8 | $100.00 | Z39.1 |
| Crisis / Bereavement | T1032 | U9 | $175.00 | Z39.2 |

**Provider taxonomy:** 374J00000X · **Provider type:** 13 · **Specialty code:** 130

---

## Reference: MCO Submission Channels

| MCO | Submission Method | Availity Payer ID | Portal |
|---|---|---|---|
| AmeriHealth Caritas | Availity (electronic) | AMCRN | — |
| Keystone First | Availity (electronic) | 23284 | — |
| Geisinger Health Plan | Availity (electronic) | 75273 | — |
| Aetna Better Health | Availity (electronic) | AETNB | — |
| UnitedHealthcare Community Plan | Availity (electronic) | 04567 | — |
| UPMC For You | Manual portal | — | [UPMC Health Plan Provider OnLine](https://www.upmchealthplan.com/providers/online) |
| Health Partners Plans | Manual portal | — | [Health Partners Plans Provider Portal](https://www.healthpartnersplans.com/home/providers/claims-and-billing/claim-submissions/) |
| Highmark Wholecare | Manual portal | 25169 (eligibility only) | [Highmark Wholecare Provider Portal](https://www.highmarkwholecare.com/providers/) |
| FFS (Fee-for-Service) | Manual portal | 77799 (eligibility) | [PROMISe™ Provider Portal (PA DHS)](https://promise.dhs.pa.gov/portal/provider) |

---

## Reference: PA HealthChoices Zones

Pennsylvania divides HealthChoices into four geographic zones. Select yours in **Settings → PA HealthChoices Zone**. The zone selection filters the county checkbox list to show only counties in your zone.

| Zone | Counties included |
|---|---|
| **Southeast** | Philadelphia, Bucks, Chester, Delaware, Montgomery |
| **Southwest** | Allegheny, Armstrong, Beaver, Butler, Fayette, Greene, Indiana, Lawrence, Washington, Westmoreland |
| **Lehigh/Capital** | Adams, Berks, Bradford, Carbon, Centre, Clinton, Columbia, Cumberland, Dauphin, Franklin, Fulton, Huntingdon, Juniata, Lancaster, Lebanon, Lehigh, Luzerne, Lycoming, Mifflin, Monroe, Montour, Northampton, Northumberland, Perry, Pike, Schuylkill, Snyder, Sullivan, Susquehanna, Tioga, Union, Wayne, Wyoming, York |
| **Northeast/Northwest** | Cameron, Clarion, Clearfield, Crawford, Elk, Erie, Forest, Jefferson, McKean, Mercer, Potter, Venango, Warren |

If you are unsure which zone covers your counties, contact your Medicaid managed care coordinator or refer to the PA Department of Human Services HealthChoices documentation.
