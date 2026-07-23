import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from app.dependencies.auth import verify_admin
from app.models.schemas import IdeaRequest, IdeaResponse
from app.services.ai_service import generate_with_ai, AIQuotaError, AIAuthError, AIConnectionError, AIServiceError
from app.services.growth_service import boost_hook, score_hook_intensity
from app.services import news_service

logger = logging.getLogger(__name__)
router = APIRouter()

_IDEA_PROMPT_TEMPLATE = """
You are generating content for the Odili Truth Seeker Catholic media channel.

Topic: {topic}

STYLE (critical): Do NOT sound like a flat Bible lesson or generic teaching. Lead with TRUTH REVELATION, MYTH-BREAKING, SALVATION URGENCY, and IDENTITY (e.g. "What Christians were REALLY called"). Open a curiosity gap that makes the viewer NEED to keep watching. Stay faithful to authentic Catholic teaching.
{news_block}
Return ONLY a valid JSON object with exactly these three keys:
- "viral_title": A compelling, curiosity-driven title that reveals a truth or breaks a myth (max 12 words)
- "hook": A scroll-stopping opening hook that interrupts scrolling and creates tension in the first 5 seconds (1-2 sentences)
- "short_script": A 150-200 word script for a short video

No extra text, no markdown, no code fences. Pure JSON only.
"""


@router.post("/generate-idea", response_model=IdeaResponse, tags=["Content Generation"])
async def generate_idea(request: IdeaRequest, _: None = Depends(verify_admin)) -> IdeaResponse:
    """
    Generate a viral title, hook, and short script for the given topic
    using GPT-4o. Admin only — this is a private content-creation tool.
    """
    # Supportive (never authoritative) context: weave in current Catholic headlines
    # so ideas feel timely. Failure here must never block idea generation.
    news_block = ""
    try:
        titles = await news_service.headline_titles(limit=5)
        if titles:
            joined = "\n".join(f"  - {t}" for t in titles)
            news_block = (
                "\nCURRENT CATHOLIC HEADLINES (optional inspiration only — supportive "
                "context, never a doctrinal source; only use if naturally relevant):\n"
                f"{joined}\n"
            )
    except Exception as exc:  # noqa: BLE001
        logger.info("News context skipped for idea generation: %s", exc)

    prompt = _IDEA_PROMPT_TEMPLATE.format(topic=request.topic.strip(), news_block=news_block)

    try:
        raw = await generate_with_ai(prompt)
    except AIQuotaError as exc:
        raise HTTPException(status_code=402, detail={
            "error": "openai_quota_exceeded",
            "message": str(exc),
            "action": "Add credits at https://platform.openai.com/account/billing",
        }) from exc
    except AIAuthError as exc:
        raise HTTPException(status_code=401, detail={"error": "openai_auth_error", "message": str(exc)}) from exc
    except (AIConnectionError, AIServiceError) as exc:
        raise HTTPException(status_code=502, detail={"error": "openai_error", "message": str(exc)}) from exc

    try:
        data = json.loads(raw)
        viral_title = data["viral_title"]
        hook = data["hook"]
        short_script = data["short_script"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI returned an unexpected format: {str(exc)}. Raw: {raw[:300]}",
        ) from exc

    # Hook intensity booster: auto-regenerate a stronger first 5 seconds if weak.
    intensity = score_hook_intensity(hook)
    if intensity < 70:
        try:
            boosted = await boost_hook(request.topic.strip(), hook, short_script)
            hook = boosted["hook"] or hook
            intensity = boosted["hook_intensity_score"]
        except Exception as exc:  # noqa: BLE001 — boosting must never break generation
            logger.info("Hook boost skipped: %s", exc)

    return IdeaResponse(
        viral_title=viral_title,
        hook=hook,
        short_script=short_script,
        hook_intensity_score=intensity,
    )
