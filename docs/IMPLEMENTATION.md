# Implementation Guide – Branch Merge Reporting

This document covers what has been built, how it works, and how to run it.
- Plan and decisions: [PROJECT_PLAN.md](PROJECT_PLAN.md)
- Database findings: [DB_ANALYSIS.md](DB_ANALYSIS.md)
- Progress and remaining work: [PROGRESS.md](PROGRESS.md)

_Last updated: 08-Nov-2026_

---

## 1. Status summary

| Phase | Status | Output |
|---|---|---|
| 0 – Setup | ✅ Done | Repo, FastAPI backend, Next.js frontend |
| 1 – Database analysis | ✅ Done | `docs/DB_ANALYSIS.md`, `docs/PROGRESS.md` §2.2 |
| 2 – Database scripts | ✅ Done | `database/`: AppUsers login table + optional consolidated views |
| 3 – Backend API | ✅ Done | GL, loan, arrears, deposit and transaction reports with Excel export and inter-branch eliminations; 28 tests passing |
| 4 – Frontend | ✅ Done | Dashboard + 9 report pages, print / Excel |
| 5a – Login & roles | ✅ Done | JWT login, admin/viewer roles, per-branch access, Users page |
| 5 – Verification & deployment | ⏳ Not started | Reconcile with MBWin, server deploy |

---

## 2. Architecture

```
MicroBanker_ho (HO, 001) ─┐
                          ├─► FastAPI backend :8000 ──► Next.js frontend :3000
MicroBanker_br (BR, 002) ─┘   reads each branch DB        server-rendered pages,
                              directly (read-only),       login cookie
                              consolidates in Python
MB_Consolidated ── AppUsers (login users only)
```

- The MBWin databases are **never written to**. The backend reads `[db].dbo.T_*` tables directly
  and consolidates in Python (`app/services/gl.py`, `portfolio.py`).
- Each branch is identified by which database it comes from. Customer IDs and account numbers clash
  between the two databases, so the branch is always shown alongside them.
- **Inter-branch eliminations:** in consolidated figures, the HO ↔ Mahapitiya advance and advance-interest
  accounts cancel out. They're configured in `config.py` → `eliminations`.
- **Money:** MBWin stores amounts as integer cents. `report()` and the dashboard divide by
  `AMOUNT_DIVISOR=100`. (Example check: HO chief cashier cash 53,103,616 → LKR 531,036.16.)

---

## 3. Repository layout

```
branchmerge/
├── database/
│   ├── 01_create_db.sql     MB_Consolidated + BranchMap
│   ├── 02_views_gl.sql      optional GL views (for ad-hoc SQL / other tools)
│   ├── 02_views_ops.sql     optional customer/account/loan/transaction views
│   ├── 03_security.sql      read-only login branchmerge_ro
│   ├── 04_auth.sql          AppUsers table (required for login)
│   └── deploy.sh
├── backend/app/
│   ├── main.py              FastAPI app, CORS, routers
│   ├── manage.py            CLI: create-user, reset-password
│   ├── core/config.py       settings (.env), branches, eliminations
│   ├── core/db.py           engine, query(), cached_query() (120 s cache)
│   ├── core/security.py     password hashing, JWT, current_user, branch access
│   ├── api/                 health, auth, branches, reports
│   └── services/            gl.py, portfolio.py, report.py (common shape), export.py (xlsx), users.py
├── frontend/src/
│   ├── app/                 dashboard, trial-balance, balance-sheet, income-statement, gl-ledger,
│   │                        loans, arrears, deposits, transactions, users, login, export/[name]
│   ├── components/ui.tsx    Filters, ReportTable, ReportPage, ReportHeader
│   ├── lib/api.ts           server-side API calls with token, formatting
│   ├── lib/session.ts       login cookie, current user, branch for user
│   └── middleware.ts        redirects to /login without a session
└── docs/
```

---

## 4. Database scripts

```sh
sh database/deploy.sh                                                       # local names
DB_SERVER=SRV HO_DB=MicroBanker_ho BR_DB=MicroBanker_br sh database/deploy.sh   # production
```

- **Required:** `04_auth.sql` (the `AppUsers` table) and `01_create_db.sql`.
- **Optional:** the views in `02_*.sql` aren't used by the backend. They're there for ad-hoc SQL and other tools.
- `03_security.sql` creates the read-only login. Run it with `-v RO_PASSWORD=...`.
- All scripts can be re-run safely.

---

## 5. Backend API

Base URL `http://localhost:8000/api`, interactive docs at `/docs`.
- `branch` = `all` | `001` | `002`. `all` gives per-branch columns, an Eliminations column and a Consolidated column.
- Add `format=xlsx` to any report to get an Excel file.
- Every report returns the same shape:
  `{title, subtitle, columns:[{key,label,type}], rows:[{…, _style}], notes:[…]}`.

| Endpoint | Parameters |
|---|---|
| `GET /health` (no login) | – |
| `POST /auth/login` (no login) | `{username, password}` |
| `GET /auth/me`, `GET/POST /auth/users`, `PATCH /auth/users/{u}` | admin for user management |
| `GET /branches`, `/periods`, `/gl/accounts`, `/dashboard` | – |
| `GET /reports/trial-balance` | `year`, `month`, `show_zero` |
| `GET /reports/balance-sheet` | `year`, `month`, `detail` |
| `GET /reports/income-statement` | `year`, `from_month`, `to_month`, `detail` |
| `GET /reports/gl-ledger` | `gl_code`, `date_from`, `date_to` (same year) |
| `GET /reports/loan-portfolio`, `/arrears-ageing`, `/deposits` | – |
| `GET /reports/arrears-list` | `min_days` (default 31) |
| `GET /reports/transactions` | `date_from`, `date_to` (max 31 days unless `acc`), `acc` |

Built-in checks appear in a report's notes: TB Dr = Cr, Assets = Liabilities + Equity, and whether the inter-branch pairs agree.

**Configuration (`backend/.env`, template `.env.example`):** `DB_SERVER`, `DB_DRIVER`, `DB_USER`/`DB_PASSWORD`
(leave empty to use Windows authentication), `DB_HO`, `DB_BR`, `DB_CONSOLIDATED`, `CORS_ORIGINS`, `AMOUNT_DIVISOR`,
`JWT_SECRET`, `JWT_EXPIRE_MINUTES`. Optional: `ELIMINATIONS`.

**Tests:** `cd backend; .\.venv\Scripts\python -m pytest -q`. There are 28 integration tests. They need the databases.

---

## 6. Frontend

| Page | URL |
|---|---|
| Dashboard: KPIs per branch + consolidated, monthly income/expense trend | `/` |
| Trial Balance | `/trial-balance` |
| Balance Sheet (summary / with accounts) | `/balance-sheet` |
| Profit & Loss (month range) | `/income-statement` |
| GL Ledger (GL code with suggestions, date range) | `/gl-ledger` |
| Loan Portfolio | `/loans` |
| Arrears ageing (PAR) / loans in arrears | `/arrears` |
| Deposits | `/deposits` |
| Customer transactions | `/transactions` |
| Users (admin only) | `/users` |

- All reports are drawn by one component (`ReportTable`) from the common report shape.
- Filters are GET forms, so URLs can be bookmarked.
- **Export Excel** goes through `/export/<report>`, which adds the login token on the server.
- **Print / PDF** uses the browser's print, set up for A4 with the navigation hidden.

---

## 7. Login & roles

| Role | Can do |
|---|---|
| `admin` | All branches; manage users (`/users`) |
| `viewer` | Reports for the assigned branch (`001`, `002` or `all`) |

- **Users:** stored in `MB_Consolidated.dbo.AppUsers`. This is the only table the backend writes to.
- **Passwords:** PBKDF2-SHA256 (600,000 iterations, salted).
- **Session:** a JWT (HS256, `JWT_SECRET`, 8 h by default) kept in the httpOnly cookie `bm_token`.
- **Branch access:** a branch user asking for `all` gets their own branch. Asking for another branch gives 403.
  Their dashboard and branch selectors show only their branch.
- **Last admin:** can't be disabled or demoted.

```powershell
cd backend
.\.venv\Scripts\python -m app.manage create-user admin --name "Administrator" --role admin --branch all
.\.venv\Scripts\python -m app.manage reset-password admin
```

---

## 8. Running locally

```powershell
sh database/deploy.sh                     # MB_Consolidated + AppUsers

cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env                    # set JWT_SECRET
.\.venv\Scripts\python -m app.manage create-user admin --name "Administrator" --role admin
.\.venv\Scripts\uvicorn app.main:app --port 8000

cd ..\frontend                            # new terminal
npm install
copy .env.local.example .env.local
npm run dev                               # or: npm run build; npm start
```

Open http://localhost:3000 and sign in.

---

## 9. Verification results (31-Oct-2026 backups, LKR)

| Check | HO | Mahapitiya | Consolidated (after eliminations) |
|---|---|---|---|
| Trial balance Dr = Cr | 1,632,886,156.07 ✅ | 282,066,868.87 ✅ | 1,788,880,759.21 ✅ |
| Total assets = Liabilities + Equity | 1,445,149,006.93 ✅ | 263,604,183.37 ✅ | 1,590,593,088.57 ✅ |
| Net profit Jan–Oct (P&L = BS) | 7,949,654.75 ✅ | 5,721,260.61 ✅ | 13,670,915.36 ✅ |
| Loans outstanding | 640,468,782.30 | 130,332,286.84 | 770,801,069.14 |

- Consolidated assets are LKR 118.16M lower than HO + Mahapitiya. That's the eliminated inter-branch advance.
- Consolidated PAR > 30 days: 15.89%.
- The GL ledger for 105010103 reconciles to the trial balance.
- Loan portfolio total = arrears ageing total.

**Not yet verified:** comparison with MBWin's own printed reports.

---

## 10. Open items & known limitations

1. **Confirm cents** against an MBWin printed report (`AMOUNT_DIVISOR`).
2. **Confirm the elimination pairs** and the **arrears-days method** (`T_LNINST`) with accounts staff / MBWin.
3. **Month-end only:** reports are at month-end level. HO's October is pre-EOM, Mahapitiya's is post-EOM.
4. **Transactions report is slow** (≈ 7 s for one day): `T_TRNHIST` has no date index, and we can't add one because we don't write to MBWin.
5. **HTTPS:** put the site behind HTTPS (IIS) before network use and set `COOKIE_SECURE=true`.
   There's no login rate limiting or audit log yet.
6. **Deployment** (Windows service / IIS) and the user guide are still to do.
