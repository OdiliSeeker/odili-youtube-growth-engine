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
- `GET /thank-you` (alias `GET /welcome`) — post-signup page: "You're In." + inbox-check reassurance + the ONLY place we intentionally drive to YouTube ("Watch the 1-Minute Starting Point" + "Subscribe on YouTube") + footer social icons. Landing JS redirects here on subscribe success
- `POST /subscribe` — public funnel subscribe: stores topic `interest` (optional) + optional `source` (`landing_page`|`voter`|`contributor`, default `landing_page`) + applies signup tags (see tagging note) + starts the 5-email drip sequence (email 1 = the lead magnet, sends immediately). Tagging runs BEFORE the duplicate check so returning subscribers still accrue new tags (then 409)
- `POST /emails` — subscribe (triggers welcome email + starts drip sequence)
- `GET /unsubscribe?email=&token=` — one-click unsubscribe (HMAC verified)
- `GET /playlist` — YouTube channel routing
- `GET /topics` — list public (approved/featured) topics with vote counts + `trending` flag
- `POST /topics/{id}/vote` — vote for a topic (deduped per visitor IP, idempotent)
- `POST /topics/request` — visitor submits a topic (lands as 'suggested' for review)
- `GET /featured-content` — admin-curated content hub: `{shorts:[{id,title}], playlists:[{title,url}], community_url}` (empty-safe defaults)
- `POST /track` — public funnel behavior event (allow-listed names only: page_view/cta_click/topic_click/video_loaded/scroll_depth/headline_variant/vote/signup; `headline` validated against the real A/B set, scroll `percent` clamped to 25/50/75/100, payload size-capped — hardened against poisoning)
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
- `GET /analytics/summary` — funnel metrics (total_visits, cta_clicks, subscriptions=signup events, votes, conversion_rate, top_headlines, top_topics by signup interest, topic_clicks, signup_sources={landing_page|voter|contributor:count}, scroll_depth); optional `?days=N` window
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
- All emails share one branded shell (`email_shell`, dark/gold theme). Logo must be an absolute `https://<domain>/static/logo.png` URL (built by `_email_urls()`) so it loads in external mail clients. Preview and send use the exact same renderer (1:1 parity)
- Admin dashboard is a self-contained SPA served at `/admin` — no separate frontend artifact
- **Deterministic-first + AI-enriched + quota-resilient** is the shared philosophy of the Social (`content_service`), Viral, and Growth layers: every generator builds usable copy from pure-Python templates and only *upgrades* it with AI when available; on ANY AI failure it silently keeps the deterministic output, so these endpoints NEVER 402. `make_viral` orchestrates score_topic + rewrite_title + boost_hook + generate_optimization. Scores (topic/hook/thumbnail) are pure-Python heuristics
- Nothing auto-posts — the Facebook pack only *suggests* groups for manual copy/paste
- `/youtube/optimize` is fully deterministic (no AI/keys) — SAFE YouTube Studio defaults; only *enriches* posting time + tags from a fresh cache (`peek_cached_insights`, no network fetch). `/youtube/intelligence` is cached in-memory 5 min; `?refresh=true` bypasses
- No `YOUTUBE_API_KEY` anywhere. "Latest video" (`content_service.latest_video_link`) = admin-curated featured Short → `FEATURED_VIDEO_ID` → channel URL. True upload-date freshness can't be honored without the API (intentional approximation); the Friday weekly post always carries this link
- Social icons (`branding.social_icons_html()`): 4 inline-SVG brand links (YouTube/Facebook/TikTok/Rumble) in the header + landing/thank-you footers. Shared CSS lives in `HEADER_CSS`. Links from `branding.*_URL`
- Video-announcement / mark-posted emails use `generate_evangelization_email` — curiosity+urgency subject, hook, short teaser (NO full script dump), drive to video; AI with deterministic fallback. The email opening line IS the video hook when supplied (1:1 message-match). The AI weekly-insights newsletter (`generate_newsletter_content`) is a separate format, left as-is
- All email YouTube links carry `?src=email&utm=odili_email` (via `_with_email_tracking`) so Email→YouTube conversion shows in YouTube Studio
- **PUBLIC vs ADMIN split (security boundary):** `/` (landing) + `/thank-you` are the only public-facing funnel pages; every growth/AI/content/optimization/newsletter/youtube endpoint requires `x-api-key`. Public endpoints are limited to: `/`, `/thank-you` (+`/welcome`), `/health`, subscribe (`POST /emails`, `POST /subscribe`), `/unsubscribe`, `/playlist`, `/featured-content`, `POST /track`, `/analytics/best-headline`, and the topic trio (`GET /topics`, `POST /topics/{id}/vote`, `POST /topics/request`)
- **Schema evolution:** new tables auto-create via `create_all` (VideoPerformance, SubscriberTag, AppSetting, Event, Topic/TopicVote — no migration). New *columns on existing tables* need an explicit ALTER migration (`_ensure_columns` in `db.init_db`, PRAGMA-checked) because `create_all` never alters existing tables — this covers Subscriber `interest`/`drip_step` and Topic `sort_order`
- **5-email evangelization drip (`drip_service.py`), offsets `[0,1,3,5,7]` days:** state is `Subscriber.drip_step` (restart-safe, no stored timestamps; due = `subscribed_at + offset[step]`). Two paths advance it — `start_drip` (on subscribe, sends email 1) and the 30-min scheduler `process_due_drips` (self-healing for later steps + any missed email 1). Both claim each step with an atomic compare-and-set UPDATE (`drip_step==step → step+1`) so step 0 can never double-send; on failure the step is released to retry. **Drip only fires while the server runs → needs an always-on (Reserved VM) deployment, not scale-to-zero.** Bulk CSV import is intentionally drip-free
- Drip segmentation (`segment_service.segment_line(interest)`): one interest-aware (HTML-safe) opening line prepended per drip email; general fallback when `interest` is null. Both drip callers pass `sub.interest`
- Signup tagging (`tag_service.apply_signup_tags`, `SubscriberTag` table): idempotent lead-source tags via unique `(subscriber_id, tag)`. Every signup → `new-lead`; `voter`/`contributor` sources add a source tag; non-empty `interest` → its own tag. Called BEFORE the 409 duplicate check so returning subscribers still accrue tags. `source` (validated to `{landing_page, voter, contributor}` in `SubscribeRequest`) is set by the funnel: main form → `landing_page`, vote→notify modal → `voter`, topic-request email → `contributor`
- **Funnel analytics (`analytics_service` + `Event` table):** event-driven single source of truth, aggregated in Python (no JSON1). `POST /track` is PUBLIC but hardened — event names allow-listed, payload size-capped, `headline` validated against `app.services.headlines.HEADLINES` (prevents best-headline poisoning), scroll `percent` clamped. Conversions = `signup` events (carrying `{headline, interest, source}`), NOT subscriber count → true `conversion_rate`. `get_best_headline` = signups/views per headline, 10-min cache + guards (≥50 visits, ≥20 views/headline) else `None` → A/B fallback. Topic auto-prioritization (`list_public_topics`): featured → engagement score (`topic_click` + 3×`signup` interest, matched on lowercased title) → sort_order → votes; badges only when score>0, else manual order
- Posting-days selector: admin-chosen Growth Engine days stored in `AppSetting` key `posting_days`; `get_posting_days` returns saved or `DEFAULT_POSTING_DAYS=["Monday","Thursday"]`; `set_posting_days` validates/dedupes/orders Sun→Sat (empty → 400). `weekly_schedule_dates` cycles selected weekdays across weeks (future-only, 09:00 UTC, 104-week cap) so `count` can exceed days/week. Newsletter cron (Sun/Wed/Fri) is a SEPARATE, unchanged system
- Catholic doctrine guardrails: shared AI system prompt carries a tiered-source hierarchy (Scripture/Magisterium > Fathers/councils > approved theologians). Additive to prompts only — no behavior change on quota failure
- Catholic news layer (`news_service.py`): Vatican News / CNA / EWTN RSS, cached 30 min, graceful fallback (never crashes idea-gen). Supportive context for `/generate-idea` only — never doctrinal authority. Links scheme-sanitized server-side + in the admin renderer (only `^https?:` clickable) — defense-in-depth vs `javascript:`/`data:` from feeds
- Featured content hub (`featured_service.py`): admin-curated Shorts/Playlists/Community as JSON in `AppSetting` key `featured_content`. Public `GET /featured-content` is empty-safe; landing JS renders only when curated (URLs guarded to `^https?:`, titles escaped, short IDs URL-encoded)
- Topic engagement: `Topic` (status suggested|approved|featured|archived; source admin|visitor) + `TopicVote`; 6 defaults seeded first boot only. Public shows featured+approved. Visitor requests land as `suggested` (hidden) for review. Vote dedup = salted SHA-256 of `X-Forwarded-For` IP (unique `(topic_id, voter_hash)`); re-votes return `counted:false`. Dedup is best-effort engagement, NOT a security boundary. `trending` = recent vote velocity. Display order sorts by `(featured desc, sort_order, votes desc)`; admin reorder posts full `ordered_ids`

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
