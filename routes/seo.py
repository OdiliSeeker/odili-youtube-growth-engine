"""
SEO engine routes (spec PART 3 / PART 5) — all admin-only (x-api-key).

    POST   /seo/keywords          topic → 10 search queries
    POST   /seo/video             topic → title / description / tags
    POST   /seo/article           topic → full article (saved to DB)
    GET    /seo/articles          list saved articles
    DELETE /seo/articles/{id}     delete an article
    GET    /seo/vote-suggestions  top-voted topics → keywords + content ideas (vote→content loop)

Deterministic-first + AI-enriched: generators never 402.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.services import seo_service

router = APIRouter(prefix="/seo", tags=["SEO Engine"])


class TopicIn(BaseModel):
    topic: str


class ArticleIn(BaseModel):
    topic: str
    video_url: str | None = None
    status: str | None = "published"


@router.post("/keywords")
async def seo_keywords(body: TopicIn, _: None = Depends(verify_admin)) -> dict:
    return await seo_service.generate_keywords(body.topic)


@router.post("/video")
async def seo_video(body: TopicIn, _: None = Depends(verify_admin)) -> dict:
    return await seo_service.generate_video_seo(body.topic)


@router.post("/article", status_code=201)
async def seo_article(
    body: ArticleIn, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    status = "draft" if (body.status or "").lower() == "draft" else "published"
    result = await seo_service.generate_article(db, body.topic, video_url=body.video_url, status=status)
    if result is None:
        raise HTTPException(status_code=400, detail="A topic is required.")
    return result


@router.get("/articles")
async def seo_articles(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    items = seo_service.list_articles(db)
    return {"count": len(items), "items": items}


@router.delete("/articles/{article_id}")
async def seo_delete_article(
    article_id: int, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    if not seo_service.delete_article(db, article_id):
        raise HTTPException(status_code=404, detail="Article not found.")
    return {"message": "Deleted."}


@router.get("/vote-suggestions")
async def seo_vote_suggestions(
    db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    """PART 5 — turn the community's top-voted topics (last 7 days) into an
    actionable content plan: SEO keywords + a content idea per topic. Newsletter
    drafts for these topics are auto-created by the email queue scheduler."""
    from datetime import datetime, timezone, timedelta
    from app.models.db_models import Topic, TopicVote

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    topics = db.query(Topic).filter(Topic.status.in_(("featured", "approved"))).all()
    ranked = []
    for t in topics:
        recent = (
            db.query(TopicVote)
            .filter(TopicVote.topic_id == t.id, TopicVote.created_at >= cutoff)
            .count()
        )
        ranked.append((recent, t))
    ranked.sort(key=lambda r: (r[0], r[1].votes), reverse=True)

    suggestions = []
    for recent, t in ranked[:5]:
        kw = await seo_service.generate_keywords(t.title)
        suggestions.append({
            "topic_id": t.id,
            "topic": t.title,
            "votes_total": t.votes,
            "votes_7d": recent,
            "keywords": kw["keywords"],
            "content_idea": f"Make a video + article answering: \"{t.title}\" — "
                            f"lead with the tension, resolve with Scripture and the Church Fathers.",
        })
    return {"count": len(suggestions), "suggestions": suggestions}
