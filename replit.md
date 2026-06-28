# Odili Truth Seeker Backend

A Python FastAPI backend powering the Odili Truth Seeker Catholic media ministry. Handles AI-generated newsletter content, subscriber management, automated email delivery via SendGrid, and a built-in admin dashboard.

## Run & Operate

- `cd python-backend && python run.py` — start the backend (port 8000)
- Admin dashboard: `https://<REPLIT_DEV_DOMAIN>:8000/admin`
- API docs: `https://<REPLIT_DEV_DOMAIN>:8000/docs`

## Stack

- Python 3.11, FastAPI, Uvicorn
- SQLite via SQLAlchemy (persistent, at `python-backend/data/odili.db`)
- SendGrid (email delivery)
- OpenAI GPT-4o (AI newsletter generation — requires billing)
- APScheduler (auto-send Sun/Wed/Fri 09:00 UTC)

## Where things live

- `python-backend/app/routes/` — all API route handlers
- `python-backend/app/services/` — business logic (email, AI, scheduler, tokens)
- `python-backend/app/models/` — SQLAlchemy DB models + Pydantic schemas
- `python-backend/app/dependencies/auth.py` — `verify_admin` dependency
- `python-backend/data/odili.db` — SQLite database (Subscriber + NewsletterLog tables)

## API Endpoints

### Public (the evangelization funnel — no auth)
- `GET /` — public landing page: conversion-first evangelization funnel in a fixed 8-section order — (1) Hero with an ANIMATED VIDEO LOGO at top-center (HTML5 `<video class="hero-logo" autoplay muted loop playsinline>` sourcing `/static/animated-logo.mp4`, poster=`/static/logo.png` fallback, max-width 140px, floaty bob + warm glow) — replaces the old static `<img>` logo, (2) email capture directly under hero, (3) "Start Here: The Truth About Salvation" video section that ROTATES the intro YouTube video so returning visitors see the OTHER video (client-side over `INTRO_VIDEO_IDS` = [`FEATURED_VIDEO_ID` default `Bm2aoEcEIPk`, `nY-N2JnuvG8`]; remembers `localStorage.lastVideo` and picks a different id next visit, first visit random; JS sets the iframe `src` + thumbnail bg + fallback href at load and fires a `video_loaded` track event). The hero `<h1 id="main-headline">` runs HEADLINE A/B TESTING: on load it fetches `GET /analytics/best-headline` and uses the auto-winner if one exists, else picks a per-visitor variant from the shared headline set and persists it in `localStorage.headline_variant` (returning visitors keep their variant). Behavior tracking fires `POST /track` events throughout (page_view, cta_click hero/mid/final, topic_click, video_loaded, scroll_depth 25/50/75/100, headline_variant, and signup on subscribe success with {headline, interest}), with a clickable poster fallback, (4) 5 fixed topic buttons (Salvation / Eucharist / Papacy / Mary & Saints / False Doctrines) that prefill a hidden `interest` field + scroll to email capture, (5) "What You'll Discover" value bullets, (6) Authority ("Rooted in Scripture, Tradition, and 2,000 years of Catholic teaching"), then the voting/request engagement system (relabeled "Ask a Question or Suggest a Topic", kept as a working public feature), (7) Final CTA ("New teachings released weekly — don't miss the truth."), (8) Footer (brand "Odili — The Seeker of Truth" + YouTube). Black/gold theme, mobile responsive. NO growth/AI/admin wording or links.
- `GET /health` — health check
- `POST /subscribe` — public funnel subscribe: stores topic `interest` (optional) + starts the 5-email drip sequence (email 1 sends immediately)
- `POST /emails` — subscribe (triggers welcome email + starts drip sequence)
- `GET /unsubscribe?email=&token=` — one-click unsubscribe (HMAC verified)
- `GET /playlist` — YouTube channel routing
- `GET /topics` — list public (approved/featured) topics with vote counts + `trending` flag
- `POST /topics/{id}/vote` — vote for a topic (deduped per visitor IP, idempotent)
- `POST /topics/request` — visitor submits a topic (lands as 'suggested' for review)
- `GET /featured-content` — admin-curated content hub: `{shorts:[{id,title}], playlists:[{title,url}], community_url}` (empty-safe defaults)
- `POST /track` — public funnel behavior event (allow-listed names only: page_view/cta_click/topic_click/video_loaded/scroll_depth/headline_variant/signup; `headline` validated against the real A/B set, scroll `percent` clamped to 25/50/75/100, payload size-capped — hardened against poisoning)
- `GET /analytics/best-headline` — auto-selected best-converting headline, or `{best_headline: null}` → landing falls back to per-visitor A/B

### Admin (require `x-api-key` header)
- `GET /newsletter/history` — send history (admin-only)
- `POST /send-newsletter/preview` — newsletter HTML preview (admin-only)
- `POST /generate-idea` — AI viral title/hook/script (admin-only)
- `POST /subscribers/import` — bulk CSV import (admin-only)
- `GET /topics/all` — list every topic incl. pending visitor requests
- `POST /topics` — curate a topic
- `PATCH /topics/{id}` — approve/feature/archive or edit a topic
- `POST /topics/reorder` — persist topic display order (body `{ordered_ids:[...]}` → sets `sort_order`)
- `DELETE /topics/{id}` — delete a topic and its votes
- `GET /news` — Catholic news headlines (RSS aggregate: Vatican News / CNA / EWTN; cached, graceful fallback)
- `POST /news/refresh` — force-refresh the news cache
- `PUT /featured-content` — save the admin-curated content hub (shorts/playlists/community_url)
- Admin dashboard "Content Hub" tab — curate featured Shorts/Playlists/Community + view/refresh Catholic news (served inside the `/admin` SPA)
- `POST /send-newsletter` — AI-generated newsletter send
- `POST /send-newsletter/custom` — custom newsletter send (no AI needed)
- `POST /send-newsletter/custom/preview` — preview custom newsletter HTML
- `GET /admin/status` — system health + subscriber count
- `GET /analytics/summary` — funnel metrics (total_visits, cta_clicks, subscriptions=signup events, conversion_rate, top_headlines, top_topics by signup interest, topic_clicks, scroll_depth); optional `?days=N` window
- Admin dashboard "📊 Analytics" tab — visits/CTA-clicks/signups/conversion cards + headline performance + top topics + scroll-depth bars (admin-only, served inside the `/admin` SPA)
- Admin dashboard "YouTube Playbook" tab — static reference: channel banner text, channel section ordering, Hook→Build→Deliver→CTA video structure, and title/thumbnail/description best practices (admin-only, served inside the `/admin` SPA)
- `GET /emails` — list all active subscribers
- `DELETE /emails/{email}` — remove a subscriber
- `GET /subscribers/export` — download subscribers CSV
- `POST /subscribers/import` — bulk CSV import

### Viral Conversion Layer (require `x-api-key` header)
- `POST /growth/score-topic` — virality_score (0-100) + sub-scores (curiosity/controversy/emotional/search) + Use/Improve/Avoid recommendation + AI improved_angle
- `POST /growth/rewrite-title` — 5 viral title rewrites (each <70 chars; AI + deterministic templates)
- `POST /growth/score-hook` — hook intensity (0-100) + auto-regenerates a stronger hook if <70
- `POST /growth/make-viral` — 🔥 one-click pipeline: score topic → 5 titles → boost hook → thumbnail psychology → full optimize blueprint
- `GET/POST/DELETE /growth/performance` — manual performance feedback loop (views/CTR/likes → verdict worked|mixed|failed + do-more/avoid takeaway)
- `/youtube/optimize` now also returns `thumbnail_psychology` (emotion/face_expression/text/contrast/example_texts)

### Growth Engine (Content Factory, require `x-api-key` header)
- `GET /growth/schedule/days` — current posting days + valid_days + default_days
- `PUT /growth/schedule/days` — save posting days (body `{days:[...]}`; validated/deduped/ordered Sun→Sat; empty → 400)
- `POST /growth/weekly-auto` — generate + schedule a full week (5 videos) in one click on the selected posting days
- `GET /growth/today` — today's scheduled video (script + YouTube package)
- `GET /growth/schedule` — the posting calendar
- `POST /growth/schedule/{id}/posted` — mark posted → pipeline to Published + returns email draft
- `POST /growth/shorts` — full Shorts package (3 hooks + script + caption + hashtags)
- `POST /youtube/optimize` — YouTube Studio publishing blueprint (category, audience, tags, title/thumbnail style, description structure, posting time, captions, visibility, playlist, advanced settings) with SAFE deterministic defaults
- Plus existing: `/growth/content-flow`, `/growth/batch`, `/growth/repurpose`, `/growth/insights`, `/growth/pipeline`, `/growth/cta`

### Traffic Engine & Social Distribution (`/content/*`, require `x-api-key` header)
- `POST /content/generate-weekly-posts` — `{sunday_post (reflective, Mass-readings tied), wednesday_post (punchy apologetics), friday_post (promotes latest video + appended watch link), optional_image_prompt}`
- `GET /content/facebook-pack` — `{post_text, suggested_groups[] (= branding.FACEBOOK_GROUPS), instructions[]}` for manual sharing (never auto-posts)
- `POST /content/generate-shorts` — body `{video_topic?, script?, count?}` → `{shorts:[{hook,script,caption,on_screen_text,hashtags[]}]}` (3-5; blank input → uses latest video)
- `POST /content/generate-hooks` — body `{topic}` → `{hooks:[5]}`
- `POST /content/repurpose` — body `{topic?|script?}` → `{shorts[], facebook_post, tiktok_caption, youtube_description, email_teaser}`
- `GET /content/posting-plan` — `{weekly_plan:{monday,wednesday,friday,sunday}, tips[]}` (static strategy, no AI)
- Admin dashboard "📢 Weekly Distribution" tab — generate weekly posts + Facebook pack with per-block copy buttons
- Admin dashboard "🎬 Traffic Engine" tab — Shorts / hooks / repurpose generators + posting plan, all with copy buttons

## Architecture decisions

- SQLite only — never reads `DATABASE_URL` (that's the Node.js artifact's Postgres)
- HMAC-signed unsubscribe tokens using `SESSION_SECRET` — no DB storage needed
- AI generation is non-blocking: if OpenAI quota is exceeded, use `/send-newsletter/custom`
- Startup validation logs warnings for bad secrets but never crashes the server
- `/youtube/intelligence` results are cached in-memory for 5 min (slow upstream + quota); pass `?refresh=true` to bypass
- All emails share one branded shell (`email_shell`): dark theme (black bg, white text, gold #FFD700 accent, deep-red #8B0000, sans-serif), STATIC logo header positioned TOP-LEFT (table layout, max-height 50px, width auto, brand name beside it) — logo is an absolute `https://<domain>/static/logo.png` URL (built by `_email_urls()`) so it loads in external mail clients, gold "▶ Watch on YouTube" + "Subscribe for more truth" CTAs, footer brand + unsubscribe. Preview and send use the exact same renderer (1:1 parity)
- Admin dashboard is a self-contained SPA served at `/admin` — no separate frontend artifact
- Social distribution layer (`content_service.py` + `routes/content.py`): deterministic-first + AI-enriched + quota-resilient (same philosophy as the Viral/Growth layers) — every generator builds usable copy from pure-Python templates and only *upgrades* it with AI when OpenAI is available; on ANY AI failure it silently keeps the deterministic output, so `/content/*` NEVER 402s and always returns copy-ready material. ALL `/content/*` endpoints are admin-only (`verify_admin`) per the PUBLIC/ADMIN split. Nothing auto-posts — the Facebook pack only *suggests* groups for manual copy/paste
- Smart video linking (`content_service.latest_video_link`): no `YOUTUBE_API_KEY`, so "latest video" = admin-curated featured Short (`featured_service.get_featured` shorts[0], admin-ordered newest-first) → else `FEATURED_VIDEO_ID` watch URL → else channel URL. True 14-day upload-date freshness can't be honored without the API; approximated via the admin-curated featured video (intentional). The Friday weekly post always carries this link
- Social favicons (`branding.py`): header (top-right, replaces the old `odili-yt` button) AND landing footer ("Follow the Mission Everywhere", centered) render 4 inline-SVG brand icons (YouTube/Facebook/TikTok/Rumble) via `social_icons_html()` — 22px, official brand colours, gold hover glow + scale 1.1, open in a new tab. Shared `.odili-social`/`.odili-soc` CSS lives in `HEADER_CSS` (injected into both the header and the landing page) so the footer reuses it. Links: `branding.YOUTUBE_URL` / `FACEBOOK_URL` / `TIKTOK_URL` / `RUMBLE_URL`
- Video-announcement / mark-posted emails use `generate_evangelization_email` — a high-conversion funnel (curiosity+urgency subject, hook, short teaser — NO full script dump, drive to video). AI-driven with deterministic funnel fallback. The AI weekly-insights newsletter (`generate_newsletter_content`) is a separate format and intentionally left as-is
- All email YouTube links carry `?src=email&utm=odili_email` (via `_with_email_tracking`) so Email→YouTube conversion shows in YouTube Studio traffic sources
- `/youtube/optimize` is fully deterministic (no AI/keys required) — always returns SAFE YouTube Studio defaults; it only *enriches* posting time + tags from cached intelligence when a fresh cache exists (`peek_cached_insights`, no network fetch)
- Viral Conversion Layer is deterministic-first + AI-enriched + quota-resilient: topic/hook/thumbnail scores are pure-Python keyword heuristics; AI only supplies the improved_angle / viral titles / regenerated hook and always falls back to deterministic templates on any AI failure. `make_viral` orchestrates score_topic + rewrite_title + boost_hook + generate_optimization
- `score_hook_intensity` is deterministic (0-100); `/generate-idea` auto-boosts a weak hook (<70) via `boost_hook` and returns `hook_intensity_score`
- P8 email alignment: `generate_evangelization_email` forces the email opening line to BE the video hook when one is supplied (1:1 message-match); the subject stays the AI curiosity subject (title *style*, not a literal title copy) with the video title as fallback
- VideoPerformance table auto-creates at startup via `create_all` (no migration). Verdict logic: CTR-dominant (≥6% worked, <3% failed)
- PUBLIC vs ADMIN split: `/` (landing) is the *only* public-facing funnel and exposes NO internal tooling — just mission, email capture, topic engagement, YouTube, authority. Every growth/AI/content/optimization/newsletter/scripts/youtube endpoint requires `x-api-key`. Public endpoints are intentionally limited to: `/`, `/health`, `POST /emails` (subscribe), `/unsubscribe`, `/playlist`, and the topic engagement trio (`GET /topics`, `POST /topics/{id}/vote`, `POST /topics/request`)
- 5-email evangelization drip (`drip_service.py`): offsets `[0,1,3,5,7]` days, branded via `email_shell`. State is `Subscriber.drip_step` (0=welcome pending; N=N emails accounted for) — restart-safe, no DB-stored timestamps; due time = `Subscriber.subscribed_at + offset[step]`. Two paths advance it: `start_drip(email)` (fire-and-forget on subscribe, sends email 1) and the 30-min scheduler `process_due_drips(db)` (self-healing for later steps + any missed email 1). Both claim each step with an atomic compare-and-set UPDATE (`_claim_step`: `drip_step==step → step+1`) so step 0 can never double-send across the two paths; on send failure the step is released (`_release_step`) to retry. Drip only fires while the server runs → needs an always-on (Reserved VM) deployment, not scale-to-zero (warning logged at startup). Bulk CSV import is intentionally drip-free.
- Subscriber `interest` (str ≤120, nullable): the topic a visitor arrived via (set by the 5 fixed landing buttons → hidden field → `POST /subscribe`). `interest` + `drip_step` are added to existing SQLite DBs by an ALTER-column migration (`_ensure_columns` in `db.init_db`, PRAGMA-checked, runs after `create_all` since `create_all` never adds columns to an existing table)
- Posting-days selector: `AppSetting` (key/value, auto-created via `create_all`) stores the admin-chosen Growth Engine posting days under key `posting_days` (comma-joined). `growth_service.get_posting_days(db)` returns saved days or `DEFAULT_POSTING_DAYS=["Monday","Thursday"]`; `set_posting_days` validates against the 7 `VALID_DAYS`, dedupes, orders Sun→Sat, and raises `ValueError` (→ 400) if none valid. `weekly_schedule_dates(count, now, days)` cycles the selected weekdays across multiple weeks (future-only, 09:00 UTC, sorted, 104-week safety cap) so `count` can exceed days/week. `weekly_auto` passes `days=get_posting_days(db)`. Admin SPA Growth Engine has a "Select Posting Days" card (7 Sun–Sat toggles, gold-on/dark-off, hover glow + scale) wired via `loadPostingDays`/`togglePostingDay`/`savePostingDays`. Newsletter cron (Sun/Wed/Fri auto-send) is a SEPARATE system and is unchanged
- Catholic doctrine guardrails: the shared AI system prompt (`ai_service`) + youtube_intelligence prompt carry a tiered-source hierarchy (Scripture/Magisterium > Church Fathers/councils > approved theologians) so all AI output stays doctrinally grounded. Purely additive to prompts — no behavior change on quota failure
- Catholic news layer (`news_service.py`): aggregates Vatican News / CNA / EWTN RSS via httpx + `xml.etree`, in-memory cached 30 min, graceful fallback note on any fetch/parse error (never crashes idea-gen). News is *supportive context* fed into `/generate-idea` prompts — never treated as doctrinal authority. Links are scheme-sanitized server-side (non-http(s) dropped) AND in the admin renderer (only http(s) headlines are clickable) — defense in depth against `javascript:`/`data:` from upstream feeds. No `YOUTUBE_API_KEY` is used
- Featured content hub (`featured_service.py`): admin-curated Shorts/Playlists/Community stored as JSON in `AppSetting` (key `featured_content`) — NOT YouTube-API-fetched (no key). Public `GET /featured-content` is empty-safe; landing JS renders it only when curated (playlist/community URLs guarded to `^https?:`, titles escaped, short IDs URL-encoded for i.ytimg thumbnails). Admin "Content Hub" tab edits it (shorts as `VIDEO_ID | Title` per line, playlists as `Title | URL` per line)
- Topic display order: `Topic.sort_order` (int, added via `_ensure_columns` migration) drives the curated order; list queries sort by `(featured desc, sort_order, votes desc)`. Admin reorder posts full `ordered_ids` to `/topics/reorder`. `trending` is a computed flag (recent vote velocity), exposed to public + admin. Reorder is within the existing status-group sort (cross-status moves re-sync on reload — intentional)
- Funnel analytics + auto-optimization (`analytics_service.py` + `Event` table, auto-created via `create_all`): ALL metrics are event-driven (single source of truth) and aggregated in Python (no JSON1 dep). `POST /track` is PUBLIC but hardened — event names allow-listed, payload size-capped, `headline` validated against the shared `app.services.headlines.HEADLINES` set (prevents best-headline poisoning / H1 defacement), scroll `percent` clamped. Conversions = `signup` events carrying `{headline, interest}` — NOT total subscriber count — so `conversion_rate` is a true funnel rate. `get_best_headline` = signups/views per headline, 10-min in-memory cache + guards (≥50 total visits, ≥20 views/headline) else `None` → landing A/B fallback. Topic auto-prioritization (`list_public_topics`): order = featured → engagement score (`topic_click` + 3×`signup` interest, matched on lowercased title) → sort_order → votes; top performers get "🔥 Most Chosen" / "Popular" badges; falls back to manual order when no data (badges only when score>0). NOTE: scoring matches by lowercased title vs the interest/click label, so a topic only earns a score once its title aligns with that label — intentional, manual featured/sort_order always respected. Admin "📊 Analytics" tab reads `GET /analytics/summary`
- Email drip segmentation (`segment_service.py`): `segment_line(interest)` returns ONE interest-aware (HTML-safe, no user input) opening line that `send_drip_email` prepends to every drip email; general fallback when `interest` is null. Both callers (`start_drip`, `process_due_drips`) pass `sub.interest`. Keeps copy clean vs 30 hand-written variants; the atomic claim/release double-send safety is unchanged (only an `interest` arg was threaded through)
- Topic engagement: `Topic` (status: suggested|approved|featured|archived; source: admin|visitor) + `TopicVote` tables auto-create via `create_all`; 6 default topics seeded on first boot only (skips if any exist). Public list shows featured+approved (featured first, then votes desc). Visitor requests land as `suggested` (hidden) for admin review in the Audience Topics page. Vote dedup = salted SHA-256 of visitor IP (salt=`SESSION_SECRET`) with a unique `(topic_id, voter_hash)` constraint; re-votes return `counted:false` (not an error). Vote count incremented atomically at DB level. IP comes from `X-Forwarded-For` (proxy) — dedup is best-effort engagement, not a security boundary

## Required Environment Secrets

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | GPT-4o newsletter generation (optional — use custom send as fallback) |
| `SENDGRID_API_KEY` | Email delivery (must start with `SG.`) |
| `SENDGRID_FROM_EMAIL` | Verified sender address |
| `SENDGRID_FROM_NAME` | Display name in From field |
| `SESSION_SECRET` | HMAC key for unsubscribe tokens |
| `ADMIN_API_KEY` | Protects admin endpoints and dashboard |
| `YOUTUBE_CHANNEL_URL` | YouTube channel link in emails |
| `FEATURED_VIDEO_ID` | Optional — 11-char YouTube video ID for the landing "Start Here" embed (falls back to a poster card linking to the channel if unset) |

## User preferences

- Keep implementation simple and clean
- Admin key passed via `x-api-key` header
- Plain text newsletter body — one paragraph per line
- Auto-send schedule: Sunday, Wednesday, Friday at 09:00 UTC

## Gotchas

- OpenAI quota (429) is a billing issue — top up at platform.openai.com/account/billing
- `load_dotenv()` runs at startup but Replit secrets take precedence over `.env`
- `python-multipart` is required for CSV upload (already installed)
- Run `pip install -r python-backend/requirements.txt` after pulling fresh if packages are missing
