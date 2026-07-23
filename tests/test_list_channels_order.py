"""list_channels must order watched channels by pending-lead count desc,
breaking ties by newest-first, with 0-pending channels at the bottom."""

from datetime import datetime, timedelta

from app.models.db_models import LeadComment, WatchlistChannel
from app.services import lead_discovery_service as lds


def _add_channel(db, n, created_at):
    ch = WatchlistChannel(
        channel_id="UC" + str(n) * 22,
        handle=f"@ch{n}",
        title=f"Channel {n}",
        uploads_playlist_id="UU" + str(n) * 22,
        category="general",
        created_at=created_at,
    )
    db.add(ch)
    db.commit()
    return ch


def _add_pending(db, ch, count):
    for i in range(count):
        db.add(LeadComment(
            channel_id=ch.channel_id,
            video_id="vid" + str(i),
            comment_id=f"c-{ch.channel_id}-{i}",
            author="a",
            text="how do I find truth?",
            intent_score=0.8,
            review_status="pending",
        ))
    db.commit()


def test_channels_sorted_by_pending_desc_tie_newest_first(db):
    base = datetime(2026, 1, 1)
    oldest = _add_channel(db, 1, base)                       # 2 pending
    middle = _add_channel(db, 2, base + timedelta(days=1))   # 0 pending
    newest = _add_channel(db, 3, base + timedelta(days=2))   # 2 pending (tie)
    busiest = _add_channel(db, 4, base + timedelta(days=3))  # 5 pending

    _add_pending(db, oldest, 2)
    _add_pending(db, newest, 2)
    _add_pending(db, busiest, 5)

    out = lds.list_channels(db)
    assert [c["title"] for c in out] == [
        "Channel 4",  # most pending first
        "Channel 3",  # tie: newer wins
        "Channel 1",
        "Channel 2",  # 0 pending at bottom
    ]
    assert [c["pending_leads"] for c in out] == [5, 2, 2, 0]
