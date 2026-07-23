"""
Canonical landing-page headline A/B variants.

Single source of truth shared by the landing page (which renders them) and the
analytics service (which validates inbound tracking events against them). Keeping
them here prevents the public /track endpoint from being poisoned with arbitrary
``headline`` values that could otherwise bias best-headline selection or deface
the live H1.
"""

HEADLINES: list[str] = [
    "Something Doesn\u2019t Add Up\u2026 And You Know It.",
    "The Earliest Christians Didn\u2019t Believe What You Think",
    "What If What You Believe About Salvation Is Incomplete?",
]

HEADLINES_SET = frozenset(HEADLINES)
