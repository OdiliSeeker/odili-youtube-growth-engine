"""Tests for the retry-safety of ``lead_discovery_service.approve_lead``.

``approve_lead`` is NOT a single transaction — it creates a Topic, a
PipelineItem, and an EmailQueue draft across several commits, plus a
deterministic AI content pack. The durable rule
(``.agents/memory/lead-discovery-quota-and-scan.md``) is that running it twice
must reuse the existing artifacts, never duplicate them.

The AI enrichment and comment-reply helpers are stubbed so no network / OpenAI
calls happen and the deterministic pack is used.
"""

import pytest

from app.models.db_models import EmailQueue, LeadComment, PipelineItem, Topic
from app.services import lead_discovery_service as lds

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _stub_ai(monkeypatch):
    async def _no_ai(_prompt):
        raise RuntimeError("AI disabled in tests")

    async def _no_reply(_text, **k):
        return {}

    # generate_with_ai is imported lazily inside _generate_content_pack.
    import app.services.ai_service as ai_service
    monkeypatch.setattr(ai_service, "generate_with_ai", _no_ai)

    import app.services.conversion_engine as conversion_engine
    monkeypatch.setattr(conversion_engine, "generate_comment_reply", _no_reply)


def _make_lead(db):
    lead = LeadComment(
        comment_id="cid-approve-1",
        video_id="vidX",
        channel_id="UCX",
        author="Seeker Sam",
        text="How do I become Catholic? I want to convert but I'm confused.",
        intent_score=0.9,
        review_status="pending",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


async def test_approve_creates_artifacts_once(db):
    lead = _make_lead(db)
    result = await lds.approve_lead(db, lead.id)

    assert result is not None
    assert result["content_source"] == "deterministic"

    db.expire_all()
    assert db.query(Topic).filter(Topic.source == "youtube_lead").count() == 1
    assert db.query(PipelineItem).count() == 1
    assert db.query(EmailQueue).filter(EmailQueue.source == "lead_discovery").count() == 1

    lead = db.get(LeadComment, lead.id)
    assert lead.review_status == "approved"
    assert lead.generated_content


async def test_approve_twice_is_idempotent(db):
    lead = _make_lead(db)

    first = await lds.approve_lead(db, lead.id)
    assert first is not None

    # Second approve should short-circuit (already approved with a pack).
    second = await lds.approve_lead(db, lead.id)
    assert second is not None
    assert second.get("already_approved") is True

    db.expire_all()
    assert db.query(Topic).filter(Topic.source == "youtube_lead").count() == 1
    assert db.query(PipelineItem).count() == 1
    assert db.query(EmailQueue).filter(EmailQueue.source == "lead_discovery").count() == 1


async def test_approve_retry_after_partial_does_not_duplicate(db):
    """Simulate a crash after the pack/topic were created but before the lead
    was marked approved (so the early short-circuit does NOT apply). Re-running
    must reuse the Topic/PipelineItem/draft rather than duplicate them."""
    lead = _make_lead(db)

    # First full approve creates all artifacts.
    await lds.approve_lead(db, lead.id)

    # Emulate a partial run: clear the approval markers so the second call
    # re-enters the full body instead of short-circuiting.
    lead = db.get(LeadComment, lead.id)
    lead.review_status = "pending"
    lead.generated_content = None
    db.commit()

    await lds.approve_lead(db, lead.id)

    db.expire_all()
    assert db.query(Topic).filter(Topic.source == "youtube_lead").count() == 1
    assert db.query(PipelineItem).count() == 1
    assert db.query(EmailQueue).filter(EmailQueue.source == "lead_discovery").count() == 1


async def test_approve_missing_lead_returns_none(db):
    assert await lds.approve_lead(db, 999999) is None
