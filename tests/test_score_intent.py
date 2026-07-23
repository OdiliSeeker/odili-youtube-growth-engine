"""Tests for the seeker-intent gate ``lead_discovery_service.score_intent``.

``score_intent`` is the pure-Python, deterministic heuristic that decides which
public YouTube comments become leads: only comments scoring at/above
``SAVE_THRESHOLD`` are stored for human review. It is the single point where a
real seeker's question is either surfaced or silently dropped, so these tests
pin down its behaviour on three fronts:

  * genuine seeker questions clear the threshold (no false negatives),
  * spam / self-promotion / low-signal chatter stay below it (no false
    positives), and
  * the discounting/weighting rules (short-comment halving, question-word boost,
    faith-term cap, phrase cap, negative gate) keep their exact contributions so
    a future weight tweak is caught.

No YouTube API is involved — ``score_intent`` is pure and deterministic.
"""

import pytest

from app.services.lead_discovery_service import SAVE_THRESHOLD, score_intent


# ── Genuine seekers must clear the threshold (no false negatives) ─────────────

SEEKER_COMMENTS = [
    "how do i become catholic?",
    "How can I become Catholic?",
    "i'm struggling with my faith",
    "I want to become Catholic, where do I start?",
    "i'm confused about confession, can someone explain?",
    "how do i pray the rosary?",
    "I don't understand the Eucharist, please explain",
    "I'm searching for the truth and losing my faith, help me",
    "Is it true that the Church teaches this about salvation?",
    "New to all this — how do you go to confession?",
]


@pytest.mark.parametrize("text", SEEKER_COMMENTS)
def test_genuine_seekers_clear_threshold(text):
    assert score_intent(text) >= SAVE_THRESHOLD


# ── Non-English seekers must clear the threshold too (Spanish/French/Portuguese) ─

SPANISH_SEEKER_COMMENTS = [
    "¿Cómo puedo ser católico?",
    "quiero ser católico, ¿por dónde empiezo?",
    "no entiendo la confesión, ¿alguien puede explicar?",
    "estoy buscando la verdad y perdiendo la fe, necesito ayuda",
    "¿es verdad que la iglesia enseña esto sobre la salvación?",
    "¿cómo rezar el rosario?",
    "estoy confundido sobre la eucaristía, ¿pueden explicar?",
]

FRENCH_SEEKER_COMMENTS = [
    "comment puis-je devenir catholique ?",
    "je veux devenir catholique, par où commencer ?",
    "je ne comprends pas la confession, pouvez-vous expliquer ?",
    "je cherche la vérité et je perds la foi, j'ai besoin d'aide",
    "est-ce vrai que l'église enseigne cela sur le salut ?",
    "comment prier le chapelet ?",
]

PORTUGUESE_SEEKER_COMMENTS = [
    "como posso ser católico?",
    "quero ser católico, por onde começo?",
    "não entendo a confissão, alguém pode explicar?",
    "estou procurando a verdade e perdendo a fé, preciso de ajuda",
    "é verdade que a igreja ensina isso sobre a salvação?",
    "como rezar o rosário?",
]

GERMAN_SEEKER_COMMENTS = [
    "wie kann ich katholisch werden?",
    "ich möchte katholisch werden, wo fange ich an?",
    "ich verstehe die beichte nicht, kann jemand erklären?",
    "ich suche die wahrheit und verliere meinen glauben, ich brauche hilfe",
    "stimmt es, dass die kirche das über die erlösung lehrt?",
    "wie bete ich den rosenkranz?",
]

TAGALOG_SEEKER_COMMENTS = [
    "paano ako magiging katoliko?",
    "gusto kong maging katoliko, saan ako magsisimula?",
    "hindi ko maintindihan ang kumpisal, may makakapagpaliwanag ba?",
    "hinahanap ko ang katotohanan at nawawalan ako ng pananampalataya, tulungan niyo ako",
    "totoo ba na ito ang itinuturo ng simbahan tungkol sa kaligtasan?",
    "paano magdasal ng rosaryo?",
    "nalilito ako sa eukaristiya, pakipaliwanag po",
]

ITALIAN_SEEKER_COMMENTS = [
    "come posso diventare cattolico?",
    "voglio diventare cattolico, da dove comincio?",
    "non capisco la confessione, qualcuno può spiegare?",
    "sto cercando la verità e sto perdendo la fede, ho bisogno di aiuto",
    "è vero che la chiesa insegna questo sulla salvezza?",
    "come pregare il rosario?",
]


@pytest.mark.parametrize(
    "text",
    SPANISH_SEEKER_COMMENTS + FRENCH_SEEKER_COMMENTS + PORTUGUESE_SEEKER_COMMENTS
    + GERMAN_SEEKER_COMMENTS + ITALIAN_SEEKER_COMMENTS + TAGALOG_SEEKER_COMMENTS,
)
def test_non_english_seekers_clear_threshold(text):
    assert score_intent(text) >= SAVE_THRESHOLD


def test_inverted_question_mark_counts():
    # Spanish opens questions with "¿" — it must earn the same 0.25 as "?".
    with_mark = score_intent("¿dónde encuentro a dios")
    without_mark = score_intent("dónde encuentro a dios")
    assert with_mark - without_mark == pytest.approx(0.25)


def test_accented_words_tokenize():
    # "católico" and "fé" must survive tokenization as single faith terms
    # (the old [a-z'] regex split them at the accent).
    assert score_intent("perdi a fé e busco a verdade, me ajude") >= SAVE_THRESHOLD


def test_non_english_first_person_bonus():
    # "estoy"/"je"/"quero" mark a personal plea the same way "i"/"my" do.
    base = score_intent("luchando con la duda todos los dias")
    personal = score_intent("estoy luchando con la duda todos los dias")
    assert personal > base


def test_german_italian_first_person_bonus():
    # "ich" (de) and "io"/"sono" (it) earn the same first-person bonus.
    de_base = score_intent("kämpfen mit dem zweifel jeden tag hier")
    de_personal = score_intent("ich kämpfe mit dem zweifel jeden tag hier")
    assert de_personal > de_base
    it_base = score_intent("lottando con il dubbio ogni giorno qui")
    it_personal = score_intent("io sto lottando con il dubbio ogni giorno qui")
    assert it_personal > it_base


def test_tagalog_first_person_bonus():
    # "ako"/"ko" mark a personal plea the same way "i"/"my" do.
    base = score_intent("nahihirapan sa pagdududa araw-araw dito")
    personal = score_intent("nahihirapan ako sa pagdududa araw-araw dito")
    assert personal > base


def test_eszett_tokenizes():
    # "ß" must stay inside the token so words like "weiß" don't split; a real
    # German seeker sentence containing "ß" still clears the threshold.
    assert score_intent(
        "ich weiß nicht wie ich beten soll, hilf mir gott"
    ) >= SAVE_THRESHOLD


@pytest.mark.parametrize("text", [
    "buen video",           # es: nice video
    "super vidéo merci",    # fr: great video thanks
    "ótimo conteúdo",       # pt: great content
    "gracias",
    "merci beaucoup",
    "obrigado",
    "tolles video danke",   # de: great video thanks
    "danke schön",          # de: thank you
    "bel video grazie",     # it: nice video thanks
    "grazie mille",         # it: thanks a lot
    "salamat",              # tl: thanks
    "ganda ng video",       # tl: nice video
    "salamat po sa video",  # tl: thank you for the video
])
def test_non_english_chatter_below_threshold(text):
    assert score_intent(text) < SAVE_THRESHOLD


def test_non_english_spam_still_zero():
    # The negative gate applies regardless of language.
    assert score_intent("quiero ser católico, visita mi canal www.spam.example") == 0.0


def test_borderline_struggle_is_kept():
    # "i'm struggling with my faith" is exactly the kind of quiet cry for help
    # that must not be dropped: two seeker phrases (0.4) + one faith term (0.12)
    # + a first-person pronoun (0.1) = 0.62, just above the 0.6 cutoff.
    assert score_intent("i'm struggling with my faith") == pytest.approx(0.62)


# ── Spam / self-promotion must score exactly 0 (negative gate) ────────────────

SPAM_COMMENTS = [
    "Subscribe to my channel for more!",
    "check out my channel",
    "sub for sub?",
    "DM me for a free gift card",
    "Visit my site https://spam.example.com",
    "www.buythisnow.example",
    "Use this promo code to make money fast",
    "click here to win",
]


@pytest.mark.parametrize("text", SPAM_COMMENTS)
def test_spam_scores_zero(text):
    assert score_intent(text) == 0.0


def test_negative_gate_overrides_seeker_signals():
    # Even a perfect-looking seeker question is dropped if it carries a spam
    # marker — the negative gate short-circuits before any points are awarded.
    seeker = "how do i become catholic?"
    assert score_intent(seeker) >= SAVE_THRESHOLD
    assert score_intent(seeker + " check out my channel") == 0.0


# ── Low-signal chatter must stay below the threshold (no false positives) ─────

CHATTER_COMMENTS = [
    "nice video",
    "great content thanks",
    "first!",
    "lol",
    "amen",
    "wow",
    "this is amazing keep it up",
]


@pytest.mark.parametrize("text", CHATTER_COMMENTS)
def test_low_signal_chatter_below_threshold(text):
    assert score_intent(text) < SAVE_THRESHOLD


def test_empty_and_none_score_zero():
    assert score_intent("") == 0.0
    assert score_intent("   ") == 0.0
    assert score_intent(None) == 0.0


# ── Discounting / weighting rules (catch weight changes) ──────────────────────

def test_short_comment_is_halved():
    # A comment under 12 chars has its whole score halved. "why god?" earns a
    # question mark (0.25) + question-word boost (0.15) + one faith term (0.12)
    # = 0.52, halved to 0.26 because len("why god?") == 8 < 12.
    assert score_intent("why god?") == pytest.approx(0.26)


def test_length_boundary_not_halved():
    # At exactly 12 characters the halving must NOT apply. Compare a short faith
    # phrase to itself padded past the boundary.
    short = "god jesus"           # len 9  -> halved
    long = "god and jesus"        # len 13 -> not halved, 2 faith terms = 0.24
    assert score_intent(short) == pytest.approx(0.12)   # 0.24 * 0.5
    assert score_intent(long) == pytest.approx(0.24)


def test_question_word_boost_is_isolated():
    # A leading question word adds exactly 0.15. The two phrasings hit the same
    # seeker phrase ("* explain") and the same faith term (trinity); the only
    # difference is whether the first word is a question word.
    with_boost = score_intent("can you explain the trinity")      # "can" boosts
    without_boost = score_intent("please explain the trinity")     # "please" does not
    assert with_boost - without_boost == pytest.approx(0.15)


def test_faith_terms_are_capped():
    # Faith terms contribute 0.12 each but cap at 0.36 (3 terms). A comment
    # stuffed with faith words alone must not exceed the cap — so doctrine
    # keyword spam can never clear the threshold on faith terms alone.
    stuffed = "jesus christ god church faith prayer heaven"
    assert score_intent(stuffed) == pytest.approx(0.36)
    assert score_intent(stuffed) < SAVE_THRESHOLD


def test_seeker_phrases_are_capped():
    # Seeker phrases contribute 0.2 each but cap at 0.4 (2 phrases). Three
    # overlapping phrases here still only yield the 0.4 cap for the phrase term.
    # "i want to", "how do i", "where do i start" -> capped at 0.4; no faith
    # term, no question mark, first word "i" is not a question word, plus the
    # first-person pronoun bonus (0.1) => 0.5.
    text = "i want to know how do i find where do i start"
    assert score_intent(text) == pytest.approx(0.5)
