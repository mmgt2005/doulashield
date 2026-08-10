# DoulaShield User Manual

**v1.39.0 · Last updated 2026-06-26**

This manual covers every provider-facing feature in DoulaShield. Read it start to finish once, then use the headings as a reference when you need a quick reminder.

---

## Table of Contents

1. [Getting Started](#getting-started)
   - [Demo Mode — Practice Walkthrough](#demo-mode--practice-walkthrough)
2. [Credentialing Status](#credentialing-status)
3. [Managing Clients](#managing-clients)
4. [Schedule](#schedule)
5. [Documenting Visits](#documenting-visits)
4. [MA 91 Patient Signatures](#ma-91-patient-signatures)
5. [Claims & Billing](#claims--billing)
   - [Submitting a Claim](#submitting-a-claim)
   - [Tracking Claim Status](#tracking-claim-status)
   - [Denial Error Codes and Resubmission](#denial-error-codes-and-resubmission)
   - [Downloading a Medicaid Audit Packet](#downloading-a-medicaid-audit-packet)
   - [Scanning Paper Remittances (EOBs)](#scanning-paper-remittances-eobs)
   - [Claim Filing Deadlines](#claim-filing-deadlines)
6. [Reports Dashboard](#reports-dashboard)
7. [Settings](#settings)
   - [CAQH ProView Attestation](#caqh-proview-attestation)
   - [PROMISe™ Re-enrollment](#promise-re-enrollment)
   - [PCB Perinatal Certification](#pcb-perinatal-certification)
   - [Liability Insurance](#liability-insurance)
   - [MA 589 Patient Certification](#ma-589-patient-certification)
8. [Reference: Billing Codes](#reference-billing-codes)
9. [Reference: MCO Submission Channels](#reference-mco-submission-channels)
10. [Reference: PA HealthChoices Zones](#reference-pa-healthchoices-zones)

---

## Getting Started

### Finding This Manual Inside the App

This manual is always one click away inside DoulaShield. At the bottom of the left sidebar, under the **Help** heading, click **User Manual** to open it as a styled page without leaving the app. The same Help section also has a **Terms of Service** link where you can re-read the full agreement at any time.

### First Login & MFA Setup

When your account is created, you receive a welcome email with your email address and a temporary password. On first login:

1. Go to the DoulaShield login page and sign in with the credentials from the email.
2. **Terms of Service** — before you can access any page, you are shown the full DoulaShield Terms of Service. Scroll to the bottom of the document, check "I have read and agree to the DoulaShield Terms of Service," then click **I Agree & Continue**. This is a one-time step; you will not be shown the ToS again on subsequent logins.
3. You will be prompted to set up multi-factor authentication (MFA). Open an authenticator app (Google Authenticator, Authy, or any TOTP app) and scan the QR code shown.
4. Enter the 6-digit code from your app to confirm setup. MFA is required on every login going forward.

If your temporary password no longer works, use **Forgot password?** on the login page to request a reset link.

### Onboarding Tour

After you accept the Terms of Service, a short guided tour starts automatically. It highlights the key areas of the platform — the sidebar, your enrollment status, the clients list, and your settings fields — with a dimmed overlay and a tooltip next to each element. The tour navigates between pages on your behalf.

- Click **Next →** to advance, **← Back** to revisit a step, or **Skip tour** (top-right of the tooltip) to dismiss immediately.
- The tour is shown once per account. It will not appear again after you complete or skip it.

### "Get Started" Checklist

After the tour, a **Get Started** card appears at the top of your Dashboard. It tracks the five setup tasks you must complete before you can submit claims:

| Task | Where |
|---|---|
| Enter your NPI number | Settings → Billing provider information |
| Set your billing name & address | Settings → Billing provider information |
| Draw your provider signature | Settings → Billing Credentials |
| Set your PA zone & counties | Settings → PA HealthChoices Zone |
| Add MCO contracts | Settings → MCO Contracts |

Each item is a link that scrolls directly to the relevant section in Settings. A thin progress bar shows how many tasks are done. The card disappears automatically once all five are complete.

If you want to hide the card before completing everything, click **Dismiss** in the card header. You can always complete the remaining items later via the Settings page.

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

### Demo Mode — Practice Walkthrough

If your admin has enabled **Demo Mode** on your account, you will see a **"Walkthrough Guide"** button in the left sidebar. Demo Mode lets you practice the full billing workflow — adding clients, documenting visits, collecting signatures, submitting claims, and scanning an EOB — without sending anything to Availity or touching any real claim data.

**What happens in Demo Mode:**

- Claim submissions are intercepted and return a simulated response. Nothing goes to Availity.
- The claim appears in your pipeline with a `DEMO-XXXXXXXX` claim ID so you know it is not real.
- All other features work exactly as they do in production: CMS 1500 generation, audit packets, SOAP notes, and MA 91 signatures all function normally.

**Using the Walkthrough Guide:**

Open the guide from the sidebar button. It provides:

1. Step-by-step workflow instructions (add client → document visit → sign MA 91 → submit claim → explore reports → scan EOB).
2. Sample SOAP notes you can copy into any prenatal visit.
3. A table of 10 sample patients with Medicaid IDs, MCOs, dates of birth, and addresses — use any row when creating a practice client.
4. A **Download Sample Remittance Advice (EOB)** link — a realistic PA Medicaid remittance PDF showing five claim outcomes (paid, partial adjustment, and two denials). Download it and upload it on the Reports page (step 6) to practice the full EOB scan flow.

When you are ready for live billing, ask your admin to disable Demo Mode. Demo clients added during the walkthrough are removed automatically at that point.

### Understanding the Dashboard

The main Dashboard (first page after login) shows alert banners at the top whenever a credential is expiring or a claim deadline is approaching. Banners are **amber** for upcoming deadlines and **red** when a deadline has already passed or is imminent (≤7 days).

| Banner | Appears when | What to do |
|---|---|---|
| CAQH attestation | ≤14 days to 90-day re-attestation deadline | Re-attest at proview.caqh.org, then update **Settings → CAQH Attestation** |
| PROMISe™ re-enrollment | ≤90 days to 5-year re-enrollment deadline | Re-enroll at promise.dhs.pa.gov, then update **Settings → PROMISe™ Re-enrollment** |
| PCB Perinatal Certification | ≤60 days to 2-year renewal deadline | Renew at pacertboard.org, then update **Settings → PCB Perinatal Certification** |
| Liability insurance | ≤30 days to policy expiry | Renew your policy, then update **Settings → Liability Insurance** |
| Claim deadline — overdue | Any unfiled claim is past the 180-day PA Medicaid deadline | Open the client record and file or correct the claim immediately |
| Claim deadline — urgent | Any unfiled claim is within 30 days of the 180-day deadline | Open the client record and file the claim |

Banners clear automatically once the date is updated in Settings (for credential banners) or the claim is filed/paid (for deadline banners). There is no dismiss button — the only resolution is completing the underlying action.

The **Reports Dashboard** (sidebar → Reports) is a separate page showing billing pipeline statistics, revenue, and MCO breakdown. It is not the same as the main Dashboard.

If your agency has started your credentialing process, the dashboard also shows a **Credentialing Status** card — see [Credentialing Status](#credentialing-status) below.

---

## Credentialing Status

DoulaShield tracks your four-stage Medicaid credentialing process: **PCB Certification → NPPES / NPI Setup → Enrollment (Stage 2) → MCO Contracting (Stage 3)**. Your agency sets up and manages each stage on your behalf; you can view your progress and upload required documents at any time.

### Dashboard Card

Once your agency has started at least one credentialing stage, a **Credentialing Status** card appears on your main Dashboard showing:
- Your current active stage and its status (in progress / complete)
- How many tasks are complete out of the total for that stage
- Stage pipeline pills (✓ complete · ● in progress · ○ not started)
- A **View details →** link to the full Enrollment Status page

### Enrollment Status Page

Go to **Sidebar → Enrollment Status** to see your full credentialing checklist.

**Authorization agreement — first visit only**

The first time you open the Enrollment Status page you will be asked to read and sign the **Authorized Delegate and NPI Surrogate Authorization Agreement**. This agreement authorizes DoulaShield to act as your administrative delegate in NPPES, CMS I&A, CAQH ProView, and PROMISe™ so your agency can complete NPI applications, enrollment forms, and attestations on your behalf. Once you check the box and click **Sign & Continue**, your electronic signature is recorded and you will not be asked again. The date of signing appears in the page header on all future visits. To revoke this authorization at any time, contact support@doulashield.com — the agency will cease surrogate activity within 48 business hours and transfer your credentials back to you.

**What you can do on this page:**
- Read the task list for each stage — each task includes a description of exactly what document to gather and what it must show
- See which tasks are complete, in progress, or not yet started
- Fill in your PCB application info directly in DoulaShield (see below) and download a pre-filled PDF
- Upload documents for any task that isn't yet complete (PDF, JPEG, or PNG, up to 20 MB per file)
- View documents you've already uploaded by clicking the filename chip under each task

**What only your agency can do:**
- Mark tasks as complete
- Advance you to the next stage
- Record completion dates (PCB certificate date, NPI number, PROMISe™ enrollment date, etc.)

**PROMISe™ enrollment tasks (Stage 2):** The two PROMISe™ tasks — Medicaid (Type 13) and CHIP (Type 130) — show a short status message rather than the full admin portal instructions. When either task is in progress, you will see a note that your enrollment specialist is completing the application and that you will be contacted by screen-share when it is time for your final attestation step (a step only you can complete). When the task is marked complete, the ATN (Application Tracking Number) assigned by DHS appears below the task — this is the tracking token you can reference if you want to check your application status.

**Uploading a document:**
1. Click **+ Upload Document** under the relevant task
2. Select a PDF, JPEG, or PNG file (max 20 MB)
3. The file uploads immediately and appears as a chip under the task
4. The task status automatically changes from "not started" to "in progress" on your first upload

Tabs at the top of the page (PCB Certification · NPPES / NPI Setup · Enrollment — Stage 2 · MCO Contracting — Stage 3) are enabled only for stages your agency has opened for you. Disabled tabs mean that stage hasn't been started yet.

### PCB Application Info & Pre-filled Download

The first task on your PCB Certification stage — **PCB Application Info** — has an inline form where you enter your personal details exactly as they should appear on your PCB application:

- Full legal name (as it should appear on your certificate)
- Mailing address, phone, and email
- Gender, race/ethnicity, and primary language
- Doula type (Birth, Postpartum, Perinatal, or Other)

Click **Save Info** to store your answers.

#### Secure Information (SSN, Date of Birth, Tax ID)

Below the standard fields is an amber **Secure Information** section for sensitive identifiers. These are stored encrypted and never written to logs or unencrypted storage:

- **Social Security Number** — enter either your last 4 digits or your full 9-digit SSN. Only the last 4 digits appear on the pre-filled PDF. If a value is already saved, the label shows the last 4 digits on record (e.g. "ending ••••1234") and you can update it at any time.
- **Date of Birth** — stored encrypted and used to populate the DOB field on the pre-filled PCB application PDF.
- **Tax ID / EIN** — optional. Agencies may use this for 1099 reporting. Leave blank if not applicable.

Click **Save Secure Info** after entering any of these fields. Because SSN is shown as a password input it is never displayed in plaintext on screen.

Once both sections are saved, click **↓ Download Pre-filled Application** to download a PDF with pages 6–8 of the PCB application pre-populated with your info, plus a live checklist of your task statuses. Print the pre-filled sheet, sign pages 12–13, take page 14 to a notary (a UPS Store, bank branch, or public library works), and submit the complete PDF package to PCB.

A link to the blank official PCB application is also available on the page if you need it for reference.

**PCB tasks on both pathways include:**
- Your application info form (completed above)
- Training certificates or experience documentation, CPR cert, client evaluations
- **Notarized Acknowledgements & Release** — page 14 must be signed in front of a notary public. Electronic notarization is not accepted.
- **Submit Application + Pay $50 Fee** — email the complete PDF to info@pacertboard.org with a $50 check or payment per PCB's current instructions. Note your submission date in the task notes.

**Downloadable forms on task cards:**
Each client evaluation task shows a **Download PCB Client Evaluation Form →** link so you can print the official form and give it to your client to complete. Each letter of recommendation task (experienced pathway) shows a **Download Recommendation Letter Template →** link — a fill-in PDF you can hand to clients to guide them in writing their letter. Both links open the document in a new tab.

### 5-Year Work History Bio-Builder

The **5-Year Work History** task in your MCO Contracting stage includes an AI-powered tool that turns your rough notes into a state-compliant work history table — no resume required.

#### Before you start (about 40 minutes total)

Click **"Before You Start — How to Gather Your Work History"** to expand the four prep steps:

1. **Audit Digital Financial Trails** (~15 min) — Log into TurboTax, TaxSlayer, or IRS.gov and pull W-2s or 1099s for the past 5 years. For private-pay work, search Stripe, PayPal, or bank statements for recurring client deposits to pin down the months you were actively working.
2. **Scrape Birth Platforms & Calendars** (~15 min) — Check your history on DoulaMatch or local collective directories. Search Google Calendar or Apple Calendar for "birth," "prenatal," "postpartum," or "client" to find exact start and end dates for contract blocks.
3. **Map Out the Gaps** (~10 min) — Identify any months where no formal employment or active clients occurred. Note the reason — PA Medicaid rejects applications with unexplained gaps over 30 days.
4. **Execute the Brain Dump** (~5 min) — Don't worry about formatting. Write a messy chronological list of dates, organization names (or "Independent Practice"), addresses, and what you did. Then paste it into the text box below the prep steps.

#### Generating your work history

After pasting your notes, click **Generate Work History with AI**. DoulaShield sends your text to an AI and returns:

- A formatted table with columns: Start Date, End Date, Employer/Organization Name, Address, Job Title, Description of Duties — in reverse chronological order covering the past 5 years.
- A **Gap Log** (amber box) listing any periods over 30 days with a plain-English explanation for each gap.

The result is saved automatically. If you close the page and come back, your table is still there.

To save your notes without regenerating (for example, mid-session), click **Save Notes** below the text box. Your text is preserved so you can pick up later without losing your work.

To revise your notes and regenerate, click **Edit / Regenerate** — your original text reappears in the text box ready to edit. Click **Save Notes** again if you want to save the revised text before running the AI.

Once you are satisfied with the AI output, upload your final signed PDF work history document using the **+ Upload Document** button below the table.

### Resume / CV Generator

The **Resume / CV** task in your MCO Contracting stage includes an AI-powered tool that generates a professional credentialing resume ready for MCO applications — no writing required.

#### What you need to enter

The form has four fields:

- **Full Name** — your name as it should appear at the top of the resume
- **Certifications & Credentials** — list each credential on a new line (e.g., "PCB Certified Perinatal Doula — issued Jan 2024", "CPR/AED — expires Dec 2025")
- **Work History Summary** — paste or type your work history in plain language. You can paste your AI-generated work history table from the 5-Year Work History task, or write freeform notes. The AI will organize and format it.
- **Care Philosophy** — one or two sentences about your approach to doula care. This appears at the bottom of the resume as a personal statement. Leave blank if you prefer not to include one.

Click **Save Draft** at any time to preserve what you have entered without running the AI.

#### Generating and downloading your resume

Click **Generate Resume with AI**. DoulaShield formats your inputs into a structured resume with:

- A credentials header (name + credentials line)
- Professional summary
- Certifications table (credential, date issued, expiry if applicable)
- Work experience table
- Education list
- Skills section
- Care philosophy statement (if provided)

The structured preview appears immediately on screen. Click **↓ Download Resume PDF** to download a print-ready PDF formatted for MCO credentialing submissions.

To make changes, click **Edit / Regenerate** — your original inputs reappear so you can update any field and run the AI again. Click **Save Draft** to save edits before regenerating.

### MCO Contracting Tasks

Your MCO Contracting stage (Stage 3) includes a separate task for each Managed Care Organization (MCO) you will be contracted with. Each task shows its name and status badge (Not Started / In Progress / Complete).

The detailed enrollment steps for each MCO are managed by your billing admin or DoulaShield staff. You will see the task status update as your agency works through the process on your behalf. If you have questions about the status of a specific MCO contract, contact your billing admin directly.

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

When a Medicaid card has been scanned for a client, a small **"Card scanned"** badge with a camera icon appears next to the MCO line in the client header. This lets you confirm at a glance that a card image is on file (which also enables the embedded card image in the audit packet).

### Checking Medicaid Eligibility

On any client's overview page, the eligibility row shows the last checked status (**Active** or **Inactive**) and date. Click **Check eligibility** to query the MCO in real time through Availity.

Requirements: Availity credentials connected in Settings, client has an MCO and date of birth on file.

### Adding a Referring Provider

The referring physician's NPI (Box 17b) and name (Box 17) are required on every claim. Enter them in the client profile under **Referring Provider NPI** and **Referring Provider Name**. These fields are shared across all visits for that client — enter them once and they auto-fill every CMS 1500.

After typing the 10-digit NPI in the client profile edit form, click **Verify NPI** to look it up in the NPPES registry. If found, the referring doctor's name is automatically filled into the **Referring Provider Name** field (CMS 1500 Box 17) — no manual name entry needed.

On a **Prenatal 1** visit, you can scan the MA 589 physician certification form to auto-fill both fields:

1. Open the Prenatal 1 visit form.
2. In the **Scan MA 589** section, photograph the form.
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

## Schedule

The **Schedule** page (sidebar → Schedule) shows all your visits for the current week across every client, grouped by day. Use it to plan upcoming visits and see your workload at a glance.

### Viewing Your Week

The page opens on the current week (Monday–Sunday). Use the **←** and **→** buttons to navigate to previous or future weeks. Click **Today** to jump back to the current week.

Each visit card shows:
- **Visit type** — e.g., Prenatal 2, Labor, Postnatal 1
- **Client name**
- **Planned time** (if set) and a status badge

Status badges:
| Badge | Meaning |
|---|---|
| Blue — time shown | Scheduled, not yet started |
| Amber — In progress | Visit started but not ended |
| Green — Done | Visit ended |

Click any card to open that visit's form directly.

The schedule shows visits that have a planned time (`scheduled_at`), a visit date, or a recorded start time. A visit with none of those fields does not appear on the schedule until you set a planned time or start the visit.

### Pre-scheduling a Visit

To add a visit to your schedule before you go:

1. Open the client → click the visit slot (e.g., Prenatal 3).
2. At the top of the form, find **Planned date & time (optional)**.
3. Pick a date and time using the date/time picker.
4. Scroll down and click **Save visit** (or any other save action).

The visit now appears on the Schedule page for that day. The planned time field is hidden once you click Start Visit — at that point the actual start time takes over.

### Today's Visits (Dashboard Widget)

If you have any visits scheduled or started today, a **Today's Visits** card appears on your Dashboard above the Clients and Reports links. Each row shows the visit label, client name, and time (or "In progress" / "Done" if the visit is underway). Click a row to open the visit form. The widget is hidden when there are no visits today.

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

**Pre-scheduling (optional):**
If you know when the visit will happen, set the **Planned date & time** field at the top of the visit form before you arrive. This makes the visit appear on your Schedule page. The field disappears once the visit is started.

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

**If your account is managed by a billing agency:**
The button reads **Preview CMS 1500 & Submit for Review** and the modal submit button reads **Send to Agency Review**. An orange notice in the modal confirms the claim will go to your billing agency's review queue first. Once you submit, the status badge shows **Pending Agency Review** (orange). Your billing agency reviews the claim and submits it to Availity on your behalf (or logs a manual submission if the MCO requires paper or portal filing) — you do not need to take any further action. The **Refresh status** button is hidden while the claim is pending agency review; it reappears once the agency has submitted the claim to Availity.

**Manual MCOs:**
Click **Preview & Download CMS 1500** to download the completed PDF. Then click the portal link next to the button to open the MCO's submission portal in a new tab. Upload the PDF through their portal.

### Tracking Claim Status

The claim status badge uses four colors:

| Color | Meaning |
|---|---|
| **Orange — Pending Agency Review** | Queued for your billing agency to review and submit to Availity |
| **Amber — Submitted** | Sent to Availity; awaiting acknowledgment |
| **Blue — Processing** | Availity accepted; payer is processing |
| **Green — Paid** | Payment confirmed; paid amount shown |
| **Red — Denied** | Claim denied; denial reason shown below the badge |

**For Availity claims:** Click **Refresh status** to query Availity for the latest 277CA acknowledgment. Status and paid amount update automatically.

**For manual MCO claims:** Use the **Log claim status** form in the claim section to record what the portal or paper EOB shows. Select the status (Submitted / Paid / Denied), date, and paid amount. Click **Save status** — the badge updates immediately. If your account is managed by a billing agency, this form is not available; your billing admin updates the claim status on your behalf after handling the submission.

### Denial Error Codes and Resubmission

When a claim is denied, DoulaShield automatically reads the denial reason and matches it to a known error code. A color-coded detail card appears below the denied badge showing:

- **Code** — a short identifier (e.g. MOD-U8, SIG-MISS)
- **Description** — what went wrong
- **Risk** — the compliance or payment consequence
- **Fix instructions** — exactly what to correct before resubmitting

The four built-in codes are:

| Code | Problem |
|---|---|
| **MOD-U8** | Missing or incorrect modifier — U8 required on T1032 postnatal visits; T1033 Labor requires no modifier |
| **SIG-MISS** | Provider or client signature not detected |
| **DT-RANGE** | Service date is in the future or beyond the 365-day filing limit |
| **DUP-CLAIM** | Same client ID and service date already exist in the system |

If the payer returns a standard X12 adjustment code (e.g. CO-45) that isn't in the list above, DoulaShield captures it automatically and stores it for future reference.

**To resubmit:** After correcting the underlying issue, click **↺ Resubmit Claim** in the claim section. For Availity claims the original claim is re-posted using the stored data. For manual MCO claims the status resets to Submitted so you can track the new outcome. The resubmission count is shown next to the button so you always know how many attempts have been made.

**CMS 1500 Box 22 on resubmissions:** DoulaShield automatically sets Box 22 (Resubmission Code / Original Ref. No.) to code **7** (replacement claim) with the original Availity claim ID as the reference number. Original claims use code **1**. This tells Availity and the MCO that the claim is a correction of a prior submission rather than a duplicate, and is required for the resubmission to be processed correctly.

### Downloading a Medicaid Audit Packet

Once a claim exists for a visit, a **📋 Download Audit Packet** button appears in the **PA Medicaid Claim** section of the visit form, directly below the claim status panel. Click it to download a single PDF that assembles every document a PA Medicaid auditor expects:

1. **Cover / Claim Summary** — patient initials, Medicaid ID (last 4), MCO, service date, procedure code, billed and paid amounts.
2. **Member Information & Eligibility** — full patient demographics, eligibility status and last verified date, embedded Medicaid card image (if scanned).
3. **Service Documentation** — visit type, dates/times, duration, location, full SOAP note, visit entry notes, referring provider, prior authorization number.
4. **MA 91 Certification** — the full legal MA 91 text, patient name, signed timestamp, and embedded signature image (in-person). For telehealth visits where the patient signed via ZipZign, the actual signed PDF document is appended immediately after this section so auditors have the fully executed document with the ZipZign request ID on record.
5. **Provider Credentials** — NPI, CAQH attestation date and days until expiry, PROMISe™ re-enrollment date and days until expiry, PCB certification, liability insurance expiry, MCO contracts.
6. **Billing Record** — claim ID, submission date, current status, billed/paid amounts, denial reason, remittance linkage.
7. **CMS 1500** — the completed form appended as the final pages.

The audit packet is for your records and any auditor requests — no patient signature is required to generate it.

### Scanning Paper Remittances (EOBs)

> **Note for agency-assigned providers:** If your account is managed by a billing agency, the EOB scan features (both on the visit page and the Reports page) are not available to you. Your billing agency handles remittance processing and updates claim statuses on your behalf.

Both EOB scan entry points accept **photos (JPEG/PNG)** and **digital PDF files** (up to 20 MB). Use **Take photo** to photograph a paper remittance with your phone camera, or **Upload PDF / image** to upload an EOB PDF you received by email or downloaded from an MCO portal.

**From a single visit page (one patient):**
Open the visit, scroll to the claim section, and click **Scan Remittance / EOB**. Photograph the paper EOB or upload the PDF. DoulaShield extracts the status, paid amount, and denial reason for this visit's claim line and updates the record automatically.

**From the Reports page (full remittance, all patients at once):**
Go to **Reports → Remittance / EOB Scan** at the bottom of the page. Photograph or upload the full multi-patient EOB. DoulaShield extracts every claim line and matches each one to a client in your roster by patient name. A review table appears showing:

- Each claim line from the EOB
- The matched client (linked to their profile), or "no match" in gray
- Service date, status, and paid amount
- An **Apply ↓** button for each matched line

Click **Apply ↓** on a row to update that visit's claim status. Rows showing "no claim" mean the visit exists in your roster but no claim has been submitted yet — go to that visit page to submit first. Click **Dismiss** to close the review table.

### Claim Filing Deadlines

Pennsylvania Medicaid imposes strict timely-filing deadlines. A claim received after the deadline is automatically rejected and cannot be recovered.

| Claim type | Deadline | Clock starts |
|---|---|---|
| **Initial claim** | 180 days | Service date |
| **Corrected / resubmitted claim** | 365 days | Original service date |
| **Secondary claim** (patient has other insurance) | 60 days | EOB payment date |
| **Best practice** | 30 days | Service date |

The 30-day best-practice window is not a hard deadline, but MCOs process claims faster and with fewer denials when they are submitted within 30 days of service.

**Inline warning on the visit form:**
When a visit has been ended but no claim has been filed, the PA Medicaid Claim section shows a color-coded banner once 30 days have passed since service:
- **Blue** — 30 or more days since service; PA Medicaid recommends filing within 30 days
- **Amber** — within 30 days of the 180-day deadline; file now
- **Red** — within 7 days of the deadline or already overdue; claim may not be reimbursable

**Dashboard banners:**
The main Dashboard shows an amber banner when any unfiled claim is within 30 days of the 180-day cutoff, and a red banner when any claim has already passed it. Click the link in the banner to go directly to your clients list.

**Automated email reminders:**
DoulaShield sends email reminders as filing deadlines approach:
- *Initial claims* — reminders at 150 days remaining (30-day best-practice nudge), then 90, 60, 30, 14, 7, and 0 days, then daily for the first 7 days overdue
- *Corrected/resubmitted claims* — reminders at 335 days remaining, then 180, 90, 30, 14, 7, and 0 days, then daily for 7 days overdue
- *Secondary claims* — reminders at 30, 14, 7, and 0 days remaining, then daily for 7 days overdue

Reminder emails show the patient's initials (e.g., J.D.) rather than their full name for privacy.

---

## Reports Dashboard

Go to **Reports** in the sidebar for an at-a-glance view of your practice performance.

### Filtering by Date Range

A row of preset buttons appears below the page title. Click any preset to scope all stats to that window:

| Preset | What it covers |
|---|---|
| **This Month** | 1st of the current month through today |
| **Last Month** | Full prior calendar month |
| **Last 3 Months** | Rolling 3 months back from today |
| **Last 6 Months** | Rolling 6 months back from today |
| **Last 180 Days** | The PA Medicaid timely-filing window |
| **Year to Date** | January 1 of the current year through today |
| **Last Year** | Full prior calendar year (Jan 1 – Dec 31) |
| **All Time** | No date filter — full history (default) |
| **Custom** | Enter a From and To date manually |

When a date range is active, the active window appears as a subtitle under the page title (e.g., `2026-01-01 → 2026-06-30`). The **Clients** card and the claim-deadline warnings on your main Dashboard always show all-time totals regardless of the selected range.

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
| **PCB Perinatal Certification** | Last certified on (date); live 2-year expiry countdown; link to PA Certification Board |
| **Liability Insurance** | Policy expiry date; live countdown; amber ≤30 days, red when expired |
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

**Reminders:** DoulaShield automatically emails you at 30, 14, 7, and 0 days before expiry, and daily for the first 7 days after expiry. The 30-day email is an early warning — the dashboard banner does not appear until 14 or fewer days remain. Do not wait for the dashboard banner to act; start re-attestation when you receive the 30-day email.

### PROMISe™ Re-enrollment

PA DHS requires every enrolled provider to re-enroll in PROMISe™ every **5 years** (1,825 days). Missing the deadline can suspend your fee-for-service (FFS) billing privileges until re-enrollment is processed.

**Workflow:**
1. Log in at [promise.dhs.pa.gov](https://promise.dhs.pa.gov) and complete the re-enrollment application.
2. Return to DoulaShield **Settings → PROMISe™ Re-enrollment** and update **Last enrolled on** to the date you submitted your re-enrollment.
3. The expiry preview updates immediately — green means more than 90 days remaining, amber means 90 days or fewer, red means overdue.

**Reminders:** DoulaShield automatically emails you at 365, 180, 90, 30, 14, 7, and 0 days before expiry, and daily for the first 7 days after expiry. The 1-year and 6-month reminders give you lead time to gather documentation, since the PA DHS review process can take several weeks. If the dashboard shows an amber or red PROMISe™ banner, begin the re-enrollment process immediately to avoid FFS billing disruption.

### PCB Perinatal Certification

The Pennsylvania Certification Board (PCB) requires doulas to renew their perinatal certification every **2 years** (730 days). An expired certification can affect your ability to document and bill for doula services.

**Workflow:**
1. Complete renewal through the [PCB portal](https://www.pacertboard.org).
2. Return to DoulaShield **Settings → PCB Perinatal Certification** and update **Last certified on** to your renewal date.
3. The expiry preview updates immediately — green means more than 60 days remaining, amber means 60 days or fewer, red means overdue.

**Reminders:** DoulaShield automatically emails you at 60, 30, 14, 7, and 0 days before expiry, and daily for the first 7 days after expiry.

### Liability Insurance

Keep your malpractice/liability insurance policy details current. DoulaShield tracks the **policy expiry date** directly — enter the date printed on your policy declarations page.

**Workflow:**
1. In **Settings → Liability Insurance**, enter your policy's expiry date.
2. The status updates immediately — green means more than 30 days remaining, amber means 30 days or fewer, red means expired.
3. When you renew, update the expiry date to your new policy end date.

**Reminders:** DoulaShield automatically emails you at 30, 14, 7, and 0 days before expiry, and daily for the first 7 days after expiry.

### MA 589 Patient Certification

The MA 589 Physician Certification form must be completed for each patient before services can be billed. When a client has a Prenatal 1 visit started but no MA 589 on file, an amber **"MA 589 not signed"** badge appears on the client overview page. DoulaShield also sends a daily email reminder until the form is recorded.

**Workflow:**
1. Have the referring physician sign the MA 589 form.
2. Open the client's profile.
3. Click **Edit profile** and enter the date the form was signed in the **MA 589 signed date** field.
4. The badge disappears once the date is recorded.

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

| MCO | Submission Method | EDI Payer ID | Portal / Notes |
|---|---|---|---|
| AmeriHealth Caritas | Availity (electronic) | AMCRN | — |
| Keystone First | Availity (electronic) | 23284 | — |
| Geisinger Health Plan | Availity (electronic) | 75273 | — |
| Aetna Better Health | Availity / Office Ally | 23228 | Electronic: DoulaShield submits via Availity API (payer 23228). Portal fallback: Availity → "Medicaid Claim Submission – Office Ally" (free; requires Office Ally account). Paper: PO Box 982973, El Paso, TX 79998-2973. |
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
