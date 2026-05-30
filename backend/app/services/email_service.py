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
) -> None:
    """Sends a combined welcome email with login credentials and the $99 deposit link."""
    if not _configured():
        raise RuntimeError("Email not configured — set RESEND_API_KEY")
    resend.api_key = settings.RESEND_API_KEY

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
            "subject": "Welcome to DoulaShield — Your Account & Deposit Link",
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; color: #1a1a1a; max-width: 480px; margin: 0 auto; padding: 24px;">
  <p style="font-size: 16px;">Hi {provider_name},</p>
  <p>Your DoulaShield provider account has been created. Here are your login details:</p>
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
