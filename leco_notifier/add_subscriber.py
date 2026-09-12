"""CLI to add or update a subscriber.

Usage:
    poetry run leco-add-subscriber user@example.com Galle "Kandewatta Rd" "Wackwella Rd"
    poetry run leco-add-subscriber user@example.com Galle --region Ambalangoda "Galle Rd"

Street names are not unique across LECO's branch regions, so every
subscription is scoped to one branch. To watch streets in more than one
branch, run this again with the same email and a different branch — it adds
a second subscriber entry rather than merging across branches.

A branch can itself cover several towns (e.g. Galle branch covers GALLE,
AMBALANGODA, HIKKADUWA), and street names can repeat across those too.
--region narrows matching to one town within the branch, matched exactly
(case-insensitive) against what LECO's site calls it — check
https://www.leco.lk/powerIntrup_e.php for the exact spelling if unsure.
Without --region, matching stays branch-wide, which risks the same false
positives across towns that branch scoping already fixed across branches.
"""

import argparse
import sys

from .areas import BRANCHES
from .store import load_subscribers, save_subscribers

BRANCHES_BY_LOWER = {b.lower(): b for b in BRANCHES}


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="leco-add-subscriber",
        description="Add or update a LECO outage notifier subscriber.",
    )
    parser.add_argument("email")
    parser.add_argument("branch", help=f"One of: {', '.join(BRANCHES)}")
    parser.add_argument(
        "--region",
        help="Town within the branch to scope matching to (e.g. 'Ambalangoda'). Optional but recommended.",
    )
    parser.add_argument("streets", nargs="+", help="Street name(s) to watch")
    return parser.parse_args(argv)


def main() -> int:
    args = _parse_args(sys.argv[1:])

    email = args.email.strip()
    branch = BRANCHES_BY_LOWER.get(args.branch.strip().lower())
    if branch is None:
        print(f"Unknown branch '{args.branch}'. Must be one of: {', '.join(BRANCHES)}", file=sys.stderr)
        return 1

    region = args.region.strip() if args.region else None
    streets = [s.strip() for s in args.streets if s.strip()]
    if not streets:
        print("Provide at least one street name to watch.", file=sys.stderr)
        return 1

    subscribers = load_subscribers()
    existing = next(
        (
            s
            for s in subscribers
            if s.get("email", "").lower() == email.lower()
            and s.get("branch", "").lower() == branch.lower()
            and (s.get("region") or "").lower() == (region or "").lower()
        ),
        None,
    )
    label = f"{branch}/{region}" if region else branch
    if existing:
        merged = sorted(set(existing.get("streets", [])) | set(streets))
        existing["streets"] = merged
        print(f"Updated {email} ({label}): watching {merged}")
    else:
        entry = {"email": email, "branch": branch, "streets": streets}
        if region:
            entry["region"] = region
        subscribers.append(entry)
        print(f"Added {email} ({label}): watching {streets}")

    save_subscribers(subscribers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
