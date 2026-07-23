"""
Public blog / SEO landing pages (spec PART 4 / PART 7).

    GET /truth            PUBLIC: index of published teachings (articles)
    GET /truth/{slug}     PUBLIC: one article + email capture + YouTube CTA

Every page cross-links to the funnel (email capture reuses POST /subscribe with
source=landing_page) and to the ministry's YouTube channel, closing the
Traffic Engine loop. All rendered fields are HTML-escaped; links scheme-guarded.
"""

import html

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.branding import APP_NAME, YOUTUBE_URL
from app.db import get_db
from app.services import seo_service

router = APIRouter(tags=["Blog"])


def _safe(url: str | None, fallback: str = "") -> str:
    u = (url or "").strip()
    return u if u.lower().startswith(("http://", "https://")) else fallback


_PAGE_CSS = """
<style>
  :root{--gold:#FFD700;--bg:#0a0a0a;--panel:#141414;--muted:#a8a8a8}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:#f0f0f0;font-family:Georgia,'Times New Roman',serif;line-height:1.75}
  a{color:var(--gold)}
  .wrap{max-width:760px;margin:0 auto;padding:32px 22px 80px}
  header.site{text-align:center;padding:26px 0 8px}
  header.site .brand{color:var(--gold);font-size:15px;letter-spacing:.14em;text-transform:uppercase;text-decoration:none;font-family:Arial,sans-serif}
  h1{font-size:34px;line-height:1.25;margin:22px 0 10px}
  .meta{color:var(--muted);font-size:14px;font-family:Arial,sans-serif;margin-bottom:26px}
  article p{font-size:18px;margin:0 0 20px}
  .cta{background:var(--panel);border:1px solid rgba(255,215,0,.25);border-radius:14px;padding:26px;margin:38px 0}
  .cta h3{margin:0 0 6px;color:var(--gold);font-family:Arial,sans-serif}
  .cta p{margin:0 0 16px;color:var(--muted);font-size:16px}
  .row{display:flex;gap:10px;flex-wrap:wrap}
  input[type=email]{flex:1;min-width:200px;padding:14px 16px;border-radius:10px;border:1px solid #333;background:#000;color:#fff;font-size:16px}
  button,.btn{background:var(--gold);color:#000;border:0;border-radius:10px;padding:14px 24px;font-weight:700;font-size:15px;cursor:pointer;text-decoration:none;display:inline-block;font-family:Arial,sans-serif}
  .btn.yt{background:#ff0000;color:#fff}
  .note{font-size:13px;color:var(--muted);margin-top:10px}
  .cards{display:grid;gap:14px}
  .card{display:block;background:var(--panel);border:1px solid #222;border-radius:12px;padding:18px 20px;text-decoration:none;color:#f0f0f0}
  .card:hover{border-color:rgba(255,215,0,.4)}
  .card .t{font-size:19px;margin-bottom:4px}
  .card .d{color:var(--muted);font-size:14px}
  footer{text-align:center;color:var(--muted);font-size:13px;padding-top:30px;font-family:Arial,sans-serif}
</style>
"""


def _capture_and_cta(video_url: str, src: str) -> str:
    yt = _safe(video_url, YOUTUBE_URL)
    return f"""
    <div class="cta">
      <h3>Get the full teaching — free</h3>
      <p>New teachings released weekly. Rooted in Scripture, Tradition, and 2,000 years of Catholic teaching.</p>
      <form id="capture" class="row" onsubmit="return subscribe(event)">
        <input type="email" id="email" placeholder="you@email.com" required>
        <button type="submit">Send me the truth</button>
      </form>
      <div class="note" id="msg"></div>
    </div>
    <div class="cta">
      <h3>Prefer to watch?</h3>
      <p>See the teaching on video and subscribe on YouTube.</p>
      <a class="btn yt" href="{html.escape(yt)}" target="_blank" rel="noopener">&#9654; Watch on YouTube</a>
    </div>
    <script>
      async function subscribe(e){{
        e.preventDefault();
        var email=document.getElementById('email').value.trim();
        var msg=document.getElementById('msg');
        if(!email){{return false;}}
        try{{
          var res=await fetch('/subscribe',{{method:'POST',headers:{{'Content-Type':'application/json'}},
            body:JSON.stringify({{email:email, source:'landing_page'}})}});
          if(res.ok||res.status===409){{
            try{{localStorage.setItem('odili_email_captured','1');}}catch(_e){{}}
            msg.textContent="You're in. Check your inbox for the first teaching.";
            msg.style.color='#8fd18f';
            document.getElementById('capture').reset();
          }}else{{msg.textContent='Something went wrong — please try again.';msg.style.color='#e58f8f';}}
        }}catch(_e){{msg.textContent='Network error — please try again.';msg.style.color='#e58f8f';}}
        return false;
      }}
    </script>
    """


@router.get("/truth-feed", include_in_schema=False)
async def blog_feed(db: Session = Depends(get_db)) -> dict:
    """PUBLIC JSON feed of published articles for the landing 'Latest Teachings' strip."""
    articles = seo_service.list_articles(db, published_only=True, limit=12)
    items = [
        {
            "slug": a["slug"],
            "title": a["title"],
            "meta_description": a.get("meta_description") or "",
        }
        for a in articles
    ]
    return {"count": len(items), "items": items}


@router.get("/truth", response_class=HTMLResponse, include_in_schema=False)
async def blog_index(db: Session = Depends(get_db)) -> HTMLResponse:
    articles = seo_service.list_articles(db, published_only=True, limit=100)
    if articles:
        cards = "".join(
            f'<a class="card" href="/truth/{html.escape(a["slug"])}">'
            f'<div class="t">{html.escape(a["title"])}</div>'
            f'<div class="d">{html.escape(a.get("meta_description") or "")}</div></a>'
            for a in articles
        )
    else:
        cards = '<p class="meta">New teachings are on the way. Check back soon.</p>'
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Teachings — {html.escape(APP_NAME)}</title>
    <meta name="description" content="Catholic teachings rooted in Scripture, the Church Fathers, and Tradition.">
    {_PAGE_CSS}</head><body>
    <header class="site"><a class="brand" href="/">{html.escape(APP_NAME)}</a></header>
    <div class="wrap">
      <h1>Teachings</h1>
      <p class="meta">Seek the truth. Rooted in Scripture and 2,000 years of Catholic teaching.</p>
      <div class="cards">{cards}</div>
      {_capture_and_cta(YOUTUBE_URL, 'article')}
      <footer>&copy; {html.escape(APP_NAME)} · <a href="/">Home</a></footer>
    </div></body></html>"""
    return HTMLResponse(body)


@router.get("/truth/{slug}", response_class=HTMLResponse, include_in_schema=False)
async def blog_article(slug: str, db: Session = Depends(get_db)) -> HTMLResponse:
    article = seo_service.get_by_slug(db, slug)
    if article is None or article.status != "published":
        return HTMLResponse(
            f"<!doctype html><html><head><meta charset='utf-8'>{_PAGE_CSS}</head><body>"
            f"<div class='wrap'><header class='site'><a class='brand' href='/'>{html.escape(APP_NAME)}</a></header>"
            f"<h1>Teaching not found</h1><p class='meta'>This teaching may have moved.</p>"
            f"<a class='btn' href='/truth'>Browse all teachings</a></div></body></html>",
            status_code=404,
        )
    paragraphs = "".join(
        f"<p>{html.escape(line.strip())}</p>"
        for line in article.body.splitlines() if line.strip()
    )
    meta = html.escape(article.meta_description or "")
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{html.escape(article.title)} — {html.escape(APP_NAME)}</title>
    <meta name="description" content="{meta}">
    {_PAGE_CSS}</head><body>
    <header class="site"><a class="brand" href="/">{html.escape(APP_NAME)}</a></header>
    <div class="wrap">
      <h1>{html.escape(article.title)}</h1>
      <p class="meta">Rooted in Scripture, the Church Fathers, and Catholic Tradition</p>
      <article>{paragraphs}</article>
      {_capture_and_cta(article.video_url or YOUTUBE_URL, 'article')}
      <footer><a href="/truth">← All teachings</a> · <a href="/">Home</a></footer>
    </div></body></html>"""
    return HTMLResponse(body)
