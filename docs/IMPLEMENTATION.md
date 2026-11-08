# Implementation Guide – Branch Merge Reporting

This document covers what has been built so far, how it works, and how to run it.
Background and decisions are in [PROJECT_PLAN.md](PROJECT_PLAN.md). Database findings are in
[DB_ANALYSIS.md](DB_ANALYSIS.md).

_Last updated: 08-Nov-2026 (commit `42f5de5`)_

---

## 1. Status summary

| Phase | Status | Output |
|---|---|---|
| 0 – Setup | ✅ Done | Repo, backend and frontend scaffolds, health check end to end |
| 1 – Database analysis | ✅ Done | `docs/DB_ANALYSIS.md` |
| 2 – Consolidated database | ✅ Done | `database/` scripts → `MB_Consolidated` views |
| 3 – Backend API | ✅ Done | FastAPI report endpoints + Excel export, 8 tests passing |
| 4 – Frontend | ✅ First version | Dashboard, trial balance, balance sheet, P&L, transactions |
| 5 – Verification & deployment | ⏳ Not started | Reconcile with MBWin, login, server deploy |

---

## 2. Architecture

```
MicroBanker_ho  (HO, 001)  ─┐
                            ├─►  MB_Consolidated (views only, BranchCode tagged)
MicroBanker_br  (BR, 002)  ─┘              │
                                           ▼
                           FastAPI backend  :8000   (read-only, JSON + Excel)
                                           │
                                           ▼
                           Next.js frontend :3000   (server-rendered report pages)
```

- The MBWin databases are **never written to**. Only `SELECT` statements are used.
- Every row carries `BranchCode` (`001` / `002`), because customer IDs and account numbers
  clash between the two databases.
- Amounts are stored by MBWin as integer **cents**. The backend converts to rupees
  (`AMOUNT_DIVISOR=100`, still to be confirmed).

---

## 3. Repository layout

```
branchmerge/
├── database/
│   ├── 01_create_db.sql     creates MB_Consolidated + BranchMap table
│   ├── 02_views_gl.sql      GL views (sort codes, accounts, month-end balances)
│   ├── 02_views_ops.sql     customers, accounts, loans, transactions
│   ├── 03_security.sql      read-only login branchmerge_ro
│   ├── deploy.sh            runs 01 + 02 scripts with sqlcmd
│   └── README.md
├── backend/
│   ├── app/main.py          FastAPI app, CORS (GET only), routers
│   ├── app/core/config.py   settings from .env
│   ├── app/core/db.py       SQLAlchemy engine (pyodbc, ApplicationIntent=ReadOnly)
│   ├── app/api/health.py    /api/health
│   ├── app/api/branches.py  /api/branches
│   ├── app/api/reports.py   GL, reports, transactions, export
│   ├── app/services/reports.py   report queries and calculations
│   └── tests/test_api.py
├── frontend/src/
│   ├── app/                 page.tsx (dashboard), trial-balance/, balance-sheet/,
│   │                        profit-loss/, transactions/, layout.tsx (nav)
│   ├── components/ui.tsx    Filters, ReportHeader, Section, Check
│   ├── components/PrintButton.tsx
│   └── lib/api.ts           API URL, branch list, money formatting
└── docs/                    PROJECT_PLAN, DB_ANALYSIS, IMPLEMENTATION (this file)
```

---

## 4. Database layer (MB_Consolidated)

| Object | Description |
|---|---|
| `BranchMap` (table) | `001` Head Office → HO DB, `002` Mahapitiya → BR DB |
| `vw_Branches` | Branch list |
| `vw_GLSortCodes` | `T_GLSC` headings from both branches |
| `vw_GLAccounts` | `T_GLAC` (current year, `Closed=0`) + `T_GLACHIST` (closed years, `Closed=1`) |
| `vw_GLBalances` | One row per branch / year / month (1–12) / account: `MonthDr`, `MonthCr`, `YtdDr`, `YtdCr`, `ClosingBal` |
| `vw_Customers` | `T_CIF` |
| `vw_Accounts` | Savings (`SV`), time deposits (`TD`) and loans (`LN`) in one list |
| `vw_Loans` | `T_LNACC` with arrears, provision and rate |
| `vw_Transactions` | `T_TRNHIST` |

**Balance calculation:** `ClosingBal(month M) = OBalAmt + Σ Debits(1..M) − Σ Credits(1..M)`.
Debit is positive, credit is negative. For the current open month this is month-to-date.

**Deploy / refresh:**

```sh
sh database/deploy.sh                                              # local restore names
DB_SERVER=SRV HO_DB=MicroBanker_ho BR_DB=MicroBanker_br sh database/deploy.sh   # production
```

The scripts can be re-run safely. Re-run them if the database names change.
All three databases must be on the same SQL Server instance.

---

## 5. Backend API

Base URL `http://localhost:8000/api`. Interactive docs are at `/docs`.
`branch` = `001` | `002` | `all` (default `all`). Any other value returns 422.

| Method & path | Parameters | Returns |
|---|---|---|
| `GET /health` | – | API status and each branch DB state |
| `GET /branches` | – | Branch codes and names |
| `GET /gl/accounts` | `branch` | Current-year chart of accounts |
| `GET /reports/trial-balance` | `date`, `branch` | Lines (debit/credit, per-branch net), totals, `balanced` |
| `GET /reports/balance-sheet` | `date`, `branch` | Assets / liabilities / equity grouped by level-2 heading, current-year profit, `balanced` |
| `GET /reports/profit-loss` | `from`, `to`, `branch` | Income / expenses grouped, net profit (whole months) |
| `GET /transactions` | `branch`, `from`, `to`, `acc`, `page`, `size` (≤500) | Paged transactions, newest first; id = `BranchCode-Recid` |
| `GET /reports/{name}/export` | `format=xlsx` + the report's parameters | Excel file (`trial-balance`, `balance-sheet`, `profit-loss`) |

**Report rules in the code (`app/services/reports.py`):**
- A date selects the month-end balance of that month.
- For "all", balances are summed per GL account. The HO account title is used.
- The balance sheet adds unclosed current-year profit (income + expense) to the
  liabilities + equity side, so Assets = Liabilities + Equity + Profit.
- P&L sums the monthly movements of income (`005`) and expense (`006`) accounts.

**Configuration (`backend/.env`, template `.env.example`):**

| Key | Meaning |
|---|---|
| `DB_SERVER`, `DB_DRIVER` | SQL Server instance, ODBC driver |
| `DB_USER`, `DB_PASSWORD` | Leave empty to use Windows authentication; otherwise use `branchmerge_ro` |
| `DB_HO`, `DB_BR`, `DB_CONSOLIDATED` | Database names |
| `CORS_ORIGINS` | Frontend URL(s) |
| `AMOUNT_DIVISOR` | 100 (cents → rupees) |

**Tests:** `cd backend && .venv\Scripts\python -m pytest`. The tests check that the trial
balance balances for each branch and for all, that the consolidated figure = HO + Mahapitiya,
that P&L profit = balance-sheet profit, and that invalid branches are rejected. Tests that need
the databases are skipped when SQL Server is unavailable.

---

## 6. Frontend

| Page | URL | Features |
|---|---|---|
| Dashboard | `/` | Assets, liabilities, equity, YTD income/expenses/profit for HO, Mahapitiya and consolidated; balance check; DB status |
| Trial Balance | `/trial-balance` | Branch + date; in "All" view shows the HO and Mahapitiya columns; Dr = Cr badge |
| Balance Sheet | `/balance-sheet` | Grouped by heading with account detail; balance badge |
| Profit & Loss | `/profit-loss` | From/to dates; income, expenses, net profit |
| Transactions | `/transactions` | Branch, date range, account number filter; 50 per page |

Each report has **Export Excel** (calls the API) and **Print / PDF** (browser print, A4, navigation hidden).
Filters are plain GET forms, so a report URL can be bookmarked or shared.
API address: `NEXT_PUBLIC_API_URL` in `frontend/.env.local` (default `http://localhost:8000`).

---

## 7. Running locally

```powershell
# 1. Database views
sh database/deploy.sh

# 2. Backend
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
.\.venv\Scripts\uvicorn app.main:app --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
copy .env.local.example .env.local
npm run dev            # or: npm run build; npm start
```

Open http://localhost:3000.

---

## 8. Verification results (31-Oct-2026 backups, LKR)

| Check | HO | Mahapitiya | Consolidated |
|---|---|---|---|
| Trial balance Dr = Cr | 1,632,886,156.07 ✅ | 282,066,868.87 ✅ | 1,914,953,024.94 ✅ |
| Total assets | 1,445,149,006.93 | 263,604,183.37 | 1,708,753,190.30 (= HO + BR ✅) |
| Balance sheet balances | ✅ | ✅ | ✅ |
| Net profit Jan–Oct (P&L = BS) | 7,949,654.75 ✅ | 5,721,260.61 ✅ | 13,670,915.36 ✅ |
| `ClosingBal` Dec = MBWin `CBalAmt` | ✅ all | ✅ all | 1 exception: HO 2022 system account (MBWin data) |

Response times are about 1–2 seconds per page on the local machine.

**Not yet verified:** these figures have not been compared with MBWin's own printed reports.

---

## 9. Open items & known limitations

1. **Confirm cents:** compare one balance with an MBWin report. If it's wrong, change `AMOUNT_DIVISOR`.
2. **Inter-branch account `418`:** decide whether to eliminate it in the consolidated balance sheet.
3. **Month-end only:** reports are at month-end level. Daily balances inside a month would need
   the journals (`T_GLJL` / `T_GlJlHIST`). HO's October figures are month-to-date (backup taken before EOM).
4. **No login yet:** the system must not be exposed on the network until authentication and roles are added.
5. **PDF** uses browser print. There is no server-side PDF.
6. Customer, account and loan views exist, but there are no API endpoints or pages for them yet.
7. **Deployment** (Windows service / IIS) and the user guide are still to do (Phase 5).
