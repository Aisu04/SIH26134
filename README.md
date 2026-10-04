# SkillBridge AI

SkillBridge AI is a full-stack platform designed to align industry skill demand with learner and institutional outcomes. The project is structured around a learning intelligence engine that connects skill gaps, personalized recommendations, training impact tracking, and job opportunity matching.

## Stage-based architecture

### Stage 1: foundation and experience
- React + Vite + TypeScript + Tailwind frontend
- FastAPI backend with health checks and API wiring
- Shared project structure for frontend and backend growth
- Dashboard-first landing experience aligned to the hackathon theme

### Stage 2: data foundation and persistence
- PostgreSQL database with SQLAlchemy models
- Schema for users, institutions, skills, learner profiles, learning paths, opportunities, and employment outcomes
- Initial Alembic migration for the SQLAlchemy models

### Stage 3: core intelligence
- Skill-gap assessment logic
- Personalized learning recommendations
- Opportunity matching and employer demand alignment
- Outcome tracking data model

### Stage 4: analytics and decision support
- Dashboards for training effectiveness, learner progression, and placement outcomes
- KPI aggregation and reporting endpoints
- Institutional analytics for skills demand vs. supply

## Folder structure

- frontend/: React application
- backend/: FastAPI application
  - app/: application package
  - .venv/: local Python virtual environment

## Local setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `DATABASE_URL` and `JWT_SECRET_KEY` in `.env`. Create the PostgreSQL database named in `DATABASE_URL`, then apply the schema:

```bash
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Public registration only creates learner accounts. For initial setup, create the first admin interactively after migrations have run:

```bash
python -m scripts.create_admin
```

The script prompts for the admin password without echoing it and refuses to run if an admin already exists. Sign in as that admin and use `POST /api/v1/admin/institutions` to create institutions, then `POST /api/v1/admin/users` to provision `institution` and `employer` accounts. Institution accounts must be assigned to an existing institution; only institution accounts may receive an institution assignment.

Run backend tests with:

```bash
pytest -q
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Create a production build with `npm run build`.

## Notes

- The current backend test suite uses an isolated in-memory SQLite database; production persistence is configured for PostgreSQL.
- Institution analytics and deployment hardening remain planned work and are not represented as live metrics.
