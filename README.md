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
2. **7 days before** the interruption date (fires anywhere in a 2–7 day
   window, not only on exactly day 7 — see below).
3. **The day before** the interruption date (fires anywhere in a 0–1 day
   window).

Both are computed against the current date in Sri Lanka local time
(Asia/Colombo), not the scheduler's clock, so the scheduled GitHub Actions
runner (UTC) can't shift which calendar day a reminder lands on.

**Why windows, not exact days:** the scraper can fail on any given run —
LECO's site being down, a network error, the workflow itself failing. If the
7-day and 1-day stages fired only on the exact matching day, a single missed
run on that specific day would mean that reminder never fires again, since
the day-count only counts down from there. Using a window instead means
whichever run first lands inside it fires the stage once (state-based dedup,
as always, is what prevents a repeat) — a late run just means a shorter
notice period, not a silently lost reminder. The 7-day and 1-day windows
don't overlap each other, so if a run is missed for the entire 7-day window
(days 7 down through 2), that reminder is simply skipped rather than firing
late with stale "7 days away" wording once it's actually tomorrow. The only
stage that can still coincide with a reminder is `immediate`, when an
outage is first discovered already inside one of these windows — in that
case only `immediate` is emailed (a "reminder" implies a prior notice
existed, which contradicts "immediate" meaning first contact), and the
coinciding reminder is marked fulfilled so it doesn't fire separately later.

If every branch's scrape fails in the same run (e.g. leco.lk is entirely
unreachable), the run aborts loudly (non-zero exit, visible as a failed
GitHub Actions run) instead of silently treating "fetched nothing" the same
as "genuinely no outages today" — the latter would otherwise hide the
difference between "nothing scheduled" and "the scraper is broken."

If an outage is later removed from LECO's site — cancelled, or the notice
retracted — no further reminders are sent for it, since matching only
considers outages that are actually present in the current scrape. This is
intentional: reminding someone about a cancelled outage would be worse than
saying nothing.

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
- `leco_notifier/store.py` persists `data/subscribers.json.enc` (who to
  notify about which streets) and `data/state.json.enc` (which
  outage+subscriber+stage combinations have already been emailed, so
  nothing is re-sent or repeated on the next run) — both encrypted at rest
  (see Encryption below).
- `.github/workflows/check-outages.yml` runs the check everyday via
  GitHub Actions and commits the updated `data/state.json.enc` back to the
  repo.

## Encryption

`data/subscribers.json.enc` and `data/state.json.enc` are both encrypted
with [Fernet](https://cryptography.io/en/latest/fernet/) symmetric
encryption (`leco_notifier/crypto.py`), decrypted in memory on load and
re-encrypted on save — nothing ever touches disk as plaintext. Both files
needed it: subscribers.json obviously holds real emails, but state.json's
dedup keys embed them too (`"<hash>:someone@example.com:immediate"`), so
leaving it plaintext would have defeated the point.

The key is a single `LECO_ENCRYPTION_KEY` env var — generate one with:

```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

and set it in `.env` for local runs and as a GitHub Actions secret for the
scheduled workflow, the same way `SMTP_PASS` already is. This is encryption
at rest, not a security boundary against the process itself — whatever runs
the notifier must hold the key to decrypt and re-encrypt on every run, so
the key is exactly as sensitive as the SMTP password. **Losing the key makes
the encrypted files unrecoverable** (subscribers would need to
re-subscribe); **leaking it is equivalent to leaking the plaintext**. There
is no way around this trade-off for a single automated process that both
reads and writes the same data — back the key up somewhere safe (e.g. a
password manager) in addition to the GitHub secret.

Because Fernet's ciphertext is non-deterministic (a random IV each time),
re-encrypting unchanged data still produces a different file every time —
`main.py` only calls `save_state()` when the `sent` set actually changed,
so the workflow's "commit only if the file changed" check still means
something instead of committing a no-op diff every run.

## Setup

1. Install dependencies:

   ```
   poetry install
   ```

2. Set an encryption key — required before adding subscribers, since the
   CLI encrypts on write. Generate one and put it in `.env`:

   ```
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   See [Encryption](#encryption) below for what this key protects and why
   losing or leaking it matters.

3. Add subscribers (repeatable):

   ```
   poetry run leco-add-subscriber someone@example.com Galle "Kandewatta Rd" "Wackwella Rd"
   ```

   This updates `data/subscribers.json.enc`, encrypted — there's nothing to
   hand-edit directly. `data/subscribers.json.example` shows the shape each
   entry has: `{"email": ..., "branch": ..., "region": ..., "streets": [...]}`
   (`region` is optional). Street names only need to be a substring of what
   LECO publishes (e.g. "Kandewatta" matches "Kandewatta Rd(portion)").

   The branch is required and must be one of `Galle`, `Kaluthara`,
   `Kelaniya`, `Kotte`, `Moratuwa`, `Negombo`, `Nugegoda` — street names are
   not unique across LECO's branch regions, so matching is scoped to one
   branch per subscription. To watch streets in more than one branch, run
   the command again with the same email and a different branch; it adds a
   second entry rather than merging across branches. If you don't know a
   street's branch, check which map region it falls under at
   https://www.leco.lk/powerIntrup_e.php.

   Each branch itself covers several towns (e.g. Galle branch covers GALLE,
   AMBALANGODA, HIKKADUWA), and street names can repeat across those too —
   add `--region "Ambalangoda"` to narrow matching to one town within the
   branch:

   ```
   poetry run leco-add-subscriber someone@example.com Galle --region Ambalangoda "Galle Rd"
   ```

   The region must match the town name exactly as LECO's site spells it
   (case-insensitive) — check the current listing at
   https://www.leco.lk/powerIntrup_e.php for the right spelling. It isn't
   validated against a fixed list the way branch is, since the set of towns
   isn't static; a typo just means the subscription matches nothing rather
   than erroring at add time. Region is optional — without it, matching
   stays branch-wide, which is fine unless a street name happens to repeat
   across towns in that branch.

4. Configure SMTP credentials. Copy `.env.example` to `.env` for local runs,
   or set the same variables as GitHub Actions repository secrets
   (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `FROM_EMAIL`,
   `LECO_ENCRYPTION_KEY`) for the scheduled workflow. Any standard
   SMTP+STARTTLS provider works:

   - **Gmail**: `smtp.gmail.com:587`, with an
     [app password](https://myaccount.google.com/apppasswords) (requires
     2-Step Verification turned on first).
   - **Outlook/Hotmail**: `smtp-mail.outlook.com:587`, with an app password
     from [account.microsoft.com](https://account.microsoft.com/security) →
     Advanced security options (also requires 2-step verification turned on
     first — if "App passwords" doesn't appear there, Microsoft has disabled
     basic SMTP auth for that account and Gmail is the more reliable option).

5. Run a check manually:

   ```
   export $(cat .env | xargs)   # or use a tool like direnv
   poetry run leco-check
   ```

6. Commit `data/subscribers.json.enc` and push. The GitHub Actions workflow
   runs on its own schedule from there (or trigger it manually from the
   Actions tab via "Run workflow").

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
6. Remove the test subscriber from `data/subscribers.json.enc` and reset
   `data/state.json.enc` back to an encrypted `{"sent": []}` before
   committing, so test data doesn't leak into production state.

## Notes

- LECO's markup is malformed HTML (unclosed `<p>` tags used as pseudo
  delimiters between town/date/street blocks); the parser relies on lxml's
  HTML parser to auto-close them the way a browser would. If LECO changes
  their page structure, `leco_notifier/parser.py` is the place to fix it.
- Matching is a simple case-insensitive substring match against the raw
  street list text LECO publishes — it isn't aware of street name synonyms
  or spelling variants.
