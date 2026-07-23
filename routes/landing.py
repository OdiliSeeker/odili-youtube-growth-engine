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
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;0,800;1,400;1,600&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  __ODILI_HEADER_CSS__
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:      #150d08;   /* deep espresso base */
      --tile:    #1f130b;
      --tile-2:  #2a1a0f;
      --tile-3:  #352214;
      --gold:    #c9a34e;
      --gold-lt: #e6c875;
      --text:    #fdfbf7;
      --muted:   #a89382;
      --line:    rgba(201,163,78,.10);
      --line-2:  rgba(201,163,78,.30);
    }

    html { scroll-behavior: smooth; }

    body {
      font-family: 'Inter', -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      overflow-x: hidden;
      line-height: 1.6;
    }
    ::selection { background: var(--gold); color: var(--bg); }

    h1, h2, h3, .serif { font-family: 'Playfair Display', Georgia, serif; }

    .wrap { max-width: 1400px; margin: 0 auto; padding: 0 20px; }
    @media (min-width: 1024px) { .wrap { padding: 0 32px; } }

    /* ── COMPACT HERO BAND (sticky) ── */
    .hero {
      position: sticky; top: 0; z-index: 50;
      background: rgba(21,13,8,.95);
      -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px);
      border-bottom: 1px solid rgba(201,163,78,.2);
      padding: 18px 0 20px;
    }
    .hero-inner {
      display: flex; flex-direction: column; gap: 18px;
      align-items: stretch; justify-content: space-between;
    }
    @media (min-width: 1024px) {
      .hero-inner { flex-direction: row; align-items: center; gap: 28px; }
    }
    .hero-copy { min-width: 0; }
    .eyebrow {
      font-size: 12px; letter-spacing: 3px; text-transform: uppercase;
      color: var(--gold); font-weight: 600; margin-bottom: 4px;
    }
    .hero h1 {
      font-size: clamp(21px, 2.6vw, 30px); line-height: 1.18; font-weight: 700;
      color: #fff; margin-bottom: 4px;
    }
    .hero p.sub {
      font-size: 13.5px; color: var(--muted); max-width: 620px; margin: 0;
    }
    .hero-gift {
      font-size: 12.5px; color: var(--gold-lt); margin-top: 6px;
    }
    .hero-watch { color: var(--gold); font-size: 12.5px; text-decoration: none; margin-left: 10px; }
    .hero-watch:hover { color: var(--gold-lt); }

    /* Hero inline capture form */
    .capture-form {
      display: flex; flex-direction: column; gap: 10px; flex-shrink: 0; width: 100%;
    }
    @media (min-width: 640px)  { .capture-form { flex-direction: row; flex-wrap: wrap; } }
    @media (min-width: 1024px) { .capture-form { width: auto; flex-wrap: nowrap; } }
    .capture-form input[type="text"], .capture-form input[type="email"] {
      background: var(--tile-2); border: 1px solid rgba(201,163,78,.3); color: #fff;
      padding: 11px 14px; border-radius: 6px; font-size: 14px; font-family: inherit;
      outline: none; transition: border-color .2s; width: 100%;
    }
    @media (min-width: 640px) {
      .capture-form input[type="text"]  { width: 12rem; flex: 1 1 auto; }
      .capture-form input[type="email"] { width: 14rem; flex: 1 1 auto; }
    }
    .capture-form input::placeholder { color: var(--muted); }
    .capture-form input:focus { border-color: var(--gold); }
    .btn-gold {
      background: var(--gold); color: var(--bg); font-weight: 700; font-family: inherit;
      border: 0; padding: 11px 22px; border-radius: 6px; font-size: 14px; cursor: pointer;
      white-space: nowrap; transition: background .2s; text-decoration: none;
      display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    }
    .btn-gold:hover { background: var(--gold-lt); }
    .btn-gold:disabled { opacity: .6; cursor: not-allowed; }

    .interest-chip { display: none; font-size: 12.5px; color: var(--gold); margin-top: 6px; }
    .interest-chip.show { display: block; }
    .capture-msg { display: none; margin-top: 8px; font-size: 13px; border-radius: 8px; padding: 9px 12px; }
    .capture-msg.ok  { display: block; background: rgba(46,125,50,.14); color: #8fe29a; border: 1px solid rgba(46,125,50,.4); }
    .capture-msg.err { display: block; background: rgba(192,57,43,.14); color: #f0a59e; border: 1px solid rgba(192,57,43,.4); }

    /* ── Seeker watermark (subtle fixed brand image behind everything) ── */
    body::before {
      content: ""; position: fixed; top: 0; right: 0;
      width: min(480px, 45vw); height: 100%;
      background-image: url('/static/seeker-watermark.jpg');
      background-repeat: no-repeat; background-position: top right; background-size: contain;
      opacity: .08; pointer-events: none; z-index: 0;
    }

    /* ── BENTO GRID ── */
    main { position: relative; z-index: 1; }
    .bento { padding: 32px 0 48px; }
    .bento-grid {
      display: grid; gap: 16px; grid-template-columns: 1fr; grid-auto-flow: dense;
    }
    @media (min-width: 768px)  { .bento-grid { grid-template-columns: repeat(2, 1fr); gap: 20px; } }
    @media (min-width: 1024px) { .bento-grid { grid-template-columns: repeat(4, 1fr); gap: 24px; } }

    .tile {
      background: var(--tile); border: 1px solid var(--line); border-radius: 12px;
      overflow: hidden; transition: border-color .3s ease, background .3s ease;
    }
    .tile:hover { border-color: var(--line-2); }
    @media (min-width: 1024px) {
      .span-2 { grid-column: span 2; }
      .row-2  { grid-row: span 2; }
    }

    /* Featured tile */
    .feat {
      position: relative; min-height: 400px;
      display: flex; flex-direction: column; justify-content: flex-end;
      padding: 28px; cursor: default;
    }
    @media (min-width: 1024px) { .feat { min-height: 500px; padding: 32px; } }
    .feat-bg {
      position: absolute; inset: 0;
      background: linear-gradient(135deg, var(--tile-2), var(--bg));
    }
    .feat-dots {
      position: absolute; inset: 0; opacity: .2;
      background-image: radial-gradient(circle at 50% 50%, var(--gold) 1px, transparent 1px);
      background-size: 30px 30px;
    }
    .feat-glass { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(31,19,11,0) 0%, rgba(21,13,8,.9) 100%); }
    .feat-body { position: relative; z-index: 2; }
    .feat-logo {
      width: 84px; height: auto; border-radius: 14px; background: #000;
      margin-bottom: 20px; display: block;
      filter: drop-shadow(0 0 26px rgba(201,163,78,.45));
    }
    .feat-badge {
      display: inline-block; padding: 5px 12px; border-radius: 999px; margin-bottom: 14px;
      background: rgba(21,13,8,.8); color: var(--gold); border: 1px solid rgba(201,163,78,.3);
      font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase;
    }
    .feat h3 {
      font-size: clamp(24px, 3vw, 34px); font-weight: 700; color: #fff;
      line-height: 1.2; margin-bottom: 10px;
    }
    .feat p { color: var(--muted); max-width: 430px; margin-bottom: 20px; font-size: 15px; }
    /* Post-signup: the Start Here embed lives inside the featured tile */
    .video-frame {
      position: relative; display: flex; align-items: center; justify-content: center;
      width: 100%; aspect-ratio: 16 / 9; border-radius: 10px; overflow: hidden;
      border: 1px solid rgba(201,163,78,.25); background: #0d0805;
      text-decoration: none; cursor: pointer;
    }
    .video-frame--embed { cursor: default; }
    .video-frame iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; z-index: 3; }
    .video-fallback { position: absolute; inset: 0; z-index: 1; display: flex; align-items: center; justify-content: center; text-decoration: none; }
    .video-poster { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; opacity: .14; }
    .video-poster img { width: 50%; max-width: 300px; }
    .video-play {
      position: relative; z-index: 2; width: 64px; height: 64px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center; padding-left: 5px;
      background: rgba(201,163,78,.2); border: 1px solid var(--gold); color: var(--gold);
      font-size: 24px;
    }
    .video-frame .vlabel {
      position: absolute; bottom: 12px; left: 0; right: 0; z-index: 2; text-align: center;
      color: var(--text); font-weight: 700; font-size: 13px;
    }

    /* Topic chips tile */
    .topics { padding: 24px; background: var(--tile-2); }
    @media (min-width: 1024px) { .topics { padding: 28px; } }
    .topics h4 {
      font-family: 'Playfair Display', serif; font-size: 20px; color: #fff;
      border-bottom: 1px solid rgba(201,163,78,.2); padding-bottom: 14px; margin-bottom: 18px;
    }
    .topic-btns { display: flex; flex-wrap: wrap; gap: 10px; }
    .topic-btn {
      font-family: inherit; font-size: 13.5px; cursor: pointer; color: var(--text);
      padding: 8px 16px; border-radius: 999px; background: transparent;
      border: 1px solid rgba(201,163,78,.4); transition: background .2s, color .2s;
      text-align: left;
    }
    .topic-btn:hover { background: rgba(201,163,78,.1); color: var(--gold-lt); }

    /* Authority quote tile */
    .quote {
      padding: 24px; border-left: 4px solid var(--gold);
      display: flex; flex-direction: column; justify-content: center;
    }
    @media (min-width: 1024px) { .quote { padding: 28px; } }
    .quote svg { width: 30px; height: 30px; color: rgba(201,163,78,.3); margin-bottom: 14px; }
    .quote blockquote {
      font-family: 'Playfair Display', serif; font-style: italic; font-size: 18px;
      color: var(--text); line-height: 1.55; margin-bottom: 14px;
    }
    .quote .attr { color: var(--gold); font-weight: 700; font-size: 12px; letter-spacing: 2px; text-transform: uppercase; }
    .quote .attr-sub { color: var(--muted); font-size: 12px; margin-top: 4px; }

    /* Discover hook tiles (always-on YouTube surface — the allowed pre-email one) */
    a.hook {
      display: flex; flex-direction: column; justify-content: space-between;
      padding: 22px; text-decoration: none; background: var(--tile-2); cursor: pointer;
    }
    a.hook:hover { background: var(--tile-3); }
    .hook h4 { font-family: 'Playfair Display', serif; font-size: 19px; color: #fff; margin: 12px 0 6px; line-height: 1.3; }
    .hook p { font-size: 13.5px; color: var(--muted); font-style: italic; }
    .hook .go { color: var(--gold); font-size: 13px; font-weight: 700; margin-top: 16px; }
    .hook .ic { color: var(--gold); opacity: .7; font-size: 18px; }
    a.hook:hover .ic { opacity: 1; }
    .video-thumbnail {
      display: block; width: 100%; height: auto; aspect-ratio: 16 / 9; object-fit: cover;
      border-radius: 8px; border: 1px solid var(--line); margin: 12px 0 4px; background: #000;
    }
    a.hook:hover .video-thumbnail { border-color: rgba(201,163,78,.4); }
    .hook-sm .video-thumbnail { margin: 0 0 10px; }

    /* Post-capture pitch strip under the intro video */
    .feat-pitch { margin-top: 18px; padding-top: 16px; border-top: 1px solid rgba(201,163,78,.2); }
    .feat-pitch p { margin-bottom: 14px; }

    a.hook-sm {
      display: flex; flex-direction: column; justify-content: space-between;
      background: var(--tile); border: 1px solid var(--line); padding: 18px;
      border-radius: 12px; text-decoration: none; min-height: 140px; cursor: pointer;
      transition: border-color .3s, background .3s;
    }
    a.hook-sm:hover { border-color: var(--line-2); background: var(--tile-2); }
    .hook-sm h4 { font-family: 'Playfair Display', serif; font-size: 16px; color: #fff; line-height: 1.3; margin-bottom: 8px; }
    .hook-sm .hint { font-size: 12px; color: var(--muted); font-style: italic; margin-bottom: 10px; }
    .hook-sm .go { color: var(--muted); font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; }
    a.hook-sm:hover .go { color: var(--gold); }
    .hook-grid {
      background: transparent; border: none; padding: 0;
      display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
    }
    @media (min-width: 1024px) { .hook-grid { gap: 20px; } }

    /* Gold capture tile */
    .gold-tile {
      background: linear-gradient(135deg, var(--gold), #997a3a); color: var(--bg);
      padding: 28px; display: flex; flex-direction: column; justify-content: center;
    }
    .gold-tile h3 { font-size: clamp(20px, 2.4vw, 27px); font-weight: 700; margin-bottom: 6px; }
    .gold-tile p { font-size: 14px; font-weight: 500; color: rgba(21,13,8,.8); margin-bottom: 18px; max-width: 520px; }
    .gold-tile .capture-form input[type="email"] {
      background: rgba(21,13,8,.1); border: 1px solid rgba(21,13,8,.25); color: var(--bg);
    }
    .gold-tile .capture-form input::placeholder { color: rgba(21,13,8,.6); }
    .gold-tile .capture-form input:focus { border-color: var(--bg); background: #fdfbf7; }
    .gold-tile .btn-gold { background: var(--bg); color: var(--gold); }
    .gold-tile .btn-gold:hover { background: var(--tile-2); }
    .gold-tile .capture-msg.ok  { background: rgba(21,13,8,.18); color: #10380f; border-color: rgba(21,13,8,.3); }
    .gold-tile .capture-msg.err { background: rgba(120,20,10,.18); color: #5e120a; border-color: rgba(120,20,10,.35); }

    /* Category video tiles (explore grid — open, no email gate) */
    .explore-cat { padding: 24px; display: flex; flex-direction: column; }
    @media (min-width: 1024px) { .explore-cat { padding: 28px; } }
    .explore-cat .cat-head {
      display: flex; align-items: center; justify-content: space-between; gap: 10px;
      border-bottom: 1px solid var(--line); padding-bottom: 14px; margin-bottom: 18px;
    }
    .explore-cat h3 {
      font-family: 'Playfair Display', serif; font-size: 19px; color: #fff;
      display: flex; align-items: center; gap: 10px;
    }
    .explore-cat h3 .ic { color: var(--gold); font-size: 15px; }
    .explore-vids { display: grid; grid-template-columns: 1fr; gap: 14px; flex-grow: 1; }
    @media (min-width: 640px) { .explore-vids { grid-template-columns: 1fr 1fr; } }
    a.mini-vid { display: flex; flex-direction: column; gap: 8px; text-decoration: none; }
    .mini-vid .mv-thumb {
      aspect-ratio: 16 / 9; border-radius: 8px; border: 1px solid var(--line);
      background: var(--tile-2) center/cover no-repeat; position: relative;
      display: flex; align-items: center; justify-content: center; overflow: hidden;
      transition: border-color .25s;
    }
    a.mini-vid:hover .mv-thumb { border-color: rgba(201,163,78,.4); }
    .mini-vid .mv-thumb::before {
      content: ''; position: absolute; inset: 0;
      background: linear-gradient(0deg, rgba(21,13,8,.6), transparent 55%);
    }
    .mini-vid .mv-play {
      width: 38px; height: 38px; border-radius: 50%; padding-left: 3px;
      background: rgba(21,13,8,.8); border: 1px solid rgba(201,163,78,.3);
      display: flex; align-items: center; justify-content: center;
      color: var(--gold); font-size: 13px; position: relative; z-index: 2;
      transition: transform .25s;
    }
    a.mini-vid:hover .mv-play { transform: scale(1.1); }
    .mini-vid .mv-title { font-size: 13.5px; font-weight: 500; color: var(--text); line-height: 1.4; }
    a.mini-vid:hover .mv-title { color: var(--gold); }

    /* Content hub (post-signup) + teachings reuse tile look */
    .hub-shorts { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 14px; margin-bottom: 20px; }
    .hub-short { display: block; text-decoration: none; border-radius: 10px; overflow: hidden; border: 1px solid var(--line); background: var(--tile-2); transition: border-color .2s; }
    .hub-short:hover { border-color: var(--line-2); }
    .hub-short .thumb { aspect-ratio: 16 / 9; background: #000 center/cover no-repeat; }
    .hub-short .stitle { padding: 10px 12px; font-size: 13px; font-weight: 600; color: var(--text); line-height: 1.35; }
    .hub-playlists { display: grid; gap: 10px; margin-bottom: 18px; }
    .hub-playlist { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 14px 16px; border-radius: 10px; border: 1px solid var(--line); border-left: 3px solid var(--gold); background: var(--tile-2); text-decoration: none; color: var(--text); transition: border-color .2s; }
    .hub-playlist:hover { border-color: var(--line-2); }
    .hub-playlist .ptitle { font-weight: 600; font-size: 14px; }
    .hub-playlist .parrow { color: var(--gold); font-weight: 700; white-space: nowrap; font-size: 13px; }
    .hub-community { text-align: center; }
    .btn-outline {
      display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px;
      border: 1px solid rgba(201,163,78,.3); border-radius: 999px; color: var(--text);
      text-decoration: none; font-size: 14px; font-weight: 500; transition: color .2s, border-color .2s;
    }
    .btn-outline:hover { color: var(--gold); border-color: var(--gold); }

    .teachings-grid { display: grid; grid-template-columns: 1fr; gap: 14px; }
    @media (min-width: 768px)  { .teachings-grid { grid-template-columns: 1fr 1fr; } }
    @media (min-width: 1024px) { .teachings-grid { grid-template-columns: repeat(3, 1fr); gap: 20px; } }
    a.teach-card {
      display: block; text-decoration: none; color: var(--text); background: var(--tile);
      border: 1px solid var(--line); border-radius: 12px; padding: 20px 22px;
      transition: border-color .25s, background .25s;
    }
    a.teach-card:hover { border-color: var(--line-2); background: var(--tile-2); }
    .teach-card .tc-title { font-family: 'Playfair Display', serif; font-size: 17px; margin-bottom: 6px; color: #fff; }
    .teach-card .tc-desc { font-size: 13px; color: var(--muted); line-height: 1.55; }
    .teach-card .tc-more { display: inline-block; margin-top: 12px; color: var(--gold); font-size: 12.5px; font-weight: 600; }

    .strip { padding: 12px 0 40px; }
    .strip-head {
      display: flex; align-items: baseline; justify-content: space-between; gap: 12px;
      margin-bottom: 18px;
    }
    .strip-head h2 { font-size: clamp(20px, 2.4vw, 26px); color: #fff; }
    .strip-head .mark { font-size: 11px; letter-spacing: 2px; text-transform: uppercase; color: var(--muted); }

    /* Funnel gate: pre-email, hide shared header/footer YouTube links.
       (The discover hook tiles are the only allowed YouTube surface.) */
    body.yt-gated .odili-nav a[href*="youtube.com"],
    body.yt-gated .odili-social a[href*="youtube.com"],
    body.yt-gated .foot-social a[href*="youtube.com"] { display: none !important; }

    /* ── FINAL CTA BAND ── */
    .final-cta {
      border-top: 1px solid rgba(201,163,78,.2); background: var(--tile);
      padding: 64px 20px; text-align: center;
    }
    @media (min-width: 1024px) { .final-cta { padding: 96px 20px; } }
    .final-cta h2 {
      font-size: clamp(28px, 4.4vw, 48px); font-weight: 700; color: #fff;
      line-height: 1.15; margin-bottom: 16px; max-width: 820px; margin-left: auto; margin-right: auto;
    }
    .final-cta > p { color: var(--muted); font-size: 17px; max-width: 640px; margin: 0 auto 34px; }
    .final-cta .capture-form { max-width: 580px; margin: 0 auto; }
    .final-cta .capture-form input[type="email"] {
      background: var(--bg); border-color: rgba(201,163,78,.4); padding: 15px 20px; font-size: 16px;
      flex: 1 1 auto; width: auto;
    }
    .final-cta .btn-gold { padding: 15px 28px; font-size: 16px; }
    .final-cta .fine { margin-top: 16px; font-size: 12.5px; color: var(--muted); }
    .final-cta .capture-msg { max-width: 580px; margin-left: auto; margin-right: auto; }

    /* ── FOOTER ── */
    footer.site-foot { background: #110a06; border-top: 1px solid var(--tile-2); padding: 44px 0; }
    .foot-inner {
      display: flex; flex-direction: column; gap: 22px; align-items: center; text-align: center;
    }
    @media (min-width: 820px) {
      .foot-inner { flex-direction: row; justify-content: space-between; text-align: left; }
    }
    .foot-brand .foot-name { color: var(--gold); font-family: 'Playfair Display', serif; font-weight: 700; font-size: 20px; }
    .foot-brand .foot-copy { color: var(--muted); font-size: 13px; margin-top: 4px; }
    .foot-logo { width: 46px; height: 46px; object-fit: contain; border-radius: 10px; background: #000; padding: 4px; margin-bottom: 10px; display: block; }
    @media (max-width: 819px) { .foot-logo { margin-left: auto; margin-right: auto; } }
    .foot-links { display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; }
    .foot-links a { color: var(--muted); text-decoration: none; font-size: 13.5px; transition: color .2s; }
    .foot-links a:hover { color: var(--gold); }
    .foot-social { text-align: center; }
    .foot-social-label { color: var(--gold); font-size: 11px; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px; }
    .foot-social .odili-social { justify-content: center; gap: 14px; }
  </style>
</head>
<body class="yt-gated">
__ODILI_HEADER_HTML__
<main>

  <!-- ── COMPACT HERO BAND · headline + primary email capture ── -->
  <section class="hero" id="capture">
    <div class="wrap hero-inner">
      <div class="hero-copy">
        <div class="eyebrow">Odili · The Seeker of Truth — Catholic Truth · History · Apologetics</div>
        <h1 id="main-headline">Something Doesn’t Add Up… And You Know It.</h1>
        <p class="sub">The earliest Christians didn’t believe what most people think today. Discover what was actually handed down — not what was invented later.</p>
        <div class="hero-gift">🎁 First teaching instantly: <strong>What Christians were really called before &ldquo;Christian&rdquo;</strong><a class="hero-watch" href="#start-here" data-cta="hero_watch" id="hero-watch-cta">Watch the Starting Point →</a></div>
        <div id="interest-chip" class="interest-chip"></div>
      </div>
      <div>
        <form class="capture-form" id="capture-form" onsubmit="joinMission(event)" novalidate>
          <input type="hidden" id="capture-interest" value="">
          <input type="text" id="capture-interest-text" placeholder="What are you seeking? (optional)" maxlength="120" aria-label="What you're seeking">
          <input type="email" id="capture-email" class="cap-email" placeholder="Your email address" required autocomplete="email" aria-label="Email address">
          <button type="submit" class="btn-gold" id="capture-btn">Send First Teaching →</button>
        </form>
        <div id="capture-msg" class="capture-msg cap-msg"></div>
      </div>
    </div>
  </section>

  <!-- ── MOSAIC BENTO GRID ── -->
  <div class="wrap bento">
    <div class="bento-grid">

      <!-- FEATURED TILE (large) · pre-email: first-teaching pitch · post-email: Start Here embed -->
      <div class="tile span-2 row-2 feat">
        <div class="feat-bg"></div>
        <div class="feat-dots"></div>
        <div class="feat-glass"></div>
        <div class="feat-body" id="start-here">
          <span class="feat-badge">▶ Start Here</span>
          <h3>This Will Challenge What You've Been Told</h3>
          <p>Just one minute. If it raises questions you've never fully answered, that's exactly where this journey begins.</p>
          __VIDEO_BLOCK__
          <div class="feat-pitch" id="feat-pitch">
            <span class="feat-badge">🎁 Free First Teaching</span>
            <p><strong>What Christians Were Really Called Before &ldquo;Christian&rdquo;</strong> — enter your email above and it lands in your inbox instantly.</p>
            <a class="btn-gold" href="#capture" data-cta="hero">Get the First Teaching →</a>
          </div>
        </div>
      </div>

      <!-- TOPIC CHIPS TILE (prefill interest → scroll to capture) -->
      <div class="tile topics">
        <h4>What are you most curious about?</h4>
        <div class="topic-btns">
          <button type="button" class="topic-btn" onclick="pickInterest('Salvation')">Salvation</button>
          <button type="button" class="topic-btn" onclick="pickInterest('Eucharist')">Eucharist</button>
          <button type="button" class="topic-btn" onclick="pickInterest('Papacy')">Papacy</button>
          <button type="button" class="topic-btn" onclick="pickInterest('Mary &amp; Saints')">Mary &amp; Saints</button>
          <button type="button" class="topic-btn" onclick="pickInterest('False Doctrines')">False Doctrines</button>
          <button type="button" class="topic-btn" onclick="pickInterestOther()">Other</button>
        </div>
      </div>

      <!-- AUTHORITY QUOTE TILE -->
      <div class="tile quote">
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10h-9.983zm-14.017 0v-7.391c0-5.704 3.748-9.57 9-10.609l.996 2.151c-2.433.917-3.996 3.638-3.996 5.849h3.983v10h-9.983z"/></svg>
        <blockquote>&ldquo;To be deep in history is to cease to be a Protestant.&rdquo;</blockquote>
        <div>
          <div class="attr">— St. John Henry Newman</div>
          <div class="attr-sub">Grounded in Scripture • The Church Fathers • Ecumenical Councils • The Catechism</div>
        </div>
      </div>

      <!-- DISCOVER HOOK 1 (always-on YouTube surface) -->
      <a class="tile hook js-discover" href="https://youtube.com/shorts/W5f0PJinZgw?si=DNiO1xubXdWbomRz" target="_blank" rel="noopener noreferrer" data-cta="discover_video">
        <div>
          <div class="ic">✠</div>
          <h4><span class="vc-title">What Christians Were Really Called Before “Christian”</span></h4>
          <img class="video-thumbnail" src="https://img.youtube.com/vi/W5f0PJinZgw/hqdefault.jpg" alt="Video thumbnail" loading="lazy" onerror="this.style.display='none'">
          <p>The identity you think you know… isn’t the original.</p>
        </div>
        <div class="go">Watch the truth →</div>
      </a>

      <!-- DISCOVER HOOK 2 -->
      <a class="tile hook js-discover" href="https://youtu.be/K_ofl6fI-1g?si=KQJa6XuSGEeDT0ek" target="_blank" rel="noopener noreferrer" data-cta="discover_video">
        <div>
          <div class="ic">🕊</div>
          <h4><span class="vc-title">Communion in the Hand — What They Didn’t Tell You</span></h4>
          <img class="video-thumbnail" src="https://img.youtube.com/vi/K_ofl6fI-1g/hqdefault.jpg" alt="Video thumbnail" loading="lazy" onerror="this.style.display='none'">
          <p>Reverence lost… or misunderstood?</p>
        </div>
        <div class="go">Watch now →</div>
      </a>

      <!-- GOLD CAPTURE TILE (secondary form) -->
      <div class="tile span-2 gold-tile">
        <h3>Don't rely on algorithms for the truth.</h3>
        <p>Get our deepest historical dives and exclusive video teachings delivered straight to your inbox.</p>
        <form class="capture-form" onsubmit="joinMission(event)" novalidate>
          <input type="email" class="cap-email" placeholder="Your email address" required autocomplete="email" aria-label="Email address">
          <button type="submit" class="btn-gold">Join the Seekers</button>
        </form>
        <div class="capture-msg cap-msg"></div>
      </div>

      <!-- DISCOVER HOOKS 3–6 · small tiles -->
      <div class="span-2 hook-grid">
        <a class="hook-sm js-discover" href="https://youtu.be/UuDAb4oWacU?si=jX_QBheO1j5qOWn7" target="_blank" rel="noopener noreferrer" data-cta="discover_video">
          <div><img class="video-thumbnail" src="https://img.youtube.com/vi/UuDAb4oWacU/hqdefault.jpg" alt="Video thumbnail" loading="lazy" onerror="this.style.display='none'">
          <h4><span class="vc-title">Jesus Never Taught Faith Alone</span></h4>
          <div class="hint">The verse everyone quotes… but never finishes.</div></div>
          <div class="go">Explore →</div>
        </a>
        <a class="hook-sm js-discover" href="https://youtu.be/24Njlocrj_o?si=ywtGlORxqEBu-UyK" target="_blank" rel="noopener noreferrer" data-cta="discover_video">
          <div><img class="video-thumbnail" src="https://img.youtube.com/vi/24Njlocrj_o/hqdefault.jpg" alt="Video thumbnail" loading="lazy" onerror="this.style.display='none'">
          <h4><span class="vc-title">The Eucharist — Symbol or Reality?</span></h4>
          <div class="hint">If it’s just bread… why did disciples walk away?</div></div>
          <div class="go">Explore →</div>
        </a>
        <a class="hook-sm js-discover" href="https://www.youtube.com/playlist?list=PL3yzY55atfNmIzm9EKMBtYpvoF3XMEbsA" target="_blank" rel="noopener noreferrer" data-cta="discover_video">
          <div><h4><span class="vc-title">The Truth About the Papacy</span></h4>
          <div class="hint">Was Peter really the first Pope?</div></div>
          <div class="go">Explore →</div>
        </a>
        <a class="hook-sm js-discover" href="https://www.youtube.com/playlist?list=PL3yzY55atfNmDcTGk5LjRjBHxML29pCEc" target="_blank" rel="noopener noreferrer" data-cta="discover_video">
          <div><h4><span class="vc-title">The Hidden History of the Early Church</span></h4>
          <div class="hint">What the first Christians actually believed.</div></div>
          <div class="go">Explore →</div>
        </a>
      </div>

      <!-- CATEGORY VIDEO TILES (explore grid — open, engage-first, no email gate)
           Rendered by loadExploreGrid() into #explore-cols as .tile.span-2.explore-cat -->
    </div>

    <div id="explore-grid" style="display:none;">
      <div class="strip-head" style="margin-top:24px;">
        <h2 class="serif">Start Exploring the Truth</h2>
        <span class="mark">Fresh teachings rotate in weekly</span>
      </div>
      <div class="bento-grid" id="explore-cols"></div>
    </div>

    <!-- CONTENT HUB · post-signup (admin-curated shorts / playlists / community) -->
    <section class="strip" id="content-hub" style="display:none;margin-top:36px;">
      <div class="strip-head">
        <h2 class="serif">Watch, Explore, Go Deeper</h2>
        <span class="mark">Go Deeper</span>
      </div>
      <div id="hub-shorts" class="hub-shorts"></div>
      <div id="hub-playlists" class="hub-playlists"></div>
      <div id="hub-community" class="hub-community"></div>
    </section>

    <!-- LATEST TEACHINGS (SEO articles cross-link) -->
    <section class="strip" id="latest-teachings" style="display:none;margin-top:36px;">
      <div class="strip-head">
        <h2 class="serif">Latest Teachings</h2>
        <span class="mark">Read &amp; Reflect</span>
      </div>
      <div class="teachings-grid" id="teachings-list"></div>
    </section>
  </div>

  <!-- ── FINAL CTA BAND ── -->
  <section class="final-cta">
    <h2>Your journey into the depths of faith begins here.</h2>
    <p>You don't need more opinions — you need clarity. Rooted in Scripture, the Church Fathers, and the Councils. One teaching at a time.</p>
    <form class="capture-form" onsubmit="joinMission(event)" novalidate>
      <input type="email" class="cap-email" placeholder="Enter your best email" required autocomplete="email" aria-label="Email address">
      <button type="submit" class="btn-gold" data-cta="final">Start Exploring</button>
    </form>
    <div class="capture-msg cap-msg"></div>
    <div class="fine">No spam. No noise. Unsubscribe anytime with one click.</div>
  </section>

  <!-- ── FOOTER ── -->
  <footer class="site-foot">
    <div class="wrap foot-inner">
      <div class="foot-brand">
        <img class="foot-logo" src="__LOGO_URL__" alt="__APP_NAME__ logo">
        <div class="foot-name">Odili</div>
        <div class="foot-copy">The Seeker of Truth © Odili Truth Seeker</div>
      </div>
      <div>
        <div class="foot-links">
          <a href="#capture">✉ Weekly Teachings</a>
          <a href="/truth">Teachings</a>
          <a href="/resources">Resources</a>
        </div>
      </div>
      <div class="foot-social">
        <div class="foot-social-label">Follow the Mission Everywhere</div>
        __FOOTER_SOCIAL__
        <div style="margin-top:14px;">
          <a class="btn-outline" href="__YOUTUBE_URL__" target="_blank" rel="noopener" id="foot-youtube" style="display:none;">▶ YouTube Channel</a>
        </div>
      </div>
    </div>
  </footer>

</main>

<script>
  function escHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ── Acquisition source (?src=platform) + session id ──
  var ACQ_SOURCES = ['youtube', 'email', 'facebook', 'tiktok', 'instagram', 'reddit', 'x'];
  var acqSrc = '';
  try {
    var urlSrc = (new URLSearchParams(window.location.search).get('src') || '').toLowerCase();
    if (ACQ_SOURCES.indexOf(urlSrc) !== -1) {
      acqSrc = urlSrc;
      localStorage.setItem('odili_src', urlSrc); // first/latest touch wins
    } else {
      acqSrc = localStorage.getItem('odili_src') || '';
      if (ACQ_SOURCES.indexOf(acqSrc) === -1) acqSrc = '';
    }
  } catch (e) {}
  var sessionId = '';
  try {
    sessionId = localStorage.getItem('odili_session_id') || '';
    if (!sessionId) {
      sessionId = 's' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
      localStorage.setItem('odili_session_id', sessionId);
    }
  } catch (e) {}

  // ── Behavior tracking → POST /track (fire-and-forget, never blocks UI) ──
  function trackEvent(eventName, data) {
    try {
      var payload = data || {};
      if (acqSrc) payload.src = acqSrc;
      if (sessionId) payload.session_id = sessionId;
      fetch('/track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event: eventName, data: payload })
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

  // ── Topic chips → prefill interest + scroll to the hero capture band ──
  function pickInterest(topic) {
    trackEvent('topic_click', { topic: topic });
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

  // ── "Other" → focus the free-text interest field (always visible in the hero form) ──
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
    const cap = document.getElementById('capture');
    if (cap) cap.scrollIntoView({ behavior: 'smooth' });
    if (other) setTimeout(function () { other.focus(); }, 480);
  }

  // ── Email capture (feeds the mailing list + starts the drip sequence) ──
  // Shared by every capture form on the page (hero band, gold tile, final CTA):
  // fields are resolved from the submitted form so each form shows its own state.
  async function joinMission(e) {
    e.preventDefault();
    const form = e.target;
    const emailEl = form.querySelector('.cap-email') || document.getElementById('capture-email');
    const email = emailEl ? emailEl.value.trim() : '';
    const interestEl = document.getElementById('capture-interest');
    const otherEl = document.getElementById('capture-interest-text');
    let interest = (interestEl && interestEl.value.trim()) ? interestEl.value.trim() : null;
    // A typed "What are you seeking?" value takes precedence over the hidden tag.
    if (otherEl && otherEl.value.trim()) {
      interest = otherEl.value.trim();
    }
    const btn = form.querySelector('button[type="submit"]');
    let msg = null;
    if (form.parentElement) msg = form.parentElement.querySelector('.cap-msg');
    if (!msg) msg = document.getElementById('capture-msg');
    if (msg) msg.className = 'capture-msg cap-msg';

    if (!email) {
      if (msg) { msg.className = 'capture-msg cap-msg err'; msg.textContent = 'Please enter your email address.'; }
      return;
    }

    if (btn) btn.disabled = true;
    const original = btn ? btn.textContent : '';
    if (btn) btn.textContent = 'Joining…';

    try {
      const res = await fetch('/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, interest: interest, source: (acqSrc || 'landing_page') })
      });
      if (res.status === 409) {
        markEmailCaptured();
        if (msg) { msg.className = 'capture-msg cap-msg ok'; msg.textContent = "You're already part of the mission — welcome back."; }
      } else if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        if (msg) { msg.className = 'capture-msg cap-msg err'; msg.textContent = (d && d.detail) ? d.detail : 'Something went wrong. Please try again.'; }
      } else {
        markEmailCaptured();
        trackEvent('signup', { headline: currentHeadline, interest: interest, source: (acqSrc || 'landing_page') });
        if (emailEl) emailEl.value = '';
        if (msg) { msg.className = 'capture-msg cap-msg ok'; msg.textContent = "✓ Welcome — taking you to your first teaching…"; }
        window.location.href = '/thank-you';
        return;
      }
    } catch (err) {
      if (msg) { msg.className = 'capture-msg cap-msg err'; msg.textContent = 'Network error — please check your connection and try again.'; }
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = original; }
    }
  }

  // ── Email-capture state (gates YouTube surfaces pre-signup) ──
  const EMAIL_CAPTURED_KEY = 'odili_email_captured';
  function emailCaptured() {
    try { return localStorage.getItem(EMAIL_CAPTURED_KEY) === '1'; } catch (e) { return false; }
  }
  function markEmailCaptured() {
    try { localStorage.setItem(EMAIL_CAPTURED_KEY, '1'); } catch (e) {}
    try { applyFunnelGates(); } catch (e) {}
  }

  // ── Content hub (admin-curated shorts / playlists / community link) ──
  function isHttp(u) { return /^https?:\\/\\//i.test(String(u || '')); }

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
        cb.innerHTML = '<a class="btn-outline" href="' + escHtml(community) + '" target="_blank" rel="noopener">Join the Community →</a>';
      } else { cb.innerHTML = ''; }

      if (any) sec.style.display = '';
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

  // ── Explore video grid (open — engage-first, no email gate) ──
  function ytId(url) {
    var m = String(url || '').match(/(?:v=|\\/embed\\/|youtu\\.be\\/|\\/shorts\\/)([A-Za-z0-9_-]{6,})/);
    return m ? m[1] : '';
  }
  function exploreCatTile(label, innerHtml) {
    return '<div class="tile span-2 explore-cat">' +
        '<div class="cat-head"><h3><span class="ic">▶</span>' + escHtml(label) + '</h3></div>' +
        innerHtml +
      '</div>';
  }
  async function loadExploreGrid() {
    var sec = document.getElementById('explore-grid');
    var cols = document.getElementById('explore-cols');
    if (!sec || !cols) return;
    try {
      var res = await fetch('/video-grid');
      var data = await res.json();
      var cats = (data && data.categories) || [];
      var withVids = cats.filter(function (c) { return (c.videos || []).length; });
      if (!withVids.length) { renderExploreFallback(sec, cols); return; }
      var html = '';
      withVids.forEach(function (c) {
        var vids = (c.videos || []);
        var inner = '<div class="explore-vids">' + vids.filter(function (v) {
            return /^https?:\\/\\//i.test(String(v.youtube_url || ''));  // defense-in-depth (backend also guards)
          }).map(function (v) {
            var id = ytId(v.youtube_url);
            var thumb = id ? 'https://i.ytimg.com/vi/' + encodeURIComponent(id) + '/hqdefault.jpg' : '';
            return '<a class="mini-vid" href="' + escHtml(v.youtube_url) + '" target="_blank" rel="noopener" data-cta="grid_video">' +
                '<span class="mv-thumb" style="background-image:url(' + escHtml(thumb) + ')"><span class="mv-play">▶</span></span>' +
                '<span class="mv-title">' + escHtml(v.title || 'Watch') + '</span>' +
              '</a>';
          }).join('') + '</div>';
        html += exploreCatTile(c.label, inner);
      });
      cols.innerHTML = html;
      sec.style.display = '';
    } catch (err) { renderExploreFallback(sec, cols); }
  }

  // Failsafe (spec): if the grid can't load, show channel cards — never empty.
  function renderExploreFallback(sec, cols) {
    var FALLBACK_CATS = [
      'Story Quizzes for the Soul', 'Ancient Heresies Exposed',
      'The Battles to Keep the Church Catholic', 'The Venom Series',
      'Prayers', 'Discover More'
    ];
    var html = '';
    FALLBACK_CATS.forEach(function (label) {
      var inner = '<div class="explore-vids"><a class="mini-vid" href="__YOUTUBE_URL__" target="_blank" rel="noopener" data-cta="grid_video">' +
        '<span class="mv-thumb"><span class="mv-play">▶</span></span><span class="mv-title">Watch on the channel →</span></a></div>';
      html += exploreCatTile(label, inner);
    });
    cols.innerHTML = html;
    sec.style.display = '';
  }

  // ── Latest teachings (SEO articles) ──
  async function loadTeachings() {
    var sec = document.getElementById('latest-teachings');
    var box = document.getElementById('teachings-list');
    if (!sec || !box) return;
    try {
      var res = await fetch('/truth-feed');
      var data = await res.json();
      var items = (data && data.items) || [];
      if (!items.length) return;
      box.innerHTML = items.slice(0, 6).map(function (a) {
        return '<a class="teach-card" href="/truth/' + encodeURIComponent(a.slug) + '">' +
            '<div class="tc-title">' + escHtml(a.title) + '</div>' +
            '<div class="tc-desc">' + escHtml(a.meta_description || '') + '</div>' +
            '<span class="tc-more">Read the teaching →</span>' +
          '</a>';
      }).join('');
      sec.style.display = '';
    } catch (err) { /* keep hidden on error */ }
  }

  // ── US phrasing (privacy-safe: coarse country only, nothing stored) ──
  // Light copy adjustment for US visitors. Deliberately does NOT touch the
  // headline (A/B system) or any CTA/tracking attributes.
  async function applyUsPhrasing() {
    try {
      const res = await fetch('/geo/hint');
      const data = await res.json();
      if (!data || data.country !== 'US') return;
      const sub = document.querySelector('.hero .sub');
      if (sub) {
        sub.textContent = "You've probably sensed it too. There are verses that don't quite add up — teachings that skip what the earliest Christians actually believed. This isn't about attacking your faith. It's about getting the full story.";
      }
    } catch (e) { /* fail-silent — never break the funnel */ }
  }

  // Funnel control: the intro video + discover tiles are always visible
  // (video engagement is the hook). After email capture, the remaining
  // surfaces (content hub, footer channel link) unlock and the free-teaching
  // pitch under the video hides.
  function applyFunnelGates() {
    if (!emailCaptured()) return;
    var fp = document.getElementById('feat-pitch');
    if (fp) fp.style.display = 'none';
    var fy = document.getElementById('foot-youtube');
    if (fy) fy.style.display = '';
    document.body.classList.remove('yt-gated');
    loadFeaturedContent();
  }
  applyFunnelGates();
  loadExploreGrid();

  // Discover video-card click tracking (event name allow-listed server-side)
  document.querySelectorAll('.js-discover').forEach(function (card) {
    card.addEventListener('click', function () {
      var t = card.querySelector('.vc-title');
      trackEvent('discover_click', { topic: t ? t.textContent : '', url: card.getAttribute('href') });
    });
  });

  loadTeachings();
  applyUsPhrasing();
</script>

</body>
</html>"""

if FEATURED_VIDEO_ID:
    # Real embed with autoplay+mute. The YouTube thumbnail is painted behind the
    # iframe so a slow/blocked embed degrades to a clickable poster fallback.
    _VIDEO_BLOCK = (
        '<div id="intro-frame" class="video-frame video-frame--embed" '
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
        '<a class="video-frame" href="__YOUTUBE_URL__" target="_blank" rel="noopener" aria-label="Watch on YouTube">'
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


# ── Thank-you page (post-signup) ─────────────────────────────────────────────
# Shown after a successful subscribe. Here — and ONLY here, once the lead is
# captured — we send them to YouTube. This is the moment YouTube CTAs belong.
_THANKYOU_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" type="image/png" href="/static/logo.png">
  <title>You're In — Odili, The Seeker of Truth</title>
  <meta name="robots" content="noindex">
  __ODILI_HEADER_CSS__
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root { --gold:#FFD700; --gold-dk:#c8a426; --red:#8B0000; --black:#000;
            --panel:#0c0c0e; --panel-2:#131316; --text:#f5f1e6; --muted:#9a948a; --border:#26221b; }
    body {
      font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background:var(--black); color:var(--text); min-height:100vh;
      display:flex; flex-direction:column;
    }
    .ty-wrap {
      flex:1; display:flex; align-items:center; justify-content:center;
      padding:120px 20px 60px; text-align:center;
    }
    .ty-card {
      max-width:600px; width:100%; background:var(--panel);
      border:1px solid var(--border); border-radius:20px; padding:48px 34px;
      box-shadow:0 30px 80px rgba(0,0,0,0.5);
    }
    .ty-logo { width:96px; height:auto; margin:0 auto 22px; display:block; }
    .ty-check { font-size:46px; margin-bottom:10px; }
    .ty-card h1 { font-size:34px; line-height:1.15; margin-bottom:16px; }
    .ty-card h1 .gold { color:var(--gold); }
    .ty-lead { color:var(--muted); font-size:16px; line-height:1.6; margin-bottom:14px; }
    .ty-note {
      background:var(--panel-2); border:1px solid var(--border); border-radius:12px;
      padding:16px 18px; font-size:14px; color:var(--muted); margin:22px 0 28px;
    }
    .ty-note strong { color:var(--text); }
    .ty-cta-row { display:flex; flex-direction:column; gap:12px; align-items:stretch; }
    .btn {
      display:inline-flex; align-items:center; justify-content:center; gap:8px;
      padding:16px 26px; border-radius:12px; font-weight:700; font-size:16px;
      text-decoration:none; cursor:pointer; border:1px solid transparent; transition:.18s;
    }
    .btn-primary { background:var(--gold); color:#1a1503; }
    .btn-primary:hover { background:#ffe14d; transform:translateY(-2px); }
    .btn-red { background:var(--red); color:#fff; border-color:#5e0000; }
    .btn-red:hover { background:#b81818; transform:translateY(-2px); }
    .ty-social { margin-top:30px; }
    .ty-social .foot-social-label { font-size:12px; color:var(--muted); margin-bottom:12px; letter-spacing:.04em; text-transform:uppercase; }
    .ty-back { display:block; margin-top:26px; color:#6d685f; font-size:13px; text-decoration:none; }
    .ty-back:hover { color:var(--gold); }
    @media (max-width:560px){ .ty-card{padding:36px 22px;} .ty-card h1{font-size:27px;} }
  </style>
</head>
<body>
__ODILI_HEADER_HTML__
<main class="ty-wrap">
  <div class="ty-card">
    <img class="ty-logo" src="__LOGO_URL__" alt="__APP_NAME__ logo">
    <div class="ty-check">✓</div>
    <h1>You're In. <span class="gold">Welcome to the mission.</span></h1>
    <p class="ty-lead">Your first teaching — <strong>what Christians were really called before &ldquo;Christian&rdquo;</strong> — is on its way to your inbox right now.</p>
    <div class="ty-note">📩 <strong>Check your inbox in the next minute or two.</strong> If you don't see it, look in your Promotions or Spam folder and mark it &ldquo;Not spam&rdquo; so you never miss a teaching.</div>
    <div class="ty-cta-row">
      <a class="btn btn-red" href="__YOUTUBE_URL__" target="_blank" rel="noopener">▶ Watch the 1-Minute Starting Point</a>
      <a class="btn btn-primary" href="__YOUTUBE_URL__" target="_blank" rel="noopener">Subscribe on YouTube →</a>
    </div>
    <div class="ty-social">
      <div class="foot-social-label">Follow the Mission Everywhere</div>
      __FOOTER_SOCIAL__
    </div>
    <a class="ty-back" href="/">← Back to home</a>
  </div>
</main>
</body>
</html>"""

_THANKYOU_HTML = _THANKYOU_HTML.replace("__ODILI_HEADER_CSS__", HEADER_CSS)
_THANKYOU_HTML = _THANKYOU_HTML.replace("__ODILI_HEADER_HTML__", header_html())
_THANKYOU_HTML = _THANKYOU_HTML.replace("__FOOTER_SOCIAL__", social_icons_html())
_THANKYOU_HTML = _THANKYOU_HTML.replace("__LOGO_URL__", LOGO_URL)
_THANKYOU_HTML = _THANKYOU_HTML.replace("__APP_NAME__", APP_NAME)
_THANKYOU_HTML = _THANKYOU_HTML.replace("__YOUTUBE_URL__", YOUTUBE_URL)


@router.get("/thank-you", response_class=HTMLResponse, include_in_schema=False)
async def thank_you_page() -> HTMLResponse:
    """Post-signup page. The one place we intentionally drive to YouTube."""
    return HTMLResponse(content=_THANKYOU_HTML)


@router.get("/welcome", response_class=HTMLResponse, include_in_schema=False)
async def welcome_page() -> HTMLResponse:
    """Alias for the thank-you page."""
    return HTMLResponse(content=_THANKYOU_HTML)
