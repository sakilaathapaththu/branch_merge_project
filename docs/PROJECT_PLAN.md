# Branch Merge Project – Consolidated Reporting for MicroBanker (MBWin)

## 1. Background

Sanasa runs **MicroBanker (MBWin – FAO-GTZ MicroBanking System, SDBL/SAMIT)** with one
SQL Server database per branch:

| Branch | Database | New code (this project) |
|---|---|---|
| Head Office (Main) | `MicroBanker_ho` | **001** |
| Mahapitiya Branch | `MicroBanker_br` | **002** |

Because each branch has its own database, transactions, trial balance, balance sheet and
other final reports must be taken separately. Management needs **one consolidated view**.

## 2. Decision

**We do NOT merge the MBWin databases.** Both stay exactly as they are and MBWin keeps running
on them. We build a **read-only consolidated reporting layer** on top.

Reasons (findings from the 31-Oct-2026 backups):

- Both databases use the same branch code internally: `BR = 00002` and `T_CLBRANCH` is empty.
- IDs clash between the databases: **4,190 customer IDs (CID)** and **43 account numbers (Acc)** exist in both.
- A physical merge would mix customer data and could break EOM, interest and loan processing. It would
  also affect the audit trail and vendor support.

## 3. Architecture

```
MBWin (HO)          ──> MicroBanker_ho ──┐
                                          ├─> MB_Consolidated (SQL views, branch tagged 001/002)
MBWin (Mahapitiya)  ──> MicroBanker_br ──┘              │
                                                         ▼
                                              Backend: FastAPI (read-only)
                                                         │  REST / JSON
                                                         ▼
                                              Frontend: Next.js (reports UI)
```

- **Source DBs**: read-only access only (a dedicated SQL login with `db_datareader`).
- **MB_Consolidated DB**: holds only views, mapping tables and (optionally) cached snapshots, no copies of MBWin logic.
  Every view adds `BranchCode` (`001` / `002`). The unique key becomes `BranchCode + original ID`.
- **Backend**: FastAPI + SQLAlchemy/pyodbc (ODBC Driver 17/18 for SQL Server).
- **Frontend**: Next.js (App Router, TypeScript, Tailwind) with tables, filters and Excel/PDF export.

## 4. Repository Layout

```
branchmerge/
├── docs/                 # plans, DB analysis, report definitions
│   └── PROJECT_PLAN.md
├── database/             # SQL scripts for MB_Consolidated (views, mappings)
│   ├── 01_create_db.sql
│   ├── 02_views_*.sql
│   └── 03_security.sql
├── backend/              # FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── core/         # config (.env), DB connection
│   │   ├── api/          # routers: branches, gl, reports, transactions
│   │   ├── schemas/      # Pydantic models
│   │   └── services/     # report queries / calculations
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/             # Next.js
│   └── src/app/          # dashboard, trial-balance, balance-sheet, pnl, transactions
└── README.md
```

## 5. Phases

### Phase 0 – Setup *(done)*
- [x] Restore backups locally (`MicroBanker_ho_BeforeEOM_20261031`, `MicroBanker_br_EOM_20261031`)
- [x] Clone repo, write this plan
- [x] Scaffold backend (FastAPI) and frontend (Next.js), with a health check end to end

### Phase 1 – Database analysis
- [x] Document key tables: GL master, `T_GLJL` / `T_GlJlHIST` / `T_GLTRNHIST`, `T_TRNHIST`, customer & account masters, loan tables (`T_LNINST`)
- [x] Compare the chart of accounts (GL codes) between HO and Mahapitiya and build a GL mapping table where they differ → not needed: same codes/classes, only titles differ
- [x] Identify how MBWin calculates GL balances (opening balance + movements, EOM snapshots)
- [x] Output: `docs/DB_ANALYSIS.md`

### Phase 2 – Consolidated database
- [x] Create `MB_Consolidated` with views using `UNION ALL` across both DBs, tagged by `BranchCode`
- [x] Views: `vw_Branches`, `vw_GLAccounts`, `vw_GLBalances`, `vw_Transactions`, `vw_Customers`, `vw_Accounts`, `vw_Loans`
- [x] Read-only SQL login for the backend
- [x] Database names are configurable (local restore names ≠ production names)

### Phase 3 – Backend API (FastAPI) *(done – xlsx export; PDF via browser print)*
- `GET /api/health`
- `GET /api/branches`
- `GET /api/gl/accounts`
- `GET /api/reports/trial-balance?date=&branch=001|002|all`
- `GET /api/reports/balance-sheet?date=&branch=`
- `GET /api/reports/profit-loss?from=&to=&branch=`
- `GET /api/transactions?branch=&from=&to=&acc=&page=`
- `GET /api/reports/{name}/export?format=xlsx|pdf`
- Validation: consolidated total = HO + Mahapitiya, and the trial balance must balance (Dr = Cr)

### Phase 4 – Frontend (Next.js) *(done – first version)*
- Dashboard: key totals per branch and consolidated
- Trial balance, balance sheet, P&L pages with a branch selector (HO / Mahapitiya / All) and date picker
- Transaction search
- Export to Excel / PDF, print layouts

### Phase 5 – Verification & deployment
- [ ] Reconcile every report against MBWin's own reports for both branches (31-Oct-2026 EOM)
- [x] Authentication (login, roles) before any network exposure
- [ ] Deploy on the server that hosts both DBs (Windows service / IIS reverse proxy)
- [ ] Docs: install guide, user guide

## 6. Rules

1. **Never write to the MBWin databases.** Read-only access only.
2. All branch data is identified by `BranchCode + ID`, never by ID alone.
3. Every report figure must reconcile with MBWin's native reports before go-live.
4. Secrets (DB passwords) go in `.env`, never in git.

## 7. Open Questions

- Does the production server host both DBs on the same SQL instance? (Cross-database views need this. If not, use a linked server or ETL.)
- ~~Are the GL charts identical across branches?~~ Yes, apart from titles (see DB_ANALYSIS.md)
- Is money stored in cents? (Assumed, `AMOUNT_DIVISOR=100`; confirm against an MBWin report)
- Should inter-branch account `418` be eliminated in the consolidated balance sheet?
- Which reports does management need first? (Suggested: trial balance → balance sheet → P&L)
- Who will use the system, and does it need login roles per branch?
