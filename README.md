# LECO Notifier

LECO (Lanka Electricity Company) only SMS's planned power-interruption
notices to the phone number linked to your account, and publishes the full
schedule on its website by street name, split across 7 branch region pages:
https://www.leco.lk/powerIntrup_e.php?areaId={1,3,5,7,9,11,13}

This project scrapes those 7 pages, matches the listed streets against a
list of subscribers' street names, and emails anyone whose street shows up
in a notice — with a reminder schedule, not just a single alert.

## Reminder schedule

For every (outage, subscriber) pair, up to three emails are sent, each only
once, tracked independently:

1. **Now** — the first time the notice is seen (could be the day it's
   published, whether that's weeks or hours ahead).
2. **7 days before** the interruption date.
3. **The day before** the interruption date.

"Day before" and "7 days before" are computed against the current date in
Sri Lanka local time (Asia/Colombo), not the scheduler's clock, so the
6-hourly GitHub Actions runner (UTC) can't shift which calendar day a
reminder lands on. If a notice is first published fewer than 7 (or 1) days
out, that stage's window has already passed and only the remaining stages
fire — no reminder is invented after the fact. A stage is never repeated
once its state entry is recorded, so re-running the workflow the same day
doesn't duplicate a stage that already went out.

## How it works

- `leco_notifier/scraper.py` fetches the 7 area pages.
- `leco_notifier/parser.py` parses each page's outage table (LECO + CEB
  notices, grouped by town, with date ranges and street lists) into
  `Outage` records.
- `leco_notifier/matcher.py` matches a subscriber's watched street names
  against each outage's street list (case-insensitive substring match) and
  drops outages whose interruption window has already passed.
- `leco_notifier/reminders.py` computes, in Sri Lanka local time, which of
  the three reminder stages (`immediate`, `7_day_reminder`, `1_day_reminder`)
  are due for a given outage as of today.
- `leco_notifier/mailer.py` emails a subscriber via SMTP when a new
  (outage, stage) pair is due.
- `leco_notifier/store.py` persists `data/subscribers.json` (who to notify
  about which streets) and `data/state.json` (which outage+subscriber+stage
  combinations have already been emailed, so nothing is re-sent or repeated
  on the next run).
- `.github/workflows/check-outages.yml` runs the check every 6 hours via
  GitHub Actions and commits the updated `data/state.json` back to the repo.

## Setup

1. Install dependencies:

   ```
   poetry install
   ```

2. Add subscribers (repeatable):

   ```
   poetry run leco-add-subscriber someone@example.com Galle "Kandewatta Rd" "Wackwella Rd"
   ```

   This updates `data/subscribers.json`. You can also edit that file by
   hand — it's a plain JSON list of
   `{"email": ..., "branch": ..., "streets": [...]}`. Street names only need
   to be a substring of what LECO publishes (e.g. "Kandewatta" matches
   "Kandewatta Rd(portion)").

   The branch is required and must be one of `Galle`, `Kaluthara`,
   `Kelaniya`, `Kotte`, `Moratuwa`, `Negombo`, `Nugegoda` — street names are
   not unique across LECO's branch regions, so matching is scoped to one
   branch per subscription. To watch streets in more than one branch, run
   the command again with the same email and a different branch; it adds a
   second entry rather than merging across branches. If you don't know a
   street's branch, check which map region it falls under at
   https://www.leco.lk/powerIntrup_e.php.

3. Configure SMTP credentials. Copy `.env.example` to `.env` for local runs,
   or set the same variables as GitHub Actions repository secrets
   (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `FROM_EMAIL`) for the
   scheduled workflow. Any standard SMTP+STARTTLS provider works:

   - **Gmail**: `smtp.gmail.com:587`, with an
     [app password](https://myaccount.google.com/apppasswords) (requires
     2-Step Verification turned on first).
   - **Outlook/Hotmail**: `smtp-mail.outlook.com:587`, with an app password
     from [account.microsoft.com](https://account.microsoft.com/security) →
     Advanced security options (also requires 2-step verification turned on
     first — if "App passwords" doesn't appear there, Microsoft has disabled
     basic SMTP auth for that account and Gmail is the more reliable option).

4. Run a check manually:

   ```
   export $(cat .env | xargs)   # or use a tool like direnv
   poetry run leco-check
   ```

5. Commit `data/subscribers.json` and push. The GitHub Actions workflow runs
   on its own schedule from there (or trigger it manually from the Actions
   tab via "Run workflow").

## Testing

### Automated tests (no network, no email)

```
poetry install
poetry run pytest -q
```

`tests/test_parser.py` parses a captured real LECO page
(`tests/fixtures/area1.html`) and checks the branch/section/date/street
extraction. `tests/test_reminders.py` checks the 7-day / 1-day / immediate
stage math. `tests/test_matcher.py` checks street matching and expiry.
`tests/test_main_dedup.py` runs the full `main()` flow twice against a
faked scraper and a fake SMTP sender (via monkeypatching), asserting the
second same-day run sends nothing new — this is what actually proves the
dedup logic works end to end. These run automatically on every push via
`.github/workflows/tests.yml`.

### Real end-to-end email test

To confirm SMTP actually delivers, without waiting for a real outage to
land exactly 7 or 1 days out:

1. Find a street currently listed on https://www.leco.lk/powerIntrup_e.php,
   its branch, and its interruption date.
2. Add yourself as a subscriber for that street:
   ```
   poetry run leco-add-subscriber you@example.com Galle "That Street Name"
   ```
3. Run once normally — this sends the "immediate" stage:
   ```
   set -a && source .env && set +a && poetry run leco-check
   ```
4. To also see the "7 days before" or "day before" stage fire, override
   what day the code thinks it is with `LECO_FAKE_NOW` (an ISO datetime),
   set to exactly 7 or 1 day before that outage's start date, then run
   again — the "immediate" stage is already recorded as sent, so only the
   new stage goes out:
   ```
   LECO_FAKE_NOW="2026-09-19T09:00:00" poetry run leco-check
   ```
5. Run it a second time with the same `LECO_FAKE_NOW` value — it should
   log/send nothing, confirming that stage won't repeat.
6. Remove the test subscriber from `data/subscribers.json` and reset
   `data/state.json` back to `{"sent": []}` before committing, so test data
   doesn't leak into production state.

## Notes

- LECO's markup is malformed HTML (unclosed `<p>` tags used as pseudo
  delimiters between town/date/street blocks); the parser relies on lxml's
  HTML parser to auto-close them the way a browser would. If LECO changes
  their page structure, `leco_notifier/parser.py` is the place to fix it.
- Matching is a simple case-insensitive substring match against the raw
  street list text LECO publishes — it isn't aware of street name synonyms
  or spelling variants.
