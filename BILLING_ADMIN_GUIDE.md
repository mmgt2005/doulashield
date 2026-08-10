# DoulaShield Billing Admin Guide

**v1.32.0 · Last updated 2026-06-24**

This guide covers the billing admin workflow in DoulaShield. As a billing admin, you manage claim submissions on behalf of the doula providers assigned to your agency — reviewing claims they send to you, submitting to Availity (or logging manual submissions), and tracking paid and denied outcomes.

---

## Table of Contents

1. [How the Agency Claims Queue Works](#how-the-agency-claims-queue-works)
2. [First Login: Configure Availity Credentials](#first-login-configure-availity-credentials)
3. [Reviewing a Claim](#reviewing-a-claim)
4. [Submitting to Availity](#submitting-to-availity)
5. [Logging a Manual Submission](#logging-a-manual-submission)
6. [Uploading Supporting Documents](#uploading-supporting-documents)
7. [Tracking Paid and Denied Outcomes](#tracking-paid-and-denied-outcomes)
8. [Reference: Claim Status Meanings](#reference-claim-status-meanings)

---

## Onboarding Tour

When a billing admin logs in for the first time after accepting the Terms of Service, a 5-step guided tour starts automatically. It spotlights My Providers, Agency Claims, and Agency Settings in the sidebar, and describes what each section does. Click **Next →** to advance, **← Back** to revisit, or **Skip tour** to dismiss. The tour appears only once per account.

### "Get Started" Checklist

After the tour, a **Get Started** card appears at the top of the My Providers page with four setup tasks:

| Task | Where |
|---|---|
| Set agency name & group NPI | Agency Settings |
| Add your agency billing address | Agency Settings |
| Connect Availity credentials | Agency Settings |
| Confirm providers are in your agency | My Providers |

Each item auto-checks when the data is saved. The card hides when all four are complete or when you click **Dismiss**. If your admin has already configured the agency settings, most items may already be checked when you first log in.

---

## How the Agency Claims Queue Works

When a doula provider assigned to your agency submits a claim, it does **not** go directly to Availity. Instead, it lands in your **Agency Claims** queue with the status **Pending Billing Review**. You decide how to handle each claim from there.

The full lifecycle of an agency claim:

```
Provider submits claim
        ↓
Pending Billing Review  ← your queue
        ↓
  You review & act
        ↓
 Submitted  ──────────────────────────────┐
        ↓                                 │ (manual MCO)
  Processing  (Availity tracking)         │
        ↓                                 │
 Paid / Denied  ←────────────────────────┘
```

Providers can see their claim status in their own Reports page but cannot update it once it is in your queue — all status changes are yours to make.

---

## First Login: Configure Availity Credentials

Before you can submit claims electronically, you need to connect your agency's Availity account.

1. In the sidebar, click **Agency Settings**.
2. Enter your **Availity NPI** (your agency's group NPI as registered with Availity).
3. Enter your **Availity Client ID** and **Client Secret** from your Availity developer account. These are write-only — once saved, the Client Secret is masked and cannot be retrieved, only overwritten.
4. A **Connected ✓** badge appears next to your credentials when the connection is verified.

Without Availity credentials, you can still receive and review claims and log manual submissions. Electronic submission to Availity requires the credentials to be configured.

If you do not yet have an Availity account, create one at availity.com using your agency's group NPI and apply for API access (free developer program).

---

## Reviewing a Claim

All pending claims appear in **Agency Claims**. Use the filter bar at the top to narrow by provider or status.

**To review a claim:**

1. Click anywhere on a claim row to expand the detail panel.
2. The panel shows three sections:

**Claim Details**
- Payer and MCO information
- Procedure code and modifiers (e.g., T1032-U7 for Prenatal 1)
- Diagnosis code (e.g., Z32.2)
- Billed amount, paid amount (if updated), denial reason (if denied)
- Resubmit count and MA 91 signature status

**Visit Notes**
- The SOAP note the provider wrote: Subjective, Objective, Assessment, Plan
- For labor visits: birth entry notes and birth location
- These confirm the service was documented before the claim was submitted

**Documents**
- **Preview CMS 1500** — open the generated CMS 1500 PDF in a preview modal
- **Download Audit Packet** — full 7-section PDF (visit record, SOAP notes, MA 91 signature, CMS 1500, and more)
- **Source Image** — the original source document the provider scanned (if any)
- **Admin Documents** — files you upload yourself (prior auth letters, eligibility confirmations, received EOBs)

---

## Submitting to Availity

For MCOs that support electronic submission (AmeriHealth Caritas, Keystone First, Aetna Better Health, etc.):

1. Expand the claim row.
2. Click **Submit to Availity ↗** in the expanded detail panel.
3. DoulaShield sends an 837P transaction to Availity for the MCO on your behalf.
4. The claim status updates to **Submitted**, then DoulaShield checks Availity periodically and updates to **Processing** → **Paid** or **Denied** automatically.

If submission fails (credential error, validation rejection), the claim returns to **Pending Billing Review** and an error message appears in the row. Correct the issue and resubmit.

**Aetna Better Health note:** DoulaShield submits Aetna Better Health claims via EDI (payer ID 23228). If an Aetna claim fails through the API, use the manual path: log into the Availity portal, click **"Medicaid Claim Submission – Office Ally"**, and submit the claim through Office Ally (free, requires an Office Ally account). Then log the submission in DoulaShield using **Log Manual Submission**. Paper claims mail to: PO Box 982973, El Paso, TX 79998-2973.

---

## Logging a Manual Submission

Use manual logging when you submitted through an MCO's web portal, by phone, by fax, or by mailing a paper CMS 1500 — situations where the submission happened outside of DoulaShield.

1. Expand the claim row.
2. Click **Log Manual Submission** (for claims in Pending Billing Review) or **Update Status** (for already-submitted claims when payment or denial arrives).
3. Fill in the form:
   - **Status**: Submitted / Paid / Denied
   - **Notes** (optional): reference number, submission method, MCO contact name
   - **Paid amount** (shown when Paid is selected)
   - **Denial reason** (shown when Denied is selected)
4. Click **Save**. The claim status updates immediately and the provider can see the outcome in their Reports view.

The claim is flagged as a manual submission (`is_manual = true`) internally, which distinguishes it from Availity submissions in the audit trail.

---

## Uploading Supporting Documents

You can attach files to any claim for internal reference — prior authorization letters, eligibility confirmations, EOBs you received from the MCO, or other correspondence.

1. Expand the claim row.
2. In the **Documents** section, click **+ Upload Document**.
3. Select a document type from the dropdown: **Prior Auth**, **Eligibility Confirmation**, **EOB Received**, or **Other**.
4. Choose a file (PDF, JPEG, or PNG, up to 20 MB).
5. The file appears in the admin documents list. Click **Preview** to open it in a viewer, or download it.

Uploaded documents are linked to the specific claim and visible to all billing admins in your agency. Providers do not see these documents.

---

## Tracking Paid and Denied Outcomes

**Paid claims:**
Once a claim is marked Paid (either by Availity status check or manual logging), it moves out of your active queue. The provider sees the paid status and paid amount in their Reports page. No further action is needed on your end unless you want to attach the EOB for your records.

**Denied claims:**
When a claim is denied, enter the denial reason code (e.g., CO-4, CO-96) in the denial reason field when logging the status. The provider sees the denial in their Reports and can resubmit from the visit page with corrections. Once they resubmit, the corrected claim comes back into your Pending Billing Review queue.

**Partial payments (contractual adjustments):**
Log the status as Paid and enter the actual paid amount (which may be less than the billed amount). The difference is a contractual write-off — do not request the patient pay the difference.

---

## Reference: Claim Status Meanings

| Status | Meaning |
|---|---|
| **Pending Billing Review** | Claim submitted by provider, waiting for your action |
| **Submitted** | You have logged or sent the claim — awaiting MCO response |
| **Processing** | Availity confirmed receipt; MCO is adjudicating |
| **Paid** | MCO approved and paid the claim |
| **Denied** | MCO rejected the claim; provider can resubmit with corrections |

Claims for providers in demo mode are excluded from this queue — they are practice submissions that carry no real billing obligation.
