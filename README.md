# Solomon's Streak Full Stack

Production-oriented FastAPI application serving the final glassmorphism frontend and a complete persistence/social API.

## Included

- Signed bearer authentication with PBKDF2 password hashing
- Fixed owner account supplied through environment variables
- Profile completion, avatars, presence and last-seen status
- Task CRUD, calendar-ready due dates, focus sessions and analytics
- Persistent frontend state migration/synchronization
- Discussions, likes, comments and nested replies
- Following, people directory, private messages and WebSocket realtime transport
- Owner-only user list, role control and data export
- SQLite local development and PostgreSQL production support
- Render Blueprint, Dockerfile, Procfile, health endpoint and API docs
- Automated user, social, owner, API, persistence and frontend smoke tests

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://localhost:8000`. API docs are at `/api/docs`.

## Tests

```bash
pytest -q
```

## Render deployment

1. Push this folder to GitHub.
2. In Render choose **New > Blueprint** and select the repository.
3. Set `OWNER_PASSWORD` in Render to a secure secret. The requested prototype default is shown in `.env.example`, but changing it before a public deployment is strongly recommended.
4. Deploy. `render.yaml` provisions the web service and PostgreSQL database.

Render uses `pip install -r requirements.txt` and starts `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

## Important production notes

- Rotate `SECRET_KEY` and `OWNER_PASSWORD` before public release.
- The adapter migrates the final frontend's local state into the signed-in user's server-side state record and continuously synchronizes changes.
- For multi-instance WebSocket scale, replace the in-memory connection hub with Redis pub/sub.
- Add Alembic migrations before changing production models after initial deployment.
