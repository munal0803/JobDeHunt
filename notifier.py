import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import EMAIL_FROM, EMAIL_TO, SMTP_HOST, SMTP_PORT, SMTP_PASSWORD, SMTP_USER


def _format_job_text(job, index):
    lines = [
        f"{index}. {job['title']}",
        f"   Company:  {job['company']}",
        f"   Location: {job['location']}",
    ]
    if job.get("posted_on"):
        lines.append(f"   Posted:   {job['posted_on']}")
    lines.append(f"   Apply:    {job['url']}")
    return "\n".join(lines)


def _format_job_html(job, index):
    posted = (
        f"<p><strong>Posted:</strong> {job['posted_on']}</p>"
        if job.get("posted_on")
        else ""
    )
    return f"""
    <div style="margin-bottom: 20px; padding: 12px; border: 1px solid #ddd; border-radius: 6px;">
        <h3 style="margin: 0 0 8px 0;">{index}. {job['title']}</h3>
        <p><strong>Company:</strong> {job['company']}</p>
        <p><strong>Location:</strong> {job['location']}</p>
        {posted}
        <p><a href="{job['url']}">View job posting</a></p>
    </div>
    """


def send_jobs_email(jobs):
    if not jobs:
        return False

    if not all([SMTP_USER, SMTP_PASSWORD, EMAIL_TO]):
        print(
            f"Email not configured. Set SMTP_USER, SMTP_PASSWORD, and EMAIL_TO in .env "
            f"({len(jobs)} job(s) were saved but not emailed)."
        )
        return False

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject = f"Job Alert: {len(jobs)} new job(s) found - {timestamp}"

    text_body = "\n\n".join(_format_job_text(job, i + 1) for i, job in enumerate(jobs))
    text_body = f"New job postings found on {timestamp}\n\n{text_body}"

    html_jobs = "".join(_format_job_html(job, i + 1) for i, job in enumerate(jobs))
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #222;">
        <h2>New Job Postings ({len(jobs)})</h2>
        <p>Found on {timestamp}</p>
        {html_jobs}
    </body>
    </html>
    """

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = EMAIL_FROM
    message["To"] = EMAIL_TO
    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, [EMAIL_TO], message.as_string())
        print(f"Email sent to {EMAIL_TO} with {len(jobs)} job(s).")
        return True
    except smtplib.SMTPAuthenticationError:
        print(
            "Failed to send email: Gmail rejected the login.\n"
            "Use a Gmail App Password (not your normal password):\n"
            "  1. Enable 2-Step Verification on your Google account\n"
            "  2. Go to https://myaccount.google.com/apppasswords\n"
            "  3. Create an app password and put it in SMTP_PASSWORD in .env\n"
            f"  ({len(jobs)} matching job(s) were saved in the database.)"
        )
        return False
    except smtplib.SMTPException as exc:
        print(f"Failed to send email: {exc} ({len(jobs)} job(s) saved in database).")
        return False


def notify_console(job):
    body = f"""
New Job Posted!

Company: {job['company']}
Role: {job['title']}
Location: {job['location']}
{f"Posted: {job['posted_on']}" if job.get('posted_on') else ""}
{job['url']}
"""
    print(body.strip())


def notify(job):
    notify_console(job)
