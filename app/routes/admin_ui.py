"""
Admin dashboard UI — served at GET /admin.

Self-contained single-page HTML/JS application. Handles its own API key
authentication client-side (stores key in sessionStorage) and calls the
existing FastAPI endpoints. No server-side auth required for the page itself.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.branding import HEADER_CSS, header_html

router = APIRouter()

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" type="image/png" href="/static/logo.png">
  <title>Odili's Truth Seeker — Admin</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:        #0d1117;
      --surface:   #161b26;
      --card:      #1e2535;
      --border:    #2a3347;
      --text:      #e2e8f0;
      --muted:     #64748b;
      --gold:      #d4af37;
      --gold-dim:  #a8882a;
      --red:       #c41e3a;
      --red-light: #e02244;
      --green:     #22c55e;
      --green-bg:  rgba(34,197,94,.12);
      --danger-bg: rgba(196,30,58,.12);
      --yellow-bg: rgba(212,175,55,.12);
      --header-h:  60px;
    }

    html, body { height: 100%; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: var(--bg); color: var(--text); font-size: 14px;
      line-height: 1.5;
    }

    /* ═══════════════════ LOGIN ═══════════════════ */
    #login {
      display: flex; align-items: center; justify-content: center;
      min-height: 100vh; padding: 96px 24px 24px; background: var(--bg);
    }
    .login-card {
      background: var(--surface); max-width: 400px; width: 100%;
      border-radius: 12px; border: 1px solid var(--border);
      overflow: hidden; box-shadow: 0 24px 48px rgba(0,0,0,.5);
    }
    .login-bar { height: 3px; background: linear-gradient(90deg, var(--red), var(--gold)); }
    .resource-link { color: #d4af37; text-decoration: underline; font-weight: 500; cursor: pointer; }
    .resource-link:hover { color: gold; }
    .resource-link strong { color: inherit; }
    .login-body { padding: 40px 36px; }
    .login-brand {
      display: flex; align-items: center; gap: 10px; margin-bottom: 28px;
    }
    .login-brand-icon {
      width: 36px; height: 36px; border-radius: 8px;
      object-fit: cover; display: block;
    }
    .login-brand-name { font-size: 15px; font-weight: 700; color: var(--text); }
    .login-brand-sub  { font-size: 11px; color: var(--muted); }
    .login-title { font-size: 22px; font-weight: 700; margin-bottom: 6px; }
    .login-sub   { font-size: 13px; color: var(--muted); margin-bottom: 28px; }
    .login-label { font-size: 12px; font-weight: 600; color: var(--muted);
      text-transform: uppercase; letter-spacing: .6px; display: block; margin-bottom: 7px; }
    .login-input {
      width: 100%; padding: 11px 14px; font-size: 14px; font-family: monospace;
      background: var(--bg); color: var(--text);
      border: 1px solid var(--border); border-radius: 8px; outline: none;
      transition: border-color .2s;
    }
    .login-input:focus { border-color: var(--gold); }
    .login-btn {
      margin-top: 16px; width: 100%; padding: 12px;
      background: linear-gradient(135deg, var(--red), var(--gold));
      color: #fff; border: none; border-radius: 8px;
      font-size: 14px; font-weight: 600; cursor: pointer;
      transition: opacity .2s;
    }
    .login-btn:hover { opacity: .88; }
    .login-err { margin-top: 12px; font-size: 13px; color: var(--red); min-height: 18px; }

    /* ═══════════════════ APP SHELL ═══════════════════ */
    #app { display: none; height: 100vh; overflow: hidden; }

    /* Top Navigation Bar (Command Center) */
    .topnav {
      position: fixed; top: 0; left: 0; right: 0; height: var(--header-h);
      background: rgba(26,31,46,.92); backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--border);
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 20px; z-index: 60; gap: 12px;
    }
    .topnav-left { display: flex; align-items: center; gap: 18px; min-width: 0; }
    .topnav-brand { display: flex; align-items: center; gap: 10px; flex-shrink: 0; cursor: pointer; }
    .topnav-brand-icon {
      width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
      object-fit: cover; display: block;
      box-shadow: 0 0 12px rgba(212,175,55,.35);
    }
    .topnav-brand-name {
      font-family: Georgia, 'Times New Roman', serif;
      font-size: 16px; font-weight: 600; letter-spacing: .4px;
      color: var(--text); white-space: nowrap;
    }
    .topnav-menus { display: flex; align-items: center; gap: 2px; }
    .topnav-home {
      display: flex; align-items: center; gap: 7px; padding: 7px 13px;
      border-radius: 8px; cursor: pointer; color: var(--muted);
      font-size: 13px; font-weight: 500; white-space: nowrap;
      transition: background .15s, color .15s;
    }
    .topnav-home:hover { background: rgba(255,255,255,.05); color: var(--text); }
    .topnav-home.active { background: rgba(212,175,55,.12); color: var(--gold); }
    .topnav-group { position: relative; }
    .topnav-group-btn {
      display: flex; align-items: center; gap: 6px; padding: 7px 13px;
      border-radius: 8px; cursor: pointer; color: var(--muted);
      font-size: 13px; font-weight: 500; background: none; border: 1px solid transparent;
      transition: background .15s, color .15s; white-space: nowrap;
    }
    .topnav-group-btn:hover { background: rgba(255,255,255,.05); color: var(--text); }
    .topnav-group-btn.active { background: rgba(212,175,55,.12); color: var(--gold); border-color: rgba(212,175,55,.25); }
    .topnav-group-btn .caret { font-size: 9px; opacity: .6; }
    .topnav-group.open .topnav-group-btn { background: rgba(255,255,255,.06); color: var(--text); }
    .topnav-dropdown {
      display: none; position: absolute; top: calc(100% + 8px); left: 0;
      min-width: 230px; max-height: calc(100vh - 90px); overflow-y: auto;
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 12px; padding: 8px;
      box-shadow: 0 18px 40px rgba(0,0,0,.55); z-index: 70;
    }
    .topnav-group.open .topnav-dropdown { display: block; }
    .nav-item {
      display: flex; align-items: center; gap: 10px; padding: 9px 12px;
      border-radius: 8px; cursor: pointer; color: var(--muted);
      font-size: 13px; font-weight: 500;
      transition: background .15s, color .15s; margin-bottom: 2px;
      white-space: nowrap;
    }
    .nav-item:hover { background: rgba(255,255,255,.04); color: var(--text); }
    .nav-item.active { background: rgba(212,175,55,.12); color: var(--gold); }
    .nav-item.active .nav-icon { color: var(--gold); }
    .nav-icon { font-size: 16px; width: 20px; text-align: center; flex-shrink: 0; }

    .topnav-right { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
    .topnav-page {
      font-size: 13px; font-weight: 600; color: var(--muted);
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 220px;
    }
    .signout-btn {
      display: flex; align-items: center; gap: 8px; padding: 7px 12px;
      border-radius: 8px; cursor: pointer; color: var(--muted);
      font-size: 13px; font-weight: 500; background: none; border: none;
      transition: background .15s, color .15s; white-space: nowrap;
    }
    .signout-btn:hover { background: var(--danger-bg); color: var(--red); }

    .status-pill {
      display: flex; align-items: center; gap: 6px;
      background: rgba(34,197,94,.08); border: 1px solid rgba(34,197,94,.25);
      border-radius: 20px; padding: 5px 12px; font-size: 12px; color: var(--muted);
      white-space: nowrap;
    }
    .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--green); }

    /* Main content area */
    .main-content {
      margin-top: var(--header-h);
      height: calc(100vh - var(--header-h));
      overflow-y: auto;
      padding: 28px;
      max-width: 1480px; margin-left: auto; margin-right: auto;
    }

    /* ═══════════════════ PAGE PANELS ═══════════════════ */
    .page { display: none; }
    .page.active { display: block; }

    /* ── Page header ── */
    .page-header { margin-bottom: 24px; }
    .page-header h1 { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
    .page-header p  { font-size: 13px; color: var(--muted); }

    /* ── Grid ── */
    .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
    .grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }

    /* ── Stat card ── */
    .stat-card {
      background: var(--card); border-radius: 12px; border: 1px solid var(--border);
      padding: 20px 22px; position: relative; overflow: hidden;
    }
    .stat-card::before {
      content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
      background: linear-gradient(90deg, var(--red), var(--gold));
    }
    .stat-label { font-size: 11px; font-weight: 600; color: var(--muted);
      text-transform: uppercase; letter-spacing: .6px; margin-bottom: 10px; }
    .stat-value { font-size: 30px; font-weight: 700; color: var(--text); line-height: 1; }
    .stat-sub   { font-size: 12px; color: var(--muted); margin-top: 6px; }
    .stat-icon  { position: absolute; top: 18px; right: 18px; font-size: 22px; opacity: .3; }

    /* ── Card ── */
    .card {
      background: var(--card); border-radius: 12px; border: 1px solid var(--border);
      margin-bottom: 20px; overflow: hidden;
    }
    .card-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 16px 20px; border-bottom: 1px solid var(--border);
    }
    .card-header-left { display: flex; align-items: center; gap: 8px; }
    .card-title { font-size: 14px; font-weight: 600; }
    .card-body  { padding: 20px; }

    /* ── Table ── */
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    thead th {
      text-align: left; font-size: 10px; font-weight: 700;
      text-transform: uppercase; letter-spacing: .7px; color: var(--muted);
      padding: 10px 16px; border-bottom: 1px solid var(--border);
      background: rgba(255,255,255,.02);
    }
    tbody td { padding: 11px 16px; border-bottom: 1px solid rgba(42,51,71,.6); }
    tbody tr:last-child td { border-bottom: none; }
    tbody tr:hover td { background: rgba(255,255,255,.02); }
    .empty-row td { color: var(--muted); text-align: center; padding: 32px; font-style: italic; }

    /* ── Badges ── */
    .badge {
      display: inline-block; padding: 3px 9px; border-radius: 12px;
      font-size: 11px; font-weight: 600;
    }
    .badge-green  { background: var(--green-bg); color: var(--green); }
    .badge-red    { background: var(--danger-bg); color: var(--red); }
    .badge-yellow { background: var(--yellow-bg); color: var(--gold); }

    /* ── Buttons ── */
    .btn {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600;
      cursor: pointer; border: none; transition: all .2s; white-space: nowrap;
    }
    .btn-primary {
      background: linear-gradient(135deg, var(--red), var(--gold));
      color: #fff;
    }
    .btn-primary:hover  { opacity: .88; }
    .btn-primary:disabled { opacity: .4; cursor: not-allowed; }
    .btn-secondary {
      background: var(--card); color: var(--text);
      border: 1px solid var(--border);
    }
    .btn-secondary:hover { border-color: var(--gold); color: var(--gold); }
    .btn-danger { background: var(--danger-bg); color: var(--red); border: 1px solid rgba(196,30,58,.3); }
    .btn-danger:hover { background: rgba(196,30,58,.2); }
    .btn-sm { padding: 6px 12px; font-size: 12px; }
    .btn-row { display: flex; gap: 10px; flex-wrap: wrap; }

    /* ── Form ── */
    .field { margin-bottom: 16px; }
    .field label {
      display: block; font-size: 12px; font-weight: 600; color: var(--muted);
      text-transform: uppercase; letter-spacing: .5px; margin-bottom: 7px;
    }
    .field input, .field textarea, .field select {
      width: 100%; padding: 10px 14px; font-size: 14px;
      background: var(--bg); color: var(--text);
      border: 1px solid var(--border); border-radius: 8px; outline: none;
      transition: border-color .2s; font-family: inherit;
    }
    .field input:focus, .field textarea:focus, .field select:focus {
      border-color: var(--gold);
    }
    .field textarea { min-height: 140px; resize: vertical; line-height: 1.6; }
    .field-hint { font-size: 12px; color: var(--muted); margin-top: 5px; }

    /* ── Status bar ── */
    .status-bar {
      padding: 12px 16px; border-radius: 8px; font-size: 13px;
      display: none; margin-top: 14px;
    }
    .status-bar.success { background: var(--green-bg); color: var(--green); border: 1px solid rgba(34,197,94,.2); }
    .status-bar.error   { background: var(--danger-bg); color: var(--red);   border: 1px solid rgba(196,30,58,.2); }

    /* ── Spinner ── */
    .spinner {
      display: inline-block; width: 12px; height: 12px;
      border: 2px solid rgba(255,255,255,.3); border-top-color: #fff;
      border-radius: 50%; animation: spin .7s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ── Preview modal ── */
    #preview-modal {
      display: none; position: fixed; inset: 0;
      background: rgba(0,0,0,.7); z-index: 200;
      align-items: center; justify-content: center; padding: 24px;
    }
    #preview-modal.open { display: flex; }
    .modal-box {
      background: var(--surface); border-radius: 12px; border: 1px solid var(--border);
      width: 100%; max-width: 680px; max-height: 90vh;
      display: flex; flex-direction: column;
      box-shadow: 0 24px 64px rgba(0,0,0,.6);
    }
    .modal-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 16px 20px; border-bottom: 1px solid var(--border);
    }
    .modal-header h3 { font-size: 15px; font-weight: 600; }
    .modal-close {
      background: none; border: none; color: var(--muted); font-size: 20px;
      cursor: pointer; padding: 2px 6px; border-radius: 4px;
      transition: color .2s;
    }
    .modal-close:hover { color: var(--text); }
    #preview-frame { flex: 1; border: none; min-height: 420px; }

    /* ── Add-sub row ── */
    .add-row { display: flex; gap: 10px; margin-bottom: 6px; }
    .add-row input {
      flex: 1; padding: 9px 14px; font-size: 13px; font-family: inherit;
      background: var(--bg); color: var(--text);
      border: 1px solid var(--border); border-radius: 8px; outline: none;
      transition: border-color .2s;
    }
    .add-row input:focus { border-color: var(--gold); }

    /* ── Insight cards ── */
    .insight-list { list-style: none; }
    .insight-list li {
      padding: 10px 12px; background: var(--bg); border-radius: 8px;
      border-left: 3px solid var(--gold); margin-bottom: 8px;
      font-size: 13px; line-height: 1.5;
    }
    .insight-list li:last-child { margin-bottom: 0; }

    /* ── Content idea result ── */
    .idea-result {
      background: var(--bg); border-radius: 12px; border: 1px solid var(--border);
      padding: 20px; margin-top: 20px; display: none;
    }
    .idea-result.visible { display: block; }
    .idea-result-title { font-size: 18px; font-weight: 700; color: var(--gold); margin-bottom: 12px; }
    .idea-result-section { margin-bottom: 16px; }
    .idea-result-section h4 { font-size: 11px; font-weight: 700; color: var(--muted);
      text-transform: uppercase; letter-spacing: .6px; margin-bottom: 6px; }
    .idea-result-section p { font-size: 13px; line-height: 1.6; }

    /* ── Settings ── */
    .setting-row {
      display: flex; align-items: flex-start; justify-content: space-between;
      gap: 20px; padding: 18px 0; border-bottom: 1px solid var(--border);
    }
    .setting-row:last-child { border-bottom: none; }
    .setting-info h4 { font-size: 14px; font-weight: 600; margin-bottom: 3px; }
    .setting-info p  { font-size: 12px; color: var(--muted); }

    /* ── Top-video highlight ── */
    .highlight-card {
      background: linear-gradient(135deg, rgba(196,30,58,.1), rgba(212,175,55,.1));
      border-radius: 12px; border: 1px solid rgba(212,175,55,.25); padding: 20px;
    }
    .highlight-label { font-size: 11px; font-weight: 700; color: var(--gold);
      text-transform: uppercase; letter-spacing: .7px; margin-bottom: 8px; }
    .highlight-title { font-size: 17px; font-weight: 700; margin-bottom: 8px; }
    .highlight-meta  { display: flex; gap: 16px; font-size: 12px; color: var(--muted); }

    /* ── Title improvement card ── */
    .title-pair {
      background: var(--bg); border-radius: 8px; border: 1px solid var(--border);
      padding: 12px 14px; margin-bottom: 10px;
    }
    .title-pair:last-child { margin-bottom: 0; }
    .title-original {
      font-size: 12px; color: var(--muted); margin-bottom: 6px;
      text-decoration: line-through; line-height: 1.4;
    }
    .title-improved {
      font-size: 13px; font-weight: 600; color: var(--text); line-height: 1.4;
      margin-bottom: 8px;
    }
    .title-pair-actions { display: flex; gap: 6px; }

    /* ── Playlist idea card ── */
    .playlist-card {
      background: var(--bg); border-radius: 8px; border: 1px solid var(--border);
      padding: 12px 14px; margin-bottom: 10px;
    }
    .playlist-card:last-child { margin-bottom: 0; }
    .playlist-title { font-size: 13px; font-weight: 700; color: var(--gold); margin-bottom: 4px; }
    .playlist-desc  { font-size: 12px; color: var(--muted); line-height: 1.5; margin-bottom: 8px; }

    /* ── Suggested topic row ── */
    .topic-row {
      display: flex; align-items: flex-start; justify-content: space-between;
      gap: 10px; padding: 10px 12px; background: var(--bg);
      border-radius: 8px; border-left: 3px solid var(--gold);
      margin-bottom: 8px; font-size: 13px; line-height: 1.5;
    }
    .topic-row:last-child { margin-bottom: 0; }
    .topic-row-text { flex: 1; }

    /* ── AI note banner ── */
    .ai-note {
      display: flex; align-items: center; gap: 10px;
      background: var(--yellow-bg); border: 1px solid rgba(212,175,55,.25);
      border-radius: 8px; padding: 10px 14px; margin-bottom: 16px;
      font-size: 12px; color: var(--gold);
    }

    /* ── Toast ── */
    #toast {
      position: fixed; bottom: 28px; right: 28px;
      background: var(--surface); color: var(--text);
      border: 1px solid var(--border); border-radius: 10px;
      padding: 12px 18px; font-size: 13px; font-weight: 500;
      box-shadow: 0 8px 24px rgba(0,0,0,.4);
      transform: translateY(20px); opacity: 0;
      transition: transform .25s, opacity .25s;
      z-index: 300; pointer-events: none;
    }
    #toast.show { transform: translateY(0); opacity: 1; }

    /* ── Script modal ── */
    #script-modal {
      display: none; position: fixed; inset: 0;
      background: rgba(0,0,0,.72); z-index: 200;
      align-items: center; justify-content: center; padding: 24px;
    }
    #script-modal.open { display: flex; }
    .script-modal-box {
      background: var(--surface); border-radius: 14px; border: 1px solid var(--border);
      width: 100%; max-width: 680px; max-height: 90vh;
      display: flex; flex-direction: column;
      box-shadow: 0 24px 72px rgba(0,0,0,.65);
    }
    .script-modal-header {
      display: flex; align-items: flex-start; justify-content: space-between;
      padding: 18px 22px; border-bottom: 1px solid var(--border); flex-shrink: 0;
      gap: 12px;
    }
    .script-modal-body { flex: 1; overflow-y: auto; padding: 20px; }
    .script-modal-footer {
      display: flex; gap: 10px; padding: 14px 22px;
      border-top: 1px solid var(--border); flex-shrink: 0; flex-wrap: wrap;
    }
    .script-section { margin-bottom: 20px; }
    .script-section:last-child { margin-bottom: 0; }
    .script-section-label {
      font-size: 10px; font-weight: 700; color: var(--muted);
      text-transform: uppercase; letter-spacing: .7px; margin-bottom: 8px;
    }
    .script-hook {
      font-size: 14px; line-height: 1.65; color: var(--text);
      background: var(--bg); padding: 12px 16px; border-radius: 8px;
      border-left: 3px solid var(--gold);
    }
    .script-body {
      font-size: 13px; line-height: 1.85; color: var(--text);
      white-space: pre-wrap; background: var(--bg);
      padding: 14px 16px; border-radius: 8px;
      border: 1px solid var(--border);
      max-height: 280px; overflow-y: auto;
    }
    .script-generating {
      display: flex; flex-direction: column; align-items: center; gap: 14px;
      padding: 48px 24px; color: var(--muted); font-size: 13px;
    }

    /* ── Loader overlay ── */
    .loader-overlay {
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; gap: 12px; padding: 48px;
      color: var(--muted); font-size: 13px;
    }
    .loader-spinner {
      width: 28px; height: 28px; border: 3px solid var(--border);
      border-top-color: var(--gold); border-radius: 50%;
      animation: spin .8s linear infinite;
    }

    /* ── Responsive ── */
    @media (max-width: 900px) {
      .grid-4 { grid-template-columns: repeat(2, 1fr); }
      .grid-3 { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 900px) {
      .topnav-page { display: none; }
      .topnav-brand-name { display: none; }
    }
    @media (max-width: 640px) {
      .topnav { padding: 0 10px; gap: 6px; }
      .topnav-left { gap: 8px; overflow-x: auto; }
      .status-pill { display: none; }
      .grid-4, .grid-3, .grid-2 { grid-template-columns: 1fr; }
    }

    /* ── Growth Engine ── */
    .daily-flow { background: linear-gradient(135deg, rgba(196,30,58,.14), rgba(212,175,55,.12)); border: 1px solid rgba(212,175,55,.32); border-radius: 12px; padding: 14px 18px; margin-bottom: 18px; }
    .daily-flow-title { font-size: 12px; font-weight: 800; letter-spacing: 1.2px; color: var(--gold); margin-bottom: 10px; }
    .daily-flow-steps { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 10px; }
    .df-step { display: flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 600; color: var(--text); }
    .df-num { flex-shrink: 0; width: 20px; height: 20px; border-radius: 50%; background: var(--gold); color: #1a1300; font-size: 11px; font-weight: 800; display: flex; align-items: center; justify-content: center; }
    .df-arrow { color: var(--gold); font-weight: 800; opacity: .7; }
    @media (max-width: 640px) { .df-arrow { display: none; } .df-step { width: 100%; } }
    .growth-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; margin-bottom: 18px; }
    .growth-card-title { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
    .growth-card-title .gi { font-size: 16px; }
    .growth-card-sub { font-size: 12px; color: var(--muted); margin-bottom: 16px; line-height: 1.5; }
    .metric-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }
    .metric-box { background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
    .metric-box.gold { border-color: rgba(212,175,55,.45); box-shadow: 0 0 0 1px rgba(212,175,55,.12) inset; }
    .metric-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .7px; color: var(--muted); margin-bottom: 6px; }
    .metric-value { font-size: 20px; font-weight: 800; color: var(--text); line-height: 1.2; }
    .metric-value.gold { color: var(--gold); }
    .next-box { background: linear-gradient(135deg, rgba(196,30,58,.10), rgba(212,175,55,.10)); border: 1px solid rgba(212,175,55,.30); border-radius: 10px; padding: 14px 16px; }
    .next-box .metric-label { color: var(--gold); }
    .next-box .next-text { font-size: 14px; font-weight: 600; color: var(--text); line-height: 1.5; }

    .hook-item, .plan-item { display: flex; gap: 12px; align-items: flex-start; background: var(--bg); border: 1px solid var(--border); border-left: 3px solid var(--gold); border-radius: 8px; padding: 11px 14px; margin-bottom: 9px; }
    .hook-num { flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%; background: rgba(212,175,55,.15); color: var(--gold); font-size: 11px; font-weight: 800; display: flex; align-items: center; justify-content: center; }
    .hook-text { font-size: 13px; line-height: 1.5; color: var(--text); flex: 1; }
    .plan-day { flex-shrink: 0; width: 96px; }
    .plan-day-name { font-size: 12px; font-weight: 800; color: var(--gold); }
    .plan-day-time { font-size: 11px; color: var(--muted); }
    .plan-title { font-size: 13px; font-weight: 600; color: var(--text); line-height: 1.4; }
    .plan-idea { font-size: 12px; color: var(--muted); margin-top: 3px; line-height: 1.45; }

    .cta-block { background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; margin-bottom: 12px; }
    .cta-block-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
    .cta-block-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .6px; color: var(--gold); }
    .cta-block-text { font-size: 13px; line-height: 1.6; color: var(--text); white-space: pre-wrap; }

    .flow-num { width: 26px; height: 26px; border-radius: 50%; background: var(--gold); color: var(--black); font-weight: 800; font-size: 13px; display: flex; align-items: center; justify-content: center; }

    .today-card { border-color: rgba(212,175,55,.45); }
    .today-title { font-size: 20px; font-weight: 800; color: var(--gold); line-height: 1.3; }
    .today-status { font-size: 12px; color: var(--muted); margin-top: 6px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; }
    .today-status.done { color: #5ad17a; }
    .today-actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }

    .sched-list { display: flex; flex-direction: column; gap: 9px; }
    .sched-row { display: flex; align-items: center; gap: 14px; background: var(--bg); border: 1px solid var(--border); border-left: 3px solid var(--gold); border-radius: 8px; padding: 11px 14px; }
    .sched-row.done { opacity: .6; border-left-color: #5ad17a; }
    .sched-date { font-size: 12px; font-weight: 800; color: var(--gold); text-transform: uppercase; min-width: 56px; display: flex; flex-direction: column; }
    .sched-date span { font-size: 11px; font-weight: 600; color: var(--muted); text-transform: none; }
    .sched-title { flex: 1; font-size: 14px; font-weight: 600; color: var(--text); }
    .sched-badge { font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: .5px; color: var(--gold); background: var(--card); border: 1px solid var(--border); border-radius: 20px; padding: 3px 10px; }
    .sched-badge.done { color: #5ad17a; border-color: rgba(90,209,122,.4); }
    /* Posting-day selector */
    .day-toggle-row { display: flex; flex-wrap: wrap; gap: 9px; margin-top: 6px; }
    .day-toggle {
      flex: 1 1 auto; min-width: 92px; text-align: center; cursor: pointer;
      padding: 11px 8px; border-radius: 10px; font-size: 13px; font-weight: 700;
      letter-spacing: .3px; user-select: none;
      background: var(--bg); color: var(--gold); border: 1.5px solid var(--gold);
      transition: transform .12s ease, box-shadow .2s ease, background .2s ease, color .2s ease;
    }
    .day-toggle:hover { box-shadow: 0 0 0 3px rgba(212,175,55,.18); transform: translateY(-1px); }
    .day-toggle.on {
      background: #FFD700; color: #1a1a1a; border-color: #FFD700;
      box-shadow: 0 0 14px rgba(255,215,0,.35); transform: scale(1.03);
    }
    .day-toggle.on:hover { box-shadow: 0 0 18px rgba(255,215,0,.5); }

    .kanban { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
    .kanban-col { background: var(--bg); border: 1px solid var(--border); border-radius: 12px; padding: 12px; min-height: 120px; }
    .kanban-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
    .kanban-stage { font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: .6px; color: var(--gold); }
    .kanban-count { font-size: 11px; font-weight: 700; color: var(--muted); background: var(--card); border-radius: 20px; padding: 2px 9px; }
    .pl-card { background: var(--card); border: 1px solid var(--border); border-radius: 9px; padding: 11px 12px; margin-bottom: 9px; }
    .pl-card-title { font-size: 13px; font-weight: 600; color: var(--text); line-height: 1.4; margin-bottom: 6px; }
    .pl-card-meta { font-size: 10px; color: var(--muted); margin-bottom: 9px; }
    .pl-actions { display: flex; align-items: center; gap: 6px; }
    .pl-btn { flex: 1; background: var(--bg); border: 1px solid var(--border); color: var(--muted); border-radius: 6px; padding: 5px 0; font-size: 12px; cursor: pointer; transition: all .15s; }
    .pl-btn:hover:not(:disabled) { border-color: var(--gold); color: var(--gold); }
    .pl-btn:disabled { opacity: .3; cursor: not-allowed; }
    .pl-btn.del:hover { border-color: var(--red); color: var(--red); }
    .kanban-empty { font-size: 11px; color: var(--muted); text-align: center; padding: 16px 4px; font-style: italic; }
    /* Weekly schedule calendar */
    .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 10px; }
    .cal-cell { background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 10px; min-height: 120px; display: flex; flex-direction: column; }
    .cal-cell.filled { border-color: rgba(212,175,55,.4); box-shadow: 0 0 0 1px rgba(212,175,55,.1) inset; }
    .cal-day { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .6px; color: var(--gold); margin-bottom: 6px; }
    .cal-time { font-size: 10px; color: var(--muted); margin-bottom: 6px; }
    .cal-title { font-size: 12px; font-weight: 700; color: var(--text); line-height: 1.35; }
    .cal-idea { font-size: 11px; color: var(--muted); line-height: 1.4; margin-top: 5px; }
    .cal-empty { font-size: 16px; color: var(--border); text-align: center; margin: auto 0; }
    /* Performance feedback */
    .perf-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
    .perf-item { background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 13px 15px; }
    .perf-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
    .perf-name { font-size: 14px; font-weight: 700; color: var(--gold); text-transform: capitalize; }
    .perf-top { font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: .5px; color: var(--black); background: var(--gold); border-radius: 20px; padding: 2px 8px; }
    .perf-meta { font-size: 11px; color: var(--muted); }
    @media (max-width: 980px) {
      .growth-grid { grid-template-columns: 1fr; }
      .kanban { grid-template-columns: repeat(2, 1fr); }
      .cal-grid { grid-template-columns: repeat(4, 1fr); }
    }
    @media (max-width: 560px) {
      .cal-grid { grid-template-columns: repeat(2, 1fr); }
      .kanban { grid-template-columns: 1fr; }
      .metric-row { grid-template-columns: 1fr; }
    }
  </style>
  __ODILI_HEADER_CSS__
</head>
<body>

<!-- ═══════════════════ LOGIN ═══════════════════ -->
<div id="login">
  __ODILI_HEADER_HTML__
  <div class="login-card">
    <div class="login-bar"></div>
    <div class="login-body">
      <div class="login-brand">
        <img class="login-brand-icon" src="/static/logo.png" alt="Odili's Truth Seeker logo">
        <div>
          <div class="login-brand-name">Odili's Truth Seeker</div>
          <div class="login-brand-sub">Catholic Media Ministry</div>
        </div>
      </div>
      <h1 class="login-title">Admin Dashboard</h1>
      <p class="login-sub">Sign in with your API key to continue.</p>
      <label class="login-label" for="key-input">API Key</label>
      <input id="key-input" class="login-input" type="password"
             placeholder="Enter your admin API key…" autocomplete="current-password">
      <button class="login-btn" onclick="login()">Sign In</button>
      <div class="login-err" id="login-err"></div>
    </div>
  </div>
</div>

<!-- ═══════════════════ APP SHELL ═══════════════════ -->
<div id="app">

  <!-- Top Navigation Bar -->
  <header class="topnav">
    <div class="topnav-left">
      <div class="topnav-brand" onclick="navigate('dashboard')">
        <img class="topnav-brand-icon" src="/static/logo.png" alt="Odili's Truth Seeker logo">
        <span class="topnav-brand-name">Odili Truth Seeker</span>
      </div>
      <nav class="topnav-menus">
        <div class="nav-item topnav-home active" onclick="navigate('dashboard')" data-page="dashboard">
          <span class="nav-icon">⊞</span> Dashboard
        </div>
        <div class="topnav-group" id="group-grow">
          <button class="topnav-group-btn" onclick="toggleMenu(event,'grow')">Grow <span class="caret">▾</span></button>
          <div class="topnav-dropdown">
            <div class="nav-item" onclick="navigate('growth-brain')" data-page="growth-brain"><span class="nav-icon">🚀</span> Growth Brain</div>
            <div class="nav-item" onclick="navigate('growth')" data-page="growth"><span class="nav-icon">🚀</span> Growth Engine</div>
            <div class="nav-item" onclick="navigate('growth-pack')" data-page="growth-pack"><span class="nav-icon">🧠</span> Growth Pack</div>
            <div class="nav-item" onclick="navigate('lead-discovery')" data-page="lead-discovery"><span class="nav-icon">🔎</span> Lead Discovery<span id="ld-tab-badge" style="display:none;margin-left:6px;background:rgba(212,175,55,.18);color:var(--gold);border:1px solid rgba(212,175,55,.45);border-radius:10px;padding:1px 7px;font-size:11px;font-weight:700;vertical-align:middle"></span></div>
            <div class="nav-item" onclick="navigate('lead-evangelist')" data-page="lead-evangelist"><span class="nav-icon">🕊️</span> Lead Evangelist</div>
            <div class="nav-item" onclick="navigate('reply-engine')" data-page="reply-engine"><span class="nav-icon">💬</span> Reply Engine</div>
            <div class="nav-item" onclick="navigate('conversion-engine')" data-page="conversion-engine"><span class="nav-icon">⚡</span> Conversion Engine</div>
            <div class="nav-item" onclick="navigate('traffic-engine')" data-page="traffic-engine"><span class="nav-icon">🎬</span> Traffic Engine</div>
            <div class="nav-item" onclick="navigate('seo-engine')" data-page="seo-engine"><span class="nav-icon">🔍</span> SEO Engine</div>
          </div>
        </div>
        <div class="topnav-group" id="group-content">
          <button class="topnav-group-btn" onclick="toggleMenu(event,'content')">Content <span class="caret">▾</span></button>
          <div class="topnav-dropdown">
            <div class="nav-item" onclick="navigate('content-hub')" data-page="content-hub"><span class="nav-icon">🎬</span> Content Hub</div>
            <div class="nav-item" onclick="navigate('ideas')" data-page="ideas"><span class="nav-icon">💡</span> Content Ideas</div>
            <div class="nav-item" onclick="navigate('content-plan')" data-page="content-plan"><span class="nav-icon">🧭</span> Content Plan</div>
            <div class="nav-item" onclick="navigate('video-grid')" data-page="video-grid"><span class="nav-icon">🎞️</span> Video Grid</div>
            <div class="nav-item" onclick="navigate('weekly-distribution')" data-page="weekly-distribution"><span class="nav-icon">📢</span> Weekly Distribution</div>
            <div class="nav-item" onclick="navigate('saved-scripts')" data-page="saved-scripts"><span class="nav-icon">💾</span> Saved Scripts</div>
            <div class="nav-item" onclick="navigate('youtube')" data-page="youtube"><span class="nav-icon">▶</span> YouTube Intelligence</div>
            <div class="nav-item" onclick="navigate('youtube-playbook')" data-page="youtube-playbook"><span class="nav-icon">📘</span> YouTube Playbook</div>
            <div class="nav-item" onclick="navigate('youtube-kit')" data-page="youtube-kit"><span class="nav-icon">🎬</span> YouTube Studio Kit</div>
          </div>
        </div>
        <div class="topnav-group" id="group-audience">
          <button class="topnav-group-btn" onclick="toggleMenu(event,'audience')">Audience <span class="caret">▾</span></button>
          <div class="topnav-dropdown">
            <div class="nav-item" onclick="navigate('analytics')" data-page="analytics"><span class="nav-icon">📊</span> Analytics</div>
            <div class="nav-item" onclick="navigate('audience-geo')" data-page="audience-geo"><span class="nav-icon">🌎</span> Audience Geography</div>
            <div class="nav-item" onclick="navigate('topics')" data-page="topics"><span class="nav-icon">🗳️</span> Audience Topics</div>
            <div class="nav-item" onclick="navigate('subscribers')" data-page="subscribers"><span class="nav-icon">👥</span> Subscribers</div>
            <div class="nav-item" onclick="navigate('newsletter')" data-page="newsletter"><span class="nav-icon">✉</span> Newsletter Manager</div>
            <div class="nav-item" onclick="navigate('email-queue')" data-page="email-queue"><span class="nav-icon">📬</span> Email Queue</div>
          </div>
        </div>
        <div class="topnav-group" id="group-system">
          <button class="topnav-group-btn" onclick="toggleMenu(event,'system')">System <span class="caret">▾</span></button>
          <div class="topnav-dropdown">
            <div class="nav-item" onclick="navigate('settings')" data-page="settings"><span class="nav-icon">⚙</span> Settings</div>
          </div>
        </div>
      </nav>
    </div>
    <div class="topnav-right">
      <span class="topnav-page" id="header-title">Dashboard</span>
      <div class="status-pill">
        <span class="status-dot"></span>
        <span id="status-subs">—</span> subscribers
      </div>
      <button class="signout-btn" onclick="signOut()">
        <span style="font-size:15px">↩</span> Sign Out
      </button>
    </div>
  </header>

  <!-- Main content -->
  <main class="main-content">

    <!-- ── WEEKLY DISTRIBUTION ── -->
    <div id="page-weekly-distribution" class="page">
      <div class="page-header">
        <h1>📢 Weekly Distribution</h1>
        <p>Generate ready-to-post social content for the week, then copy &amp; paste it everywhere. Nothing posts automatically.</p>
      </div>
      <div class="status-bar" id="wd-status"></div>

      <div class="card" style="margin-bottom:20px">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:6px">
          <div>
            <h2 style="margin:0">Weekly Posts</h2>
            <p style="margin:4px 0 0;color:var(--muted);font-size:14px">Sunday reflection · Wednesday apologetics · Friday video promo · image prompt.</p>
          </div>
          <button class="btn btn-primary" id="wd-gen-btn" onclick="genWeeklyPosts()">Generate Weekly Posts</button>
        </div>
        <div id="wd-output" style="margin-top:14px"></div>
      </div>

      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:6px">
          <div>
            <h2 style="margin:0">Facebook Distribution Pack</h2>
            <p style="margin:4px 0 0;color:var(--muted);font-size:14px">A ready post plus the groups you're approved to share into.</p>
          </div>
          <button class="btn btn-secondary" onclick="loadFacebookPack()">Load Facebook Pack</button>
        </div>
        <div id="fb-output" style="margin-top:14px"></div>
      </div>
    </div>

    <!-- ── TRAFFIC ENGINE ── -->
    <div id="page-traffic-engine" class="page">
      <div class="page-header">
        <h1>🎬 Traffic Engine</h1>
        <p>Turn one idea into Shorts, hooks, and cross-platform posts that drive traffic back to YouTube.</p>
      </div>
      <div class="status-bar" id="te-status"></div>

      <div class="card" style="margin-bottom:20px">
        <h2 style="margin:0 0 4px">Generate Shorts</h2>
        <p style="margin:0 0 12px;color:var(--muted);font-size:14px">3-5 vertical-video packages: hook, script, caption, on-screen text, hashtags.</p>
        <input type="text" id="te-shorts-topic" placeholder="Video topic or theme (leave blank to use your latest video)…" style="width:100%;margin-bottom:10px">
        <button class="btn btn-primary" onclick="genShorts()">Generate Shorts</button>
        <div id="te-shorts-out" style="margin-top:14px"></div>
      </div>

      <div class="card" style="margin-bottom:20px">
        <h2 style="margin:0 0 4px">Generate Hooks</h2>
        <p style="margin:0 0 12px;color:var(--muted);font-size:14px">Five scroll-stopping opening lines for a topic.</p>
        <input type="text" id="te-hooks-topic" placeholder="Topic (e.g. the Eucharist, the Papacy)…" style="width:100%;margin-bottom:10px">
        <button class="btn btn-primary" onclick="genHooks()">Generate Hooks</button>
        <div id="te-hooks-out" style="margin-top:14px"></div>
      </div>

      <div class="card" style="margin-bottom:20px">
        <h2 style="margin:0 0 4px">Repurpose Content</h2>
        <p style="margin:0 0 12px;color:var(--muted);font-size:14px">One topic or script → Shorts + Facebook + TikTok + YouTube description + email teaser.</p>
        <textarea id="te-repurpose-input" rows="4" placeholder="Paste a topic or full script to repurpose…" style="width:100%;margin-bottom:10px"></textarea>
        <button class="btn btn-primary" onclick="genRepurpose()">Repurpose</button>
        <div id="te-repurpose-out" style="margin-top:14px"></div>
      </div>

      <div class="card">
        <h2 style="margin:0 0 4px">Weekly Posting Plan</h2>
        <p style="margin:0 0 12px;color:var(--muted);font-size:14px">A simple rhythm to keep traffic flowing all week.</p>
        <div id="te-plan-out"></div>
      </div>
    </div>

    <!-- ── ANALYTICS ── -->
    <div id="page-analytics" class="page">
      <div class="page-header" style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
        <div>
          <h1>Analytics</h1>
          <p>Funnel behavior, headline performance, and topic engagement.</p>
        </div>
        <div class="btn-row">
          <select id="an-range" onchange="loadAnalytics()" style="background:#111;color:#eee;border:1px solid #333;border-radius:8px;padding:8px 10px;font-size:13px">
            <option value="">All time</option>
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
          </select>
          <button class="btn btn-secondary btn-sm" onclick="loadAnalytics()">Refresh</button>
        </div>
      </div>

      <div class="status-bar" id="an-status"></div>

      <div class="grid-4" style="margin-bottom:24px">
        <div class="stat-card">
          <div class="stat-icon">👁</div>
          <div class="stat-label">Page Visits</div>
          <div class="stat-value" id="an-visits">—</div>
          <div class="stat-sub">Landing page views</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">👆</div>
          <div class="stat-label">CTA Clicks</div>
          <div class="stat-value" id="an-clicks">—</div>
          <div class="stat-sub">Hero / mid / final buttons</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">✅</div>
          <div class="stat-label">Signups</div>
          <div class="stat-value" id="an-signups">—</div>
          <div class="stat-sub">New subscribers</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📈</div>
          <div class="stat-label">Conversion Rate</div>
          <div class="stat-value" id="an-conv">—</div>
          <div class="stat-sub">Signups ÷ visits</div>
        </div>
      </div>

      <div class="grid-2" style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:24px">
        <div class="card">
          <div class="card-header">
            <div class="card-header-left"><span>📰</span><span class="card-title">Headline Performance</span></div>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Headline</th><th style="text-align:right">Views</th></tr></thead>
              <tbody id="an-headlines"><tr class="empty-row"><td colspan="2">Loading…</td></tr></tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <div class="card-header">
            <div class="card-header-left"><span>🗳️</span><span class="card-title">Top Topics (by signups)</span></div>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Topic</th><th style="text-align:right">Signups</th></tr></thead>
              <tbody id="an-topics"><tr class="empty-row"><td colspan="2">Loading…</td></tr></tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>📜</span><span class="card-title">Scroll Depth</span></div>
        </div>
        <div class="card-body" id="an-scroll">
          <div style="color:#8a8a8a;font-size:14px">Loading…</div>
        </div>
      </div>
    </div>

    <!-- ── DASHBOARD ── -->
    <div id="page-dashboard" class="page active">
      <div class="page-header">
        <h1>Dashboard</h1>
        <p>Overview of your ministry's performance and recent activity.</p>
      </div>

      <!-- Stat cards -->
      <div class="grid-4" style="margin-bottom:24px">
        <div class="stat-card">
          <div class="stat-icon">👥</div>
          <div class="stat-label">Total Subscribers</div>
          <div class="stat-value" id="d-subs">—</div>
          <div class="stat-sub">Active mailing list</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📅</div>
          <div class="stat-label">Send Today?</div>
          <div class="stat-value" id="d-today" style="font-size:20px;padding-top:5px">—</div>
          <div class="stat-sub" id="d-next">Next: —</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">✉</div>
          <div class="stat-label">Last Newsletter</div>
          <div class="stat-value" id="d-last-date" style="font-size:18px;padding-top:4px">—</div>
          <div class="stat-sub" id="d-last-subject" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px">—</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📊</div>
          <div class="stat-label">Last Delivery</div>
          <div class="stat-value" id="d-last-sent" style="font-size:22px;padding-top:3px">—</div>
          <div class="stat-sub" id="d-last-failed">—</div>
        </div>
      </div>

      <!-- Quick compose -->
      <div class="card">
        <div class="card-header">
          <div class="card-header-left">
            <span>✉</span>
            <span class="card-title">Quick Send Newsletter</span>
          </div>
          <div class="btn-row">
            <button class="btn btn-secondary btn-sm" onclick="navigate('newsletter')">Full Editor →</button>
          </div>
        </div>
        <div class="card-body">
          <div class="field">
            <label>Subject Line</label>
            <input id="d-subject" type="text" placeholder="Your email subject…">
          </div>
          <div class="field">
            <label>Body</label>
            <textarea id="d-body" placeholder="Write your newsletter here…&#10;&#10;Each paragraph on its own line." style="min-height:100px"></textarea>
          </div>
          <div class="btn-row">
            <button class="btn btn-secondary" onclick="dashPreview()">Preview</button>
            <button id="d-send-btn" class="btn btn-primary" onclick="dashSend()">
              Send to All Subscribers
            </button>
          </div>
          <div class="status-bar" id="d-send-status"></div>
        </div>
      </div>

      <!-- Recent history -->
      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>📋</span><span class="card-title">Recent Send History</span></div>
          <button class="btn btn-secondary btn-sm" onclick="loadDashboard()">Refresh</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th><th>Subject</th><th>Sent</th><th>Status</th><th>Trigger</th>
              </tr>
            </thead>
            <tbody id="d-history-body">
              <tr class="empty-row"><td colspan="5">Loading…</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── YOUTUBE INTELLIGENCE ── -->
    <div id="page-youtube" class="page">
      <div class="page-header" style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
        <div>
          <h1>YouTube Intelligence</h1>
          <p>Channel performance analysis, keyword patterns, and AI-powered content strategy.</p>
        </div>
        <button class="btn btn-primary" onclick="loadYoutube(true)">
          <span>↻</span> Refresh Analysis
        </button>
      </div>

      <div id="yt-content">
        <div class="loader-overlay">
          <div class="loader-spinner"></div>
          <span>Loading YouTube intelligence…</span>
        </div>
      </div>
    </div>

    <!-- ── NEWSLETTER MANAGER ── -->
    <div id="page-newsletter" class="page">
      <div class="page-header">
        <h1>Newsletter Manager</h1>
        <p>Compose, preview, and send newsletters to all active subscribers.</p>
      </div>

      <div class="grid-2">
        <!-- Compose -->
        <div class="card" style="margin-bottom:0">
          <div class="card-header">
            <div class="card-header-left"><span>✍</span><span class="card-title">Compose</span></div>
          </div>
          <div class="card-body">
            <div class="field">
              <label>Subject Line</label>
              <input id="nl-subject" type="text" placeholder="Your email subject…">
            </div>
            <div class="field">
              <label>Body</label>
              <textarea id="nl-body" placeholder="Write your newsletter here…&#10;&#10;Each paragraph on its own line." style="min-height:200px"></textarea>
              <p class="field-hint">Each line break becomes a new paragraph. Plain text only — no HTML needed.</p>
            </div>
            <div class="btn-row">
              <button class="btn btn-secondary" onclick="previewNewsletter()">Preview Email</button>
              <button id="nl-weekly-btn" class="btn btn-secondary" onclick="generateWeeklyEmail()">✨ Weekly Plan</button>
              <button id="nl-send-btn" class="btn btn-primary" onclick="sendNewsletter()">
                Send to All
              </button>
            </div>
            <div class="status-bar" id="nl-send-status"></div>
          </div>
        </div>

        <!-- Auto-send info -->
        <div style="display:flex;flex-direction:column;gap:16px">
          <div class="card" style="margin-bottom:0">
            <div class="card-header">
              <div class="card-header-left"><span>📅</span><span class="card-title">Auto-Send Schedule</span></div>
            </div>
            <div class="card-body">
              <p style="font-size:13px;color:var(--muted);margin-bottom:12px">
                The scheduler automatically sends newsletters on:
              </p>
              <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px">
                <span class="badge badge-yellow">Sunday</span>
                <span class="badge badge-yellow">Wednesday</span>
                <span class="badge badge-yellow">Friday</span>
              </div>
              <p style="font-size:12px;color:var(--muted)">All sends fire at <strong style="color:var(--text)">09:00 UTC</strong>. Auto-send uses GPT-4o to generate content. Use this form for manual or custom sends.</p>
              <div style="margin-top:16px;padding:12px;background:var(--bg);border-radius:8px;border:1px solid var(--border)">
                <div style="font-size:12px;color:var(--muted);margin-bottom:4px">Next send day</div>
                <div style="font-size:20px;font-weight:700;color:var(--gold)" id="nl-next-day">—</div>
              </div>
            </div>
          </div>
          <div class="card" style="margin-bottom:0">
            <div class="card-header">
              <div class="card-header-left"><span>ℹ</span><span class="card-title">Delivery Stats</span></div>
            </div>
            <div class="card-body">
              <div style="display:flex;gap:20px">
                <div>
                  <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Subscribers</div>
                  <div style="font-size:28px;font-weight:700;color:var(--text)" id="nl-subs">—</div>
                </div>
                <div>
                  <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Send Today</div>
                  <div style="font-size:28px;font-weight:700" id="nl-today">—</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- History -->
      <div class="card" style="margin-top:20px">
        <div class="card-header">
          <div class="card-header-left"><span>📋</span><span class="card-title">Send History</span></div>
          <button class="btn btn-secondary btn-sm" onclick="loadHistory()">Refresh</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date &amp; Time</th><th>Subject</th><th>Sent</th><th>Failed</th><th>Triggered By</th>
              </tr>
            </thead>
            <tbody id="history-body">
              <tr class="empty-row"><td colspan="5">Loading…</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── SUBSCRIBERS ── -->
    <div id="page-subscribers" class="page">
      <div class="page-header" style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
        <div>
          <h1>Subscribers</h1>
          <p>Manage your active mailing list.</p>
        </div>
        <div class="btn-row">
          <button class="btn btn-secondary" onclick="exportCSV()">⬇ Export CSV</button>
          <button class="btn btn-secondary" onclick="loadSubscribers()">↻ Refresh</button>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>➕</span><span class="card-title">Add Subscriber</span></div>
          <div id="sub-count-pill" class="status-pill">
            <span class="status-dot"></span>
            <span id="sub-count-display">—</span> active
          </div>
        </div>
        <div class="card-body" style="padding-bottom:0">
          <div class="add-row">
            <input id="add-sub-input" type="email" placeholder="name@example.com"
                   onkeydown="if(event.key==='Enter') addSubscriber()">
            <button class="btn btn-primary" onclick="addSubscriber()">Add</button>
          </div>
          <div id="add-sub-msg" style="font-size:13px;min-height:20px;margin-bottom:12px;padding:4px 0"></div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>Email Address</th><th style="text-align:right">Action</th></tr>
            </thead>
            <tbody id="sub-table-body">
              <tr class="empty-row"><td colspan="2">Loading…</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── CONTENT IDEAS ── -->
    <div id="page-ideas" class="page">
      <div class="page-header">
        <h1>Content Ideas</h1>
        <p>Generate viral titles, hooks, and short scripts powered by GPT-4o.</p>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>💡</span><span class="card-title">Generate Content Idea</span></div>
        </div>
        <div class="card-body">
          <div class="field">
            <label>Topic</label>
            <input id="idea-topic" type="text" placeholder="e.g. Why Catholics pray to saints, The truth about purgatory…"
                   onkeydown="if(event.key==='Enter') generateIdea()">
            <p class="field-hint">Enter any Catholic topic and AI will generate a viral title, attention hook, and short video script.</p>
          </div>
          <button id="idea-btn" class="btn btn-primary" onclick="generateIdea()">
            Generate Idea
          </button>
          <div class="status-bar" id="idea-status"></div>
        </div>
      </div>

      <div class="idea-result" id="idea-result">
        <div class="idea-result-title" id="idea-viral-title"></div>
        <div class="idea-result-section">
          <h4>Hook</h4>
          <p id="idea-hook"></p>
        </div>
        <div class="idea-result-section">
          <h4>Short Script</h4>
          <p id="idea-script" style="white-space:pre-wrap"></p>
        </div>
        <div style="margin-top:16px">
          <button class="btn btn-secondary btn-sm" onclick="generateIdea()">↻ Regenerate</button>
          <button class="btn btn-secondary btn-sm" style="margin-left:8px" onclick="copyIdea()">Copy Script</button>
        </div>
      </div>
    </div>

    <!-- ── AUDIENCE TOPICS ── -->
    <div id="page-topics" class="page">
      <div class="page-header" style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
        <div>
          <h1>Audience Topics</h1>
          <p>Review visitor requests and curate what appears on the public page.</p>
        </div>
        <div class="btn-row">
          <button class="btn btn-secondary" onclick="loadAdminTopics()">↻ Refresh</button>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>➕</span><span class="card-title">Add a Topic</span></div>
        </div>
        <div class="card-body" style="padding-bottom:16px">
          <div class="field">
            <label>Title</label>
            <input id="topic-add-title" type="text" placeholder="e.g. The truth about the Eucharist" maxlength="200">
          </div>
          <div class="field">
            <label>Description <span style="color:var(--muted);font-weight:400">(optional)</span></label>
            <input id="topic-add-desc" type="text" placeholder="One line shown under the title" maxlength="500">
          </div>
          <div class="field">
            <label>Status</label>
            <select id="topic-add-status">
              <option value="approved">Approved (shown publicly)</option>
              <option value="featured">Featured (top of list)</option>
              <option value="suggested">Suggested (hidden, pending)</option>
            </select>
          </div>
          <button class="btn btn-primary" onclick="createAdminTopic()">Add Topic</button>
          <div class="status-bar" id="topic-add-status-bar"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🗳️</span><span class="card-title">All Topics</span></div>
          <div id="topic-count-pill" class="status-pill">
            <span class="status-dot"></span>
            <span id="topic-count-display">—</span> total
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Topic</th>
                <th style="text-align:center">Votes</th>
                <th style="text-align:center">Status</th>
                <th style="text-align:right">Actions</th>
              </tr>
            </thead>
            <tbody id="topic-table-body">
              <tr class="empty-row"><td colspan="4">Loading…</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── CONTENT HUB ── -->
    <div id="page-content-hub" class="page">
      <div class="page-header" style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
        <div>
          <h1>Content Hub</h1>
          <p>Curate the landing page's featured Shorts, playlists &amp; community link — and check Catholic news.</p>
        </div>
        <div class="btn-row">
          <button class="btn btn-secondary" onclick="loadFeaturedAdmin()">↻ Reload</button>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🎬</span><span class="card-title">Featured Content</span></div>
        </div>
        <div class="card-body">
          <div class="field">
            <label>Shorts <span style="color:var(--muted);font-weight:400">(one per line: <code>VIDEO_ID | Title</code>)</span></label>
            <textarea id="fc-shorts" rows="5" placeholder="Bm2aoEcEIPk | The truth about Salvation"></textarea>
          </div>
          <div class="field">
            <label>Playlists <span style="color:var(--muted);font-weight:400">(one per line: <code>Title | https://youtube.com/playlist?list=…</code>)</span></label>
            <textarea id="fc-playlists" rows="4" placeholder="Apologetics 101 | https://www.youtube.com/playlist?list=..."></textarea>
          </div>
          <div class="field">
            <label>Community link <span style="color:var(--muted);font-weight:400">(optional)</span></label>
            <input id="fc-community" type="text" placeholder="https://www.youtube.com/@odilitheseekeroftruth/community">
          </div>
          <button class="btn btn-primary" onclick="saveFeaturedAdmin()">Save Featured Content</button>
          <div class="status-bar" id="fc-status-bar"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>📰</span><span class="card-title">Catholic News</span></div>
          <button class="btn btn-secondary btn-sm" onclick="refreshNews()">↻ Refresh cache</button>
        </div>
        <div class="card-body">
          <p style="color:var(--muted);font-size:13px;margin-bottom:12px">Supportive headlines from Vatican News &amp; CNA (cached 30 min). Used to inform content ideas — never as doctrinal authority.</p>
          <div id="news-list"><div class="empty-row">Loading…</div></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>📚</span><span class="card-title">Playlist Resources</span></div>
        </div>
        <div class="card-body">
          <p style="color:var(--muted);font-size:13px;margin-bottom:12px">The authority knowledge base behind the public <a href="/resources" target="_blank" rel="noopener" style="color:var(--gold)">/resources</a> page: trusted sources organized into four sections. Every card shows the insight first, then the YouTube teaching — authority before the ask.</p>
          <div class="form-row">
            <input id="pr-title" class="input" placeholder="Title (e.g. Liber Pontificalis)">
            <select id="pr-category" class="input"></select>
            <select id="pr-source-type" class="input"></select>
          </div>
          <div class="form-row">
            <input id="pr-source-name" class="input" placeholder="Source name (e.g. Eusebius, Historia Ecclesiastica)">
          </div>
          <textarea id="pr-description" class="input" rows="2" placeholder="Short description — what this source is"></textarea>
          <textarea id="pr-relevance" class="input" rows="2" placeholder="Why it matters — the insight shown before the video CTA"></textarea>
          <div class="form-row">
            <input id="pr-link" class="input" placeholder="Source link (optional, https://…)">
            <input id="pr-video" class="input" placeholder="YouTube teaching link (optional, https://…)">
          </div>
          <div id="pr-tags" style="margin:8px 0"></div>
          <button class="btn btn-primary" id="pr-submit-btn" onclick="prCreate()">Add Resource</button>
          <div class="status-bar" id="pr-status-bar"></div>
          <div style="margin-top:16px">
            <div id="pr-list"><div class="empty-row">Loading…</div></div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── EMAIL QUEUE ── -->
    <div id="page-email-queue" class="page">
      <div class="page-header" style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
        <div>
          <h1>Email Queue</h1>
          <p>Every broadcast email lands here as a draft first — review, edit, then approve to send or schedule. Nothing sends without your approval.</p>
        </div>
        <div class="btn-row">
          <button class="btn btn-secondary" onclick="eqLoad()">↻ Refresh</button>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>📬</span><span class="card-title">Queue</span></div>
          <div class="status-pill"><span class="status-dot"></span><span id="eq-count">—</span> items</div>
        </div>
        <div class="card-body">
          <div class="status-bar" id="eq-status-bar"></div>
          <div id="eq-list"><div class="empty-row">Loading…</div></div>
        </div>
      </div>
    </div>

    <!-- ── CONTENT PLAN ── -->
    <div id="page-content-plan" class="page">
      <div class="page-header" style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
        <div>
          <h1>Content Plan</h1>
          <p>Audience demand → your next videos. Ranked by votes, recent surges, subscriber interests &amp; email clicks.</p>
        </div>
        <div class="btn-row">
          <button class="btn btn-secondary" onclick="cpLoad()">↻ Refresh</button>
        </div>
      </div>

      <div id="cp-alerts"></div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🧭</span><span class="card-title">Make These Next</span></div>
        </div>
        <div class="card-body">
          <div class="status-bar" id="cp-status-bar"></div>
          <div id="cp-list"><div class="empty-row">Loading…</div></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🔗</span><span class="card-title">YouTube → Landing CTA Pack</span></div>
          <button class="btn btn-secondary btn-sm" onclick="cpLoadCtas()">Generate</button>
        </div>
        <div class="card-body">
          <p style="color:var(--muted);font-size:13px;margin-bottom:12px">Paste-ready description block, pinned comment &amp; end-screen script. Every link carries <code>?src=youtube</code> so signups are attributed to YouTube.</p>
          <div class="field">
            <label>Video title <span style="color:var(--muted);font-weight:400">(optional — personalizes the description)</span></label>
            <input id="cp-cta-title" type="text" placeholder="e.g. The Truth About the Eucharist" maxlength="200">
          </div>
          <div id="cp-cta-out"></div>
        </div>
      </div>
    </div>

    <!-- ── VIDEO GRID MANAGER ── -->
    <div id="page-video-grid" class="page">
      <div class="page-header" style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
        <div>
          <h1>Video Grid Manager</h1>
          <p>Curate the landing page "Start Exploring the Truth" grid. Add videos to any of the 6 categories — the public grid shows 3 per category and rotates weekly.</p>
        </div>
        <div class="btn-row">
          <button class="btn btn-secondary" onclick="vgLoad()">↻ Refresh</button>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>➕</span><span class="card-title">Add a Video</span></div>
        </div>
        <div class="card-body">
          <div class="status-bar" id="vg-status-bar"></div>
          <div class="field">
            <label>Category</label>
            <select id="vg-category"></select>
          </div>
          <div class="field">
            <label>Title</label>
            <input id="vg-title" type="text" placeholder="e.g. What the Early Church Believed About the Eucharist" maxlength="200">
          </div>
          <div class="field">
            <label>YouTube URL</label>
            <input id="vg-url" type="text" placeholder="https://www.youtube.com/watch?v=..." maxlength="500">
          </div>
          <button class="btn btn-primary" onclick="vgAdd()">Add Video</button>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🔁</span><span class="card-title">Weekly Rotation</span></div>
        </div>
        <div class="card-body">
          <p style="color:var(--muted);font-size:13px;margin-bottom:12px">When enabled, each category cycles through its video pool weekly so returning visitors see fresh teachings.</p>
          <label style="display:flex;align-items:center;gap:10px;cursor:pointer">
            <input type="checkbox" id="vg-rotation-enabled" onchange="vgSaveRotation()">
            <span>Enable weekly rotation</span>
          </label>
          <div id="vg-rotation-info" style="color:var(--muted);font-size:12px;margin-top:8px"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🎞️</span><span class="card-title">Video Pool</span></div>
          <div class="status-pill"><span class="status-dot"></span><span id="vg-count">—</span> videos</div>
        </div>
        <div class="card-body">
          <div id="vg-list"><div class="empty-row">Loading…</div></div>
        </div>
      </div>
    </div>

    <!-- ── SEO ENGINE ── -->
    <div id="page-seo-engine" class="page">
      <div class="page-header">
        <h1>SEO Engine</h1>
        <p>Generate search-optimized keywords, YouTube metadata, and full blog teachings — deterministic first, AI-enriched when available. Articles publish to <code>/truth/{slug}</code>.</p>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🔑</span><span class="card-title">Keyword &amp; Metadata Generator</span></div>
        </div>
        <div class="card-body">
          <div class="status-bar" id="seo-status-bar"></div>
          <div class="field">
            <label>Topic</label>
            <input id="seo-topic" type="text" placeholder="e.g. purgatory, the papacy, the Eucharist" maxlength="200">
          </div>
          <div class="btn-row">
            <button class="btn btn-secondary" onclick="seoKeywords()">Generate Keywords</button>
            <button class="btn btn-secondary" onclick="seoVideo()">YouTube Metadata</button>
          </div>
          <div id="seo-kw-out" style="margin-top:14px"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>📝</span><span class="card-title">Write a Blog Teaching</span></div>
        </div>
        <div class="card-body">
          <div class="field">
            <label>Topic</label>
            <input id="seo-art-topic" type="text" placeholder="e.g. What the Church Fathers taught about Mary" maxlength="200">
          </div>
          <div class="field">
            <label>Linked video URL <span style="color:var(--muted);font-weight:400">(optional — cross-links the article to YouTube)</span></label>
            <input id="seo-art-video" type="text" placeholder="https://www.youtube.com/watch?v=..." maxlength="500">
          </div>
          <button class="btn btn-primary" onclick="seoArticle()">Generate &amp; Publish</button>
          <div id="seo-art-out" style="margin-top:14px"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🗳️</span><span class="card-title">Content Ideas from Votes</span></div>
          <button class="btn btn-secondary btn-sm" onclick="seoVotes()">Refresh</button>
        </div>
        <div class="card-body">
          <p style="color:var(--muted);font-size:13px;margin-bottom:12px">Top-voted audience topics, ready to turn into keywords and teachings.</p>
          <div id="seo-votes-out"><div class="empty-row">Click Refresh to load.</div></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>📚</span><span class="card-title">Published Teachings</span></div>
          <div class="status-pill"><span class="status-dot"></span><span id="seo-art-count">—</span> articles</div>
        </div>
        <div class="card-body">
          <div id="seo-articles"><div class="empty-row">Loading…</div></div>
        </div>
      </div>
    </div>

    <!-- ── LEAD DISCOVERY ── -->
    <div id="page-lead-discovery" class="page">
      <div class="page-header">
        <h1>🔎 Lead Discovery</h1>
        <p>Find real seekers asking faith questions in the <strong>public comments</strong> of channels you watch. Every lead is reviewed by you — nothing is ever auto-replied or posted to YouTube. Approving a lead creates an Audience Topic, a Content Idea, an email draft, and an AI content pack.</p>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>📊</span><span class="card-title">Engine Status</span></div>
          <button class="btn btn-primary btn-sm" onclick="ldScan()">🔄 Scan now</button>
        </div>
        <div class="card-body">
          <div class="status-bar" id="ld-status-bar"></div>
          <div id="ld-status"><div class="empty-row">Loading…</div></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>📺</span><span class="card-title">Watched Channels</span></div>
        </div>
        <div class="card-body">
          <div class="field">
            <label>Channel URL, @handle, or channel ID</label>
            <input id="ld-ch-url" type="text" placeholder="https://www.youtube.com/@handle  ·  @handle  ·  UC..." maxlength="500">
          </div>
          <div class="field">
            <label>Category <span style="color:var(--muted);font-weight:400">(groups leads by theme)</span></label>
            <input id="ld-ch-cat" type="text" placeholder="e.g. apologetics, conversion, prayer" maxlength="60" value="general">
          </div>
          <button class="btn btn-primary" onclick="ldAddChannel()">+ Watch channel</button>
          <div id="ld-channels" style="margin-top:16px"><div class="empty-row">No channels watched yet.</div></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🌱</span><span class="card-title">Leads to Review</span></div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <select id="ld-channel" onchange="ldChannelChanged()" style="max-width:200px">
              <option value="">All channels</option>
            </select>
            <select id="ld-category" onchange="ldCategoryChanged()" style="max-width:180px">
              <option value="">All categories</option>
            </select>
            <select id="ld-filter" onchange="ldLoadLeads()" style="max-width:170px">
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="skipped">Skipped</option>
              <option value="all">All</option>
            </select>
            <select id="ld-sort" onchange="ldLoadLeads()" style="max-width:190px">
              <option value="intent">🔥 Highest intent first</option>
              <option value="newest">🕒 Newest first</option>
            </select>
            <button class="btn btn-secondary btn-sm" onclick="ldLoadLeads()">Refresh</button>
          </div>
        </div>
        <div class="card-body">
          <p style="color:var(--muted);font-size:13px;margin-bottom:12px">High-intent seeker comments (score &ge; 0.6). Open goes straight to the comment on YouTube so you can reply as a human.</p>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:14px">
            <span style="font-size:13px;color:var(--muted)">Clear the tail:</span>
            <span style="font-size:13px;color:var(--muted)">under</span>
            <input type="range" id="ld-bulk-threshold-slider" min="0" max="100" step="1" value="65" style="width:140px;vertical-align:middle" oninput="ldThresholdInput('slider')">
            <input type="number" id="ld-bulk-threshold" min="0" max="100" step="1" value="65" style="width:64px" oninput="ldThresholdInput('number')">
            <span style="font-size:13px;color:var(--muted)">%</span>
            <button class="btn btn-secondary btn-sm" onclick="ldBulkSkip(this)" style="color:#e57373">🧹 Skip all under threshold</button>
            <span id="ld-bulk-count" style="font-size:12px;color:var(--muted)"></span>
            <button id="ld-undo-bulk-skip" class="btn btn-secondary btn-sm" onclick="ldUndoBulkSkip(this)" style="display:none">↩️ Undo bulk-skip</button>
          </div>
          <div id="ld-bulk-near-miss" style="display:none;margin:-4px 0 14px;padding:8px 12px;border:1px solid var(--border);border-radius:8px;background:rgba(212,175,55,.05);font-size:12px;color:var(--muted)"></div>
          <div id="ld-leads"><div class="empty-row">Loading…</div></div>
        </div>
      </div>
    </div>

    <!-- ── REPLY ENGINE ── -->
    <div id="page-reply-engine" class="page">
      <div class="page-header">
        <h1>💬 Reply Engine</h1>
        <p>Generates <strong>human-like reply suggestions</strong> for YouTube lead comments — 3 tones, intent-aware CTAs, and reply-timing advice. Nothing is ever posted automatically: copy a reply, tweak a word or two, and post it yourself on YouTube.</p>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>✍️</span><span class="card-title">Any Comment</span></div>
        </div>
        <div class="card-body">
          <div class="status-bar" id="re-status-bar"></div>
          <div class="field"><label>Comment text</label><textarea id="re-comment" rows="3" placeholder="Paste a YouTube comment…"></textarea></div>
          <div class="field-row">
            <div class="field" style="flex:1"><label>Video title (optional)</label><input id="re-video" placeholder="Video the comment was left on"></div>
            <div class="field" style="flex:1"><label>Channel (optional)</label><input id="re-channel" placeholder="Channel name"></div>
          </div>
          <button class="btn btn-primary" onclick="reGenerateRaw()">⚡ Generate Replies</button>
          <div id="re-raw-result" style="margin-top:14px"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🔎</span><span class="card-title">Discovered Leads</span></div>
          <div style="display:flex;gap:8px;align-items:center">
            <select id="re-filter" onchange="reRenderLeads()" style="max-width:170px">
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="all">All</option>
            </select>
            <button class="btn btn-secondary btn-sm" onclick="reLoad()">Refresh</button>
          </div>
        </div>
        <div class="card-body">
          <p style="color:var(--muted);font-size:13px;margin-bottom:12px">Comment, video, intent type and score for each lead — generate a tailored reply pack per lead.</p>
          <div id="re-leads"><div class="empty-row">Loading…</div></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🧵</span><span class="card-title">Conversation Continuation</span></div>
        </div>
        <div class="card-body">
          <p style="color:var(--muted);font-size:13px;margin-bottom:12px">Someone replied to you? Paste the whole thread (oldest first) and get follow-up suggestions.</p>
          <div class="field"><textarea id="re-thread" rows="4" placeholder="Me: …&#10;Them: …"></textarea></div>
          <button class="btn btn-primary" onclick="reContinue()">🧵 Suggest Follow-ups</button>
          <div id="re-thread-result" style="margin-top:14px"></div>
        </div>
      </div>
    </div>

    <!-- ── CONVERSION ENGINE ── -->
    <div id="page-conversion-engine" class="page">
      <div class="page-header">
        <h1>⚡ Conversion Engine</h1>
        <p>Psychology-driven copy for every step of the funnel: CTR titles/hooks/CTAs, conversion emails, landing copy and US-audience optimization. Generation-only — nothing sends or publishes automatically.</p>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🎯</span><span class="card-title">Generators</span></div>
        </div>
        <div class="card-body">
          <div class="status-bar" id="ce-status-bar"></div>
          <div class="field"><label>Topic</label><input id="ce-topic" placeholder="e.g. The Eucharist in the early Church"></div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn btn-primary btn-sm" onclick="ceRun('ctr')">🔥 CTR Phrases</button>
            <button class="btn btn-primary btn-sm" onclick="ceRun('email')">✉️ Email Converter</button>
            <button class="btn btn-primary btn-sm" onclick="ceRun('landing')">🖥️ Landing CTA</button>
            <button class="btn btn-primary btn-sm" onclick="ceRun('us')">🇺🇸 US Optimize</button>
          </div>
          <div id="ce-result" style="margin-top:14px"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>📈</span><span class="card-title">Phrase Performance</span></div>
          <button class="btn btn-secondary btn-sm" onclick="ceLoadPerf()">Refresh</button>
        </div>
        <div class="card-body">
          <p style="color:var(--muted);font-size:13px;margin-bottom:12px">Phrases you saved as "in use", with clicks and conversions you log against them.</p>
          <div id="ce-perf"><div class="empty-row">No saved phrases yet — generate CTR phrases and hit Save on the ones you use.</div></div>
        </div>
      </div>
    </div>

    <!-- ── GROWTH PACK ── -->
    <div id="page-growth-pack" class="page">
      <div class="page-header">
        <h1>🧠 Growth Pack</h1>
        <p>One command for high-conversion growth: rank titles by predicted click-through, pull viral hooks, US keywords, conversion scripts and trigger phrases — all from one topic. Deterministic-first: it keeps working even when AI is offline, and never sends or publishes anything.</p>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🎯</span><span class="card-title">Title CTR Scorer</span></div>
        </div>
        <div class="card-body">
          <div class="status-bar" id="gp-score-status-bar"></div>
          <div class="field"><label>Paste one or more titles (one per line)</label><textarea id="gp-titles" rows="3" placeholder="Is Purgatory Actually Biblical? (What the Early Church Said)"></textarea></div>
          <button class="btn btn-primary btn-sm" onclick="gpScore()">Score & Rank</button>
          <div id="gp-score-result" style="margin-top:14px"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🧠</span><span class="card-title">Full Growth Pack</span></div>
        </div>
        <div class="card-body">
          <div class="status-bar" id="gp-status-bar"></div>
          <div class="field"><label>Topic</label><input id="gp-topic" placeholder="e.g. Why Catholics pray to Mary"></div>
          <label style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted);margin-bottom:10px">
            <input type="checkbox" id="gp-draft" style="width:auto"> Also queue a Newsletter draft (draft only — never sends)
          </label>
          <button class="btn btn-primary btn-sm" onclick="gpBrain()">Build Growth Pack</button>
          <div id="gp-result" style="margin-top:14px"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>⚡</span><span class="card-title">Click Trigger Phrases</span></div>
          <button class="btn btn-secondary btn-sm" onclick="gpTriggers()">Refresh</button>
        </div>
        <div class="card-body">
          <p style="color:var(--muted);font-size:13px;margin-bottom:12px">A curated library of proven high-CTR patterns. Fill in the topic above and refresh to personalize them.</p>
          <div id="gp-triggers"><div class="empty-row">Loading…</div></div>
        </div>
      </div>
    </div>

    <!-- ── AUDIENCE GEOGRAPHY ── -->
    <div id="page-audience-geo" class="page">
      <div class="page-header">
        <h1>🌎 Audience Geography</h1>
        <p>Where landing-page visitors come from — privacy-safe: only coarse country/region is ever stored, never IP addresses.</p>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>📊</span><span class="card-title">Summary</span></div>
          <div style="display:flex;gap:8px;align-items:center">
            <select id="geo-days" onchange="geoLoad()" style="max-width:150px">
              <option value="7">Last 7 days</option>
              <option value="30" selected>Last 30 days</option>
              <option value="90">Last 90 days</option>
            </select>
            <button class="btn btn-secondary btn-sm" onclick="geoLoad()">Refresh</button>
          </div>
        </div>
        <div class="card-body">
          <div class="status-bar" id="geo-status-bar"></div>
          <div id="geo-content"><div class="empty-row">Loading…</div></div>
        </div>
      </div>
    </div>

    <!-- ── LEAD EVANGELIST ── -->
    <div id="page-lead-evangelist" class="page">
      <div class="page-header">
        <h1>🕊️ Lead Evangelist</h1>
        <p>Turn every platform into a lead source — the compliant way. Copy a personalized message, post it yourself as a human, log it here. Nothing auto-posts, pace caps keep you spam-safe, and every link carries attribution so signups trace back to the platform.</p>
      </div>

      <div class="card">
        <div class="card-header"><h2>⏰ Auto-Cadence (every 2 days)</h2></div>
        <div class="card-body">
          <p class="hint">Every 2 days, at your audience's most active hour, the app prepares the next platform's personalized post and emails it to you ready to paste. It never posts for you — that keeps your accounts safe.</p>
          <div id="le-auto-status"><div class="empty-row">Loading…</div></div>
          <button class="btn" id="le-auto-toggle" onclick="leAutoToggle()">Toggle</button>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><h2>✍️ Personalize a Message</h2></div>
        <div class="card-body">
          <div class="form-row">
            <select id="le-platform" class="input"></select>
            <select id="le-msgtype" class="input">
              <option value="">Recommended for platform</option>
              <option value="universal">Universal Marketing Message</option>
              <option value="short_comment">Short Comment</option>
              <option value="high_conversion_comment">High Conversion Comment</option>
              <option value="tiktok_short">TikTok / Short Style</option>
            </select>
          </div>
          <textarea id="le-context" class="input" rows="2" placeholder="Optional: paste the comment/question/thread you're answering — makes the message personal"></textarea>
          <button class="btn btn-primary" onclick="lePersonalize()">Personalize</button>
          <div class="status-bar" id="le-personalize-status"></div>
          <div id="le-personalize-out"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><h2>📖 Message Playbook</h2></div>
        <div class="card-body">
          <div id="le-playbook"><div class="empty-row">Loading…</div></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><h2>📝 Outreach Log</h2></div>
        <div class="card-body">
          <p class="hint">After you post somewhere, log it here so pace tracking and the dashboard stay honest.</p>
          <div class="form-row">
            <select id="le-log-platform" class="input"></select>
            <input id="le-log-target" class="input" placeholder="Where? (video URL, group name, thread link…)" />
          </div>
          <input id="le-log-notes" class="input" placeholder="Notes (optional)" />
          <button class="btn" onclick="leLogOutreach()">Log Outreach</button>
          <div class="status-bar" id="le-log-status"></div>
          <div id="le-outreach-list"><div class="empty-row">Loading…</div></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><h2>📊 Evangelist Dashboard</h2></div>
        <div class="card-body">
          <div id="le-dashboard"><div class="empty-row">Loading…</div></div>
        </div>
      </div>
    </div>

    <!-- ── GROWTH BRAIN ── -->
    <div id="page-growth-brain" class="page">
      <div class="page-header">
        <h1>🚀 Growth Brain</h1>
        <p>Predict a title's click power before you publish, generate viral hooks and US-targeted keywords, and build ranked optimized titles. Deterministic-first — always works, never blocks. Nothing here posts or sends.</p>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🎯</span><span class="card-title">Title Scorer</span></div>
        </div>
        <div class="card-body">
          <div class="status-bar" id="gb-score-bar"></div>
          <div class="field"><label>Title to score</label><input id="gb-title" placeholder="e.g. What Early Christians Actually Believed About the Eucharist"></div>
          <button class="btn btn-primary btn-sm" onclick="gbScore()">🔎 Score Title</button>
          <div id="gb-score-result" style="margin-top:14px"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🧠</span><span class="card-title">Topic Generators</span></div>
        </div>
        <div class="card-body">
          <div class="status-bar" id="gb-gen-bar"></div>
          <div class="field"><label>Topic</label><input id="gb-topic" placeholder="e.g. purgatory, praying to Mary, the papacy"></div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn btn-primary btn-sm" onclick="gbRun('optimized')">🏆 Optimized Titles</button>
            <button class="btn btn-primary btn-sm" onclick="gbRun('hooks')">🪝 Viral Hooks</button>
            <button class="btn btn-primary btn-sm" onclick="gbRun('keywords')">🇺🇸 US Keywords</button>
          </div>
          <div id="gb-gen-result" style="margin-top:14px"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>💥</span><span class="card-title">Click Trigger Phrases</span></div>
          <button class="btn btn-secondary btn-sm" onclick="gbTriggerLibrary()">Proven Library</button>
        </div>
        <div class="card-body">
          <div class="status-bar" id="gb-trig-bar"></div>
          <p style="color:var(--muted);font-size:13px;margin-bottom:10px">Proven high-CTR phrases by trigger type. Load the library, or tailor them to a topic (uses the Topic box above).</p>
          <button class="btn btn-primary btn-sm" onclick="gbTriggerTopic()">🎯 Tailor to Topic</button>
          <div id="gb-trig-result" style="margin-top:14px"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🎙️</span><span class="card-title">Subscriber Conversion Scripts</span></div>
        </div>
        <div class="card-body">
          <div class="status-bar" id="gb-scripts-bar"></div>
          <p style="color:var(--muted);font-size:13px;margin-bottom:10px">Ready-to-paste pinned comment, reply CTAs, subscribe CTAs, and a description block. Uses the Topic box above.</p>
          <div class="field"><label>Video title (optional)</label><input id="gb-video-title" placeholder="e.g. Why Catholics Pray to Mary"></div>
          <button class="btn btn-primary btn-sm" onclick="gbScripts()">🎬 Generate Scripts</button>
          <div id="gb-scripts-result" style="margin-top:14px"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>📈</span><span class="card-title">Title Performance</span></div>
          <button class="btn btn-secondary btn-sm" onclick="gbLoadPerf()">Refresh</button>
        </div>
        <div class="card-body">
          <p style="color:var(--muted);font-size:13px;margin-bottom:12px">Titles you saved to track, with the real clicks and CTR you log against them.</p>
          <div id="gb-perf"><div class="empty-row">No saved titles yet — score or generate titles and hit Save on the ones you use.</div></div>
        </div>
      </div>
    </div>

    <!-- ── SETTINGS ── -->
    <div id="page-settings" class="page">
      <div class="page-header">
        <h1>Settings</h1>
        <p>System configuration and status overview.</p>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>📅</span><span class="card-title">Newsletter Schedule</span></div>
        </div>
        <div class="card-body">
          <div class="setting-row">
            <div class="setting-info">
              <h4>Auto-send Days</h4>
              <p>Newsletters are automatically generated and sent on these days.</p>
            </div>
            <div style="display:flex;gap:8px">
              <span class="badge badge-yellow">Sunday</span>
              <span class="badge badge-yellow">Wednesday</span>
              <span class="badge badge-yellow">Friday</span>
            </div>
          </div>
          <div class="setting-row">
            <div class="setting-info">
              <h4>Send Time</h4>
              <p>All scheduled sends fire at this UTC time.</p>
            </div>
            <span class="badge badge-green">09:00 UTC</span>
          </div>
          <div class="setting-row">
            <div class="setting-info">
              <h4>Scheduler Status</h4>
              <p>Whether the APScheduler background process is running.</p>
            </div>
            <span class="badge" id="sched-status">—</span>
          </div>
          <div class="setting-row">
            <div class="setting-info">
              <h4>Send Today?</h4>
              <p>Whether today is a scheduled send day.</p>
            </div>
            <span id="sched-today">—</span>
          </div>
          <div class="setting-row">
            <div class="setting-info">
              <h4>Next Send Day</h4>
              <p>The next day the auto-scheduler will trigger.</p>
            </div>
            <span id="sched-next" style="color:var(--gold);font-weight:600">—</span>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-header-left"><span>🔑</span><span class="card-title">API Integrations</span></div>
        </div>
        <div class="card-body">
          <div class="setting-row">
            <div class="setting-info">
              <h4>SendGrid</h4>
              <p>Email delivery provider. Configure SENDGRID_API_KEY in environment secrets.</p>
            </div>
          </div>
          <div class="setting-row">
            <div class="setting-info">
              <h4>OpenAI GPT-4o</h4>
              <p>Powers auto-send newsletters and content idea generation. Configure OPENAI_API_KEY.</p>
            </div>
          </div>
          <div class="setting-row">
            <div class="setting-info">
              <h4>YouTube Data API v3</h4>
              <p>Required for YouTube Intelligence. Configure YOUTUBE_API_KEY + YOUTUBE_CHANNEL_ID.</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── SAVED SCRIPTS ── -->
    <div id="page-saved-scripts" class="page">
      <div class="page-header" style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
        <div>
          <h1>Saved Scripts</h1>
          <p>AI-generated scripts saved for later use.</p>
        </div>
        <button class="btn btn-secondary" onclick="loadSavedScripts()">↻ Refresh</button>
      </div>
      <div id="saved-scripts-list">
        <div class="loader-overlay">
          <div class="loader-spinner"></div>
          <span>Loading saved scripts…</span>
        </div>
      </div>
    </div>

    <!-- ── GROWTH ENGINE ── -->
    <div id="page-growth" class="page">
      <div class="page-header" style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
        <div>
          <h1>🚀 Growth Engine</h1>
          <p>Your YouTube growth automation cockpit — strategy, content flow, and pipeline in one place.</p>
        </div>
        <button class="btn btn-secondary" onclick="loadGrowth()">↻ Refresh</button>
      </div>

      <!-- DAILY FLOW banner -->
      <div class="daily-flow">
        <div class="daily-flow-title">📌 DAILY FLOW</div>
        <div class="daily-flow-steps">
          <span class="df-step"><span class="df-num">1</span> Check Today's Video</span>
          <span class="df-arrow">→</span>
          <span class="df-step"><span class="df-num">2</span> Record &amp; Upload to YouTube</span>
          <span class="df-arrow">→</span>
          <span class="df-step"><span class="df-num">3</span> Click "Mark as Posted"</span>
          <span class="df-arrow">→</span>
          <span class="df-step"><span class="df-num">4</span> Send Email</span>
        </div>
      </div>

      <!-- Today's Video -->
      <div class="card today-card" style="margin-bottom:18px">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:4px">
          <div>
            <div class="growth-card-title"><span class="gi">📅</span> Today's Video</div>
            <div class="growth-card-sub" style="margin-bottom:0">Your scheduled video for today — record it, post it, then mark it done to fire the email loop.</div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="loadTodayVideo()">↻ Refresh</button>
        </div>
        <div id="today-video-panel" style="margin-top:14px">
          <div class="loader-overlay"><div class="loader-spinner"></div><span>Checking today's schedule…</span></div>
        </div>
      </div>

      <div class="growth-grid">
        <!-- Auto Strategy Insights -->
        <div class="card">
          <div class="growth-card-title"><span class="gi">📊</span> Auto Strategy Insights</div>
          <div class="growth-card-sub">Pulled live from your YouTube Intelligence data.</div>
          <div id="growth-insights">
            <div class="loader-overlay"><div class="loader-spinner"></div><span>Analysing channel…</span></div>
          </div>
        </div>

        <!-- One-Click Content Flow (Master Button) -->
        <div class="card">
          <div class="growth-card-title"><span class="gi">⚡</span> Create Full Content Package</div>
          <div class="growth-card-sub">One click → Idea → Script → YouTube Package → Saved → Pipeline.</div>
          <input id="flow-topic" class="login-input" style="margin-bottom:10px" placeholder="Video topic (e.g. Why Confession heals the soul)">
          <button class="btn btn-primary" id="flow-btn" style="width:100%" onclick="runContentFlow()">⚡ Create Full Content Package</button>
          <div id="flow-status" class="status-bar" style="display:none;margin-top:12px"></div>
          <div id="flow-result" style="margin-top:14px"></div>
        </div>

        <!-- Weekly Content Factory -->
        <div class="card">
          <div class="growth-card-title"><span class="gi">🏭</span> Generate Full Week</div>
          <div class="growth-card-sub">One click → 5 videos generated, saved to the pipeline, and auto-scheduled across the week.</div>
          <button class="btn btn-primary" id="batch-btn" style="width:100%" onclick="runWeeklyAuto()">🏭 Generate &amp; Schedule 5 Videos</button>
          <div class="growth-card-sub" style="margin-top:8px;font-size:11px">Topics are pulled from your YouTube Intelligence, with your weekly plan as a fallback.</div>
          <div id="batch-status" class="status-bar" style="display:none;margin-top:12px"></div>
          <div id="batch-result" style="margin-top:14px"></div>
        </div>

        <!-- Weekly Content Plan -->
        <div class="card">
          <div class="growth-card-title"><span class="gi">🗓️</span> Weekly Content Plan</div>
          <div class="growth-card-sub">5 video ideas with titles and a posting schedule.</div>
          <button class="btn btn-primary" id="plan-btn" style="width:100%" onclick="generateWeeklyPlan()">Generate Weekly Plan</button>
          <div id="plan-status" class="status-bar" style="display:none;margin-top:12px"></div>
          <div id="plan-result" style="margin-top:14px"></div>
        </div>

        <!-- Hook Optimization -->
        <div class="card">
          <div class="growth-card-title"><span class="gi">🎣</span> Hook Optimization</div>
          <div class="growth-card-sub">Turn any topic into 5 scroll-stopping viral hooks.</div>
          <input id="hook-topic" class="login-input" style="margin-bottom:10px" placeholder="Video topic (e.g. The truth about Purgatory)">
          <button class="btn btn-primary" id="hook-btn" style="width:100%" onclick="generateHooks()">Generate 5 Viral Hooks</button>
          <div id="hook-status" class="status-bar" style="display:none;margin-top:12px"></div>
          <div id="hook-result" style="margin-top:14px"></div>
        </div>
      </div>

      <!-- Performance Feedback -->
      <div class="card" style="margin-bottom:18px">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:4px">
          <div>
            <div class="growth-card-title"><span class="gi">📈</span> What's Working — Do More Of This</div>
            <div class="growth-card-sub" style="margin-bottom:0">Your strongest themes and title patterns, pulled from YouTube performance.</div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="loadPerformance()">↻ Refresh</button>
        </div>
        <div id="performance-panel" style="margin-top:14px">
          <div class="loader-overlay"><div class="loader-spinner"></div><span>Reviewing performance…</span></div>
        </div>
      </div>

      <!-- Performance Feedback Loop (manual logging) -->
      <div class="card" style="margin-bottom:18px">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:4px">
          <div>
            <div class="growth-card-title"><span class="gi">🧪</span> Performance Feedback Loop</div>
            <div class="growth-card-sub" style="margin-bottom:0">Log a published video's real numbers — get an instant verdict and a do-more / avoid call.</div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="loadPerfLog()">↻ Refresh</button>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:12px">
          <input id="perf-title" class="login-input" style="flex:2;min-width:200px;margin:0" placeholder="Video title">
          <input id="perf-views" type="number" min="0" class="login-input" style="flex:1;min-width:90px;margin:0" placeholder="Views">
          <input id="perf-ctr" type="number" min="0" step="0.1" class="login-input" style="flex:1;min-width:90px;margin:0" placeholder="CTR %">
          <input id="perf-likes" type="number" min="0" class="login-input" style="flex:1;min-width:90px;margin:0" placeholder="Likes">
          <button class="btn btn-primary" id="perf-btn" onclick="logPerformance()">Log + Analyse</button>
        </div>
        <div id="perf-status" class="status-bar" style="display:none;margin-top:12px"></div>
        <div id="perf-log-panel" style="margin-top:14px"></div>
      </div>

      <!-- Select Posting Days -->
      <div class="card" style="margin-bottom:18px">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:4px">
          <div>
            <div class="growth-card-title"><span class="gi">🗓️</span> Select Posting Days</div>
            <div class="growth-card-sub" style="margin-bottom:0">Pick the days your weekly content factory schedules videos on. Click a day to toggle it.</div>
          </div>
        </div>
        <div id="posting-days-row" class="day-toggle-row">
          <div class="loader-overlay" style="width:100%"><div class="loader-spinner"></div><span>Loading posting days…</span></div>
        </div>
        <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-top:14px">
          <button class="btn btn-primary btn-sm" id="save-days-btn" onclick="savePostingDays()">💾 Save Posting Days</button>
          <span id="posting-days-status" class="status-bar" style="display:none;margin:0;flex:1;min-width:200px"></span>
        </div>
      </div>

      <!-- This Week's Schedule -->
      <div class="card" style="margin-bottom:18px">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:4px">
          <div>
            <div class="growth-card-title"><span class="gi">📆</span> This Week's Schedule</div>
            <div class="growth-card-sub" style="margin-bottom:0">Your auto-scheduled posting calendar — generate a full week to fill it.</div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="loadSchedule()">↻ Refresh</button>
        </div>
        <div id="schedule-panel" style="margin-top:14px">
          <div class="loader-overlay"><div class="loader-spinner"></div><span>Loading schedule…</span></div>
        </div>
      </div>

      <!-- CTA Booster -->
      <div class="card" style="margin-bottom:18px">
        <div class="growth-card-title"><span class="gi">📣</span> CTA Booster</div>
        <div class="growth-card-sub">Auto-insert a Subscribe CTA and a Watch-Next CTA into your scripts.</div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">
          <input id="cta-next" class="login-input" style="flex:1;min-width:220px;margin:0" placeholder="Next video title (optional)">
          <button class="btn btn-primary" id="cta-btn" onclick="generateCTAs()">Generate CTAs</button>
        </div>
        <div id="cta-status" class="status-bar" style="display:none;margin-top:12px"></div>
        <div id="cta-result" style="margin-top:14px"></div>
      </div>

      <!-- Content Pipeline Tracker -->
      <div class="card">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:16px">
          <div>
            <div class="growth-card-title"><span class="gi">📋</span> Content Pipeline Tracker</div>
            <div class="growth-card-sub" style="margin-bottom:0">Move items across stages: Idea → Script → Package → Published.</div>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <input id="pl-new-title" class="login-input" style="margin:0;min-width:200px" placeholder="New idea title…">
            <button class="btn btn-primary" onclick="addPipelineItem()">+ Add Idea</button>
          </div>
        </div>
        <div id="pl-status" class="status-bar" style="display:none;margin-bottom:12px"></div>
        <div id="pipeline-board">
          <div class="loader-overlay"><div class="loader-spinner"></div><span>Loading pipeline…</span></div>
        </div>
      </div>
    </div>

    <!-- ── YOUTUBE STUDIO KIT ── -->
    <div id="page-youtube-kit" class="page">
      <div class="page-header" style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
        <div>
          <h1>YouTube Studio Kit</h1>
          <p>AI-generated YouTube packages — titles, descriptions, tags, and thumbnail text.</p>
        </div>
        <button class="btn btn-secondary" onclick="loadYouTubePackages()">↻ Refresh</button>
      </div>
      <div id="yt-packages-list">
        <div class="loader-overlay">
          <div class="loader-spinner"></div>
          <span>Loading packages…</span>
        </div>
      </div>
    </div>

    <!-- ── YOUTUBE PLAYBOOK (admin reference) ── -->
    <div id="page-youtube-playbook" class="page">
      <div class="page-header">
        <h1>YouTube Playbook</h1>
        <p>Your private upload checklist — optimize every video for subscriber growth. Not visible to the public.</p>
      </div>

      <div class="card" style="margin-bottom:20px">
        <h3 style="color:var(--gold);margin-bottom:8px">1 · Channel Banner</h3>
        <p style="color:var(--muted);margin-bottom:10px">Set your channel banner text to a clear, bold mission line:</p>
        <div style="background:#060606;border:1px solid var(--border);border-radius:10px;padding:14px 16px;color:var(--gold);font-weight:700;font-size:17px">
          "Seek the Truth. Defend the Faith."
        </div>
      </div>

      <div class="card" style="margin-bottom:20px">
        <h3 style="color:var(--gold);margin-bottom:8px">2 · Channel Sections (top → bottom)</h3>
        <p style="color:var(--muted);margin-bottom:12px">Arrange your homepage in this order so new visitors find the best entry points first:</p>
        <ol style="padding-left:20px;line-height:1.9">
          <li><strong>Start Here</strong> — your best intro videos</li>
          <li><strong>Most Popular Truths</strong> — highest-performing videos</li>
          <li><strong>Answering Your Questions</strong> — audience-driven content</li>
          <li><strong>Ancient Heresies Exposed</strong></li>
          <li><strong>The Papacy Series</strong></li>
        </ol>
      </div>

      <div class="card" style="margin-bottom:20px">
        <h3 style="color:var(--gold);margin-bottom:8px">3 · Video Structure (every video)</h3>
        <p style="color:var(--muted);margin-bottom:12px">Follow the <strong>Hook → Build → Deliver → CTA</strong> arc:</p>
        <ul style="list-style:none;padding:0;line-height:1.5">
          <li style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid var(--border)"><span style="color:var(--gold);font-weight:700;min-width:78px">HOOK</span><span>Strong hook in the first 5 seconds — a question, claim, or tension that stops the scroll.</span></li>
          <li style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid var(--border)"><span style="color:var(--gold);font-weight:700;min-width:78px">BUILD</span><span>State a clear thesis, then build tension — raise the stakes of the question.</span></li>
          <li style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid var(--border)"><span style="color:var(--gold);font-weight:700;min-width:78px">DELIVER</span><span>Deliver the truth — Scripture, history, and Tradition, explained simply.</span></li>
          <li style="display:flex;gap:12px;padding:10px 0"><span style="color:var(--gold);font-weight:700;min-width:78px">CTA</span><span>End with "Subscribe for more truth" — every single video.</span></li>
        </ul>
      </div>

      <div class="card">
        <h3 style="color:var(--gold);margin-bottom:8px">4 · Title, Thumbnail &amp; Description</h3>
        <div style="display:grid;gap:16px;margin-top:8px">
          <div>
            <div style="font-weight:700;margin-bottom:4px">Titles</div>
            <p style="color:var(--muted)">Lead with curiosity or a bold claim. Keep under 60 characters so it never truncates. One clear idea — no clickbait you can't pay off.</p>
          </div>
          <div>
            <div style="font-weight:700;margin-bottom:4px">Thumbnails</div>
            <p style="color:var(--muted)">High contrast, one expressive face or symbol, 3–5 large words max. Readable at a glance on mobile. Consistent style builds brand recognition.</p>
          </div>
          <div>
            <div style="font-weight:700;margin-bottom:4px">Descriptions</div>
            <p style="color:var(--muted)">First line restates the hook (shows in search). Add a 1–2 sentence summary, then your YouTube + mailing-list links, then 3–5 relevant tags/keywords.</p>
          </div>
        </div>
      </div>
    </div>

  </main>
</div>

<!-- Toast notification -->
<div id="toast"></div>

<!-- Script Result Modal -->
<div id="script-modal">
  <div class="script-modal-box">
    <div class="script-modal-header">
      <div style="overflow:hidden;flex:1">
        <div style="font-size:10px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.7px;margin-bottom:4px">Generated Script</div>
        <div id="smodal-title" style="font-size:16px;font-weight:700;color:var(--gold);line-height:1.3"></div>
      </div>
      <button class="modal-close" onclick="closeScriptModal()" style="flex-shrink:0">✕</button>
    </div>
    <div class="script-modal-body" id="smodal-body">
      <div class="script-generating" id="smodal-loading">
        <div class="loader-spinner"></div>
        <span>Generating script with AI…</span>
      </div>
      <div id="smodal-content" style="display:none">
        <div class="script-section">
          <div class="script-section-label">Hook</div>
          <div class="script-hook" id="smodal-hook"></div>
        </div>
        <div class="script-section">
          <div class="script-section-label">Full Script</div>
          <div class="script-body" id="smodal-script"></div>
        </div>
        <!-- YouTube Package section (expands inline after generation) -->
        <div id="smodal-yt-section" style="display:none;margin-top:22px;padding-top:22px;border-top:1px solid var(--border)">
          <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.7px;margin-bottom:14px">▶ YouTube Package</div>
          <div id="smodal-yt-loading" class="script-generating" style="display:none">
            <div class="loader-spinner"></div>
            <span>Generating YouTube package with AI…</span>
          </div>
          <div id="smodal-yt-content" style="display:none">
            <div class="script-section">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
                <div class="script-section-label" style="margin-bottom:0">Title</div>
                <button class="btn btn-secondary btn-sm" onclick="ytPkgCopy('yt-pkg-title')">Copy</button>
              </div>
              <div class="script-hook" id="yt-pkg-title" style="font-size:14px;font-weight:600;color:var(--gold)"></div>
            </div>
            <div class="script-section">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
                <div class="script-section-label" style="margin-bottom:0">Description</div>
                <button class="btn btn-secondary btn-sm" onclick="ytPkgCopy('yt-pkg-desc')">Copy</button>
              </div>
              <div class="script-body" id="yt-pkg-desc" style="max-height:160px"></div>
            </div>
            <div class="script-section">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
                <div class="script-section-label" style="margin-bottom:0">Tags</div>
                <button class="btn btn-secondary btn-sm" onclick="ytPkgCopy('yt-pkg-tags')">Copy</button>
              </div>
              <div style="font-size:12px;color:var(--text);background:var(--bg);padding:10px 14px;border-radius:8px;border:1px solid var(--border);line-height:1.7" id="yt-pkg-tags"></div>
            </div>
            <div class="script-section">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
                <div class="script-section-label" style="margin-bottom:0">Thumbnail Text</div>
                <button class="btn btn-secondary btn-sm" onclick="ytPkgCopy('yt-pkg-thumb')">Copy</button>
              </div>
              <div style="font-size:18px;font-weight:800;color:var(--gold);background:var(--bg);padding:12px 16px;border-radius:8px;border:1px solid var(--border);text-align:center;letter-spacing:.5px" id="yt-pkg-thumb"></div>
            </div>
          </div>
        </div>
        <!-- 🔥 Make This Viral panel (expands inline after one-click viralise) -->
        <div id="smodal-viral-section" style="display:none;margin-top:22px;padding-top:22px;border-top:1px solid var(--border)">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
            <div style="font-size:10px;font-weight:700;color:var(--gold);text-transform:uppercase;letter-spacing:.7px">🔥 Viral Conversion Package</div>
          </div>
          <div id="smodal-viral-loading" class="script-generating" style="display:none">
            <div class="loader-spinner"></div>
            <span>Maximising virality — scoring, rewriting, boosting…</span>
          </div>
          <div id="smodal-viral-content" style="display:none"></div>
        </div>
        <!-- YouTube Studio Optimization panel (expands inline after optimise) -->
        <div id="smodal-opt-section" style="display:none;margin-top:22px;padding-top:22px;border-top:1px solid var(--border)">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
            <div style="font-size:10px;font-weight:700;color:var(--gold);text-transform:uppercase;letter-spacing:.7px">🎯 YouTube Studio Optimization</div>
            <button class="btn btn-primary btn-sm" onclick="applyStrategy()" id="smodal-apply-btn" style="display:none">✓ Apply Strategy</button>
          </div>
          <div id="smodal-opt-loading" class="script-generating" style="display:none">
            <div class="loader-spinner"></div>
            <span>Building your publishing blueprint…</span>
          </div>
          <div id="smodal-opt-content" style="display:none"></div>
        </div>
        <!-- Content Reuse section (expands inline after repurposing) -->
        <div id="smodal-reuse-section" style="display:none;margin-top:22px;padding-top:22px;border-top:1px solid var(--border)">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
            <div id="smodal-reuse-label" style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.7px">♻ Repurposed Content</div>
            <button class="btn btn-secondary btn-sm" onclick="copyReuse()">Copy</button>
          </div>
          <div id="smodal-reuse-loading" class="script-generating" style="display:none">
            <div class="loader-spinner"></div>
            <span>Repurposing with AI…</span>
          </div>
          <div class="script-body" id="smodal-reuse-content" style="white-space:pre-wrap"></div>
        </div>
      </div>
      <div id="smodal-error" style="display:none;padding:32px;text-align:center;color:var(--red)"></div>
    </div>
    <div class="script-modal-footer" id="smodal-footer">
      <button class="btn btn-primary" onclick="modalCopyScript()" id="smodal-copy-btn" style="display:none">Copy Script</button>
      <button class="btn btn-secondary" onclick="modalSendToNewsletter()" id="smodal-send-btn" style="display:none">✉ Turn into Email</button>
      <button class="btn btn-secondary" onclick="repurposeCurrent('youtube_post')" id="smodal-ytpost-btn" style="display:none">📢 YouTube Post</button>
      <button class="btn btn-secondary" onclick="generateShortsCurrent()" id="smodal-shorts-btn" style="display:none">⚡ Generate Shorts</button>
      <button class="btn btn-secondary" onclick="pkgSendToNewsletter()" id="smodal-pkg-send-btn" style="display:none">✉ Package as Newsletter</button>
      <button class="btn btn-secondary" onclick="modalSaveForLater()" id="smodal-save-btn" style="display:none">Save for Later</button>
      <button class="btn btn-secondary" onclick="generateYouTubePackage()" id="smodal-ytpkg-btn" style="display:none">▶ YT Package</button>
      <button class="btn btn-secondary" onclick="optimizeCurrent()" id="smodal-optimize-btn" style="display:none">🎯 Optimize</button>
      <button class="btn btn-primary" onclick="makeViralCurrent()" id="smodal-viral-btn" style="display:none">🔥 Make This Viral</button>
      <button class="btn btn-secondary" onclick="closeScriptModal()" style="margin-left:auto">Close</button>
    </div>
  </div>
</div>

<!-- Preview Modal -->
<div id="preview-modal">
  <div class="modal-box">
    <div class="modal-header">
      <h3>Email Preview</h3>
      <button class="modal-close" onclick="closePreview()">✕</button>
    </div>
    <iframe id="preview-frame" title="Email Preview" sandbox=""></iframe>
  </div>
</div>

<script>
  const SESSION_KEY = 'odili_admin_key';
  let _ytData = null;
  let _ytChannelUrl = '';

  // Resilient key storage: sessionStorage can throw (SecurityError) when the
  // dashboard is embedded in a cross-origin iframe or when storage is blocked.
  // Fall back to an in-memory key so sign-in still works for this page load.
  let _memKey = '';
  function getStoredKey() {
    try { return sessionStorage.getItem(SESSION_KEY) || _memKey || ''; }
    catch (e) { return _memKey || ''; }
  }
  function setStoredKey(k) {
    _memKey = k || '';
    try { sessionStorage.setItem(SESSION_KEY, k); } catch (e) {}
  }
  function clearStoredKey() {
    _memKey = '';
    try { sessionStorage.removeItem(SESSION_KEY); } catch (e) {}
  }

  // ── Helpers ──────────────────────────────────────────────
  const $ = id => document.getElementById(id);
  function apiKey() { return getStoredKey(); }

  async function apiFetch(path, opts = {}) {
    const headers = {
      'x-api-key': apiKey(),
      'Content-Type': 'application/json',
      ...(opts.headers || {})
    };
    return fetch(path, { ...opts, headers });
  }

  function fmtDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
    return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  }

  function fmtNum(n) {
    if (n == null) return '—';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return String(n);
  }

  // Escapes quotes too, so the output is safe in BOTH text and
  // double/single-quoted attribute contexts (e.g. value="...").
  function esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // Serialise a value for safe embedding inside a DOUBLE-QUOTED HTML attribute
  // (e.g. inline onclick). JSON.stringify wraps strings in double quotes, which
  // would otherwise terminate the attribute early and kill the click handler, so
  // we entity-encode the result. The browser decodes it back to valid JS before
  // evaluating the handler.
  function safeUrl(u) {
    u = String(u || '').trim();
    return /^https?:\/\//i.test(u) ? u : '';
  }
  function jsAttr(v) {
    return JSON.stringify(v)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function showBar(id, msg, type) {
    const el = $(id);
    el.textContent = msg;
    el.className = 'status-bar ' + type;
    el.style.display = 'block';
    if (type === 'success') setTimeout(() => { el.style.display = 'none'; }, 6000);
  }

  // ── Auth ─────────────────────────────────────────────────
  async function login() {
    const key = $('key-input').value.trim();
    const errEl = $('login-err');
    errEl.textContent = '';
    if (!key) { errEl.textContent = 'Please enter your API key.'; return; }
    try {
      const res = await fetch('/admin/status', { headers: { 'x-api-key': key } });
      if (res.status === 401) { errEl.textContent = 'Invalid API key. Try again.'; return; }
      if (!res.ok) { errEl.textContent = 'Server error. Check backend is running.'; return; }
      setStoredKey(key);
      showApp();
    } catch (e) { errEl.textContent = 'Could not reach the server. Try again.'; }
  }

  function signOut() {
    clearStoredKey();
    $('app').style.display = 'none';
    $('login').style.display = 'flex';
    $('key-input').value = '';
    _ytData = null;
  }

  // ── Navigation ────────────────────────────────────────────
  const PAGE_TITLES = {
    dashboard: 'Dashboard',
    youtube: 'YouTube Intelligence',
    growth: 'Growth Engine',
    'growth-pack': '🧠 Growth Pack',
    analytics: 'Analytics',
    'weekly-distribution': '📢 Weekly Distribution',
    'traffic-engine': '🎬 Traffic Engine',
    'lead-discovery': '🔎 Lead Discovery',
    'reply-engine': '💬 Reply Engine',
    'conversion-engine': '⚡ Conversion Engine',
    'audience-geo': '🌎 Audience Geography',
    'growth-brain': '🚀 Growth Brain',
    'lead-evangelist': '🕊️ Lead Evangelist',
    newsletter: 'Newsletter Manager',
    subscribers: 'Subscribers',
    ideas: 'Content Ideas',
    topics: 'Audience Topics',
    'content-hub': 'Content Hub',
    'email-queue': 'Email Queue',
    'content-plan': 'Content Plan',
    'video-grid': '🎞️ Video Grid Manager',
    'seo-engine': '🔍 SEO Engine',
    'saved-scripts': 'Saved Scripts',
    'youtube-kit': 'YouTube Studio Kit',
    'youtube-playbook': 'YouTube Playbook',
    settings: 'Settings',
  };

  var ADMIN_TAB_KEY = 'odili_admin_tab';
  var ADMIN_SCROLL_KEY = 'odili_admin_scroll';
  var currentPage = null;

  function scrollMemLoad() {
    try {
      var raw = sessionStorage.getItem(ADMIN_SCROLL_KEY);
      var m = raw ? JSON.parse(raw) : {};
      return (m && typeof m === 'object') ? m : {};
    } catch (e) { return {}; }
  }
  function scrollMemSave(page, top) {
    if (!page) return;
    try {
      var m = scrollMemLoad();
      m[page] = top;
      sessionStorage.setItem(ADMIN_SCROLL_KEY, JSON.stringify(m));
    } catch (e) {}
  }
  function restoreScroll(page) {
    var m = scrollMemLoad();
    var target = m[page];
    if (typeof target !== 'number' || !(target > 0)) return;
    var mainEl = document.querySelector('.main-content');
    if (!mainEl) return;
    var attempts = 0;
    (function tryRestore() {
      if (currentPage !== page) return;
      mainEl.scrollTop = target;
      attempts++;
      // Content loads async and grows the page; retry until it sticks.
      if (Math.abs(mainEl.scrollTop - target) > 2 && attempts < 12) {
        setTimeout(tryRestore, 250);
      }
    })();
  }
  function initScrollTracking() {
    var mainEl = document.querySelector('.main-content');
    if (!mainEl) return;
    var pending = null;
    mainEl.addEventListener('scroll', function () {
      if (pending) return;
      pending = setTimeout(function () {
        pending = null;
        if (currentPage) scrollMemSave(currentPage, mainEl.scrollTop);
      }, 200);
    }, { passive: true });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initScrollTracking);
  } else {
    initScrollTracking();
  }

  function toggleMenu(ev, name) {
    ev.stopPropagation();
    var group = $('group-' + name);
    var wasOpen = group.classList.contains('open');
    closeAllMenus();
    if (!wasOpen) group.classList.add('open');
  }
  function closeAllMenus() {
    document.querySelectorAll('.topnav-group.open').forEach(g => g.classList.remove('open'));
  }
  document.addEventListener('click', closeAllMenus);

  function navigate(page) {
    if (!$('page-' + page)) page = 'dashboard';
    var prevEl = document.querySelector('.main-content');
    if (currentPage && currentPage !== page && prevEl) {
      scrollMemSave(currentPage, prevEl.scrollTop);
    }
    try { localStorage.setItem(ADMIN_TAB_KEY, page); } catch (e) {}
    closeAllMenus();
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.topnav-group-btn').forEach(b => b.classList.remove('active'));
    $('page-' + page).classList.add('active');
    var navEl = document.querySelector('[data-page="' + page + '"]');
    if (navEl) {
      navEl.classList.add('active');
      var group = navEl.closest('.topnav-group');
      if (group) group.querySelector('.topnav-group-btn').classList.add('active');
    }
    $('header-title').textContent = PAGE_TITLES[page] || page;
    currentPage = page;
    var mainEl = document.querySelector('.main-content');
    if (mainEl) mainEl.scrollTop = 0;
    restoreScroll(page);

    if (page === 'dashboard')      loadDashboard();
    if (page === 'newsletter')     { loadHistory(); loadStatus(); }
    if (page === 'subscribers')    loadSubscribers();
    if (page === 'topics')         loadAdminTopics();
    if (page === 'content-hub')    { loadFeaturedAdmin(); loadNews(); prLoad(); }
    if (page === 'email-queue')    eqLoad();
    if (page === 'content-plan')   cpLoad();
    if (page === 'video-grid')     vgLoad();
    if (page === 'seo-engine')     { seoArticles(); }
    if (page === 'youtube')        loadYoutube(false);
    if (page === 'growth')         loadGrowth();
    if (page === 'growth-pack')    gpInit();
    if (page === 'analytics')      loadAnalytics();
    if (page === 'traffic-engine') loadPostingPlan();
    if (page === 'lead-discovery') ldLoad();
    if (page === 'reply-engine')   reLoad();
    if (page === 'conversion-engine') ceLoadPerf();
    if (page === 'audience-geo')   geoLoad();
    if (page === 'growth-brain')   gbLoadPerf();
    if (page === 'lead-evangelist') leInit();
    if (page === 'saved-scripts')  loadSavedScripts();
    if (page === 'youtube-kit')    loadYouTubePackages();
    if (page === 'settings')       loadStatus();
  }

  // ── Email Queue ───────────────────────────────────────────
  var eqItems = [];

  async function eqLoad() {
    try {
      const res = await apiFetch('/email-queue');
      if (!res.ok) { showBar('eq-status-bar', 'Could not load the email queue.', 'error'); return; }
      const d = await res.json();
      eqItems = d.items || [];
      $('eq-count').textContent = eqItems.length;
      eqRender();
    } catch (e) {
      showBar('eq-status-bar', 'Could not load the email queue.', 'error');
    }
  }

  function eqStatusPill(item) {
    if (item.status === 'sent') return '<span style="color:#4caf50;font-weight:600">✓ Sent</span>';
    if (item.status === 'approved' && item.scheduled_at) return '<span style="color:var(--gold);font-weight:600">⏰ Scheduled</span>';
    if (item.status === 'approved') return '<span style="color:var(--gold);font-weight:600">Approved</span>';
    return '<span style="color:var(--muted);font-weight:600">Draft</span>';
  }

  function eqSourceLabel(src) {
    const map = { trending_topic: '🔥 Trending topic', video_posted: '🎬 Video posted', content_plan: '🧭 Content plan', manual: '✍️ Manual' };
    return map[src] || esc(src || '');
  }

  function eqRender() {
    if (!eqItems.length) {
      $('eq-list').innerHTML = '<div class="empty-row">Queue is empty. Drafts appear here automatically when a topic trends or you mark a video posted.</div>';
      return;
    }
    $('eq-list').innerHTML = eqItems.map(function (it) {
      const editable = it.status !== 'sent';
      const when = it.sent_at ? ('Sent ' + esc(it.sent_at.slice(0, 16).replace('T', ' ')) + ' UTC')
        : it.scheduled_at ? ('Sends ' + esc(it.scheduled_at.slice(0, 16).replace('T', ' ')) + ' UTC')
        : ('Created ' + esc((it.created_at || '').slice(0, 16).replace('T', ' ')) + ' UTC');
      let html = '<div class="card" style="margin-bottom:14px">'
        + '<div class="card-body" style="padding:16px 18px">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px">'
        + '<div style="font-size:12px;color:var(--muted)">' + eqSourceLabel(it.source) + ' · ' + when + '</div>'
        + '<div>' + eqStatusPill(it) + '</div></div>';
      if (editable) {
        html += '<div class="field"><label>Subject</label><input id="eq-subj-' + it.id + '" type="text" maxlength="300" value="' + esc(it.subject) + '"></div>'
          + '<div class="field"><label>Body <span style="color:var(--muted);font-weight:400">(one paragraph per line)</span></label>'
          + '<textarea id="eq-body-' + it.id + '" rows="5">' + esc(it.body) + '</textarea></div>';
      } else {
        html += '<div style="font-weight:600;margin-bottom:6px">' + esc(it.subject) + '</div>'
          + '<div style="color:var(--muted);font-size:13px;white-space:pre-wrap">' + esc(it.body) + '</div>';
      }
      if (it.error) html += '<div style="color:#e57373;font-size:13px;margin:8px 0">⚠ ' + esc(it.error) + '</div>';
      html += '<div class="btn-row" style="margin-top:12px;flex-wrap:wrap">';
      if (editable) {
        html += '<button class="btn btn-secondary btn-sm" onclick="eqSave(' + it.id + ')">💾 Save edits</button>'
          + '<button class="btn btn-secondary btn-sm" onclick="eqPreview(' + it.id + ')">👁 Preview</button>'
          + '<button class="btn btn-primary btn-sm" onclick="eqApprove(' + it.id + ')">✅ Approve &amp; send now</button>'
          + '<input id="eq-when-' + it.id + '" type="datetime-local" style="max-width:210px">'
          + '<button class="btn btn-secondary btn-sm" onclick="eqSchedule(' + it.id + ')">⏰ Schedule</button>';
      }
      html += '<button class="btn btn-secondary btn-sm" onclick="eqDelete(' + it.id + ')" style="color:#e57373">🗑 Delete</button>'
        + '</div></div></div>';
      return html;
    }).join('');
  }

  async function eqSave(id) {
    const subject = $('eq-subj-' + id).value.trim();
    const body = $('eq-body-' + id).value.trim();
    if (!subject || !body) { showBar('eq-status-bar', 'Subject and body cannot be empty.', 'error'); return; }
    const res = await apiFetch('/email-queue/' + id, { method: 'PATCH', body: JSON.stringify({ subject: subject, body: body }) });
    if (res.ok) { showBar('eq-status-bar', 'Draft saved.', 'success'); eqLoad(); }
    else showBar('eq-status-bar', 'Could not save the draft.', 'error');
  }

  async function eqApprove(id) {
    if (!confirm('Send this email to ALL active subscribers now?')) return;
    showBar('eq-status-bar', 'Sending…', 'success');
    const res = await apiFetch('/email-queue/' + id + '/approve', { method: 'POST', body: JSON.stringify({}) });
    const d = await res.json().catch(function () { return {}; });
    if (res.ok && d.status === 'sent') {
      const s = d.send_summary || {};
      showBar('eq-status-bar', 'Sent to ' + (s.sent || 0) + ' subscriber(s).', 'success');
    } else if (res.ok) {
      showBar('eq-status-bar', d.error || 'Approved, but the send did not complete.', 'error');
    } else {
      showBar('eq-status-bar', d.detail || 'Could not send.', 'error');
    }
    eqLoad();
  }

  async function eqSchedule(id) {
    const val = $('eq-when-' + id).value;
    if (!val) { showBar('eq-status-bar', 'Pick a date & time first.', 'error'); return; }
    const iso = new Date(val).toISOString();
    const res = await apiFetch('/email-queue/' + id + '/approve', { method: 'POST', body: JSON.stringify({ scheduled_at: iso }) });
    if (res.ok) { showBar('eq-status-bar', 'Scheduled. It will send automatically.', 'success'); eqLoad(); }
    else showBar('eq-status-bar', 'Could not schedule.', 'error');
  }

  async function eqPreview(id) {
    const res = await apiFetch('/email-queue/' + id + '/preview');
    if (!res.ok) { showBar('eq-status-bar', 'Could not load the preview.', 'error'); return; }
    const html = await res.text();
    const w = window.open('', '_blank');
    if (w) { w.document.open(); w.document.write(html); w.document.close(); }
  }

  async function eqDelete(id) {
    if (!confirm('Delete this email from the queue?')) return;
    const res = await apiFetch('/email-queue/' + id, { method: 'DELETE' });
    if (res.ok) { showBar('eq-status-bar', 'Deleted.', 'success'); eqLoad(); }
    else showBar('eq-status-bar', 'Could not delete.', 'error');
  }

  // ── Content Plan ──────────────────────────────────────────
  async function cpLoad() {
    try {
      const res = await apiFetch('/content/plan');
      if (!res.ok) { showBar('cp-status-bar', 'Could not load the content plan.', 'error'); return; }
      const d = await res.json();

      const alerts = d.alerts || [];
      $('cp-alerts').innerHTML = alerts.map(function (a) {
        return '<div class="card" style="border-left:3px solid var(--gold);margin-bottom:14px"><div class="card-body" style="padding:14px 18px;color:var(--gold);font-weight:600">' + esc(a.message) + '</div></div>';
      }).join('');

      const plan = d.plan || [];
      if (!plan.length) {
        $('cp-list').innerHTML = '<div class="empty-row">No approved topics yet — add topics in the Audience Topics tab.</div>';
        return;
      }
      $('cp-list').innerHTML = plan.map(function (p, i) {
        return '<div class="card" style="margin-bottom:14px"><div class="card-body" style="padding:16px 18px">'
          + '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">'
          + '<div style="font-weight:700;font-size:16px">#' + (i + 1) + ' · ' + esc(p.topic) + '</div>'
          + '<div style="color:var(--gold);font-weight:700">Score ' + p.score + '</div></div>'
          + '<div style="color:var(--muted);font-size:13px;margin-bottom:10px">' + esc(p.why) + '</div>'
          + '<div style="font-size:13px;margin-bottom:4px"><b>Title:</b> ' + esc(p.suggested_title) + '</div>'
          + '<div style="font-size:13px;margin-bottom:4px"><b>Hook:</b> ' + esc(p.suggested_hook) + '</div>'
          + '<div style="font-size:13px;margin-bottom:4px"><b>Angle:</b> ' + esc(p.suggested_angle) + '</div>'
          + '<div style="font-size:13px;margin-bottom:8px"><b>Thumbnail:</b> ' + esc(p.thumbnail_idea) + '</div>'
          + '<div style="font-size:13px;color:var(--muted);margin-bottom:10px">' + (p.script_outline || []).map(esc).join('<br>') + '</div>'
          + '<div class="btn-row" style="flex-wrap:wrap">'
          + '<button class="btn btn-secondary btn-sm" onclick="copyText(' + jsAttr(p.suggested_title) + ', \\'Title\\')">📋 Copy title</button>'
          + '<button class="btn btn-secondary btn-sm" onclick="copyText(' + jsAttr(p.suggested_hook) + ', \\'Hook\\')">📋 Copy hook</button>'
          + '<button class="btn btn-primary btn-sm" onclick="cpEmailDraft(' + p.topic_id + ')">📬 Draft email for this</button>'
          + '</div></div></div>';
      }).join('');
    } catch (e) {
      showBar('cp-status-bar', 'Could not load the content plan.', 'error');
    }
  }

  async function cpEmailDraft(topicId) {
    const res = await apiFetch('/content/plan/' + topicId + '/email-draft', { method: 'POST' });
    if (res.ok) showBar('cp-status-bar', 'Email draft added to the Email Queue for review.', 'success');
    else showBar('cp-status-bar', 'Could not create the draft.', 'error');
  }

  async function cpLoadCtas() {
    const title = $('cp-cta-title').value.trim();
    const qs = title ? ('?video_title=' + encodeURIComponent(title)) : '';
    const res = await apiFetch('/content/youtube-ctas' + qs);
    if (!res.ok) { $('cp-cta-out').innerHTML = '<div class="empty-row">Could not generate the CTA pack.</div>'; return; }
    const d = await res.json();
    function block(label, text) {
      return '<div style="margin-top:12px"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
        + '<b style="font-size:13px">' + esc(label) + '</b>'
        + '<button class="btn btn-secondary btn-sm" onclick="copyText(' + jsAttr(text) + ', ' + jsAttr(label) + ')">📋 Copy</button></div>'
        + '<div style="background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:8px;padding:12px;font-size:13px;white-space:pre-wrap;color:var(--muted)">' + esc(text) + '</div></div>';
    }
    $('cp-cta-out').innerHTML =
      block('Description CTA', d.description_cta || '')
      + block('Pinned comment', d.pinned_comment || '')
      + block('End-screen script', d.end_screen_script || '');
  }

  // ── Analytics ─────────────────────────────────────────────
  async function loadAnalytics() {
    const range = $('an-range') ? $('an-range').value : '';
    const qs = range ? ('?days=' + encodeURIComponent(range)) : '';
    try {
      const res = await apiFetch('/analytics/summary' + qs);
      if (!res.ok) { showBar('an-status', 'Could not load analytics.', 'error'); return; }
      const d = await res.json();

      $('an-visits').textContent  = fmtNum(d.total_visits || 0);
      $('an-clicks').textContent  = fmtNum(d.cta_clicks || 0);
      $('an-signups').textContent = fmtNum(d.subscriptions || 0);
      $('an-conv').textContent    = (d.conversion_rate || 0) + '%';

      const heads = d.top_headlines || [];
      $('an-headlines').innerHTML = heads.length
        ? heads.map(h => '<tr><td>' + esc(h.headline) + '</td><td style="text-align:right">' + fmtNum(h.views) + '</td></tr>').join('')
        : '<tr class="empty-row"><td colspan="2">No headline data yet.</td></tr>';

      const topics = d.top_topics || [];
      $('an-topics').innerHTML = topics.length
        ? topics.map(t => '<tr><td>' + esc(t.topic) + '</td><td style="text-align:right">' + fmtNum(t.count) + '</td></tr>').join('')
        : '<tr class="empty-row"><td colspan="2">No topic conversions yet.</td></tr>';

      const sd = d.scroll_depth || {};
      const levels = ['25', '50', '75', '100'];
      const maxScroll = Math.max(1, ...levels.map(l => sd[l] || 0));
      $('an-scroll').innerHTML = levels.map(function (lvl) {
        const v = sd[lvl] || 0;
        const pct = Math.round((v / maxScroll) * 100);
        return '<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">' +
            '<span style="width:46px;color:#8a8a8a;font-size:13px">' + lvl + '%</span>' +
            '<span style="flex:1;height:10px;background:#1c1c1c;border-radius:6px;overflow:hidden">' +
              '<span style="display:block;height:100%;width:' + pct + '%;background:#FFD700"></span>' +
            '</span>' +
            '<span style="width:56px;text-align:right;font-size:13px">' + fmtNum(v) + '</span>' +
          '</div>';
      }).join('');

      $('an-status').style.display = 'none';
    } catch (e) {
      showBar('an-status', 'Network error loading analytics.', 'error');
    }
  }

  // ── App init ──────────────────────────────────────────────
  function showApp() {
    $('login').style.display = 'none';
    $('app').style.display = 'block';
    console.log('[GrowthLoop] Admin dashboard opened.');
    var lastTab = 'dashboard';
    try { lastTab = localStorage.getItem(ADMIN_TAB_KEY) || 'dashboard'; } catch (e) {}
    navigate(lastTab);
    if (lastTab !== 'dashboard') loadStatus();
    if (lastTab !== 'lead-discovery') ldRefreshTabBadge();
  }

  // ── Status ────────────────────────────────────────────────
  async function loadStatus() {
    try {
      const res = await apiFetch('/admin/status');
      if (!res.ok) return;
      const d = await res.json();

      // Header pill
      $('status-subs').textContent = d.subscriber_count ?? '—';
      if (d.youtube_channel_url) _ytChannelUrl = d.youtube_channel_url;

      // Dashboard stats
      safeSet('d-subs', d.subscriber_count ?? '—');
      const todayYes = d.send_today;
      safeSet('d-today', todayYes ? '✓ Yes' : 'No');
      if ($('d-today')) $('d-today').style.color = todayYes ? 'var(--green)' : 'var(--muted)';
      const nextDay = d.next_send_day
        ? d.next_send_day.charAt(0).toUpperCase() + d.next_send_day.slice(1)
        : '—';
      safeSet('d-next', 'Next: ' + nextDay);

      // Last newsletter
      if (d.last_newsletter) {
        safeSet('d-last-date', fmtDate(d.last_newsletter.sent_at));
        safeSet('d-last-subject', d.last_newsletter.subject || '—');
        const sent = d.last_newsletter.sent ?? 0;
        const failed = d.last_newsletter.failed ?? 0;
        const total = d.last_newsletter.recipients_total ?? 0;
        safeSet('d-last-sent', sent + ' / ' + total);
        safeSet('d-last-failed', failed > 0 ? failed + ' failed' : 'No failures ✓');
        if ($('d-last-failed')) {
          $('d-last-failed').style.color = failed > 0 ? 'var(--red)' : 'var(--green)';
        }
      }

      // Newsletter page stats
      safeSet('nl-subs', d.subscriber_count ?? '—');
      if ($('nl-today')) {
        $('nl-today').textContent = todayYes ? 'Yes ✓' : 'No';
        $('nl-today').style.color = todayYes ? 'var(--green)' : 'var(--muted)';
      }
      safeSet('nl-next-day', nextDay);

      // Settings page
      safeSet('sched-next', nextDay);
      if ($('sched-status')) {
        $('sched-status').textContent = d.scheduler_running ? 'Running' : 'Stopped';
        $('sched-status').className = 'badge ' + (d.scheduler_running ? 'badge-green' : 'badge-red');
      }
      if ($('sched-today')) {
        $('sched-today').textContent = todayYes ? 'Yes ✓' : 'No';
        $('sched-today').style.color = todayYes ? 'var(--green)' : 'var(--muted)';
      }
    } catch (e) { /* silent */ }
  }

  function safeSet(id, val) { const el = $(id); if (el) el.textContent = val; }

  // ── Dashboard ─────────────────────────────────────────────
  async function loadDashboard() {
    await Promise.all([loadStatus(), loadHistoryTo('d-history-body', 5)]);
  }

  async function dashSend() {
    const subject = $('d-subject').value.trim();
    const body    = $('d-body').value.trim();
    if (!subject || !body) { showBar('d-send-status', 'Please fill in both fields.', 'error'); return; }
    const btn = $('d-send-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Sending…';
    try {
      const res = await apiFetch('/send-newsletter/custom?force=true', {
        method: 'POST', body: JSON.stringify({ subject, body }),
      });
      const d = await res.json();
      if (!res.ok) {
        showBar('d-send-status', 'Error: ' + (d.detail || JSON.stringify(d)), 'error');
      } else if (d.status === 'success') {
        console.log('[GrowthLoop] Newsletter sent to ' + d.sent + ' subscriber(s):', subject);
        showBar('d-send-status', '✓ Sent to ' + d.sent + ' subscriber' + (d.sent !== 1 ? 's' : '') + '.', 'success');
        $('d-subject').value = ''; $('d-body').value = '';
        loadDashboard();
      } else if (d.status === 'partial') {
        showBar('d-send-status', 'Partial: ' + d.sent + ' sent, ' + d.failed + ' failed.', 'error');
        loadDashboard();
      } else {
        showBar('d-send-status', d.detail || d.reason || 'Skipped — check scheduler.', 'error');
      }
    } catch (e) { showBar('d-send-status', 'Network error.', 'error'); }
    finally { btn.disabled = false; btn.textContent = 'Send to All Subscribers'; }
  }

  async function dashPreview() {
    const subject = $('d-subject').value.trim();
    const body    = $('d-body').value.trim();
    if (!subject || !body) { showBar('d-send-status', 'Fill in both fields first.', 'error'); return; }
    await doPreview(subject, body, 'd-send-status');
  }

  // ── History ───────────────────────────────────────────────
  async function loadHistory()            { await loadHistoryTo('history-body', 20); }
  async function loadHistoryTo(tbodyId, limit) {
    const tbody = $(tbodyId);
    if (!tbody) return;
    tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Loading…</td></tr>';
    try {
      const res = await apiFetch('/newsletter/history?limit=' + limit);
      if (!res.ok) { tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Failed to load history.</td></tr>'; return; }
      const { history } = await res.json();
      if (!history.length) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="5">No newsletters sent yet.</td></tr>';
        return;
      }
      tbody.innerHTML = history.map(row => {
        const st    = row.failed === 0 ? 'green' : row.sent === 0 ? 'red' : 'yellow';
        const label = row.failed === 0 ? 'All sent' : row.sent === 0 ? 'All failed' : 'Partial';
        const trig  = (row.triggered_by || '').replace(/_/g, ' ');
        return `<tr>
          <td style="color:var(--muted);font-size:12px">${fmtDate(row.sent_at)}</td>
          <td>${esc(row.subject)}</td>
          <td>${row.sent} / ${row.recipients_total}</td>
          <td><span class="badge badge-${st}">${label}</span></td>
          <td style="font-size:12px;color:var(--muted)">${esc(trig)}</td>
        </tr>`;
      }).join('');
    } catch (e) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Error loading history.</td></tr>';
    }
  }

  // ── Subscribers ───────────────────────────────────────────
  async function loadSubscribers() {
    const tbody = $('sub-table-body');
    tbody.innerHTML = '<tr class="empty-row"><td colspan="2">Loading…</td></tr>';
    try {
      const res = await apiFetch('/emails');
      if (!res.ok) { tbody.innerHTML = '<tr class="empty-row"><td colspan="2">Failed to load.</td></tr>'; return; }
      const { emails, count } = await res.json();
      $('status-subs').textContent = count;
      $('sub-count-display').textContent = count;
      if (!emails.length) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="2">No active subscribers yet.</td></tr>';
        return;
      }
      tbody.innerHTML = emails.map(email => `<tr>
        <td style="font-family:monospace;font-size:12px">${esc(email)}</td>
        <td style="text-align:right">
          <button class="btn btn-danger btn-sm"
            onclick="removeSubscriber('${esc(email).replace(/'/g,"\\'").replace(/"/g,'\\"')}')">Remove</button>
        </td>
      </tr>`).join('');
    } catch (e) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="2">Error loading subscribers.</td></tr>';
    }
  }

  async function addSubscriber() {
    const input = $('add-sub-input');
    const msg   = $('add-sub-msg');
    const email = input.value.trim();
    msg.textContent = '';
    if (!email) { msg.style.color = 'var(--red)'; msg.textContent = 'Please enter an email address.'; return; }
    try {
      const res = await apiFetch('/emails', { method: 'POST', body: JSON.stringify({ email }) });
      if (res.status === 409) { msg.style.color = 'var(--red)'; msg.textContent = 'Already subscribed.'; return; }
      if (!res.ok) { msg.style.color = 'var(--red)'; msg.textContent = 'Failed — check the address.'; return; }
      msg.style.color = 'var(--green)';
      msg.textContent = '✓ ' + email + ' added. Welcome email sent.';
      input.value = '';
      loadSubscribers(); loadStatus();
      setTimeout(() => { msg.textContent = ''; }, 5000);
    } catch (e) { msg.style.color = 'var(--red)'; msg.textContent = 'Network error. Try again.'; }
  }

  async function removeSubscriber(email) {
    if (!confirm('Remove ' + email + ' from the mailing list?')) return;
    try {
      const res = await apiFetch('/emails/' + encodeURIComponent(email), { method: 'DELETE' });
      if (!res.ok) { alert('Failed to remove subscriber.'); return; }
      loadSubscribers(); loadStatus();
    } catch (e) { alert('Network error. Try again.'); }
  }

  // ── Audience Topics ───────────────────────────────────────
  const TOPIC_STATUS_META = {
    featured:  { label: 'Featured',  color: 'var(--gold)' },
    approved:  { label: 'Approved',  color: 'var(--green)' },
    suggested: { label: 'Requested', color: '#e0a23c' },
    archived:  { label: 'Archived',  color: 'var(--muted)' },
  };

  let _adminTopics = [];

  async function loadAdminTopics() {
    const tbody = $('topic-table-body');
    tbody.innerHTML = '<tr class="empty-row"><td colspan="4">Loading…</td></tr>';
    try {
      const res = await apiFetch('/topics/all');
      if (!res.ok) { tbody.innerHTML = '<tr class="empty-row"><td colspan="4">Failed to load.</td></tr>'; return; }
      const { topics, count } = await res.json();
      $('topic-count-display').textContent = count;
      _adminTopics = topics || [];
      renderAdminTopics();
    } catch (e) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="4">Error loading topics.</td></tr>';
    }
  }

  function renderAdminTopics() {
    const tbody = $('topic-table-body');
    const topics = _adminTopics;
    if (!topics.length) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="4">No topics yet.</td></tr>';
      return;
    }
    tbody.innerHTML = topics.map((t, i) => {
      const meta = TOPIC_STATUS_META[t.status] || { label: t.status, color: 'var(--muted)' };
      const desc = t.description ? '<div style="font-size:12px;color:var(--muted);margin-top:3px">' + esc(t.description) + '</div>' : '';
      const src  = t.source === 'visitor' ? ' <span style="font-size:11px;color:var(--muted)">· visitor request</span>' : '';
      const trend = t.trending ? ' <span style="font-size:11px;color:var(--gold);font-weight:700">🔥 Trending</span>' : '';
      const up   = '<button class="btn btn-secondary btn-sm" onclick="moveTopic(' + t.id + ',-1)"' + (i === 0 ? ' disabled' : '') + ' title="Move up">↑</button> ';
      const down = '<button class="btn btn-secondary btn-sm" onclick="moveTopic(' + t.id + ',1)"' + (i === topics.length - 1 ? ' disabled' : '') + ' title="Move down">↓</button> ';
      return '<tr>' +
        '<td><div style="font-weight:600">' + esc(t.title) + src + trend + '</div>' + desc + '</td>' +
        '<td style="text-align:center;font-weight:700">' + (t.votes || 0) + '</td>' +
        '<td style="text-align:center"><span style="color:' + meta.color + ';font-weight:600;font-size:12px">' + meta.label + '</span></td>' +
        '<td style="text-align:right;white-space:nowrap">' +
          up + down +
          (t.status !== 'featured'  ? '<button class="btn btn-secondary btn-sm" onclick="setTopicStatus(' + t.id + ', &quot;featured&quot;)">Feature</button> ' : '') +
          (t.status !== 'approved'  ? '<button class="btn btn-secondary btn-sm" onclick="setTopicStatus(' + t.id + ', &quot;approved&quot;)">Approve</button> ' : '') +
          (t.status !== 'archived'  ? '<button class="btn btn-secondary btn-sm" onclick="setTopicStatus(' + t.id + ', &quot;archived&quot;)">Archive</button> ' : '') +
          '<button class="btn btn-danger btn-sm" onclick="deleteAdminTopic(' + t.id + ')">Delete</button>' +
        '</td>' +
      '</tr>';
    }).join('');
  }

  async function moveTopic(id, dir) {
    const idx = _adminTopics.findIndex(t => t.id === id);
    if (idx < 0) return;
    const j = idx + dir;
    if (j < 0 || j >= _adminTopics.length) return;
    const a = _adminTopics[idx]; _adminTopics[idx] = _adminTopics[j]; _adminTopics[j] = a;
    renderAdminTopics();
    try {
      await apiFetch('/topics/reorder', {
        method: 'POST',
        body: JSON.stringify({ ordered_ids: _adminTopics.map(t => t.id) }),
      });
    } catch (e) { /* order will re-sync on next reload */ }
  }

  async function createAdminTopic() {
    const title  = $('topic-add-title').value.trim();
    const desc   = $('topic-add-desc').value.trim();
    const status = $('topic-add-status').value;
    if (title.length < 3) { showBar('topic-add-status-bar', 'Please enter a topic title.', 'error'); return; }
    try {
      const res = await apiFetch('/topics', {
        method: 'POST',
        body: JSON.stringify({ title, description: desc || null, status }),
      });
      if (!res.ok) { showBar('topic-add-status-bar', 'Failed to add topic.', 'error'); return; }
      showBar('topic-add-status-bar', '✓ Topic added.', 'success');
      $('topic-add-title').value = ''; $('topic-add-desc').value = '';
      loadAdminTopics();
      setTimeout(() => { const b = $('topic-add-status-bar'); if (b) b.className = 'status-bar'; }, 4000);
    } catch (e) { showBar('topic-add-status-bar', 'Network error. Try again.', 'error'); }
  }

  async function setTopicStatus(id, status) {
    try {
      const res = await apiFetch('/topics/' + id, { method: 'PATCH', body: JSON.stringify({ status }) });
      if (!res.ok) { alert('Failed to update topic.'); return; }
      loadAdminTopics();
    } catch (e) { alert('Network error. Try again.'); }
  }

  async function deleteAdminTopic(id) {
    if (!confirm('Delete this topic and all its votes? This cannot be undone.')) return;
    try {
      const res = await apiFetch('/topics/' + id, { method: 'DELETE' });
      if (!res.ok) { alert('Failed to delete topic.'); return; }
      loadAdminTopics();
    } catch (e) { alert('Network error. Try again.'); }
  }

  // ── Content Hub: featured content ─────────────────────────
  function _parseShorts(text) {
    return text.split('\\n').map(l => l.trim()).filter(Boolean).map(l => {
      const parts = l.split('|');
      return { id: (parts[0] || '').trim(), title: parts.slice(1).join('|').trim() };
    }).filter(s => s.id);
  }
  function _parsePlaylists(text) {
    return text.split('\\n').map(l => l.trim()).filter(Boolean).map(l => {
      const parts = l.split('|');
      if (parts.length >= 2) return { title: parts[0].trim(), url: parts.slice(1).join('|').trim() };
      return { title: '', url: parts[0].trim() };
    }).filter(p => p.url);
  }

  async function loadFeaturedAdmin() {
    try {
      const res = await apiFetch('/featured-content');
      if (!res.ok) return;
      const d = await res.json();
      $('fc-shorts').value = (d.shorts || []).map(s => s.title ? (s.id + ' | ' + s.title) : s.id).join('\\n');
      $('fc-playlists').value = (d.playlists || []).map(p => (p.title ? (p.title + ' | ') : '') + p.url).join('\\n');
      $('fc-community').value = d.community_url || '';
    } catch (e) { /* leave fields as-is */ }
  }

  async function saveFeaturedAdmin() {
    const body = {
      shorts: _parseShorts($('fc-shorts').value),
      playlists: _parsePlaylists($('fc-playlists').value),
      community_url: $('fc-community').value.trim(),
    };
    try {
      const res = await apiFetch('/featured-content', { method: 'PUT', body: JSON.stringify(body) });
      if (!res.ok) { showBar('fc-status-bar', 'Failed to save featured content.', 'error'); return; }
      showBar('fc-status-bar', '✓ Featured content saved — it is now live on the landing page.', 'success');
      loadFeaturedAdmin();
      setTimeout(() => { const b = $('fc-status-bar'); if (b) b.className = 'status-bar'; }, 4000);
    } catch (e) { showBar('fc-status-bar', 'Network error. Try again.', 'error'); }
  }

  // ── Content Hub: Catholic news ────────────────────────────
  async function loadNews() {
    const box = $('news-list');
    if (!box) return;
    box.innerHTML = '<div class="empty-row">Loading…</div>';
    try {
      const res = await apiFetch('/news');
      if (!res.ok) { box.innerHTML = '<div class="empty-row">Failed to load news.</div>'; return; }
      const d = await res.json();
      const items = d.headlines || [];
      if (!items.length) {
        box.innerHTML = '<div class="empty-row">' + esc(d.note || 'No headlines available right now.') + '</div>';
        return;
      }
      const note = d.note ? '<div style="color:var(--muted);font-size:12px;margin-bottom:10px">' + esc(d.note) + '</div>' : '';
      const safeHttp = (u) => /^https?:\/\//i.test(String(u || ''));
      box.innerHTML = note + items.map(h => {
        const title = esc(h.title);
        // Only make the headline clickable when the link is a real http(s) URL —
        // never trust an upstream feed to supply a safe scheme (no javascript:/data:).
        const titleHtml = safeHttp(h.link)
          ? '<a href="' + esc(h.link) + '" target="_blank" rel="noopener" style="color:var(--text);text-decoration:none;font-weight:600">' + title + '</a>'
          : '<span style="color:var(--text);font-weight:600">' + title + '</span>';
        return '<div style="padding:10px 0;border-bottom:1px solid var(--border)">' +
            titleHtml +
            '<div style="font-size:12px;color:var(--muted);margin-top:2px">' + esc(h.source || '') + (h.published ? ' · ' + esc(h.published) : '') + '</div>' +
          '</div>';
      }).join('');
    } catch (e) { box.innerHTML = '<div class="empty-row">Network error loading news.</div>'; }
  }

  async function refreshNews() {
    const box = $('news-list');
    if (box) box.innerHTML = '<div class="empty-row">Refreshing…</div>';
    try { await apiFetch('/news/refresh', { method: 'POST' }); } catch (e) { /* fall through to reload */ }
    loadNews();
  }

  // ── Newsletter ────────────────────────────────────────────
  async function sendNewsletter() {
    const subject = $('nl-subject').value.trim();
    const body    = $('nl-body').value.trim();
    if (!subject || !body) { showBar('nl-send-status', 'Please fill in both fields.', 'error'); return; }
    const btn = $('nl-send-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Sending…';
    try {
      const res = await apiFetch('/send-newsletter/custom?force=true', {
        method: 'POST', body: JSON.stringify({ subject, body }),
      });
      const d = await res.json().catch(() => ({}));
      const when = new Date().toLocaleString();
      if (!res.ok) {
        const detail = aiErrText(d, JSON.stringify(d));
        showBar('nl-send-status', 'Send failed (HTTP ' + res.status + '): ' + detail, 'error');
        toast('Email failed — HTTP ' + res.status, '⚠');
        console.error('[GrowthLoop] Newsletter send failed:', res.status, d);
      } else if (d.status === 'success') {
        console.log('[GrowthLoop] Newsletter sent to ' + d.sent + ' subscriber(s) at ' + when + ':', subject);
        const hhmm = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        showBar('nl-send-status', '✓ Email sent successfully — ' + d.sent + ' of ' + (d.recipients_total != null ? d.recipients_total : d.sent) + ' recipient' + (d.sent !== 1 ? 's' : '') + ' · ' + when, 'success');
        toast('Email sent to ' + d.sent + ' recipient' + (d.sent !== 1 ? 's' : '') + ' at ' + hhmm, '✉');
        $('nl-subject').value = ''; $('nl-body').value = '';
        loadHistory(); loadStatus();
      } else if (d.status === 'partial') {
        showBar('nl-send-status', 'Partial send — ' + d.sent + ' sent, ' + d.failed + ' failed · ' + when, 'error');
        toast(d.failed + ' email' + (d.failed !== 1 ? 's' : '') + ' failed', '⚠');
        loadHistory();
      } else {
        showBar('nl-send-status', d.detail || d.reason || 'Skipped.', 'error');
      }
    } catch (e) {
      console.error('[GrowthLoop] Newsletter send network error:', e);
      showBar('nl-send-status', 'Something went wrong. Try again.', 'error');
      toast('Something went wrong. Try again.', '⚠');
    }
    finally { btn.disabled = false; btn.textContent = 'Send to All'; }
  }

  async function previewNewsletter() {
    const subject = $('nl-subject').value.trim();
    const body    = $('nl-body').value.trim();
    if (!subject && !body) {
      console.warn('[GrowthLoop] Preview requested with no content.');
      showBar('nl-send-status', 'No content to preview — write a subject and message first.', 'error');
      toast('No content to preview', '⚠');
      return;
    }
    await doPreview(subject || 'Odili — The Seeker of Truth', body || 'Write your message above — each line becomes a paragraph.', 'nl-send-status');
  }

  // Step 4: generate a "Your Weekly Catholic Content Plan" email via AI and
  // drop it into the composer, then auto-open the branded preview.
  async function generateWeeklyEmail() {
    const btn = $('nl-weekly-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Generating…';
    try {
      const res = await apiFetch('/newsletter/weekly/generate', {
        method: 'POST', body: JSON.stringify({ topics: [] }),
      });
      const d = await res.json().catch(() => ({}));
      if (!res.ok || !d.body) {
        const msg = d.detail
          ? (typeof d.detail === 'string' ? d.detail : (d.detail.message || JSON.stringify(d.detail)))
          : ('Weekly plan failed (HTTP ' + res.status + ').');
        showBar('nl-send-status', msg, 'error');
        return;
      }
      $('nl-subject').value = d.subject;
      $('nl-body').value = d.body;
      console.log('[GrowthLoop] Weekly content plan generated.');
      doPreview(d.subject, d.body, 'nl-send-status');
      toast('Weekly plan ready — preview opened.', '✨');
    } catch (e) {
      showBar('nl-send-status', 'Network error generating weekly plan.', 'error');
    } finally {
      btn.disabled = false; btn.innerHTML = '✨ Weekly Plan';
    }
  }

  async function doPreview(subject, body, statusId) {
    console.log('[GrowthLoop] Preview payload:', { subject, body });
    if (!subject && !body) {
      showBar(statusId, 'No content to preview.', 'error');
      return;
    }
    try {
      const res = await apiFetch('/send-newsletter/custom/preview', {
        method: 'POST', body: JSON.stringify({ subject, body }),
      });
      const d = await res.json().catch(() => ({}));
      if (!res.ok || !d.html) {
        console.error('[GrowthLoop] Preview render failed:', res.status, d);
        const msg = d.detail
          ? (typeof d.detail === 'string' ? d.detail : JSON.stringify(d.detail))
          : ('Preview failed (HTTP ' + res.status + ').');
        showBar(statusId, msg, 'error');
        return;
      }
      $('preview-frame').srcdoc = d.html;
      $('preview-modal').classList.add('open');
    } catch (e) { showBar(statusId, 'Could not generate preview.', 'error'); }
  }

  function closePreview() {
    $('preview-modal').classList.remove('open');
    $('preview-frame').srcdoc = '';
  }

  // ── Export ────────────────────────────────────────────────
  function exportCSV() {
    apiFetch('/subscribers/export')
      .then(r => r.blob())
      .then(blob => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'subscribers.csv';
        document.body.appendChild(a); a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
      })
      .catch(() => alert('Export failed. Please try again.'));
  }

  // ── Toast ────────────────────────────────────────────────
  let _toastTimer = null;
  function toast(msg, emoji) {
    const el = $('toast');
    el.textContent = (emoji ? emoji + '  ' : '') + msg;
    el.classList.add('show');
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(() => el.classList.remove('show'), 3000);
  }

  // ── YouTube Intelligence ──────────────────────────────────
  async function loadYoutube(force) {
    if (_ytData && !force) { renderYoutube(_ytData); return; }
    const el = $('yt-content');
    el.innerHTML = '<div class="loader-overlay"><div class="loader-spinner"></div><span>Fetching channel data and running AI analysis… this may take 15–30 seconds.</span></div>';
    try {
      const res = await apiFetch('/youtube/intelligence' + (force ? '?refresh=true' : ''));
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        el.innerHTML = `<div class="loader-overlay" style="color:var(--red)">
          <span style="font-size:32px">⚠</span>
          <strong>${esc(d.detail || 'Failed to load YouTube intelligence.')}</strong>
          <span style="font-size:12px;text-align:center;max-width:460px;color:var(--muted)">
            Make sure YOUTUBE_API_KEY and YOUTUBE_CHANNEL_ID are set in Replit environment secrets.
          </span>
        </div>`;
        return;
      }
      _ytData = await res.json();
      renderYoutube(_ytData);
    } catch (e) {
      el.innerHTML = '<div class="loader-overlay" style="color:var(--red)"><span style="font-size:32px">⚠</span><strong>Network error — could not reach the server.</strong></div>';
    }
  }

  // ── Script modal ──────────────────────────────────────────
  let _currentScript = null;

  function _showScriptModal(title) {
    $('smodal-title').textContent = title || 'Generating…';
    $('smodal-loading').style.display = 'flex';
    $('smodal-content').style.display = 'none';
    $('smodal-error').style.display = 'none';
    $('smodal-copy-btn').style.display = 'none';
    $('smodal-send-btn').style.display = 'none';
    $('smodal-ytpost-btn').style.display = 'none';
    $('smodal-shorts-btn').style.display = 'none';
    $('smodal-pkg-send-btn').style.display = 'none';
    $('smodal-save-btn').style.display = 'none';
    $('smodal-ytpkg-btn').style.display = 'none';
    $('smodal-optimize-btn').style.display = 'none';
    $('smodal-viral-btn').style.display = 'none';
    $('smodal-viral-section').style.display = 'none';
    $('smodal-viral-loading').style.display = 'none';
    $('smodal-viral-content').style.display = 'none';
    $('smodal-yt-section').style.display = 'none';
    $('smodal-yt-loading').style.display = 'none';
    $('smodal-yt-content').style.display = 'none';
    $('smodal-opt-section').style.display = 'none';
    $('smodal-opt-loading').style.display = 'none';
    $('smodal-opt-content').style.display = 'none';
    $('smodal-apply-btn').style.display = 'none';
    $('smodal-reuse-section').style.display = 'none';
    $('script-modal').classList.add('open');
  }

  function _showScriptResult(data) {
    $('smodal-title').textContent = data.title;
    $('smodal-hook').textContent = data.hook;
    $('smodal-script').textContent = data.script;
    $('smodal-loading').style.display = 'none';
    $('smodal-content').style.display = 'block';
    $('smodal-copy-btn').style.display = '';
    $('smodal-send-btn').style.display = '';
    $('smodal-ytpost-btn').style.display = '';
    $('smodal-shorts-btn').style.display = '';
    $('smodal-save-btn').style.display = '';
    $('smodal-ytpkg-btn').style.display = '';
    $('smodal-optimize-btn').style.display = '';
    $('smodal-viral-btn').style.display = '';
  }

  function _showScriptError(msg) {
    $('smodal-loading').style.display = 'none';
    $('smodal-error').textContent = msg;
    $('smodal-error').style.display = 'block';
  }

  async function ytGenerateScript(topic) {
    _currentScript = null;
    _showScriptModal('Generating…');
    try {
      const res = await apiFetch('/generate-idea', {
        method: 'POST',
        body: JSON.stringify({ topic }),
      });
      const d = await res.json();
      if (!res.ok) {
        _showScriptError((d.detail?.message || d.detail || 'Generation failed. Check OpenAI quota.'));
        return;
      }
      _currentScript = {
        topic,
        title: d.viral_title || topic,
        hook: d.hook || '',
        script: d.short_script || '',
      };
      _showScriptResult(_currentScript);
    } catch (e) {
      _showScriptError('Network error — could not reach the server.');
    }
  }

  function closeScriptModal() {
    $('script-modal').classList.remove('open');
  }

  function modalCopyScript() {
    if (!_currentScript) return;
    const text = 'Title: ' + _currentScript.title +
      '\\n\\nHook: ' + _currentScript.hook +
      '\\n\\nScript:\\n' + _currentScript.script;
    navigator.clipboard.writeText(text).then(() => toast('Script copied to clipboard.', '✓'));
  }

  // ── Content Reuse (Turn script into YouTube Post / Shorts Idea) ──
  let _reuseText = '';
  const _REUSE_LABELS = { youtube_post: '📢 YouTube Community Post', shorts: '⚡ Shorts Idea' };

  async function repurposeCurrent(fmt) {
    if (!_currentScript) return;
    const btnId = fmt === 'shorts' ? 'smodal-shorts-btn' : 'smodal-ytpost-btn';
    const btn = $(btnId);
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Working…';
    $('smodal-reuse-section').style.display = 'block';
    $('smodal-reuse-loading').style.display = 'flex';
    $('smodal-reuse-content').textContent = '';
    $('smodal-reuse-label').textContent = _REUSE_LABELS[fmt] || 'Repurposed Content';
    try {
      const res = await apiFetch('/growth/repurpose', {
        method: 'POST',
        body: JSON.stringify({
          format: fmt,
          title: _currentScript.title,
          hook: _currentScript.hook,
          script: _currentScript.script,
        }),
      });
      const d = await res.json();
      $('smodal-reuse-loading').style.display = 'none';
      if (!res.ok) { $('smodal-reuse-content').textContent = aiErrText(d, 'Could not repurpose this script.'); _reuseText = ''; return; }
      if (fmt === 'shorts') {
        _reuseText = 'Title: ' + (d.title || '') + '\\n\\nHook: ' + (d.hook || '') +
          '\\n\\nScript:\\n' + (d.script || '') + '\\n\\nCaption: ' + (d.caption || '');
      } else {
        _reuseText = d.content || '';
      }
      $('smodal-reuse-content').textContent = _reuseText;
      console.log('[GrowthLoop] Script repurposed →', fmt, ':', _currentScript.title);
    } catch (e) {
      $('smodal-reuse-loading').style.display = 'none';
      $('smodal-reuse-content').textContent = 'Network error — could not reach the server.';
      _reuseText = '';
    } finally {
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  }

  function copyReuse() {
    if (!_reuseText) { toast('Nothing to copy yet.', '⚠'); return; }
    navigator.clipboard.writeText(_reuseText).then(() => toast('Repurposed content copied.', '✓'));
  }

  // Build a newsletter body from content parts, appending the YouTube growth CTA.
  // The Growth Engine CTA is added automatically by the branded email template.
  function buildNewsletterBody(hook, summary) {
    let body = '';
    if (hook) body += hook.trim() + '\\n\\n';
    if (summary) body += summary.trim() + '\\n\\n';
    if (_ytChannelUrl) {
      body += 'Watch the full video on YouTube: ' + _ytChannelUrl + '\\n\\n';
    }
    body += 'Keep seeking the truth — and share it with someone today.';
    return body.trim();
  }

  function modalSendToNewsletter() {
    if (!_currentScript) return;
    const subject = _currentScript.title;
    const body = buildNewsletterBody(_currentScript.hook, _currentScript.script);
    closeScriptModal();
    navigate('newsletter');
    setTimeout(() => {
      $('nl-subject').value = subject;
      $('nl-body').value = body;
      console.log('[GrowthLoop] Script → Newsletter editor:', subject);
      // Step 3: auto-open the branded preview so the loop is visible immediately.
      doPreview(subject, body, 'nl-send-status');
    }, 80);
    toast('Script loaded — preview opened.', '✉');
  }

  // Step 3: send a generated YouTube package straight into the newsletter loop.
  function pkgSendToNewsletter() {
    const title = $('yt-pkg-title')?.textContent?.trim();
    const desc  = $('yt-pkg-desc')?.textContent?.trim();
    if (!title) { toast('Generate a YouTube package first.', '⚠'); return; }
    const subject = title;
    const body = buildNewsletterBody('', desc);
    closeScriptModal();
    navigate('newsletter');
    setTimeout(() => {
      $('nl-subject').value = subject;
      $('nl-body').value = body;
      console.log('[GrowthLoop] YouTube package → Newsletter editor:', subject);
      doPreview(subject, body, 'nl-send-status');
    }, 80);
    toast('Package loaded — preview opened.', '✉');
  }

  async function modalSaveForLater() {
    if (!_currentScript) return;
    const btn = $('smodal-save-btn');
    btn.disabled = true;
    btn.textContent = 'Saving…';
    try {
      const res = await apiFetch('/scripts', {
        method: 'POST',
        body: JSON.stringify(_currentScript),
      });
      if (!res.ok) {
        toast('Failed to save script.', '⚠');
        btn.disabled = false; btn.textContent = 'Save for Later';
        return;
      }
      btn.textContent = 'Saved ✓';
      toast('Script saved to Saved Scripts.', '💾');
    } catch (e) {
      toast('Network error saving script.', '⚠');
      btn.disabled = false; btn.textContent = 'Save for Later';
    }
  }

  // ── Saved Scripts ──────────────────────────────────────────
  async function loadSavedScripts() {
    const el = $('saved-scripts-list');
    el.innerHTML = '<div class="loader-overlay"><div class="loader-spinner"></div><span>Loading saved scripts…</span></div>';
    try {
      const res = await apiFetch('/scripts');
      if (!res.ok) {
        el.innerHTML = '<div class="loader-overlay" style="color:var(--red)">Failed to load scripts.</div>';
        return;
      }
      const { scripts } = await res.json();
      window._savedScripts = scripts;
      if (!scripts.length) {
        el.innerHTML = '<div class="loader-overlay"><span style="color:var(--muted)">No saved scripts yet. Generate a script from YouTube Intelligence and click "Save for Later".</span></div>';
        return;
      }
      el.innerHTML = scripts.map(s => `
        <div class="card" style="margin-bottom:16px" id="script-card-${s.id}">
          <div class="card-header">
            <div class="card-header-left" style="flex-direction:column;align-items:flex-start;gap:4px;overflow:hidden">
              <div class="card-title" style="color:var(--gold)">${esc(s.title)}</div>
              <div style="font-size:11px;color:var(--muted)">Topic: ${esc(s.topic)} &middot; ${fmtDate(s.created_at)}</div>
            </div>
            <div class="btn-row" style="flex-shrink:0;gap:6px">
              <button class="btn btn-secondary btn-sm" onclick="viewSavedScript(${s.id})">View</button>
              <button class="btn btn-secondary btn-sm" onclick="copySavedScript(${s.id})">Copy</button>
              <button class="btn btn-secondary btn-sm" style="color:var(--red);border-color:var(--red)" onclick="deleteSavedScript(${s.id})">Delete</button>
            </div>
          </div>
          <div class="card-body" style="padding-top:8px;padding-bottom:14px">
            <div style="font-size:13px;color:var(--muted);line-height:1.55;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${esc(s.hook)}</div>
          </div>
        </div>`).join('');
    } catch (e) {
      el.innerHTML = '<div class="loader-overlay" style="color:var(--red)">Error loading saved scripts.</div>';
    }
  }

  function viewSavedScript(id) {
    const s = (window._savedScripts || []).find(x => x.id === id);
    if (!s) return;
    _currentScript = { topic: s.topic, title: s.title, hook: s.hook, script: s.script };
    _showScriptModal(s.title);
    _showScriptResult(_currentScript);
  }

  function copySavedScript(id) {
    const s = (window._savedScripts || []).find(x => x.id === id);
    if (!s) return;
    const text = 'Title: ' + s.title + '\\n\\nHook: ' + s.hook + '\\n\\nScript:\\n' + s.script;
    navigator.clipboard.writeText(text).then(() => toast('Script copied to clipboard.', '✓'));
  }

  async function deleteSavedScript(id) {
    if (!confirm('Delete this saved script?')) return;
    try {
      const res = await apiFetch('/scripts/' + id, { method: 'DELETE' });
      if (!res.ok) { toast('Failed to delete script.', '⚠'); return; }
      document.getElementById('script-card-' + id)?.remove();
      if (window._savedScripts) window._savedScripts = window._savedScripts.filter(x => x.id !== id);
      const remaining = $('saved-scripts-list').querySelectorAll('.card').length;
      if (!remaining) {
        $('saved-scripts-list').innerHTML = '<div class="loader-overlay"><span style="color:var(--muted)">No saved scripts yet. Generate a script from YouTube Intelligence and click "Save for Later".</span></div>';
      }
      toast('Script deleted.', '✓');
    } catch (e) { toast('Network error.', '⚠'); }
  }

  // ── YouTube Package generation ─────────────────────────────
  async function generateYouTubePackage() {
    if (!_currentScript) return;
    const btn = $('smodal-ytpkg-btn');
    btn.disabled = true;
    btn.textContent = 'Generating…';

    $('smodal-yt-section').style.display = 'block';
    $('smodal-yt-loading').style.display = 'flex';
    $('smodal-yt-content').style.display = 'none';
    setTimeout(() => { $('smodal-body').scrollTop = $('smodal-body').scrollHeight; }, 50);

    try {
      const res = await apiFetch('/youtube-packages/generate', {
        method: 'POST',
        body: JSON.stringify({
          script_id: null,
          title: _currentScript.title,
          hook: _currentScript.hook,
          script: _currentScript.script,
        }),
      });
      const d = await res.json();
      if (!res.ok) {
        $('smodal-yt-loading').style.display = 'none';
        const errEl = document.createElement('div');
        errEl.style.cssText = 'color:var(--red);padding:12px;font-size:13px';
        errEl.textContent = d.detail?.message || d.detail || 'Generation failed.';
        $('smodal-yt-section').appendChild(errEl);
        btn.disabled = false; btn.textContent = '▶ YT Package';
        return;
      }
      $('yt-pkg-title').textContent = d.title;
      $('yt-pkg-desc').textContent = d.description;
      $('yt-pkg-tags').textContent = d.tags;
      $('yt-pkg-thumb').textContent = d.thumbnail_text;
      $('smodal-yt-loading').style.display = 'none';
      $('smodal-yt-content').style.display = 'block';
      $('smodal-pkg-send-btn').style.display = '';
      btn.disabled = false; btn.textContent = '↺ Regenerate';
      toast('YouTube package generated!', '🎬');
      setTimeout(() => { $('smodal-body').scrollTop = $('smodal-body').scrollHeight; }, 100);
    } catch (e) {
      $('smodal-yt-loading').style.display = 'none';
      btn.disabled = false; btn.textContent = '▶ YT Package';
      toast('Network error generating package.', '⚠');
    }
  }

  function ytPkgCopy(fieldId) {
    const text = $(fieldId)?.textContent || '';
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => toast('Copied to clipboard.', '✓'));
  }

  // ── YouTube Studio Optimization (publishing blueprint) ──
  let _optStrategy = null;

  const _OPT_TIPS = {
    posting_time: 'Upload (or schedule) at this UTC window — derived from when your best videos went live.',
    category: 'Education tells YouTube to surface this to learners and faith-seekers.',
    audience: 'Select "No, it\\'s not made for kids" — required, and keeps comments + notifications on.',
    visibility: 'Public maximises reach. Use Unlisted only for previews.',
    language: 'Set the video language so captions and search work correctly.',
    captions: 'Captions boost watch-time, accessibility, and search ranking.',
    playlist: 'Add to this playlist so binge-watching lifts session time.',
    title_style: 'Front-load the curiosity gap; keep it 8-11 words.',
    thumbnail_style: 'High contrast + a few bold words wins the click.',
    tags: 'Paste these into the Tags field to reinforce topic relevance.',
    description_structure: 'Follow this order in your description for retention + SEO.',
    advanced: 'Leave these ON so comments, embeds and subscriber alerts all fire.',
  };

  function _optRow(label, value, tipKey) {
    return '<div style="display:flex;justify-content:space-between;gap:14px;padding:9px 0;border-bottom:1px solid var(--border)">' +
      '<span title="' + esc(_OPT_TIPS[tipKey] || '') + '" style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;cursor:help;white-space:nowrap">' + esc(label) + '</span>' +
      '<span style="font-size:13px;color:var(--text);text-align:right">' + esc(value) + '</span></div>';
  }

  function _renderOptimization(d) {
    const tags = Array.isArray(d.tags) ? d.tags : [];
    const desc = Array.isArray(d.description_structure) ? d.description_structure : [];
    const adv = d.advanced_settings || {};
    const advOn = Object.keys(adv).filter(k => adv[k] === true)
      .map(k => k.replace(/_/g, ' ')).join(', ');
    let html = '';
    html += _optRow('Best posting time', d.posting_time || '—', 'posting_time');
    html += _optRow('Category', d.category || '—', 'category');
    html += _optRow('Audience', d.audience || '—', 'audience');
    html += _optRow('Visibility', d.visibility || '—', 'visibility');
    html += _optRow('Language', d.language || '—', 'language');
    html += _optRow('Captions', d.captions || '—', 'captions');
    html += _optRow('Playlist', d.playlist || '—', 'playlist');
    html += _optRow('Title style', d.title_style || '—', 'title_style');
    html += _optRow('Thumbnail', d.thumbnail_style || '—', 'thumbnail_style');

    // Thumbnail psychology block (P3).
    const tp = d.thumbnail_psychology || null;
    if (tp) {
      const examples = Array.isArray(tp.example_texts) ? tp.example_texts : [];
      html += '<div style="padding:12px 0;border-bottom:1px solid var(--border)">' +
        '<div title="The emotion + face + bold text combination that wins the click." style="font-size:11px;font-weight:700;color:var(--gold);text-transform:uppercase;letter-spacing:.5px;cursor:help;margin-bottom:8px">🧠 Thumbnail psychology</div>' +
        '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px">' +
        '<span style="font-size:11px;color:var(--text);background:var(--bg);padding:4px 9px;border-radius:6px;border:1px solid var(--border)">Emotion: <b>' + esc(tp.emotion || '—') + '</b></span>' +
        '<span style="font-size:11px;color:var(--text);background:var(--bg);padding:4px 9px;border-radius:6px;border:1px solid var(--border)">Face: <b>' + esc(tp.face_expression || '—') + '</b></span>' +
        '<span style="font-size:11px;color:var(--text);background:var(--bg);padding:4px 9px;border-radius:6px;border:1px solid var(--border)">Contrast: <b>' + esc(tp.contrast || '—') + '</b></span>' +
        '</div>' +
        '<div style="font-size:12.5px;color:var(--text);margin-bottom:8px">On-thumbnail text: <b style="color:var(--gold)">' + esc(tp.text || '—') + '</b></div>' +
        (examples.length ? '<div style="display:flex;flex-wrap:wrap;gap:6px">' +
          examples.map(t => '<span style="font-size:11px;color:var(--text);background:var(--bg);padding:4px 9px;border-radius:6px;border:1px solid var(--border)">' + esc(t) + '</span>').join('') +
          '</div>' : '') +
        '</div>';
    }

    // Tags block with copy button.
    html += '<div style="padding:12px 0;border-bottom:1px solid var(--border)">' +
      '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">' +
      '<span title="' + esc(_OPT_TIPS.tags) + '" style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;cursor:help">Tags</span>' +
      '<button class="btn btn-secondary btn-sm" onclick="copyOptTags()">Copy tags</button></div>' +
      '<div style="display:flex;flex-wrap:wrap;gap:6px">' +
      tags.map(t => '<span style="font-size:11px;color:var(--text);background:var(--bg);padding:4px 9px;border-radius:6px;border:1px solid var(--border)">' + esc(t) + '</span>').join('') +
      '</div></div>';

    // Description structure checklist.
    html += '<div style="padding:12px 0;border-bottom:1px solid var(--border)">' +
      '<div title="' + esc(_OPT_TIPS.description_structure) + '" style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;cursor:help;margin-bottom:8px">Description structure</div>' +
      '<ol style="margin:0;padding-left:18px;color:var(--text);font-size:12.5px;line-height:1.9">' +
      desc.map(s => '<li>' + esc(s) + '</li>').join('') + '</ol></div>';

    // Advanced settings.
    html += _optRow('Advanced (keep ON)', advOn || '—', 'advanced');

    $('smodal-opt-content').innerHTML = html;
  }

  async function optimizeCurrent() {
    if (!_currentScript) return;
    const btn = $('smodal-optimize-btn');
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Optimizing…';
    $('smodal-opt-section').style.display = 'block';
    $('smodal-opt-loading').style.display = 'flex';
    $('smodal-opt-content').style.display = 'none';
    $('smodal-apply-btn').style.display = 'none';
    setTimeout(() => { $('smodal-body').scrollTop = $('smodal-body').scrollHeight; }, 50);
    try {
      const res = await apiFetch('/youtube/optimize', {
        method: 'POST',
        body: JSON.stringify({
          title: _currentScript.title,
          topic: _currentScript.topic || _currentScript.title,
          script: _currentScript.script,
        }),
      });
      const d = await res.json();
      $('smodal-opt-loading').style.display = 'none';
      if (!res.ok) {
        $('smodal-opt-content').innerHTML = '<div style="color:var(--red);font-size:13px">' +
          esc(aiErrText(d, 'Could not build the optimization strategy.')) + '</div>';
        $('smodal-opt-content').style.display = 'block';
        _optStrategy = null;
        return;
      }
      _optStrategy = d;
      _renderOptimization(d);
      $('smodal-opt-content').style.display = 'block';
      $('smodal-apply-btn').style.display = '';
      console.log('[GrowthLoop] Optimization built for:', _currentScript.title);
      toast('Publishing blueprint ready.', '🎯');
      setTimeout(() => { $('smodal-body').scrollTop = $('smodal-body').scrollHeight; }, 100);
    } catch (e) {
      $('smodal-opt-loading').style.display = 'none';
      $('smodal-opt-content').innerHTML = '<div style="color:var(--red);font-size:13px">Network error — could not reach the server.</div>';
      $('smodal-opt-content').style.display = 'block';
      _optStrategy = null;
    } finally {
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  }

  function copyOptTags() {
    if (!_optStrategy || !Array.isArray(_optStrategy.tags)) { toast('Nothing to copy yet.', '⚠'); return; }
    navigator.clipboard.writeText(_optStrategy.tags.join(', ')).then(() => toast('Tags copied.', '✓'));
  }

  let _viralResult = null;

  function _scoreColor(n) {
    n = Number(n) || 0;
    if (n >= 70) return 'var(--gold)';
    if (n >= 40) return '#e0a800';
    return 'var(--red)';
  }

  function _scoreBar(label, value) {
    const v = Math.max(0, Math.min(100, Number(value) || 0));
    return '<div style="margin-bottom:9px">' +
      '<div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:3px">' +
      '<span>' + esc(label) + '</span><span style="color:' + _scoreColor(v) + ';font-weight:700">' + v + '</span></div>' +
      '<div style="height:6px;background:var(--bg);border-radius:4px;overflow:hidden;border:1px solid var(--border)">' +
      '<div style="height:100%;width:' + v + '%;background:' + _scoreColor(v) + '"></div></div></div>';
  }

  function _renderViral(d) {
    const ts = d.topic_score || {};
    const titles = Array.isArray(d.viral_titles) ? d.viral_titles : [];
    let html = '';

    // Virality score headline.
    html += '<div style="display:flex;align-items:center;gap:14px;margin-bottom:16px">' +
      '<div style="font-size:34px;font-weight:900;color:' + _scoreColor(ts.virality_score) + '">' + (ts.virality_score != null ? ts.virality_score : '—') + '</div>' +
      '<div><div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Virality score</div>' +
      '<div style="font-size:13px;font-weight:700;color:var(--text)">Recommendation: <span style="color:' + _scoreColor(ts.virality_score) + '">' + esc(ts.recommendation || '—') + '</span></div></div></div>';

    // Sub-scores.
    html += '<div style="margin-bottom:16px">' +
      _scoreBar('Curiosity gap', ts.curiosity_gap) +
      _scoreBar('Controversy level', ts.controversy_level) +
      _scoreBar('Emotional trigger', ts.emotional_trigger) +
      _scoreBar('Search demand', ts.search_demand) + '</div>';

    if (ts.improved_angle) {
      html += '<div style="padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px;margin-bottom:16px">' +
        '<div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">💡 Improved angle</div>' +
        '<div style="font-size:13px;color:var(--gold);font-weight:600">' + esc(ts.improved_angle) + '</div></div>';
    }

    // Viral titles.
    if (titles.length) {
      html += '<div style="margin-bottom:16px"><div style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">📝 Viral titles</div>';
      titles.forEach((t, i) => {
        const isBest = t === d.best_title;
        html += '<div style="display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid var(--border)">' +
          '<span style="font-size:13px;color:var(--text);flex:1">' + (isBest ? '⭐ ' : '') + esc(t) + '</span>' +
          '<button class="btn btn-secondary btn-sm" onclick="copyText(' + jsAttr(t) + ', \\'Title\\')">Copy</button></div>';
      });
      html += '</div>';
    }

    // Hook.
    if (d.hook) {
      html += '<div style="padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px;margin-bottom:16px">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">' +
        '<span style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">🎬 Boosted hook' + (d.hook_regenerated ? ' (regenerated)' : '') + '</span>' +
        '<span style="font-size:11px;font-weight:700;color:' + _scoreColor(d.hook_intensity_score) + '">Intensity ' + (d.hook_intensity_score != null ? d.hook_intensity_score : '—') + '</span></div>' +
        '<div style="font-size:13px;color:var(--text)">' + esc(d.hook) + '</div></div>';
    }

    // Reuse the optimization renderer (incl. thumbnail psychology).
    if (d.optimization) {
      html += '<div style="font-size:11px;font-weight:700;color:var(--gold);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">🎯 Publishing blueprint</div>';
      html += '<div id="_viral-opt-mount"></div>';
    }

    $('smodal-viral-content').innerHTML = html;
    if (d.optimization) {
      // Render optimization into a temp node then move it under the mount.
      const prev = $('smodal-opt-content').innerHTML;
      _renderOptimization(d.optimization);
      $('_viral-opt-mount').innerHTML = $('smodal-opt-content').innerHTML;
      $('smodal-opt-content').innerHTML = prev;
    }
  }

  async function makeViralCurrent() {
    if (!_currentScript) return;
    const btn = $('smodal-viral-btn');
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Viralising…';
    $('smodal-viral-section').style.display = 'block';
    $('smodal-viral-loading').style.display = 'flex';
    $('smodal-viral-content').style.display = 'none';
    setTimeout(() => { $('smodal-body').scrollTop = $('smodal-body').scrollHeight; }, 50);
    try {
      const res = await apiFetch('/growth/make-viral', {
        method: 'POST',
        body: JSON.stringify({
          title: _currentScript.title,
          topic: _currentScript.topic || _currentScript.title,
          hook: _currentScript.hook,
          script: _currentScript.script,
        }),
      });
      const d = await res.json();
      $('smodal-viral-loading').style.display = 'none';
      if (!res.ok) {
        $('smodal-viral-content').innerHTML = '<div style="color:var(--red);font-size:13px">' +
          esc(aiErrText(d, 'Could not build the viral package.')) + '</div>';
        $('smodal-viral-content').style.display = 'block';
        _viralResult = null;
        return;
      }
      _viralResult = d;
      _renderViral(d);
      $('smodal-viral-content').style.display = 'block';
      console.log('[GrowthLoop] Viral package built for:', _currentScript.title);
      toast('Viral package ready.', '🔥');
      setTimeout(() => { $('smodal-body').scrollTop = $('smodal-body').scrollHeight; }, 100);
    } catch (e) {
      $('smodal-viral-loading').style.display = 'none';
      $('smodal-viral-content').innerHTML = '<div style="color:var(--red);font-size:13px">Network error — could not reach the server.</div>';
      $('smodal-viral-content').style.display = 'block';
      _viralResult = null;
    } finally {
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  }

  function _strategyToText(d) {
    const adv = d.advanced_settings || {};
    const advOn = Object.keys(adv).filter(k => adv[k] === true).map(k => k.replace(/_/g, ' ')).join(', ');
    const lines = [
      'YOUTUBE STUDIO STRATEGY — ' + (_currentScript ? _currentScript.title : ''),
      '',
      'Best posting time: ' + (d.posting_time || ''),
      'Category: ' + (d.category || ''),
      'Audience: ' + (d.audience || ''),
      'Visibility: ' + (d.visibility || ''),
      'Language: ' + (d.language || ''),
      'Captions: ' + (d.captions || ''),
      'Playlist: ' + (d.playlist || ''),
      'Title style: ' + (d.title_style || ''),
      'Thumbnail: ' + (d.thumbnail_style || ''),
      '',
      'Tags: ' + (Array.isArray(d.tags) ? d.tags.join(', ') : ''),
      '',
      'Description structure:',
      ...(Array.isArray(d.description_structure) ? d.description_structure.map((s, i) => (i + 1) + '. ' + s) : []),
      '',
      'Advanced (keep ON): ' + advOn,
    ];
    return lines.join('\\n');
  }

  function applyStrategy() {
    if (!_optStrategy) { toast('Build a strategy first.', '⚠'); return; }
    navigator.clipboard.writeText(_strategyToText(_optStrategy)).then(() => {
      toast('Strategy copied — paste into YouTube Studio.', '✓');
      console.log('[GrowthLoop] Strategy applied (copied) for:', _currentScript ? _currentScript.title : '');
    });
  }

  // ── YouTube Studio Kit ─────────────────────────────────────
  async function loadYouTubePackages() {
    const el = $('yt-packages-list');
    el.innerHTML = '<div class="loader-overlay"><div class="loader-spinner"></div><span>Loading packages…</span></div>';
    try {
      const res = await apiFetch('/youtube-packages');
      if (!res.ok) {
        el.innerHTML = '<div class="loader-overlay" style="color:var(--red)">Failed to load packages.</div>';
        return;
      }
      const { packages } = await res.json();
      window._ytPackages = packages;
      if (!packages.length) {
        el.innerHTML = '<div class="loader-overlay"><span style="color:var(--muted)">No YouTube packages yet. Generate a script and click "▶ YT Package" in the script modal.</span></div>';
        return;
      }
      el.innerHTML = packages.map(p => `
        <div class="card" style="margin-bottom:16px" id="ytpkg-card-${p.id}">
          <div class="card-header">
            <div class="card-header-left" style="flex-direction:column;align-items:flex-start;gap:4px;overflow:hidden">
              <div class="card-title" style="color:var(--gold)">${esc(p.title)}</div>
              <div style="font-size:11px;color:var(--muted)">${fmtDate(p.created_at)}</div>
            </div>
            <div class="btn-row" style="flex-shrink:0;gap:6px;flex-wrap:wrap">
              <button class="btn btn-secondary btn-sm" onclick="ytPkgListCopy(${p.id},'title')">Copy Title</button>
              <button class="btn btn-secondary btn-sm" onclick="ytPkgListCopy(${p.id},'description')">Copy Desc</button>
              <button class="btn btn-secondary btn-sm" onclick="ytPkgListCopy(${p.id},'tags')">Copy Tags</button>
              <button class="btn btn-secondary btn-sm" style="color:var(--red);border-color:var(--red)" onclick="deleteYouTubePackage(${p.id})">Delete</button>
            </div>
          </div>
          <div class="card-body" style="padding-top:10px;padding-bottom:14px">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
              <div>
                <div style="font-size:10px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.6px;margin-bottom:5px">Thumbnail Text</div>
                <div style="font-size:15px;font-weight:800;color:var(--gold)">${esc(p.thumbnail_text)}</div>
              </div>
              <div>
                <div style="font-size:10px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.6px;margin-bottom:5px">Tags</div>
                <div style="font-size:12px;color:var(--text);line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${esc(p.tags)}</div>
              </div>
            </div>
            <div style="margin-top:10px">
              <div style="font-size:10px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.6px;margin-bottom:5px">Description Preview</div>
              <div style="font-size:12px;color:var(--text);line-height:1.5;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden">${esc(p.description)}</div>
            </div>
          </div>
        </div>`).join('');
    } catch (e) {
      el.innerHTML = '<div class="loader-overlay" style="color:var(--red)">Error loading packages.</div>';
    }
  }

  function ytPkgListCopy(id, field) {
    const p = (window._ytPackages || []).find(x => x.id === id);
    if (!p || !p[field]) return;
    navigator.clipboard.writeText(p[field]).then(() => toast('Copied to clipboard.', '✓'));
  }

  async function deleteYouTubePackage(id) {
    if (!confirm('Delete this YouTube package?')) return;
    try {
      const res = await apiFetch('/youtube-packages/' + id, { method: 'DELETE' });
      if (!res.ok) { toast('Failed to delete package.', '⚠'); return; }
      document.getElementById('ytpkg-card-' + id)?.remove();
      if (window._ytPackages) window._ytPackages = window._ytPackages.filter(x => x.id !== id);
      const remaining = $('yt-packages-list').querySelectorAll('.card').length;
      if (!remaining) {
        $('yt-packages-list').innerHTML = '<div class="loader-overlay"><span style="color:var(--muted)">No YouTube packages yet. Generate a script and click "▶ YT Package" in the script modal.</span></div>';
      }
      toast('Package deleted.', '✓');
    } catch (e) { toast('Network error.', '⚠'); }
  }

  function useImprovedTitle(improved) {
    navigate('newsletter');
    setTimeout(() => {
      $('nl-subject').value = improved;
      $('nl-subject').focus();
      $('nl-subject').scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 80);
    toast('Improved title loaded into Newsletter subject.', '✍');
  }

  function copyText(text, label) {
    navigator.clipboard.writeText(text).then(() => toast(label + ' copied to clipboard.', '✓'));
  }

  function addToStrategy(title, desc) {
    const text = title + (desc ? '\\n' + desc : '');
    navigator.clipboard.writeText(text).then(() => toast('"' + title + '" added to clipboard strategy.', '📋'));
  }

  function renderYoutube(d) {
    // ── Correct field names from the actual API response ──
    const top    = d.top_videos         || [];
    const under  = d.underperforming    || [];
    const kw     = d.keyword_patterns   || [];
    const tp     = d.topic_patterns     || [];
    const topics = d.suggested_topics   || [];  // string[]
    const titles = d.title_improvements || [];  // [{original, improved}]
    const plists = d.playlist_ideas     || [];  // [{title, description}]
    const aiNote = d.ai_note;
    const analysed = d.videos_analysed  || 0;

    // ── Channel summary banner ──
    const summaryBar = `
      <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;padding:12px 16px;background:var(--surface);border:1px solid var(--border);border-radius:10px;flex-wrap:wrap">
        <span style="font-size:12px;color:var(--muted)">📺 <strong style="color:var(--text)">${analysed}</strong> videos analysed</span>
        <span style="font-size:12px;color:var(--muted)">🏆 <strong style="color:var(--gold)">${top.length}</strong> top performers identified</span>
        <span style="font-size:12px;color:var(--muted)">⚠ <strong style="color:var(--red)">${under.length}</strong> underperforming</span>
        <span style="font-size:12px;color:var(--muted)">✨ <strong style="color:var(--text)">${topics.length}</strong> AI topic ideas generated</span>
      </div>`;

    // ── AI note (e.g. OpenAI quota or missing key) ──
    const aiNoteHtml = aiNote ? `
      <div class="ai-note">
        <span>⚠</span>
        <span>${esc(aiNote)}</span>
      </div>` : '';

    // ── Hero: top video ──
    const topHero = top[0] ? `
      <div class="highlight-card" style="margin-bottom:20px">
        <div class="highlight-label">🏆 Top Performing Video</div>
        <div class="highlight-title">
          ${top[0].url
            ? `<a href="${esc(top[0].url)}" target="_blank" rel="noopener"
                 style="color:inherit;text-decoration:none;"
                 onmouseover="this.style.color='var(--gold)'"
                 onmouseout="this.style.color='inherit'">${esc(top[0].title)}</a>`
            : esc(top[0].title)}
        </div>
        <div class="highlight-meta">
          <span>👁 ${fmtNum(top[0].views)} views</span>
          <span>👍 ${fmtNum(top[0].likes)} likes</span>
          <span>📅 ${top[0].published_at ? top[0].published_at.slice(0,10) : '—'}</span>
          ${top[0].url ? `<a href="${esc(top[0].url)}" target="_blank" rel="noopener"
            style="color:var(--gold);font-size:12px;text-decoration:none">▶ Watch on YouTube ↗</a>` : ''}
        </div>
      </div>` : '';

    // ── Top 5 videos table ──
    const topRows = top.map((v, i) => {
      const link = v.url
        ? `<a href="${esc(v.url)}" target="_blank" rel="noopener"
             style="color:var(--text);text-decoration:none;font-size:13px"
             onmouseover="this.style.color='var(--gold)'"
             onmouseout="this.style.color='var(--text)'">${esc(v.title)}</a>`
        : esc(v.title);
      return `<tr>
        <td style="color:var(--muted);font-size:12px;font-weight:700">${i + 1}</td>
        <td style="line-height:1.4">${link}
          ${v.url ? `<a href="${esc(v.url)}" target="_blank" rel="noopener"
            style="display:inline-block;margin-left:6px;font-size:10px;color:var(--muted);text-decoration:none;vertical-align:middle"
            title="Watch on YouTube">↗</a>` : ''}
        </td>
        <td style="font-weight:700;color:var(--gold);white-space:nowrap">${fmtNum(v.views)}</td>
        <td style="color:var(--muted);white-space:nowrap">${fmtNum(v.likes)}</td>
        <td style="font-size:11px;color:var(--muted);white-space:nowrap">${v.published_at ? v.published_at.slice(0,10) : '—'}</td>
      </tr>`;
    }).join('') || '<tr class="empty-row"><td colspan="5">No data available.</td></tr>';

    // ── Underperforming videos table (with Use Improved Title button) ──
    const underRows = under.map((v, i) => {
      const improved = titles[i] ? titles[i].improved : null;
      const improvedBtn = improved
        ? `<button class="btn btn-secondary btn-sm"
             onclick="useImprovedTitle(${jsAttr(improved)})"
             title="${esc(improved)}">Use Improved Title</button>`
        : '';
      return `<tr>
        <td style="line-height:1.4;font-size:13px">${esc(v.title)}</td>
        <td style="color:var(--red);font-weight:600;white-space:nowrap">${fmtNum(v.views)}</td>
        <td style="color:var(--muted);white-space:nowrap">${fmtNum(v.likes)}</td>
        <td style="white-space:nowrap">${improvedBtn}</td>
      </tr>`;
    }).join('') || '<tr class="empty-row"><td colspan="4">No underperforming videos detected.</td></tr>';

    // ── Keyword chips ──
    const kwChips = kw.slice(0, 20).map(k =>
      `<span class="badge badge-yellow" style="margin:3px;cursor:pointer;user-select:none"
         onclick="ytGenerateScript(${jsAttr(k.keyword)})"
         title="Click to generate a script about '${esc(k.keyword)}'"
       >${esc(k.keyword)} <span style="opacity:.65">${k.count}×</span></span>`
    ).join('') || '<span style="color:var(--muted);font-size:13px">No keywords found.</span>';

    // ── Topic patterns ──
    const tpRows = tp.map(p => `
      <div class="topic-row">
        <div class="topic-row-text">
          <strong style="color:var(--gold)">${esc(p.pattern)}</strong>
          <span style="color:var(--muted)"> — ${p.count} video${p.count !== 1 ? 's' : ''}</span>
          ${p.examples && p.examples.length
            ? '<br><span style="font-size:11px;color:var(--muted)">' + p.examples.slice(0,2).map(esc).join(' · ') + '</span>'
            : ''}
        </div>
        <button class="btn btn-secondary btn-sm"
          onclick="ytGenerateScript(${jsAttr(p.pattern + ' (Catholic)')})"
          style="flex-shrink:0">Script →</button>
      </div>`
    ).join('') || '<p style="color:var(--muted);font-size:13px">No topic patterns detected.</p>';

    // ── AI: Suggested topics ──
    const topicCards = topics.map(t => `
      <div class="topic-row">
        <span class="topic-row-text">${esc(t)}</span>
        <button class="btn btn-primary btn-sm"
          onclick="ytGenerateScript(${jsAttr(t)})"
          style="flex-shrink:0">Generate Script</button>
      </div>`
    ).join('') || `<p style="color:var(--muted);font-size:13px">${aiNote ? 'AI analysis unavailable — see note above.' : 'No suggestions generated.'}</p>`;

    // ── AI: Title improvements ──
    const titleCards = titles.map(pair => `
      <div class="title-pair">
        <div class="title-original">${esc(pair.original || '')}</div>
        <div class="title-improved">${esc(pair.improved || '')}</div>
        <div class="title-pair-actions">
          <button class="btn btn-secondary btn-sm"
            onclick="copyText(${jsAttr(pair.improved || '')}, 'Improved title')">Copy</button>
          <button class="btn btn-primary btn-sm"
            onclick="useImprovedTitle(${jsAttr(pair.improved || '')})">Use as Subject</button>
        </div>
      </div>`
    ).join('') || `<p style="color:var(--muted);font-size:13px">${aiNote ? 'AI analysis unavailable.' : 'No title improvements generated.'}</p>`;

    // ── AI: Playlist ideas ──
    const playlistCards = plists.map(p => `
      <div class="playlist-card">
        <div class="playlist-title">${esc(p.title || '')}</div>
        <div class="playlist-desc">${esc(p.description || '')}</div>
        <button class="btn btn-secondary btn-sm"
          onclick="addToStrategy(${jsAttr(p.title || '')}, ${jsAttr(p.description || '')})">
          + Add to Strategy
        </button>
      </div>`
    ).join('') || `<p style="color:var(--muted);font-size:13px">${aiNote ? 'AI analysis unavailable.' : 'No playlist ideas generated.'}</p>`;

    $('yt-content').innerHTML = `
      ${summaryBar}
      ${aiNoteHtml}
      ${topHero}

      <!-- Top + Underperforming tables -->
      <div class="grid-2" style="margin-bottom:20px">
        <div class="card" style="margin-bottom:0">
          <div class="card-header">
            <div class="card-header-left">
              <span>🏆</span>
              <span class="card-title">Top 5 Videos</span>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>#</th><th>Title</th><th>Views</th><th>Likes</th><th>Published</th></tr></thead>
              <tbody>${topRows}</tbody>
            </table>
          </div>
        </div>

        <div class="card" style="margin-bottom:0">
          <div class="card-header">
            <div class="card-header-left">
              <span>⚠</span>
              <span class="card-title" style="color:var(--red)">Underperforming Videos</span>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Title</th><th>Views</th><th>Likes</th><th>Action</th></tr></thead>
              <tbody>${underRows}</tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Keywords + Topic patterns -->
      <div class="grid-2" style="margin-bottom:20px">
        <div class="card" style="margin-bottom:0">
          <div class="card-header">
            <div class="card-header-left"><span>#</span><span class="card-title">Keyword Patterns</span></div>
            <span style="font-size:11px;color:var(--muted)">Click any keyword to generate a script</span>
          </div>
          <div class="card-body" style="display:flex;flex-wrap:wrap;gap:2px">
            ${kwChips}
          </div>
        </div>
        <div class="card" style="margin-bottom:0">
          <div class="card-header">
            <div class="card-header-left"><span>⊕</span><span class="card-title">Topic Patterns</span></div>
          </div>
          <div class="card-body" style="padding-top:8px">
            ${tpRows}
          </div>
        </div>
      </div>

      <!-- AI Insights: 3 full-width panels -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-header">
          <div class="card-header-left">
            <span>💡</span>
            <span class="card-title">Suggested Topics</span>
          </div>
          <span style="font-size:11px;color:var(--muted)">${topics.length} AI-generated ideas</span>
        </div>
        <div class="card-body" style="padding-top:8px">
          ${topicCards}
        </div>
      </div>

      <div class="grid-2" style="margin-bottom:20px">
        <div class="card" style="margin-bottom:0">
          <div class="card-header">
            <div class="card-header-left"><span>✍</span><span class="card-title">Title Improvements</span></div>
            <span style="font-size:11px;color:var(--muted)">Original → Improved</span>
          </div>
          <div class="card-body" style="padding-top:8px">
            ${titleCards}
          </div>
        </div>
        <div class="card" style="margin-bottom:0">
          <div class="card-header">
            <div class="card-header-left"><span>📋</span><span class="card-title">Playlist Ideas</span></div>
          </div>
          <div class="card-body" style="padding-top:8px">
            ${playlistCards}
          </div>
        </div>
      </div>`;
  }

  // ── Content Ideas ─────────────────────────────────────────
  async function generateIdea() {
    const topic = $('idea-topic').value.trim();
    if (!topic) { showBar('idea-status', 'Please enter a topic first.', 'error'); return; }
    const btn = $('idea-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Generating…';
    $('idea-status').style.display = 'none';
    $('idea-result').classList.remove('visible');
    try {
      const res = await apiFetch('/generate-idea', {
        method: 'POST', body: JSON.stringify({ topic }),
      });
      const d = await res.json();
      if (!res.ok) {
        const msg = d.detail?.message || d.detail || 'Failed to generate idea.';
        showBar('idea-status', msg, 'error');
        return;
      }
      $('idea-viral-title').textContent = d.viral_title;
      $('idea-hook').textContent = d.hook;
      $('idea-script').textContent = d.short_script;
      $('idea-result').classList.add('visible');
    } catch (e) { showBar('idea-status', 'Network error. Try again.', 'error'); }
    finally { btn.disabled = false; btn.textContent = 'Generate Idea'; }
  }

  function copyIdea() {
    const title  = $('idea-viral-title').textContent;
    const hook   = $('idea-hook').textContent;
    const script = $('idea-script').textContent;
    const text = `Title: ${title}\\n\\nHook: ${hook}\\n\\nScript:\\n${script}`;
    navigator.clipboard.writeText(text).then(() => {
      const btn = event.target;
      btn.textContent = '✓ Copied!';
      setTimeout(() => { btn.textContent = 'Copy Script'; }, 2000);
    });
  }

  // ── Event wiring ──────────────────────────────────────────
  $('key-input').addEventListener('keydown', e => { if (e.key === 'Enter') login(); });

  $('preview-modal').addEventListener('click', e => {
    if (e.target === $('preview-modal')) closePreview();
  });

  $('script-modal').addEventListener('click', e => {
    if (e.target === $('script-modal')) closeScriptModal();
  });

  // ── Growth Engine ─────────────────────────────────────────
  const STAGE_LABELS = { idea: 'Idea', script: 'Script', package: 'Package', published: 'Published' };
  let _growthStages = ['idea', 'script', 'package', 'published'];

  function loadGrowth() {
    console.log('[GrowthLoop] Growth Engine opened');
    loadTodayVideo();
    loadGrowthInsights();
    loadPerformance();
    loadPerfLog();
    loadPostingDays();
    loadSchedule();
    loadPipeline();
  }

  // ── Posting-day selector ──
  const POSTING_DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  let selectedDays = [];

  function renderPostingDays() {
    const row = $('posting-days-row');
    row.innerHTML = POSTING_DAY_NAMES.map(name => {
      const on = selectedDays.includes(name);
      return '<div class="day-toggle' + (on ? ' on' : '') + '" role="button" tabindex="0"'
        + ' onclick="togglePostingDay(' + jsAttr(name) + ')">' + esc(name.slice(0, 3)) + '</div>';
    }).join('');
  }

  function togglePostingDay(name) {
    if (selectedDays.includes(name)) {
      selectedDays = selectedDays.filter(d => d !== name);
    } else {
      selectedDays = POSTING_DAY_NAMES.filter(d => d === name || selectedDays.includes(d));
    }
    renderPostingDays();
  }

  async function loadPostingDays() {
    const row = $('posting-days-row');
    row.innerHTML = '<div class="loader-overlay" style="width:100%"><div class="loader-spinner"></div><span>Loading posting days…</span></div>';
    try {
      const res = await apiFetch('/growth/schedule/days');
      const d = await res.json();
      if (!res.ok) { row.innerHTML = '<div class="kanban-empty">' + esc(aiErrText(d, 'Could not load posting days.')) + '</div>'; return; }
      selectedDays = Array.isArray(d.days) ? d.days : [];
      renderPostingDays();
    } catch (e) { row.innerHTML = '<div class="kanban-empty">Network error loading posting days.</div>'; }
  }

  async function savePostingDays() {
    if (!selectedDays.length) { showBar('posting-days-status', 'Select at least one posting day before saving.', 'error'); return; }
    const btn = $('save-days-btn');
    const orig = btn.innerHTML;
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Saving…';
    try {
      const res = await apiFetch('/growth/schedule/days', { method: 'PUT', body: JSON.stringify({ days: selectedDays }) });
      const d = await res.json().catch(() => ({}));
      if (!res.ok) { showBar('posting-days-status', aiErrText(d, 'Could not save posting days.'), 'error'); return; }
      selectedDays = Array.isArray(d.days) ? d.days : selectedDays;
      renderPostingDays();
      showBar('posting-days-status', 'Posting days saved — used for your next weekly schedule.', 'success');
      console.log('[GrowthLoop] Posting days saved:', selectedDays.join(', '));
    } catch (e) {
      showBar('posting-days-status', 'Network error saving posting days.', 'error');
    } finally { btn.disabled = false; btn.innerHTML = orig; }
  }

  // ── Today's Video ──
  let _todayItem = null;

  async function loadTodayVideo() {
    const box = $('today-video-panel');
    box.innerHTML = '<div class="loader-overlay"><div class="loader-spinner"></div><span>Checking today\\'s schedule…</span></div>';
    try {
      const res = await apiFetch('/growth/today');
      const d = await res.json();
      if (!res.ok) { box.innerHTML = '<div class="kanban-empty">' + esc(aiErrText(d, 'Could not load today\\'s video.')) + '</div>'; return; }
      if (!d.scheduled) {
        _todayItem = null;
        box.innerHTML = '<div class="kanban-empty">No video scheduled for today. Generate a full week to build your calendar.</div>';
        return;
      }
      _todayItem = d;
      const posted = d.status === 'posted';
      let html = '<div class="today-title">' + esc(d.title) + '</div>'
        + '<div class="today-status' + (posted ? ' done' : '') + '">' + (posted ? '✓ Posted' : '● Scheduled for today') + '</div>'
        + '<div class="today-actions">'
        + '<button class="btn btn-secondary btn-sm" onclick="viewTodayScript()">📄 View Script</button>'
        + '<button class="btn btn-secondary btn-sm" onclick="copyTodayPackage()">📋 Copy YouTube Package</button>';
      if (!posted) html += '<button class="btn btn-primary btn-sm" onclick="markPosted(' + d.id + ', this)">✅ Mark as Posted</button>';
      html += '</div>';
      box.innerHTML = html;
      console.log('[GrowthLoop] Today\\'s video loaded:', d.title);
    } catch (e) { box.innerHTML = '<div class="kanban-empty">Network error loading today\\'s video.</div>'; }
  }

  function viewTodayScript() {
    if (!_todayItem || !_todayItem.script) { toast('No script available for today.', '⚠'); return; }
    _currentScript = {
      topic: _todayItem.title,
      title: _todayItem.script.title || _todayItem.title,
      hook: _todayItem.script.hook || '',
      script: _todayItem.script.script || '',
    };
    _showScriptModal(_currentScript.title);
    _showScriptResult(_currentScript);
  }

  function copyTodayPackage() {
    if (!_todayItem || !_todayItem.package) { toast('No YouTube package available for today.', '⚠'); return; }
    const p = _todayItem.package;
    const text = 'Title: ' + (p.title || '')
      + '\\n\\nDescription:\\n' + (p.description || '')
      + '\\n\\nTags: ' + (p.tags || '')
      + '\\n\\nThumbnail: ' + (p.thumbnail_text || '');
    navigator.clipboard.writeText(text).then(() => toast('YouTube package copied.', '✓'));
  }

  let _markingPosted = false;
  async function markPosted(id, btn) {
    if (_markingPosted) return;            // guard against double-submit
    _markingPosted = true;
    let origHtml = '';
    if (btn) { origHtml = btn.innerHTML; btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Posting…'; }
    try {
      const res = await apiFetch('/growth/schedule/' + id + '/posted', { method: 'POST' });
      const d = await res.json().catch(() => ({}));
      if (!res.ok) {
        toast(aiErrText(d, 'Could not mark as posted.'), '⚠');
        if (btn) { btn.disabled = false; btn.innerHTML = origHtml; }
        return;
      }
      console.log('[GrowthLoop] Marked posted → Published:', id);
      toast('Marked as posted — moved to Published.', '✓');
      loadTodayVideo();
      loadSchedule();
      loadPipeline();
      if (d.email) {
        navigate('newsletter');
        setTimeout(() => {
          $('nl-subject').value = d.email.subject;
          $('nl-body').value = d.email.body;
          console.log('[GrowthLoop] Posted → Newsletter editor:', d.email.subject);
          doPreview(d.email.subject, d.email.body, 'nl-send-status');
        }, 80);
        toast('Email draft ready — preview opened.', '✉');
      }
    } catch (e) {
      console.error('[GrowthLoop] Mark-posted network error:', e);
      toast('Something went wrong. Try again.', '⚠');
      if (btn) { btn.disabled = false; btn.innerHTML = origHtml; }
    } finally { _markingPosted = false; }
  }

  // ── This Week's Schedule ──
  async function loadSchedule() {
    const box = $('schedule-panel');
    box.innerHTML = '<div class="loader-overlay"><div class="loader-spinner"></div><span>Loading schedule…</span></div>';
    try {
      const res = await apiFetch('/growth/schedule');
      const d = await res.json();
      if (!res.ok) { box.innerHTML = '<div class="kanban-empty">' + esc(aiErrText(d, 'Could not load schedule.')) + '</div>'; return; }
      const items = d.items || [];
      if (!items.length) {
        box.innerHTML = '<div class="kanban-empty">No content scheduled yet. Generate a full week to populate your calendar.</div>';
        return;
      }
      box.innerHTML = '<div class="sched-list">' + items.map(it => {
        const posted = it.status === 'posted';
        return '<div class="sched-row' + (posted ? ' done' : '') + '">'
          + '<div class="sched-date">' + esc((it.day || '').slice(0, 3)) + '<span>' + esc(it.date || '') + '</span></div>'
          + '<div class="sched-title">' + esc(it.title) + '</div>'
          + '<div class="sched-badge' + (posted ? ' done' : '') + '">' + (posted ? 'Posted' : 'Scheduled') + '</div>'
          + '</div>';
      }).join('') + '</div>';
    } catch (e) { box.innerHTML = '<div class="kanban-empty">Network error loading schedule.</div>'; }
  }

  // ── Weekly Content Factory ──
  async function runWeeklyAuto() {
    const btn = $('batch-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Building &amp; scheduling your week…';
    $('batch-result').innerHTML = '';
    showBar('batch-status', 'Generating 5 videos and scheduling them — this can take a minute…', 'info');
    try {
      const res = await apiFetch('/growth/weekly-auto', { method: 'POST', body: JSON.stringify({}) });
      const d = await res.json();
      if (!res.ok) { showBar('batch-status', aiErrText(d, 'Weekly generation failed.'), 'error'); return; }
      const created = d.created || [];
      const failed = d.failed || [];
      if (!created.length) {
        const reason = (failed[0] && failed[0].error) ? failed[0].error : 'No content was generated. Check your OpenAI quota.';
        showBar('batch-status', reason, 'error');
        return;
      }
      let msg = '✓ Created &amp; scheduled ' + created.length + ' video' + (created.length === 1 ? '' : 's') + ' — added to your pipeline and calendar.';
      if (failed.length) msg += ' (' + failed.length + ' skipped)';
      showBar('batch-status', msg, 'success');
      console.log('[GrowthLoop] Weekly auto generated & scheduled', created.length, 'videos');
      $('batch-result').innerHTML = created.map((c, i) =>
        '<div class="cta-block" style="display:flex;align-items:center;gap:10px">'
        + '<div class="flow-num" style="flex-shrink:0">' + (i + 1) + '</div>'
        + '<div style="flex:1"><div class="cta-block-text" style="color:var(--gold);font-weight:700">' + esc(c.title) + '</div>'
        + '<div class="cta-block-label" style="margin-top:2px">' + esc(c.scheduled_label || '') + '</div></div>'
        + '</div>'
      ).join('');
      loadTodayVideo();
      loadSchedule();
      loadPipeline();
    } catch (e) { showBar('batch-status', 'Network error.', 'error'); }
    finally { btn.disabled = false; btn.innerHTML = '🏭 Generate &amp; Schedule 5 Videos'; }
  }

  // ── Shorts generator (from script modal) ──
  async function generateShortsCurrent() {
    if (!_currentScript) return;
    const btn = $('smodal-shorts-btn');
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Working…';
    $('smodal-reuse-section').style.display = 'block';
    $('smodal-reuse-loading').style.display = 'flex';
    $('smodal-reuse-content').textContent = '';
    $('smodal-reuse-label').textContent = '⚡ Shorts Package';
    try {
      const res = await apiFetch('/growth/shorts', {
        method: 'POST',
        body: JSON.stringify({
          title: _currentScript.title,
          hook: _currentScript.hook,
          script: _currentScript.script,
        }),
      });
      const d = await res.json();
      $('smodal-reuse-loading').style.display = 'none';
      if (!res.ok) { $('smodal-reuse-content').textContent = aiErrText(d, 'Could not generate Shorts.'); _reuseText = ''; return; }
      const hooks = (d.hooks || []).map((h, i) => (i + 1) + '. ' + h).join('\\n');
      _reuseText = 'HOOKS:\\n' + hooks
        + '\\n\\nSCRIPT:\\n' + (d.script || '')
        + '\\n\\nCAPTION:\\n' + (d.caption || '')
        + '\\n\\nHASHTAGS:\\n' + (d.hashtags || '');
      $('smodal-reuse-content').textContent = _reuseText;
      console.log('[GrowthLoop] Shorts generated:', _currentScript.title);
    } catch (e) {
      $('smodal-reuse-loading').style.display = 'none';
      $('smodal-reuse-content').textContent = 'Network error — could not reach the server.';
      _reuseText = '';
    } finally {
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  }

  function aiErrText(d, fallback) {
    if (!d) return fallback;
    const det = d.detail;
    if (typeof det === 'string') return det;
    if (det && det.message) return det.message;
    if (Array.isArray(det) && det[0] && det[0].msg) return det[0].msg;
    return fallback;
  }

  async function loadGrowthInsights() {
    const box = $('growth-insights');
    box.innerHTML = '<div class="loader-overlay"><div class="loader-spinner"></div><span>Analysing channel…</span></div>';
    try {
      const res = await apiFetch('/growth/insights');
      const d = await res.json();
      if (!res.ok) { box.innerHTML = '<div class="kanban-empty">' + esc(aiErrText(d, 'Could not load insights.')) + '</div>'; return; }
      if (d.configured === false) {
        box.innerHTML = '<div class="metric-box" style="border-color:rgba(212,175,55,.3)">'
          + '<div class="metric-label">YouTube not connected</div>'
          + '<div style="font-size:13px;color:var(--text);line-height:1.55;margin-top:4px">' + esc(d.message || 'Configure YOUTUBE_API_KEY and YOUTUBE_CHANNEL_ID to unlock live strategy insights.') + '</div>'
          + '</div>';
        return;
      }
      const cluster = d.best_cluster ? esc(d.best_cluster) + (d.best_cluster_count ? ' <span style="font-size:12px;color:var(--muted)">(' + d.best_cluster_count + ' videos)</span>' : '') : '—';
      const time = d.best_posting_time ? esc(d.best_posting_time) : '—';
      const next = d.what_to_post_next ? esc(d.what_to_post_next) : 'Generate more content matching your top themes.';
      let html = '<div class="metric-row">'
        + '<div class="metric-box gold"><div class="metric-label">🏆 Best Topic Cluster</div><div class="metric-value gold">' + cluster + '</div></div>'
        + '<div class="metric-box gold"><div class="metric-label">⏰ Best Posting Time</div><div class="metric-value gold">' + time + '</div></div>'
        + '</div>'
        + '<div class="next-box"><div class="metric-label">🎯 Next Best Video To Make</div><div class="next-text">' + next + '</div></div>';
      if (d.suggested_topics && d.suggested_topics.length) {
        html += '<div style="margin-top:14px"><div class="metric-label" style="margin-bottom:8px">More Ideas</div>';
        d.suggested_topics.slice(0, 4).forEach(t => {
          html += '<div class="hook-item" style="border-left-color:var(--red)"><div class="hook-text">' + esc(t) + '</div>'
            + '<button class="btn btn-secondary btn-sm" onclick="flowFromTopic(' + jsAttr(t) + ')">Use →</button></div>';
        });
        html += '</div>';
      }
      box.innerHTML = html;
    } catch (e) { box.innerHTML = '<div class="kanban-empty">Network error loading insights.</div>'; }
  }

  function flowFromTopic(topic) {
    navigate('growth');
    $('flow-topic').value = topic;
    $('flow-topic').scrollIntoView({ behavior: 'smooth', block: 'center' });
    runContentFlow();
  }

  // ── One-Click Content Flow ──
  async function runContentFlow() {
    const topic = $('flow-topic').value.trim();
    if (!topic) { showBar('flow-status', 'Enter a video topic first.', 'error'); return; }
    const btn = $('flow-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Generating idea → script → package…';
    $('flow-result').innerHTML = '';
    try {
      const res = await apiFetch('/growth/content-flow', { method: 'POST', body: JSON.stringify({ topic }) });
      const d = await res.json();
      if (!res.ok) { showBar('flow-status', aiErrText(d, 'Generation failed.'), 'error'); return; }
      showBar('flow-status', '✓ Created & saved. Added to pipeline at the Package stage.', 'success');
      const pkg = d.package || {};
      $('flow-result').innerHTML =
        '<div class="cta-block"><div class="cta-block-label">Title</div><div class="cta-block-text" style="color:var(--gold);font-weight:700;margin-top:4px">' + esc(d.title) + '</div></div>'
        + '<div class="cta-block"><div class="cta-block-label">Hook</div><div class="cta-block-text">' + esc(d.hook) + '</div></div>'
        + '<div class="cta-block"><div class="cta-block-label">Script</div><div class="cta-block-text">' + esc(d.script) + '</div></div>'
        + '<div class="cta-block"><div class="cta-block-label">YouTube Package · Tags</div><div class="cta-block-text">' + esc(pkg.tags || '') + '</div></div>'
        + '<div class="cta-block" style="margin-bottom:0"><div class="cta-block-label">Thumbnail Text</div><div class="cta-block-text" style="color:var(--gold);font-weight:800;text-align:center;font-size:18px">' + esc(pkg.thumbnail_text || '') + '</div></div>';
      $('flow-topic').value = '';
      loadPipeline();
    } catch (e) { showBar('flow-status', 'Network error.', 'error'); }
    finally { btn.disabled = false; btn.innerHTML = '⚡ Create Full Content Package'; }
  }

  // ── Batch Generation (Generate 5 Videos) ──
  async function runBatchGenerate() {
    const btn = $('batch-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Building a week of content…';
    $('batch-result').innerHTML = '';
    showBar('batch-status', 'Generating 5 full content packages — this can take a minute…', 'info');
    try {
      const res = await apiFetch('/growth/batch', { method: 'POST', body: JSON.stringify({ count: 5 }) });
      const d = await res.json();
      if (!res.ok) { showBar('batch-status', aiErrText(d, 'Batch generation failed.'), 'error'); return; }
      const created = d.created || [];
      const failed = d.failed || [];
      if (!created.length) {
        const reason = (failed[0] && failed[0].error) ? failed[0].error : 'No content was generated. Check your OpenAI quota.';
        showBar('batch-status', reason, 'error');
        return;
      }
      let msg = '✓ Created ' + created.length + ' full package' + (created.length === 1 ? '' : 's') + ' — all saved to the pipeline.';
      if (failed.length) msg += ' (' + failed.length + ' skipped)';
      showBar('batch-status', msg, 'success');
      console.log('[GrowthLoop] Batch generated', created.length, 'videos');
      $('batch-result').innerHTML = created.map((c, i) =>
        '<div class="cta-block" style="display:flex;align-items:center;gap:10px">'
        + '<div class="flow-num" style="flex-shrink:0">' + (i + 1) + '</div>'
        + '<div style="flex:1"><div class="cta-block-text" style="color:var(--gold);font-weight:700">' + esc(c.title) + '</div>'
        + '<div class="cta-block-label" style="margin-top:2px">' + esc(c.topic) + '</div></div></div>'
      ).join('');
      loadPipeline();
    } catch (e) { showBar('batch-status', 'Network error.', 'error'); }
    finally { btn.disabled = false; btn.innerHTML = '🏭 Generate 5 Videos'; }
  }

  // ── Performance Feedback (What's working → do more of this) ──
  async function loadPerformance() {
    const box = $('performance-panel');
    box.innerHTML = '<div class="loader-overlay"><div class="loader-spinner"></div><span>Reviewing performance…</span></div>';
    try {
      const res = await apiFetch('/growth/insights');
      const d = await res.json();
      if (!res.ok) { box.innerHTML = '<div class="kanban-empty">' + esc(aiErrText(d, 'Could not load performance data.')) + '</div>'; return; }
      if (d.configured === false) {
        box.innerHTML = '<div class="kanban-empty">' + esc(d.message || 'Connect YouTube to see what is working.') + '</div>';
        return;
      }
      const clusters = d.top_clusters || [];
      if (!clusters.length) {
        box.innerHTML = '<div class="kanban-empty">Not enough data yet — keep publishing and check back.</div>';
        return;
      }
      let html = '<div class="perf-grid">';
      clusters.forEach((c, i) => {
        const badge = i === 0 ? '<span class="perf-top">★ Top performer</span>' : '';
        html += '<div class="perf-item"><div class="perf-head"><span class="perf-name">' + esc(c.pattern || '—') + '</span>' + badge + '</div>'
          + '<div class="perf-meta">' + (c.count || 0) + ' video' + ((c.count || 0) === 1 ? '' : 's') + ' in this theme</div>'
          + '<button class="btn btn-secondary btn-sm" style="margin-top:8px" onclick="flowFromTopic(' + jsAttr('More ' + (c.pattern || '') + ' content') + ')">Do more of this →</button></div>';
      });
      html += '</div>';
      html += '<div class="next-box" style="margin-top:14px"><div class="metric-label">💡 Takeaway</div><div class="next-text">Your audience responds most to <strong style="color:var(--gold)">' + esc(clusters[0].pattern || '') + '</strong>. Lean into it — create more videos on this theme.</div></div>';
      box.innerHTML = html;
    } catch (e) { box.innerHTML = '<div class="kanban-empty">Network error loading performance.</div>'; }
  }

  // ── Performance Feedback Loop (manual logging) ──
  const _VERDICT_META = {
    worked: { label: 'Worked', color: 'var(--gold)', icon: '✅' },
    mixed: { label: 'Mixed', color: '#e0a800', icon: '➖' },
    failed: { label: 'Failed', color: 'var(--red)', icon: '⚠' },
  };

  async function logPerformance() {
    const title = ($('perf-title').value || '').trim();
    if (!title) { showBar('perf-status', 'Enter a video title.', 'error'); return; }
    const btn = $('perf-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Analysing…';
    try {
      const res = await apiFetch('/growth/performance', {
        method: 'POST',
        body: JSON.stringify({
          title: title,
          views: Number($('perf-views').value) || 0,
          ctr: Number($('perf-ctr').value) || 0,
          likes: Number($('perf-likes').value) || 0,
        }),
      });
      const d = await res.json();
      if (!res.ok) { showBar('perf-status', aiErrText(d, 'Could not log performance.'), 'error'); return; }
      const m = _VERDICT_META[d.verdict] || _VERDICT_META.mixed;
      showBar('perf-status', m.icon + ' ' + m.label + ' — ' + (d.note || ''), d.verdict === 'failed' ? 'error' : 'success');
      $('perf-title').value = ''; $('perf-views').value = ''; $('perf-ctr').value = ''; $('perf-likes').value = '';
      console.log('[GrowthLoop] Performance logged:', title, '→', d.verdict);
      loadPerfLog();
    } catch (e) { showBar('perf-status', 'Network error.', 'error'); }
    finally { btn.disabled = false; btn.textContent = 'Log + Analyse'; }
  }

  async function loadPerfLog() {
    const box = $('perf-log-panel');
    box.innerHTML = '<div class="loader-overlay"><div class="loader-spinner"></div><span>Loading log…</span></div>';
    try {
      const res = await apiFetch('/growth/performance');
      const d = await res.json();
      if (!res.ok) { box.innerHTML = '<div class="kanban-empty">' + esc(aiErrText(d, 'Could not load the log.')) + '</div>'; return; }
      const items = d.items || [];
      const s = d.summary || {};
      if (!items.length) { box.innerHTML = '<div class="kanban-empty">No videos logged yet — add real numbers above to learn what works.</div>'; return; }
      let html = '';
      if (s.takeaway) {
        html += '<div class="next-box" style="margin-bottom:14px"><div class="metric-label">💡 Takeaway</div>' +
          '<div class="next-text">' + esc(s.takeaway) + '</div>' +
          '<div style="font-size:11px;color:var(--muted);margin-top:6px">' + (s.worked_count || 0) + ' worked · ' + (s.failed_count || 0) + ' failed · avg CTR ' + (s.avg_ctr != null ? s.avg_ctr : 0) + '%</div></div>';
      }
      items.forEach(it => {
        const m = _VERDICT_META[it.verdict] || _VERDICT_META.mixed;
        html += '<div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--border)">' +
          '<span style="font-size:11px;font-weight:700;color:' + m.color + ';min-width:64px">' + m.icon + ' ' + m.label + '</span>' +
          '<div style="flex:1;min-width:0"><div style="font-size:13px;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + esc(it.title) + '</div>' +
          '<div style="font-size:11px;color:var(--muted)">' + (it.views || 0) + ' views · ' + (it.ctr || 0) + '% CTR · ' + (it.likes || 0) + ' likes</div></div>' +
          '<button class="btn btn-secondary btn-sm" onclick="deletePerf(' + it.id + ')">✕</button></div>';
      });
      box.innerHTML = html;
    } catch (e) { box.innerHTML = '<div class="kanban-empty">Network error loading the log.</div>'; }
  }

  async function deletePerf(id) {
    try {
      const res = await apiFetch('/growth/performance/' + id, { method: 'DELETE' });
      if (res.ok) { toast('Record deleted.', '✓'); loadPerfLog(); }
      else { toast('Could not delete.', '⚠'); }
    } catch (e) { toast('Network error.', '⚠'); }
  }

  // ── Weekly Content Plan (rendered as a Mon–Sun calendar) ──
  const _WEEK_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  async function generateWeeklyPlan() {
    const btn = $('plan-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Planning your week…';
    $('plan-result').innerHTML = '';
    try {
      const res = await apiFetch('/growth/weekly-plan', { method: 'POST', body: JSON.stringify({}) });
      const d = await res.json();
      if (!res.ok) { showBar('plan-status', aiErrText(d, 'Could not generate plan.'), 'error'); return; }
      const plan = d.plan || [];
      if (!plan.length) { showBar('plan-status', 'No plan returned.', 'error'); return; }
      $('plan-status').style.display = 'none';
      console.log('[GrowthLoop] Weekly plan generated:', plan.length, 'videos');
      renderWeeklyCalendar(plan);
    } catch (e) { showBar('plan-status', 'Network error.', 'error'); }
    finally { btn.disabled = false; btn.textContent = 'Generate Weekly Plan'; }
  }

  function renderWeeklyCalendar(plan) {
    // Bucket each plan item under its day (case-insensitive); unmatched fall through in order.
    const byDay = {};
    const leftovers = [];
    plan.forEach(p => {
      const day = _WEEK_DAYS.find(d => d.toLowerCase() === String(p.day || '').trim().toLowerCase());
      if (day && !byDay[day]) byDay[day] = p; else leftovers.push(p);
    });
    _WEEK_DAYS.forEach(d => { if (!byDay[d] && leftovers.length) byDay[d] = leftovers.shift(); });
    let html = '<div class="cal-grid">';
    _WEEK_DAYS.forEach(day => {
      const p = byDay[day];
      html += '<div class="cal-cell' + (p ? ' filled' : '') + '">'
        + '<div class="cal-day">' + day.slice(0, 3) + '</div>';
      if (p) {
        html += '<div class="cal-time">' + esc(p.time || '') + '</div>'
          + '<div class="cal-title">' + esc(p.title || '') + '</div>'
          + (p.idea ? '<div class="cal-idea">' + esc(p.idea) + '</div>' : '')
          + '<button class="btn btn-secondary btn-sm" style="margin-top:8px;width:100%" onclick="addPipelineFromTitle(' + jsAttr(p.title || '') + ')">+ Pipeline</button>';
      } else {
        html += '<div class="cal-empty">—</div>';
      }
      html += '</div>';
    });
    html += '</div>';
    $('plan-result').innerHTML = html;
  }

  // ── Hook Optimization ──
  async function generateHooks() {
    const topic = $('hook-topic').value.trim();
    if (!topic) { showBar('hook-status', 'Enter a video topic first.', 'error'); return; }
    const btn = $('hook-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Writing hooks…';
    $('hook-result').innerHTML = '';
    try {
      const res = await apiFetch('/growth/hooks', { method: 'POST', body: JSON.stringify({ topic }) });
      const d = await res.json();
      if (!res.ok) { showBar('hook-status', aiErrText(d, 'Could not generate hooks.'), 'error'); return; }
      const hooks = d.hooks || [];
      $('hook-status').style.display = 'none';
      $('hook-result').innerHTML = hooks.map((h, i) =>
        '<div class="hook-item"><div class="hook-num">' + (i + 1) + '</div><div class="hook-text">' + esc(h) + '</div></div>'
      ).join('');
    } catch (e) { showBar('hook-status', 'Network error.', 'error'); }
    finally { btn.disabled = false; btn.textContent = 'Generate 5 Viral Hooks'; }
  }

  // ── CTA Booster ──
  async function generateCTAs() {
    const next = $('cta-next').value.trim();
    const btn = $('cta-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Building…';
    try {
      const res = await apiFetch('/growth/cta', { method: 'POST', body: JSON.stringify({ next_video_title: next || null }) });
      const d = await res.json();
      if (!res.ok) { showBar('cta-status', aiErrText(d, 'Could not build CTAs.'), 'error'); return; }
      $('cta-status').style.display = 'none';
      $('cta-result').innerHTML =
        '<div class="cta-block"><div class="cta-block-head"><span class="cta-block-label">🔔 Subscribe CTA</span><button class="btn btn-secondary btn-sm" onclick="copyCtaText(' + jsAttr(d.subscribe_cta) + ',this)">Copy</button></div><div class="cta-block-text">' + esc(d.subscribe_cta) + '</div></div>'
        + '<div class="cta-block" style="margin-bottom:0"><div class="cta-block-head"><span class="cta-block-label">▶ Watch-Next CTA</span><button class="btn btn-secondary btn-sm" onclick="copyCtaText(' + jsAttr(d.watch_next_cta) + ',this)">Copy</button></div><div class="cta-block-text">' + esc(d.watch_next_cta) + '</div></div>';
    } catch (e) { showBar('cta-status', 'Network error.', 'error'); }
    finally { btn.disabled = false; btn.textContent = 'Generate CTAs'; }
  }

  function copyCtaText(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
      const orig = btn.textContent;
      btn.textContent = 'Copied ✓';
      setTimeout(() => { btn.textContent = orig; }, 1500);
    });
  }

  // ── Content Pipeline Tracker ──
  async function loadPipeline() {
    const board = $('pipeline-board');
    try {
      const res = await apiFetch('/growth/pipeline');
      if (!res.ok) { board.innerHTML = '<div class="kanban-empty">Failed to load pipeline.</div>'; return; }
      const d = await res.json();
      _growthStages = d.stage_order || _growthStages;
      const stages = d.stages || {};
      board.innerHTML = '<div class="kanban">' + _growthStages.map(stage => {
        const items = stages[stage] || [];
        const cards = items.length
          ? items.map(it => renderPipelineCard(it)).join('')
          : '<div class="kanban-empty">No items</div>';
        return '<div class="kanban-col"><div class="kanban-head"><span class="kanban-stage">' + esc(STAGE_LABELS[stage] || stage) + '</span><span class="kanban-count">' + items.length + '</span></div>' + cards + '</div>';
      }).join('') + '</div>';
    } catch (e) { board.innerHTML = '<div class="kanban-empty">Network error loading pipeline.</div>'; }
  }

  function renderPipelineCard(it) {
    const idx = _growthStages.indexOf(it.stage);
    const canBack = idx > 0;
    const canFwd = idx >= 0 && idx < _growthStages.length - 1;
    const meta = it.script_id ? 'Script #' + it.script_id + (it.package_id ? ' · Pkg #' + it.package_id : '') : 'Manual';
    return '<div class="pl-card"><div class="pl-card-title">' + esc(it.title) + '</div>'
      + '<div class="pl-card-meta">' + esc(meta) + '</div>'
      + '<div class="pl-actions">'
      + '<button class="pl-btn" onclick="movePipeline(' + it.id + ',-1)"' + (canBack ? '' : ' disabled') + '>◀</button>'
      + '<button class="pl-btn" onclick="movePipeline(' + it.id + ',1)"' + (canFwd ? '' : ' disabled') + '>▶</button>'
      + '<button class="pl-btn del" onclick="deletePipeline(' + it.id + ')">✕</button>'
      + '</div></div>';
  }

  async function addPipelineItem() {
    const input = $('pl-new-title');
    const title = input.value.trim();
    if (!title) { showBar('pl-status', 'Enter an idea title first.', 'error'); return; }
    await createPipeline(title);
    input.value = '';
  }

  async function addPipelineFromTitle(title) {
    if (!title) return;
    await createPipeline(title);
  }

  async function createPipeline(title) {
    try {
      const res = await apiFetch('/growth/pipeline', { method: 'POST', body: JSON.stringify({ title, stage: 'idea' }) });
      const d = await res.json();
      if (!res.ok) { showBar('pl-status', aiErrText(d, 'Could not add item.'), 'error'); return; }
      showBar('pl-status', '✓ Added to the Idea stage.', 'success');
      loadPipeline();
    } catch (e) { showBar('pl-status', 'Network error.', 'error'); }
  }

  async function movePipeline(id, dir) {
    const board = $('pipeline-board');
    // Determine current stage from the DOM-independent reload approach: fetch order locally
    try {
      const listRes = await apiFetch('/growth/pipeline');
      if (!listRes.ok) return;
      const data = await listRes.json();
      let current = null;
      for (const st of (data.stage_order || _growthStages)) {
        for (const it of (data.stages[st] || [])) { if (it.id === id) current = it; }
      }
      if (!current) return;
      const idx = _growthStages.indexOf(current.stage);
      const newIdx = idx + dir;
      if (newIdx < 0 || newIdx >= _growthStages.length) return;
      const res = await apiFetch('/growth/pipeline/' + id, { method: 'PATCH', body: JSON.stringify({ stage: _growthStages[newIdx] }) });
      if (!res.ok) { const d = await res.json(); showBar('pl-status', aiErrText(d, 'Could not move item.'), 'error'); return; }
      loadPipeline();
    } catch (e) { showBar('pl-status', 'Network error.', 'error'); }
  }

  async function deletePipeline(id) {
    if (!confirm('Remove this item from the pipeline?')) return;
    try {
      const res = await apiFetch('/growth/pipeline/' + id, { method: 'DELETE' });
      if (!res.ok) { const d = await res.json(); showBar('pl-status', aiErrText(d, 'Could not delete.'), 'error'); return; }
      loadPipeline();
    } catch (e) { showBar('pl-status', 'Network error.', 'error'); }
  }

  // ── Weekly Distribution + Traffic Engine ──────────────────
  function _postBlock(title, text) {
    return '<div class="card" style="margin-bottom:14px">'
      + '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px">'
      + '<strong style="color:var(--gold)">' + esc(title) + '</strong>'
      + '<button class="btn btn-secondary btn-sm" onclick="copyText(' + jsAttr(text || '') + ', ' + jsAttr(title) + ')">Copy</button>'
      + '</div><div style="white-space:pre-wrap">' + esc(text) + '</div></div>';
  }

  function _renderShorts(shorts) {
    if (!shorts || !shorts.length) return '<p style="color:var(--muted)">No shorts returned.</p>';
    return shorts.map(function (s, i) {
      const tags = (s.hashtags || []).join(' ');
      const full = 'HOOK: ' + s.hook + '\\n\\nSCRIPT: ' + s.script + '\\n\\nCAPTION: ' + s.caption
        + '\\n\\nON-SCREEN: ' + s.on_screen_text + '\\n\\n' + tags;
      return '<div class="card" style="margin-bottom:12px">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px">'
        + '<strong style="color:var(--gold)">Short ' + (i + 1) + '</strong>'
        + '<button class="btn btn-secondary btn-sm" onclick="copyText(' + jsAttr(full) + ', \\'Short\\')">Copy</button></div>'
        + '<div style="white-space:pre-wrap"><strong>Hook:</strong> ' + esc(s.hook)
        + '\\n<strong>Script:</strong> ' + esc(s.script)
        + '\\n<strong>Caption:</strong> ' + esc(s.caption)
        + '\\n<strong>On-screen:</strong> ' + esc(s.on_screen_text)
        + '\\n<strong>Hashtags:</strong> ' + esc(tags) + '</div></div>';
    }).join('');
  }

  async function genWeeklyPosts() {
    const btn = $('wd-gen-btn'); const out = $('wd-output');
    const orig = btn.textContent; btn.disabled = true; btn.textContent = 'Generating…';
    out.innerHTML = '<p style="color:var(--muted)">Generating posts…</p>';
    try {
      const res = await apiFetch('/content/generate-weekly-posts', { method: 'POST', body: '{}' });
      if (!res.ok) { out.innerHTML = ''; showBar('wd-status', 'Could not generate posts.', 'error'); return; }
      const d = await res.json();
      out.innerHTML = _postBlock('📖 Sunday — Reflection', d.sunday_post)
        + _postBlock('⚔ Wednesday — Apologetics', d.wednesday_post)
        + _postBlock('▶ Friday — Video Promo', d.friday_post)
        + _postBlock('🎨 Image Prompt', d.optional_image_prompt);
    } catch (e) { out.innerHTML = ''; showBar('wd-status', 'Network error.', 'error'); }
    finally { btn.disabled = false; btn.textContent = orig; }
  }

  async function loadFacebookPack() {
    const out = $('fb-output');
    out.innerHTML = '<p style="color:var(--muted)">Loading…</p>';
    try {
      const res = await apiFetch('/content/facebook-pack');
      if (!res.ok) { out.innerHTML = ''; showBar('wd-status', 'Could not load Facebook pack.', 'error'); return; }
      const d = await res.json();
      let html = _postBlock('📝 Ready-to-Post', d.post_text);
      const groups = (d.suggested_groups || []).map(function (g) {
        return '<li style="margin-bottom:6px"><a href="' + esc(g) + '" target="_blank" rel="noopener" style="color:var(--gold)">' + esc(g) + '</a></li>';
      }).join('');
      html += '<div class="card" style="margin-bottom:14px"><strong style="color:var(--gold)">Suggested Groups</strong>'
        + '<ul style="margin:10px 0 0 18px">' + (groups || '<li style="color:var(--muted)">No groups configured.</li>') + '</ul></div>';
      const tips = (d.instructions || []).map(function (t) { return '<li style="margin-bottom:6px">' + esc(t) + '</li>'; }).join('');
      if (tips) html += '<div class="card"><strong style="color:var(--gold)">Posting Instructions</strong><ul style="margin:10px 0 0 18px">' + tips + '</ul></div>';
      out.innerHTML = html;
    } catch (e) { out.innerHTML = ''; showBar('wd-status', 'Network error.', 'error'); }
  }

  async function genShorts() {
    const topic = $('te-shorts-topic').value.trim();
    const out = $('te-shorts-out');
    out.innerHTML = '<p style="color:var(--muted)">Generating…</p>';
    try {
      const res = await apiFetch('/content/generate-shorts', { method: 'POST', body: JSON.stringify({ video_topic: topic }) });
      if (!res.ok) { out.innerHTML = ''; showBar('te-status', 'Could not generate shorts.', 'error'); return; }
      const d = await res.json();
      out.innerHTML = _renderShorts(d.shorts);
    } catch (e) { out.innerHTML = ''; showBar('te-status', 'Network error.', 'error'); }
  }

  async function genHooks() {
    const topic = $('te-hooks-topic').value.trim();
    if (!topic) { showBar('te-status', 'Enter a topic for hooks.', 'error'); return; }
    const out = $('te-hooks-out');
    out.innerHTML = '<p style="color:var(--muted)">Generating…</p>';
    try {
      const res = await apiFetch('/content/generate-hooks', { method: 'POST', body: JSON.stringify({ topic: topic }) });
      if (!res.ok) { out.innerHTML = ''; showBar('te-status', 'Could not generate hooks.', 'error'); return; }
      const d = await res.json();
      const hooks = d.hooks || [];
      const all = hooks.join('\\n');
      out.innerHTML = '<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
        + '<strong style="color:var(--gold)">5 Hooks</strong>'
        + '<button class="btn btn-secondary btn-sm" onclick="copyText(' + jsAttr(all) + ', \\'Hooks\\')">Copy All</button></div>'
        + '<ul style="margin:0 0 0 18px">' + hooks.map(function (h) { return '<li style="margin-bottom:6px">' + esc(h) + '</li>'; }).join('') + '</ul></div>';
    } catch (e) { out.innerHTML = ''; showBar('te-status', 'Network error.', 'error'); }
  }

  async function genRepurpose() {
    const input = $('te-repurpose-input').value.trim();
    if (!input) { showBar('te-status', 'Enter a topic or script to repurpose.', 'error'); return; }
    const out = $('te-repurpose-out');
    out.innerHTML = '<p style="color:var(--muted)">Generating…</p>';
    try {
      const res = await apiFetch('/content/repurpose', { method: 'POST', body: JSON.stringify({ topic: input }) });
      if (!res.ok) { out.innerHTML = ''; showBar('te-status', 'Could not repurpose.', 'error'); return; }
      const d = await res.json();
      let html = '<h3 style="color:var(--gold);margin:0 0 10px">Shorts</h3>' + _renderShorts(d.shorts);
      html += _postBlock('📘 Facebook Post', d.facebook_post);
      html += _postBlock('🎵 TikTok Caption', d.tiktok_caption);
      html += _postBlock('▶ YouTube Description', d.youtube_description);
      html += _postBlock('✉ Email Teaser', d.email_teaser);
      out.innerHTML = html;
    } catch (e) { out.innerHTML = ''; showBar('te-status', 'Network error.', 'error'); }
  }

  async function loadPostingPlan() {
    const out = $('te-plan-out');
    if (!out) return;
    out.innerHTML = '<p style="color:var(--muted)">Loading…</p>';
    try {
      const res = await apiFetch('/content/posting-plan');
      if (!res.ok) { out.innerHTML = '<p style="color:var(--muted)">Could not load plan.</p>'; return; }
      const d = await res.json();
      const p = d.weekly_plan || {};
      const days = [['Monday', p.monday], ['Wednesday', p.wednesday], ['Friday', p.friday], ['Sunday', p.sunday]];
      let html = '<ul style="margin:0 0 0 18px">' + days.map(function (x) {
        return '<li style="margin-bottom:8px"><strong style="color:var(--gold)">' + x[0] + ':</strong> ' + esc(x[1] || '') + '</li>';
      }).join('') + '</ul>';
      const tips = d.tips || [];
      if (tips.length) html += '<div style="margin-top:12px;color:var(--muted)"><strong>Tips:</strong><ul style="margin:6px 0 0 18px">'
        + tips.map(function (t) { return '<li style="margin-bottom:4px">' + esc(t) + '</li>'; }).join('') + '</ul></div>';
      out.innerHTML = html;
    } catch (e) { out.innerHTML = '<p style="color:var(--muted)">Network error.</p>'; }
  }

  // ── Video Grid Manager ────────────────────────────────────
  var vgCategories = [];

  function vgIsHttp(u) { return /^https?:\/\//i.test(String(u || '')); }

  async function vgLoad() {
    try {
      const res = await apiFetch('/admin/video-grid');
      if (!res.ok) { showBar('vg-status-bar', 'Could not load the video grid.', 'error'); return; }
      const d = await res.json();
      vgCategories = d.categories || [];
      // Populate category select once
      const sel = $('vg-category');
      if (sel && !sel.options.length) {
        sel.innerHTML = vgCategories.map(function (c) {
          return '<option value="' + esc(c.key) + '">' + esc(c.label) + '</option>';
        }).join('');
      }
      var total = 0;
      var html = '';
      vgCategories.forEach(function (c) {
        var vids = c.videos || [];
        total += vids.length;
        html += '<div style="margin-bottom:18px">'
          + '<div style="font-weight:600;color:var(--gold);margin-bottom:8px">' + esc(c.label)
          + ' <span style="color:var(--muted);font-weight:400">(' + vids.length + ')</span></div>';
        if (vids.length) {
          html += vids.map(function (v) {
            var url = vgIsHttp(v.youtube_url) ? v.youtube_url : '';
            return '<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px;border:1px solid var(--border);border-radius:8px;margin-bottom:6px">'
              + '<div style="min-width:0"><div style="font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + esc(v.title || 'Untitled') + '</div>'
              + (url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener" style="font-size:12px;color:var(--muted)">' + esc(url) + '</a>' : '')
              + '</div>'
              + '<button class="btn btn-secondary btn-sm" onclick="vgDelete(' + Number(v.id) + ')">Delete</button>'
              + '</div>';
          }).join('');
        } else {
          html += '<div class="empty-row" style="padding:8px">No videos yet.</div>';
        }
        html += '</div>';
      });
      $('vg-count').textContent = total;
      $('vg-list').innerHTML = html || '<div class="empty-row">No categories.</div>';

      // Rotation state
      const rres = await apiFetch('/admin/video-grid/rotation');
      if (rres.ok) {
        const r = await rres.json();
        $('vg-rotation-enabled').checked = !!r.enabled;
        var info = r.enabled ? 'Rotation is ON.' : 'Rotation is OFF — the first 3 videos per category show.';
        if (r.rotated_at) info += ' Last rotated: ' + fmtDate(r.rotated_at) + '.';
        $('vg-rotation-info').textContent = info;
      }
    } catch (e) {
      showBar('vg-status-bar', 'Could not load the video grid.', 'error');
    }
  }

  async function vgAdd() {
    const category = $('vg-category').value;
    const title = $('vg-title').value.trim();
    const url = $('vg-url').value.trim();
    if (!title) { showBar('vg-status-bar', 'Please enter a title.', 'error'); return; }
    if (!vgIsHttp(url)) { showBar('vg-status-bar', 'Please enter a valid http(s) YouTube URL.', 'error'); return; }
    try {
      const res = await apiFetch('/admin/video-grid', {
        method: 'POST',
        body: JSON.stringify({ category: category, title: title, youtube_url: url })
      });
      if (!res.ok) {
        const d = await res.json().catch(function () { return {}; });
        showBar('vg-status-bar', (d && d.detail) ? d.detail : 'Could not add the video.', 'error');
        return;
      }
      $('vg-title').value = '';
      $('vg-url').value = '';
      showBar('vg-status-bar', 'Video added.', 'success');
      vgLoad();
    } catch (e) {
      showBar('vg-status-bar', 'Network error — please try again.', 'error');
    }
  }

  async function vgDelete(id) {
    if (!confirm('Delete this video from the grid?')) return;
    try {
      const res = await apiFetch('/admin/video-grid/' + Number(id), { method: 'DELETE' });
      if (!res.ok) { showBar('vg-status-bar', 'Could not delete the video.', 'error'); return; }
      showBar('vg-status-bar', 'Video deleted.', 'success');
      vgLoad();
    } catch (e) {
      showBar('vg-status-bar', 'Network error — please try again.', 'error');
    }
  }

  async function vgSaveRotation() {
    const enabled = $('vg-rotation-enabled').checked;
    try {
      const res = await apiFetch('/admin/video-grid/rotation', {
        method: 'PUT',
        body: JSON.stringify({ enabled: enabled })
      });
      if (!res.ok) { showBar('vg-status-bar', 'Could not update rotation.', 'error'); return; }
      showBar('vg-status-bar', 'Rotation ' + (enabled ? 'enabled' : 'disabled') + '.', 'success');
      vgLoad();
    } catch (e) {
      showBar('vg-status-bar', 'Network error — please try again.', 'error');
    }
  }

  // ── SEO Engine ────────────────────────────────────────────
  function seoTopicVal() { return ($('seo-topic').value || '').trim(); }

  async function seoKeywords() {
    const topic = seoTopicVal();
    if (!topic) { showBar('seo-status-bar', 'Please enter a topic.', 'error'); return; }
    $('seo-kw-out').innerHTML = '<div class="empty-row">Generating…</div>';
    try {
      const res = await apiFetch('/seo/keywords', { method: 'POST', body: JSON.stringify({ topic: topic }) });
      if (!res.ok) { $('seo-kw-out').innerHTML = '<p style="color:var(--muted)">Could not generate keywords.</p>'; return; }
      const d = await res.json();
      const kws = d.keywords || [];
      $('seo-kw-out').innerHTML = '<div style="font-weight:600;margin-bottom:8px">Keywords for "' + esc(d.topic || topic) + '"</div>'
        + '<div style="display:flex;flex-wrap:wrap;gap:8px">'
        + kws.map(function (k) { return '<span class="badge badge-yellow">' + esc(k) + '</span>'; }).join('')
        + '</div>';
    } catch (e) { $('seo-kw-out').innerHTML = '<p style="color:var(--muted)">Network error.</p>'; }
  }

  async function seoVideo() {
    const topic = seoTopicVal();
    if (!topic) { showBar('seo-status-bar', 'Please enter a topic.', 'error'); return; }
    $('seo-kw-out').innerHTML = '<div class="empty-row">Generating…</div>';
    try {
      const res = await apiFetch('/seo/video', { method: 'POST', body: JSON.stringify({ topic: topic }) });
      if (!res.ok) { $('seo-kw-out').innerHTML = '<p style="color:var(--muted)">Could not generate metadata.</p>'; return; }
      const d = await res.json();
      const tags = d.tags || [];
      $('seo-kw-out').innerHTML = '<div class="field"><label>Title</label><input type="text" readonly value="' + esc(d.title || '') + '"></div>'
        + '<div class="field"><label>Description</label><textarea readonly rows="6">' + esc(d.description || '') + '</textarea></div>'
        + '<div style="font-weight:600;margin:8px 0">Tags</div>'
        + '<div style="display:flex;flex-wrap:wrap;gap:8px">'
        + tags.map(function (t) { return '<span class="badge badge-yellow">' + esc(t) + '</span>'; }).join('')
        + '</div>';
    } catch (e) { $('seo-kw-out').innerHTML = '<p style="color:var(--muted)">Network error.</p>'; }
  }

  async function seoArticle() {
    const topic = ($('seo-art-topic').value || '').trim();
    const video = ($('seo-art-video').value || '').trim();
    if (!topic) { showBar('seo-status-bar', 'Please enter a topic for the article.', 'error'); return; }
    $('seo-art-out').innerHTML = '<div class="empty-row">Writing the teaching… this can take a moment.</div>';
    var payload = { topic: topic };
    if (video) payload.video_url = video;
    try {
      const res = await apiFetch('/seo/article', { method: 'POST', body: JSON.stringify(payload) });
      if (!res.ok) {
        const d = await res.json().catch(function () { return {}; });
        $('seo-art-out').innerHTML = '<p style="color:var(--muted)">' + esc((d && d.detail) ? d.detail : 'Could not generate the article.') + '</p>';
        return;
      }
      const d = await res.json();
      $('seo-art-out').innerHTML = '<div class="status-bar success" style="display:block">Published: '
        + esc(d.title || '') + ' (' + (d.word_count || 0) + ' words) — '
        + '<a href="/truth/' + encodeURIComponent(d.slug || '') + '" target="_blank" rel="noopener">View at /truth/' + esc(d.slug || '') + '</a></div>';
      $('seo-art-topic').value = '';
      $('seo-art-video').value = '';
      seoArticles();
    } catch (e) { $('seo-art-out').innerHTML = '<p style="color:var(--muted)">Network error.</p>'; }
  }

  async function seoArticles() {
    try {
      const res = await apiFetch('/seo/articles');
      if (!res.ok) { $('seo-articles').innerHTML = '<div class="empty-row">Could not load teachings.</div>'; return; }
      const d = await res.json();
      const items = d.items || [];
      $('seo-art-count').textContent = d.count != null ? d.count : items.length;
      if (!items.length) { $('seo-articles').innerHTML = '<div class="empty-row">No teachings published yet.</div>'; return; }
      $('seo-articles').innerHTML = items.map(function (a) {
        return '<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px;border:1px solid var(--border);border-radius:8px;margin-bottom:6px">'
          + '<div style="min-width:0"><div style="font-size:14px">' + esc(a.title || 'Untitled') + '</div>'
          + '<a href="/truth/' + encodeURIComponent(a.slug || '') + '" target="_blank" rel="noopener" style="font-size:12px;color:var(--muted)">/truth/' + esc(a.slug || '') + '</a></div>'
          + '<button class="btn btn-secondary btn-sm" onclick="seoDeleteArticle(' + Number(a.id) + ')">Delete</button>'
          + '</div>';
      }).join('');
    } catch (e) { $('seo-articles').innerHTML = '<div class="empty-row">Network error.</div>'; }
  }

  async function seoDeleteArticle(id) {
    if (!confirm('Delete this teaching? Its /truth page will stop working.')) return;
    try {
      const res = await apiFetch('/seo/articles/' + Number(id), { method: 'DELETE' });
      if (!res.ok) { showBar('seo-status-bar', 'Could not delete the teaching.', 'error'); return; }
      showBar('seo-status-bar', 'Teaching deleted.', 'success');
      seoArticles();
    } catch (e) { showBar('seo-status-bar', 'Network error — please try again.', 'error'); }
  }

  async function seoVotes() {
    $('seo-votes-out').innerHTML = '<div class="empty-row">Loading…</div>';
    try {
      const res = await apiFetch('/seo/vote-suggestions');
      if (!res.ok) { $('seo-votes-out').innerHTML = '<div class="empty-row">Could not load suggestions.</div>'; return; }
      const d = await res.json();
      const items = d.suggestions || [];
      if (!items.length) { $('seo-votes-out').innerHTML = '<div class="empty-row">No voted topics yet.</div>'; return; }
      $('seo-votes-out').innerHTML = items.map(function (s) {
        return '<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px;border:1px solid var(--border);border-radius:8px;margin-bottom:6px">'
          + '<div style="min-width:0"><div style="font-size:14px">' + esc(s.topic || '') + '</div>'
          + '<div style="font-size:12px;color:var(--muted)">' + Number(s.votes_total || 0) + ' votes total</div></div>'
          + '<button class="btn btn-secondary btn-sm" onclick="seoUseTopic(' + jsAttr(s.topic || '') + ')">Use →</button>'
          + '</div>';
      }).join('');
    } catch (e) { $('seo-votes-out').innerHTML = '<div class="empty-row">Network error.</div>'; }
  }

  function seoUseTopic(topic) {
    $('seo-topic').value = topic;
    $('seo-art-topic').value = topic;
    $('seo-topic').scrollIntoView({ behavior: 'smooth', block: 'center' });
    seoKeywords();
  }

  // ── Lead Discovery ────────────────────────────────────────
  var ldLeads = [];
  var ldChannelList = [];
  var LD_FILTER_KEY = 'odili_ld_filters';
  var LD_THRESHOLD_KEY = 'odili_ld_bulk_threshold';
  var ldPendingRestore = null;

  function ldSaveThreshold() {
    try { localStorage.setItem(LD_THRESHOLD_KEY, String(ldBulkThresholdPct())); } catch (e) { /* silent */ }
  }

  function ldRestoreThreshold() {
    let v = 65;
    try {
      const raw = localStorage.getItem(LD_THRESHOLD_KEY);
      if (raw !== null && raw !== '') {
        const parsed = parseFloat(raw);
        if (!isNaN(parsed)) v = Math.min(100, Math.max(0, parsed));
      }
    } catch (e) { /* silent */ }
    const num = $('ld-bulk-threshold');
    const slider = $('ld-bulk-threshold-slider');
    if (num) num.value = v;
    if (slider) slider.value = v;
  }

  function ldSetIfOption(sel, val) {
    if (!sel || !val) return false;
    for (var i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === val) { sel.value = val; return true; }
    }
    return false;
  }

  function ldSaveFilters() {
    try {
      localStorage.setItem(LD_FILTER_KEY, JSON.stringify({
        status: $('ld-filter') ? $('ld-filter').value : 'pending',
        sort: $('ld-sort') ? $('ld-sort').value : 'intent',
        channel: $('ld-channel') ? $('ld-channel').value : '',
        category: $('ld-category') ? $('ld-category').value : ''
      }));
    } catch (e) { /* silent */ }
  }

  function ldLoad() {
    try { ldPendingRestore = JSON.parse(localStorage.getItem(LD_FILTER_KEY) || 'null'); } catch (e) { ldPendingRestore = null; }
    if (ldPendingRestore && typeof ldPendingRestore === 'object') {
      ldSetIfOption($('ld-filter'), ldPendingRestore.status);
      ldSetIfOption($('ld-sort'), ldPendingRestore.sort);
    } else {
      ldPendingRestore = null;
    }
    ldRestoreThreshold();
    ldLoadStatus();
    ldLoadChannels();
    ldLoadLeads();
  }

  function ldUpdateTabBadge(count) {
    const el = $('ld-tab-badge');
    if (!el) return;
    const n = count || 0;
    if (n > 0) {
      el.textContent = n;
      el.title = n + ' pending lead' + (n === 1 ? '' : 's') + ' awaiting review';
      el.style.display = 'inline-block';
    } else {
      el.style.display = 'none';
    }
  }

  async function ldRefreshTabBadge() {
    try {
      const res = await apiFetch('/leads/status');
      if (!res.ok) return;
      const d = await res.json();
      ldUpdateTabBadge(d.pending_leads);
    } catch (e) {}
  }

  async function ldLoadStatus() {
    try {
      const res = await apiFetch('/leads/status');
      if (!res.ok) { $('ld-status').innerHTML = '<div class="empty-row">Could not load status.</div>'; return; }
      const d = await res.json();
      ldUpdateTabBadge(d.pending_leads);
      ldSetUndoVisible(d.last_bulk_skip);
      const q = d.quota || {};
      const pct = q.cap ? Math.min(100, Math.round((q.units_used / q.cap) * 100)) : 0;
      const cfg = d.configured
        ? '<span style="color:#4caf50;font-weight:600">✓ Connected</span>'
        : '<span style="color:#e57373;font-weight:600">✗ YOUTUBE_API_KEY not set</span>';
      const alert = d.quota_alert;
      let banner = '';
      if (alert && alert.stopped_early) {
        const when = alert.at ? (' (' + esc(fmtDate(alert.at)) + ')') : '';
        banner =
            '<div style="margin-bottom:16px;padding:12px 14px;border:1px solid #e57373;background:rgba(229,115,115,.12);border-radius:8px;color:#ffb4b4;font-size:13px;line-height:1.5">'
          + '<strong>⚠️ Last scan stopped early — daily YouTube quota cap reached.</strong>' + when
          + '<div style="color:var(--muted);margin-top:4px">Some videos were deferred to the next UTC day. If channels are added faster than the daily quota covers, they will keep being deferred. Watch fewer channels or wait for the quota to reset.</div>'
          + '</div>';
      }
      const dry = d.dry_spell;
      if (dry && dry.count > 0) {
        const since = dry.since ? (' since ' + esc(fmtDate(dry.since))) : '';
        const n = dry.count;
        banner +=
            '<div style="margin-bottom:16px;padding:12px 14px;border:1px solid var(--gold);background:rgba(212,175,55,.10);border-radius:8px;color:var(--gold);font-size:13px;line-height:1.5">'
          + '<strong>🌵 No new seeker leads in the last ' + n + ' scan' + (n === 1 ? '' : 's') + '</strong>' + since + '.'
          + '<div style="color:var(--muted);margin-top:4px">Comments are being scanned but none met the seeker-intent threshold'
          + (dry.notified ? ' — an alert email was already sent.' : (dry.threshold ? ' — an alert email fires at ' + dry.threshold + ' consecutive dry scans.' : '.'))
          + ' Consider adding more channels or checking that watched channels are still active.</div>'
          + '<div style="margin-top:8px"><button class="btn btn-secondary btn-sm" id="ld-dry-scan-btn" onclick="ldDryScan()">🔄 Scan now</button></div>'
          + '</div>';
      }
      const nf = d.network_failure;
      if (nf && nf.count > 0) {
        const nfSince = nf.since ? (' since ' + esc(fmtDate(nf.since))) : '';
        const nfN = nf.count;
        banner +=
            '<div style="margin-bottom:16px;padding:12px 14px;border:1px solid #e57373;background:rgba(229,115,115,.12);border-radius:8px;color:#ffb4b4;font-size:13px;line-height:1.5">'
          + '<strong>📡 ' + nfN + ' scan' + (nfN === 1 ? '' : 's') + ' in a row failed on network errors</strong>' + nfSince + '.'
          + '<div style="color:var(--muted);margin-top:4px">YouTube could not be reached at all during these scans'
          + (nf.last_error ? ' — last error: ' + esc(nf.last_error) + '.' : '.')
          + (nf.notified ? ' An alert email was already sent.' : (nf.threshold ? ' An alert email fires at ' + nf.threshold + ' consecutive failed scans.' : ''))
          + ' Scanning retries automatically every few hours.</div>'
          + '</div>';
      }
      $('ld-status').innerHTML =
          banner
        + '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:14px">'
        + '<div><div style="font-size:12px;color:var(--muted)">API</div><div style="font-size:15px;font-weight:600">' + cfg + '</div></div>'
        + '<div><div style="font-size:12px;color:var(--muted)">Channels watched</div><div style="font-size:22px;font-weight:700">' + (d.channels || 0) + '</div></div>'
        + '<div><div style="font-size:12px;color:var(--muted)">Videos tracked</div><div style="font-size:22px;font-weight:700">' + (d.videos_tracked || 0) + '</div></div>'
        + '<div><div style="font-size:12px;color:var(--muted)">Pending leads</div><div style="font-size:22px;font-weight:700;color:var(--gold)">' + (d.pending_leads || 0) + '</div></div>'
        + '</div>'
        + '<div style="margin-top:16px"><div style="font-size:12px;color:var(--muted);margin-bottom:4px">Daily API quota — ' + (q.units_used || 0) + ' / ' + (q.cap || 0) + ' units (' + pct + '%)</div>'
        + '<div style="height:8px;background:rgba(255,255,255,.08);border-radius:4px;overflow:hidden"><div style="height:100%;width:' + pct + '%;background:var(--gold)"></div></div></div>';
    } catch (e) {
      $('ld-status').innerHTML = '<div class="empty-row">Could not load status.</div>';
    }
  }

  async function ldLoadChannels() {
    try {
      const res = await apiFetch('/leads/channels');
      if (!res.ok) return;
      const d = await res.json();
      const chs = d.channels || [];
      ldRenderChannelFilter(chs);
      if (!chs.length) { $('ld-channels').innerHTML = '<div class="empty-row">No channels watched yet. Add one above.</div>'; return; }
      $('ld-channels').innerHTML = chs.map(function (c) {
        const last = c.last_checked_at ? ('Last scan ' + fmtDate(c.last_checked_at)) : 'Not scanned yet';
        const nPend = c.pending_leads || 0;
        const badge = nPend > 0
          ? '<span title="Pending leads awaiting review" style="flex-shrink:0;background:rgba(212,175,55,.15);color:var(--gold);border:1px solid rgba(212,175,55,.4);border-radius:12px;padding:2px 10px;font-size:12px;font-weight:700">' + nPend + ' pending</span>'
          : '<span title="No pending leads" style="flex-shrink:0;color:var(--muted);font-size:12px">0 pending</span>';
        return '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--border);border-radius:8px;margin-bottom:8px">'
          + '<div style="min-width:0"><div style="font-weight:600">' + esc(c.title) + '</div>'
          + '<div style="font-size:12px;color:var(--muted)">' + esc(c.category || 'general') + (c.handle ? (' · ' + esc(c.handle)) : '') + ' · ' + esc(last) + '</div></div>'
          + badge
          + '<button class="btn btn-secondary btn-sm" onclick="ldRemoveChannel(' + c.id + ')" style="color:#e57373;flex-shrink:0">🗑 Remove</button>'
          + '</div>';
      }).join('');
    } catch (e) { /* silent */ }
  }

  async function ldAddChannel() {
    const url = $('ld-ch-url').value.trim();
    const cat = $('ld-ch-cat').value.trim() || 'general';
    if (!url) { showBar('ld-status-bar', 'Paste a channel URL, @handle, or ID first.', 'error'); return; }
    showBar('ld-status-bar', 'Looking up channel…', 'info');
    try {
      const res = await apiFetch('/leads/channels', { method: 'POST', body: JSON.stringify({ url: url, category: cat }) });
      const d = await res.json();
      if (!res.ok) { showBar('ld-status-bar', d.detail || 'Could not add channel.', 'error'); return; }
      showBar('ld-status-bar', (d.created ? '✓ Now watching ' : '✓ Updated ') + (d.channel ? d.channel.title : 'channel') + '.', 'success');
      $('ld-ch-url').value = '';
      ldLoadChannels();
      ldLoadStatus();
    } catch (e) { showBar('ld-status-bar', 'Network error.', 'error'); }
  }

  async function ldRemoveChannel(id) {
    if (!confirm('Stop watching this channel? Existing leads are kept.')) return;
    try {
      const res = await apiFetch('/leads/channels/' + id, { method: 'DELETE' });
      if (!res.ok) { showBar('ld-status-bar', 'Could not remove channel.', 'error'); return; }
      showBar('ld-status-bar', '✓ Channel removed.', 'success');
      ldLoadChannels();
      ldLoadStatus();
    } catch (e) { showBar('ld-status-bar', 'Network error.', 'error'); }
  }

  async function ldDryScan() {
    const btn = $('ld-dry-scan-btn');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Scanning…'; }
    try {
      await ldScan();
    } finally {
      const b = $('ld-dry-scan-btn');
      if (b) { b.disabled = false; b.textContent = '🔄 Scan now'; }
    }
  }

  async function ldScan() {
    showBar('ld-status-bar', 'Scanning watched channels for new comment leads…', 'info');
    try {
      const res = await apiFetch('/leads/scan', { method: 'POST' });
      const d = await res.json();
      if (!res.ok) { showBar('ld-status-bar', d.detail || 'Scan failed.', 'error'); return; }
      if (d.status === 'not_configured') { showBar('ld-status-bar', 'YOUTUBE_API_KEY is not set.', 'error'); return; }
      let msg = '✓ Scan complete — ' + (d.new_videos || 0) + ' new videos, ' + (d.comments_scanned || 0) + ' comments, ' + (d.leads_found || 0) + ' new leads.';
      if (d.stopped_early) msg += ' (stopped early — daily quota cap)';
      showBar('ld-status-bar', msg, 'success');
      ldSetUndoVisible(false);
      ldLoadStatus();
      ldLoadLeads();
      ldLoadChannels();
    } catch (e) { showBar('ld-status-bar', 'Network error.', 'error'); }
  }

  function ldRenderChannelFilter(chs) {
    ldChannelList = chs || [];
    ldRenderCategoryFilter(ldChannelList);
    const sel = $('ld-channel');
    if (!sel) return;
    const prev = sel.value;
    const catSel = $('ld-category');
    const cat = catSel ? catSel.value : '';
    const visible = cat
      ? ldChannelList.filter(function (c) { return (c.category || 'general').trim() === cat; })
      : ldChannelList;
    let html = '<option value="">All channels</option>';
    visible.forEach(function (c) {
      const pend = c.pending_leads || 0;
      html += '<option value="' + esc(c.channel_id) + '">' + esc(c.title) + ' (' + esc(c.category || 'general') + ')' + (pend > 0 ? (' — ' + pend + ' pending') : '') + '</option>';
    });
    sel.innerHTML = html;
    if (prev && visible.some(function (c) { return c.channel_id === prev; })) {
      sel.value = prev;
    } else if (ldPendingRestore && ldPendingRestore.channel) {
      ldSetIfOption(sel, ldPendingRestore.channel);
    }
    if (ldPendingRestore) {
      const restored = (ldPendingRestore.channel && sel.value === ldPendingRestore.channel)
        || (catSel && ldPendingRestore.category && catSel.value === ldPendingRestore.category);
      ldPendingRestore = null;
      if (restored) ldLoadLeads(); else ldSaveFilters();
    }
  }

  function ldRenderCategoryFilter(chs) {
    const sel = $('ld-category');
    if (!sel) return;
    const prev = sel.value;
    const cats = [];
    const catPending = {};
    (chs || []).forEach(function (c) {
      const cat = (c.category || 'general').trim();
      if (!cat) return;
      if (cats.indexOf(cat) === -1) cats.push(cat);
      catPending[cat] = (catPending[cat] || 0) + (c.pending_leads || 0);
    });
    cats.sort();
    let html = '<option value="">All categories</option>';
    cats.forEach(function (cat) {
      const pend = catPending[cat] || 0;
      html += '<option value="' + esc(cat) + '">' + esc(cat) + (pend > 0 ? (' — ' + pend + ' pending') : '') + '</option>';
    });
    sel.innerHTML = html;
    if (prev && cats.indexOf(prev) !== -1) {
      sel.value = prev;
    } else if (ldPendingRestore && ldPendingRestore.category && cats.indexOf(ldPendingRestore.category) !== -1) {
      sel.value = ldPendingRestore.category;
    }
  }

  function ldChannelChanged() {
    ldLoadLeads();
  }

  function ldCategoryChanged() {
    ldRenderChannelFilter(ldChannelList);
    ldLoadLeads();
  }

  async function ldLoadLeads() {
    if (!ldPendingRestore) ldSaveFilters();
    const status = $('ld-filter') ? $('ld-filter').value : 'pending';
    const sort = $('ld-sort') ? $('ld-sort').value : 'intent';
    const channel = $('ld-channel') ? $('ld-channel').value : '';
    const category = $('ld-category') ? $('ld-category').value : '';
    try {
      let url = '/leads?status=' + encodeURIComponent(status) + '&sort=' + encodeURIComponent(sort);
      if (channel) url += '&channel_id=' + encodeURIComponent(channel);
      if (category) url += '&category=' + encodeURIComponent(category);
      const res = await apiFetch(url);
      if (!res.ok) { $('ld-leads').innerHTML = '<div class="empty-row">Could not load leads.</div>'; return; }
      const d = await res.json();
      ldLeads = d.leads || [];
      ldRenderLeads();
      ldUpdateBulkSkipCount();
    } catch (e) {
      $('ld-leads').innerHTML = '<div class="empty-row">Could not load leads.</div>';
    }
  }

  function ldScoreBadge(score) {
    const s = Math.round((score || 0) * 100);
    const color = s >= 80 ? '#4caf50' : (s >= 65 ? 'var(--gold)' : 'var(--muted)');
    const border = s >= 80 ? 'rgba(76,175,80,.5)' : (s >= 65 ? 'rgba(212,175,55,.5)' : 'var(--border)');
    const bg = s >= 80 ? 'rgba(76,175,80,.12)' : (s >= 65 ? 'rgba(212,175,55,.12)' : 'rgba(255,255,255,.04)');
    return '<span style="display:inline-block;font-size:14px;font-weight:800;color:' + color + ';border:1px solid ' + border + ';background:' + bg + ';border-radius:999px;padding:3px 12px">🔥 ' + s + '% intent</span>';
  }

  function ldStatusPill(st) {
    if (st === 'approved') return '<span style="color:#4caf50;font-weight:600">✓ Approved</span>';
    if (st === 'skipped') return '<span style="color:var(--muted);font-weight:600">Skipped</span>';
    return '<span style="color:var(--gold);font-weight:600">Pending</span>';
  }

  function ldRenderLeads() {
    if (!ldLeads.length) { $('ld-leads').innerHTML = '<div class="empty-row">No leads here yet. Add channels and run a scan.</div>'; return; }
    $('ld-leads').innerHTML = ldLeads.map(function (l) {
      const link = /^https?:\/\//i.test(l.comment_link || '') ? l.comment_link : '#';
      let html = '<div class="card" style="margin-bottom:14px"><div class="card-body" style="padding:16px 18px">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">'
        + '<div>' + ldScoreBadge(l.intent_score) + ' &nbsp; ' + ldStatusPill(l.review_status) + '</div>'
        + '<div style="font-size:12px;color:var(--muted)">' + esc(l.channel_title || '') + '</div></div>'
        + '<div style="font-weight:600;font-size:14px;margin-bottom:4px">' + esc(l.author || 'Anonymous') + '</div>'
        + '<div style="color:var(--text);font-size:14px;white-space:pre-wrap;margin-bottom:8px">' + esc(l.text) + '</div>'
        + '<div style="font-size:12px;color:var(--muted);margin-bottom:10px">On: ' + esc(l.video_title || l.video_id) + '</div>';
      if (l.content_pack) {
        const p = l.content_pack;
        html += '<div style="border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:10px;background:rgba(212,175,55,.05)">'
          + '<div style="font-size:12px;color:var(--gold);font-weight:700;margin-bottom:6px">📦 AI Content Pack</div>'
          + '<div style="font-size:13px;margin-bottom:4px"><strong>Video:</strong> ' + esc(p.video_title || '') + '</div>'
          + '<div style="font-size:13px;margin-bottom:4px"><strong>Email subject:</strong> ' + esc(p.email_subject || '') + '</div>'
          + '</div>';
      }
      html += '<div class="btn-row" style="flex-wrap:wrap">'
        + '<a class="btn btn-secondary btn-sm" href="' + esc(link) + '" target="_blank" rel="noopener noreferrer">▶ Open on YouTube</a>';
      if (l.review_status === 'pending') {
        html += '<button class="btn btn-primary btn-sm" onclick="ldApprove(' + l.id + ', this)">✅ Approve &amp; create content</button>'
          + '<button class="btn btn-secondary btn-sm" onclick="ldSkip(' + l.id + ', this)" style="color:var(--muted)">Skip</button>';
      }
      html += '</div></div></div>';
      return html;
    }).join('');
  }

  async function ldApprove(id, btn) {
    if (btn) {
      if (btn.disabled) return;
      btn.disabled = true;
      btn.dataset.label = btn.innerHTML;
      btn.innerHTML = '⏳ Approving…';
    }
    showBar('ld-status-bar', 'Approving lead and building content pack…', 'info');
    try {
      const res = await apiFetch('/leads/' + id + '/approve', { method: 'POST' });
      const d = await res.json();
      if (!res.ok) {
        showBar('ld-status-bar', d.detail || 'Could not approve lead.', 'error');
        if (btn) { btn.disabled = false; btn.innerHTML = btn.dataset.label || '✅ Approve &amp; create content'; }
        return;
      }
      showBar('ld-status-bar', '✓ Approved — created a topic, a content idea, and an email draft.', 'success');
      ldLoadLeads();
      ldLoadStatus();
      ldLoadChannels();
    } catch (e) {
      showBar('ld-status-bar', 'Network error.', 'error');
      if (btn) { btn.disabled = false; btn.innerHTML = btn.dataset.label || '✅ Approve &amp; create content'; }
    }
  }

  async function ldSkip(id, btn) {
    if (btn) {
      if (btn.disabled) return;
      btn.disabled = true;
    }
    try {
      const res = await apiFetch('/leads/' + id + '/skip', { method: 'POST' });
      if (!res.ok) { showBar('ld-status-bar', 'Could not skip lead.', 'error'); if (btn) btn.disabled = false; return; }
      ldLoadLeads();
      ldLoadStatus();
      ldLoadChannels();
    } catch (e) { showBar('ld-status-bar', 'Network error.', 'error'); if (btn) btn.disabled = false; }
  }

  var ldBulkCountSeq = 0;
  async function ldFetchBulkSkipCount(maxScore) {
    try {
      const res = await apiFetch('/leads/bulk-skip/count?max_score=' + encodeURIComponent(maxScore));
      if (!res.ok) return null;
      const d = await res.json();
      return (typeof d.count === 'number') ? d : null;
    } catch (e) { return null; }
  }

  function ldScoreRangeText(d) {
    if (!d || typeof d.min_score !== 'number' || typeof d.max_score !== 'number') return '';
    const lo = Math.round(d.min_score * 100);
    const hi = Math.round(d.max_score * 100);
    return (lo === hi) ? 'all scoring ' + hi + '%' : 'scores ' + lo + '\u2013' + hi + '%';
  }

  function ldBulkThresholdPct() {
    const num = $('ld-bulk-threshold');
    let v = num ? parseFloat(num.value) : 65;
    if (isNaN(v)) v = 65;
    return Math.min(100, Math.max(0, v));
  }

  var ldThresholdDebounce = null;
  function ldThresholdInput(src) {
    const num = $('ld-bulk-threshold');
    const slider = $('ld-bulk-threshold-slider');
    if (src === 'slider' && num && slider) num.value = slider.value;
    if (src === 'number' && num && slider && num.value !== '') {
      slider.value = ldBulkThresholdPct();
    }
    ldSaveThreshold();
    if (ldThresholdDebounce) clearTimeout(ldThresholdDebounce);
    ldThresholdDebounce = setTimeout(ldUpdateBulkSkipCount, 350);
  }

  async function ldUpdateBulkSkipCount() {
    const el = $('ld-bulk-count');
    if (!el) return;
    const seq = ++ldBulkCountSeq;
    el.textContent = '…';
    const d = await ldFetchBulkSkipCount(ldBulkThresholdPct() / 100);
    if (seq !== ldBulkCountSeq) return;
    if (d === null) { el.textContent = ''; ldRenderNearMisses(null); return; }
    const range = ldScoreRangeText(d);
    el.textContent = 'would skip ' + d.count + ' pending lead' + (d.count === 1 ? '' : 's') + (range ? ' (' + range + ')' : '');
    ldRenderNearMisses(d);
  }

  function ldRenderNearMisses(d) {
    const box = $('ld-bulk-near-miss');
    if (!box) return;
    const list = (d && Array.isArray(d.near_misses)) ? d.near_misses : [];
    if (!list.length) { box.style.display = 'none'; box.innerHTML = ''; return; }
    const rows = list.map(function (m) {
      const s = Math.round((m.score || 0) * 100);
      const who = m.author ? '<strong style="color:var(--text)">' + esc(m.author) + '</strong> ' : '';
      const link = /^https?:\/\//i.test(m.comment_link || '') ? m.comment_link : '';
      let actions = '<span style="white-space:nowrap;margin-left:8px">';
      actions += '<button class="btn btn-primary btn-sm" style="padding:2px 8px;font-size:11px" onclick="ldNearMissApprove(' + m.id + ', this)">✅ Keep &amp; approve</button>';
      if (link) actions += ' <a class="btn btn-secondary btn-sm" style="padding:2px 8px;font-size:11px" href="' + esc(link) + '" target="_blank" rel="noopener noreferrer">▶ Open</a>';
      actions += '</span>';
      return '<div style="margin-top:4px;display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap"><div>' +
        '<span style="font-weight:700;color:var(--gold)">' + s + '%</span> ' + who +
        '<span>&ldquo;' + esc(m.snippet || '') + '&rdquo;</span></div>' + actions + '</div>';
    }).join('');
    box.innerHTML = '<div style="font-weight:600;color:var(--text)">Closest keepers just above the cutoff \u2014 worth a quick look before clearing:</div>' + rows;
    box.style.display = '';
  }

  async function ldNearMissApprove(id, btn) {
    if (btn) {
      if (btn.disabled) return;
      btn.disabled = true;
      btn.dataset.label = btn.innerHTML;
      btn.innerHTML = '⏳ Approving…';
    }
    showBar('ld-status-bar', 'Approving lead and building content pack…', 'info');
    try {
      const res = await apiFetch('/leads/' + id + '/approve', { method: 'POST' });
      const d = await res.json();
      if (!res.ok) {
        showBar('ld-status-bar', d.detail || 'Could not approve lead.', 'error');
        if (btn) { btn.disabled = false; btn.innerHTML = btn.dataset.label || '✅ Keep &amp; approve'; }
        return;
      }
      showBar('ld-status-bar', '✓ Kept — approved lead, created a topic, a content idea, and an email draft.', 'success');
      ldUpdateBulkSkipCount();
      ldLoadLeads();
      ldLoadStatus();
      ldLoadChannels();
    } catch (e) {
      showBar('ld-status-bar', 'Network error.', 'error');
      if (btn) { btn.disabled = false; btn.innerHTML = btn.dataset.label || '✅ Keep &amp; approve'; }
    }
  }

  function ldNearMissConfirmText(d) {
    const list = (d && Array.isArray(d.near_misses)) ? d.near_misses : [];
    if (!list.length) return '';
    const parts = list.map(function (m) {
      const s = Math.round((m.score || 0) * 100);
      const snip = String(m.snippet || '').slice(0, 60);
      return s + '% ' + (m.author ? m.author + ': ' : '') + '"' + snip + '"';
    });
    return ' Closest keepers just above the cutoff: ' + parts.join(' | ') + '.';
  }

  async function ldBulkSkip(btn) {
    const pct = Math.round(ldBulkThresholdPct());
    const maxScore = pct / 100;
    const d = await ldFetchBulkSkipCount(maxScore);
    const n = (d === null) ? null : d.count;
    const range = ldScoreRangeText(d);
    const countLine = (n === null)
      ? 'Skip every pending lead scoring under ' + pct + '% intent?'
      : 'This will skip ' + n + ' pending lead' + (n === 1 ? '' : 's') + (range ? ' (' + range + ')' : '') + ' scoring under ' + pct + '% intent.';
    if (n === 0) { showBar('ld-status-bar', 'No pending leads score under ' + pct + '% — nothing to skip.', 'info'); return; }
    if (!confirm(countLine + ldNearMissConfirmText(d) + ' Approved and already-skipped leads are not touched. You can undo right after if it clears too many.')) return;
    if (btn) {
      if (btn.disabled) return;
      btn.disabled = true;
      btn.dataset.label = btn.innerHTML;
      btn.innerHTML = '⏳ Skipping…';
    }
    try {
      const res = await apiFetch('/leads/bulk-skip', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ max_score: maxScore }) });
      const d = await res.json();
      if (!res.ok) { showBar('ld-status-bar', d.detail || 'Could not bulk-skip leads.', 'error'); if (btn) { btn.disabled = false; btn.innerHTML = btn.dataset.label || '🧹 Skip all under threshold'; } return; }
      showBar('ld-status-bar', '✓ Skipped ' + (d.skipped || 0) + ' lead' + ((d.skipped === 1) ? '' : 's') + ' under ' + pct + '% intent.', 'success');
      ldSetUndoVisible((d.skipped || 0) > 0 ? { size: d.skipped, at: new Date().toISOString() } : null);
      ldLoadLeads();
      ldLoadStatus();
      ldLoadChannels();
    } catch (e) {
      showBar('ld-status-bar', 'Network error.', 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = btn.dataset.label || '🧹 Skip all under threshold'; }
    }
  }

  function ldRelTime(iso) {
    if (!iso) return '';
    const t = Date.parse(iso);
    if (isNaN(t)) return '';
    const mins = Math.max(0, Math.round((Date.now() - t) / 60000));
    if (mins < 1) return 'just now';
    if (mins < 60) return mins + 'm ago';
    const hrs = Math.round(mins / 60);
    if (hrs < 24) return hrs + 'h ago';
    return Math.round(hrs / 24) + 'd ago';
  }

  let ldUndoInfo = null;
  let ldUndoTimer = null;

  function ldRenderUndoLabel() {
    const el = $('ld-undo-bulk-skip');
    if (!el || !ldUndoInfo) return;
    const info = ldUndoInfo;
    const rel = ldRelTime(info.at);
    el.textContent = '↩️ Undo bulk-skip (' + info.size + ' lead' + (info.size === 1 ? '' : 's') + (rel ? ', ' + rel : '') + ')';
    el.title = info.at ? 'Batch skipped ' + (rel || 'recently') + ' — restores ' + info.size + ' lead' + (info.size === 1 ? '' : 's') + ' to pending.' : '';
  }

  function ldSetUndoVisible(info) {
    const el = $('ld-undo-bulk-skip');
    if (!el) return;
    const show = !!(info && info.size > 0);
    el.style.display = show ? '' : 'none';
    if (show) {
      ldUndoInfo = info;
      ldRenderUndoLabel();
      if (!ldUndoTimer) ldUndoTimer = setInterval(ldRenderUndoLabel, 60000);
    } else {
      ldUndoInfo = null;
      if (ldUndoTimer) { clearInterval(ldUndoTimer); ldUndoTimer = null; }
      el.textContent = '↩️ Undo bulk-skip';
      el.title = '';
    }
  }

  async function ldUndoBulkSkip(btn) {
    if (btn) {
      if (btn.disabled) return;
      btn.disabled = true;
      btn.dataset.label = btn.innerHTML;
      btn.innerHTML = '⏳ Restoring…';
    }
    try {
      const res = await apiFetch('/leads/bulk-skip/undo', { method: 'POST' });
      const d = await res.json();
      if (!res.ok) { showBar('ld-status-bar', d.detail || 'Could not undo the bulk-skip.', 'error'); return; }
      const n = d.restored || 0;
      if (n > 0) {
        showBar('ld-status-bar', '↩️ Restored ' + n + ' lead' + (n === 1 ? '' : 's') + ' to pending.', 'success');
      } else {
        showBar('ld-status-bar', 'Nothing to undo — the leads were already restored, approved, or a new scan ran.', 'error');
      }
      ldSetUndoVisible(false);
      ldLoadLeads();
      ldLoadStatus();
      ldLoadChannels();
    } catch (e) {
      showBar('ld-status-bar', 'Network error.', 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = btn.dataset.label || '↩️ Undo bulk-skip'; }
    }
  }

  // ── Reply Engine ──────────────────────────────────────────
  var reLeadItems = [];
  var reNonces = {};

  async function reLoad() {
    try {
      const res = await apiFetch('/leads?status=all');
      if (!res.ok) { showBar('re-status-bar', 'Could not load leads.', 'error'); return; }
      const d = await res.json();
      reLeadItems = (d.leads || d.items || []).filter(function (l) { return l.review_status !== 'skipped'; });
      reRenderLeads();
    } catch (e) { showBar('re-status-bar', 'Network error.', 'error'); }
  }

  function reIntentBadge(intent) {
    const colors = { SEEKING: '#4caf50', CURIOUS: '#64b5f6', CONFUSED: '#ffb74d', HOSTILE: '#e57373', TESTIMONY: 'var(--gold)' };
    return '<span style="font-weight:700;color:' + (colors[intent] || 'var(--muted)') + '">' + esc(intent) + '</span>';
  }

  function reRenderLeads() {
    const filter = $('re-filter').value;
    const list = reLeadItems.filter(function (l) { return filter === 'all' || l.review_status === filter; });
    if (!list.length) { $('re-leads').innerHTML = '<div class="empty-row">No leads here yet — the Lead Discovery engine feeds this list.</div>'; return; }
    $('re-leads').innerHTML = list.map(function (l) {
      return '<div class="card" style="margin-bottom:14px"><div class="card-body">' +
        '<div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:6px">' +
          '<div style="font-size:13px;color:var(--muted)">' + esc(l.author || 'Commenter') + ' · 🎬 ' + esc(l.video_title || l.video_id || '') + '</div>' +
          '<div style="font-size:13px">Score <strong>' + Number(l.intent_score || 0).toFixed(2) + '</strong> · ' + esc(l.review_status) + '</div>' +
        '</div>' +
        '<div style="margin-bottom:10px;white-space:pre-wrap">' + esc(l.text) + '</div>' +
        '<div style="display:flex;gap:8px;flex-wrap:wrap">' +
          '<button class="btn btn-primary btn-sm" onclick="reGenerateLead(' + l.id + ', false)">⚡ Generate Replies</button>' +
          '<button class="btn btn-secondary btn-sm" onclick="reGenerateLead(' + l.id + ', true)">🔄 Regenerate</button>' +
        '</div>' +
        '<div id="re-pack-' + l.id + '" style="margin-top:12px"></div>' +
      '</div></div>';
    }).join('');
  }

  function reCopyBtns(pack) {
    const friendly = (pack.tones || {}).friendly || {};
    let html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">';
    if (friendly.primary) html += '<button class="btn btn-secondary btn-sm" onclick="copyText(' + jsAttr(friendly.primary) + ', ' + jsAttr('Primary reply') + ')">📋 Copy Primary</button>';
    if (friendly.soft_cta) html += '<button class="btn btn-secondary btn-sm" onclick="copyText(' + jsAttr(friendly.soft_cta) + ', ' + jsAttr('Soft CTA reply') + ')">📋 Copy Soft CTA</button>';
    html += '<button class="btn btn-secondary btn-sm" onclick="copyText(' + jsAttr(reAllText(pack)) + ', ' + jsAttr('All replies') + ')">📋 Copy All</button></div>';
    return html;
  }

  function reAllText(pack) {
    const parts = [];
    ['gentle', 'logical', 'friendly'].forEach(function (tone) {
      const t = (pack.tones || {})[tone] || {};
      parts.push('== ' + tone.toUpperCase() + ' ==');
      if (t.primary) parts.push('Primary: ' + t.primary);
      if (t.expansion) parts.push('Expansion: ' + t.expansion);
      if (t.soft_cta) parts.push('Soft CTA: ' + t.soft_cta);
      if (t.hard_cta) parts.push('Hard CTA: ' + t.hard_cta);
      parts.push('');
    });
    return parts.join('\\n');
  }

  function reReplyBlock(label, text) {
    if (!text) return '';
    return '<div style="margin-bottom:8px"><div style="font-size:12px;font-weight:700;color:var(--gold);margin-bottom:2px">' + esc(label) +
      ' <button class="btn btn-secondary btn-sm" style="padding:1px 8px;font-size:11px" onclick="copyText(' + jsAttr(text) + ', ' + jsAttr(label) + ')">Copy</button></div>' +
      '<div style="white-space:pre-wrap;font-size:13px">' + esc(text) + '</div></div>';
  }

  function rePackHtml(pack) {
    let html = '<div style="border:1px solid rgba(255,215,0,.25);border-radius:10px;padding:12px">' +
      '<div style="margin-bottom:8px">Intent: ' + reIntentBadge(pack.intent) + (pack.high_intent ? ' · <strong style="color:#4caf50">HIGH intent</strong>' : '') +
      ' · <span style="color:var(--muted);font-size:12px">' + esc(pack.content_source === 'ai' ? 'AI-enhanced' : 'Template (AI unavailable)') + '</span></div>' +
      '<div style="font-size:13px;color:var(--muted);margin-bottom:10px">⏰ ' + esc(pack.timing_suggestion || '') + '</div>' +
      reCopyBtns(pack);
    ['gentle', 'logical', 'friendly'].forEach(function (tone) {
      const t = (pack.tones || {})[tone] || {};
      const names = { gentle: '🕊️ Gentle / Pastoral', logical: '📖 Logical / Apologetic', friendly: '💬 Friendly / Conversational' };
      html += '<div style="margin:12px 0 4px;font-weight:700">' + names[tone] + '</div>' +
        reReplyBlock('Primary', t.primary) +
        reReplyBlock('Expansion', t.expansion) +
        reReplyBlock('Soft CTA', t.soft_cta) +
        reReplyBlock('Hard CTA', t.hard_cta);
    });
    html += '<div style="font-size:12px;color:var(--muted);margin-top:8px">' + esc(pack.notes || '') + '</div></div>';
    return html;
  }

  async function reGenerateLead(id, regen) {
    const el = $('re-pack-' + id);
    el.innerHTML = '<div class="empty-row">Generating replies…</div>';
    if (regen) reNonces[id] = (reNonces[id] || 0) + 1;
    try {
      const res = await apiFetch('/replies/generate', {
        method: 'POST',
        body: JSON.stringify({ lead_id: id, regenerate: reNonces[id] || 0 }),
      });
      const d = await res.json();
      if (!res.ok) { el.innerHTML = '<div class="empty-row" style="color:var(--red)">' + esc(d.detail || 'Generation failed.') + '</div>'; return; }
      el.innerHTML = rePackHtml(d);
    } catch (e) { el.innerHTML = '<div class="empty-row" style="color:var(--red)">Network error.</div>'; }
  }

  var reRawNonce = 0;
  async function reGenerateRaw() {
    const comment = $('re-comment').value.trim();
    if (!comment) { showBar('re-status-bar', 'Paste a comment first.', 'error'); return; }
    const el = $('re-raw-result');
    el.innerHTML = '<div class="empty-row">Generating replies…</div>';
    reRawNonce += 1;
    try {
      const res = await apiFetch('/replies/generate', {
        method: 'POST',
        body: JSON.stringify({
          comment_text: comment,
          video_title: $('re-video').value.trim(),
          channel_name: $('re-channel').value.trim(),
          regenerate: reRawNonce,
        }),
      });
      const d = await res.json();
      if (!res.ok) { el.innerHTML = '<div class="empty-row" style="color:var(--red)">' + esc(d.detail || 'Generation failed.') + '</div>'; return; }
      el.innerHTML = rePackHtml(d);
    } catch (e) { el.innerHTML = '<div class="empty-row" style="color:var(--red)">Network error.</div>'; }
  }

  async function reContinue() {
    const thread = $('re-thread').value.trim();
    if (thread.length < 10) { showBar('re-status-bar', 'Paste the reply thread first.', 'error'); return; }
    const el = $('re-thread-result');
    el.innerHTML = '<div class="empty-row">Thinking through the thread…</div>';
    try {
      const res = await apiFetch('/replies/continue', { method: 'POST', body: JSON.stringify({ thread_text: thread }) });
      const d = await res.json();
      if (!res.ok) { el.innerHTML = '<div class="empty-row" style="color:var(--red)">' + esc(d.detail || 'Generation failed.') + '</div>'; return; }
      let html = '<div style="border:1px solid rgba(255,215,0,.25);border-radius:10px;padding:12px">' +
        '<div style="margin-bottom:8px">Thread intent: ' + reIntentBadge(d.intent) + '</div>' +
        '<div style="font-size:13px;color:var(--muted);margin-bottom:10px">⏰ ' + esc(d.timing_suggestion || '') + '</div>';
      const names = { gentle: '🕊️ Gentle', logical: '📖 Logical', friendly: '💬 Friendly' };
      Object.keys(d.replies || {}).forEach(function (tone) {
        html += reReplyBlock(names[tone] || tone, d.replies[tone]);
      });
      html += '</div>';
      el.innerHTML = html;
    } catch (e) { el.innerHTML = '<div class="empty-row" style="color:var(--red)">Network error.</div>'; }
  }

  // ── Conversion Engine ─────────────────────────────────────
  const CE_ENDPOINTS = {
    ctr: '/conversion/ctr-phrases',
    email: '/conversion/email',
    landing: '/conversion/landing-cta',
    us: '/conversion/us-optimize',
  };

  async function ceRun(kind) {
    const topic = $('ce-topic').value.trim();
    if (topic.length < 2) { showBar('ce-status-bar', 'Enter a topic first.', 'error'); return; }
    const el = $('ce-result');
    el.innerHTML = '<div class="empty-row">Generating…</div>';
    try {
      const res = await apiFetch(CE_ENDPOINTS[kind], { method: 'POST', body: JSON.stringify({ topic: topic }) });
      const d = await res.json();
      if (!res.ok) { el.innerHTML = '<div class="empty-row" style="color:var(--red)">' + esc(d.detail || 'Generation failed.') + '</div>'; return; }
      if (kind === 'ctr') el.innerHTML = ceCtrHtml(d);
      else if (kind === 'email') el.innerHTML = ceEmailHtml(d);
      else if (kind === 'landing') el.innerHTML = ceLandingHtml(d);
      else el.innerHTML = ceUsHtml(d);
    } catch (e) { el.innerHTML = '<div class="empty-row" style="color:var(--red)">Network error.</div>'; }
  }

  function ceSourceNote(d) {
    return '<div style="font-size:12px;color:var(--muted);margin-bottom:10px">' + esc(d.content_source === 'ai' ? 'AI-enhanced' : 'Template (AI unavailable)') + '</div>';
  }

  function cePhraseRow(phrase, type) {
    return '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.06)">' +
      '<span style="font-size:13px">' + esc(phrase) + '</span>' +
      '<span style="display:flex;gap:6px;flex-shrink:0">' +
        '<button class="btn btn-secondary btn-sm" style="padding:1px 8px;font-size:11px" onclick="copyText(' + jsAttr(phrase) + ', ' + jsAttr('Phrase') + ')">Copy</button>' +
        '<button class="btn btn-secondary btn-sm" style="padding:1px 8px;font-size:11px" onclick="ceSavePhrase(' + jsAttr(phrase) + ', ' + jsAttr(type) + ')">Save</button>' +
      '</span></div>';
  }

  function ceCtrHtml(d) {
    let html = ceSourceNote(d);
    const sections = [['🔥 Titles', d.titles || [], 'title'], ['🪝 Hooks', d.hooks || [], 'hook'], ['👉 CTA Phrases', d.cta_phrases || [], 'cta']];
    sections.forEach(function (s) {
      html += '<div style="font-weight:700;margin:12px 0 4px">' + s[0] + '</div>' + s[1].map(function (p) { return cePhraseRow(p, s[2]); }).join('');
    });
    return html;
  }

  function ceLabeled(label, text) {
    if (!text) return '';
    return '<div style="margin-bottom:8px"><div style="font-size:12px;font-weight:700;color:var(--gold)">' + esc(label) +
      ' <button class="btn btn-secondary btn-sm" style="padding:1px 8px;font-size:11px" onclick="copyText(' + jsAttr(text) + ', ' + jsAttr(label) + ')">Copy</button></div>' +
      '<div style="white-space:pre-wrap;font-size:13px">' + esc(text) + '</div></div>';
  }

  function ceEmailHtml(d) {
    const all = ['Subject: ' + (d.subject_line || ''), '', d.opening_hook || '', '', d.teaching_body || '', '', d.youtube_cta || '', '', d.reply_prompt || ''].join('\\n');
    return ceSourceNote(d) +
      '<button class="btn btn-secondary btn-sm" style="margin-bottom:10px" onclick="copyText(' + jsAttr(all) + ', ' + jsAttr('Full email') + ')">📋 Copy Full Email</button>' +
      ceLabeled('Subject Line', d.subject_line) +
      ceLabeled('Opening Hook', d.opening_hook) +
      ceLabeled('Teaching Body', d.teaching_body) +
      ceLabeled('YouTube CTA', d.youtube_cta) +
      ceLabeled('Reply Prompt', d.reply_prompt);
  }

  function ceLandingHtml(d) {
    return ceSourceNote(d) +
      ceLabeled('Headline', d.headline) +
      ceLabeled('Subheadline', d.subheadline) +
      ceLabeled('Button Text', d.button_text);
  }

  function ceUsHtml(d) {
    let html = ceSourceNote(d) + ceLabeled('Phrasing Adjustments', d.phrasing_adjustments);
    html += '<div style="font-weight:700;margin:12px 0 4px">🔑 US Keywords</div>' +
      (d.keywords || []).map(function (k) { return cePhraseRow(k, 'hook'); }).join('');
    html += '<div style="font-weight:700;margin:12px 0 4px">🎬 US Title Variants</div>' +
      (d.title_variants || []).map(function (t) { return cePhraseRow(t, 'title'); }).join('');
    return html;
  }

  async function ceSavePhrase(phrase, type) {
    try {
      const res = await apiFetch('/ctr/performance', { method: 'POST', body: JSON.stringify({ phrase: phrase, type: type }) });
      if (!res.ok) { toast('Could not save phrase.', '⚠'); return; }
      toast('Phrase saved — log clicks/conversions in Phrase Performance.', '✓');
      ceLoadPerf();
    } catch (e) { toast('Network error.', '⚠'); }
  }

  async function ceLoadPerf() {
    try {
      const res = await apiFetch('/ctr/performance');
      if (!res.ok) return;
      const d = await res.json();
      const items = d.items || [];
      if (!items.length) { $('ce-perf').innerHTML = '<div class="empty-row">No saved phrases yet — generate CTR phrases and hit Save on the ones you use.</div>'; return; }
      $('ce-perf').innerHTML = items.map(function (it) {
        return '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.06)">' +
          '<span style="font-size:13px">' + esc(it.phrase) + ' <span style="color:var(--muted);font-size:11px">(' + esc(it.type) + ')</span></span>' +
          '<span style="display:flex;gap:6px;align-items:center;flex-shrink:0;font-size:12px">' +
            '👆 ' + it.clicks + ' <button class="btn btn-secondary btn-sm" style="padding:1px 7px;font-size:11px" onclick="ceLogPerf(' + it.id + ', 1, 0)">+1</button>' +
            ' ✅ ' + it.conversions + ' <button class="btn btn-secondary btn-sm" style="padding:1px 7px;font-size:11px" onclick="ceLogPerf(' + it.id + ', 0, 1)">+1</button>' +
          '</span></div>';
      }).join('');
    } catch (e) { /* leave as-is */ }
  }

  async function ceLogPerf(id, clicks, conversions) {
    try {
      const res = await apiFetch('/ctr/performance/' + id, { method: 'PATCH', body: JSON.stringify({ clicks: clicks, conversions: conversions }) });
      if (res.ok) ceLoadPerf();
    } catch (e) { /* ignore */ }
  }

  // ── Growth Pack ───────────────────────────────────────────
  function gpInit() {
    if ($('gp-triggers').dataset.loaded !== '1') gpTriggers();
  }

  function gpBandColor(band) {
    if (band === 'Elite') return '#4caf50';
    if (band === 'Strong') return 'var(--gold)';
    if (band === 'Average') return '#e0a92b';
    return 'var(--muted)';
  }

  function gpScoreCard(r) {
    let html = '<div class="card" style="margin-bottom:12px"><div class="card-body" style="padding:14px 16px">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">';
    html += '<span style="font-size:13px;font-weight:600">' + esc(r.title) + '</span>';
    html += '<span style="flex-shrink:0;font-weight:800;color:' + gpBandColor(r.band) + '">' + r.score + '/100 · ' + esc(r.band) + '</span>';
    html += '</div>';
    const c = r.components || {};
    const labels = { length_fit: 'Length', curiosity: 'Curiosity', emotional_pull: 'Emotion', specificity: 'Specificity', clarity: 'Clarity' };
    html += '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:8px;font-size:11px;color:var(--muted)">';
    Object.keys(labels).forEach(function (k) { if (c[k] !== undefined) html += '<span>' + labels[k] + ': ' + c[k] + '</span>'; });
    html += '</div>';
    if ((r.reasons || []).length) html += '<ul style="margin:8px 0 0;padding-left:18px;font-size:12px;color:#9fca9f">' + r.reasons.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>';
    if ((r.tips || []).length) html += '<ul style="margin:6px 0 0;padding-left:18px;font-size:12px;color:#d8b46a">' + r.tips.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>';
    html += '</div></div>';
    return html;
  }

  async function gpScore() {
    const raw = $('gp-titles').value.split('\\n').map(function (s) { return s.trim(); }).filter(Boolean);
    if (!raw.length) { showBar('gp-score-status-bar', 'Paste at least one title.', 'error'); return; }
    const el = $('gp-score-result');
    el.innerHTML = '<div class="empty-row">Scoring…</div>';
    try {
      const res = await apiFetch('/growth/score-title', { method: 'POST', body: JSON.stringify({ titles: raw }) });
      const d = await res.json();
      if (!res.ok) { el.innerHTML = '<div class="empty-row" style="color:var(--red)">' + esc(d.detail || 'Scoring failed.') + '</div>'; return; }
      const results = d.results || (d.result ? [d.result] : []);
      el.innerHTML = results.map(gpScoreCard).join('');
    } catch (e) { el.innerHTML = '<div class="empty-row" style="color:var(--red)">Network error.</div>'; }
  }

  function gpList(title, items, type) {
    if (!items || !items.length) return '';
    let html = '<div style="font-weight:700;margin:14px 0 4px">' + title + '</div>';
    html += items.map(function (p) {
      return '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.06)">' +
        '<span style="font-size:13px">' + esc(p) + '</span>' +
        '<button class="btn btn-secondary btn-sm" style="padding:1px 8px;font-size:11px;flex-shrink:0" onclick="copyText(' + jsAttr(p) + ', ' + jsAttr(type) + ')">Copy</button>' +
      '</div>';
    }).join('');
    return html;
  }

  function gpBrainHtml(d) {
    let html = '<div style="font-size:12px;color:var(--muted);margin-bottom:10px">' + esc(d.content_source === 'ai' ? 'AI-enhanced' : 'Template (AI unavailable)');
    if (d.email_draft_id) html += ' · Newsletter draft #' + d.email_draft_id + ' queued';
    html += '</div>';
    if (d.best_title) {
      html += '<div style="font-weight:700;margin:4px 0">🏆 Best Title (predicted CTR)</div>' + gpScoreCard(d.best_title);
    }
    html += (d.optimized_titles || []).slice(1).map(gpScoreCard).join('');
    const hooks = (d.viral_hooks || []).map(function (h) { return h.hook + '  (intensity ' + h.intensity + ')'; });
    html += gpList('🪝 Viral Hooks', hooks, 'Hook');
    const us = d.us_targeting || {};
    html += gpList('🔑 US Keywords', us.keywords || [], 'Keyword');
    const cs = d.conversion_scripts || {};
    html += gpList('📌 Pinned Comment', cs.pinned_comment ? [cs.pinned_comment] : [], 'Pinned comment');
    html += gpList('👉 CTA Phrases', cs.cta_phrases || [], 'CTA');
    html += gpList('🔔 Subscribe / Watch-Next', [cs.subscribe_cta, cs.watch_next_cta].filter(Boolean), 'CTA');
    const lc = d.landing_cta || {};
    html += gpList('🖥️ Landing CTA', [lc.headline, lc.subheadline, lc.button_text].filter(Boolean), 'Landing copy');
    return html;
  }

  async function gpBrain() {
    const topic = $('gp-topic').value.trim();
    if (topic.length < 2) { showBar('gp-status-bar', 'Enter a topic first.', 'error'); return; }
    const el = $('gp-result');
    el.innerHTML = '<div class="empty-row">Building growth pack…</div>';
    try {
      const res = await apiFetch('/growth/brain', { method: 'POST', body: JSON.stringify({ topic: topic, create_email_draft: $('gp-draft').checked }) });
      const d = await res.json();
      if (!res.ok) { el.innerHTML = '<div class="empty-row" style="color:var(--red)">' + esc(d.detail || 'Build failed.') + '</div>'; return; }
      el.innerHTML = gpBrainHtml(d);
      if (d.email_draft_id) toast('Newsletter draft queued — approve it in Email Queue.', '✓');
    } catch (e) { el.innerHTML = '<div class="empty-row" style="color:var(--red)">Network error.</div>'; }
  }

  async function gpTriggers() {
    const el = $('gp-triggers');
    const topic = $('gp-topic') ? $('gp-topic').value.trim() : '';
    el.innerHTML = '<div class="empty-row">Loading…</div>';
    try {
      const res = await apiFetch('/growth/trigger-phrases' + (topic ? ('?topic=' + encodeURIComponent(topic)) : ''));
      const d = await res.json();
      if (!res.ok) { el.innerHTML = '<div class="empty-row" style="color:var(--red)">Could not load phrases.</div>'; return; }
      const cats = d.categories || {};
      const labels = { curiosity_gap: 'Curiosity Gap', authority_reversal: 'Authority Reversal', us_searcher: 'US Searcher', urgency: 'Urgency', social_proof: 'Social Proof', subscribe_cta: 'Subscribe CTA' };
      el.innerHTML = Object.keys(cats).map(function (k) { return gpList('⚡ ' + (labels[k] || k), cats[k], 'Phrase'); }).join('');
      el.dataset.loaded = '1';
    } catch (e) { el.innerHTML = '<div class="empty-row" style="color:var(--red)">Network error.</div>'; }
  }

  // ── Audience Geography ────────────────────────────────────
  async function geoLoad() {
    const el = $('geo-content');
    el.innerHTML = '<div class="empty-row">Loading…</div>';
    try {
      const res = await apiFetch('/analytics/geo?days=' + $('geo-days').value);
      if (!res.ok) { showBar('geo-status-bar', 'Could not load geography data.', 'error'); return; }
      const d = await res.json();
      if (!d.total_located_visits) {
        el.innerHTML = '<div class="empty-row">No geo data yet. Visits are located (coarsely, privacy-safe) as people view the landing page.</div>';
        return;
      }
      let html = '<div style="display:flex;gap:18px;flex-wrap:wrap;margin-bottom:16px">' +
        '<div><div style="font-size:24px;font-weight:800;color:var(--gold)">' + d.total_located_visits + '</div><div style="font-size:12px;color:var(--muted)">Located visits</div></div>' +
        '<div><div style="font-size:24px;font-weight:800;color:var(--gold)">' + d.pct_usa + '%</div><div style="font-size:12px;color:var(--muted)">USA traffic</div></div>' +
      '</div>';
      html += geoBarList('🌍 Top Countries', d.top_countries || [], 'country');
      html += geoBarList('🇺🇸 Top US States', d.top_us_regions || [], 'region');
      const trend = d.trend || [];
      if (trend.length) {
        html += '<div style="font-weight:700;margin:14px 0 6px">📈 Trend (daily visits · US share)</div>' +
          trend.slice(-14).map(function (t) {
            const pct = t.total ? Math.round(100 * t.us / t.total) : 0;
            return '<div style="display:flex;gap:10px;font-size:12px;padding:2px 0"><span style="width:80px;color:var(--muted)">' + esc(t.date) + '</span>' +
              '<span style="width:60px">' + t.total + ' visits</span><span>' + pct + '% US</span></div>';
          }).join('');
      }
      el.innerHTML = html;
    } catch (e) { showBar('geo-status-bar', 'Network error.', 'error'); }
  }

  function geoBarList(title, items, key) {
    if (!items.length) return '';
    const max = Math.max.apply(null, items.map(function (i) { return i.visits; }));
    return '<div style="font-weight:700;margin:14px 0 6px">' + title + '</div>' + items.map(function (i) {
      const w = max ? Math.max(4, Math.round(100 * i.visits / max)) : 4;
      return '<div style="display:flex;align-items:center;gap:8px;padding:2px 0;font-size:13px">' +
        '<span style="width:110px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + esc(i[key]) + '</span>' +
        '<span style="flex:1;background:rgba(255,255,255,.06);border-radius:4px;height:12px"><span style="display:block;height:12px;border-radius:4px;width:' + w + '%;background:linear-gradient(90deg,var(--gold),#ffb43d)"></span></span>' +
        '<span style="width:44px;text-align:right;color:var(--muted)">' + i.visits + '</span></div>';
    }).join('');
  }

  // ── Lead Evangelist ───────────────────────────────────────
  var lePlaybook = null;

  function leInit() {
    leLoadPlaybook();
    leLoadOutreach();
    leLoadDashboard();
    leLoadAuto();
  }

  var leAutoEnabled = true;

  async function leLoadAuto() {
    try {
      const res = await apiFetch('/evangelist/auto');
      const d = await res.json();
      leAutoEnabled = !!d.enabled;
      const fmt = function (iso) { return iso ? new Date(iso + 'Z').toLocaleString() : '—'; };
      $('le-auto-status').innerHTML =
        '<div style="font-size:13px;line-height:1.8">' +
        'Status: <strong style="color:' + (d.enabled ? '#4caf50' : '#e57373') + '">' + (d.enabled ? 'ON' : 'OFF') + '</strong><br>' +
        'Best posting hour (from your visitors): <strong>' + String(d.best_hour_utc).padStart(2, '0') + ':00 UTC</strong><br>' +
        'Last post prepared: <strong>' + esc(fmt(d.last_prepared_at)) + '</strong><br>' +
        'Next one due: <strong>' + (d.last_prepared_at ? esc(fmt(d.next_due_at)) : 'at the next best hour') + '</strong><br>' +
        'Next platform up: <strong>' + esc(d.next_platform) + '</strong> <span class="hint">(rotation: ' + d.rotation.map(esc).join(' → ') + ')</span></div>';
      $('le-auto-toggle').textContent = d.enabled ? 'Turn Off' : 'Turn On';
    } catch (e) {
      $('le-auto-status').innerHTML = '<div class="empty-row">Failed to load Auto-Cadence status.</div>';
    }
  }

  async function leAutoToggle() {
    try {
      const res = await apiFetch('/evangelist/auto', { method: 'PUT', body: JSON.stringify({ enabled: !leAutoEnabled }) });
      if (!res.ok) throw new Error('Failed');
      toast('Auto-Cadence ' + (!leAutoEnabled ? 'enabled' : 'disabled') + '.', '✓');
      leLoadAuto();
    } catch (e) {
      toast('Failed to update Auto-Cadence.', '✗');
    }
  }

  async function leLoadPlaybook() {
    try {
      const res = await apiFetch('/evangelist/playbook');
      lePlaybook = await res.json();
      const opts = lePlaybook.platforms.map(function (p) {
        return '<option value="' + esc(p.key) + '">' + esc(p.label) + '</option>';
      }).join('');
      $('le-platform').innerHTML = opts;
      $('le-log-platform').innerHTML = opts;
      var html = '<div class="hint" style="margin-bottom:10px">' + lePlaybook.principles.map(function (p) { return '• ' + esc(p); }).join('<br>') + '</div>';
      html += lePlaybook.messages.map(function (m) {
        return '<div style="border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:10px">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px">' +
          '<strong>' + esc(m.label) + '</strong>' +
          '<button class="btn btn-sm" onclick="leCopyMsg(' + jsAttr(JSON.stringify(m.key)) + ')">Copy</button></div>' +
          '<div class="hint">Best for: ' + esc(m.best_for) + '</div>' +
          '<pre style="white-space:pre-wrap;font-size:12px;margin:8px 0 0">' + esc(m.text) + '</pre></div>';
      }).join('');
      html += '<div class="hint" style="margin-top:8px"><strong>Platform etiquette &amp; daily pace caps:</strong></div>';
      html += lePlaybook.platforms.map(function (p) {
        return '<div style="border:1px solid var(--border);border-radius:8px;padding:10px;margin-top:8px">' +
          '<strong>' + esc(p.label) + '</strong> <span class="hint">(max ' + p.daily_cap + '/day · <a href="' + esc(p.tracked_link) + '" target="_blank" rel="noopener">tracked link</a>)</span>' +
          '<div class="hint">' + p.etiquette.map(esc).join('<br>') + '</div></div>';
      }).join('');
      $('le-playbook').innerHTML = html;
    } catch (e) {
      $('le-playbook').innerHTML = '<div class="empty-row">Failed to load playbook.</div>';
    }
  }

  function leCopyMsg(key) {
    if (!lePlaybook) return;
    const m = lePlaybook.messages.find(function (x) { return x.key === key; });
    if (m) copyText(m.text, 'Message');
  }

  async function lePersonalize() {
    const bar = $('le-personalize-status');
    bar.textContent = 'Personalizing…';
    try {
      const res = await apiFetch('/evangelist/personalize', { method: 'POST', body: JSON.stringify({
        platform: $('le-platform').value,
        message_type: $('le-msgtype').value,
        context: $('le-context').value,
      }) });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Failed');
      bar.textContent = '';
      const s = d.spam_safety || {};
      const paceColor = s.over_cap ? '#e57373' : '#4caf50';
      $('le-personalize-out').innerHTML =
        '<div style="border:1px solid var(--border);border-radius:8px;padding:12px;margin-top:10px">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px">' +
        '<strong>' + esc(d.platform) + ' · ' + esc(d.message_type) + '</strong>' +
        '<button class="btn btn-sm" onclick="leCopyPersonalized()">Copy</button></div>' +
        '<pre id="le-personalized-text" style="white-space:pre-wrap;font-size:12px;margin:8px 0">' + esc(d.message) + '</pre>' +
        '<div class="hint" style="color:' + paceColor + '">Pace today: ' + (s.used_today || 0) + '/' + (s.daily_cap || 0) +
        (s.over_cap ? ' — daily cap reached. Post tomorrow instead; slow and sincere beats fast and flagged.' : ' — ' + (s.remaining_today || 0) + ' left today.') + '</div>' +
        '<div class="hint">' + esc(s.reminder || '') + '</div></div>';
    } catch (e) {
      bar.textContent = 'Failed: ' + e.message;
    }
  }

  function leCopyPersonalized() {
    const el = $('le-personalized-text');
    if (el) copyText(el.textContent, 'Message');
  }

  async function leLogOutreach() {
    const bar = $('le-log-status');
    bar.textContent = 'Saving…';
    try {
      const res = await apiFetch('/evangelist/outreach', { method: 'POST', body: JSON.stringify({
        platform: $('le-log-platform').value,
        target: $('le-log-target').value,
        notes: $('le-log-notes').value,
      }) });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Failed');
      bar.textContent = '';
      $('le-log-target').value = '';
      $('le-log-notes').value = '';
      toast('Outreach logged.', '✓');
      leLoadOutreach();
      leLoadDashboard();
    } catch (e) {
      bar.textContent = 'Failed: ' + e.message;
    }
  }

  async function leLoadOutreach() {
    try {
      const res = await apiFetch('/evangelist/outreach');
      const d = await res.json();
      if (!d.items || !d.items.length) {
        $('le-outreach-list').innerHTML = '<div class="empty-row">No outreach logged yet.</div>';
        return;
      }
      $('le-outreach-list').innerHTML = d.items.map(function (r) {
        const when = r.created_at ? new Date(r.created_at).toLocaleDateString() : '';
        return '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;border-bottom:1px solid var(--border);padding:8px 0;font-size:13px">' +
          '<div><strong>' + esc(r.platform) + '</strong> · ' + esc(r.target || '(no target)') + ' <span class="hint">' + esc(when) + ' · ' + esc(r.status) + '</span>' +
          (r.notes ? '<div class="hint">' + esc(r.notes) + '</div>' : '') + '</div>' +
          '<div style="white-space:nowrap">' +
          '<button class="btn btn-sm" onclick="leSetStatus(' + r.id + ', \\'responded\\')">Responded</button> ' +
          '<button class="btn btn-sm" onclick="leSetStatus(' + r.id + ', \\'subscribed\\')">Subscribed</button></div></div>';
      }).join('');
    } catch (e) {
      $('le-outreach-list').innerHTML = '<div class="empty-row">Failed to load outreach log.</div>';
    }
  }

  async function leSetStatus(id, status) {
    try {
      const res = await apiFetch('/evangelist/outreach/' + id, { method: 'PATCH', body: JSON.stringify({ status: status }) });
      if (!res.ok) throw new Error('Failed');
      toast('Marked ' + status + '.', '✓');
      leLoadOutreach();
      leLoadDashboard();
    } catch (e) {
      toast('Failed to update status.', '✗');
    }
  }

  async function leLoadDashboard() {
    try {
      const res = await apiFetch('/evangelist/dashboard');
      const d = await res.json();
      const t = d.totals || {};
      var html = '<div class="hint" style="margin-bottom:8px">Total outreach: <strong>' + (t.outreach || 0) + '</strong> · Responded: <strong>' + (t.responded || 0) + '</strong> · Subscribed: <strong>' + (t.subscribed || 0) + '</strong></div>';
      html += '<table class="table"><thead><tr><th>Platform</th><th>Outreach</th><th>Responded</th><th>Subscribed</th><th>Today</th></tr></thead><tbody>';
      html += (d.platforms || []).map(function (p) {
        const pace = p.over_cap ? '<span style="color:#e57373">' + p.used_today + '/' + p.daily_cap + ' (cap)</span>' : p.used_today + '/' + p.daily_cap;
        return '<tr><td>' + esc(p.label) + '</td><td>' + p.outreach_total + '</td><td>' + p.responded + '</td><td>' + p.subscribed + '</td><td>' + pace + '</td></tr>';
      }).join('');
      html += '</tbody></table>';
      const srcs = d.signup_sources || {};
      const keys = Object.keys(srcs);
      if (keys.length) {
        html += '<div class="hint" style="margin-top:10px"><strong>Signups attributed by platform link:</strong> ' +
          keys.map(function (k) { return esc(k) + ': ' + srcs[k]; }).join(' · ') + '</div>';
      } else {
        html += '<div class="hint" style="margin-top:10px">No attributed signups yet — attribution appears once someone signs up through a tracked link.</div>';
      }
      $('le-dashboard').innerHTML = html;
    } catch (e) {
      $('le-dashboard').innerHTML = '<div class="empty-row">Failed to load dashboard.</div>';
    }
  }

  // ── Growth Brain ──────────────────────────────────────────
  function gbVerdictColor(v) {
    if (v === 'High CTR') return '#4caf50';
    if (v === 'Medium') return 'var(--gold)';
    return '#e57373';
  }

  function gbScoreCard(r) {
    const bd = r.breakdown || {};
    const bars = [
      ['Curiosity', bd.curiosity, 25],
      ['Clarity', bd.clarity, 20],
      ['Emotional pull', bd.emotional_pull, 20],
      ['Keyword strength', bd.keyword_strength, 20],
      ['Length', bd.length, 15],
    ].map(function (row) {
      const pct = row[2] ? Math.round(100 * (row[1] || 0) / row[2]) : 0;
      return '<div style="display:flex;align-items:center;gap:10px;font-size:12px;padding:2px 0">' +
        '<span style="width:120px;color:var(--muted)">' + row[0] + '</span>' +
        '<span style="flex:1;height:8px;background:rgba(255,255,255,.08);border-radius:4px;overflow:hidden"><span style="display:block;height:100%;width:' + pct + '%;background:var(--gold)"></span></span>' +
        '<span style="width:48px;text-align:right">' + (row[1] || 0) + '/' + row[2] + '</span></div>';
    }).join('');
    const tips = (r.improvements || []).map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('');
    return '<div style="border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:14px">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px">' +
        '<div><div style="font-size:32px;font-weight:800;color:' + gbVerdictColor(r.verdict) + '">' + r.score + '<span style="font-size:15px;color:var(--muted)">/100</span></div>' +
        '<div style="font-size:13px;font-weight:600;color:' + gbVerdictColor(r.verdict) + '">' + esc(r.verdict) + '</div></div>' +
        '<div style="display:flex;gap:6px;flex-wrap:wrap">' +
          '<button class="btn btn-secondary btn-sm" onclick="copyText(' + jsAttr(r.title) + ', \\'Title\\')">Copy</button>' +
          '<button class="btn btn-primary btn-sm" onclick="gbSaveTitle(' + jsAttr(r.title) + ', ' + r.score + ')">💾 Save to Track</button>' +
        '</div>' +
      '</div>' + bars +
      (tips ? '<div style="margin-top:12px"><div style="font-weight:700;font-size:12px;margin-bottom:4px">💡 Improvements</div><ul style="margin:0;padding-left:18px;font-size:12px;color:var(--muted)">' + tips + '</ul></div>' : '') +
    '</div>';
  }

  async function gbScore() {
    const title = ($('gb-title').value || '').trim();
    if (!title) { showBar('gb-score-bar', 'Enter a title to score.', 'error'); return; }
    showBar('gb-score-bar', 'Scoring…', 'info');
    try {
      const res = await apiFetch('/growth-brain/score-title', { method: 'POST', body: JSON.stringify({ title: title }) });
      if (!res.ok) { showBar('gb-score-bar', 'Could not score that title.', 'error'); return; }
      const r = await res.json();
      $('gb-score-bar').style.display = 'none';
      $('gb-score-result').innerHTML = gbScoreCard(r);
    } catch (e) { showBar('gb-score-bar', 'Network error.', 'error'); }
  }

  function gbTitleRow(r) {
    return '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.06)">' +
      '<span style="font-size:13px"><span style="color:' + gbVerdictColor(r.verdict) + ';font-weight:700">' + r.score + '</span> ' + esc(r.title) + '</span>' +
      '<span style="display:flex;gap:6px;flex-shrink:0">' +
        '<button class="btn btn-secondary btn-sm" style="padding:1px 8px;font-size:11px" onclick="copyText(' + jsAttr(r.title) + ', \\'Title\\')">Copy</button>' +
        '<button class="btn btn-primary btn-sm" style="padding:1px 8px;font-size:11px" onclick="gbSaveTitle(' + jsAttr(r.title) + ', ' + r.score + ')">Save</button>' +
      '</span></div>';
  }

  function gbChipList(title, items) {
    if (!items || !items.length) return '';
    return '<div style="font-weight:700;font-size:13px;margin:12px 0 6px">' + title + '</div>' +
      items.map(function (it) {
        return '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:4px 0;font-size:13px">' +
          '<span>' + esc(it) + '</span>' +
          '<button class="btn btn-secondary btn-sm" style="padding:1px 8px;font-size:11px;flex-shrink:0" onclick="copyText(' + jsAttr(it) + ', \\'Text\\')">Copy</button>' +
        '</div>';
      }).join('');
  }

  function gbSourceBadge(src) {
    const label = src === 'ai' ? '✨ AI-enriched' : '⚙️ Deterministic';
    return '<div style="font-size:11px;color:var(--muted);margin-bottom:8px">' + label + '</div>';
  }

  async function gbRun(kind) {
    const topic = ($('gb-topic').value || '').trim();
    if (!topic) { showBar('gb-gen-bar', 'Enter a topic first.', 'error'); return; }
    const paths = { optimized: '/growth-brain/optimized-titles', hooks: '/growth-brain/hooks', keywords: '/growth-brain/keywords' };
    showBar('gb-gen-bar', 'Generating…', 'info');
    $('gb-gen-result').innerHTML = '';
    try {
      const res = await apiFetch(paths[kind], { method: 'POST', body: JSON.stringify({ topic: topic }) });
      if (!res.ok) { showBar('gb-gen-bar', 'Generation failed — please try again.', 'error'); return; }
      const d = await res.json();
      $('gb-gen-bar').style.display = 'none';
      let html = gbSourceBadge(d.content_source);
      if (kind === 'optimized') {
        html += '<div style="font-weight:700;font-size:13px;margin-bottom:6px">🏆 Top 3</div>' +
          (d.top_titles || []).map(gbTitleRow).join('');
        const rest = (d.all_titles_ranked || []).slice(3);
        if (rest.length) html += '<div style="font-weight:700;font-size:13px;margin:12px 0 6px">More candidates</div>' + rest.map(gbTitleRow).join('');
      } else if (kind === 'hooks') {
        html += gbChipList('🪝 Short hooks', d.short_hooks);
        html += gbChipList('📝 Long hooks', d.long_hooks);
        const pt = d.pattern_types || {};
        const names = { curiosity: '🤔 Curiosity', contradiction: '⚡ Contradiction', challenge: '🥊 Challenge', hidden_truth: '🔦 Hidden truth' };
        Object.keys(names).forEach(function (k) { html += gbChipList(names[k], pt[k]); });
      } else {
        html += gbChipList('🔑 Primary keywords', d.primary_keywords);
        html += gbChipList('🌾 Long-tail keywords', d.long_tail_keywords);
        html += gbChipList('❓ Questions', d.questions);
        html += gbChipList('🎬 Video titles', d.video_titles);
      }
      $('gb-gen-result').innerHTML = html;
    } catch (e) { showBar('gb-gen-bar', 'Network error.', 'error'); }
  }

  async function gbSaveTitle(title, score) {
    try {
      const res = await apiFetch('/growth-brain/title-performance', { method: 'POST', body: JSON.stringify({ title: title, score: score }) });
      if (res.ok) { toast('Title saved to tracking.', '💾'); gbLoadPerf(); }
      else toast('Could not save title.', '⚠️');
    } catch (e) { toast('Network error.', '⚠️'); }
  }

  async function gbLoadPerf() {
    try {
      const res = await apiFetch('/growth-brain/title-performance');
      if (!res.ok) return;
      const d = await res.json();
      const items = d.items || [];
      if (!items.length) { $('gb-perf').innerHTML = '<div class="empty-row">No saved titles yet — score or generate titles and hit Save on the ones you use.</div>'; return; }
      $('gb-perf').innerHTML = items.map(function (it) {
        return '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.06)">' +
          '<span style="font-size:13px"><span style="color:var(--gold);font-weight:700">' + it.score + '</span> ' + esc(it.title) + '</span>' +
          '<span style="display:flex;gap:6px;align-items:center;flex-shrink:0;font-size:12px">' +
            '👆 ' + it.clicks + ' <button class="btn btn-secondary btn-sm" style="padding:1px 7px;font-size:11px" onclick="gbLogClicks(' + it.id + ')">+clicks</button>' +
            ' 📊 ' + it.ctr + '% <button class="btn btn-secondary btn-sm" style="padding:1px 7px;font-size:11px" onclick="gbLogCtr(' + it.id + ')">set CTR</button>' +
          '</span></div>';
      }).join('');
    } catch (e) { /* leave as-is */ }
  }

  async function gbLogClicks(id) {
    const v = prompt('How many clicks to add?');
    if (v === null) return;
    const n = parseInt(v, 10);
    if (isNaN(n) || n < 0) { toast('Enter a valid number.', '⚠️'); return; }
    try {
      const res = await apiFetch('/growth-brain/title-performance/' + id, { method: 'PATCH', body: JSON.stringify({ clicks: n }) });
      if (res.ok) gbLoadPerf();
    } catch (e) { /* ignore */ }
  }

  async function gbLogCtr(id) {
    const v = prompt('Latest CTR for this title (%)?');
    if (v === null) return;
    const n = parseFloat(v);
    if (isNaN(n) || n < 0 || n > 100) { toast('Enter a CTR between 0 and 100.', '⚠️'); return; }
    try {
      const res = await apiFetch('/growth-brain/title-performance/' + id, { method: 'PATCH', body: JSON.stringify({ clicks: 0, ctr: n }) });
      if (res.ok) gbLoadPerf();
    } catch (e) { /* ignore */ }
  }

  function gbTriggerCategory(cat) {
    const phrases = (cat.phrases || []).map(function (p) {
      return '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:4px 0;font-size:13px">' +
        '<span>' + esc(p) + '</span>' +
        '<button class="btn btn-secondary btn-sm" style="padding:1px 8px;font-size:11px;flex-shrink:0" onclick="copyText(' + jsAttr(p) + ', \\'Phrase\\')">Copy</button>' +
      '</div>';
    }).join('');
    return '<div style="border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:12px;margin-bottom:10px">' +
      '<div style="font-weight:700;font-size:13px;margin-bottom:2px">' + esc(cat.label) + '</div>' +
      (cat.why ? '<div style="font-size:11px;color:var(--muted);margin-bottom:8px">' + esc(cat.why) + '</div>' : '') +
      phrases + '</div>';
  }

  async function gbTriggerLibrary() {
    showBar('gb-trig-bar', 'Loading library…', 'info');
    try {
      const res = await apiFetch('/growth-brain/trigger-phrases');
      if (!res.ok) { showBar('gb-trig-bar', 'Could not load the library.', 'error'); return; }
      const d = await res.json();
      $('gb-trig-bar').style.display = 'none';
      $('gb-trig-result').innerHTML = gbSourceBadge(d.content_source) +
        (d.categories || []).map(gbTriggerCategory).join('');
    } catch (e) { showBar('gb-trig-bar', 'Network error.', 'error'); }
  }

  async function gbTriggerTopic() {
    const topic = ($('gb-topic').value || '').trim();
    if (!topic) { showBar('gb-trig-bar', 'Enter a topic in the box above first.', 'error'); return; }
    showBar('gb-trig-bar', 'Tailoring phrases…', 'info');
    try {
      const res = await apiFetch('/growth-brain/trigger-phrases', { method: 'POST', body: JSON.stringify({ topic: topic }) });
      if (!res.ok) { showBar('gb-trig-bar', 'Generation failed — please try again.', 'error'); return; }
      const d = await res.json();
      $('gb-trig-bar').style.display = 'none';
      const names = { curiosity_gap: 'Curiosity Gap', urgency: 'Urgency & Stakes', authority: 'Authority & Proof', us_targeted: 'US Audience', subscribe_cta: 'Subscribe CTA', comment_cta: 'Comment CTA' };
      let html = gbSourceBadge(d.content_source);
      Object.keys(names).forEach(function (k) { html += gbTriggerCategory({ label: names[k], phrases: d[k] }); });
      $('gb-trig-result').innerHTML = html;
    } catch (e) { showBar('gb-trig-bar', 'Network error.', 'error'); }
  }

  function gbScriptBlock(title, text) {
    if (!text) return '';
    return '<div style="border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:12px;margin-bottom:10px">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px">' +
        '<span style="font-weight:700;font-size:13px">' + title + '</span>' +
        '<button class="btn btn-secondary btn-sm" style="padding:1px 8px;font-size:11px" onclick="copyText(' + jsAttr(text) + ', \\'Script\\')">Copy</button>' +
      '</div>' +
      '<div style="font-size:13px;color:var(--muted);white-space:pre-wrap">' + esc(text) + '</div></div>';
  }

  async function gbScripts() {
    const topic = ($('gb-topic').value || '').trim();
    if (!topic) { showBar('gb-scripts-bar', 'Enter a topic in the box above first.', 'error'); return; }
    const videoTitle = ($('gb-video-title').value || '').trim();
    showBar('gb-scripts-bar', 'Generating scripts…', 'info');
    $('gb-scripts-result').innerHTML = '';
    try {
      const res = await apiFetch('/growth-brain/conversion-scripts', { method: 'POST', body: JSON.stringify({ topic: topic, video_title: videoTitle }) });
      if (!res.ok) { showBar('gb-scripts-bar', 'Generation failed — please try again.', 'error'); return; }
      const d = await res.json();
      $('gb-scripts-bar').style.display = 'none';
      let html = gbSourceBadge(d.content_source);
      html += gbScriptBlock('📌 Pinned comment', d.pinned_comment);
      html += gbChipList('💬 Comment reply CTAs', d.comment_ctas);
      html += gbChipList('🔔 Subscribe CTAs', d.subscribe_ctas);
      html += gbScriptBlock('📝 Description CTA block', d.description_cta);
      $('gb-scripts-result').innerHTML = html;
    } catch (e) { showBar('gb-scripts-bar', 'Network error.', 'error'); }
  }

  // ── Playlist Resources ────────────────────────────────────
  var prData = { sections: [], source_types: [], tags: [], resources: [] };
  var prEditId = null;

  async function prLoad() {
    try {
      const res = await apiFetch('/admin/resources');
      if (!res.ok) { showBar('pr-status-bar', 'Could not load resources.', 'error'); return; }
      prData = await res.json();
      prFillSelectors();
      prRender();
    } catch (e) { showBar('pr-status-bar', 'Network error.', 'error'); }
  }

  function prFillSelectors() {
    const cat = $('pr-category');
    cat.innerHTML = prData.sections.map(function(s) {
      return '<option value="' + jsAttr(s.slug) + '">' + esc(s.label) + '</option>';
    }).join('');
    const st = $('pr-source-type');
    st.innerHTML = prData.source_types.map(function(t) {
      return '<option value="' + jsAttr(t) + '">' + esc(t) + '</option>';
    }).join('');
    $('pr-tags').innerHTML = prData.tags.map(function(t) {
      return '<label style="margin-right:14px;font-size:13px;color:var(--muted)">' +
        '<input type="checkbox" class="pr-tag" value="' + jsAttr(t) + '"> ' + esc(t) + '</label>';
    }).join('');
  }

  function prRender() {
    const box = $('pr-list');
    if (!prData.resources.length) { box.innerHTML = '<div class="empty-row">No resources yet — add the first one above.</div>'; return; }
    var html = '';
    prData.sections.forEach(function(s) {
      const items = prData.resources.filter(function(r) { return r.category === s.slug; });
      if (!items.length) return;
      html += '<h3 style="color:var(--gold);margin:18px 0 8px;font-size:14px;letter-spacing:.08em;text-transform:uppercase">' + esc(s.label) + ' (' + items.length + ')</h3>';
      items.forEach(function(r) {
        html += '<div class="list-row" style="display:flex;gap:10px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #222">' +
          '<div style="flex:1">' +
            '<div>' + (safeUrl(r.link)
                ? '<a class="resource-link" href="' + esc(safeUrl(r.link)) + '" target="_blank" rel="noopener noreferrer"><strong>' + esc(r.title) + '</strong> \u2197</a>'
                : '<strong>' + esc(r.title) + '</strong> <span style="color:#a66;font-size:12px">· resource unavailable — add a link</span>') +
              ' <span style="color:var(--muted);font-size:12px">· ' + esc(r.source_type) + (r.source_name ? ' · ' + esc(r.source_name) : '') + '</span></div>' +
            '<div style="color:var(--muted);font-size:13px;margin-top:2px">' + esc(r.description) + '</div>' +
            (r.tags && r.tags.length ? '<div style="font-size:12px;color:#777;margin-top:2px">tags: ' + esc(r.tags.join(', ')) + '</div>' : '') +
            (r.video_url ? '<div style="font-size:12px;margin-top:2px">🎥 <a href="' + esc(safeUrl(r.video_url)) + '" target="_blank" rel="noopener" style="color:var(--gold)">teaching linked</a></div>' : '<div style="font-size:12px;color:#775;margin-top:2px">no teaching video yet</div>') +
          '</div>' +
          '<div style="display:flex;gap:6px;flex-wrap:wrap">' +
            '<button class="btn btn-sm" onclick="prEdit(' + r.id + ')">✏️ Edit</button>' +
            '<button class="btn btn-sm" onclick="prPromote(' + r.id + ')">📬 Topic + Email</button>' +
            '<button class="btn btn-sm btn-danger" onclick="prDelete(' + r.id + ')">🗑️</button>' +
          '</div>' +
        '</div>';
      });
    });
    box.innerHTML = html;
  }

  function prForm() {
    return {
      title: $('pr-title').value.trim(),
      category: $('pr-category').value,
      source_type: $('pr-source-type').value,
      source_name: $('pr-source-name').value.trim(),
      description: $('pr-description').value.trim(),
      relevance: $('pr-relevance').value.trim(),
      link: $('pr-link').value.trim() || null,
      video_url: $('pr-video').value.trim() || null,
      tags: Array.prototype.slice.call(document.querySelectorAll('.pr-tag:checked')).map(function(c) { return c.value; })
    };
  }

  function prClearForm() {
    prEditId = null;
    ['pr-title','pr-source-name','pr-description','pr-relevance','pr-link','pr-video'].forEach(function(id) { $(id).value = ''; });
    document.querySelectorAll('.pr-tag').forEach(function(c) { c.checked = false; });
    document.getElementById('pr-submit-btn').textContent = 'Add Resource';
  }

  function prEdit(id) {
    const r = prData.resources.find(function(x) { return x.id === id; });
    if (!r) return;
    prEditId = id;
    $('pr-title').value = r.title;
    $('pr-category').value = r.category;
    $('pr-source-type').value = r.source_type;
    $('pr-source-name').value = r.source_name || '';
    $('pr-description').value = r.description || '';
    $('pr-relevance').value = r.relevance || '';
    $('pr-link').value = r.link || '';
    $('pr-video').value = r.video_url || '';
    document.querySelectorAll('.pr-tag').forEach(function(c) { c.checked = (r.tags || []).indexOf(c.value) !== -1; });
    document.getElementById('pr-submit-btn').textContent = 'Save Changes';
    var prFocusEl = $('pr-title');
    if (prFocusEl && prFocusEl.scrollIntoView) prFocusEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    else window.scrollTo(0, 0);
  }

  async function prCreate() {
    const body = prForm();
    if (!body.title) { showBar('pr-status-bar', 'A title is required.', 'error'); return; }
    try {
      const path = prEditId ? '/admin/resources/' + prEditId : '/admin/resources';
      const method = prEditId ? 'PATCH' : 'POST';
      const res = await apiFetch(path, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!res.ok) { showBar('pr-status-bar', 'Save failed.', 'error'); return; }
      showBar('pr-status-bar', prEditId ? 'Resource updated.' : 'Resource added.', 'success');
      prClearForm();
      prLoad();
    } catch (e) { showBar('pr-status-bar', 'Network error.', 'error'); }
  }

  async function prDelete(id) {
    if (!confirm('Delete this resource? This cannot be undone.')) return;
    try {
      const res = await apiFetch('/admin/resources/' + id, { method: 'DELETE' });
      if (!res.ok) { showBar('pr-status-bar', 'Delete failed.', 'error'); return; }
      if (prEditId === id) prClearForm();
      showBar('pr-status-bar', 'Resource deleted.', 'success');
      prLoad();
    } catch (e) { showBar('pr-status-bar', 'Network error.', 'error'); }
  }

  async function prPromote(id) {
    try {
      const res = await apiFetch('/admin/resources/' + id + '/promote', { method: 'POST' });
      if (!res.ok) { showBar('pr-status-bar', 'Could not create the topic + email draft.', 'error'); return; }
      const d = await res.json();
      showBar('pr-status-bar', 'Created topic + email draft' + (d.email_draft_id ? ' (#' + d.email_draft_id + ' in the Email Queue)' : '') + '.', 'success');
    } catch (e) { showBar('pr-status-bar', 'Network error.', 'error'); }
  }

  // Auto-login
  if (getStoredKey()) showApp();
</script>
</body>
</html>"""

_HTML = _HTML.replace("__ODILI_HEADER_CSS__", HEADER_CSS)
_HTML = _HTML.replace("__ODILI_HEADER_HTML__", header_html())


@router.get("/admin", tags=["Admin"], response_class=HTMLResponse, include_in_schema=False)
async def admin_dashboard() -> HTMLResponse:
    """Serve the admin SPA. no-store: authed dashboard must never be cached
    (stale cached copies previously kept serving old broken JS)."""
    return HTMLResponse(
        content=_HTML,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"},
    )
