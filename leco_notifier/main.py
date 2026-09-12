import logging
import sys

from .mailer import build_email_body, send_email
from .matcher import find_matches
from .parser import parse_all_areas
from .reminders import STAGE_IMMEDIATE, STAGE_ORDER, eligible_stages, local_now
from .scraper import fetch_all_areas
from .store import load_state, load_subscribers, save_state

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _sent_key(outage_id: str, email: str, stage: str) -> str:
    return f"{outage_id}:{email}:{stage}"


def main() -> int:
    subscribers = load_subscribers()
    if not subscribers:
        logger.info("No subscribers configured; nothing to do.")
        return 0

    state = load_state()
    sent = set(state.get("sent", []))

    now_local = local_now()
    today_local = now_local.date()
    now_naive = now_local.replace(tzinfo=None)

    logger.info("Fetching outage notices for %d area(s)...", 7)
    pages = fetch_all_areas()
    outages = parse_all_areas(pages)
    logger.info("Parsed %d outage record(s).", len(outages))

    new_sent = set(sent)
    for subscriber in subscribers:
        email = subscriber.get("email")
        if not email:
            continue

        matches = find_matches(subscriber, outages, now=now_naive)

        # Collect (outage, stage) pairs that are due now and haven't been
        # sent before, keeping stage order (immediate, 7-day, 1-day) stable.
        to_notify = []  # (outage, stage, key) that will actually be emailed
        to_mark_sent_only = []  # keys fulfilled by the email but not listed in it

        for outage in matches:
            due = [
                (outage, stage, _sent_key(outage.id, email, stage))
                for stage in eligible_stages(outage, today_local)
                if _sent_key(outage.id, email, stage) not in sent
            ]
            if not due:
                continue

            # If an outage is first seen on the same day its 7-day or 1-day
            # reminder would also fire, that's one event, not two: a
            # "reminder" implies a prior notice existed, which "immediate"
            # contradicts. Send only the immediate stage, but still mark the
            # coinciding stage as fulfilled so it never fires as a separate
            # message later.
            immediate_entry = next((d for d in due if d[1] == STAGE_IMMEDIATE), None)
            if immediate_entry:
                to_notify.append(immediate_entry)
                to_mark_sent_only.extend(key for _, stage, key in due if stage != STAGE_IMMEDIATE)
            else:
                to_notify.extend(due)

        to_notify.sort(key=lambda t: STAGE_ORDER.index(t[1]))

        if not to_notify:
            continue

        body = build_email_body([(outage, stage) for outage, stage, _ in to_notify])
        subject = f"LECO power interruption notice ({len(to_notify)} update{'s' if len(to_notify) != 1 else ''})"
        try:
            send_email(email, subject, body)
            logger.info("Sent %d new notice(s) to %s", len(to_notify), email)
            for _, _, key in to_notify:
                new_sent.add(key)
            new_sent.update(to_mark_sent_only)
        except Exception:
            logger.exception("Failed to send email to %s", email)

    save_state({"sent": sorted(new_sent)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
