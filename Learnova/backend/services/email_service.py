"""
Weekly progress email service using Resend API.
Runs every Monday at 8:00 AM via APScheduler.
"""
from __future__ import annotations

import os
import json
import httpx
from datetime import datetime, timezone, timedelta


RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "learnovaaiproject@gmail.com")
# Resend requires a verified domain — use their onboarding address for testing
EMAIL_FROM_NAME = "Learnova"


async def send_weekly_report(user_email: str, user_name: str, stats: dict) -> bool:
    """Send weekly progress email via Resend API. Returns True on success."""
    if not RESEND_API_KEY:
        print("[email] RESEND_API_KEY not set — skipping email")
        return False

    html = _build_email_html(user_name, stats)
    subject = f"Your Learnova weekly report — {datetime.now().strftime('%d %b %Y')}"

    # Resend free tier only allows sending to the verified account email
    # Use EMAIL_FROM as the recipient override if set, otherwise use user_email
    verified_email = os.getenv("EMAIL_FROM", user_email)
    payload = {
        "from": f"{EMAIL_FROM_NAME} <onboarding@resend.dev>",
        "to": [verified_email],
        "reply_to": user_email,
        "subject": subject,
        "html": html,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code == 200:
                print(f"[email] ✅ Weekly report sent to {user_email}")
                return True
            else:
                print(f"[email] ❌ Failed to send to {user_email}: {resp.status_code} {resp.text[:500]}")
                return False
    except Exception as e:
        print(f"[email] ❌ Error sending to {user_email}: {e}")
        return False


async def gather_user_stats(user_id: str, db_history) -> dict:
    """Pull last 7 days of activity from MongoDB for a user."""
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
    """Called by the scheduler every Monday. Sends report to all active users."""
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


async def send_summary_report(user_email: str, user_name: str, doc_title: str, summary: dict) -> bool:
    """Send an email containing the document summary via Resend API."""
    if not RESEND_API_KEY:
        print("[email] RESEND_API_KEY not set — skipping summary email")
        return False

    html = _build_summary_email_html(user_name, doc_title, summary)
    subject = f"Your Learnova summary — {doc_title[:60]}"

    verified_email = os.getenv("EMAIL_FROM", user_email)
    payload = {
        "from": f"{EMAIL_FROM_NAME} <onboarding@resend.dev>",
        "to": [verified_email],
        "reply_to": user_email,
        "subject": subject,
        "html": html,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code == 200:
                print(f"[email] ✅ Summary report sent to {user_email}")
                return True
            else:
                print(f"[email] ❌ Failed to send summary to {user_email}: {resp.status_code} {resp.text[:500]}")
                return False
    except Exception as e:
        print(f"[email] ❌ Error sending summary to {user_email}: {e}")
        return False


def _build_summary_email_html(name: str, doc_title: str, summary: dict) -> str:
    """Build HTML for a summary report email."""
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


def _build_email_html(name: str, stats: dict) -> str:
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