"""CLI to add or update a subscriber.

Usage:
    poetry run leco-add-subscriber user@example.com Galle "Kandewatta Rd" "Wackwella Rd"

Street names are not unique across LECO's branch regions, so every
subscription is scoped to one branch. To watch streets in more than one
branch, run this again with the same email and a different branch — it adds
a second subscriber entry rather than merging across branches.
"""

import sys

from .areas import BRANCHES
from .store import load_subscribers, save_subscribers

BRANCHES_BY_LOWER = {b.lower(): b for b in BRANCHES}


def main() -> int:
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <email> <branch> <street1> [street2 ...]", file=sys.stderr)
        print(f"Branches: {', '.join(BRANCHES)}", file=sys.stderr)
        return 1

    email = sys.argv[1].strip()
    branch_input = sys.argv[2].strip()
    branch = BRANCHES_BY_LOWER.get(branch_input.lower())
    if branch is None:
        print(f"Unknown branch '{branch_input}'. Must be one of: {', '.join(BRANCHES)}", file=sys.stderr)
        return 1

    streets = [s.strip() for s in sys.argv[3:] if s.strip()]
    if not streets:
        print("Provide at least one street name to watch.", file=sys.stderr)
        return 1

    subscribers = load_subscribers()
    existing = next(
        (
            s
            for s in subscribers
            if s.get("email", "").lower() == email.lower() and s.get("branch", "").lower() == branch.lower()
        ),
        None,
    )
    if existing:
        merged = sorted(set(existing.get("streets", [])) | set(streets))
        existing["streets"] = merged
        print(f"Updated {email} ({branch}): watching {merged}")
    else:
        subscribers.append({"email": email, "branch": branch, "streets": streets})
        print(f"Added {email} ({branch}): watching {streets}")

    save_subscribers(subscribers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
