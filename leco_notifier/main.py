import logging
import sys

from .mailer import build_email_body, send_email
from .matcher import find_matches
from .parser import parse_all_areas
from .reminders import DISPLAY_PRIORITY, STAGE_ORDER, eligible_stages, local_now
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
    if not pages:
        # scraper.fetch_all_areas already logs each area's failure; this is
        # the "all 7 failed" case, which would otherwise look identical to a
        # legitimately quiet day (0 outages) and hide a real outage. Fail the
        # run loudly instead of silently sending nothing.
        logger.error("Failed to fetch any area pages this run; aborting without sending.")
        return 1
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

            # More than one stage can become due for the same outage in the
            # same run — either because it's discovered late (e.g. first seen
            # 3 days out: immediate and the 7-day window are both open), or
            # because a run was missed and the calendar rolled past a stage's
            # window before a run caught it (e.g. skipping straight from
            # 7-days-out to 1-day-out). Either way that's one event, not
            # several: only the most urgent/informative stage is actually
            # emailed; the rest are still real and get marked fulfilled so
            # they never fire separately later.
            due_stages = {stage for _, stage, _ in due}
            display_stage = next(s for s in DISPLAY_PRIORITY if s in due_stages)
            display_entry = next(d for d in due if d[1] == display_stage)
            to_notify.append(display_entry)
            to_mark_sent_only.extend(key for _, stage, key in due if stage != display_stage)

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

    if new_sent != sent:
        # Fernet's ciphertext is non-deterministic (random IV per encrypt),
        # so re-saving unchanged state would still produce a different file
        # every run — only write when the sent set actually changed, so the
        # workflow's "commit only if the file changed" check stays meaningful
        # instead of committing a no-op diff every single run.
        save_state({"sent": sorted(new_sent)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
