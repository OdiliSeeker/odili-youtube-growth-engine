"""Corpus-based regression check for the seeker-intent gate.

The unit tests in ``test_score_intent.py`` pin individual scoring rules, but
the real field risk is *drift*: someone tweaks ``_SEEKER_PHRASES``,
``_FAITH_TERMS``, or a weight, and the average real seeker quietly slides
below ``SAVE_THRESHOLD`` — leads dry up with no signal until the admin
notices an empty queue weeks later.

This test scores a labeled fixture corpus of real-world-style comments
(``tests/fixtures/intent_corpus.json``) and enforces aggregate targets:

  * seeker recall  >= SEEKER_RECALL_TARGET   (real questions keep getting saved)
  * spam rejection == 1.0                     (negative gate stays absolute)
  * chatter rejection >= CHATTER_REJECTION_TARGET (low-signal noise stays out)

To extend: add new examples to the matching list in the JSON fixture. The
targets tolerate a small number of borderline misses so a single tricky new
example doesn't demand a scorer change — but a systemic drift trips them.
"""

import json
from pathlib import Path

import pytest

from app.services.lead_discovery_service import SAVE_THRESHOLD, score_intent

FIXTURE = Path(__file__).parent / "fixtures" / "intent_corpus.json"

SEEKER_RECALL_TARGET = 0.9
CHATTER_REJECTION_TARGET = 0.9


def _load_corpus() -> dict:
    with FIXTURE.open() as f:
        return json.load(f)


CORPUS = _load_corpus()


def test_corpus_is_well_formed():
    for label in ("seeker", "spam", "chatter"):
        assert label in CORPUS, f"corpus missing '{label}' list"
        assert isinstance(CORPUS[label], list) and CORPUS[label]
        assert all(isinstance(t, str) and t.strip() for t in CORPUS[label])
    # Keep the corpus meaningful — a shrunken corpus weakens the guarantee.
    assert len(CORPUS["seeker"]) >= 20
    assert len(CORPUS["spam"]) >= 10
    assert len(CORPUS["chatter"]) >= 10


def test_seeker_recall_meets_target():
    seekers = CORPUS["seeker"]
    misses = [(t, score_intent(t)) for t in seekers if score_intent(t) < SAVE_THRESHOLD]
    recall = 1 - len(misses) / len(seekers)
    assert recall >= SEEKER_RECALL_TARGET, (
        f"Seeker recall dropped to {recall:.2f} (target {SEEKER_RECALL_TARGET}). "
        f"These real-seeker comments would now be silently dropped: {misses}"
    )


def test_spam_rejection_is_absolute():
    # The negative gate must never award points to spam/self-promotion.
    leaked = [(t, score_intent(t)) for t in CORPUS["spam"] if score_intent(t) != 0.0]
    assert not leaked, f"Spam comments scored above 0.0: {leaked}"


def test_chatter_rejection_meets_target():
    chatter = CORPUS["chatter"]
    leaked = [(t, score_intent(t)) for t in chatter if score_intent(t) >= SAVE_THRESHOLD]
    rejection = 1 - len(leaked) / len(chatter)
    assert rejection >= CHATTER_REJECTION_TARGET, (
        f"Chatter rejection dropped to {rejection:.2f} (target {CHATTER_REJECTION_TARGET}). "
        f"These low-signal comments would now flood the review queue: {leaked}"
    )


# The messy-formatting variants (emoji, smart quotes, ALL CAPS, ellipsis,
# em dash, newlines, fullwidth ？) sit at the tail of the seeker list. Unlike
# the aggregate recall target, EVERY one of these must clear the gate — they
# exist to pin the normalization layer in score_intent.
MESSY_VARIANTS = CORPUS["seeker"][-10:]


@pytest.mark.parametrize("comment", MESSY_VARIANTS)
def test_messy_formatting_variant_clears_threshold(comment):
    score = score_intent(comment)
    assert score >= SAVE_THRESHOLD, (
        f"Messy-formatting seeker comment scored {score} < {SAVE_THRESHOLD}: {comment!r}"
    )


def test_seeker_scores_have_headroom():
    # Early-warning canary: even while recall holds, a weight tweak that pushes
    # the *average* saved seeker toward the cliff should be visible. The mean
    # score of the seekers that clear the gate must sit comfortably above it.
    passing = [s for s in (score_intent(t) for t in CORPUS["seeker"]) if s >= SAVE_THRESHOLD]
    assert passing, "no seeker cleared the threshold at all"
    mean_score = sum(passing) / len(passing)
    assert mean_score >= SAVE_THRESHOLD + 0.05, (
        f"Mean passing-seeker score {mean_score:.3f} is hugging the {SAVE_THRESHOLD} "
        "cutoff — a small future tweak would start dropping real seekers."
    )
