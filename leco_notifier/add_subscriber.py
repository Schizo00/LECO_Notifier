"""CLI to add or update a subscriber.

Usage:
    poetry run leco-add-subscriber user@example.com "Kandewatta Rd" "Wackwella Rd"
"""

import sys

from .store import load_subscribers, save_subscribers


def main() -> int:
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <email> <street1> [street2 ...]", file=sys.stderr)
        return 1

    email = sys.argv[1].strip()
    streets = [s.strip() for s in sys.argv[2:] if s.strip()]

    subscribers = load_subscribers()
    existing = next((s for s in subscribers if s.get("email", "").lower() == email.lower()), None)
    if existing:
        merged = sorted(set(existing.get("streets", [])) | set(streets))
        existing["streets"] = merged
        print(f"Updated {email}: watching {merged}")
    else:
        subscribers.append({"email": email, "streets": streets})
        print(f"Added {email}: watching {streets}")

    save_subscribers(subscribers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
