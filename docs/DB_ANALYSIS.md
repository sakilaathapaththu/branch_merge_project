# MBWin Database Analysis

Source: local restores `MicroBanker_ho_BeforeEOM_20261031` (HO, 001) and
`MicroBanker_br_EOM_20261031` (Mahapitiya, 002), analysed 08-Nov-2026.

## 1. Branch parameters (`T_BRPARMS`)

| | HO | Mahapitiya |
|---|---|---|
| BrName / Br | Ahugoda Sanasa / `00002` | Ahugoda Sanasa / `00002` |
| CurrRunDate | 2026-10-31 | 2026-10-31 |
| LastMlyDate | 2026-09-30 (October **not** closed, "BeforeEOM") | 2026-10-31 (October EOM done) |
| FinYear | 2026 (calendar year) | 2026 |
| Currency | LKR | LKR |

Both databases carry the same internal branch name and code, so the branch is identified
only by **which database** a row comes from (see `BranchMap` in MB_Consolidated).

## 2. Money

All amount columns are `numeric(18,0)`, which looks like **integer cents**.
Example: HO chief cashier cash `53103616` = LKR 531,036.16. The backend divides by
`AMOUNT_DIVISOR=100`. **Confirm this against an MBWin printed report before go-live.**

Sign convention: debit balance is positive, credit balance is negative.

## 3. General ledger

| Table | Content | Rows (HO / BR) |
|---|---|---|
| `T_GLSC` | Sort-code headings (levels 1–2, e.g. `3` ASSETS, `315` LOANS AND ADVANCES) | identical in both DBs |
| `T_GLAC` | GL accounts for the **current** financial year | 802 / 715 |
| `T_GLACHIST` | Same layout, one copy per **closed** year | HO 2007–2025, BR 2012–2025 |
| `T_GLJL` / `T_GLJH` | Journal lines / headers (current) | 86k / 36k lines |
| `T_GlJlHIST`, `T_GLJHHIST` | Journal history | 1.41M / 0.44M lines |
| `T_GLTRNHIST` | GL transaction history | 861k (HO) |
| `T_SixColTBMonthly` | MBWin's own 6-column TB snapshot (last month-end only) | |

### How MBWin holds GL balances (`T_GLAC`)

- `OBalAmt` = opening balance for the year (`DebitsOBAmt − CreditsOBAmt`). It is 0 for income and expense accounts.
- `DebitsAmtN` / `CreditsAmtN`, N = 1..12, are the movements per calendar month.
- `CBalAmt = OBalAmt + DebitsAmt − CreditsAmt`, where `DebitsAmt` is the sum of the 12 months.
  This holds for every row in the current year in both databases.
- So the **balance at the end of month M** = `OBalAmt + Σ(Dr1..M) − Σ(Cr1..M)`. The view
  `vw_GLBalances` does this calculation. For the open month the figure is month-to-date.
- `SUM(CBalAmt)` over all accounts = 0 in both databases (the books balance).

`CaluieType` (account class): `001` Equity, `002` Asset, `003` Liability, `004` System /
transit, `005` Income, `006` Expense. `SortAcc` points to `T_GLSC`. The first 3 digits
give the level-2 heading used for grouping in the balance sheet and P&L.

### Chart-of-accounts comparison

- 706 GL accounts exist in both branches. 96 exist only in HO and 9 only in Mahapitiya.
- For the shared accounts, **sort code and account class are identical**. Only `FullTitle` differs (205 accounts, wording only).
  → **No GL mapping table is needed.** Consolidation adds balances by `GlAcc`. The HO title is shown.
- `T_GLSC` headings are identical.

### Data-quality notes

- HO 2022 `901010101 System Transitoria Account`: the stored `CBalAmt` = 0, but the monthly
  movements net to −388,887.26. This is a closed year and a system account, so it doesn't affect
  current reports.
- `418` INTER BRANCH ACCOUNT exists in both charts. If the branches post to each other through
  it, these balances should be **eliminated** in the consolidated balance sheet. This isn't
  implemented yet (open question for the accountant).

## 4. Customers, accounts, transactions

| Table | Content | Key |
|---|---|---|
| `T_CIF` | Customers | `CID` (4,190 clash across DBs) |
| `T_SVACC`, `T_TDACC`, `T_LNACC` | Savings, time deposits, loans | `Acc` (43 clash) |
| `T_LNINST`, `T_LNHIST` | Loan instalment schedule / history | `Acc` |
| `T_TRNHIST` | Posted customer + GL transactions | `Recid` (HO 1.63M, BR 0.50M) |
| `T_TRNP` | Pending (unapproved) transactions | |

All consolidated views therefore expose `BranchCode` and the API builds IDs as `BranchCode-Recid`.

## 5. Consolidated views (MB_Consolidated)

`vw_Branches`, `vw_GLSortCodes`, `vw_GLAccounts`, `vw_GLBalances`, `vw_Customers`,
`vw_Accounts`, `vw_Loans`, `vw_Transactions`. See `database/`.

## 6. Verified figures (as of 31-Oct-2026, LKR)

| | HO | Mahapitiya | Consolidated |
|---|---|---|---|
| Trial balance Dr = Cr | 1,632,886,156.07 | 282,066,868.87 | 1,914,953,024.94 |
| Total assets | 1,445,149,006.93 | 263,604,183.37 | 1,708,753,190.30 |
| Net profit Jan–Oct | 7,949,654.75 | 5,721,260.61 | 13,670,915.36 |

The balance sheet balances for all three. P&L net profit equals current-year profit in the balance sheet.
These figures still need to be **reconciled with MBWin's own reports** (Phase 5).
