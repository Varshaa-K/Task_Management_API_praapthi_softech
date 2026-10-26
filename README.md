# Task Management REST API

A FastAPI task API with JWT authentication, SQLAlchemy persistence, Alembic migrations, and pytest tests.

## Requirements

- Python 3.11 or newer

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `SECRET_KEY` in `.env` to a unique random value of at least 32 characters. Keep `.env` private and out of version control. `DATABASE_URL` defaults to a local SQLite database.

## Run

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

Interactive API documentation is available at <http://127.0.0.1:8000/docs>.

## API

- `POST /auth/register` — create an account; passwords are hashed with Argon2.
- `POST /auth/login` — exchange JSON email/password credentials for a 30-minute JWT.
- `GET /users/me` — retrieve the authenticated user's profile.
- `POST /tasks`, `GET /tasks`, `GET /tasks/{task_id}`, `PATCH /tasks/{task_id}`, `DELETE /tasks/{task_id}` — CRUD for the authenticated user's own tasks.
- `GET /tasks/stats` — per-status counts and overdue count for the authenticated user.

Send authenticated requests with `Authorization: Bearer <access_token>`. Task status is `todo`, `in_progress`, or `done`. Priority is an integer from 1 (highest) to 5. Listing supports `status`, `priority`, `page` (default 1), `limit` (default 20, maximum 100), and `sort=asc|desc` (due date; null dates sort last). Overdue means a task with a due date before now whose status is not `done`.

## Migrations

Create and apply schema changes with Alembic:

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Tests

```powershell
pytest -q
```
