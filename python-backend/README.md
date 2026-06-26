# Odili Truth Seeker Backend

A clean, modular FastAPI backend for the Odili Truth Seeker Catholic media ministry.

---

## Features

| Module | Endpoint(s) | Description |
|---|---|---|
| Health | `GET /health` | Liveness check — returns `{"status": "OK"}` |
| Content Generation | `POST /generate-idea` | GPT-4o generates a viral title, hook, and short script |
| Playlist Routing | `POST /playlist` | Maps text to the best-matching content playlist |
| Email List | `POST /emails` | Subscribe an email address |
| Email List | `GET /emails` | List all subscribed emails |
| Scheduler | `GET /emails/scheduler` | Returns whether today is a send day (Sun/Wed/Fri) |

---

## Project Structure

```
python-backend/
├── app/
│   ├── main.py                  # FastAPI app factory, middleware, router registration
│   ├── models/
│   │   └── schemas.py           # Pydantic request/response models
│   ├── routes/
│   │   ├── health.py            # GET /health
│   │   ├── ideas.py             # POST /generate-idea
│   │   ├── playlist.py          # POST /playlist
│   │   └── emails.py            # POST/GET /emails, GET /emails/scheduler
│   └── services/
│       ├── ai_service.py        # generate_with_ai(prompt) → GPT-4o call
│       ├── playlist_service.py  # route_to_playlist(text) → playlist name
│       ├── email_service.py     # add_email / list_emails (in-memory)
│       └── scheduler_service.py # should_send_emails() → bool
├── run.py                       # Uvicorn entry point
├── requirements.txt
└── .env.example
```

---

## Setup

```bash
cd python-backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in OPENAI_API_KEY
python run.py
```

Interactive docs: http://localhost:8000/docs

---

## Playlists

Text is matched to one of the following playlists by keyword scoring:

- Story Quizzes for the Soul
- Beware of Contradictions
- Easter Special
- Ancient Heresies Exposed
- The Venom Series
- The Papacy Series
- The Battles to Keep the Church Catholic
- Death Judgment Heaven Hell
- Prayers
- Christmas Specials
- **Default:** General Content

---

## Scheduler

`should_send_emails()` returns `True` on **Sundays**, **Wednesdays**, and **Fridays**.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT-4o |
| `PORT` | No | Server port (default: `8000`) |
