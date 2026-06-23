from __future__ import annotations

import asyncio

import resend

from app.core.config import settings


def _configured() -> bool:
    return bool(settings.RESEND_API_KEY)


async def send_welcome_and_deposit(
    provider_email: str,
    provider_name: str,
    temp_password: str,
    checkout_url: str | None,
    frontend_origin: str,
    role: str = "provider",
) -> None:
    """Sends a combined welcome email with login credentials and (for providers) the $99 deposit link."""
    if not _configured():
        raise RuntimeError("Email not configured — set RESEND_API_KEY")
    resend.api_key = settings.RESEND_API_KEY

    is_admin = role == "admin"
    subject = (
        "Welcome to DoulaShield — Your Account Details"
        if is_admin
        else "Welcome to DoulaShield — Your Account & Deposit Link"
    )
    account_label = "account" if is_admin else "provider account"

    deposit_section = ""
    if checkout_url:
        deposit_section = f"""
  <p style="margin-top:24px;">To complete your enrollment, please pay the <strong>$99 credentialing deposit</strong>:</p>
  <p style="margin: 20px 0;">
    <a href="{checkout_url}"
       style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;
              text-decoration:none;font-weight:600;font-size:15px;">
      Pay $99 Deposit &rarr;
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px;">This link expires in 24&nbsp;hours.</p>"""

    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": settings.EMAIL_FROM,
            "to": [provider_email],
            "subject": subject,
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; color: #1a1a1a; max-width: 480px; margin: 0 auto; padding: 24px;">
  <p style="font-size: 16px;">Hi {provider_name},</p>
  <p>Your DoulaShield {account_label} has been created. Here are your login details:</p>
  <table style="margin:16px 0;border-collapse:collapse;">
    <tr>
      <td style="padding:4px 12px 4px 0;font-size:13px;color:#6b7280;">Email</td>
      <td style="padding:4px 0;font-size:13px;font-weight:600;">{provider_email}</td>
    </tr>
    <tr>
      <td style="padding:4px 12px 4px 0;font-size:13px;color:#6b7280;">Password</td>
      <td style="padding:4px 0;font-size:13px;font-weight:600;font-family:monospace;">{temp_password}</td>
    </tr>
  </table>
  <p style="color:#6b7280;font-size:13px;">
    Please <a href="{frontend_origin}/login" style="color:#2563eb;">log in</a> and change your password
    from the Settings page.
  </p>
  {deposit_section}
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#9ca3af;font-size:12px;">The DoulaShield Team</p>
</body>
</html>
""",
        },
    )


async def send_walkthrough_email(provider_email: str, provider_name: str, frontend_origin: str) -> None:
    """Sent automatically when an admin enables demo mode for a provider."""
    if not _configured():
        raise RuntimeError("Email not configured — set RESEND_API_KEY")
    resend.api_key = settings.RESEND_API_KEY

    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": settings.EMAIL_FROM,
            "to": [provider_email],
            "subject": "Your DoulaShield Walkthrough Guide",
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; color: #1a1a1a; max-width: 600px; margin: 0 auto; padding: 24px;">
  <p style="font-size: 16px;">Hi {provider_name},</p>
  <p>Your DoulaShield account is in <strong>Demo Mode</strong>. You can practice the full billing
  workflow below — nothing will be sent to Availity while demo mode is on. When you're ready to go
  live, your admin will disable demo mode.</p>
  <p style="margin:0;"><a href="{frontend_origin}/login" style="color:#2563eb;">Log in to DoulaShield &rarr;</a></p>

  <h2 style="font-size:14px;font-weight:600;color:#374151;margin-top:28px;margin-bottom:8px;text-transform:uppercase;letter-spacing:.05em;">Workflow Steps</h2>
  <ol style="padding-left:20px;margin:0;line-height:1.9;font-size:14px;color:#374151;">
    <li><strong>Add a client</strong> — Clients &rarr; Add Client. Use any name from the table below.</li>
    <li><strong>Document a visit</strong> — Open the client &rarr; click a visit type (e.g. Prenatal 1) &rarr; Start Visit &rarr; End Visit &rarr; fill in SOAP notes.</li>
    <li><strong>Collect MA&nbsp;91 signature</strong> — Click &ldquo;Collect MA&nbsp;91 Signature&rdquo; and sign on-screen, or test ZipZign by sending to your own email.</li>
    <li><strong>Submit claim</strong> — Click &ldquo;Submit Claim.&rdquo; <strong>Demo Mode is on</strong>&mdash;the submission is simulated. No real claim goes to Availity. Status shows as Processing.</li>
    <li><strong>Explore Reports &amp; Audit Packet</strong> — Go to Reports to see the claim. Open the visit and click &ldquo;Download Audit Packet&rdquo; to see the full 7-section PDF.</li>
    <li><strong>Log payment (EOB)</strong> — When payment arrives, go to Reports &rarr; Scan Remittance / EOB &rarr; upload the payment document to mark the claim as paid.</li>
  </ol>

  <h2 style="font-size:14px;font-weight:600;color:#374151;margin-top:28px;margin-bottom:8px;text-transform:uppercase;letter-spacing:.05em;">Sample SOAP Notes (Prenatal 1)</h2>
  <table style="font-size:13px;border-collapse:collapse;width:100%;">
    <tr><td style="padding:3px 12px 3px 0;color:#6b7280;white-space:nowrap;vertical-align:top;">Subjective</td><td style="padding:3px 0;color:#111827;">First doula visit at 12 weeks. Morning sickness improving. Client interested in natural birth and breastfeeding support.</td></tr>
    <tr><td style="padding:3px 12px 3px 0;color:#6b7280;vertical-align:top;">Objective</td><td style="padding:3px 0;color:#111827;">BP 118/72. Client alert and engaged. Reviewed birth preferences and prenatal nutrition.</td></tr>
    <tr><td style="padding:3px 12px 3px 0;color:#6b7280;vertical-align:top;">Assessment</td><td style="padding:3px 0;color:#111827;">Low-risk pregnancy at 12 weeks progressing normally.</td></tr>
    <tr><td style="padding:3px 12px 3px 0;color:#6b7280;vertical-align:top;">Plan</td><td style="padding:3px 0;color:#111827;">Provide birth education materials. Schedule Prenatal 2 at 20 weeks. Follow up on iron levels.</td></tr>
  </table>

  <h2 style="font-size:14px;font-weight:600;color:#374151;margin-top:28px;margin-bottom:8px;text-transform:uppercase;letter-spacing:.05em;">10 Sample Patients</h2>
  <p style="font-size:12px;color:#6b7280;margin:0 0 8px;">Use any of these when adding clients. Referring NPI 9999999999 is a placeholder.</p>
  <table style="font-size:12px;border-collapse:collapse;width:100%;">
    <thead>
      <tr style="background:#f9fafb;">
        <th style="padding:6px 8px;text-align:left;border-bottom:1px solid #e5e7eb;color:#6b7280;">#</th>
        <th style="padding:6px 8px;text-align:left;border-bottom:1px solid #e5e7eb;color:#6b7280;">Name</th>
        <th style="padding:6px 8px;text-align:left;border-bottom:1px solid #e5e7eb;color:#6b7280;">Medicaid ID</th>
        <th style="padding:6px 8px;text-align:left;border-bottom:1px solid #e5e7eb;color:#6b7280;">MCO</th>
        <th style="padding:6px 8px;text-align:left;border-bottom:1px solid #e5e7eb;color:#6b7280;">DOB</th>
      </tr>
    </thead>
    <tbody>
      <tr><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">1</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">Jane Sample</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;font-family:monospace;">1234567890</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">AmeriHealth Caritas</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">01/15/1992</td></tr>
      <tr style="background:#f9fafb;"><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">2</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">Maria Rodriguez</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;font-family:monospace;">2345678901</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">UPMC For You</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">11/22/1988</td></tr>
      <tr><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">3</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">Ashley Williams</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;font-family:monospace;">3456789012</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">Keystone First</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">07/08/1995</td></tr>
      <tr style="background:#f9fafb;"><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">4</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">Sarah Johnson</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;font-family:monospace;">4567890123</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">Geisinger Health Plan</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">03/30/1990</td></tr>
      <tr><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">5</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">Emily Davis</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;font-family:monospace;">5678901234</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">Aetna Better Health</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">09/12/1993</td></tr>
      <tr style="background:#f9fafb;"><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">6</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">Destiny Brown</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;font-family:monospace;">6789012345</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">Health Partners Plans</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">05/05/1997</td></tr>
      <tr><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">7</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">Tamara Wilson</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;font-family:monospace;">7890123456</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">Highmark Wholecare</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">12/28/1991</td></tr>
      <tr style="background:#f9fafb;"><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">8</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">Keisha Moore</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;font-family:monospace;">8901234567</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">UnitedHealthcare Community Plan</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">02/14/1986</td></tr>
      <tr><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">9</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">Brianna Taylor</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;font-family:monospace;">9012345678</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">FFS</td><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6;">08/22/1994</td></tr>
      <tr style="background:#f9fafb;"><td style="padding:5px 8px;">10</td><td style="padding:5px 8px;">Jasmine Anderson</td><td style="padding:5px 8px;font-family:monospace;">0123456789</td><td style="padding:5px 8px;">AmeriHealth Caritas</td><td style="padding:5px 8px;">06/11/1989</td></tr>
    </tbody>
  </table>
  <p style="font-size:12px;color:#6b7280;margin-top:8px;">All addresses: use any Philadelphia-area address. Referring NPI: 9999999999.</p>

  <hr style="border:none;border-top:1px solid #e5e7eb;margin:28px 0;">
  <p style="color:#9ca3af;font-size:12px;">The DoulaShield Team</p>
</body>
</html>
""",
        },
    )


async def send_password_reset_email(email: str, name: str, reset_url: str) -> None:
    if not _configured():
        raise RuntimeError("Email not configured — set RESEND_API_KEY")
    resend.api_key = settings.RESEND_API_KEY
    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": settings.EMAIL_FROM,
            "to": [email],
            "subject": "Reset your DoulaShield password",
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; color: #1a1a1a; max-width: 480px; margin: 0 auto; padding: 24px;">
  <p style="font-size: 16px;">Hi {name},</p>
  <p>We received a request to reset your DoulaShield password. Click the button below to set a new one.
  This link expires in <strong>1 hour</strong>.</p>
  <p style="margin: 28px 0;">
    <a href="{reset_url}"
       style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;
              text-decoration:none;font-weight:600;font-size:15px;">
      Reset Password &rarr;
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px;">
    If you didn&rsquo;t request this, you can safely ignore this email &mdash; your password won&rsquo;t change.
  </p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#9ca3af;font-size:12px;">The DoulaShield Team</p>
</body>
</html>
""",
        },
    )


async def send_caqh_reminder_email(
    provider_email: str,
    provider_name: str,
    days_remaining: int,
) -> None:
    """Sends a CAQH re-attestation reminder. days_remaining <= 0 means overdue."""
    if not _configured():
        return
    resend.api_key = settings.RESEND_API_KEY

    abs_days = abs(days_remaining)
    day_word = "day" if abs_days == 1 else "days"

    if days_remaining <= 0:
        subject = "CAQH attestation overdue — action required"
        urgency_text = (
            f"Your CAQH ProView attestation expired <strong>{abs_days} {day_word} ago</strong>. "
            "MCOs may begin removing you from their provider directories, which will block claim reimbursement."
        )
        cta_color = "#dc2626"
    else:
        subject = f"CAQH attestation due in {days_remaining} {day_word}"
        urgency_text = (
            f"Your CAQH ProView attestation expires in <strong>{days_remaining} {day_word}</strong>. "
            "Re-attesting on time keeps you enrolled in MCO directories and ensures uninterrupted billing."
        )
        cta_color = "#d97706" if days_remaining <= 7 else "#2563eb"

    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": settings.EMAIL_FROM,
            "to": [provider_email],
            "subject": subject,
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; color: #1a1a1a; max-width: 480px; margin: 0 auto; padding: 24px;">
  <p style="font-size: 16px;">Hi {provider_name},</p>
  <p>{urgency_text}</p>
  <p style="margin: 28px 0; display: flex; gap: 12px; flex-wrap: wrap;">
    <a href="https://proview.caqh.org"
       style="background:{cta_color};color:#fff;padding:12px 24px;border-radius:6px;
              text-decoration:none;font-weight:600;font-size:15px;display:inline-block;">
      Re-attest on CAQH ProView &rarr;
    </a>
    <a href="{settings.FRONTEND_ORIGIN}/settings"
       style="background:#f3f4f6;color:#374151;padding:12px 24px;border-radius:6px;
              text-decoration:none;font-weight:600;font-size:15px;display:inline-block;border:1px solid #d1d5db;">
      Update in DoulaShield
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px;">
    After re-attesting on CAQH ProView, update your "Last attested on" date in DoulaShield Settings
    so your 90-day clock resets.
  </p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#9ca3af;font-size:12px;">The DoulaShield Team</p>
</body>
</html>
""",
        },
    )


async def send_promise_reminder_email(
    provider_email: str,
    provider_name: str,
    days_remaining: int,
) -> None:
    """Sends a PROMISe™ re-enrollment reminder. days_remaining <= 0 means overdue."""
    if not _configured():
        return
    resend.api_key = settings.RESEND_API_KEY

    abs_days = abs(days_remaining)
    day_word = "day" if abs_days == 1 else "days"

    if days_remaining <= 0:
        subject = "PROMISe™ re-enrollment overdue — action required"
        urgency_text = (
            f"Your PA DHS PROMISe™ provider enrollment expired <strong>{abs_days} {day_word} ago</strong>. "
            "You may lose FFS billing privileges until re-enrollment is completed."
        )
        cta_color = "#dc2626"
    else:
        subject = f"PROMISe™ re-enrollment due in {days_remaining} {day_word}"
        urgency_text = (
            f"Your PA DHS PROMISe™ provider enrollment expires in <strong>{days_remaining} {day_word}</strong>. "
            "Re-enrolling on time preserves your FFS billing privileges and avoids a lapse in reimbursement."
        )
        cta_color = "#d97706" if days_remaining <= 30 else "#2563eb"

    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": settings.EMAIL_FROM,
            "to": [provider_email],
            "subject": subject,
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; color: #1a1a1a; max-width: 480px; margin: 0 auto; padding: 24px;">
  <p style="font-size: 16px;">Hi {provider_name},</p>
  <p>{urgency_text}</p>
  <p style="margin: 28px 0; display: flex; gap: 12px; flex-wrap: wrap;">
    <a href="https://promise.dhs.pa.gov"
       style="background:{cta_color};color:#fff;padding:12px 24px;border-radius:6px;
              text-decoration:none;font-weight:600;font-size:15px;display:inline-block;">
      Re-enroll on PROMISe&trade; &rarr;
    </a>
    <a href="{settings.FRONTEND_ORIGIN}/settings"
       style="background:#f3f4f6;color:#374151;padding:12px 24px;border-radius:6px;
              text-decoration:none;font-weight:600;font-size:15px;display:inline-block;border:1px solid #d1d5db;">
      Update in DoulaShield
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px;">
    After completing re-enrollment on PROMISe&trade;, update your "Last enrolled on" date in
    DoulaShield Settings so your 5-year clock resets.
  </p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#9ca3af;font-size:12px;">The DoulaShield Team</p>
</body>
</html>
""",
        },
    )


async def send_pcb_reminder_email(
    provider_email: str,
    provider_name: str,
    days_remaining: int,
) -> None:
    """Sends a PCB Perinatal Certification renewal reminder. days_remaining <= 0 means overdue."""
    if not _configured():
        return
    resend.api_key = settings.RESEND_API_KEY

    abs_days = abs(days_remaining)
    day_word = "day" if abs_days == 1 else "days"

    if days_remaining <= 0:
        subject = "PCB Perinatal Certification expired — renewal required"
        urgency_text = (
            f"Your PA Certification Board (PCB) Perinatal Certification expired "
            f"<strong>{abs_days} {day_word} ago</strong>. "
            "Renew immediately to maintain your certified doula credentials."
        )
        cta_color = "#dc2626"
    else:
        subject = f"PCB Perinatal Certification renewal due in {days_remaining} {day_word}"
        urgency_text = (
            f"Your PA Certification Board (PCB) Perinatal Certification expires in "
            f"<strong>{days_remaining} {day_word}</strong>. "
            "Renewing on time ensures your certification remains current."
        )
        cta_color = "#d97706" if days_remaining <= 14 else "#2563eb"

    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": settings.EMAIL_FROM,
            "to": [provider_email],
            "subject": subject,
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; color: #1a1a1a; max-width: 480px; margin: 0 auto; padding: 24px;">
  <p style="font-size: 16px;">Hi {provider_name},</p>
  <p>{urgency_text}</p>
  <p style="margin: 28px 0; display: flex; gap: 12px; flex-wrap: wrap;">
    <a href="https://www.pacertboard.org"
       style="background:{cta_color};color:#fff;padding:12px 24px;border-radius:6px;
              text-decoration:none;font-weight:600;font-size:15px;display:inline-block;">
      Renew on PA Cert Board &rarr;
    </a>
    <a href="{settings.FRONTEND_ORIGIN}/settings"
       style="background:#f3f4f6;color:#374151;padding:12px 24px;border-radius:6px;
              text-decoration:none;font-weight:600;font-size:15px;display:inline-block;border:1px solid #d1d5db;">
      Update in DoulaShield
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px;">
    After renewing, update your "Last certified on" date in DoulaShield Settings so your 2-year clock resets.
  </p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#9ca3af;font-size:12px;">The DoulaShield Team</p>
</body>
</html>
""",
        },
    )


async def send_liability_reminder_email(
    provider_email: str,
    provider_name: str,
    days_remaining: int,
) -> None:
    """Sends a liability insurance expiry reminder. days_remaining <= 0 means expired."""
    if not _configured():
        return
    resend.api_key = settings.RESEND_API_KEY

    abs_days = abs(days_remaining)
    day_word = "day" if abs_days == 1 else "days"

    if days_remaining <= 0:
        subject = "Liability insurance expired — renew immediately"
        urgency_text = (
            f"Your professional liability insurance expired <strong>{abs_days} {day_word} ago</strong>. "
            "You may not be covered for client visits until you renew your policy."
        )
        cta_color = "#dc2626"
    else:
        subject = f"Liability insurance expires in {days_remaining} {day_word}"
        urgency_text = (
            f"Your professional liability insurance expires in <strong>{days_remaining} {day_word}</strong>. "
            "Renew your policy before the expiration date to maintain continuous coverage for client visits."
        )
        cta_color = "#d97706" if days_remaining <= 7 else "#2563eb"

    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": settings.EMAIL_FROM,
            "to": [provider_email],
            "subject": subject,
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; color: #1a1a1a; max-width: 480px; margin: 0 auto; padding: 24px;">
  <p style="font-size: 16px;">Hi {provider_name},</p>
  <p>{urgency_text}</p>
  <p style="margin: 28px 0;">
    <a href="{settings.FRONTEND_ORIGIN}/settings"
       style="background:{cta_color};color:#fff;padding:12px 24px;border-radius:6px;
              text-decoration:none;font-weight:600;font-size:15px;display:inline-block;">
      Update Expiry Date in DoulaShield &rarr;
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px;">
    After renewing your policy, update the expiration date in DoulaShield Settings and upload your
    new Declarations Page for your records.
  </p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#9ca3af;font-size:12px;">The DoulaShield Team</p>
</body>
</html>
""",
        },
    )


async def send_ma589_reminder_email(
    provider_email: str,
    provider_name: str,
    patient_name: str,
) -> None:
    """Notifies a provider that a patient is missing a signed MA 589 form."""
    if not _configured():
        return
    resend.api_key = settings.RESEND_API_KEY

    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": settings.EMAIL_FROM,
            "to": [provider_email],
            "subject": f"MA 589 required for {patient_name}",
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; color: #1a1a1a; max-width: 480px; margin: 0 auto; padding: 24px;">
  <p style="font-size: 16px;">Hi {provider_name},</p>
  <p>A prenatal visit has been documented for <strong>{patient_name}</strong>, but no signed
  <strong>MA 589 Medical Assistance Physician Certification</strong> has been recorded for this patient.</p>
  <p>Pennsylvania Medicaid requires a completed MA 589 before doula services can be billed. Please
  obtain and scan the signed form as soon as possible to avoid claim denial.</p>
  <p style="margin: 28px 0;">
    <a href="{settings.FRONTEND_ORIGIN}/clients"
       style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;
              text-decoration:none;font-weight:600;font-size:15px;display:inline-block;">
      View Client in DoulaShield &rarr;
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px;">
    Once you have the signed form, open the Prenatal 1 visit and scan the MA 589 to record the date.
  </p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#9ca3af;font-size:12px;">The DoulaShield Team</p>
</body>
</html>
""",
        },
    )


async def send_claim_deadline_email(
    provider_email: str,
    provider_name: str,
    patient_initials: str,
    visit_type: str,
    service_date: str,
    days_remaining: int,
    deadline_type: str,
) -> None:
    """Sends a PA Medicaid claim filing deadline reminder.
    deadline_type: 'initial' (180-day), 'corrected' (365-day), or 'secondary' (60-day from EOB).
    days_remaining <= 0 means the deadline has passed.
    """
    if not _configured():
        return
    resend.api_key = settings.RESEND_API_KEY

    abs_days = abs(days_remaining)
    day_word = "day" if abs_days == 1 else "days"

    if deadline_type == "secondary":
        deadline_days = 60
        deadline_label = "secondary claim (60 days from EOB)"
    elif deadline_type == "corrected":
        deadline_days = 365
        deadline_label = "corrected claim (365-day limit)"
    else:
        deadline_days = 180
        deadline_label = "initial claim (180-day PA Medicaid limit)"

    is_best_practice_nudge = deadline_type == "initial" and days_remaining == 150

    if days_remaining <= 0:
        if deadline_type == "secondary":
            subject = f"Secondary claim filing deadline passed — {abs_days} {day_word} overdue"
        elif deadline_type == "corrected":
            subject = f"Corrected claim filing deadline passed — {abs_days} {day_word} overdue"
        else:
            subject = f"PA Medicaid claim filing deadline passed — {abs_days} {day_word} overdue"
        urgency_text = (
            f"The {deadline_label} for visit <strong>{visit_type}</strong> (patient {patient_initials}, "
            f"service date {service_date}) passed <strong>{abs_days} {day_word} ago</strong>. "
            "This claim may no longer be reimbursable. Contact PA Medicaid immediately if you believe "
            "an exception applies."
        )
        cta_color = "#dc2626"
    elif is_best_practice_nudge:
        subject = "Reminder: PA Medicaid recommends filing claims within 30 days of service"
        urgency_text = (
            f"It has been 30 days since the service date ({service_date}) for visit "
            f"<strong>{visit_type}</strong> (patient {patient_initials}). "
            "PA Medicaid recommends filing within 30 days, though the hard deadline is "
            f"<strong>{deadline_days} days</strong> from service date. File now to avoid delays."
        )
        cta_color = "#2563eb"
    else:
        if deadline_type == "secondary":
            subject = f"Secondary claim due in {days_remaining} {day_word} — 60-day EOB window"
        elif deadline_type == "corrected":
            subject = f"Corrected claim due in {days_remaining} {day_word} — file before deadline"
        else:
            subject = f"PA Medicaid claim due in {days_remaining} {day_word} — file to avoid forfeiture"
        urgency_text = (
            f"The {deadline_label} for visit <strong>{visit_type}</strong> (patient {patient_initials}, "
            f"service date {service_date}) expires in <strong>{days_remaining} {day_word}</strong>. "
            "File this claim now to ensure reimbursement."
        )
        cta_color = "#dc2626" if days_remaining <= 7 else ("#d97706" if days_remaining <= 30 else "#2563eb")

    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": settings.EMAIL_FROM,
            "to": [provider_email],
            "subject": subject,
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; color: #1a1a1a; max-width: 480px; margin: 0 auto; padding: 24px;">
  <p style="font-size: 16px;">Hi {provider_name},</p>
  <p>{urgency_text}</p>
  <p style="margin: 28px 0;">
    <a href="{settings.FRONTEND_ORIGIN}/clients"
       style="background:{cta_color};color:#fff;padding:12px 24px;border-radius:6px;
              text-decoration:none;font-weight:600;font-size:15px;display:inline-block;">
      View Claims in DoulaShield &rarr;
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px;">
    Open the client&rsquo;s visit page in DoulaShield to submit or resubmit the claim. For manual MCOs
    (UPMC, HPP, FFS), download the CMS 1500 and submit through the payer&rsquo;s portal.
  </p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#9ca3af;font-size:12px;">The DoulaShield Team</p>
</body>
</html>
""",
        },
    )


async def send_filing_deadline_reminder_email(
    provider_email: str,
    provider_name: str,
    patient_name: str,
    days_remaining: int,
    service_date: str,
    claim_url: str,
) -> None:
    """Sends a timely-filing deadline reminder. days_remaining <= 0 means overdue."""
    if not _configured():
        return
    resend.api_key = settings.RESEND_API_KEY

    abs_days = abs(days_remaining)
    day_word = "day" if abs_days == 1 else "days"

    if days_remaining <= 0:
        subject = "Claim filing deadline overdue — action required"
        urgency_text = (
            f"The timely-filing deadline for <strong>{patient_name}</strong> "
            f"(service date {service_date}) passed <strong>{abs_days} {day_word} ago</strong>. "
            "This claim may no longer be reimbursable."
        )
        cta_color = "#dc2626"
    else:
        subject = f"Claim filing deadline in {days_remaining} {day_word}"
        urgency_text = (
            f"The timely-filing deadline for <strong>{patient_name}</strong> "
            f"(service date {service_date}) is in <strong>{days_remaining} {day_word}</strong>. "
            "Submit or resubmit the claim before the deadline to ensure reimbursement."
        )
        cta_color = "#d97706" if days_remaining <= 7 else "#2563eb"

    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": settings.EMAIL_FROM,
            "to": [provider_email],
            "subject": subject,
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; color: #1a1a1a; max-width: 480px; margin: 0 auto; padding: 24px;">
  <p style="font-size: 16px;">Hi {provider_name},</p>
  <p>{urgency_text}</p>
  <p style="margin: 28px 0;">
    <a href="{claim_url}"
       style="background:{cta_color};color:#fff;padding:12px 24px;border-radius:6px;
              text-decoration:none;font-weight:600;font-size:15px;display:inline-block;">
      View Claim &rarr;
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px;">
    PA Medicaid MCOs typically enforce a 365-day timely-filing window from the date of service.
    Contact your MCO if you need to request a filing deadline exception.
  </p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#9ca3af;font-size:12px;">The DoulaShield Team</p>
</body>
</html>
""",
        },
    )


async def send_agency_onboarding_email(
    admin_email: str,
    admin_name: str,
    agency_name: str,
    agency_group_npi: str,
    frontend_origin: str,
) -> None:
    """Email sent to the billing admin when their agency is first created in DoulaShield."""
    if not _configured():
        return
    resend.api_key = settings.RESEND_API_KEY
    subject = f"Your DoulaShield billing agency is ready — {agency_name}"
    npi_display = agency_group_npi if agency_group_npi else "Not yet set"
    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": settings.EMAIL_FROM,
            "to": [admin_email],
            "subject": subject,
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; color: #1a1a1a; max-width: 480px; margin: 0 auto; padding: 24px;">
  <p style="font-size: 16px;">Hi {admin_name},</p>
  <p>Your DoulaShield billing agency has been set up and is ready to use.</p>
  <table style="margin:16px 0;border-collapse:collapse;width:100%;">
    <tr>
      <td style="padding:6px 12px 6px 0;font-size:13px;color:#6b7280;white-space:nowrap;">Agency Name</td>
      <td style="padding:6px 0;font-size:13px;font-weight:600;">{agency_name}</td>
    </tr>
    <tr>
      <td style="padding:6px 12px 6px 0;font-size:13px;color:#6b7280;white-space:nowrap;">Group NPI</td>
      <td style="padding:6px 0;font-size:13px;font-weight:600;">{npi_display}</td>
    </tr>
  </table>
  <p style="margin-top:20px;">Get started:</p>
  <ul style="margin:8px 0;padding-left:20px;font-size:14px;line-height:1.8;">
    <li>
      <a href="{frontend_origin}/billing-admin/claims" style="color:#2563eb;">View claim queue</a>
      &mdash; review and submit queued claims from your providers
    </li>
    <li>
      <a href="{frontend_origin}/billing-admin/settings" style="color:#2563eb;">Agency Settings</a>
      &mdash; add your Availity credentials to enable agency claim submission
    </li>
  </ul>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#9ca3af;font-size:12px;">The DoulaShield Team</p>
</body>
</html>
""",
        },
    )


async def send_deposit_link(provider_email: str, provider_name: str, checkout_url: str) -> None:
    if not _configured():
        raise RuntimeError("Email not configured — set RESEND_API_KEY")
    resend.api_key = settings.RESEND_API_KEY
    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": settings.EMAIL_FROM,
            "to": [provider_email],
            "subject": "Complete Your DoulaShield Enrollment — $99 Deposit Required",
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; color: #1a1a1a; max-width: 480px; margin: 0 auto; padding: 24px;">
  <p style="font-size: 16px;">Hi {provider_name},</p>
  <p>To complete your DoulaShield enrollment, please pay the <strong>$99 non-refundable
  credentialing deposit</strong> using the secure link below.</p>
  <p style="margin: 28px 0;">
    <a href="{checkout_url}"
       style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;
              text-decoration:none;font-weight:600;font-size:15px;">
      Pay $99 Deposit &rarr;
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px;">
    This link expires in 24&nbsp;hours. Once payment is received your account will be
    fully activated and you can begin using DoulaShield.
  </p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#9ca3af;font-size:12px;">The DoulaShield Team</p>
</body>
</html>
""",
        },
    )
