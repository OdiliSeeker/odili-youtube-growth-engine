"""
Shared site-wide branding.

Single source of truth for the global header bar and brand colours so the Odili
logo and identity appear consistently on every page. Inject ``HEADER_CSS`` into
each page's <head> and ``header_html()`` into the body.
"""

import os

APP_NAME = "Odili — The Seeker of Truth"
LOGO_URL = "/static/logo.png"
YOUTUBE_URL = "https://www.youtube.com/@odilitheseekeroftruth"
FACEBOOK_URL = "https://www.facebook.com/groups/1823217011909716"
TIKTOK_URL = "https://www.tiktok.com/@odilitheseeker"
RUMBLE_URL = "https://rumble.com/user/Odili"

# Facebook group(s) the admin is authorised to share into manually (the
# distribution assistant suggests these — it never auto-posts).
FACEBOOK_GROUPS = [FACEBOOK_URL]

# Compact favicon set shown in the header (top-right) and footer. Inline SVGs
# (no external requests) keep them crisp and reliable on the dark theme. Order
# is preserved. Each renders in its official brand colour with a gold hover glow.
SOCIAL_LINKS = [
    ("YouTube", YOUTUBE_URL),
    ("Facebook", FACEBOOK_URL),
    ("TikTok", TIKTOK_URL),
    ("Rumble", RUMBLE_URL),
]

_SOCIAL_SVGS = {
    "YouTube": (
        '<svg viewBox="0 0 24 24" fill="#FF0000" aria-hidden="true">'
        '<path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 '
        '3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 '
        '5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 '
        '9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 '
        '15.568V8.432L15.818 12l-6.273 3.568z"/></svg>'
    ),
    "Facebook": (
        '<svg viewBox="0 0 24 24" fill="#1877F2" aria-hidden="true">'
        '<path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 '
        '10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 '
        '2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 '
        '3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>'
    ),
    "TikTok": (
        '<svg viewBox="0 0 24 24" fill="#FFFFFF" aria-hidden="true">'
        '<path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 '
        '2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 '
        '2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 '
        '3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 '
        '1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 '
        '4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 '
        '1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/></svg>'
    ),
    "Rumble": (
        '<svg viewBox="0 0 24 24" aria-hidden="true">'
        '<rect width="24" height="24" rx="6" fill="#85C742"/>'
        '<text x="12" y="17.5" font-size="15" font-family="Arial, sans-serif" '
        'font-weight="700" fill="#0b2b00" text-anchor="middle">R</text></svg>'
    ),
}


def social_icons_html(extra_class: str = "") -> str:
    """Return the compact social favicon row (YouTube / Facebook / TikTok / Rumble)."""
    cls = ("odili-social " + extra_class).strip()
    items = "".join(
        f'<a class="odili-soc" href="{url}" target="_blank" rel="noopener" '
        f'aria-label="{name}" title="{name}">{_SOCIAL_SVGS[name]}</a>'
        for name, url in SOCIAL_LINKS
    )
    return f'<div class="{cls}">{items}</div>'

# Featured video for the landing "Start Here" section. Set the 11-char YouTube
# video ID (the part after `watch?v=`) to override the default. Always renders a
# real embedded player; a thumbnail/poster fallback covers any embed failure.
_DEFAULT_FEATURED_VIDEO_ID = "Bm2aoEcEIPk"
FEATURED_VIDEO_ID = "".join(
    c for c in os.getenv("FEATURED_VIDEO_ID", "").strip() if c.isalnum() or c in "-_"
) or _DEFAULT_FEATURED_VIDEO_ID

# Intro videos rotated A/B at random on each landing-page load. Video A is the
# featured/default; Video B is the second teaching. Deduped, order preserved.
_INTRO_VIDEO_B = "nY-N2JnuvG8"
INTRO_VIDEO_IDS = list(dict.fromkeys([FEATURED_VIDEO_ID, _INTRO_VIDEO_B]))

# Brand palette
GOLD = "#FFD700"
DEEP_RED = "#8B0000"
BLACK = "#000000"

HEADER_CSS = """<style>
  .odili-header {
    position: fixed; top: 0; left: 0; right: 0; z-index: 3000;
    display: flex; align-items: center; justify-content: space-between;
    gap: 16px; padding: 8px 22px; box-sizing: border-box;
    background: #000000; border-bottom: 2px solid #FFD700;
    box-shadow: 0 2px 16px rgba(0,0,0,.45);
  }
  .odili-header *, .odili-header *::before, .odili-header *::after { box-sizing: border-box; }
  .odili-brand { display: flex; align-items: center; gap: 13px; text-decoration: none; }
  .odili-brand img {
    height: 48px; width: auto; display: block; border-radius: 8px;
    filter: drop-shadow(0 0 7px rgba(255,215,0,.55));
  }
  .odili-brand .odili-name {
    font-family: Georgia, 'Times New Roman', serif; font-weight: 700; font-size: 18px;
    color: #FFD700; letter-spacing: .3px; white-space: nowrap;
  }
  .odili-nav { display: flex; align-items: center; gap: 8px; }
  .odili-nav a {
    color: #f5f5f5; text-decoration: none;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px; font-weight: 600; padding: 8px 14px; border-radius: 8px;
    transition: background .15s, color .15s; white-space: nowrap;
  }
  .odili-nav a:hover { color: #FFD700; background: rgba(255,215,0,.10); }
  .odili-nav a.odili-yt { background: #8B0000; color: #fff; }
  .odili-nav a.odili-yt:hover { background: #a81010; color: #fff; }
  .odili-social { display: inline-flex; align-items: center; gap: 10px; }
  .odili-soc {
    width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center;
    border-radius: 8px; text-decoration: none;
    transition: transform .15s ease, filter .15s ease, box-shadow .15s ease;
  }
  .odili-soc svg { width: 22px; height: 22px; display: block; }
  .odili-soc:hover {
    transform: scale(1.1);
    filter: drop-shadow(0 0 5px rgba(255,215,0,.85));
    box-shadow: 0 0 12px rgba(255,215,0,.35);
  }
  @media (max-width: 560px) {
    .odili-header { padding: 7px 14px; }
    .odili-brand img { height: 40px; }
    .odili-brand .odili-name { font-size: 14px; }
    .odili-nav a { padding: 7px 11px; font-size: 13px; }
    .odili-nav a.odili-sub { display: none; }
  }
  @media (max-width: 380px) {
    .odili-brand .odili-name { display: none; }
  }
</style>"""


def header_html() -> str:
    """Return the global header bar markup. The logo links back to the homepage."""
    return (
        '<header class="odili-header">'
        f'<a class="odili-brand" href="/" aria-label="{APP_NAME} home">'
        f'<img src="{LOGO_URL}" alt="{APP_NAME} logo">'
        f'<span class="odili-name">{APP_NAME}</span>'
        "</a>"
        '<nav class="odili-nav">'
        '<a class="odili-sub" href="/subscribe">Subscribe</a>'
        f"{social_icons_html()}"
        "</nav>"
        "</header>"
    )
