# Branch Merge Project

Read-only consolidated reporting (trial balance, balance sheet, P&L, transactions) across
Sanasa MicroBanker (MBWin) branch databases: Head Office (`001`) and Mahapitiya (`002`).

See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for the full plan.

## Requirements

- Python 3.12, Node.js 20+
- SQL Server with both MBWin databases, plus **ODBC Driver 17 for SQL Server**

## Backend (FastAPI)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env      # edit DB names / server
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

Open http://localhost:3000
