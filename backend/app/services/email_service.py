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
    <a href="https://promise.dpw.state.pa.us"
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
