import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.branding import HEADER_CSS, header_html

router = APIRouter()

_SUBSCRIBE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" type="image/png" href="/static/logo.png">
  <title>Subscribe · Odili Truth Seeker</title>
  __ODILI_HEADER_CSS__
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --red:    #7a1212;
      --red-dk: #5a0d0d;
      --gold:   #c8a84b;
      --cream:  #fdf8f2;
      --card:   #ffffff;
      --text:   #1a1a1a;
      --muted:  #6b5f56;
      --border: #e5ddd4;
      --success:#2e7d32;
      --danger: #c0392b;
      --shadow: 0 4px 24px rgba(0,0,0,.10);
    }

    body {
      font-family: Georgia, 'Times New Roman', serif;
      background: var(--cream);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 96px 16px 24px;
    }

    /* ── Cross accent ── */
    .cross-wrap {
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 10px;
    }
    .cross {
      position: relative;
      width: 28px;
      height: 34px;
      flex-shrink: 0;
    }
    .cross::before {
      content: '';
      position: absolute;
      left: 50%;
      transform: translateX(-50%);
      width: 5px;
      height: 100%;
      background: var(--gold);
      border-radius: 2px;
    }
    .cross::after {
      content: '';
      position: absolute;
      top: 28%;
      left: 0;
      width: 100%;
      height: 5px;
      background: var(--gold);
      border-radius: 2px;
    }

    /* ── Card ── */
    .card {
      background: var(--card);
      border-radius: 10px;
      box-shadow: var(--shadow);
      padding: 48px 44px 44px;
      max-width: 500px;
      width: 100%;
      border-top: 4px solid var(--red);
    }

    /* ── Header ── */
    .header { text-align: center; margin-bottom: 36px; }
    .brand-logo {
      width: 132px;
      height: 132px;
      object-fit: contain;
      border-radius: 16px;
      margin: 0 auto 18px;
      display: block;
      background: #000;
      padding: 6px;
    }
    .ministry-name {
      font-size: 22px;
      font-weight: bold;
      color: var(--red);
      letter-spacing: .5px;
      line-height: 1.3;
    }
    .tagline {
      font-size: 13px;
      color: var(--muted);
      margin-top: 6px;
      font-style: italic;
      letter-spacing: .3px;
    }
    .divider {
      width: 48px;
      height: 2px;
      background: var(--gold);
      margin: 16px auto 0;
      border-radius: 2px;
    }

    /* ── Body copy ── */
    .invite {
      font-size: 15px;
      line-height: 1.75;
      color: var(--muted);
      text-align: center;
      margin-bottom: 32px;
    }
    .invite strong { color: var(--text); font-style: normal; font-weight: normal; }

    /* ── Form ── */
    .field { margin-bottom: 18px; }
    label {
      display: block;
      font-size: 12px;
      font-weight: bold;
      text-transform: uppercase;
      letter-spacing: .8px;
      color: var(--muted);
      margin-bottom: 7px;
      font-family: system-ui, sans-serif;
    }
    input[type=text], input[type=email] {
      width: 100%;
      padding: 12px 14px;
      font-size: 15px;
      font-family: Georgia, serif;
      border: 1px solid var(--border);
      border-radius: 5px;
      outline: none;
      transition: border .2s, box-shadow .2s;
      background: #fefefe;
      color: var(--text);
    }
    input:focus {
      border-color: var(--red);
      box-shadow: 0 0 0 3px rgba(122,18,18,.08);
    }
    input::placeholder { color: #bbb; font-style: italic; }

    .btn-subscribe {
      width: 100%;
      padding: 14px;
      font-size: 15px;
      font-family: Georgia, serif;
      font-weight: bold;
      letter-spacing: .5px;
      background: var(--red);
      color: #fff;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      transition: background .2s, transform .1s;
      margin-top: 6px;
    }
    .btn-subscribe:hover  { background: var(--red-dk); }
    .btn-subscribe:active { transform: scale(.98); }
    .btn-subscribe:disabled { opacity: .6; cursor: not-allowed; transform: none; }

    /* ── Messages ── */
    .msg {
      display: none;
      border-radius: 5px;
      padding: 14px 16px;
      font-size: 14px;
      line-height: 1.5;
      margin-top: 20px;
      font-family: system-ui, sans-serif;
    }
    .msg.success { display: block; background: #edf7ee; color: var(--success); border: 1px solid #c3e6c5; }
    .msg.error   { display: block; background: #fdecea; color: var(--danger);  border: 1px solid #f5c6c4; }

    /* ── Footer ── */
    .footer {
      margin-top: 28px;
      font-size: 12px;
      color: var(--muted);
      text-align: center;
      line-height: 1.6;
      font-family: system-ui, sans-serif;
    }
    .footer a { color: var(--muted); text-decoration: underline; }

    /* ── Success state ── */
    .success-state { display: none; text-align: center; }
    .success-icon {
      font-size: 48px;
      margin-bottom: 16px;
    }
    .success-state h2 { font-size: 22px; color: var(--red); margin-bottom: 10px; }
    .success-state p  { font-size: 15px; color: var(--muted); line-height: 1.7; }

    @media (max-width: 520px) {
      .card { padding: 36px 24px 32px; }
    }
  </style>
</head>
<body>
__ODILI_HEADER_HTML__
<div class="card">

  <!-- Header -->
  <div class="header">
    <img class="brand-logo" src="/static/logo.png" alt="Odili — The Seeker of Truth logo">
    <div class="ministry-name">Odili Truth Seeker</div>
    <div class="tagline">Catholic Media Ministry</div>
    <div class="divider"></div>
  </div>

  <!-- Subscribe form -->
  <div id="form-state">
    <p class="invite">
      Join our community and receive <strong>reflections, homilies, and Catholic truth</strong>
      delivered straight to your inbox — three times a week.
    </p>

    <form id="sub-form" onsubmit="handleSubmit(event)" novalidate>
      <div class="field">
        <label for="name">Your Name (optional)</label>
        <input type="text" id="name" name="name" placeholder="e.g. Mary" autocomplete="given-name">
      </div>
      <div class="field">
        <label for="email">Email Address *</label>
        <input type="email" id="email" name="email" placeholder="you@example.com"
               required autocomplete="email">
      </div>
      <button type="submit" class="btn-subscribe" id="sub-btn">
        Subscribe — It&rsquo;s Free
      </button>
      <div id="msg" class="msg"></div>
    </form>

    <div class="footer">
      We send newsletters on&nbsp;Sunday, Wednesday &amp; Friday.<br>
      No spam &mdash; ever.
      <a href="/unsubscribe?email=&token=placeholder" id="unsub-link" style="display:none"></a>
      You may unsubscribe at any time via the link in each email.
    </div>
  </div>

  <!-- Success state (shown after subscribe) -->
  <div id="success-state" class="success-state">
    <div class="success-icon">✝</div>
    <h2>You&rsquo;re Subscribed!</h2>
    <p>
      Welcome to the Odili Truth Seeker family.<br>
      A welcome email is on its way &mdash; check your inbox (and your spam folder, just in case).
    </p>
    <div class="footer" style="margin-top:24px">
      Newsletters arrive every Sunday, Wednesday &amp; Friday at 9&nbsp;AM&nbsp;UTC.<br>
      You can unsubscribe at any time via the link in each email.
    </div>
  </div>

</div>

<script>
  async function handleSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('email').value.trim();
    const name  = document.getElementById('name').value.trim();
    const msg   = document.getElementById('msg');
    const btn   = document.getElementById('sub-btn');

    msg.className = 'msg';
    msg.textContent = '';

    if (!email) {
      msg.className = 'msg error';
      msg.textContent = 'Please enter your email address.';
      return;
    }

    btn.disabled    = true;
    btn.textContent = 'Subscribing…';

    try {
      const res = await fetch('/emails', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, name: name || undefined }),
      });

      if (res.status === 409) {
        msg.className   = 'msg error';
        msg.textContent = 'This email is already subscribed — check your inbox for our next newsletter!';
        btn.disabled    = false;
        btn.textContent = 'Subscribe — It\\u2019s Free';
        return;
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        msg.className   = 'msg error';
        msg.textContent = data.detail || 'Something went wrong. Please try again in a moment.';
        btn.disabled    = false;
        btn.textContent = 'Subscribe — It\\u2019s Free';
        return;
      }

      // Success
      document.getElementById('form-state').style.display    = 'none';
      document.getElementById('success-state').style.display = 'block';

    } catch (err) {
      msg.className   = 'msg error';
      msg.textContent = 'Network error — please check your connection and try again.';
      btn.disabled    = false;
      btn.textContent = 'Subscribe — It\\u2019s Free';
    }
  }
</script>

</body>
</html>"""

_SUBSCRIBE_HTML = _SUBSCRIBE_HTML.replace("__ODILI_HEADER_CSS__", HEADER_CSS)
_SUBSCRIBE_HTML = _SUBSCRIBE_HTML.replace("__ODILI_HEADER_HTML__", header_html())


@router.get("/subscribe", response_class=HTMLResponse, include_in_schema=False)
async def subscribe_page() -> HTMLResponse:
    """Public-facing subscriber sign-up landing page."""
    return HTMLResponse(content=_SUBSCRIBE_HTML)
