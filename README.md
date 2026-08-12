# Solomon's Streak FastAPI backend

Production-oriented API for the supplied frontend. Every private record carries an owner/user foreign key and every endpoint derives the user from the access token. New accounts receive an empty task list and a `user_stats` row containing zeros.

## Run

```bash
cp .env.example .env
# Replace SECRET_KEY
docker compose up --build
```

Open `http://localhost:8000/docs`.

## Core behavior

- Registration creates a user and zeroed stats atomically.
- Passwords use Argon2. Access tokens are short-lived; opaque refresh tokens are hashed in PostgreSQL and rotated.
- Task completion is transactional and row-locks stats to avoid double awards.
- Score: Low +10, Medium +15, High +20, completed focus minutes +1/minute; 7/30/100-day bonuses.
- A day counts when at least one task is completed. Reopening rebuilds current streak from completion dates.
- `/users` lists all active users except the caller and decorates follow, follows-me, and mutual status.
- Direct conversation keys are canonical, so each pair gets exactly one room.
- WebSocket messages are authenticated and stored before broadcast.
- Community posts support feed sorting, author-only edits/deletes, likes, comments, and nested replies.

## Frontend replacement map

Replace localStorage calls with:

- Login/register: `/api/v1/auth/*`
- Dashboard/profile: `/api/v1/users/me`, `/api/v1/progress`
- Tasks/calendar: `/api/v1/tasks`
- Focus completion: `/api/v1/progress/focus`
- Make Friends: `/api/v1/users`, `/users/{id}/follow`
- Chat: create `/api/v1/chat/direct/{id}`, load history, then connect `ws://host/api/v1/chat/ws/{conversation_id}?token=ACCESS_TOKEN`
- Discussions: `/api/v1/discussions`

Use `Authorization: Bearer <access_token>`. In a browser production deployment, prefer storing the refresh token in a Secure, HttpOnly, SameSite cookie. The sample returns it in JSON for framework-neutral integration.

## Production hardening before launch

1. Generate Alembic migrations and disable development `create_all`.
2. Put API behind TLS and a reverse proxy.
3. Add verified email, password reset, rate limiting, audit logs, moderation/reporting, block controls, and media scanning.
4. Replace the process-local WebSocket hub with Redis Pub/Sub for multiple API replicas.
5. Add tests, backups, observability, retention rules, and privacy/terms flows.
6. Do not retain the hard-coded owner password visible in the supplied HTML. Rotate it immediately and remove that text from the frontend.
