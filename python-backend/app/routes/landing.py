from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.branding import HEADER_CSS, header_html, LOGO_URL, APP_NAME, YOUTUBE_URL

router = APIRouter()

_LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" type="image/png" href="/static/logo.png">
  <title>Odili — The Seeker of Truth · Catholic Truth, History & Apologetics</title>
  <meta name="description" content="Join the mission of Odili — The Seeker of Truth. Catholic truth, history, and apologetics on YouTube. Subscribe, vote on what we cover next, and seek the truth.">
  <script>document.documentElement.classList.add('js');</script>
  __ODILI_HEADER_CSS__
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --gold:    #FFD700;
      --gold-dk: #c8a426;
      --red:     #8B0000;
      --red-lt:  #b81818;
      --black:   #000000;
      --panel:   #0c0c0e;
      --panel-2: #131316;
      --text:    #f5f1e6;
      --muted:   #9a948a;
      --border:  #26221b;
    }

    html { scroll-behavior: smooth; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: var(--black);
      color: var(--text);
      overflow-x: hidden;
      line-height: 1.6;
    }

    h1, h2, h3, .serif { font-family: Georgia, 'Times New Roman', serif; }

    .wrap { max-width: 1080px; margin: 0 auto; padding: 0 22px; }

    /* ── Ambient glow backdrop ── */
    .glow-field {
      position: fixed; inset: 0; z-index: 0; pointer-events: none;
      background:
        radial-gradient(620px 420px at 50% -8%, rgba(255,215,0,.16), transparent 70%),
        radial-gradient(520px 380px at 12% 18%, rgba(139,0,0,.22), transparent 72%),
        radial-gradient(560px 420px at 92% 30%, rgba(255,140,0,.10), transparent 72%);
    }
    main { position: relative; z-index: 1; }

    /* ── Reveal animation ── */
    .js .reveal {
      opacity: 0; transform: translateY(34px);
      transition: opacity .9s cubic-bezier(.2,.7,.2,1), transform .9s cubic-bezier(.2,.7,.2,1);
    }
    .js .reveal.in { opacity: 1; transform: none; }

    /* ── HERO ── */
    .hero {
      min-height: 100vh;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      text-align: center; padding: 150px 22px 90px;
    }
    .hero-logo {
      width: 132px; height: 132px; object-fit: contain;
      border-radius: 22px; background: #000; padding: 10px;
      margin-bottom: 28px;
      filter: drop-shadow(0 0 26px rgba(255,215,0,.45));
      animation: floaty 6s ease-in-out infinite;
    }
    @keyframes floaty { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-12px); } }

    .eyebrow {
      font-size: 13px; letter-spacing: 3.5px; text-transform: uppercase;
      color: var(--gold); font-weight: 700; margin-bottom: 20px; opacity: .9;
    }
    .hero h1 {
      font-size: clamp(34px, 6.2vw, 68px); line-height: 1.06; font-weight: 700;
      letter-spacing: -1px; margin-bottom: 22px; max-width: 980px;
    }
    .hero h1 .accent {
      background: linear-gradient(105deg, var(--gold) 0%, #ff9d2f 55%, var(--gold) 100%);
      -webkit-background-clip: text; background-clip: text; color: transparent;
    }
    .hero p.sub {
      font-size: clamp(16px, 2.2vw, 21px); color: var(--muted);
      max-width: 680px; margin: 0 auto 40px;
    }

    /* ── Buttons ── */
    .cta-row { display: flex; gap: 16px; flex-wrap: wrap; justify-content: center; }
    .urgency-pill {
      display: inline-flex; align-items: center; gap: 8px; margin-bottom: 26px;
      padding: 9px 18px; border-radius: 999px; font-size: 13.5px; font-weight: 700;
      letter-spacing: .3px; color: var(--gold);
      background: rgba(255,215,0,.07); border: 1px solid rgba(255,215,0,.32);
    }
    .btn {
      display: inline-flex; align-items: center; justify-content: center; gap: 9px;
      font-size: 16px; font-weight: 700; letter-spacing: .3px;
      padding: 16px 32px; border-radius: 12px; cursor: pointer;
      text-decoration: none; border: 1.5px solid transparent;
      transition: transform .18s ease, box-shadow .25s ease, background .2s ease, color .2s ease;
      font-family: inherit;
    }
    .btn-primary {
      background: linear-gradient(100deg, var(--gold) 0%, #ffb43d 100%);
      color: #1a1300; box-shadow: 0 0 0 rgba(255,215,0,0);
      animation: pulseGlow 3s ease-in-out infinite;
    }
    @keyframes pulseGlow {
      0%,100% { box-shadow: 0 0 22px rgba(255,215,0,.28); }
      50%     { box-shadow: 0 0 42px rgba(255,215,0,.6); }
    }
    .btn-primary:hover { transform: scale(1.05) translateY(-1px); box-shadow: 0 0 52px rgba(255,215,0,.75); }
    .btn-ghost { background: rgba(255,255,255,.03); color: var(--text); border-color: rgba(255,215,0,.4); }
    .btn-ghost:hover { transform: scale(1.05) translateY(-1px); border-color: var(--gold); color: var(--gold); box-shadow: 0 0 30px rgba(255,215,0,.3); }
    .btn-red { background: linear-gradient(100deg, var(--red) 0%, var(--red-lt) 100%); color: #fff; }
    .btn-red:hover { transform: scale(1.05) translateY(-1px); box-shadow: 0 0 34px rgba(184,24,24,.55); }
    .btn:active { transform: scale(.98); }
    .btn:disabled { opacity: .6; cursor: not-allowed; transform: none; animation: none; }

    /* ── Section heading ── */
    .section { padding: 92px 0; }
    .section-head { text-align: center; max-width: 680px; margin: 0 auto 56px; }
    .section-head h2 { font-size: clamp(28px, 4.4vw, 44px); letter-spacing: -.5px; margin-bottom: 14px; }
    .section-head .gold { color: var(--gold); }
    .section-head p { color: var(--muted); font-size: 17px; }

    /* ── MISSION manifesto ── */
    .mission { background: radial-gradient(720px 320px at 50% 0%, rgba(139,0,0,.16), transparent 70%); }
    .pillars { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; max-width: 880px; margin: 0 auto; }
    .pillar {
      background: linear-gradient(180deg, var(--panel-2), var(--panel));
      border: 1px solid var(--border); border-radius: 18px; padding: 30px 24px; text-align: center;
      transition: transform .25s ease, border-color .25s ease, box-shadow .3s ease;
    }
    .pillar:hover { transform: translateY(-6px); border-color: rgba(255,215,0,.35); box-shadow: 0 20px 44px rgba(0,0,0,.5); }
    .pillar .picon { font-size: 30px; margin-bottom: 12px; }
    .pillar h3 { font-size: 19px; color: var(--gold); margin-bottom: 8px; }
    .pillar p { font-size: 14.5px; color: var(--muted); }

    /* ── Email capture ── */
    .capture-card {
      max-width: 680px; margin: 0 auto;
      background: linear-gradient(180deg, var(--panel-2), var(--panel));
      border: 1px solid rgba(255,215,0,.22); border-radius: 22px; padding: 48px 40px;
      text-align: center; box-shadow: 0 24px 60px rgba(0,0,0,.45); position: relative; overflow: hidden;
    }
    .capture-card .badge {
      display: inline-block; font-size: 12px; letter-spacing: 2px; text-transform: uppercase;
      color: var(--gold); font-weight: 700; margin-bottom: 16px;
      padding: 6px 14px; border: 1px solid rgba(255,215,0,.35); border-radius: 999px; background: rgba(255,215,0,.06);
    }
    .capture-card h2 { font-size: clamp(26px, 4vw, 38px); margin-bottom: 12px; line-height: 1.15; }
    .capture-card h2 .gold { color: var(--gold); }
    .capture-card p.lead { color: var(--muted); margin-bottom: 28px; font-size: 16px; }
    .capture-form { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; }
    .capture-form input {
      flex: 1; min-width: 240px; padding: 16px 18px; font-size: 16px;
      border-radius: 12px; border: 1px solid var(--border);
      background: #060606; color: var(--text); outline: none; transition: border .2s, box-shadow .2s; font-family: inherit;
    }
    .capture-form input:focus { border-color: var(--gold); box-shadow: 0 0 0 3px rgba(255,215,0,.14); }
    .capture-form input::placeholder { color: #6d685f; }
    .capture-fine { margin-top: 14px; font-size: 12.5px; color: #6d685f; }
    .capture-msg { display: none; margin-top: 20px; font-size: 15px; border-radius: 10px; padding: 14px 16px; }
    .capture-msg.ok  { display: block; background: rgba(46,125,50,.14); color: #8fe29a; border: 1px solid rgba(46,125,50,.4); }
    .capture-msg.err { display: block; background: rgba(192,57,43,.14); color: #f0a59e; border: 1px solid rgba(192,57,43,.4); }

    /* ── Topic entry buttons (fast conversion → prefill interest) ── */
    .topic-entry { max-width: 760px; margin: 0 auto; text-align: center; }
    .topic-entry .mark { font-size: 13px; letter-spacing: 3px; text-transform: uppercase; color: var(--muted); margin-bottom: 18px; }
    .topic-btns { display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; }
    .topic-btn {
      font-family: inherit; font-size: 15px; font-weight: 700; cursor: pointer;
      padding: 12px 22px; border-radius: 999px; color: var(--gold);
      background: rgba(255,215,0,.06); border: 1px solid rgba(255,215,0,.32);
      transition: background .2s, transform .15s, box-shadow .2s, color .2s;
    }
    .topic-btn:hover { background: rgba(255,215,0,.16); transform: translateY(-2px); box-shadow: 0 0 22px rgba(255,215,0,.28); }
    .topic-btn:active { transform: scale(.96); }
    .interest-chip { display: none; margin-bottom: 18px; font-size: 14.5px; color: var(--gold); }
    .interest-chip.show { display: block; }

    /* ── TOPIC ENGAGEMENT ── */
    .topics { background: radial-gradient(680px 300px at 50% 0%, rgba(255,215,0,.08), transparent 70%); }
    .topic-list { display: grid; gap: 12px; max-width: 760px; margin: 0 auto; }
    .topic-card {
      display: flex; align-items: center; gap: 16px;
      background: var(--panel); border: 1px solid var(--border); border-left: 3px solid var(--gold-dk);
      border-radius: 14px; padding: 16px 18px; transition: border-color .2s, transform .2s;
    }
    .topic-card:hover { border-color: rgba(255,215,0,.3); transform: translateY(-2px); }
    .topic-main { flex: 1; min-width: 0; }
    .topic-title { font-size: 16px; font-weight: 600; color: var(--text); }
    .topic-desc { font-size: 13.5px; color: var(--muted); margin-top: 3px; }
    .vote-btn {
      display: flex; flex-direction: column; align-items: center; gap: 2px; flex-shrink: 0;
      min-width: 64px; padding: 10px 14px; border-radius: 12px; cursor: pointer; font-family: inherit;
      background: rgba(255,215,0,.06); border: 1px solid rgba(255,215,0,.32); color: var(--gold);
      font-weight: 700; transition: background .2s, transform .15s, box-shadow .2s;
    }
    .vote-btn:hover:not(:disabled) { background: rgba(255,215,0,.14); transform: translateY(-2px); box-shadow: 0 0 22px rgba(255,215,0,.25); }
    .vote-btn:active { transform: scale(.95); }
    .vote-btn:disabled { cursor: default; opacity: .85; }
    .vote-btn.voted { background: linear-gradient(100deg, var(--gold), #ffb43d); color: #1a1300; border-color: transparent; }
    .vote-arrow { font-size: 15px; line-height: 1; }
    .vote-count { font-size: 18px; line-height: 1.1; }
    .vote-label { font-size: 10px; letter-spacing: .5px; text-transform: uppercase; font-weight: 700; opacity: .8; }
    .topics-empty { text-align: center; color: var(--muted); padding: 20px; }

    .request-card {
      max-width: 620px; margin: 44px auto 0;
      background: linear-gradient(180deg, var(--panel-2), var(--panel));
      border: 1px solid var(--border); border-radius: 20px; padding: 34px 30px; text-align: center;
    }
    .request-card h3 { font-size: 22px; margin-bottom: 8px; }
    .request-card h3 .gold { color: var(--gold); }
    .request-card p.lead { color: var(--muted); margin-bottom: 22px; font-size: 15px; }
    .request-form { display: flex; flex-direction: column; gap: 12px; }
    .request-form input, .request-form textarea {
      width: 100%; padding: 14px 16px; font-size: 15px; border-radius: 12px;
      border: 1px solid var(--border); background: #060606; color: var(--text); outline: none;
      transition: border .2s, box-shadow .2s; font-family: inherit; resize: vertical;
    }
    .request-form input:focus, .request-form textarea:focus { border-color: var(--gold); box-shadow: 0 0 0 3px rgba(255,215,0,.14); }
    .request-form input::placeholder, .request-form textarea::placeholder { color: #6d685f; }
    .request-msg { display: none; margin-top: 6px; font-size: 14px; border-radius: 10px; padding: 12px 14px; }
    .request-msg.ok  { display: block; background: rgba(46,125,50,.14); color: #8fe29a; border: 1px solid rgba(46,125,50,.4); }
    .request-msg.err { display: block; background: rgba(192,57,43,.14); color: #f0a59e; border: 1px solid rgba(192,57,43,.4); }

    /* ── YOUTUBE BRIDGE ── */
    .bridge {
      text-align: center;
      background: radial-gradient(700px 260px at 50% 50%, rgba(139,0,0,.30), transparent 70%);
      border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); padding: 90px 22px;
    }
    .bridge .mark { font-size: 13px; letter-spacing: 3px; text-transform: uppercase; color: var(--muted); margin-bottom: 14px; }
    .bridge h2 { font-size: clamp(28px, 4.6vw, 46px); margin-bottom: 14px; }
    .bridge h2 .gold { color: var(--gold); }
    .bridge p { color: var(--muted); max-width: 560px; margin: 0 auto 30px; font-size: 16px; }

    /* ── TRUST / AUTHORITY ── */
    .trust { text-align: center; padding: 88px 22px; background: radial-gradient(620px 300px at 50% 50%, rgba(255,215,0,.10), transparent 70%); }
    .trust-logo {
      width: 108px; height: 108px; object-fit: contain; border-radius: 20px;
      background: #000; padding: 10px; margin: 0 auto 22px; display: block;
      filter: drop-shadow(0 0 28px rgba(255,215,0,.55)); animation: floaty 6s ease-in-out infinite;
    }
    .trust .mark { font-size: 13px; letter-spacing: 3px; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; }
    .trust h2 { font-size: clamp(24px, 4vw, 40px); margin-bottom: 16px; }
    .trust h2 .gold { color: var(--gold); }
    .trust p { color: var(--muted); max-width: 560px; margin: 0 auto; font-size: 16px; }

    /* ── FOOTER CTA ── */
    .footer-cta { text-align: center; padding: 96px 22px; background: linear-gradient(180deg, transparent, rgba(139,0,0,.14)); }
    .footer-cta h2 { font-size: clamp(28px, 5vw, 52px); margin-bottom: 26px; letter-spacing: -.5px; }
    .footer-cta h2 .gold { color: var(--gold); }

    /* ── Footer ── */
    footer { text-align: center; padding: 56px 22px 48px; border-top: 1px solid var(--border); background: #050505; }
    .foot-logo {
      width: 64px; height: 64px; object-fit: contain; border-radius: 14px;
      background: #000; padding: 6px; margin: 0 auto 16px; display: block; filter: drop-shadow(0 0 14px rgba(255,215,0,.4));
    }
    .foot-name { color: var(--gold); font-family: Georgia, serif; font-size: 18px; font-weight: 700; margin-bottom: 18px; }
    .foot-links { display: flex; gap: 20px; justify-content: center; margin-bottom: 22px; flex-wrap: wrap; }
    .foot-links a { color: var(--muted); text-decoration: none; font-size: 14px; font-weight: 600; transition: color .2s; }
    .foot-links a:hover { color: var(--gold); }
    .foot-copy { color: #5d574e; font-size: 13px; }

    @media (max-width: 820px) {
      .pillars { grid-template-columns: 1fr; max-width: 420px; }
    }
    @media (max-width: 560px) {
      .section { padding: 70px 0; }
      .hero { padding: 130px 18px 70px; }
      .capture-card { padding: 36px 24px; }
      .btn { width: 100%; }
      .cta-row { width: 100%; }
      .topic-card { flex-direction: row; }
    }
  </style>
</head>
<body>
__ODILI_HEADER_HTML__
<div class="glow-field"></div>
<main>

  <!-- ── SECTION 1 · HERO ── -->
  <section class="hero">
    <img class="hero-logo" src="__LOGO_URL__" alt="__APP_NAME__ logo">
    <div class="eyebrow reveal">Catholic Truth · History · Apologetics</div>
    <h1 class="reveal">Seek the Truth.<br><span class="accent">Grow the Message.</span></h1>
    <p class="sub reveal">Discover the truth of the Catholic faith. Watch powerful teachings. Ask the questions others are afraid to answer.</p>
    <div class="urgency-pill reveal">🔥 New truth-driven videos every week</div>
    <div class="cta-row reveal">
      <a class="btn btn-primary" href="#capture">Join the Mission</a>
      <a class="btn btn-red" href="__YOUTUBE_URL__" target="_blank" rel="noopener">▶ Watch on YouTube</a>
    </div>
  </section>

  <!-- ── SECTION 2 · MISSION ── -->
  <section class="section mission">
    <div class="wrap">
      <div class="section-head reveal">
        <div class="mark" style="font-size:13px;letter-spacing:3px;text-transform:uppercase;color:var(--muted);margin-bottom:12px">Built by Odili — The Seeker of Truth</div>
        <h2>Find the truth. <span class="gold">Grow in faith.</span></h2>
        <p>Defending truth. Exposing error. Leading souls to Christ.</p>
      </div>
      <div class="pillars reveal">
        <div class="pillar">
          <div class="picon">🔥</div>
          <h3>Find the Truth</h3>
          <p>Clear answers to difficult Catholic questions.</p>
        </div>
        <div class="pillar">
          <div class="picon">📜</div>
          <h3>Grow in Faith</h3>
          <p>Scripture and Tradition explained simply.</p>
        </div>
        <div class="pillar">
          <div class="picon">🛡️</div>
          <h3>Ask Anything</h3>
          <p>Submit questions for future videos.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- ── SECTION 3a · TOPIC ENTRY POINTS (fast conversion) ── -->
  <section class="section wrap" style="padding-bottom:0">
    <div class="topic-entry reveal">
      <div class="mark">Where do you want to begin?</div>
      <div class="topic-btns">
        <button type="button" class="topic-btn" onclick="pickInterest('Salvation')">Salvation</button>
        <button type="button" class="topic-btn" onclick="pickInterest('The Eucharist')">The Eucharist</button>
        <button type="button" class="topic-btn" onclick="pickInterest('The Papacy')">The Papacy</button>
        <button type="button" class="topic-btn" onclick="pickInterest('Mary &amp; the Saints')">Mary &amp; the Saints</button>
        <button type="button" class="topic-btn" onclick="pickInterest('False Doctrines')">False Doctrines</button>
      </div>
    </div>
  </section>

  <!-- ── SECTION 3 · EMAIL CAPTURE ── -->
  <section class="section wrap" id="capture">
    <div class="capture-card reveal">
      <span class="badge">Join the Mission</span>
      <h2>Truth, straight to <span class="gold">your inbox</span></h2>
      <p class="lead">Be the first to know when a new video drops — plus reflections and Catholic truth you can share. No noise, just the mission.</p>
      <div id="interest-chip" class="interest-chip"></div>
      <form class="capture-form" id="capture-form" onsubmit="joinMission(event)" novalidate>
        <input type="hidden" id="capture-interest" value="">
        <input type="email" id="capture-email" placeholder="you@example.com" required autocomplete="email" aria-label="Email address">
        <button type="submit" class="btn btn-primary" id="capture-btn">Join the Mission</button>
      </form>
      <div class="capture-fine">No spam. Unsubscribe anytime with one click.</div>
      <div id="capture-msg" class="capture-msg"></div>
    </div>
  </section>

  <!-- ── SECTION 4 · TOPIC ENGAGEMENT ── -->
  <section class="section topics">
    <div class="wrap">
      <div class="section-head reveal">
        <h2>Ask a Question or <span class="gold">Suggest a Topic</span></h2>
        <p>Vote on what the mission covers next — or send in your own question. Your voice shapes the channel.</p>
      </div>
      <div class="topic-list reveal" id="topic-list">
        <div class="topics-empty">Loading topics…</div>
      </div>

      <div class="request-card reveal">
        <h3>Have a topic in mind? <span class="gold">Request it.</span></h3>
        <p class="lead">Is there a question, a doubt, or a truth you want Odili to explore? Send it in.</p>
        <form class="request-form" id="request-form" onsubmit="submitTopic(event)" novalidate>
          <input type="text" id="request-title" placeholder="The topic you'd like covered…" maxlength="200" required aria-label="Topic title">
          <textarea id="request-desc" placeholder="Add any detail (optional)…" rows="3" maxlength="500" aria-label="Topic detail"></textarea>
          <button type="submit" class="btn btn-primary" id="request-btn">Submit Topic</button>
        </form>
        <div id="request-msg" class="request-msg"></div>
      </div>
    </div>
  </section>

  <!-- ── SECTION 5 · YOUTUBE BRIDGE ── -->
  <section class="bridge reveal">
    <div class="mark">The Channel</div>
    <h2>Watch the <span class="gold">Truth in Action</span></h2>
    <p>Real Catholic truth, history, and apologetics — published every week on YouTube.</p>
    <div class="cta-row">
      <a class="btn btn-red" href="__YOUTUBE_URL__" target="_blank" rel="noopener">▶ Visit the Channel</a>
      <a class="btn btn-ghost" href="__YOUTUBE_URL__/videos" target="_blank" rel="noopener">Browse Videos</a>
    </div>
  </section>

  <!-- ── SECTION 6 · AUTHORITY / TRUST ── -->
  <section class="trust reveal">
    <img class="trust-logo" src="__LOGO_URL__" alt="__APP_NAME__ logo">
    <div class="mark">The Voice</div>
    <h2>Odili — <span class="gold">The Seeker of Truth</span></h2>
    <p>A Catholic media ministry devoted to seeking, revealing, and defending the truth — for the glory of God and the good of souls.</p>
  </section>

  <!-- ── SECTION 7 · FOOTER CTA ── -->
  <section class="footer-cta reveal">
    <h2>Don't Just Watch Truth.<br><span class="gold">Live It.</span></h2>
    <div class="cta-row">
      <a class="btn btn-primary" href="#capture">Join the Mission</a>
      <a class="btn btn-red" href="__YOUTUBE_URL__" target="_blank" rel="noopener">▶ Watch on YouTube</a>
    </div>
  </section>

  <!-- ── FOOTER ── -->
  <footer>
    <img class="foot-logo" src="__LOGO_URL__" alt="__APP_NAME__ logo">
    <div class="foot-name">__APP_NAME__</div>
    <div class="foot-links">
      <a href="#capture">Subscribe</a>
      <a href="#topic-list">Topics</a>
      <a href="__YOUTUBE_URL__" target="_blank" rel="noopener">YouTube</a>
    </div>
    <div class="foot-copy">© Odili Truth Seeker</div>
  </footer>

</main>

<script>
  // ── Scroll reveal ──
  const revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) { entry.target.classList.add('in'); io.unobserve(entry.target); }
      });
    }, { threshold: 0.12 });
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add('in'));
  }

  function escHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ── Topic entry buttons → prefill interest + scroll to capture ──
  function pickInterest(topic) {
    const hidden = document.getElementById('capture-interest');
    const chip   = document.getElementById('interest-chip');
    if (hidden) hidden.value = topic;
    if (chip) {
      chip.innerHTML = '✓ Exploring: <strong>' + escHtml(topic) + '</strong>';
      chip.classList.add('show');
    }
    const cap = document.getElementById('capture');
    if (cap) cap.scrollIntoView({ behavior: 'smooth' });
    const inp = document.getElementById('capture-email');
    if (inp) setTimeout(function () { inp.focus(); }, 480);
  }

  // ── Email capture (feeds the mailing list + starts the drip sequence) ──
  async function joinMission(e) {
    e.preventDefault();
    const email = document.getElementById('capture-email').value.trim();
    const interestEl = document.getElementById('capture-interest');
    const interest = (interestEl && interestEl.value.trim()) ? interestEl.value.trim() : null;
    const btn   = document.getElementById('capture-btn');
    const msg   = document.getElementById('capture-msg');
    msg.className = 'capture-msg';

    if (!email) { msg.className = 'capture-msg err'; msg.textContent = 'Please enter your email address.'; return; }

    btn.disabled = true;
    const original = btn.textContent;
    btn.textContent = 'Joining…';

    try {
      const res = await fetch('/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, interest: interest })
      });
      if (res.status === 409) {
        msg.className = 'capture-msg ok';
        msg.textContent = "You're already part of the mission — welcome back.";
      } else if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        msg.className = 'capture-msg err';
        msg.textContent = (d && d.detail) ? d.detail : 'Something went wrong. Please try again.';
      } else {
        msg.className = 'capture-msg ok';
        msg.textContent = "✓ Welcome to the mission — check your inbox.";
        document.getElementById('capture-email').value = '';
      }
    } catch (err) {
      msg.className = 'capture-msg err';
      msg.textContent = 'Network error — please check your connection and try again.';
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  }

  // ── Topic engagement ──
  const VOTED_KEY = 'odili_voted_topics';
  function votedSet() {
    try { return new Set(JSON.parse(localStorage.getItem(VOTED_KEY) || '[]')); }
    catch (e) { return new Set(); }
  }
  function rememberVote(id) {
    const s = votedSet(); s.add(id);
    try { localStorage.setItem(VOTED_KEY, JSON.stringify([...s])); } catch (e) {}
  }

  async function loadTopics() {
    const box = document.getElementById('topic-list');
    try {
      const res = await fetch('/topics');
      const data = await res.json();
      const topics = (data && data.topics) || [];
      if (!topics.length) {
        box.innerHTML = '<div class="topics-empty">No topics yet — be the first to suggest one below.</div>';
        return;
      }
      const voted = votedSet();
      box.innerHTML = topics.map((t) => {
        const isVoted = voted.has(t.id);
        const desc = t.description ? '<div class="topic-desc">' + escHtml(t.description) + '</div>' : '';
        return '<div class="topic-card">' +
            '<div class="topic-main"><div class="topic-title">' + escHtml(t.title) + '</div>' + desc + '</div>' +
            '<button class="vote-btn' + (isVoted ? ' voted' : '') + '" data-id="' + t.id + '"' + (isVoted ? ' disabled' : '') +
              ' onclick="voteTopic(' + t.id + ', this)" aria-label="Vote for this topic">' +
              '<span class="vote-arrow">▲</span>' +
              '<span class="vote-count" id="vc-' + t.id + '">' + (t.votes || 0) + '</span>' +
              '<span class="vote-label">vote' + ((t.votes === 1) ? '' : 's') + '</span>' +
            '</button>' +
          '</div>';
      }).join('');
    } catch (err) {
      box.innerHTML = '<div class="topics-empty">Could not load topics. Please refresh.</div>';
    }
  }

  async function voteTopic(id, btn) {
    if (btn.disabled) return;
    btn.disabled = true;
    try {
      const res = await fetch('/topics/' + id + '/vote', { method: 'POST' });
      if (!res.ok) { btn.disabled = false; return; }
      const data = await res.json();
      const vc = document.getElementById('vc-' + id);
      if (vc) vc.textContent = data.votes;
      btn.classList.add('voted');
      rememberVote(id);
    } catch (err) {
      btn.disabled = false;
    }
  }

  async function submitTopic(e) {
    e.preventDefault();
    const title = document.getElementById('request-title').value.trim();
    const desc  = document.getElementById('request-desc').value.trim();
    const btn   = document.getElementById('request-btn');
    const msg   = document.getElementById('request-msg');
    msg.className = 'request-msg';

    if (title.length < 5) { msg.className = 'request-msg err'; msg.textContent = 'Please describe the topic in at least 5 characters.'; return; }

    btn.disabled = true;
    const original = btn.textContent;
    btn.textContent = 'Submitting…';

    try {
      const res = await fetch('/topics/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description: desc || null })
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        let detail = 'Something went wrong. Please try again.';
        if (d && d.detail) detail = (typeof d.detail === 'string') ? d.detail : (d.detail[0] && d.detail[0].msg) || detail;
        msg.className = 'request-msg err';
        msg.textContent = detail;
      } else {
        msg.className = 'request-msg ok';
        msg.textContent = '✓ Thank you — your topic has been submitted for review.';
        document.getElementById('request-title').value = '';
        document.getElementById('request-desc').value = '';
      }
    } catch (err) {
      msg.className = 'request-msg err';
      msg.textContent = 'Network error — please try again.';
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  }

  loadTopics();
</script>

</body>
</html>"""

_LANDING_HTML = _LANDING_HTML.replace("__ODILI_HEADER_CSS__", HEADER_CSS)
_LANDING_HTML = _LANDING_HTML.replace("__ODILI_HEADER_HTML__", header_html())
_LANDING_HTML = _LANDING_HTML.replace("__LOGO_URL__", LOGO_URL)
_LANDING_HTML = _LANDING_HTML.replace("__APP_NAME__", APP_NAME)
_LANDING_HTML = _LANDING_HTML.replace("__YOUTUBE_URL__", YOUTUBE_URL)


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page() -> HTMLResponse:
    """Public evangelization funnel for Odili — The Seeker of Truth. No internal tools."""
    return HTMLResponse(content=_LANDING_HTML)
