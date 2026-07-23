"""Tests for the near-miss ("closest keepers") preview in
``lead_discovery_service.count_bulk_skip_leads``: only pending leads at or
above the cutoff are returned, lowest score first, capped at 3.
"""

from app.models.db_models import LeadComment
from app.services import lead_discovery_service as lds


def _lead(db, comment_id, score, status="pending", text="Sample comment text", author="Seeker"):
    lead = LeadComment(
        comment_id=comment_id,
        video_id="vid1",
        channel_id="UCchan1",
        author=author,
        text=text,
        intent_score=score,
        review_status=status,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def test_near_misses_are_lowest_pending_at_or_above_cutoff(db):
    _lead(db, "below", 0.62)
    at_cutoff = _lead(db, "at", 0.70)
    _lead(db, "high1", 0.72)
    _lead(db, "high2", 0.75)
    _lead(db, "high3", 0.80)
    _lead(db, "approved", 0.71, status="approved")
    _lead(db, "skipped", 0.71, status="skipped")

    d = lds.count_bulk_skip_leads(db, 0.70)

    assert d["count"] == 1
    scores = [m["score"] for m in d["near_misses"]]
    assert len(scores) == 3  # capped at 3
    assert scores == sorted(scores)  # lowest first
    assert d["near_misses"][0]["id"] == at_cutoff.id  # == cutoff is a keeper
    ids = {m["id"] for m in d["near_misses"]}
    assert 0.80 not in scores  # only the 3 closest survive the cap
    assert all("snippet" in m and "author" in m for m in d["near_misses"])
    assert at_cutoff.id in ids


def test_near_misses_empty_when_no_keepers(db):
    _lead(db, "low1", 0.61)
    _lead(db, "low2", 0.65)

    d = lds.count_bulk_skip_leads(db, 0.70)

    assert d["count"] == 2
    assert d["near_misses"] == []


def test_near_miss_snippet_truncated(db):
    _lead(db, "long", 0.75, text="x" * 500)

    d = lds.count_bulk_skip_leads(db, 0.70)

    assert len(d["near_misses"]) == 1
    assert len(d["near_misses"][0]["snippet"]) == 120
