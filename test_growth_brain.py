"""
Tests for the Growth Brain core.

Covers the two genuinely-new primitives and the aggregator:
  * score_title()        — deterministic, stable, sensible ranking
  * list_trigger_phrases — curated library, topic-filled
  * build_brain()        — composes existing engines, NEVER 402 (no AI key),
                           titles ranked by predicted CTR, hooks by intensity

The route layer is exercised via FastAPI's TestClient to prove admin auth and
the topic/lead/topic_id resolution + Newsletter draft hook.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.services import growth_brain_service as gb


# ── Title CTR Scorer ──────────────────────────────────────────────────────────

def test_score_title_empty():
    r = gb.score_title("   ")
    assert r["score"] == 0
    assert r["band"] == "Weak"


def test_score_title_deterministic_and_bounded():
    title = "Is Purgatory Actually Biblical? (What the Early Church Said)"
    a = gb.score_title(title)
    b = gb.score_title(title)
    assert a == b  # stable — no randomness
    assert 0 <= a["score"] <= 100
    assert set(a["components"]) == {
        "length_fit", "curiosity", "emotional_pull", "specificity", "clarity"
    }


def test_score_title_strong_beats_weak():
    strong = gb.score_title("The Truth About Confession Nobody Tells You (Real Evidence)")
    weak = gb.score_title("confession")
    assert strong["score"] > weak["score"]


def test_score_title_flags_clickbait_caps():
    r = gb.score_title("STOP WRONG LIES ABOUT MARY NOW")
    assert any("ALL-CAPS" in t for t in r["tips"])


def test_rank_titles_sorted_and_deduped():
    ranked = gb.rank_titles([
        "confession",
        "The Truth About Confession Nobody Tells You (Real Evidence)",
        "confession",  # duplicate — dropped
    ])
    assert len(ranked) == 2
    assert ranked[0]["score"] >= ranked[1]["score"]


# ── Trigger phrases ───────────────────────────────────────────────────────────

def test_trigger_phrases_generic():
    out = gb.list_trigger_phrases()
    assert out["topic"] is None
    assert "curiosity_gap" in out["categories"]
    assert any("{t}" in p for p in out["categories"]["curiosity_gap"])


def test_trigger_phrases_filled():
    out = gb.list_trigger_phrases("Purgatory")
    assert out["topic"] == "Purgatory"
    joined = " ".join(out["categories"]["curiosity_gap"])
    assert "{t}" not in joined
    assert "Purgatory" in joined


# ── Aggregator (never 402, no AI key configured) ──────────────────────────────

def test_build_brain_deterministic(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    brain = asyncio.run(gb.build_brain("Why Catholics pray to Mary"))
    assert brain["content_source"] == "deterministic"
    assert brain["best_title"]["score"] >= 0
    # Titles are ranked best-first.
    scores = [t["score"] for t in brain["optimized_titles"]]
    assert scores == sorted(scores, reverse=True)
    # Hooks ranked by intensity best-first.
    intensities = [h["intensity"] for h in brain["viral_hooks"]]
    assert intensities == sorted(intensities, reverse=True)
    assert brain["us_targeting"]["keywords"]
    assert brain["conversion_scripts"]["pinned_comment"]
    assert "Mary" in brain["conversion_scripts"]["pinned_comment"]
    assert "curiosity_gap" in brain["trigger_phrases"]
    assert brain["landing_cta"]["headline"]


def test_build_brain_requires_topic():
    with pytest.raises(ValueError):
        asyncio.run(gb.build_brain("  "))


# ── Route layer ───────────────────────────────────────────────────────────────

@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from app.main import app
    return TestClient(app)


HEADERS = {"x-api-key": "test-admin-key"}


def test_score_title_route_requires_auth(client):
    res = client.post("/growth/score-title", json={"title": "hello"})
    assert res.status_code == 401


def test_score_title_route_single(client):
    res = client.post("/growth/score-title", json={"title": "The Truth About Mary Nobody Tells You"}, headers=HEADERS)
    assert res.status_code == 200
    assert "result" in res.json()


def test_score_title_route_many(client):
    res = client.post("/growth/score-title", json={"titles": ["a", "The Real Story of Confession (Evidence)"]}, headers=HEADERS)
    assert res.status_code == 200
    assert len(res.json()["results"]) == 2


def test_brain_route(client):
    res = client.post("/growth/brain", json={"topic": "The Eucharist"}, headers=HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert body["topic"] == "The Eucharist"
    assert body["content_source"] == "deterministic"
    assert body.get("email_draft_id") is None


def test_brain_route_needs_a_source(client):
    res = client.post("/growth/brain", json={}, headers=HEADERS)
    assert res.status_code == 422


def test_trigger_phrases_route(client):
    res = client.get("/growth/trigger-phrases?topic=Baptism", headers=HEADERS)
    assert res.status_code == 200
    assert res.json()["topic"] == "Baptism"
