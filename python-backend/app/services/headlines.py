"""
Canonical landing-page headline A/B variants.

Single source of truth shared by the landing page (which renders them) and the
analytics service (which validates inbound tracking events against them). Keeping
them here prevents the public /track endpoint from being poisoned with arbitrary
``headline`` values that could otherwise bias best-headline selection or deface
the live H1.
"""

HEADLINES: list[str] = [
    "Most Christians Were Never Told This About Salvation\u2026",
    "What If What You Believe About Salvation Is Incomplete?",
    "The Truth About Salvation Was Never Meant to Be Hidden",
    "Something Doesn\u2019t Add Up\u2026 And Deep Down, You Know It",
    "The Earliest Christians Didn\u2019t Believe What You Think",
]

HEADLINES_SET = frozenset(HEADLINES)
