from __future__ import annotations

import asyncio

import resend

from app.core.config import settings


def _configured() -> bool:
    return bool(settings.RESEND_API_KEY)


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
