"""Multilingual corpus regression check for the seeker-intent gate.

``test_intent_corpus_regression.py`` pins English behavior; this test does
the same for the non-English signal lists (Spanish/French/Portuguese, plus
German/Italian samples). The field risk here is the *opposite* direction:
the multilingual lists include very common words ("como", "que", "fe",
"verdad", "salut" — also French for "hi"), so ordinary non-English chatter
(praise, greetings, debate, testimony) could flood the review queue with
false positives if a weight or word list drifts.

This test scores a labeled fixture corpus
(``tests/fixtures/intent_corpus_multilingual.json``) and enforces:

  * seeker recall  >= SEEKER_RECALL_TARGET   (real non-English seekers get saved)
  * spam rejection == 1.0                     (negative gate stays absolute)
  * chatter rejection >= CHATTER_REJECTION_TARGET (common chatter stays out)

To extend: add new examples to the matching list in the JSON fixture.
"""

import json
from pathlib import Path

from app.services.lead_discovery_service import SAVE_THRESHOLD, score_intent

FIXTURE = Path(__file__).parent / "fixtures" / "intent_corpus_multilingual.json"

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
    assert len(CORPUS["chatter"]) >= 25


def test_multilingual_seeker_recall_meets_target():
    seekers = CORPUS["seeker"]
    misses = [(t, score_intent(t)) for t in seekers if score_intent(t) < SAVE_THRESHOLD]
    recall = 1 - len(misses) / len(seekers)
    assert recall >= SEEKER_RECALL_TARGET, (
        f"Multilingual seeker recall dropped to {recall:.2f} (target {SEEKER_RECALL_TARGET}). "
        f"These real-seeker comments would now be silently dropped: {misses}"
    )


def test_multilingual_spam_rejection_is_absolute():
    leaked = [(t, score_intent(t)) for t in CORPUS["spam"] if score_intent(t) != 0.0]
    assert not leaked, f"Non-English spam comments scored above 0.0: {leaked}"


def test_multilingual_chatter_rejection_meets_target():
    # THE core guarantee of this file: common non-English chatter built from
    # everyday words that overlap the signal lists ("como", "que", "fe",
    # "verdad", "salut") must not flood the lead queue.
    chatter = CORPUS["chatter"]
    leaked = [(t, score_intent(t)) for t in chatter if score_intent(t) >= SAVE_THRESHOLD]
    rejection = 1 - len(leaked) / len(chatter)
    assert rejection >= CHATTER_REJECTION_TARGET, (
        f"Multilingual chatter rejection dropped to {rejection:.2f} "
        f"(target {CHATTER_REJECTION_TARGET}). These ordinary non-English "
        f"comments would now flood the review queue: {leaked}"
    )


def test_multilingual_seeker_scores_have_headroom():
    # Early-warning canary, mirroring the English corpus test: the mean score
    # of passing multilingual seekers must sit comfortably above the cutoff.
    passing = [s for s in (score_intent(t) for t in CORPUS["seeker"]) if s >= SAVE_THRESHOLD]
    assert passing, "no multilingual seeker cleared the threshold at all"
    mean_score = sum(passing) / len(passing)
    assert mean_score >= SAVE_THRESHOLD + 0.05, (
        f"Mean passing multilingual-seeker score {mean_score:.3f} is hugging "
        f"the {SAVE_THRESHOLD} cutoff — a small future tweak would start "
        "dropping real non-English seekers."
    )
