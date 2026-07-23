"""
Lead Discovery Engine — compliant, API-only, HUMAN-review-only.

Finds real people asking faith/seeker questions in the PUBLIC comments of
watched YouTube channels, scores their intent with a pure-Python heuristic
(no API cost, deterministic), and stores only high-intent comments as leads for
a human to review. Approving a lead feeds the existing content systems
(Audience Topics, Content Ideas pipeline, Email Queue) and generates an AI
content pack (deterministic-first, never 402).

HARD RULE: nothing in this module ever replies to, comments on, or posts to
YouTube. The only action is surfacing a lead + a deep-link for a human.
"""

import json
import logging
import re
import threading
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.db_models import (
    AppSetting,
    LeadComment,
    PipelineItem,
    TrackedVideo,
    WatchlistChannel,
)
from app.services import youtube_api_service as yt

logger = logging.getLogger(__name__)

# Only comments scoring at/above this are stored as leads.
SAVE_THRESHOLD = 0.6

# Persisted flag so the dashboard can surface a "scan stopped early on quota"
# banner even when the stop happened during a background (scheduler) scan the
# admin never watched. Reuses AppSetting — no new table, no always-on cost.
_QUOTA_ALERT_KEY = "lead_discovery_quota_alert"

# Dry-spell alert: consecutive scans that scanned comments but saved 0 leads.
# Scans run ~every 6h (4/day) → 8 consecutive dry scans ≈ 2 days of silence.
_DRY_SPELL_KEY = "lead_discovery_dry_spell"
DRY_SPELL_THRESHOLD = 8

# Network-failure alert: consecutive scans where every YouTube API call failed
# on a non-quota error (network down, DNS, API outage) and nothing was fetched.
# Scans run ~every 6h (4/day) → 4 consecutive failures ≈ 1 day of silence.
_NETWORK_FAILURE_KEY = "lead_discovery_network_failure"
NETWORK_FAILURE_THRESHOLD = 4

# Guards against a manual scan overlapping the scheduler's scan (double quota
# spend + row races). Single-process app, so an in-process lock is sufficient.
_scan_lock = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Intent scoring (pure Python, no API cost) ────────────────────────────────

_QUESTION_WORDS = {
    "how", "why", "what", "who", "when", "where", "which", "can", "should",
    "is", "are", "do", "does", "did", "will", "could", "would", "was", "were",
    # Spanish
    "cómo", "como", "por", "qué", "que", "quién", "quien", "cuándo", "cuando",
    "dónde", "donde", "cuál", "cual", "puedo", "es", "hay", "debo",
    # French
    "comment", "pourquoi", "quoi", "qui", "quand", "où", "ou", "quel",
    "quelle", "est", "peut", "puis", "dois",
    # Portuguese
    "porque", "quem", "onde", "qual", "posso", "devo",
    # German
    "wie", "warum", "wieso", "weshalb", "wer", "wann", "wo", "welche",
    "welcher", "welches", "kann", "soll", "sollte", "darf", "muss", "ist",
    "sind", "gibt", "stimmt",
    # Italian
    "come", "perché", "perche", "cosa", "chi", "quando", "dove", "quale",
    "quali", "posso", "devo", "è", "c'è", "esiste",
    # Tagalog
    "paano", "bakit", "ano", "sino", "kailan", "saan", "alin", "pwede",
    "puwede", "maaari", "dapat", "totoo",
}

_SEEKER_PHRASES = [
    "i want to", "i need to", "how do i", "how can i", "how do you", "i'm looking",
    "im looking", "looking for", "help me", "i'm struggling", "im struggling",
    "struggling with", "i don't understand", "i dont understand", "dont understand",
    "can someone explain", "please explain", "can you explain", "i'm confused",
    "im confused", "confused about", "new to", "where do i start", "where should i start",
    "i'm searching", "im searching", "lost my faith", "losing my faith", "i have a question",
    "become catholic", "becoming catholic", "want to convert", "thinking of converting",
    "how to pray", "teach me", "i'm seeking", "im seeking", "does anyone",
    "is it true", "what does the church", "what does the bible",
    # Spanish
    "quiero ser", "quiero convertirme", "cómo puedo", "como puedo", "cómo hago",
    "como hago", "ayúdame", "ayudame", "no entiendo", "estoy confundido",
    "estoy confundida", "estoy buscando", "busco la verdad", "perdí la fe",
    "perdi la fe", "perdiendo la fe", "tengo una pregunta", "hacerme católico",
    "hacerme catolico", "ser católico", "ser catolico", "cómo rezar", "como rezar",
    "cómo orar", "como orar", "alguien puede explicar", "pueden explicar",
    "por dónde empiezo", "por donde empiezo", "es verdad que", "qué dice la iglesia",
    "que dice la iglesia", "qué dice la biblia", "que dice la biblia",
    "estoy luchando", "necesito ayuda", "soy nuevo en", "soy nueva en",
    # French
    "je veux devenir", "je veux me convertir", "comment puis-je", "comment puis je",
    "comment faire pour", "aidez-moi", "aidez moi", "aide-moi", "aide moi",
    "je ne comprends pas", "je suis perdu", "je suis perdue", "je suis confus",
    "je suis confuse", "je cherche", "perdu la foi", "perds la foi",
    "j'ai une question", "jai une question", "devenir catholique",
    "comment prier", "quelqu'un peut expliquer", "pouvez-vous expliquer",
    "pouvez vous expliquer", "par où commencer", "par ou commencer",
    "est-ce vrai", "est ce vrai", "que dit l'église", "que dit l'eglise",
    "que dit la bible", "nouveau dans la foi", "j'ai besoin d'aide",
    # Portuguese
    "quero ser", "quero me converter", "como posso", "como faço", "como faco",
    "me ajude", "ajude-me", "não entendo", "nao entendo", "estou confuso",
    "estou confusa", "estou procurando", "busco a verdade", "perdi a fé",
    "perdi a fe", "perdendo a fé", "perdendo a fe", "tenho uma pergunta",
    "tornar-me católico", "me tornar católico", "me tornar catolico",
    "ser católico", "ser catolico", "como rezar", "como orar",
    "alguém pode explicar", "alguem pode explicar", "por onde começo",
    "por onde comeco", "é verdade que", "e verdade que", "o que a igreja",
    "o que a bíblia", "o que a biblia", "preciso de ajuda", "sou novo na",
    "sou nova na",
    # German
    "ich möchte", "ich moechte", "ich will katholisch", "katholisch werden",
    "wie kann ich", "wie werde ich", "wie fange ich an", "wo fange ich an",
    "hilf mir", "helft mir", "ich verstehe nicht", "verstehe nicht",
    "ich bin verwirrt", "ich weiß nicht", "ich weiss nicht", "ich suche", "suche die wahrheit", "glauben verloren",
    "verliere meinen glauben", "ich habe eine frage", "hab eine frage",
    "wie bete ich", "wie betet man", "kann jemand erklären",
    "kann jemand erklaeren", "können sie erklären", "koennen sie erklaeren",
    "stimmt es dass", "stimmt es, dass", "was sagt die kirche",
    "was sagt die bibel", "ich brauche hilfe", "bin neu im glauben",
    "neu im glauben", "ich kämpfe mit", "ich kaempfe mit", "ich zweifle",
    # Italian
    "voglio diventare", "voglio convertirmi", "diventare cattolico",
    "diventare cattolica", "come posso", "come faccio", "da dove comincio",
    "da dove inizio", "aiutami", "aiutatemi", "non capisco", "sono confuso",
    "sono confusa", "sto cercando", "cerco la verità", "cerco la verita",
    "perso la fede", "perdendo la fede", "ho una domanda", "come pregare",
    "come si prega", "qualcuno può spiegare", "qualcuno puo spiegare",
    "potete spiegare", "è vero che", "e vero che", "cosa dice la chiesa",
    "cosa dice la bibbia", "ho bisogno di aiuto", "sono nuovo nella fede",
    "sono nuova nella fede", "sto lottando",
    # Tagalog
    "paano ako magiging katoliko", "gusto kong maging katoliko",
    "paano maging katoliko", "paano ako", "paano ko", "paano po",
    "hindi ko maintindihan", "hindi ko naiintindihan", "nalilito ako",
    "naguguluhan ako", "naghahanap ako", "hinahanap ko ang katotohanan",
    "nawawalan ako ng pananampalataya", "nawala ang pananampalataya ko",
    "nawawala ang pananampalataya", "may tanong ako", "may katanungan ako",
    "paano magdasal", "paano mag-rosaryo", "paano magrosaryo",
    "pwede bang ipaliwanag", "puwede bang ipaliwanag",
    "may makakapagpaliwanag ba", "pakipaliwanag", "totoo ba na", "totoo ba ang",
    "ano ang sinasabi ng simbahan", "ano ang sinasabi ng bibliya",
    "ano ang turo ng simbahan", "saan ako magsisimula",
    "saan ako magsimula", "tulungan niyo ako", "tulungan nyo ako",
    "tulungan mo ako", "kailangan ko ng tulong", "bago ako sa pananampalataya",
    "bago lang ako", "nahihirapan ako", "gusto kong matuto",
]

_FAITH_TERMS = {
    "god", "jesus", "christ", "catholic", "church", "faith", "bible", "scripture",
    "pray", "prayer", "salvation", "sin", "confession", "mass", "eucharist",
    "rosary", "mary", "saint", "saints", "heaven", "gospel", "holy", "spirit",
    "baptism", "priest", "soul", "repent", "forgive", "forgiveness", "doctrine",
    "protestant", "orthodox", "apologetics", "purgatory", "pope", "magisterium",
    "trinity", "grace", "conversion", "rcia", "believe", "belief", "doubt",
    # Spanish
    "dios", "jesús", "jesus", "cristo", "católico", "catolico", "católica",
    "catolica", "iglesia", "fe", "biblia", "rezar", "orar", "oración", "oracion",
    "salvación", "salvacion", "pecado", "confesión", "confesion", "misa",
    "eucaristía", "eucaristia", "rosario", "maría", "maria", "santo", "santos",
    "santa", "cielo", "evangelio", "bautismo", "sacerdote", "alma",
    "purgatorio", "papa", "trinidad", "gracia", "creer", "duda", "verdad",
    # French
    "dieu", "jésus", "christ", "catholique", "église", "eglise", "foi",
    "prier", "prière", "priere", "salut", "péché", "peche", "confession",
    "messe", "eucharistie", "chapelet", "marie", "saint", "saints", "sainte",
    "ciel", "évangile", "evangile", "baptême", "bapteme", "prêtre", "pretre",
    "âme", "ame", "purgatoire", "pape", "trinité", "trinite", "grâce",
    "croire", "doute", "vérité", "verite",
    # Portuguese
    "deus", "católicos", "igreja", "fé", "bíblia", "oração", "oracao",
    "salvação", "salvacao", "pecado", "confissão", "confissao", "missa",
    "eucaristia", "rosário", "rosario", "céu", "ceu", "evangelho", "batismo",
    "padre", "purgatório", "trindade", "graça", "graca", "crer", "dúvida",
    "duvida", "verdade",
    # German
    "gott", "jesus", "christus", "katholisch", "katholik", "kirche", "glaube",
    "glauben", "bibel", "beten", "gebet", "erlösung", "erloesung", "sünde",
    "suende", "beichte", "messe", "eucharistie", "rosenkranz", "maria",
    "heilige", "heiliger", "himmel", "evangelium", "taufe", "priester",
    "seele", "fegefeuer", "papst", "dreifaltigkeit", "gnade", "glaubst",
    "zweifel", "wahrheit",
    # Italian
    "dio", "gesù", "gesu", "cristo", "cattolico", "cattolica", "chiesa",
    "fede", "bibbia", "pregare", "preghiera", "salvezza", "peccato",
    "confessione", "messa", "eucaristia", "rosario", "maria", "santo",
    "santi", "santa", "cielo", "vangelo", "battesimo", "sacerdote", "anima",
    "purgatorio", "papa", "trinità", "trinita", "grazia", "credere",
    "dubbio", "verità", "verita",
    # Tagalog
    "diyos", "hesus", "kristo", "hesukristo", "katoliko", "katolika",
    "simbahan", "pananampalataya", "pananalig", "bibliya", "banal",
    "kasulatan", "magdasal", "dasal", "panalangin", "nagdadasal",
    "kaligtasan", "kasalanan", "kumpisal", "kumpisalan", "pagkukumpisal",
    "misa", "eukaristiya", "rosaryo", "birhen", "santo", "santa", "langit",
    "ebanghelyo", "espiritu", "binyag", "pagbibinyag", "pari", "kaluluwa",
    "pagsisisi", "kapatawaran", "doktrina", "protestante", "purgatoryo",
    "santatlo", "grasya", "maniwala", "naniniwala", "paniniwala",
    "pagdududa", "nagdududa", "katotohanan",
}

# Obvious spam / self-promotion — never a lead.
_NEGATIVE = [
    "subscribe to my", "check out my channel", "check my channel", "buy now",
    "promo code", "discount code", "click here", "follow me on", "onlyfans",
    "http://", "https://", "www.", "free gift card", "make money", "dm me",
    "visit my", "my channel", "sub for sub",
    # Spanish / French / Portuguese / German / Italian self-promotion
    "mi canal", "suscríbete", "suscribete", "meu canal", "inscreva-se",
    "se inscreve", "ma chaîne", "ma chaine", "abonnez-vous", "abonne-toi",
    "mein kanal", "abonniert", "il mio canale", "iscriviti",
    # Tagalog self-promotion
    "channel ko", "aking channel", "mag-subscribe", "i-subscribe",
    "subscribe kayo", "bisitahin ang",
]

# Link-evasion spam: bare domains without http/www ("meucanal.com.br"),
# spelled-out dots ("ejemplo dot com" / "punto com" / "ponto com" / "point com"),
# and channel-handle drops ("@mychannel") in a promo context. Complements the
# plain substrings in _NEGATIVE.
_BARE_DOMAIN_RE = re.compile(
    r"\b[a-z0-9][a-z0-9-]*\.(?:com|net|org|info|biz|xyz|online|site|shop|"
    r"store|club|live|app|link|page|me|tv|co|io|gg|ru|br|mx|ar|es|fr|pt|de|"
    r"it|ph|uk)\b"
)
_DOT_EVASION_RE = re.compile(
    r"\b(?:dot|punto|ponto|point)\s+(?:com|net|org)\b"
)
_HANDLE_DROP_RE = re.compile(r"@[a-z0-9][a-z0-9_.-]{2,}")
# Handle drops are only spam alongside a promo cue — plain "@user thanks!"
# reply mentions must survive.
_PROMO_CONTEXT = (
    "channel", "canal", "chaîne", "chaine", "kanal", "canale",
    "subscribe", "suscr", "inscrev", "abonn", "iscriv",
    "follow", "visit", "visita", "check",
)

# Include accented Latin letters so Spanish/French/Portuguese words tokenize
# (e.g. "católico", "église", "fé") instead of splitting on the accent.
# "ß" (U+00DF) sits outside the à-ö/ø-ÿ ranges, so it's listed explicitly for
# German words like "weiß"/"heißt".
_WORD_RE = re.compile(r"[a-zà-öø-ÿß'-]+")

# First-person markers signalling a personal (not abstract) question — EN/ES/FR/PT/DE/IT.
_FIRST_PERSON = {
    "i", "im", "me", "my", "myself",
    "yo", "mi", "mis", "conmigo", "estoy", "soy", "quiero", "necesito",
    "je", "j'ai", "moi", "mon", "ma", "mes", "suis", "veux",
    "eu", "meu", "minha", "comigo", "sou", "quero", "preciso",
    # German
    "ich", "mich", "mir", "mein", "meine", "meinen", "meinem", "bin",
    "möchte", "moechte", "brauche", "zweifle",
    # Italian
    "io", "mi", "mio", "mia", "miei", "sono", "voglio", "cerco", "vorrei",
    "ho",
    # Tagalog
    "ako", "ko", "akin", "kong",
}


# Messy real-world formatting → canonical form so exact-substring phrase
# matching still works: smart quotes → ', curly double quotes dropped,
# ellipsis → "...", unicode dashes → '-', NBSP/newlines → space, fullwidth
# '？' → '?'. Emoji/symbols are replaced with a space (never deleted inline)
# so "faith🙏help" still tokenizes as two words.
_CHAR_NORMALIZE = str.maketrans({
    "\u2019": "'", "\u2018": "'", "\u201b": "'", "\u02bc": "'", "\u00b4": "'",
    "\u0060": "'",
    "\u201c": '"', "\u201d": '"',
    "\u2026": "...",
    "\u2013": "-", "\u2014": "-",
    "\u00a0": " ", "\n": " ", "\r": " ", "\t": " ",
    "\uff1f": "?",
})

_EMOJI_RE = re.compile(
    "["
    "\U0001f000-\U0001fbff"   # emoji, symbols, pictographs, extended-A
    "\u2600-\u27bf"            # misc symbols & dingbats
    "\ufe00-\ufe0f"            # variation selectors
    "\u200d"                   # zero-width joiner
    "\u2b00-\u2bff"            # arrows/stars (⭐ etc.)
    "\U000e0020-\U000e007f"   # tag characters (flag sequences)
    "]+"
)


def _normalize(text: str) -> str:
    t = text.translate(_CHAR_NORMALIZE)
    t = _EMOJI_RE.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()


def score_intent(text: str) -> float:
    """Heuristic 0..1 seeker-intent score for a comment. Deterministic."""
    t = _normalize((text or "").lower())
    if not t:
        return 0.0
    if any(neg in t for neg in _NEGATIVE):
        return 0.0
    if _BARE_DOMAIN_RE.search(t) or _DOT_EVASION_RE.search(t):
        return 0.0
    if _HANDLE_DROP_RE.search(t) and any(c in t for c in _PROMO_CONTEXT):
        return 0.0

    words = _WORD_RE.findall(t)
    word_set = set(words)
    # French elision/hyphenation ("l'église", "est-ce", "puis-je") keeps the
    # apostrophe/hyphen inside the token — also index the split parts so the
    # underlying word still matches faith terms and question words.
    for w in words:
        if "'" in w or "-" in w:
            word_set.update(p for p in re.split(r"['-]", w) if p)
    score = 0.0

    if "?" in t or "¿" in t:
        score += 0.25
    first_parts = re.split(r"['-]", words[0]) if words else []
    if words and (words[0] in _QUESTION_WORDS or (first_parts and first_parts[0] in _QUESTION_WORDS)):
        score += 0.15

    phrase_hits = sum(1 for p in _SEEKER_PHRASES if p in t)
    score += min(phrase_hits * 0.2, 0.4)

    faith_hits = len(word_set & _FAITH_TERMS)
    score += min(faith_hits * 0.12, 0.36)

    if word_set & _FIRST_PERSON or "i'm" in t:
        score += 0.1

    # Very short, low-signal comments get discounted.
    if len(t) < 12:
        score *= 0.5

    return round(min(score, 1.0), 3)


# ── Serializers ──────────────────────────────────────────────────────────────

def _serialize_channel(ch: WatchlistChannel, pending_leads: int = 0) -> dict:
    return {
        "id": ch.id,
        "channel_id": ch.channel_id,
        "handle": ch.handle,
        "title": ch.title,
        "category": ch.category,
        "active": ch.active,
        "pending_leads": pending_leads,
        "last_checked_at": ch.last_checked_at.isoformat() if ch.last_checked_at else None,
        "created_at": ch.created_at.isoformat() if ch.created_at else None,
    }


def _pending_counts_by_channel(db: Session) -> dict[str, int]:
    """One grouped query: channel_id -> count of leads still awaiting review."""
    rows = (
        db.query(LeadComment.channel_id, func.count(LeadComment.id))
        .filter(LeadComment.review_status == "pending")
        .group_by(LeadComment.channel_id)
        .all()
    )
    return {channel_id: count for channel_id, count in rows}


def _serialize_lead(db: Session, lead: LeadComment) -> dict:
    video = db.query(TrackedVideo).filter(TrackedVideo.video_id == lead.video_id).first()
    channel = db.query(WatchlistChannel).filter(WatchlistChannel.channel_id == lead.channel_id).first()
    pack = None
    if lead.generated_content:
        try:
            pack = json.loads(lead.generated_content)
        except (TypeError, ValueError):
            pack = None
    return {
        "id": lead.id,
        "author": lead.author,
        "text": lead.text,
        "intent_score": lead.intent_score,
        "review_status": lead.review_status,
        "video_id": lead.video_id,
        "video_title": video.title if video else None,
        "channel_id": lead.channel_id,
        "channel_title": channel.title if channel else None,
        "comment_link": yt.comment_link(lead.video_id, lead.comment_id),
        "content_pack": pack,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
    }


# ── Watchlist management ─────────────────────────────────────────────────────

def add_channel(db: Session, raw: str, category: str = "general") -> tuple[dict, bool]:
    """Resolve + store a channel (idempotent). Returns (channel, created)."""
    info = yt.resolve_channel(db, raw)
    existing = (
        db.query(WatchlistChannel)
        .filter(WatchlistChannel.channel_id == info["channel_id"])
        .first()
    )
    if existing:
        existing.active = True
        if category:
            existing.category = category.strip()[:60]
        existing.title = info["title"]
        existing.uploads_playlist_id = info["uploads_playlist_id"]
        db.commit()
        db.refresh(existing)
        return _serialize_channel(existing), False

    ch = WatchlistChannel(
        channel_id=info["channel_id"],
        handle=info.get("handle"),
        title=info["title"],
        uploads_playlist_id=info["uploads_playlist_id"],
        category=(category or "general").strip()[:60] or "general",
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return _serialize_channel(ch), True


def list_channels(db: Session) -> list[dict]:
    rows = db.query(WatchlistChannel).order_by(WatchlistChannel.created_at.desc()).all()
    counts = _pending_counts_by_channel(db)
    # Busiest first: pending leads desc; ties keep newest-first (rows already
    # sorted newest-first and Python's sort is stable).
    rows.sort(key=lambda r: counts.get(r.channel_id, 0), reverse=True)
    return [_serialize_channel(r, counts.get(r.channel_id, 0)) for r in rows]


def remove_channel(db: Session, channel_pk: int) -> bool:
    ch = db.query(WatchlistChannel).filter(WatchlistChannel.id == channel_pk).first()
    if ch is None:
        return False
    db.delete(ch)
    db.commit()
    return True


# ── Leads ────────────────────────────────────────────────────────────────────

def list_leads(
    db: Session,
    *,
    status: str = "pending",
    sort: str = "intent",
    channel_id: str | None = None,
    category: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """List leads. sort='intent' → highest intent score first (default);
    sort='newest' → most recently discovered first. Display-only ordering —
    the SAVE_THRESHOLD storage cutoff is unaffected.

    Optional ``channel_id`` restricts to one watched channel; optional
    ``category`` restricts to every channel sharing that theme. Both combine
    with the status/sort options. A ``category`` with no matching channels
    yields an empty list."""
    q = db.query(LeadComment)
    if status and status != "all":
        q = q.filter(LeadComment.review_status == status)
    if channel_id:
        q = q.filter(LeadComment.channel_id == channel_id)
    if category:
        matching = [
            row.channel_id
            for row in db.query(WatchlistChannel.channel_id)
            .filter(WatchlistChannel.category == category)
            .all()
        ]
        if not matching:
            return []
        q = q.filter(LeadComment.channel_id.in_(matching))
    if sort == "newest":
        order = (LeadComment.created_at.desc(), LeadComment.intent_score.desc())
    else:
        order = (LeadComment.intent_score.desc(), LeadComment.created_at.desc())
    rows = q.order_by(*order).limit(limit).all()
    return [_serialize_lead(db, r) for r in rows]


def skip_lead(db: Session, lead_id: int) -> bool:
    lead = db.get(LeadComment, lead_id)
    if lead is None:
        return False
    lead.review_status = "skipped"
    db.commit()
    return True


def count_bulk_skip_leads(db: Session, max_score: float) -> dict:
    """Preview what a bulk-skip at ``max_score`` would clear: count plus the
    min/max intent score in the batch. Read-only — mirrors the exact filter
    used by :func:`bulk_skip_leads` so the preview matches what gets skipped.
    ``min_score``/``max_score`` are None when the batch is empty.

    Also returns ``near_misses``: the 3 lowest-scoring PENDING leads at or
    above the cutoff (the "closest keepers") so the admin can eyeball who
    would just barely survive before confirming a bulk cleanup."""
    count, lo, hi = (
        db.query(
            func.count(LeadComment.id),
            func.min(LeadComment.intent_score),
            func.max(LeadComment.intent_score),
        )
        .filter(
            LeadComment.review_status == "pending",
            LeadComment.intent_score < max_score,
        )
        .one()
    )
    keepers = (
        db.query(LeadComment)
        .filter(
            LeadComment.review_status == "pending",
            LeadComment.intent_score >= max_score,
        )
        .order_by(LeadComment.intent_score.asc(), LeadComment.id.asc())
        .limit(3)
        .all()
    )
    near_misses = [
        {
            "id": lead.id,
            "score": float(lead.intent_score or 0.0),
            "author": (lead.author or "")[:80],
            "snippet": (lead.text or "").strip()[:120],
            "comment_link": yt.comment_link(lead.video_id, lead.comment_id),
        }
        for lead in keepers
    ]
    return {
        "count": int(count or 0),
        "min_score": float(lo) if lo is not None else None,
        "max_score": float(hi) if hi is not None else None,
        "near_misses": near_misses,
    }


def bulk_skip_leads(db: Session, max_score: float) -> int:
    """Mark every PENDING lead with intent_score < ``max_score`` as skipped in
    one pass. Only pending leads are touched — approved/skipped leads are never
    changed — and the SAVE_THRESHOLD storage cutoff is unaffected (this only
    reclassifies already-stored leads). Returns the number of leads skipped.

    Records the exact lead IDs skipped as the "last bulk-skip batch"
    (AppSetting, no new table) so the admin can one-click undo. Each new
    bulk-skip overwrites the batch, and a new scan clears it — undo only ever
    applies to the most recent bulk-skip."""
    ids = [
        row.id
        for row in db.query(LeadComment.id)
        .filter(
            LeadComment.review_status == "pending",
            LeadComment.intent_score < max_score,
        )
        .all()
    ]
    if ids:
        # Re-check "pending" in the UPDATE itself so a concurrent approve
        # between the SELECT and the UPDATE is never overwritten.
        db.query(LeadComment).filter(
            LeadComment.id.in_(ids),
            LeadComment.review_status == "pending",
        ).update({LeadComment.review_status: "skipped"}, synchronize_session=False)
    _set_last_bulk_skip(db, ids)
    db.commit()
    return len(ids)


# Undo support for bulk-skip. Reuses AppSetting — no new table. The batch is
# best-effort safety-net state, not a security boundary.
_BULK_SKIP_BATCH_KEY = "lead_discovery_last_bulk_skip"


def _set_last_bulk_skip(db: Session, ids: list[int]) -> None:
    """Persist (or clear, when ids is empty) the last bulk-skip batch. Does not
    commit — callers commit as part of their own transaction."""
    row = db.query(AppSetting).filter(AppSetting.key == _BULK_SKIP_BATCH_KEY).first()
    value = json.dumps({"ids": ids, "at": _now().isoformat()}) if ids else ""
    if row is None:
        if not ids:
            return
        db.add(AppSetting(key=_BULK_SKIP_BATCH_KEY, value=value))
    else:
        row.value = value


def _get_last_bulk_skip(db: Session) -> list[int]:
    row = db.query(AppSetting).filter(AppSetting.key == _BULK_SKIP_BATCH_KEY).first()
    if not row or not row.value:
        return []
    try:
        data = json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        return []
    ids = data.get("ids") if isinstance(data, dict) else None
    if not isinstance(ids, list):
        return []
    return [i for i in ids if isinstance(i, int)]


def _get_last_bulk_skip_info(db: Session) -> dict | None:
    """Return `{size, at}` for the persisted bulk-skip batch, or None when no
    batch is available. Used by status() so the admin UI can re-show the Undo
    button after a page refresh."""
    row = db.query(AppSetting).filter(AppSetting.key == _BULK_SKIP_BATCH_KEY).first()
    if not row or not row.value:
        return None
    try:
        data = json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    ids = data.get("ids")
    if not isinstance(ids, list):
        return None
    ids = [i for i in ids if isinstance(i, int)]
    if not ids:
        return None
    at = data.get("at")
    return {"size": len(ids), "at": at if isinstance(at, str) else None}


def clear_bulk_skip_batch(db: Session) -> None:
    """Invalidate the undo batch (called after a scan — the lead pool has
    changed, so a late undo would be confusing). Fail-silent."""
    try:
        _set_last_bulk_skip(db, [])
        db.commit()
    except Exception:  # noqa: BLE001 — never break the scan on undo bookkeeping
        db.rollback()


def undo_bulk_skip(db: Session) -> int:
    """Restore the leads from the last bulk-skip batch to "pending". Only leads
    that are STILL "skipped" are touched — a later approve is never overridden.
    The batch is consumed (one-shot); no batch → no-op returning 0."""
    ids = _get_last_bulk_skip(db)
    if not ids:
        return 0
    restored = (
        db.query(LeadComment)
        .filter(
            LeadComment.id.in_(ids),
            LeadComment.review_status == "skipped",
        )
        .update({LeadComment.review_status: "pending"}, synchronize_session=False)
    )
    _set_last_bulk_skip(db, [])
    db.commit()
    return int(restored or 0)


def _get_quota_alert(db: Session) -> dict | None:
    """Return the persisted quota-stop alert, or None if the last scan finished
    without hitting the daily cap."""
    row = db.query(AppSetting).filter(AppSetting.key == _QUOTA_ALERT_KEY).first()
    if not row or not row.value:
        return None
    try:
        data = json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) and data.get("stopped_early") else None


def _notify_admin_quota_stall(payload: dict) -> bool:
    """Email the ministry/admin address once when lead scanning stalls on the
    daily YouTube quota. Returns True only if the notice was actually sent.

    Fail-silent: a send failure (misconfigured SendGrid, network) never breaks
    the scan and leaves the 'notified' flag False so the next scan retries. Goes
    ONLY to the admin/from address — never the subscriber list or EmailQueue."""
    try:
        from app.services.email_sender_service import send_admin_notice

        units = payload.get("units_used")
        cap = payload.get("cap")
        checked = payload.get("channels_checked", 0)
        subject = "⚠️ Odili Lead Discovery paused — YouTube daily quota reached"
        body = "\n".join([
            "Heads up — the Lead Discovery scan stopped early because it hit the "
            "YouTube Data API daily quota cap.",
            "",
            f"Quota used: {units} / {cap} units",
            f"Channels checked before stopping: {checked}",
            "",
            "New comment leads may be incomplete until the quota resets at "
            "midnight UTC, when scanning resumes automatically.",
            "",
            "No action is required — this is an automatic, one-time notice so a "
            "quota stall doesn't go unnoticed for days.",
        ])
        result = send_admin_notice(subject, body)
        if result and result.success:
            logger.info("Admin quota-stall notice sent.")
            return True
        logger.warning(
            "Admin quota-stall notice not sent: %s",
            (result.error if result else "no result"),
        )
        return False
    except Exception as exc:  # noqa: BLE001 — never break the scan on a notice
        logger.warning("Admin quota-stall notice failed to send: %s", exc)
        return False


def _notify_admin_dry_spell(payload: dict) -> bool:
    """Email the ministry/admin address once when several consecutive scans have
    scanned comments but saved zero leads (a field dry spell — channels quiet,
    comments disabled, audience shift). Returns True only if actually sent.

    Fail-silent: a send failure never breaks the scan and leaves 'notified'
    False so the next dry scan retries. Goes ONLY to the admin/from address —
    never the subscriber list or EmailQueue."""
    try:
        from app.services.email_sender_service import send_admin_notice

        dry = payload.get("count", 0)
        since = payload.get("since") or "unknown"
        subject = "⚠️ Odili Lead Discovery — no new seekers found for days"
        body = "\n".join([
            "Heads up — the Lead Discovery scans are running and reading "
            "comments as usual, but they haven't found a single new seeker "
            "lead in a while.",
            "",
            f"Consecutive scans with zero leads: {dry}",
            f"Dry spell started around: {since} (UTC)",
            "",
            "Possible reasons: the watched channels went quiet, comments were "
            "disabled on new uploads, or the audience conversation shifted.",
            "",
            "You may want to review the watched channels in the Lead Discovery "
            "tab and consider adding fresh ones.",
            "",
            "This is an automatic, one-time notice — you'll get another only "
            "if leads recover and then dry up again.",
        ])
        result = send_admin_notice(subject, body)
        if result and result.success:
            logger.info("Admin dry-spell notice sent.")
            return True
        logger.warning(
            "Admin dry-spell notice not sent: %s",
            (result.error if result else "no result"),
        )
        return False
    except Exception as exc:  # noqa: BLE001 — never break the scan on a notice
        logger.warning("Admin dry-spell notice failed to send: %s", exc)
        return False


def _notify_admin_network_failure(payload: dict) -> bool:
    """Email the ministry/admin address once when several consecutive scheduled
    scans failed entirely on network/API errors (YouTube unreachable) — so an
    outage doesn't silently produce empty scans for days. Returns True only if
    the notice was actually sent.

    Fail-silent: a send failure never breaks the scan and leaves 'notified'
    False so the next failing scan retries. Goes ONLY to the admin/from address —
    never the subscriber list or EmailQueue."""
    try:
        from app.services.email_sender_service import send_admin_notice

        count = payload.get("count", 0)
        since = payload.get("since") or "unknown"
        last_error = payload.get("last_error") or "unknown error"
        subject = "⚠️ Odili Lead Discovery — scans failing on network errors"
        body = "\n".join([
            "Heads up — the scheduled Lead Discovery scans have been failing "
            "because YouTube couldn't be reached (network or API errors). No "
            "comments were read at all during these scans.",
            "",
            f"Consecutive fully-failed scans: {count}",
            f"Failures started around: {since} (UTC)",
            f"Most recent error: {last_error}",
            "",
            "This is usually temporary (network hiccup or a YouTube API "
            "outage). Scanning retries automatically every few hours — if it "
            "keeps failing, check the server's internet access and the "
            "YouTube API key.",
            "",
            "This is an automatic, one-time notice — you'll get another only "
            "if scans recover and then start failing again.",
        ])
        result = send_admin_notice(subject, body)
        if result and result.success:
            logger.info("Admin network-failure notice sent.")
            return True
        logger.warning(
            "Admin network-failure notice not sent: %s",
            (result.error if result else "no result"),
        )
        return False
    except Exception as exc:  # noqa: BLE001 — never break the scan on a notice
        logger.warning("Admin network-failure notice failed to send: %s", exc)
        return False


def _get_network_failure(db: Session) -> dict | None:
    """Return the persisted network-failure streak, or None when there is no
    active streak (last scan reached YouTube). Fail-safe: bad JSON → None."""
    row = db.query(AppSetting).filter(AppSetting.key == _NETWORK_FAILURE_KEY).first()
    if not row or not row.value:
        return None
    try:
        data = json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        if int(data.get("count") or 0) <= 0:
            return None
    except (ValueError, TypeError):
        return None
    data["threshold"] = NETWORK_FAILURE_THRESHOLD
    return data


def _record_network_failures(db: Session, summary: dict) -> None:
    """Track consecutive scans where every YouTube API call failed on a
    non-quota error (network down / API outage) in AppSetting and email the
    admin once when the streak reaches NETWORK_FAILURE_THRESHOLD
    (incident-based, like the quota-stall and dry-spell notices).

    Counting rules:
    - api_failures > 0 and api_successes == 0 → total failure: streak += 1
    - api_successes > 0 → recovery: streak resets to 0 and the alert re-arms
    - api_failures == 0 and api_successes == 0 (no channels, or stopped on
      quota before any call) → neutral: streak unchanged, no false signal

    Fail-silent: any error here is swallowed so alerting can never break a scan."""
    try:
        failures = int(summary.get("api_failures") or 0)
        successes = int(summary.get("api_successes") or 0)
        if failures <= 0 and successes <= 0:
            return  # neutral scan — no evidence either way

        row = db.query(AppSetting).filter(AppSetting.key == _NETWORK_FAILURE_KEY).first()
        data: dict = {}
        if row and row.value:
            try:
                loaded = json.loads(row.value)
                if isinstance(loaded, dict):
                    data = loaded
            except (json.JSONDecodeError, TypeError):
                data = {}

        count = int(data.get("count") or 0)
        notified = bool(data.get("notified"))
        since = data.get("since")
        last_error = data.get("last_error")

        if successes > 0:
            # Recovery — reset the streak and re-arm the alert.
            count, notified, since, last_error = 0, False, None, None
        else:
            count += 1
            if since is None:
                since = _now().isoformat()
            new_err = summary.get("last_api_error")
            if new_err:
                last_error = str(new_err)[:300]

        payload = {
            "count": count,
            "notified": notified,
            "since": since,
            "last_error": last_error,
        }

        if count >= NETWORK_FAILURE_THRESHOLD and not notified:
            if _notify_admin_network_failure(payload):
                payload["notified"] = True

        if row is None:
            row = AppSetting(key=_NETWORK_FAILURE_KEY, value=json.dumps(payload))
            db.add(row)
        else:
            row.value = json.dumps(payload)
        db.commit()
    except Exception as exc:  # noqa: BLE001 — alerting must never break a scan
        logger.warning("Network-failure bookkeeping failed (ignored): %s", exc)
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass


def _get_dry_spell(db: Session) -> dict | None:
    """Return the persisted dry-spell streak, or None when there is no active
    streak (last comment-bearing scan found leads). Fail-safe: bad JSON → None."""
    row = db.query(AppSetting).filter(AppSetting.key == _DRY_SPELL_KEY).first()
    if not row or not row.value:
        return None
    try:
        data = json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        if int(data.get("count") or 0) <= 0:
            return None
    except (ValueError, TypeError):
        return None
    data["threshold"] = DRY_SPELL_THRESHOLD
    return data


def _record_dry_spell(db: Session, summary: dict) -> None:
    """Track consecutive "scanned comments but saved 0 leads" scans in
    AppSetting and email the admin once when the streak reaches
    DRY_SPELL_THRESHOLD (incident-based, like the scheduler failure alerts).

    Counting rules:
    - comments_scanned > 0 and leads_found == 0 → streak += 1
    - leads_found > 0 → recovery: streak resets to 0 and the alert re-arms
    - comments_scanned == 0 (nothing new to scan, or stopped on quota before
      reading any comments) → neutral: streak unchanged, no false signal

    Fail-silent: any error here is swallowed so alerting can never break a scan."""
    try:
        comments = int(summary.get("comments_scanned") or 0)
        leads = int(summary.get("leads_found") or 0)
        if comments <= 0 and leads <= 0:
            return  # neutral scan — no evidence either way

        row = db.query(AppSetting).filter(AppSetting.key == _DRY_SPELL_KEY).first()
        data: dict = {}
        if row and row.value:
            try:
                loaded = json.loads(row.value)
                if isinstance(loaded, dict):
                    data = loaded
            except (json.JSONDecodeError, TypeError):
                data = {}

        count = int(data.get("count") or 0)
        notified = bool(data.get("notified"))
        since = data.get("since")

        if leads > 0:
            # Recovery — reset the streak and re-arm the alert.
            count, notified, since = 0, False, None
        else:
            count += 1
            if since is None:
                since = _now().isoformat()

        payload = {"count": count, "notified": notified, "since": since}

        if count >= DRY_SPELL_THRESHOLD and not notified:
            if _notify_admin_dry_spell(payload):
                payload["notified"] = True

        if row is None:
            row = AppSetting(key=_DRY_SPELL_KEY, value=json.dumps(payload))
            db.add(row)
        else:
            row.value = json.dumps(payload)
        db.commit()
    except Exception as exc:  # noqa: BLE001 — alerting must never break a scan
        logger.warning("Dry-spell bookkeeping failed (ignored): %s", exc)
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass


def _record_scan_outcome(db: Session, summary: dict) -> None:
    """Persist whether the last scan stopped early on the daily quota cap so the
    dashboard can surface a banner — including for background scheduler scans the
    admin never saw. A scan that finishes fully clears the alert automatically.

    On the transition INTO a stopped-early state, emails the admin once (deduped
    via a 'notified' flag) so a quota stall is surfaced proactively rather than
    only when someone opens the Lead Discovery tab. Subsequent stalled scans do
    not re-notify; a fully-completed scan resets the flag so the next transition
    notifies again."""
    stopped_early = bool(summary.get("stopped_early"))

    row = db.query(AppSetting).filter(AppSetting.key == _QUOTA_ALERT_KEY).first()
    prev_data: dict = {}
    if row and row.value:
        try:
            loaded = json.loads(row.value)
            if isinstance(loaded, dict):
                prev_data = loaded
        except (json.JSONDecodeError, TypeError):
            prev_data = {}
    # 'notified' only carries meaning while we remain in a stopped-early state.
    prev_notified = bool(prev_data.get("stopped_early")) and bool(prev_data.get("notified"))

    payload = {
        "stopped_early": stopped_early,
        "at": _now().isoformat(),
        "units_used": summary.get("quota_used_end"),
        "cap": yt.DAILY_QUOTA_CAP,
        "channels_checked": summary.get("channels_checked", 0),
        # Reset the dedupe flag whenever a scan completes fully.
        "notified": prev_notified if stopped_early else False,
    }

    # Notify once per quota-stop transition (not on every 6-hourly scan).
    if stopped_early and not prev_notified:
        if _notify_admin_quota_stall(payload):
            payload["notified"] = True

    if row is None:
        row = AppSetting(key=_QUOTA_ALERT_KEY, value=json.dumps(payload))
        db.add(row)
    else:
        row.value = json.dumps(payload)
    db.commit()


def status(db: Session) -> dict:
    return {
        "configured": yt.is_configured(),
        "quota": yt.quota_status(db),
        "quota_alert": _get_quota_alert(db),
        "dry_spell": _get_dry_spell(db),
        "network_failure": _get_network_failure(db),
        "channels": db.query(WatchlistChannel).count(),
        "active_channels": db.query(WatchlistChannel).filter(WatchlistChannel.active.is_(True)).count(),
        "videos_tracked": db.query(TrackedVideo).count(),
        "pending_leads": db.query(LeadComment).filter(LeadComment.review_status == "pending").count(),
        "approved_leads": db.query(LeadComment).filter(LeadComment.review_status == "approved").count(),
        "save_threshold": SAVE_THRESHOLD,
        "last_bulk_skip": _get_last_bulk_skip_info(db),
    }


# ── Polling scan ─────────────────────────────────────────────────────────────

def scan_all(
    db: Session,
    *,
    videos_per_channel: int = 5,
    comments_per_video: int = 100,
) -> dict:
    """Poll every active watched channel for new uploads and scan their comments.

    Quota-safe: stops as soon as the daily cap is reached. Only NEW (unscanned)
    videos have their comments fetched.
    """
    if not yt.is_configured():
        return {"status": "not_configured"}

    # Only one scan may run at a time; a manual /leads/scan overlapping the
    # 6-hourly scheduler job would double-spend quota and race on the same rows.
    if not _scan_lock.acquire(blocking=False):
        return {"status": "busy", "message": "A scan is already in progress."}
    try:
        summary = _scan_all_locked(
            db,
            videos_per_channel=videos_per_channel,
            comments_per_video=comments_per_video,
        )
        # Persist the quota-stop state (set if stopped early, cleared otherwise)
        # so the dashboard can surface it even for background scheduler scans.
        _record_scan_outcome(db, summary)
        # Track "scanned but found nothing" streaks so a field dry spell
        # (quiet channels, disabled comments) emails the admin once.
        _record_dry_spell(db, summary)
        # Track "every API call failed on a network error" streaks so a
        # YouTube/network outage emails the admin once instead of producing
        # silently-empty scans for days.
        _record_network_failures(db, summary)
        # A scan changes the lead pool — invalidate the bulk-skip undo batch so
        # a stale undo can't fire against a refreshed list.
        clear_bulk_skip_batch(db)
        return summary
    finally:
        _scan_lock.release()


def _scan_all_locked(
    db: Session,
    *,
    videos_per_channel: int,
    comments_per_video: int,
) -> dict:
    summary = {
        "status": "ok",
        "channels_checked": 0,
        "new_videos": 0,
        "comments_scanned": 0,
        "leads_found": 0,
        "quota_used_start": yt.units_used_today(db),
        "stopped_early": False,
        "api_successes": 0,
        "api_failures": 0,
        "last_api_error": None,
    }

    channels = db.query(WatchlistChannel).filter(WatchlistChannel.active.is_(True)).all()
    for ch in channels:
        if yt.remaining_today(db) < yt.COST_LIST:
            summary["stopped_early"] = True
            break
        summary["channels_checked"] += 1
        try:
            uploads = yt.list_uploads(db, ch.uploads_playlist_id, videos_per_channel)
        except yt.YouTubeQuotaError:
            summary["stopped_early"] = True
            break
        except yt.YouTubeAPIError as exc:
            summary["api_failures"] += 1
            summary["last_api_error"] = str(exc)
            logger.warning("Uploads fetch failed for %s: %s", ch.channel_id, exc)
            continue
        summary["api_successes"] += 1

        ch.last_checked_at = _now()
        db.commit()

        for v in uploads:
            existing = (
                db.query(TrackedVideo)
                .filter(TrackedVideo.video_id == v["video_id"])
                .first()
            )
            if existing and existing.scanned:
                continue
            if existing is None:
                tv = TrackedVideo(
                    video_id=v["video_id"],
                    channel_id=ch.channel_id,
                    title=v["title"][:500],
                    published_at=v["published_at"],
                )
                db.add(tv)
                try:
                    db.commit()
                    db.refresh(tv)
                except IntegrityError:
                    db.rollback()
                    tv = (
                        db.query(TrackedVideo)
                        .filter(TrackedVideo.video_id == v["video_id"])
                        .first()
                    )
                    if tv is None or tv.scanned:
                        continue
                else:
                    summary["new_videos"] += 1
            else:
                tv = existing

            if yt.remaining_today(db) < yt.COST_LIST:
                summary["stopped_early"] = True
                break
            try:
                comments = yt.list_comments(db, v["video_id"], comments_per_video)
            except yt.YouTubeQuotaError:
                summary["stopped_early"] = True
                break
            except yt.YouTubeAPIError as exc:
                # Transient failure (network/API) — leave the video UNscanned so
                # it is retried on the next scan instead of silently skipped.
                summary["api_failures"] += 1
                summary["last_api_error"] = str(exc)
                logger.warning(
                    "Comment fetch failed for %s (leaving unscanned for retry): %s",
                    v["video_id"], exc,
                )
                continue
            summary["api_successes"] += 1

            summary["comments_scanned"] += len(comments)
            for c in comments:
                sc = score_intent(c["text"])
                if sc < SAVE_THRESHOLD:
                    continue
                if db.query(LeadComment).filter(LeadComment.comment_id == c["comment_id"]).first():
                    continue
                lead = LeadComment(
                    comment_id=c["comment_id"],
                    video_id=v["video_id"],
                    channel_id=ch.channel_id,
                    author=c["author"][:200],
                    text=c["text"][:2000],
                    intent_score=sc,
                )
                db.add(lead)
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    continue
                summary["leads_found"] += 1

            tv.scanned = True
            db.commit()

        if summary["stopped_early"]:
            break

    summary["quota_used_end"] = yt.units_used_today(db)
    return summary


# ── Approve → content systems + AI pack ──────────────────────────────────────

def _derive_topic(text: str) -> str:
    """Turn a raw comment into a short topic/question title (<=140 chars)."""
    t = " ".join((text or "").split())
    # Prefer the first question sentence if present.
    m = re.search(r"([^.?!]*\?)", t)
    candidate = m.group(1).strip() if m else t
    candidate = candidate.strip().strip('"').strip()
    if len(candidate) > 140:
        candidate = candidate[:137].rstrip() + "..."
    return candidate or "A seeker's question"


def _fallback_pack(question: str) -> dict:
    q = question.rstrip("?.!").strip()
    ql = q.lower()
    return {
        "question": question,
        "video_title": f"The Truth About {q} (What the Church Really Teaches)",
        "video_idea": (
            f"A direct, pastoral answer to a real seeker who asked: \"{question}\". "
            "Open with their exact question, then walk through Scripture, the Church "
            "Fathers, and the Catechism to give the full Catholic answer."
        ),
        "short_script": "\n".join([
            f"HOOK: Someone recently asked, \"{question}\" — and it deserves a real answer.",
            f"BUILD: Here's what many people assume about {ql}, and why it feels convincing.",
            "EVIDENCE: What Scripture says first, then the early Church Fathers and the Catechism.",
            "ANSWER: The full Catholic teaching, stated plainly and pastorally.",
            "CTA: Get the complete teaching free by email, and keep seeking the truth.",
        ]),
        "email_subject": f"You asked about {ql} — here's the Catholic answer",
        "email_body": "\n".join([
            f"Someone recently asked a question a lot of people are quietly wondering: {question}",
            "",
            f"It's a fair question, and the Catholic Church has a clear, beautiful answer rooted in "
            f"Scripture, the Church Fathers, and 2,000 years of Tradition.",
            "",
            "We're preparing a full teaching on this. Reply and let us know what you'd most like answered.",
            "",
            "Keep seeking the truth.",
        ]),
    }


async def _generate_content_pack(question: str, comment_text: str) -> tuple[dict, str]:
    """Deterministic-first content pack; AI only enriches. Never raises."""
    pack = _fallback_pack(question)
    source = "deterministic"
    try:
        from app.services.ai_service import generate_with_ai

        prompt = (
            "A truth-seeker left this YouTube comment:\n"
            f"\"{comment_text[:500]}\"\n\n"
            "Create a Catholic content pack answering their question. Respond with ONLY a JSON "
            "object (no markdown) with these exact string keys: "
            "\"video_title\" (<70 chars, curiosity-driven), "
            "\"video_idea\" (2-3 sentences), "
            "\"short_script\" (a 5-beat hook-to-CTA outline), "
            "\"email_subject\" (<70 chars), "
            "\"email_body\" (plain text, one paragraph per line, warm and evangelistic)."
        )
        raw = (await generate_with_ai(prompt)).strip()
        parsed = _extract_json(raw)
        if isinstance(parsed, dict):
            for key in ("video_title", "video_idea", "short_script", "email_subject", "email_body"):
                val = parsed.get(key)
                if isinstance(val, str) and val.strip():
                    pack[key] = val.strip()
            pack["question"] = question
            source = "ai"
    except Exception as exc:  # noqa: BLE001 — never 402, keep deterministic pack
        logger.info("Content pack AI enrich skipped: %s", exc)
    return pack, source


def _extract_json(raw: str):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw).rstrip("`").strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(raw[start:end + 1])
    except (ValueError, TypeError):
        return None


async def approve_lead(db: Session, lead_id: int) -> dict | None:
    """Approve a lead: create Topic + pipeline idea + email draft + AI pack."""
    lead = db.get(LeadComment, lead_id)
    if lead is None:
        return None
    if lead.review_status == "approved" and lead.generated_content:
        return {"lead": _serialize_lead(db, lead), "already_approved": True}

    from app.services import topic_service, email_queue_service
    from app.models.db_models import Topic

    question = _derive_topic(lead.text)
    pack, source = await _generate_content_pack(question, lead.text)

    # Conversion Engine: suggested human reply for this comment (generation
    # only — NEVER auto-posted). Fail-silent: approval never depends on it,
    # and a reply-engine rate limit must not block approving a lead.
    try:
        from app.services import conversion_engine
        pack["comment_reply"] = await conversion_engine.generate_comment_reply(lead.text)
    except Exception as exc:
        logger.info("Comment reply suggestion skipped for lead %s: %s", lead_id, exc)

    # Growth Brain: attach the best optimized titles + viral hooks so the admin
    # gets ready-to-use, CTR-scored packaging with the approved idea. Fail-silent
    # — approval never depends on this.
    try:
        from app.services import title_scorer, viral_hook_engine
        opt = await title_scorer.generate_optimized_titles(question)
        pack["optimized_titles"] = opt.get("top_titles", [])
        hooks = await viral_hook_engine.generate_hooks(question)
        pack["viral_hooks"] = hooks.get("short_hooks", [])[:5]
    except Exception as exc:
        logger.info("Growth Brain packaging skipped for lead %s: %s", lead_id, exc)

    # 1. Audience Topic (approved) — also surfaces in the Content Plan ranking.
    #    Dedup so a retry after a partial failure reuses the existing topic
    #    instead of creating a duplicate (approve isn't a single transaction).
    title = question[:300]
    existing_topic = (
        db.query(Topic)
        .filter(Topic.source == "youtube_lead", Topic.title == title)
        .first()
    )
    if existing_topic is not None:
        topic = topic_service._serialize(existing_topic, public=False)
    else:
        topic = topic_service.create_topic(
            db,
            title=title,
            description=f"From a YouTube comment by {lead.author}: {lead.text[:280]}",
            status="approved",
            source="youtube_lead",
        )

    # 2. Content Ideas pipeline entry (dedup on the lead's note for retry-safety).
    idea_notes = f"Lead-sourced (YouTube comment). Seeker asked: {question}"
    if not db.query(PipelineItem).filter(PipelineItem.notes == idea_notes).first():
        db.add(PipelineItem(
            title=pack["video_title"][:500],
            stage="idea",
            notes=idea_notes,
        ))
        db.commit()

    # 3. Newsletter draft (draft only — never bulk-sends). Ends with a reply
    #    prompt (conversion-engine engagement driver) unless one is present.
    email_body = pack["email_body"]
    if "hit reply" not in email_body.lower() and "reply to this email" not in email_body.lower():
        email_body += (
            "\n\nHit reply and tell me — what's the one question about this "
            "you've never gotten a straight answer to? I read every response."
        )
    email_queue_service.create_draft(
        db,
        subject=pack["email_subject"],
        body=email_body,
        source="lead_discovery",
        topic_id=topic["id"],
        dedup=True,
    )

    lead.review_status = "approved"
    lead.generated_content = json.dumps(pack)
    db.commit()

    return {
        "lead": _serialize_lead(db, lead),
        "topic": topic,
        "content_pack": pack,
        "content_source": source,
    }
