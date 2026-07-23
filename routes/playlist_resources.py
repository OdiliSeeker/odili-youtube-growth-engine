"""
Playlist Resources — authority knowledge base.

PUBLIC (funnel surface):
    GET /resources             HTML: 4-section card layout, insight-first modal
    GET /resources-feed        JSON feed (sections + resources) for landing use

ADMIN (x-api-key):
    GET    /admin/resources                 all resources grouped
    POST   /admin/resources                 add
    PATCH  /admin/resources/{id}            edit
    DELETE /admin/resources/{id}            remove
    POST   /admin/resources/{id}/promote    → Topic + Email draft (content loop)

Conversion rule (spec): resource → insight → THEN YouTube. The modal shows the
summary and relevance first; the video CTA comes last. All rendered fields are
HTML-escaped; stored links scheme-guarded server-side.
"""

import html
import json


from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.branding import APP_NAME, YOUTUBE_URL
from app.db import get_db
from app.dependencies.auth import verify_admin
from app.services import playlist_resource_service as prs

router = APIRouter(tags=["Playlist Resources"])


def _json_for_script(value) -> str:
    """Serialize JSON safely for embedding inside an inline <script> block.

    Escapes ``</`` so a stored ``</script>`` in any field can never break out
    of the script context (stored-XSS guard), and U+2028/U+2029 which are
    valid JSON but illegal in JS string literals.
    """
    return (
        json.dumps(value)
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


class ResourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    category: str = Field(min_length=1, max_length=60)
    description: str = Field(default="", max_length=5000)
    relevance: str = Field(default="", max_length=2000)
    source_type: str = Field(default="book", max_length=30)
    source_name: str = Field(default="", max_length=300)
    link: str | None = Field(default=None, max_length=1000)
    video_url: str | None = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list)
    sort_order: int = 0


class ResourceUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    category: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=5000)
    relevance: str | None = Field(default=None, max_length=2000)
    source_type: str | None = Field(default=None, max_length=30)
    source_name: str | None = Field(default=None, max_length=300)
    link: str | None = Field(default=None, max_length=1000)
    video_url: str | None = Field(default=None, max_length=1000)
    tags: list[str] | None = None
    sort_order: int | None = None


# ── Admin endpoints ──────────────────────────────────────────────────────────

@router.get("/admin/resources")
async def admin_list(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    return {
        "sections": [{"slug": s, "label": l} for s, l in prs.SECTIONS.items()],
        "source_types": list(prs.SOURCE_TYPES),
        "tags": list(prs.ALLOWED_TAGS),
        "resources": prs.list_resources(db),
    }


@router.post("/admin/resources", status_code=201)
async def admin_create(
    payload: ResourceCreate, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    try:
        return prs.create_resource(db, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.patch("/admin/resources/{resource_id}")
async def admin_update(
    resource_id: int,
    payload: ResourceUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    updated = prs.update_resource(db, resource_id, payload.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Resource not found.")
    return updated


@router.delete("/admin/resources/{resource_id}")
async def admin_delete(
    resource_id: int, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    if not prs.delete_resource(db, resource_id):
        raise HTTPException(status_code=404, detail="Resource not found.")
    return {"ok": True}


@router.post("/admin/resources/{resource_id}/promote")
async def admin_promote(
    resource_id: int, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    result = prs.promote_resource(db, resource_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Resource not found.")
    return result


# ── Public surface ───────────────────────────────────────────────────────────

@router.get("/resources-feed", include_in_schema=False)
async def resources_feed(db: Session = Depends(get_db)) -> dict:
    """PUBLIC JSON: sections + resources (safe fields only)."""
    sections = prs.grouped(db)
    return {
        "count": sum(len(s["resources"]) for s in sections),
        "sections": [
            {
                "slug": s["slug"],
                "label": s["label"],
                "resources": [
                    {
                        "id": r["id"],
                        "title": r["title"],
                        "description": r["description"],
                        "relevance": r["relevance"],
                        "source_name": r["source_name"],
                        "source_type": r["source_type"],
                        "link": r["link"],
                        "video_url": r["video_url"],
                        "tags": r["tags"],
                    }
                    for r in s["resources"]
                ],
            }
            for s in sections
        ],
    }


_PAGE_CSS = """
<style>
  :root{--gold:#FFD700;--bg:#0a0a0a;--panel:#141414;--muted:#a8a8a8}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:#f0f0f0;font-family:Georgia,'Times New Roman',serif;line-height:1.7}
  a{color:var(--gold)}
  .wrap{max-width:960px;margin:0 auto;padding:32px 22px 80px}
  header.site{text-align:center;padding:26px 0 8px}
  header.site .brand{color:var(--gold);font-size:15px;letter-spacing:.14em;text-transform:uppercase;text-decoration:none;font-family:Arial,sans-serif}
  h1{font-size:34px;line-height:1.25;margin:22px 0 8px;text-align:center}
  .lede{color:var(--muted);text-align:center;max-width:640px;margin:0 auto 36px;font-size:17px}
  h2.section{color:var(--gold);font-family:Arial,sans-serif;font-size:15px;letter-spacing:.12em;text-transform:uppercase;border-bottom:1px solid rgba(255,215,0,.25);padding-bottom:8px;margin:42px 0 16px}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:14px}
  .card{background:var(--panel);border:1px solid #222;border-radius:12px;padding:18px 20px;display:flex;flex-direction:column}
  .card:hover{border-color:rgba(255,215,0,.4)}
  .card .t{font-size:18px;margin-bottom:6px}
  .card .d{color:var(--muted);font-size:14px;flex:1}
  .card .src{color:#777;font-size:12px;font-family:Arial,sans-serif;margin:10px 0}
  .btn{background:var(--gold);color:#000;border:0;border-radius:10px;padding:10px 18px;font-weight:700;font-size:14px;cursor:pointer;text-decoration:none;display:inline-block;font-family:Arial,sans-serif;align-self:flex-start}
  .btn.yt{background:#ff0000;color:#fff}
  .overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.82);z-index:50;padding:24px;overflow:auto}
  .overlay.open{display:flex;align-items:flex-start;justify-content:center}
  .modal{background:var(--panel);border:1px solid rgba(255,215,0,.3);border-radius:14px;max-width:640px;width:100%;padding:28px;margin:40px 0}
  .modal h3{margin:0 0 4px;font-size:24px}
  .modal .src{color:#777;font-size:13px;font-family:Arial,sans-serif;margin-bottom:16px}
  .modal .why{background:#000;border-left:3px solid var(--gold);padding:12px 16px;margin:18px 0;color:#ddd}
  .modal .close{float:right;background:none;border:0;color:var(--muted);font-size:22px;cursor:pointer}
  .modal .actions{margin-top:22px;display:flex;gap:10px;flex-wrap:wrap}
  footer{text-align:center;color:var(--muted);font-size:13px;padding-top:40px;font-family:Arial,sans-serif}
</style>
"""


@router.get("/resources", response_class=HTMLResponse, include_in_schema=False)
async def resources_page(db: Session = Depends(get_db)) -> HTMLResponse:
    """PUBLIC authority hub: sections → cards → insight-first modal → YouTube CTA."""
    sections = prs.grouped(db)
    yt_fallback = YOUTUBE_URL

    payload = []
    sections_html = []
    for s in sections:
        cards = []
        for r in s["resources"]:
            payload.append(
                {
                    "id": r["id"],
                    "title": r["title"],
                    "description": r["description"],
                    "relevance": r["relevance"],
                    "source_name": r["source_name"],
                    "link": r["link"],
                    "video_url": r["video_url"],
                }
            )
            cards.append(
                f'<div class="card"><div class="t">{html.escape(r["title"])}</div>'
                f'<div class="d">{html.escape((r["description"] or "")[:160])}</div>'
                f'<div class="src">{html.escape(r["source_name"])}</div>'
                f'<button class="btn" onclick="openRes({int(r["id"])})">Explore</button></div>'
            )
        sections_html.append(
            f'<h2 class="section">{html.escape(s["label"])}</h2>'
            f'<div class="grid">{"".join(cards)}</div>'
        )

    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Playlist Resources — {html.escape(APP_NAME)}</title>
    <meta name="description" content="Trusted Catholic sources: papal history, councils, the Church Fathers, and the trials the Church survived — organized so you can verify the faith yourself.">
    {_PAGE_CSS}</head><body>
    <header class="site"><a class="brand" href="/">{html.escape(APP_NAME)}</a></header>
    <div class="wrap">
      <h1>Playlist Resources</h1>
      <p class="lede">Don't take anyone's word for it — not even ours. These are the trusted historical and doctrinal sources. Read what they say, then watch the teaching.</p>
      {"".join(sections_html) if sections_html else '<p class="lede">Resources are being prepared. Check back soon.</p>'}
      <footer><a href="/truth">Teachings</a> · <a href="/">Home</a> · &copy; {html.escape(APP_NAME)}</footer>
    </div>
    <div class="overlay" id="ov" onclick="if(event.target===this)closeRes()">
      <div class="modal">
        <button class="close" onclick="closeRes()">&times;</button>
        <h3 id="m-title"></h3>
        <div class="src" id="m-src"></div>
        <p id="m-desc"></p>
        <div class="why"><strong style="color:var(--gold);font-family:Arial,sans-serif;font-size:13px">WHY IT MATTERS</strong><br><span id="m-why"></span></div>
        <div class="actions" id="m-actions"></div>
      </div>
    </div>
    <script>
      var RES = {_json_for_script({str(p["id"]): p for p in payload})};
      var YT_FALLBACK = {_json_for_script(yt_fallback)};
      function esc(s) {{
        var d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML;
      }}
      function safeUrl(u) {{
        return (typeof u === 'string' && /^https?:\\/\\//i.test(u)) ? u : null;
      }}
      function openRes(id) {{
        var r = RES[String(id)];
        if (!r) return;
        document.getElementById('m-title').textContent = r.title;
        document.getElementById('m-src').textContent = r.source_name || '';
        document.getElementById('m-desc').textContent = r.description || '';
        document.getElementById('m-why').textContent = r.relevance || '';
        var acts = [];
        var link = safeUrl(r.link);
        if (link) acts.push('<a class="btn" href="' + esc(link) + '" target="_blank" rel="noopener">Read the source</a>');
        var vid = safeUrl(r.video_url) || YT_FALLBACK;
        if (vid) acts.push('<a class="btn yt" href="' + esc(vid) + '" target="_blank" rel="noopener">&#9654; See this explained in a short teaching</a>');
        document.getElementById('m-actions').innerHTML = acts.join('');
        document.getElementById('ov').classList.add('open');
      }}
      function closeRes() {{ document.getElementById('ov').classList.remove('open'); }}
    </script>
    </body></html>"""
    return HTMLResponse(body)
