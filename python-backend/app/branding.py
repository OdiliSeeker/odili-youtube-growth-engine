"""
Shared site-wide branding.

Single source of truth for the global header bar and brand colours so the Odili
logo and identity appear consistently on every page. Inject ``HEADER_CSS`` into
each page's <head> and ``header_html()`` into the body.
"""

APP_NAME = "Odili — The Seeker of Truth"
LOGO_URL = "/static/logo.png"
YOUTUBE_URL = "https://www.youtube.com/@odilitheseekeroftruth"

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
        f'<a class="odili-yt" href="{YOUTUBE_URL}" target="_blank" rel="noopener">YouTube</a>'
        "</nav>"
        "</header>"
    )
