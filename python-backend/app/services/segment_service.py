"""
Email segmentation by subscriber interest.

Each subscriber arrives via a topic button (or "Other"), which stores their
``interest``. Instead of hand-writing a full email per interest × per drip
step (30+ variants), we inject ONE interest-aware opening line into every drip
email. This keeps the proven drip copy intact while making each message feel
personal to what drew the visitor in. Unknown / missing interest → general line.
"""

# Map of interest → a focused opening line for the drip emails.
_ANGLES = {
    "salvation": (
        "Since you came seeking the truth about <strong>salvation</strong>, "
        "let's start at the very heart of it."
    ),
    "eucharist": (
        "You're here for the truth about the <strong>Eucharist</strong> — "
        "what the first Christians really believed about the bread and wine."
    ),
    "papacy": (
        "You wanted clarity on the <strong>Papacy</strong> — where the authority "
        "of Peter comes from, and why it still matters."
    ),
    "mary & saints": (
        "You came with questions about <strong>Mary and the Saints</strong> — "
        "and the Scriptural roots most people never hear."
    ),
    "false doctrines": (
        "You're here to tell truth from error. Let's expose the "
        "<strong>false doctrines</strong> that lead so many astray."
    ),
    "other": (
        "Whatever first drew you here, you're seeking the truth — and that's "
        "exactly where this journey begins."
    ),
}

_GENERAL = (
    "You're seeking the truth — and that's exactly where this journey begins."
)


def segment_line(interest: str | None) -> str:
    """A single interest-aware opening line (already HTML-safe, no user input)."""
    if not interest:
        return _GENERAL
    return _ANGLES.get(interest.strip().lower(), _GENERAL)
