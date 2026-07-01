from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator

VALID_SIGNUP_SOURCES = {"landing_page", "voter", "contributor"}


class IdeaRequest(BaseModel):
    topic: str


class IdeaResponse(BaseModel):
    viral_title: str
    hook: str
    short_script: str
    hook_intensity_score: int = 0


class EmailRequest(BaseModel):
    email: EmailStr


class SubscribeRequest(BaseModel):
    email: EmailStr
    interest: str | None = None
    source: str | None = None

    @field_validator("source")
    @classmethod
    def _clean_source(cls, v: str | None) -> str | None:
        if not v:
            return None
        v = v.strip().lower()
        return v if v in VALID_SIGNUP_SOURCES else None


class EmailListResponse(BaseModel):
    emails: list[str]
    count: int


class PlaylistRequest(BaseModel):
    text: str


class PlaylistResponse(BaseModel):
    playlist: str


class HealthResponse(BaseModel):
    status: str


class NewsletterSkippedResponse(BaseModel):
    status: str
    reason: str
    detail: str


class NewsletterSentResponse(BaseModel):
    status: str
    subject: str
    recipients_total: int
    sent: int
    failed: int
    failures: list[dict] | None = None


class NewsletterLogEntry(BaseModel):
    id: int
    sent_at: str
    subject: str
    recipients_total: int
    sent: int
    failed: int
    triggered_by: str
    failures: list[dict]


class AdminStatusResponse(BaseModel):
    status: str
    version: str
    subscriber_count: int
    scheduler_running: bool
    send_today: bool
    next_send_day: str
    last_newsletter: NewsletterLogEntry | None = None
