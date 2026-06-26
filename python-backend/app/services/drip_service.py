"""
Automated 5-email evangelization drip sequence.

When a visitor subscribes they receive a timed sequence of branded emails that
deepen engagement and drive them back to YouTube:

    Email 1 — immediate (welcome)
    Email 2 — +1 day
    Email 3 — +3 days
    Email 4 — +5 days
    Email 5 — +7 days

State lives in the database (``Subscriber.drip_step``) so the sequence survives
server restarts and never double-sends. A periodic scheduler job
(:func:`process_due_drips`) advances each subscriber one step at a time as each
email comes due.

IMPORTANT: drip emails only fire while the server is running. Reliable delivery
therefore requires an always-on deployment (Reserved VM), not a scale-to-zero
one — see the warning logged by the scheduler at startup.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.db_models import Subscriber

logger = logging.getLogger(__name__)

# Day offset (from subscription) at which each email is due. Index = email - 1.
DRIP_OFFSETS_DAYS = [0, 1, 3, 5, 7]
TOTAL_STEPS = len(DRIP_OFFSETS_DAYS)


def _video_link() -> str:
    """A YouTube link carrying email→YouTube conversion tracking."""
    from app.services.newsletter_service import YOUTUBE_URL, _with_email_tracking

    return _with_email_tracking(YOUTUBE_URL)


def _p(text: str) -> str:
    return f'<p style="font-size:15px;margin:0 0 16px">{text}</p>'


def _inline_cta(label: str) -> str:
    """A secondary in-body gold link to YouTube (the shell already has the big CTA)."""
    return (
        f'<p style="margin:22px 0 4px">'
        f'<a href="{_video_link()}" '
        f'style="color:#FFD700;font-weight:bold;text-decoration:none">{label} &rarr;</a>'
        f"</p>"
    )


# ── The sequence ───────────────────────────────────────────────────────────
# Each entry: subject, eyebrow, title, and a builder for the inner HTML body.
def _seq() -> list[dict]:
    return [
        {
            "subject": "You asked for truth. Here it is.",
            "eyebrow": "Welcome",
            "title": "You asked for truth. Here it is.",
            "inner": (
                _p("Peace be with you — and welcome to <strong>Odili, The Seeker of Truth</strong>.")
                + _p(
                    "This isn't just another newsletter. It's a mission: to defend the truth of "
                    "the Catholic faith, expose error, and lead souls back to Christ."
                )
                + _p("Your first teaching is waiting. Start where the journey begins:")
                + _inline_cta("Watch the first teaching")
            ),
        },
        {
            "subject": "Most people get this wrong...",
            "eyebrow": "Common Misconception",
            "title": "Most people get this wrong...",
            "inner": (
                _p(
                    "Here's something most people — even lifelong believers — get wrong: they "
                    "treat faith as a feeling instead of the truth it actually rests on."
                )
                + _p(
                    "Scripture and the witness of the early Church tell a clearer, bolder story "
                    "than most of us were ever taught. Once you see it, you can't unsee it."
                )
                + _inline_cta("See what most people miss")
            ),
        },
        {
            "subject": "This might challenge what you believe",
            "eyebrow": "Go Deeper",
            "title": "This might challenge what you believe",
            "inner": (
                _p("Fair warning: this one goes deeper.")
                + _p(
                    "Some of the hardest questions in the faith — about authority, salvation, and "
                    "what the first Christians truly believed — have answers most people never hear."
                )
                + _p("If you're ready to be challenged, this is for you:")
                + _inline_cta("Take on the hard questions")
            ),
        },
        {
            "subject": "You're not alone in this journey",
            "eyebrow": "Encouragement",
            "title": "You're not alone in this journey",
            "inner": (
                _p("Seeking the truth can feel lonely. It isn't.")
                + _p(
                    "Across the world, people just like you are rediscovering the depth, beauty, "
                    "and confidence of the Catholic faith — and standing firmer because of it."
                )
                + _p("Let this strengthen you today:")
                + _inline_cta("Be encouraged")
            ),
        },
        {
            "subject": "Now take the next step",
            "eyebrow": "Your Next Step",
            "title": "Now take the next step",
            "inner": (
                _p("You've come this far for a reason. Now make it count.")
                + _p(
                    "<strong>Subscribe on YouTube</strong> so you never miss a teaching, and "
                    "<strong>share</strong> the truth with someone who needs it. That's how the "
                    "mission grows — one soul at a time."
                )
                + _p("Defend the truth. Live the faith. Walk with us:")
                + _inline_cta("Subscribe and join the mission")
            ),
        },
    ]


def send_drip_email(to_email: str, idx: int) -> bool:
    """
    Render and send drip email at 0-based ``idx`` (0..4). Returns True on success.
    Uses the shared branded email shell (logo header + YouTube CTA + unsubscribe).
    """
    if idx < 0 or idx >= TOTAL_STEPS:
        logger.error("Drip: invalid email index %s", idx)
        return False

    from app.services.email_sender_service import send_email
    from app.services.newsletter_service import email_shell, _plain_text_footer
    from app.services.token_service import make_unsubscribe_url

    item = _seq()[idx]
    unsubscribe_url = make_unsubscribe_url(to_email)

    html_body = email_shell(
        eyebrow=item["eyebrow"],
        title=item["title"],
        inner_html=item["inner"],
    ).replace("{UNSUBSCRIBE_URL}", unsubscribe_url)

    # Plain-text fallback: strip tags crudely from the inner body.
    import re

    text_inner = re.sub(r"<[^>]+>", "", item["inner"]).strip()
    text_body = (
        f"{item['title']}\n\n{text_inner}\n\nWatch on YouTube: {_video_link()}"
        + _plain_text_footer()
    ).replace("{UNSUBSCRIBE_URL}", unsubscribe_url)

    result = send_email(
        to_email=to_email,
        subject=item["subject"],
        content=html_body,
        text_content=text_body,
    )
    if result.success:
        logger.info("Drip email %d sent to %s", idx + 1, to_email)
    else:
        logger.warning("Drip email %d failed for %s: %s", idx + 1, to_email, result.error)
    return result.success


def _claim_step(db: Session, sub_id: int, step: int) -> bool:
    """
    Atomically claim drip ``step`` for a subscriber via a compare-and-set
    UPDATE (``drip_step == step`` → ``step + 1``). Returns True only if THIS
    caller won the claim. SQLite serialises writes, so exactly one path —
    :func:`start_drip` or :func:`process_due_drips` — can ever claim a given
    step, which removes the step-0 race between them. The email is sent only by
    the winner, so no email is ever sent twice.
    """
    claimed = (
        db.query(Subscriber)
        .filter(
            Subscriber.id == sub_id,
            Subscriber.drip_step == step,
            Subscriber.active == True,  # noqa: E712
        )
        .update({Subscriber.drip_step: step + 1}, synchronize_session=False)
    )
    db.commit()
    return bool(claimed)


def _release_step(db: Session, sub_id: int, step: int) -> None:
    """
    Roll a claimed step back (``step + 1`` → ``step``) after a send failure so
    the email is retried on the next pass. Guarded on the post-claim value so it
    never clobbers progress made by another path in the meantime.
    """
    db.query(Subscriber).filter(
        Subscriber.id == sub_id,
        Subscriber.drip_step == step + 1,
    ).update({Subscriber.drip_step: step}, synchronize_session=False)
    db.commit()


def start_drip(email: str) -> None:
    """
    Kick off the sequence for a new subscriber: send email 1 immediately and
    advance the subscriber to step 1. Claims step 0 atomically, so it can never
    double-send the welcome email even if the scheduler fires concurrently.

    Designed to run as a fire-and-forget background task; opens its own session.
    """
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        sub = db.query(Subscriber).filter(Subscriber.email == email.strip().lower()).first()
        if not sub or not sub.active or sub.drip_step != 0:
            return
        if not _claim_step(db, sub.id, 0):
            return  # another path already claimed email 1
        if not send_drip_email(sub.email, 0):
            _release_step(db, sub.id, 0)  # send failed — let it retry
    except Exception as exc:
        logger.error("start_drip failed for %s: %s", email, exc, exc_info=True)
    finally:
        db.close()


def process_due_drips(db: Session) -> int:
    """
    Advance every active subscriber whose next drip email is now due, one step
    per call. State-driven and restart-safe: progress is read from and written
    to ``Subscriber.drip_step`` via an atomic compare-and-set claim, so no email
    is ever sent twice — even if :func:`start_drip` runs concurrently.

    Returns the number of emails sent this pass.
    """
    now = datetime.now(timezone.utc)
    subs = (
        db.query(Subscriber)
        .filter(Subscriber.active == True, Subscriber.drip_step < TOTAL_STEPS)  # noqa: E712
        .all()
    )

    sent = 0
    for sub in subs:
        step = sub.drip_step  # 0-based index of the next email to send
        base = sub.subscribed_at
        # SQLite reads tz-aware columns back as naive — normalise to UTC.
        if base is None:
            continue
        if base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)
        due_at = base + timedelta(days=DRIP_OFFSETS_DAYS[step])
        if now < due_at:
            continue
        # Atomically claim the step before sending; skip if another path won it.
        if not _claim_step(db, sub.id, step):
            continue
        if send_drip_email(sub.email, step):
            sent += 1
        else:
            _release_step(db, sub.id, step)  # send failed — retry next pass

    if sent:
        logger.info("Drip pass complete — %d email(s) sent.", sent)
    return sent
