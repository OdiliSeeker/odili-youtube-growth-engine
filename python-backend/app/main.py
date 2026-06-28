import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.startup import validate_environment
from app.db import init_db
from app.services.auto_scheduler import start_scheduler, stop_scheduler
from app.routes import health, ideas, playlist, emails, newsletter, admin, admin_ui, unsubscribe, subscribe_ui, youtube, scripts, youtube_packages, landing, growth, topics, news, featured, analytics, content

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    logger.info("Starting Odili Truth Seeker Backend v1.2.0")
    try:
        validate_environment()
    except RuntimeError as exc:
        logger.critical("%s", exc)
        raise SystemExit(1) from exc

    init_db()
    logger.info("Database initialised.")

    start_scheduler()

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    stop_scheduler()
    logger.info("Server shutdown complete.")


app = FastAPI(
    title="Odili Truth Seeker Backend",
    description=(
        "Modular FastAPI backend powering the Odili Truth Seeker Catholic media ministry. "
        "AI content generation · Playlist routing · Persistent subscriber management · "
        "Automated weekly newsletter via SendGrid · Welcome emails · One-click unsubscribe · Full send history."
    ),
    version="1.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


app.include_router(landing.router)
app.include_router(health.router)
app.include_router(ideas.router)
app.include_router(playlist.router)
app.include_router(emails.router)
app.include_router(newsletter.router)
app.include_router(admin.router)
app.include_router(admin_ui.router)
app.include_router(unsubscribe.router)
app.include_router(subscribe_ui.router)
app.include_router(youtube.router)
app.include_router(scripts.router)
app.include_router(youtube_packages.router)
app.include_router(growth.router)
app.include_router(topics.router)
app.include_router(news.router)
app.include_router(featured.router)
app.include_router(analytics.router)
app.include_router(content.router)
