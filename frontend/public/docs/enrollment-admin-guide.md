# DoulaShield Enrollment Admin Guide

**v1.33.0 · Last updated 2026-06-26**

This guide covers the PCB (Pennsylvania Certification Board) credentialing workflow for admins managing the end-to-end enrollment service. As an enrollment admin, you create enrollment services on behalf of doula providers, collect and verify the required documents, and record outcomes back to the provider's profile.

---

## Table of Contents

1. [How the Enrollment Service Works](#how-the-enrollment-service-works)
2. [Choosing the Right PCB Pathway](#choosing-the-right-pcb-pathway)
3. [Starting an Enrollment Service](#starting-an-enrollment-service)
4. [Task-by-Task Guide: Education/Training Pathway](#task-by-task-guide-educationtraining-pathway)
5. [Task-by-Task Guide: Experienced Pathway](#task-by-task-guide-experienced-pathway)
6. [Submitting to PCB](#submitting-to-pcb)
7. [Recording the PCB Certificate](#recording-the-pcb-certificate)
8. [Reference: Task Completion Checklist](#reference-task-completion-checklist)

---

## How the Enrollment Service Works

When you create an enrollment service for a provider, DoulaShield automatically generates the correct task checklist based on the pathway you select. You work through each task — uploading documents and marking tasks complete — until all required items are in place. Then you submit the application to PCB at pacertboard.org/doula and record the certificate when it arrives.

```
Select pathway
      ↓
Checklist generated automatically
      ↓
Collect + upload documents for each task
      ↓
Mark tasks complete (DoulaShield validates hours)
      ↓
Submit application to PCB (pacertboard.org/doula)
      ↓
Record certificate date in DoulaShield
      ↓
Provider's pcb_last_certified_on updated → Stage 2 (PROMISe, CAQH) unlocked
```

PCB does not have an API — all submissions go through their online application form or by mail.

---

## Choosing the Right PCB Pathway

| If the provider… | Use this pathway |
|---|---|
| Completed a formal doula training program | Education/Training |
| Is already working as a doula (active clients) | Experienced |
| Unsure — default to | Education/Training |

The Education/Training pathway is available to ALL applicants regardless of experience. When in doubt, choose it. The Experienced pathway requires proof of active practice, client evaluations within the last year, AND three letters of recommendation — all three, all from the past year.

---

## Starting an Enrollment Service

1. In the sidebar, click **Admin → Enrollment Services**.
2. Click **+ New Enrollment Service**.
3. Select the provider from the dropdown.
4. Choose the PCB pathway: **Education/Training** or **Experienced**.
5. Click **Create Service** — DoulaShield generates the task checklist automatically.

The pathway can be changed until the first task is marked complete.

---

## Task-by-Task Guide: Education/Training Pathway

### Task 1: Training Certificate(s) — 24 Hours Minimum

**What to collect from the provider:**
A certificate of completion from their doula training program. Acceptable programs include DONA International, CAPPA, ProDoula, Birthing From Within, or any recognized perinatal doula training program. The certificate must show the number of training hours.

**What to verify before uploading:**
- Total hours documented across all certificates must be at least 24
- All 24 hours must relate to perinatal doula knowledge areas (birth support, postpartum care, breastfeeding support, perinatal mood disorders, etc.)
- General topics like "customer service" or unrelated healthcare training do not count toward the 24

**How to enter in DoulaShield:**
Upload the certificate PDF or image. In the **Total training hours** field, enter the cumulative hours from all uploaded certificates. DoulaShield will prevent task completion if the total is under 24.

**If the provider cannot provide a certificate:**
Contact their training program directly — most programs issue replacement certificates for a small fee. PCB does not accept a self-reported hour count without documentation.

---

### Task 2: HIPAA/Confidentiality Training Certificate — 1 Hour Minimum

**What to collect from the provider:**
A certificate showing completion of a HIPAA or client confidentiality course. This can be:
- A standalone online HIPAA training (HIPAATraining.com, Compliancy Group — free options available)
- A confidentiality module within their doula training program **if** the program explicitly lists HIPAA or client confidentiality as a topic with separate hours

**What to verify before uploading:**
- Certificate explicitly mentions HIPAA, health information privacy, or client confidentiality
- At least 1 hour documented
- Certificate is dated (any date is acceptable — PCB does not specify recency for this item)

**If this is part of the same training program certificate:**
If the training certificate lists HIPAA as a distinct topic with hour tracking, you can upload the same file for both Task 1 and Task 2. Enter the HIPAA-specific hours separately in the HIPAA hours field.

---

### Task 3: CPR Certification — Adult + Infant

**What to collect from the provider:**
A valid, unexpired CPR certification card or certificate. Must explicitly cover both:
- Adult CPR
- Infant CPR (or "pediatric" — this covers infants)

**Accepted sources:** American Heart Association (BLS for Healthcare Providers), American Red Cross (CPR/AED for Professional Rescuers), or equivalent. Online-only CPR certifications without a hands-on skills component are NOT accepted by PCB.

**What to verify before uploading:**
- Not expired (check expiration date — most CPR certs are valid 2 years)
- "Adult and infant" competencies explicitly listed
- Issued by a recognized organization

**If the CPR cert is expired:**
The provider must renew before PCB will process the application. Most local hospitals and fire stations offer BLS renewal courses (typically 2–3 hours).

---

### Tasks 4, 5, 6: Client Evaluations

**What to collect from the provider:**
Three completed PCB Client Evaluation forms — one per family served. PCB provides the official form at pacertboard.org/doula. Download it and share with the provider to distribute to families.

**What to verify before uploading:**
- Three separate evaluations from three different families
- Each form must be signed by the client (family member), not the doula
- Forms can be handwritten or typed; PCB accepts both

**How to handle reluctant families:**
Remind the provider that PCB evaluations are brief (one page) and can be completed by email, mail, or in person. The provider gives the blank form to the family at or after the last visit.

---

## Task-by-Task Guide: Experienced Pathway

### Task 1: Proof of Active Practice

**What to collect from the provider:**
Documentation that they are currently working as a doula. Acceptable forms include:
- A letter from a doula agency confirming active contractor status
- An active listing on a doula directory (DoulaMatch, DONA member directory, etc.) — screenshot with URL
- Business registration or DBA filing if they operate independently
- A signed statement from a recent client confirming doula services (not a PCB evaluation form)

**What to verify before uploading:**
- Evidence is current (within the last 6 months preferred)
- Clearly identifies the provider by name

---

### Task 2: CPR Certification — Adult + Infant

Same requirements as Education/Training pathway Task 3 above.

---

### Tasks 3, 4, 5: Client Evaluations (within last year)

Same requirements as Education/Training pathway Tasks 4–6, with one additional requirement:

- All three evaluations must be from families served **within the last 12 months**
- Check the service date on each form before uploading

---

### Tasks 6, 7, 8: Letters of Recommendation (within last year)

**What to collect from the provider:**
Three letters of recommendation from families the doula served. These are **different** from client evaluations — they are free-form letters, not PCB forms.

**What to verify before uploading:**
- Three separate letters from three different families
- Each letter must be signed by the client (family member)
- Must be from families served within the **last 12 months** (PCB requirement for Experienced pathway)
- Letters should describe the doula's support during pregnancy, labor, or postpartum period
- No minimum length — even a brief sincere letter is acceptable

**How to help providers collect recommendation letters:**
Provide the provider with a sample request they can send to past clients:

> *"I am applying for my PCB Certified Perinatal Doula credential. Would you be willing to write a brief letter describing your experience working with me? It can be as short as a paragraph. I need it signed and dated. Thank you so much."*

---

## Submitting to PCB

Once all tasks are marked complete, submit the application to PCB at **pacertboard.org/doula** through their online application form or by mail.

**Before submitting, confirm:**
- [ ] All tasks marked complete in DoulaShield
- [ ] Training hours total ≥ 24 (Education/Training pathway)
- [ ] HIPAA training hours ≥ 1 (Education/Training pathway)
- [ ] CPR cert is current and not expired
- [ ] Three client evaluations collected and signed
- [ ] Experienced pathway: evaluations and letters all from within the last year
- [ ] PCB application fee paid (check current fee at pacertboard.org/doula)

**After submitting:**
Update the enrollment service status by clicking **Mark as Submitted to PCB** in DoulaShield. PCB typically processes applications within 4–6 weeks.

---

## Recording the PCB Certificate

When the provider receives their PCB certificate:

1. Go to **Admin → Enrollment Services** → open the service.
2. Upload the certificate file as a document on the service page.
3. Click **Mark PCB Complete** and enter the certificate issue date.
4. DoulaShield writes the certification date to the provider's profile (`pcb_last_certified_on`). The provider will see this date in their Settings page.

Note the certificate number in the task notes — it is required when completing CAQH ProView entry in Stage 2.

---

## Reference: Task Completion Checklist

| Task | Pathway | PCB Requirement |
|---|---|---|
| Training Certificate(s) | Education/Training | ≥ 24 total hours in CPD knowledge areas |
| HIPAA Training Certificate | Education/Training | ≥ 1 hour HIPAA/confidentiality |
| CPR Certification | Both | Current; adult + infant competencies |
| Client Evaluation #1 | Both | Signed by client |
| Client Evaluation #2 | Both | Signed by client |
| Client Evaluation #3 | Both | Signed by client; within last year (Experienced) |
| Proof of Active Practice | Experienced | Current evidence of active doula work |
| Letter of Recommendation #1 | Experienced | Signed by client; within last year |
| Letter of Recommendation #2 | Experienced | Signed by client; within last year |
| Letter of Recommendation #3 | Experienced | Signed by client; within last year |
