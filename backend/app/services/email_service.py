import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple


def is_email_configured() -> bool:
    """Checks whether the SMTP email service is configured via environment variables."""
    host = os.getenv("SMTP_HOST", "").strip()
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASS", "").strip()
    return bool(host and user and password)


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> Tuple[bool, str]:
    """Send an email using SMTP.

    Returns:
        (True, "Success message") if sent successfully.
        (False, "Error message") if unconfigured or if delivery fails.
    """
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port_str = os.getenv("SMTP_PORT", "587").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    smtp_from = os.getenv("SMTP_FROM", "").strip() or smtp_user or "no-reply@aicodebase.local"
    smtp_use_ssl = os.getenv("SMTP_USE_SSL", "false").strip().lower() in ("true", "1", "yes")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in ("true", "1", "yes")

    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        smtp_port = 587

    if not smtp_host or not smtp_user or not smtp_pass:
        return (
            False,
            "Email delivery service is not configured. Please set SMTP_HOST, SMTP_PORT, "
            "SMTP_USER, and SMTP_PASS in the backend environment."
        )

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = to_email

        plain = text_content or html_content
        msg.attach(MIMEText(plain, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        if smtp_use_ssl or smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_from, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
                if smtp_use_tls:
                    server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_from, [to_email], msg.as_string())

        return True, "Email delivered successfully"

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed. Please verify SMTP_USER and SMTP_PASS (e.g. Gmail App Password)."
    except smtplib.SMTPConnectError:
        return False, f"Failed to connect to SMTP server at {smtp_host}:{smtp_port}."
    except smtplib.SMTPException as exc:
        return False, f"SMTP delivery error: {str(exc)}"
    except Exception as exc:
        return False, f"Email delivery failed ({type(exc).__name__}): {str(exc)}"


def send_verification_email(to_email: str, otp: str) -> Tuple[bool, str]:
    """Formats and sends the 6-digit email verification code."""
    subject = "Verify your email — AI Codebase Assistant"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #0f172a; margin: 0; padding: 24px; }}
        .card {{ max-width: 500px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
        .logo {{ font-size: 20px; font-weight: bold; color: #4f46e5; margin-bottom: 24px; }}
        .code-box {{ background: #eef2ff; border: 1px dashed #6366f1; border-radius: 12px; padding: 18px; text-align: center; margin: 24px 0; }}
        .code {{ font-family: monospace; font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #4338ca; }}
        .footer {{ font-size: 12px; color: #64748b; margin-top: 24px; border-top: 1px solid #f1f5f9; padding-top: 16px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="logo">AI Codebase Assistant</div>
        <h2 style="margin-top: 0; font-size: 20px;">Email Verification Code</h2>
        <p style="font-size: 14px; color: #475569; line-height: 1.5;">
          Please use the verification code below to confirm your email address. This code is valid for <strong>10 minutes</strong>.
        </p>
        <div class="code-box">
          <span class="code">{otp}</span>
        </div>
        <p style="font-size: 13px; color: #64748b;">
          If you did not request this verification code, please ignore this email.
        </p>
        <div class="footer">
          &copy; 2026 AI Codebase Assistant. All rights reserved.
        </div>
      </div>
    </body>
    </html>
    """

    text_content = (
        f"Your verification code for AI Codebase Assistant is: {otp}\n\n"
        f"This code will expire in 10 minutes.\n"
        f"If you did not request this code, you can safely ignore this email."
    )

    return send_email(to_email, subject, html_content, text_content)
