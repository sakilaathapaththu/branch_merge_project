# Progress Report – Branch Merge Project

_Last updated: 2026-11-08_

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the overall plan and architecture.

---

## 1. Summary

| Area | Status |
|---|---|
| Backups restored to local SQL Server | ✅ Done |
| Database analysis (GL, loans, deposits, inter-branch) | ✅ Done |
| Project setup (repo, FastAPI, Next.js) | ✅ Done |
| Backend report services + API | ✅ Done – 28 tests passing |
| Excel export | ✅ Done (tested) |
| Frontend report pages | ✅ Done – dashboard + 9 reports |
| Login & roles | ✅ Done – admin / viewer, per-branch access |
| Reconciliation against MBWin reports | ❌ Not started |
| Deployment | ❌ Not started |

> Two parallel work streams were merged on 2026-11-08: this report backend, and a second session's
> database scripts, login and frontend pages. See [IMPLEMENTATION.md](IMPLEMENTATION.md) for how the merged system works.

---

## 2. Completed Work

### 2.1 Local databases
Restored on `SAKILA\SQLEXPRESS` under **new names**. The existing `MicroBanker_br` / `MicroBanker_ho` databases were not touched.

| Database | Source backup | Branch |
|---|---|---|
| `MicroBanker_ho_BeforeEOM_20261031` | `MicroBanker_ho_BackupBeforeEOMOn_Sat_31_Oct_2026.bak` | 001 Head Office |
| `MicroBanker_br_EOM_20261031` | `MBBackUp_00002_LKR_EOM2026_10.bak` | 002 Mahapitiya |

Both were upgraded from SQL Server 2008 R2 format (v661) to v904 during the restore. They run at compatibility level 100.

### 2.2 Database findings

**Why we do not physically merge the databases**
- Both databases use the same internal branch code `BR = 00002`, and `T_CLBRANCH` is empty in both.
- IDs clash between the databases: 4,190 customer IDs (`CID`) and 43 account numbers (`Acc`) exist in both.

**General ledger**
- `T_GLAC` holds the current year (2026). For each GL it stores the opening balance `OBalAmt` plus `DebitsAmt1..12` / `CreditsAmt1..12` per month.
- Verified for every GL in both databases:
  - `CBalAmt = OBalAmt + DebitsAmt − CreditsAmt`
  - The monthly columns add up to the yearly totals.
  - So the balance at the end of any month can be calculated.
- `T_GLACHIST` holds previous years with the same structure: HO from 2007, Mahapitiya from 2012.
- `T_GLSC` holds the report headings (e.g. `315` LOANS AND ADVANCES). A GL belongs to the heading given by the first 3 digits of its `SortAcc`.
- `CaluieType` codes:

  | Code | Type |
  |---|---|
  | 001 | Equity |
  | 002 | Assets |
  | 003 | Liabilities |
  | 004 | Suspense |
  | 005 | Income |
  | 006 | Expenses |

- Sign convention: debit balances are positive, credit balances negative. Each branch trial balance sums to 0.
- Chart of accounts: HO has 802 GLs, Mahapitiya 715, and 706 are common.
  - The codes mean the same thing in both branches.
  - 205 of the common GLs have spelling differences in the title. Reports use the HO title.
- Journal: `T_GlJlHIST` (history) + `T_GLJL` (current day) reconcile exactly to `T_GLAC`. Checked on GL 105010103: 1,453,314,369 + 23,938,190 = 1,477,252,559.
  - `T_GLTRNHIST` was **not** used, because its debit/credit direction is not reliable from its columns.

**Inter-branch accounts (eliminated on consolidation)**

| HO (001) | Mahapitiya (002) | Amount |
|---|---|---|
| 418010101 Branch Advances – Mahapitiya | 315400101 Branch Advances – Ahugoda | ±LKR 118,160,101.73 |
| 201040102 Branch Advance interest (expense) | 120010117 Branch Advance Interest Income | ±LKR 7,912,164.00 |

Both pairs net to zero exactly. They are configured in `backend/app/core/config.py` → `eliminations`.

**Loans / deposits**
- `T_LNACC` (loans), `T_SVACC` (savings), `T_TDACC` (fixed deposits). `AccStatus '99'` = closed.
- Product names come from `T_PRPARMS` (`AppType + PrType`). Customers come from `T_RELACC` → `T_CIF`.
- **`LateDaysNo` in `T_LNACC` is always 0.** MBWin does not maintain it. Arrears days are instead derived from `T_LNINST`, using the oldest instalment due on or before the system date with `Status <> '9'` (paid). **Must be reconciled with MBWin's arrears report.**
- `OduePriAmt`: positive = overdue principal, negative = paid in advance.
- System date per branch = `MAX(CurrRunDate)` in `T_GLJL` (31-Oct-2026 in both backups).

### 2.3 Project setup
- Repo cloned to `D:\Development\Blackcode\Sanasa_Project\branchmerge` and pushed to GitHub.
- Backend: Python 3.12 venv in `backend/.venv`, FastAPI, SQLAlchemy + pyodbc (ODBC Driver 17), Windows auth. MBWin is only read. The only write is the `AppUsers` login table in `MB_Consolidated`.
- Frontend: Next.js 15.5.4 (App Router, TypeScript, Tailwind).
  - Tailwind is pinned to **4.1.13**, because 4.3.x needs Node ≥ 20.19 and this machine has Node 20.18.2.
- The status page (`frontend/src/app/page.tsx`) shows API health and both branch DBs as ONLINE (verified in the browser).

### 2.4 Backend code

| File | Purpose |
|---|---|
| `app/core/config.py` | Settings from `.env`: branch → database map, elimination pairs. DB names are validated because they are used as SQL identifiers. |
| `app/core/db.py` | Engine, `query()`, `cached_query()` (120 s TTL cache) |
| `app/services/report.py` | Common report shape `{title, subtitle, columns, rows, notes}` and branch helpers |
| `app/services/gl.py` | Trial balance, balance sheet, income statement, GL ledger, dashboard GL KPIs, monthly trend |
| `app/services/portfolio.py` | Loan portfolio, arrears ageing (PAR), arrears list, deposits, transactions, dashboard portfolio KPIs |
| `app/services/export.py` | Excel (.xlsx) export of any report (openpyxl) |
| `app/api/reports.py` | Report endpoints |
| `tests/test_api.py` | Integration tests (≈20) |

**API endpoints** (all `GET`, read-only; `branch` = `all` | `001` | `002`; add `format=xlsx` for Excel):

| Endpoint | Parameters |
|---|---|
| `/api/health`, `/api/branches`, `/api/periods`, `/api/gl/accounts` | – |
| `/api/dashboard` | – |
| `/api/reports/trial-balance` | `year`, `month`, `show_zero` |
| `/api/reports/balance-sheet` | `year`, `month`, `detail` |
| `/api/reports/income-statement` | `year`, `from_month`, `to_month`, `detail` |
| `/api/reports/gl-ledger` | `gl_code`, `date_from`, `date_to` (same year) |
| `/api/reports/loan-portfolio` | – |
| `/api/reports/arrears-ageing` | – |
| `/api/reports/arrears-list` | `min_days` (default 31) |
| `/api/reports/deposits` | – |
| `/api/reports/transactions` | `date_from`, `date_to` (max 31 days unless `acc`), `acc` |

The consolidated reports show HO, Mahapitiya, an Eliminations column and a Consolidated column. Built-in checks add a note to the report: TB Dr = Cr, Assets = Liabilities + Equity, and inter-branch pairs agree.

---

## 3. Known Issues

1. **Drive D: incident (2026-11-08, 21:24).**
   - What happened: the NVMe controller on the "OSC PCIe 1TB" SSD reset (`stornvme` events 11/129). Disk/NTFS errors followed until about 21:43 (events 51, 50, 140).
   - Current state: Windows reports the disk as Healthy, and a later write/read test passed.
   - Leftovers: `backend/app/core/config.py.bad` and `db.py.bad` are old, locked copies. Delete them after a restart.
   - A clean copy of the backend is kept in the Claude scratchpad (`...\scratchpad\stage\backend`).
   - Still to do: run `chkdsk D: /scan` as Administrator and check SMART (CrystalDiskInfo). If the controller errors return, update the SSD firmware or disable PCIe Link State Power Management.
2. ~~`openpyxl` not installed~~: fixed, requirements reinstalled.
3. The HO backup was taken **before EOM** and the Mahapitiya backup **after EOM**, so October figures are not at the same stage. Use a matching pair of backups for reconciliation.

---

## 4. Remaining Work

### Step 1 – Get the backend green
- [ ] Restart the PC, then delete `app/core/*.py.bad` (ignored by git)
- [x] `cd backend; .\.venv\Scripts\pip install -r requirements.txt`
- [x] `.\.venv\Scripts\python -m pytest -q`: 28 passed
- [x] Check query speed: `gl-ledger` and `arrears` take 1–2 s. `transactions` takes ≈ 7 s per day, because `T_TRNHIST` has no date index.
- [x] Commit and push to GitHub (`sakilaathapaththu/branch_merge_project`)

### Step 2 – Frontend (Next.js)
- [x] Layout: top navigation, header, light theme suitable for printing
- [x] Shared components: branch selector (All / HO / Mahapitiya), period pickers, generic `ReportTable` (formats money/number/percent, styles heading/subtotal/total rows, shows notes), "Export Excel" and "Print" buttons
- [x] Pages:
  - [x] Dashboard: KPI cards per branch + consolidated, monthly income/expense trend
  - [x] Trial Balance
  - [x] Balance Sheet (summary / detail)
  - [x] Income Statement (month range, summary / detail)
  - [x] GL Ledger (GL search + date range)
  - [x] Loan Portfolio
  - [x] Arrears Ageing and Arrears List
  - [x] Deposits
  - [x] Transactions (date range / account)
- [x] Print CSS (A4, report header with branch and period)
- [x] Login page, Users admin page

### Step 3 – Reconciliation with MBWin (required before go-live)
- [ ] For 31-Oct-2026, export from MBWin for each branch: Trial Balance, Balance Sheet, P&L, Loan portfolio / arrears, Deposit summary
- [ ] Compare each with this system. Document any differences in `docs/RECONCILIATION.md`
- [ ] Confirm the arrears-days method, the meaning of `T_LNINST.Status` codes (0/1/8/9) and the loan `AccStatus` codes (11/12/13/14/50/90) with MBWin / the vendor
- [ ] Confirm the inter-branch elimination pairs with accounts staff

### Step 4 – Production readiness
- [ ] Find out whether both live databases are on the same SQL Server instance (needed for this design). If not, use a linked server or a nightly copy.
- [ ] Create the read-only SQL login (script ready: `database/03_security.sql`) and set it in `.env`
- [x] Add user login and roles (e.g. HO management sees everything; a branch user sees only their own branch)
- [ ] Add an audit log of who ran or exported which report
- [ ] Deploy: FastAPI as a Windows service, Next.js build behind IIS / reverse proxy, HTTPS on the internal network
- [ ] Write an install guide and a user guide (Sinhala / English)

### Step 5 – Later improvements
- [ ] Comparative columns (previous year / previous month)
- [ ] Cash flow statement
- [ ] Customer search and account statement
- [ ] PDF export
- [ ] Easy configuration to add more branches
