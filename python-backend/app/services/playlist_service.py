PLAYLIST_KEYWORDS: dict[str, list[str]] = {
    "Story Quizzes for the Soul": [
        "quiz", "story quiz", "soul", "test your faith", "bible quiz",
    ],
    "Beware of Contradictions": [
        "contradiction", "false teaching", "heresy", "inconsistency", "misleading",
        "beware", "false prophet", "deceive",
    ],
    "Easter Special": [
        "easter", "resurrection", "risen", "good friday", "holy week",
        "passion", "calvary",
    ],
    "Ancient Heresies Exposed": [
        "heresy", "gnostic", "arianism", "donatism", "pelagianism", "ancient",
        "early church error", "expose heresy",
    ],
    "The Venom Series": [
        "venom", "poison", "toxic", "spiritual danger", "antidote",
    ],
    "The Papacy Series": [
        "pope", "papacy", "peter", "vatican", "holy see", "successor",
        "bishop of rome",
    ],
    "The Battles to Keep the Church Catholic": [
        "battle", "defend", "council", "schism", "reformation", "catholic church",
        "fight for faith", "apologist",
    ],
    "Death Judgment Heaven Hell": [
        "death", "judgment", "heaven", "hell", "purgatory", "afterlife",
        "last things", "eschatology", "eternal",
    ],
    "Prayers": [
        "prayer", "rosary", "novena", "intercession", "litany", "devotion",
        "daily prayer", "pray",
    ],
    "Christmas Specials": [
        "christmas", "nativity", "advent", "bethlehem", "incarnation",
        "born savior", "manger",
    ],
}

DEFAULT_PLAYLIST = "General Content"


def route_to_playlist(text: str) -> str:
    """
    Map a piece of text to the most relevant playlist based on keyword matching.
    Returns the playlist name, or 'General Content' if no match is found.
    """
    normalised = text.lower()

    scores: dict[str, int] = {}
    for playlist, keywords in PLAYLIST_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in normalised)
        if score > 0:
            scores[playlist] = score

    if not scores:
        return DEFAULT_PLAYLIST

    return max(scores, key=lambda k: scores[k])
