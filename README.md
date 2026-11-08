# Branch Merge Project

Read-only consolidated reporting (trial balance, balance sheet, P&L, transactions) across
Sanasa MicroBanker (MBWin) branch databases: Head Office (`001`) and Mahapitiya (`002`).

See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for the full plan.

## Requirements

- Python 3.12, Node.js 20+
- SQL Server with both MBWin databases, plus **ODBC Driver 17 for SQL Server**

## Database (MB_Consolidated)

```sh
sh database/deploy.sh      # creates the consolidated views; see database/README.md
```

## Backend (FastAPI)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env      # edit DB names / server
# set JWT_SECRET in .env:  python -c "import secrets;print(secrets.token_urlsafe(48))"
.\.venv\Scripts\python -m app.manage create-user admin --name "Administrator" --role admin --branch all
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs · Tests: `.\.venv\Scripts\python -m pytest`

## Frontend (Next.js)

```powershell
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Open http://localhost:3000 (dashboard, trial balance, balance sheet, P&L, transactions).

DB findings: [docs/DB_ANALYSIS.md](docs/DB_ANALYSIS.md) · Full implementation guide: [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md).
