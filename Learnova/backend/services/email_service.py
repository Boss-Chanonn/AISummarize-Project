"""
email_service.py  —  Transactional email service via Gmail SMTP
================================================================
Sends four types of emails to Learnova users:
  1. Welcome email          — sent on registration
  2. Pro welcome email      — sent on plan upgrade
  3. Summary report email   — sent after document summarisation
  4. Weekly report email    — sent every Monday via scheduler

All email HTML is built inline (no template engine) and sent through
Gmail's SMTP server (smtp.gmail.com:587) with STARTTLS.

Cross-references:
  - Called by backend/routers/ (auth_router.py, document_router.py)
  - Weekly reports triggered by a scheduler in app.py
  - gather_user_stats queries MongoDB history collection
"""
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
import asyncio


# ── SMTP Configuration ────────────────────────────────────────────────────────

EMAIL_FROM = os.getenv("EMAIL_FROM", "learnovaaiproject@gmail.com")
EMAIL_FROM_NAME = "Learnova"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER", EMAIL_FROM)
SMTP_PASS = os.getenv("SMTP_PASS", "")


# ── Core send function ────────────────────────────────────────────────────────

async def _send_email(to_email: str, subject: str, html: str) -> bool:
    """Send an email via Gmail SMTP.

    Runs the SMTP call in a thread executor to avoid blocking the async event loop.
    Skips sending if SMTP_PASS is not configured (safe for development).

    Args:
        to_email: Recipient email address.
        subject:  Email subject line.
        html:     HTML body content.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    if not SMTP_PASS:
        print("[email] SMTP_PASS not set — skipping email")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html, "html"))
        import asyncio
        loop = asyncio.get_running_loop()

        def _send():
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(EMAIL_FROM, [to_email], msg.as_string())

        await loop.run_in_executor(None, _send)
        print(f"[email] ✅ Sent to {to_email}")
        return True
    except Exception as e:
        print(f"[email] ❌ Failed to send to {to_email}: {e}")
        return False


# ── Weekly Report ──────────────────────────────────────────────────────────────

async def send_weekly_report(user_email: str, user_name: str, stats: dict) -> bool:
    """Send a weekly progress email to a single user.

    Args:
        user_email: Recipient's email address.
        user_name:  Recipient's display name.
        stats:      Dict from gather_user_stats() containing activity data.

    Returns:
        True if the email was sent successfully.
    """
    html = _build_email_html(user_name, stats)
    subject = f"Your Learnova weekly report — {datetime.now().strftime('%d %b %Y')}"
    return await _send_email(user_email, subject, html)


async def gather_user_stats(user_id: str, db_history) -> dict:
    """Pull the last 7 days of activity from MongoDB for a given user.

    Aggregates total documents, completed quizzes, average score,
    weak topics, strong topics, and document titles.

    Args:
        user_id:     MongoDB ObjectId string for the user.
        db_history:  Async MongoDB collection for document/quiz history.

    Returns:
        Dict with keys: total_docs, quizzes_completed, avg_score,
                        weak_topics, strong_topics, doc_titles.
    """
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    cursor = db_history.find({
        "userId": user_id,
        "uploadedAt": {"$gte": week_ago}
    })
    docs = await cursor.to_list(length=100)

    total_docs = len(docs)
    completed = [d for d in docs if d.get("done")]
    scores = [d["score"] for d in completed if d.get("score") is not None]
    avg_score = round(sum(scores) / len(scores)) if scores else None

    # Collect weak topics across all sessions
    weak = []
    for d in completed:
        analysis = d.get("analysis", {})
        weak.extend(analysis.get("weaknesses", []))
    weak_topics = list(dict.fromkeys(weak))[:3]  # deduplicated, top 3

    # Collect strong topics
    strong = []
    for d in completed:
        analysis = d.get("analysis", {})
        strong.extend(analysis.get("strengths", []))
    strong_topics = list(dict.fromkeys(strong))[:3]

    return {
        "total_docs": total_docs,
        "quizzes_completed": len(completed),
        "avg_score": avg_score,
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
        "doc_titles": [d.get("title", "Untitled") for d in docs[:5]],
    }


async def send_weekly_reports_to_all(users_col, history_col) -> None:
    """Called by the scheduler every Monday. Sends reports to all active users.

    Iterates all active users, gathers their weekly stats, and sends a
    personalised weekly report email. Skips users with zero activity.
    Records the run date in system_settings to prevent duplicate sends on restart.

    Args:
        users_col:   Async MongoDB collection for user accounts.
        history_col: Async MongoDB collection for document/quiz history.
    """
    print("[email] Starting weekly report run…")
    cursor = users_col.find({"isActive": {"$ne": False}})
    users = await cursor.to_list(length=10000)
    sent = 0
    for user in users:
        email = user.get("email", "")
        name = user.get("name", user.get("username", "Learner"))
        uid = str(user.get("_id", ""))
        if not email:
            continue
        stats = await gather_user_stats(uid, history_col)
        if stats["total_docs"] == 0:
            continue  # don't email inactive users
        ok = await send_weekly_report(email, name, stats)
        if ok:
            sent += 1
    print(f"[email] Weekly run complete — {sent}/{len(users)} emails sent")
    # Record today's run so catch-up doesn't re-trigger on restart
    try:
        from zoneinfo import ZoneInfo
        _nz_now = datetime.now(ZoneInfo("Pacific/Auckland")).strftime("%Y-%m-%d")
        _result = await users_col.database["system_settings"].update_one(
            {"_id": "weekly_email_last_run"},
            {"$set": {"date": _nz_now}},
            upsert=True,
        )
        if _result.acknowledged:
            print(f"[email] Last-run date saved: {_nz_now}")
        else:
            print(f"[email] Last-run save not acknowledged")
    except Exception as _se:
        print(f"[email] Could not save last-run date: {_se}")
        import sys; sys.stdout.flush()


# ── Summary Report ──────────────────────────────────────────────────────────────

async def send_summary_report(user_email: str, user_name: str, doc_title: str, summary: dict) -> bool:
    """Send an email containing the AI-generated document summary.

    Args:
        user_email: Recipient's email address.
        user_name:  Recipient's display name.
        doc_title:  Title of the summarised document.
        summary:    Dict with keys: body (list of paragraphs), takeaways (list).

    Returns:
        True if the email was sent successfully.
    """
    html = _build_summary_email_html(user_name, doc_title, summary)
    subject = f"Your Learnova summary — {doc_title[:60]}"
    return await _send_email(user_email, subject, html)


# ── HTML Builders ──────────────────────────────────────────────────────────────

def _build_summary_email_html(name: str, doc_title: str, summary: dict) -> str:
    """Build the HTML for a summary report email.

    Inlines all CSS for maximum email client compatibility.
    Uses the Learnova brand palette (dark bg, gold accents).

    Args:
        name:     Recipient's display name.
        doc_title: Title of the summarised document.
        summary:  Dict with "body" (list of paragraphs) and "takeaways" (list).

    Returns:
        Complete HTML string ready for sending.
    """
    body_paragraphs = summary.get("body", [])
    takeaways = summary.get("takeaways", [])
    body_html = "".join(f"<p>{p}</p>" for p in body_paragraphs)
    takeaways_html = "".join(
        f'<tr><td style="padding:6px 0;font-size:14px;color:#1C1917;border-bottom:1px solid #E5E0D8">— {t}</td></tr>'
        for t in takeaways
    )

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: Georgia, serif; background: #F7F5F2; margin: 0; padding: 0; color: #1C1917; }}
  .wrap {{ max-width: 580px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; }}
  .header {{ background: #1C1917; padding: 36px 40px; }}
  .header h1 {{ color: #C8B89A; font-size: 28px; margin: 0 0 4px; }}
  .header p {{ color: rgba(240,237,232,0.5); margin: 0; font-size: 14px; }}
  .body {{ padding: 36px 40px; }}
  .greeting {{ font-size: 20px; margin-bottom: 24px; }}
  .doc-title {{ font-size: 18px; font-weight: bold; color: #6E512B; margin-bottom: 20px; }}
  .body p {{ font-size: 14px; line-height: 1.7; color: #1C1917; margin-bottom: 14px; }}
  .takes-section {{ margin-top: 28px; }}
  .takes-label {{ font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #6B7280; margin-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  .cta {{ display: block; background: #1C1917; color: #C8B89A !important; text-decoration: none;
          text-align: center; padding: 14px; border-radius: 8px; font-size: 15px; margin-top: 32px; }}
  .footer {{ padding: 20px 40px; font-size: 12px; color: #9CA3AF; text-align: center; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>Learnova ✦</h1>
    <p>Document summary report</p>
  </div>
  <div class="body">
    <div class="greeting">Hi {name},</div>
    <p style="font-size:14px;color:#6B7280;margin-bottom:20px">
      Here is your AI-generated summary of <strong>{doc_title}</strong>.
    </p>
    <div class="doc-title">{doc_title}</div>
    {body_html}
    <div class="takes-section">
      <div class="takes-label">Key Takeaways</div>
      <table><tbody>{takeaways_html}</tbody></table>
    </div>
    <a href="http://localhost:8000/upload.html" class="cta">View full summary →</a>
  </div>
  <div class="footer">
    You're receiving this because you uploaded a document to Learnova.<br>
    Learnova · AI-Powered Learning Platform
  </div>
</div>
</body>
</html>"""


# ── Welcome Emails ────────────────────────────────────────────────────────────

async def send_welcome_email(user_email: str, user_name: str) -> bool:
    """Send a welcome email to a newly registered user.

    Args:
        user_email: Recipient's email address.
        user_name:  Recipient's display name.

    Returns:
        True if the email was sent successfully.
    """
    html = _build_welcome_email_html(user_name)
    subject = f"Welcome to Learnova, {user_name}! 🎉"
    return await _send_email(user_email, subject, html)


async def send_pro_welcome_email(user_email: str, user_name: str, plan_type: str) -> bool:
    """Send a welcome email when a user upgrades to a Pro plan.

    Args:
        user_email: Recipient's email address.
        user_name:  Recipient's display name.
        plan_type:  One of "monthly" or "yearly".

    Returns:
        True if the email was sent successfully.
    """
    html = _build_pro_welcome_email_html(user_name, plan_type)
    subject = f"You're now a Learnova Pro, {user_name}! 🚀"
    return await _send_email(user_email, subject, html)


async def send_verification_email(user_email: str, user_name: str, code: str) -> bool:
    """Send a 6-digit verification code to a newly registered user.

    Args:
        user_email: Recipient's email address.
        user_name:  Recipient's display name.
        code:       6-digit verification code.

    Returns:
        True if the email was sent successfully.
    """
    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: Georgia, serif; background: #F7F5F2; margin: 0; padding: 0; color: #1C1917; }}
  .wrap {{ max-width: 580px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; }}
  .header {{ background: linear-gradient(135deg,#1C1917,#2D2A27); padding: 40px; text-align: center; }}
  .header h1 {{ color: #C8B89A; font-size: 28px; margin: 0; }}
  .body {{ padding: 36px 40px; }}
  .greeting {{ font-size: 20px; margin-bottom: 16px; }}
  p {{ font-size: 14px; color: #6B7280; line-height: 1.7; }}
  .code {{ text-align: center; font-size: 36px; font-weight: bold; color: #C8B89A; letter-spacing: 8px;
           margin: 24px 0; padding: 20px; background: #F7F5F2; border-radius: 8px; }}
  .footer {{ padding: 20px 40px; font-size: 12px; color: #9CA3AF; text-align: center; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header"><h1>Learnova ✦</h1></div>
  <div class="body">
    <div class="greeting">Welcome to Learnova, {user_name}!</div>
    <p>Thanks for creating an account. Use the code below to verify your email address and get started.</p>
    <div class="code">{code}</div>
    <p>This code expires in 1 hour. If you didn't create this account, you can ignore this email.</p>
  </div>
  <div class="footer">Learnova &mdash; AI-powered learning</div>
</div>
</body>
</html>"""
    subject = f"Your Learnova verification code: {code}"
    return await _send_email(user_email, subject, html)


async def send_reset_password_email(user_email: str, user_name: str, reset_token: str) -> bool:
    """Send a password reset email with a link containing the reset token.

    Args:
        user_email:  Recipient's email address.
        user_name:   Recipient's display name.
        reset_token: JWT token to embed in the reset link.

    Returns:
        True if the email was sent successfully.
    """
    app_url = os.getenv("APP_URL", "http://localhost:8000")
    reset_link = f"{app_url}/reset-password.html?token={reset_token}"
    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: Georgia, serif; background: #F7F5F2; margin: 0; padding: 0; color: #1C1917; }}
  .wrap {{ max-width: 580px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; }}
  .header {{ background: linear-gradient(135deg,#1C1917,#2D2A27); padding: 40px; text-align: center; }}
  .header h1 {{ color: #C8B89A; font-size: 28px; margin: 0; }}
  .body {{ padding: 36px 40px; }}
  .greeting {{ font-size: 20px; margin-bottom: 16px; }}
  p {{ font-size: 14px; color: #6B7280; line-height: 1.7; }}
  .cta {{ display: inline-block; background: #1C1917; color: #C8B89A !important; text-decoration: none;
          text-align: center; padding: 14px 32px; border-radius: 8px; font-size: 15px; margin: 20px 0; }}
  .footer {{ padding: 20px 40px; font-size: 12px; color: #9CA3AF; text-align: center; }}
  .footer a {{ color: #9CA3AF; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header"><h1>Learnova ✦</h1></div>
  <div class="body">
    <div class="greeting">Hi {user_name},</div>
    <p>We received a request to reset your Learnova account password.
       Click the button below to set a new password. This link expires in <strong>1 hour</strong>.</p>
    <div style="text-align:center">
      <a class="cta" href="{reset_link}">Reset your password</a>
    </div>
    <p style="margin-top:24px">If you didn't request this, you can safely ignore this email.
       Your current password will stay the same.</p>
  </div>
  <div class="footer">
    Learnova &mdash; AI-powered learning<br>
    <a href="{app_url}">{app_url}</a>
  </div>
</div>
</body>
</html>"""
    subject = "Reset your Learnova password"
    return await _send_email(user_email, subject, html)


def _build_pro_welcome_email_html(name: str, plan_type: str) -> str:
    """Build the HTML for a Pro upgrade welcome email.

    Highlights the premium features unlocked by the upgrade.
    Uses the Learnova brand palette with a gradient header.

    Args:
        name:      Recipient's display name.
        plan_type:  One of "monthly" or "yearly".

    Returns:
        Complete HTML string.
    """
    label = "Monthly" if plan_type == "monthly" else "Yearly"
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: Georgia, serif; background: #F7F5F2; margin: 0; padding: 0; color: #1C1917; }}
  .wrap {{ max-width: 580px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; }}
  .header {{ background: linear-gradient(135deg,#1C1917,#2D2A27); padding: 40px; text-align: center; }}
  .header h1 {{ color: #C8B89A; font-size: 28px; margin: 0; }}
  .header .badge {{ display: inline-block; background: #C8B89A; color: #1C1917; font-size: 11px;
          letter-spacing: 2px; text-transform: uppercase; padding: 4px 12px; border-radius: 12px; margin-top: 12px; }}
  .body {{ padding: 36px 40px; }}
  .greeting {{ font-size: 20px; margin-bottom: 16px; }}
  .perks {{ list-style: none; padding: 0; margin: 24px 0; }}
  .perks li {{ padding: 10px 0; border-bottom: 1px solid #E5E0D8; font-size: 14px; color: #1C1917; }}
  .perks li::before {{ content: "✓ "; color: #6E512B; font-weight: bold; }}
  .cta {{ display: block; background: #1C1917; color: #C8B89A !important; text-decoration: none;
          text-align: center; padding: 14px; border-radius: 8px; font-size: 15px; margin-top: 32px; }}
  .footer {{ padding: 20px 40px; font-size: 12px; color: #9CA3AF; text-align: center; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>Learnova ✦</h1>
    <div class="badge">Pro · {label}</div>
  </div>
  <div class="body">
    <div class="greeting">You're a Pro now, {name}!</div>
    <p style="font-size:14px;color:#6B7280;line-height:1.6">
      Thanks for upgrading. Here's what you've unlocked:
    </p>
    <ul class="perks">
      <li>Upload PPTX files for summarisation</li>
      <li>Upload up to 3 files at once</li>
      <li>Priority processing on both AI models</li>
      <li>Full study history and analytics</li>
      <li>Calendar integration with Apple & Google</li>
    </ul>
    <a href="http://localhost:8000/upload.html" class="cta">Upload your first PPTX →</a>
  </div>
  <div class="footer">
    Learnova · AI-Powered Learning Platform<br>
    {label} plan · cancel anytime
  </div>
</div>
</body>
</html>"""


def _build_welcome_email_html(name: str) -> str:
    """Build the HTML for a new-user welcome email.

    Simple, friendly design with a call-to-action to upload the first document.
    Inlines all CSS for email client compatibility.

    Args:
        name: Recipient's display name.

    Returns:
        Complete HTML string.
    """
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: Georgia, serif; background: #F7F5F2; margin: 0; padding: 0; color: #1C1917; }}
  .wrap {{ max-width: 580px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; }}
  .header {{ background: #1C1917; padding: 36px 40px; text-align: center; }}
  .header h1 {{ color: #C8B89A; font-size: 28px; margin: 0; }}
  .header p {{ color: rgba(240,237,232,0.5); margin: 8px 0 0; font-size: 14px; }}
  .body {{ padding: 36px 40px; text-align: center; }}
  .greeting {{ font-size: 22px; margin-bottom: 8px; }}
  .sub {{ font-size: 14px; color: #6B7280; margin-bottom: 28px; line-height: 1.6; }}
  .rocket {{ font-size: 64px; margin: 0 0 20px; display: block; }}
  .cta {{ display: inline-block; background: #1C1917; color: #C8B89A !important; text-decoration: none;
          padding: 14px 32px; border-radius: 8px; font-size: 15px; margin-top: 8px; }}
  .footer {{ padding: 20px 40px; font-size: 12px; color: #9CA3AF; text-align: center; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>Learnova ✦</h1>
    <p>AI-Powered Learning Platform</p>
  </div>
  <div class="body">
    <span class="rocket">🚀</span>
    <div class="greeting">Hey {name},</div>
    <div class="sub">
      Welcome to Learnova!<br><br>
      Nothing to see here yet — but give it a week<br>
      and you'll have summaries, quizzes, and insights<br>
      waiting for you.<br><br>
      Upload your first document and let the AI<br>
      do the heavy lifting.
    </div>
    <a href="http://localhost:8000/upload.html" class="cta">Upload your first document →</a>
  </div>
  <div class="footer">
    Learnova · AI-Powered Learning Platform
  </div>
</div>
</body>
</html>"""


def _build_email_html(name: str, stats: dict) -> str:
    """Build the HTML for a weekly progress report email.

    Displays summary stats (documents, quizzes, average score) in a card layout,
    followed by lists of strong areas and topics needing more work.

    Args:
        name:  Recipient's display name.
        stats: Dict from gather_user_stats() containing weekly activity data.

    Returns:
        Complete HTML string.
    """
    avg = f"{stats['avg_score']}%" if stats['avg_score'] is not None else "No quizzes yet"
    weak_html = "".join(f"<li>{t}</li>" for t in stats["weak_topics"]) or "<li>None identified</li>"
    strong_html = "".join(f"<li>{t}</li>" for t in stats["strong_topics"]) or "<li>None identified</li>"
    docs_html = "".join(f"<li>{t}</li>" for t in stats["doc_titles"]) or "<li>None this week</li>"

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: Georgia, serif; background: #F7F5F2; margin: 0; padding: 0; color: #1C1917; }}
  .wrap {{ max-width: 580px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; }}
  .header {{ background: #1C1917; padding: 36px 40px; }}
  .header h1 {{ color: #C8B89A; font-size: 28px; margin: 0 0 4px; }}
  .header p {{ color: rgba(240,237,232,0.5); margin: 0; font-size: 14px; }}
  .body {{ padding: 36px 40px; }}
  .greeting {{ font-size: 20px; margin-bottom: 24px; }}
  .stat-row {{ display: flex; gap: 16px; margin-bottom: 28px; }}
  .stat {{ flex: 1; background: #F7F5F2; border-radius: 8px; padding: 18px; text-align: center; }}
  .stat-num {{ font-size: 32px; font-weight: bold; color: #6E512B; }}
  .stat-label {{ font-size: 11px; color: #6B7280; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }}
  h3 {{ font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #6B7280; margin: 24px 0 8px; }}
  ul {{ margin: 0; padding-left: 18px; }}
  li {{ font-size: 14px; color: #1C1917; margin-bottom: 4px; }}
  .cta {{ display: block; background: #1C1917; color: #C8B89A !important; text-decoration: none;
          text-align: center; padding: 14px; border-radius: 8px; font-size: 15px; margin-top: 32px; }}
  .footer {{ padding: 20px 40px; font-size: 12px; color: #9CA3AF; text-align: center; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>Learnova ✦</h1>
    <p>Your weekly learning report</p>
  </div>
  <div class="body">
    <div class="greeting">Hi {name},</div>
    <p style="font-size:14px;color:#6B7280;margin-bottom:28px">
      Here's what you accomplished this week on Learnova.
    </p>
    <div class="stat-row">
      <div class="stat">
        <div class="stat-num">{stats['total_docs']}</div>
        <div class="stat-label">Documents studied</div>
      </div>
      <div class="stat">
        <div class="stat-num">{stats['quizzes_completed']}</div>
        <div class="stat-label">Quizzes completed</div>
      </div>
      <div class="stat">
        <div class="stat-num">{avg}</div>
        <div class="stat-label">Average score</div>
      </div>
    </div>
    <h3>Documents this week</h3>
    <ul>{docs_html}</ul>
    <h3>Strong areas</h3>
    <ul>{strong_html}</ul>
    <h3>Needs more work</h3>
    <ul>{weak_html}</ul>
    <a href="http://localhost:8000/dashboard.html" class="cta">Continue learning →</a>
  </div>
  <div class="footer">
    You're receiving this because you have an active Learnova account.<br>
    Learnova · AI-Powered Learning Platform
  </div>
</div>
</body>
</html>
"""
