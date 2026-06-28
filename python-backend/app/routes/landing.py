import json

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.branding import HEADER_CSS, header_html, social_icons_html, LOGO_URL, APP_NAME, YOUTUBE_URL, FEATURED_VIDEO_ID, INTRO_VIDEO_IDS
from app.services.headlines import HEADLINES

router = APIRouter()

_LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" type="image/png" href="/static/logo.png">
  <title>Odili — The Seeker of Truth · Catholic Truth, History & Apologetics</title>
  <meta name="description" content="You weren't taught everything about salvation. Short, focused teachings backed by Scripture, the Church Fathers, and the early Church — finishing the picture.">
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
      min-height: 96vh;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      text-align: center; padding: 140px 22px 70px;
    }
    .hero-logo {
      display: block;
      width: 140px; max-width: 140px; height: auto;
      border-radius: 18px; background: #000;
      margin: 0 auto 26px;
      filter: drop-shadow(0 0 30px rgba(255,150,0,.5));
      animation: floaty 6s ease-in-out infinite;
    }
    @keyframes floaty { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-12px); } }
    /* Flickering "fire" glow around the logo (PNG can't be layer-isolated, so we
       animate a warm drop-shadow flicker to evoke the flame in the mark). */
    @keyframes fireGlow {
      0%,100% { filter: drop-shadow(0 0 20px rgba(255,150,0,.45)) drop-shadow(0 0 9px rgba(255,215,0,.40)); }
      40%     { filter: drop-shadow(0 0 40px rgba(255,110,0,.80)) drop-shadow(0 0 16px rgba(255,215,0,.65)); }
      65%     { filter: drop-shadow(0 0 26px rgba(255,80,0,.55))  drop-shadow(0 0 12px rgba(255,180,0,.55)); }
    }
    @media (prefers-reduced-motion: reduce) {
      .hero-logo { animation: none; }
    }

    .eyebrow {
      font-size: 13px; letter-spacing: 3.5px; text-transform: uppercase;
      color: var(--gold); font-weight: 700; margin-bottom: 20px; opacity: .9;
    }
    .hero h1 {
      font-size: clamp(32px, 5.6vw, 60px); line-height: 1.1; font-weight: 700;
      letter-spacing: -.5px; margin-bottom: 22px; max-width: 940px;
    }
    .hero h1 .accent {
      background: linear-gradient(105deg, var(--gold) 0%, #ff9d2f 55%, var(--gold) 100%);
      -webkit-background-clip: text; background-clip: text; color: transparent;
    }
    .hero p.sub {
      font-size: clamp(16px, 2.2vw, 21px); color: var(--muted);
      max-width: 700px; margin: 0 auto 36px;
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
    .section { padding: 88px 0; }
    .section-head { text-align: center; max-width: 720px; margin: 0 auto 50px; }
    .section-head .mark { font-size: 13px; letter-spacing: 3px; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; }
    .section-head h2 { font-size: clamp(28px, 4.4vw, 44px); letter-spacing: -.5px; margin-bottom: 14px; }
    .section-head .gold { color: var(--gold); }
    .section-head p { color: var(--muted); font-size: 17px; }

    /* ── Email capture ── */
    .capture { padding-top: 0; }
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
    .interest-chip { display: none; margin-bottom: 18px; font-size: 14.5px; color: var(--gold); }
    .interest-chip.show { display: block; }

    /* ── START HERE video ── */
    .video-section { text-align: center; }
    .video-frame {
      position: relative; display: flex; align-items: center; justify-content: center;
      max-width: 840px; margin: 0 auto 30px; aspect-ratio: 16 / 9;
      border-radius: 20px; overflow: hidden; cursor: pointer; text-decoration: none;
      border: 1px solid rgba(255,215,0,.25);
      background: radial-gradient(circle at 50% 38%, rgba(139,0,0,.55), #090909 72%);
      box-shadow: 0 30px 70px rgba(0,0,0,.55);
      transition: transform .25s ease, box-shadow .3s ease, border-color .2s ease;
    }
    .video-frame:hover { transform: translateY(-4px); border-color: rgba(255,215,0,.5); box-shadow: 0 0 60px rgba(255,215,0,.28); }
    .video-frame--embed { cursor: default; }
    .video-frame--embed:hover { transform: none; box-shadow: 0 30px 70px rgba(0,0,0,.55); border-color: rgba(255,215,0,.25); }
    .video-frame iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; z-index: 3; }
    .video-poster { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; opacity: .14; }
    .video-poster img { width: 58%; max-width: 360px; }
    .video-play {
      position: relative; z-index: 2;
      width: 92px; height: 92px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      background: linear-gradient(100deg, var(--gold), #ffb43d); color: #1a1300;
      font-size: 32px; padding-left: 6px;
      box-shadow: 0 0 40px rgba(255,215,0,.6); animation: pulseGlow 3s ease-in-out infinite;
    }
    .video-frame .vlabel {
      position: absolute; bottom: 16px; left: 0; right: 0; z-index: 2;
      color: var(--text); font-weight: 700; font-size: 14.5px; letter-spacing: .3px;
    }
    /* Thumbnail fallback (sits behind the iframe; visible if the embed fails) */
    .video-fallback { position: absolute; inset: 0; z-index: 1; display: flex; align-items: center; justify-content: center; text-decoration: none; }

    /* ── CONTENT HUB (latest shorts, playlists, community) ── */
    .hub-shorts { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 16px; margin-bottom: 34px; }
    .hub-short { display: block; text-decoration: none; border-radius: 14px; overflow: hidden; border: 1px solid var(--border); background: var(--panel); transition: transform .2s, border-color .2s, box-shadow .3s; }
    .hub-short:hover { transform: translateY(-4px); border-color: rgba(255,215,0,.42); box-shadow: 0 14px 32px rgba(0,0,0,.45); }
    .hub-short .thumb { aspect-ratio: 16 / 9; background: #000 center/cover no-repeat; }
    .hub-short .stitle { padding: 11px 13px; font-size: 13.5px; font-weight: 600; color: var(--text); line-height: 1.35; }
    .hub-playlists { display: grid; gap: 12px; max-width: 760px; margin: 0 auto 28px; }
    .hub-playlist { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 16px 18px; border-radius: 14px; border: 1px solid var(--border); border-left: 3px solid var(--gold-dk); background: var(--panel); text-decoration: none; color: var(--text); transition: border-color .2s, transform .2s; }
    .hub-playlist:hover { border-color: rgba(255,215,0,.35); transform: translateY(-2px); }
    .hub-playlist .ptitle { font-weight: 600; }
    .hub-playlist .parrow { color: var(--gold); font-weight: 700; white-space: nowrap; }
    .hub-community { text-align: center; }

    /* Trending badge on voted topics */
    .topic-badge { display: inline-block; margin-left: 8px; font-size: 10.5px; font-weight: 700; letter-spacing: .5px; text-transform: uppercase; color: #1a1300; background: linear-gradient(100deg, var(--gold), #ffb43d); padding: 2px 9px; border-radius: 999px; vertical-align: middle; }

    /* Free-text "Other" interest field in the capture card */
    .capture-other { flex-basis: 100%; min-width: 100% !important; display: none; }
    .capture-other.show { display: block; }

    /* ── Topic entry buttons (fast conversion → prefill interest) ── */
    .topic-entry { max-width: 760px; margin: 0 auto; text-align: center; }
    .topic-entry .mark { font-size: 13px; letter-spacing: 3px; text-transform: uppercase; color: var(--muted); margin-bottom: 18px; }
    .topic-btns { display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; }
    .topic-btn {
      font-family: inherit; font-size: 15px; font-weight: 700; cursor: pointer;
      padding: 13px 24px; border-radius: 999px; color: var(--gold);
      background: rgba(255,215,0,.06); border: 1px solid rgba(255,215,0,.32);
      transition: background .2s, transform .15s, box-shadow .2s, color .2s;
    }
    .topic-btn:hover { background: rgba(255,215,0,.16); transform: translateY(-2px); box-shadow: 0 0 22px rgba(255,215,0,.28); }
    .topic-btn:active { transform: scale(.96); }

    /* ── WHAT YOU'LL DISCOVER ── */
    .discover-wrap { background: radial-gradient(720px 320px at 50% 0%, rgba(255,215,0,.08), transparent 70%); }
    .discover { max-width: 760px; margin: 0 auto; display: grid; gap: 14px; }
    .discover-item {
      display: flex; align-items: center; gap: 18px;
      background: linear-gradient(180deg, var(--panel-2), var(--panel));
      border: 1px solid var(--border); border-left: 3px solid var(--gold-dk);
      border-radius: 14px; padding: 18px 22px;
      transition: transform .2s ease, border-color .2s ease, box-shadow .3s ease;
    }
    .discover-item:hover { transform: translateX(5px); border-color: rgba(255,215,0,.35); box-shadow: 0 14px 32px rgba(0,0,0,.45); }
    .discover-item .dnum { flex-shrink: 0; width: 34px; font-family: Georgia, serif; font-weight: 700; font-size: 22px; color: var(--gold); }
    .discover-item .dtext { font-size: clamp(15px, 2.2vw, 17.5px); font-weight: 600; color: var(--text); }

    /* ── AUTHORITY / TRUST ── */
    .trust { text-align: center; padding: 92px 22px; background: radial-gradient(620px 300px at 50% 50%, rgba(255,215,0,.10), transparent 70%); border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }
    .trust-icon { font-size: 46px; margin-bottom: 18px; filter: drop-shadow(0 0 20px rgba(255,215,0,.5)); }
    .trust .mark { font-size: 13px; letter-spacing: 3px; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; }
    .trust h2 { font-size: clamp(24px, 4vw, 40px); margin-bottom: 16px; max-width: 760px; margin-left: auto; margin-right: auto; line-height: 1.2; }
    .trust h2 .gold { color: var(--gold); }
    .trust p { color: var(--muted); max-width: 560px; margin: 0 auto; font-size: 16px; }

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

    /* ── FINAL CTA ── */
    .footer-cta { text-align: center; padding: 96px 22px; background: linear-gradient(180deg, transparent, rgba(139,0,0,.16)); }
    .footer-cta .mark { font-size: 13px; letter-spacing: 3px; text-transform: uppercase; color: var(--gold); margin-bottom: 16px; }
    .footer-cta h2 { font-size: clamp(28px, 5vw, 50px); margin-bottom: 30px; letter-spacing: -.5px; line-height: 1.12; }
    .footer-cta h2 .gold { color: var(--gold); }

    /* ── Footer ── */
    footer { text-align: center; padding: 56px 22px 48px; border-top: 1px solid var(--border); background: #050505; }
    .foot-logo {
      width: 64px; height: 64px; object-fit: contain; border-radius: 14px;
      background: #000; padding: 6px; margin: 0 auto 16px; display: block; filter: drop-shadow(0 0 14px rgba(255,215,0,.4));
    }
    .foot-name { color: var(--gold); font-family: Georgia, serif; font-size: 18px; font-weight: 700; margin-bottom: 18px; }
    .foot-social { text-align: center; margin: 4px auto 24px; }
    .foot-social-label { color: var(--gold); font-size: 12px; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 14px; }
    .foot-social .odili-social { justify-content: center; gap: 14px; }
    .foot-links { display: flex; gap: 20px; justify-content: center; margin-bottom: 22px; flex-wrap: wrap; }
    .foot-links a { color: var(--muted); text-decoration: none; font-size: 14px; font-weight: 600; transition: color .2s; }
    .foot-links a:hover { color: var(--gold); }
    .foot-copy { color: #5d574e; font-size: 13px; }

    @media (max-width: 560px) {
      .section { padding: 66px 0; }
      .hero { padding: 120px 18px 60px; }
      .capture-card { padding: 36px 24px; }
      .btn { width: 100%; }
      .cta-row { width: 100%; }
    }
  </style>
</head>
<body>
__ODILI_HEADER_HTML__
<div class="glow-field"></div>
<main>

  <!-- ── SECTION 1 · HERO ── -->
  <section class="hero">
    <video class="hero-logo" autoplay muted loop playsinline poster="__LOGO_URL__" aria-label="__APP_NAME__ logo">
      <source src="/static/animated-logo.mp4" type="video/mp4">
    </video>
    <div class="eyebrow reveal">Catholic Truth • History • Apologetics • + More</div>
    <h1 class="reveal" id="main-headline">You Weren't Taught Everything<br><span class="accent">About Salvation.</span></h1>
    <p class="sub reveal">And deep down, you've probably sensed it. There are verses that don't quite fit — teachings that don't fully explain what the early Church believed. This isn't about attacking what you believe. It's about finishing the picture.</p>
    <div class="urgency-pill reveal">🔥 New teachings every week — rooted in Scripture, Tradition &amp; the earliest Christians</div>
    <div class="cta-row reveal">
      <a class="btn btn-primary" href="#capture" data-cta="hero">Receive the Teachings →</a>
      <a class="btn btn-red" href="__YOUTUBE_URL__" target="_blank" rel="noopener" data-cta="hero">▶ Watch the 1-Minute Starting Point</a>
    </div>
    <div class="reveal" style="margin-top:16px;font-size:13px;color:#6d685f;">No spam. No noise. Just truth, clearly explained.</div>
  </section>

  <!-- ── SECTION 2 · EMAIL CAPTURE (primary CTA) ── -->
  <section class="section capture wrap" id="capture">
    <div class="capture-card reveal">
      <span class="badge">Begin Here</span>
      <h2>Don't try to piece this together <span class="gold">alone.</span></h2>
      <p class="lead">Receive short, focused teachings on what the earliest Christians actually believed, where modern interpretations diverged, and how Scripture, Tradition, and history align.</p>
      <div id="interest-chip" class="interest-chip"></div>
      <form class="capture-form" id="capture-form" onsubmit="joinMission(event)" novalidate>
        <input type="hidden" id="capture-interest" value="">
        <input type="text" id="capture-interest-text" class="capture-other" placeholder="Tell us what you're seeking (optional)…" maxlength="120" aria-label="What you're seeking">
        <input type="email" id="capture-email" placeholder="you@example.com" required autocomplete="email" aria-label="Email address">
        <button type="submit" class="btn btn-primary" id="capture-btn">Start Learning the Truth →</button>
      </form>
      <div class="capture-fine">No spam. Unsubscribe anytime with one click.</div>
      <div id="capture-msg" class="capture-msg"></div>
    </div>
  </section>

  <!-- ── SECTION 3 · START HERE VIDEO ── -->
  <section class="section video-section">
    <div class="wrap">
      <div class="section-head reveal">
        <div class="mark">Start Here</div>
        <h2>This Will Challenge <span class="gold">What You've Been Told</span></h2>
        <p>Just one minute. If it raises questions you've never fully answered, that's exactly where this journey begins.</p>
      </div>
      __VIDEO_BLOCK__
      <div class="cta-row reveal">
        <a class="btn btn-primary" href="#capture" data-cta="mid">Send Me the Next Teaching →</a>
        <a class="btn btn-red" href="__YOUTUBE_URL__" target="_blank" rel="noopener" data-cta="mid">▶ Watch on YouTube</a>
      </div>
    </div>
  </section>

  <!-- ── CONTENT HUB · latest shorts / playlists / community (admin-curated) ── -->
  <section class="section content-hub wrap" id="content-hub" style="display:none;">
    <div class="section-head reveal">
      <div class="mark">Go Deeper</div>
      <h2>Watch, Explore, <span class="gold">Go Deeper</span></h2>
      <p>Latest teachings, short breakdowns, and topic playlists. If something resonates, don't stop there — follow it through.</p>
    </div>
    <div id="hub-shorts" class="hub-shorts reveal"></div>
    <div id="hub-playlists" class="hub-playlists reveal"></div>
    <div id="hub-community" class="hub-community reveal"></div>
  </section>

  <!-- ── SECTION 4 · TOPIC SELECTION BUTTONS (prefill interest → scroll to capture) ── -->
  <section class="section wrap">
    <div class="topic-entry reveal">
      <div class="mark">What are you most curious about?</div>
      <div class="topic-btns">
        <button type="button" class="topic-btn" onclick="pickInterest('Salvation')">Salvation</button>
        <button type="button" class="topic-btn" onclick="pickInterest('Eucharist')">Eucharist</button>
        <button type="button" class="topic-btn" onclick="pickInterest('Papacy')">Papacy</button>
        <button type="button" class="topic-btn" onclick="pickInterest('Mary &amp; Saints')">Mary &amp; Saints</button>
        <button type="button" class="topic-btn" onclick="pickInterest('False Doctrines')">False Doctrines</button>
        <button type="button" class="topic-btn" onclick="pickInterestOther()">Other</button>
      </div>
    </div>
  </section>

  <!-- ── SECTION 5 · WHAT YOU'LL DISCOVER ── -->
  <section class="section discover-wrap">
    <div class="wrap">
      <div class="section-head reveal">
        <h2>What You'll <span class="gold">Discover</span></h2>
        <p>This isn't surface-level content. Clear. Direct. No confusion.</p>
      </div>
      <div class="discover reveal">
        <div class="discover-item"><span class="dnum">01</span><span class="dtext">Why "faith alone" doesn't fully explain salvation</span></div>
        <div class="discover-item"><span class="dnum">02</span><span class="dtext">How the Eucharist was understood from the beginning</span></div>
        <div class="discover-item"><span class="dnum">03</span><span class="dtext">What the early Church believed about authority</span></div>
        <div class="discover-item"><span class="dnum">04</span><span class="dtext">Where common teachings today break from history</span></div>
        <div class="discover-item"><span class="dnum">05</span><span class="dtext">How to defend your faith without strawman arguments</span></div>
      </div>
    </div>
  </section>

  <!-- ── SECTION 6 · AUTHORITY ── -->
  <section class="trust reveal">
    <div class="trust-icon">✝️</div>
    <div class="mark">Grounded In</div>
    <h2>Scripture • The Church Fathers • <span class="gold">Ecumenical Councils • The Catechism</span></h2>
    <p>Not opinion. Not trends. What has actually been handed down.</p>
  </section>

  <!-- ── TOPIC ENGAGEMENT (vote + request) ── -->
  <section class="section topics">
    <div class="wrap">
      <div class="section-head reveal">
        <h2>Have a Question You've Never Had a <span class="gold">Clear Answer To?</span></h2>
        <p>Submit it, or see what others are asking. The next teaching might come from you.</p>
      </div>
      <div class="topic-list reveal" id="topic-list">
        <div class="topics-empty">Loading topics…</div>
      </div>

      <div class="request-card reveal">
        <h3>The next teaching <span class="gold">might come from you.</span></h3>
        <p class="lead">Send in a question, a doubt, or a truth you want Odili to explore.</p>
        <form class="request-form" id="request-form" onsubmit="submitTopic(event)" novalidate>
          <input type="text" id="request-title" placeholder="The topic you'd like covered…" maxlength="200" required aria-label="Topic title">
          <textarea id="request-desc" placeholder="Add any detail (optional)…" rows="3" maxlength="500" aria-label="Topic detail"></textarea>
          <button type="submit" class="btn btn-primary" id="request-btn">Submit Topic</button>
        </form>
        <div id="request-msg" class="request-msg"></div>
      </div>
    </div>
  </section>

  <!-- ── SECTION 7 · FINAL CTA ── -->
  <section class="footer-cta reveal">
    <div class="mark">🔥 New Teachings Released Weekly</div>
    <h2>You don't need more opinions.<br><span class="gold">You need clarity.</span></h2>
    <p class="sub" style="max-width:600px;margin:0 auto 30px;color:var(--muted);">And once you see it, you won't unsee it.</p>
    <div class="cta-row">
      <a class="btn btn-primary" href="#capture" data-cta="final">Receive the Next One →</a>
      <a class="btn btn-red" href="__YOUTUBE_URL__" target="_blank" rel="noopener" data-cta="final">▶ Watch on YouTube</a>
    </div>
    <div style="margin-top:20px;font-size:13px;color:#6d685f;">This is for those who want the full truth — not just part of it.</div>
  </section>

  <!-- ── SECTION 8 · FOOTER ── -->
  <footer>
    <img class="foot-logo" src="__LOGO_URL__" alt="__APP_NAME__ logo">
    <div class="foot-name">Odili — The Seeker of Truth</div>
    <div class="foot-social">
      <div class="foot-social-label">Follow the Mission Everywhere</div>
      __FOOTER_SOCIAL__
    </div>
    <div class="foot-links">
      <a href="#capture">✉ Weekly Teachings</a>
      <a href="__YOUTUBE_URL__" target="_blank" rel="noopener">▶ YouTube Channel</a>
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

  // ── Behavior tracking → POST /track (fire-and-forget, never blocks UI) ──
  function trackEvent(eventName, data) {
    try {
      fetch('/track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event: eventName, data: data || {} })
      }).catch(function () {});
    } catch (e) {}
  }

  // ── Headline A/B testing: auto-best headline, else per-visitor variant ──
  var HEADLINES = __HEADLINES__;
  var currentHeadline = '';

  function applyHeadline(text, persist) {
    var el = document.getElementById('main-headline');
    currentHeadline = text;
    if (el) el.textContent = text;
    if (persist) { try { localStorage.setItem('headline_variant', text); } catch (e) {} }
    trackEvent('headline_variant', { headline: text });
  }

  function runHeadlineTest() {
    var v = null;
    try { v = localStorage.getItem('headline_variant'); } catch (e) {}
    if (!v || HEADLINES.indexOf(v) === -1) {
      v = HEADLINES[Math.floor(Math.random() * HEADLINES.length)];
      applyHeadline(v, true);
    } else {
      applyHeadline(v, false);  // returning visitor → same headline (consistency)
    }
  }

  async function loadHeadline() {
    if (!HEADLINES || !HEADLINES.length) return;
    try {
      const res = await fetch('/analytics/best-headline');
      const data = await res.json();
      if (data && data.best_headline) { applyHeadline(data.best_headline, false); return; }
    } catch (e) {}
    runHeadlineTest();  // not enough data yet → fall back to A/B testing
  }

  // ── Topic entry buttons → prefill interest + scroll to capture ──
  function pickInterest(topic) {
    trackEvent('topic_click', { topic: topic });
    const hidden = document.getElementById('capture-interest');
    const chip   = document.getElementById('interest-chip');
    if (hidden) hidden.value = topic;
    if (chip) {
      chip.innerHTML = '✓ Exploring: <strong>' + escHtml(topic) + '</strong>';
      chip.classList.add('show');
    }
    const other = document.getElementById('capture-interest-text');
    if (other) other.classList.remove('show');
    const cap = document.getElementById('capture');
    if (cap) cap.scrollIntoView({ behavior: 'smooth' });
    const inp = document.getElementById('capture-email');
    if (inp) setTimeout(function () { inp.focus(); }, 480);
  }

  // ── "Other" → reveal a free-text interest field + general signup ──
  function pickInterestOther() {
    trackEvent('topic_click', { topic: 'Other' });
    const hidden = document.getElementById('capture-interest');
    const chip   = document.getElementById('interest-chip');
    const other  = document.getElementById('capture-interest-text');
    if (hidden) hidden.value = 'Other';
    if (chip) {
      chip.innerHTML = '✓ Exploring: <strong>Something else</strong>';
      chip.classList.add('show');
    }
    if (other) other.classList.add('show');
    const cap = document.getElementById('capture');
    if (cap) cap.scrollIntoView({ behavior: 'smooth' });
    if (other) setTimeout(function () { other.focus(); }, 480);
  }

  // ── Email capture (feeds the mailing list + starts the drip sequence) ──
  async function joinMission(e) {
    e.preventDefault();
    const email = document.getElementById('capture-email').value.trim();
    const interestEl = document.getElementById('capture-interest');
    const otherEl = document.getElementById('capture-interest-text');
    let interest = (interestEl && interestEl.value.trim()) ? interestEl.value.trim() : null;
    // A typed "Other" value (when shown) takes precedence over the hidden tag.
    if (otherEl && otherEl.classList.contains('show') && otherEl.value.trim()) {
      interest = otherEl.value.trim();
    }
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
        trackEvent('signup', { headline: currentHeadline, interest: interest });
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
        const badge = t.trending ? '<span class="topic-badge">🔥 Trending</span>' : '';
        return '<div class="topic-card">' +
            '<div class="topic-main"><div class="topic-title">' + escHtml(t.title) + badge + '</div>' + desc + '</div>' +
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

  // ── Content hub (admin-curated shorts / playlists / community link) ──
  function isHttp(u) { return /^https?:\/\//i.test(String(u || '')); }

  async function loadFeaturedContent() {
    const sec = document.getElementById('content-hub');
    if (!sec) return;
    try {
      const res = await fetch('/featured-content');
      const data = await res.json();
      const shorts = (data && data.shorts) || [];
      const playlists = (data && data.playlists) || [];
      const community = (data && data.community_url) || '';
      let any = false;

      const sb = document.getElementById('hub-shorts');
      const validShorts = shorts.filter(function (s) { return s && s.id; });
      if (validShorts.length) {
        any = true;
        sb.innerHTML = validShorts.map(function (s) {
          const id = encodeURIComponent(s.id);
          const title = escHtml(s.title || 'Watch on YouTube');
          return '<a class="hub-short" href="https://www.youtube.com/watch?v=' + id + '" target="_blank" rel="noopener">' +
              '<div class="thumb" style="background-image:url(https://i.ytimg.com/vi/' + id + '/hqdefault.jpg)"></div>' +
              '<div class="stitle">' + title + '</div>' +
            '</a>';
        }).join('');
      } else { sb.innerHTML = ''; }

      const pb = document.getElementById('hub-playlists');
      const validPlaylists = playlists.filter(function (p) { return p && isHttp(p.url); });
      if (validPlaylists.length) {
        any = true;
        pb.innerHTML = validPlaylists.map(function (p) {
          return '<a class="hub-playlist" href="' + escHtml(p.url) + '" target="_blank" rel="noopener">' +
              '<span class="ptitle">' + escHtml(p.title || 'View Playlist') + '</span>' +
              '<span class="parrow">▶ Watch</span>' +
            '</a>';
        }).join('');
      } else { pb.innerHTML = ''; }

      const cb = document.getElementById('hub-community');
      if (isHttp(community)) {
        any = true;
        cb.innerHTML = '<a class="btn btn-ghost" href="' + escHtml(community) + '" target="_blank" rel="noopener">Join the Community →</a>';
      } else { cb.innerHTML = ''; }

      if (any) {
        sec.style.display = '';
        sec.querySelectorAll('.reveal').forEach(function (el) { el.classList.add('in'); });
      }
    } catch (err) { /* hub stays hidden on error */ }
  }

  // ── Smart intro video rotation: returning visitors see the OTHER video ──
  (function () {
    var ids = __INTRO_VIDEO_IDS__;
    var iframe = document.getElementById('intro-video');
    if (!iframe || !ids || !ids.length) return;
    var id;
    if (ids.length > 1) {
      var last = null;
      try { last = localStorage.getItem('lastVideo'); } catch (e) {}
      if (last && ids.indexOf(last) !== -1) {
        id = ids.find(function (v) { return v !== last; }) || ids[0];  // show the other
      } else {
        id = ids[Math.floor(Math.random() * ids.length)];             // first visit → random
      }
    } else {
      id = ids[0];
    }
    try { localStorage.setItem('lastVideo', id); } catch (e) {}
    iframe.addEventListener('load', function () { trackEvent('video_loaded', { video: id }); });
    iframe.src = 'https://www.youtube.com/embed/' + encodeURIComponent(id) + '?rel=0&autoplay=1&mute=1&playsinline=1';
    var frame = document.getElementById('intro-frame');
    if (frame) frame.style.backgroundImage = 'url(https://i.ytimg.com/vi/' + encodeURIComponent(id) + '/hqdefault.jpg)';
    var fb = document.getElementById('intro-fallback');
    if (fb) fb.href = 'https://www.youtube.com/watch?v=' + encodeURIComponent(id);
  })();

  // ── Funnel init: page view, headline, scroll depth, CTA click tracking ──
  trackEvent('page_view');
  loadHeadline();

  var scrollTracked = {};
  window.addEventListener('scroll', function () {
    var h = document.body.scrollHeight - window.innerHeight;
    if (h <= 0) return;
    var pct = Math.round((window.scrollY / h) * 100);
    [25, 50, 75, 100].forEach(function (lvl) {
      if (pct >= lvl && !scrollTracked[lvl]) {
        scrollTracked[lvl] = true;
        trackEvent('scroll_depth', { percent: lvl });
      }
    });
  }, { passive: true });

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-cta]');
    if (btn) trackEvent('cta_click', { location: btn.getAttribute('data-cta') });
  });

  loadTopics();
  loadFeaturedContent();
</script>

</body>
</html>"""

if FEATURED_VIDEO_ID:
    # Real embed with autoplay+mute. The YouTube thumbnail is painted behind the
    # iframe so a slow/blocked embed degrades to a clickable poster fallback.
    _VIDEO_BLOCK = (
        '<div id="intro-frame" class="video-frame video-frame--embed reveal" '
        'style="background-size:cover;background-position:center;">'
        '<a id="intro-fallback" class="video-fallback" '
        'href="__YOUTUBE_URL__" target="_blank" rel="noopener" '
        'aria-label="Watch on YouTube"><span class="video-play">▶</span></a>'
        '<iframe id="intro-video" '
        'title="Start Here: The Truth About Salvation" loading="lazy" '
        'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
        "allowfullscreen></iframe>"
        "</div>"
    )
else:
    _VIDEO_BLOCK = (
        '<a class="video-frame reveal" href="__YOUTUBE_URL__" target="_blank" rel="noopener" aria-label="Watch on YouTube">'
        '<span class="video-poster"><img src="__LOGO_URL__" alt=""></span>'
        '<span class="video-play">▶</span>'
        '<span class="vlabel">▶ Watch on YouTube</span>'
        "</a>"
    )

_LANDING_HTML = _LANDING_HTML.replace("__VIDEO_BLOCK__", _VIDEO_BLOCK)
_LANDING_HTML = _LANDING_HTML.replace("__ODILI_HEADER_CSS__", HEADER_CSS)
_LANDING_HTML = _LANDING_HTML.replace("__FOOTER_SOCIAL__", social_icons_html())
_LANDING_HTML = _LANDING_HTML.replace("__ODILI_HEADER_HTML__", header_html())
_LANDING_HTML = _LANDING_HTML.replace("__LOGO_URL__", LOGO_URL)
_LANDING_HTML = _LANDING_HTML.replace("__APP_NAME__", APP_NAME)
_LANDING_HTML = _LANDING_HTML.replace("__YOUTUBE_URL__", YOUTUBE_URL)
# Headline A/B test variants live in app.services.headlines (shared with the
# analytics validator). The static h1 above is the no-JS fallback; JS swaps in
# one of these (or the auto-selected best headline).
_LANDING_HTML = _LANDING_HTML.replace("__INTRO_VIDEO_IDS__", json.dumps(INTRO_VIDEO_IDS))
_LANDING_HTML = _LANDING_HTML.replace("__HEADLINES__", json.dumps(HEADLINES))


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page() -> HTMLResponse:
    """Public evangelization funnel for Odili — The Seeker of Truth. No internal tools."""
    return HTMLResponse(content=_LANDING_HTML)
