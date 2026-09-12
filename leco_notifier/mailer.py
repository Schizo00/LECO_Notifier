import os
import smtplib
from email.mime.text import MIMEText

from .reminders import STAGE_LABELS


def _format_outage(outage, stage: str) -> str:
    date_from = outage.date_from.strftime("%a %d %b, %I:%M %p") if outage.date_from else outage.date_from_raw
    date_to = outage.date_to.strftime("%I:%M %p") if outage.date_to else outage.date_to_raw
    label = STAGE_LABELS.get(stage, stage)
    return (
        f"[{label}]\n"
        f"- {outage.town} ({outage.branch}, {outage.source})\n"
        f"  {date_from} to {date_to}\n"
        f"  Streets: {outage.streets_raw}"
    )


def build_email_body(notifications: list) -> str:
    """`notifications` is a list of (outage, stage) tuples."""
    sections = [_format_outage(outage, stage) for outage, stage in notifications]
    return (
        "LECO has a planned power interruption that may affect one of your "
        "subscribed streets:\n\n"
        + "\n\n".join(sections)
        + "\n\nSource: https://www.leco.lk/powerIntrup_e.php\n"
    )


def send_email(to_address: str, subject: str, body: str) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    from_address = os.environ.get("FROM_EMAIL", user)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(from_address, [to_address], msg.as_string())
