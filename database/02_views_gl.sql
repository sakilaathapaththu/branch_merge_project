/*  02_views_gl.sql – general-ledger views across both branches.
    Amounts are stored by MBWin as integers in cents (numeric(18,0)).
    Sign: debit balance positive, credit balance negative.
    CaluieType: 001 Equity, 002 Asset, 003 Liability, 004 System,
                005 Income, 006 Expense.                                  */
USE [$(CONS_DB)];
GO
CREATE OR ALTER VIEW dbo.vw_Branches AS
SELECT BranchCode, BranchName, SourceDb FROM dbo.BranchMap;
GO
/* Sort-code (heading) hierarchy. Identical in both branches today, kept per branch. */
CREATE OR ALTER VIEW dbo.vw_GLSortCodes AS
SELECT N'001' AS BranchCode, SortCode, LevelNumber, FullDesc, CaluieType AS AccType
FROM [$(HO_DB)].dbo.T_GLSC
UNION ALL
SELECT N'002', SortCode, LevelNumber, FullDesc, CaluieType
FROM [$(BR_DB)].dbo.T_GLSC;
GO
/* GL account master, one row per branch + financial year (current + closed years). */
CREATE OR ALTER VIEW dbo.vw_GLAccounts AS
WITH src AS (
    SELECT N'001' AS BranchCode, 0 AS Closed, g.FinYear, g.GlAcc, g.ExpGlAcc, g.FullTitle, g.SortAcc, g.LevelNumber, g.CaluieType, g.OBalAmt, g.DebitsAmt, g.CreditsAmt, g.CBalAmt, g.LastTrnDate,
           g.DebitsAmt1,g.CreditsAmt1,g.DebitsAmt2,g.CreditsAmt2,g.DebitsAmt3,g.CreditsAmt3,g.DebitsAmt4,g.CreditsAmt4,g.DebitsAmt5,g.CreditsAmt5,g.DebitsAmt6,g.CreditsAmt6,
           g.DebitsAmt7,g.CreditsAmt7,g.DebitsAmt8,g.CreditsAmt8,g.DebitsAmt9,g.CreditsAmt9,g.DebitsAmt10,g.CreditsAmt10,g.DebitsAmt11,g.CreditsAmt11,g.DebitsAmt12,g.CreditsAmt12
    FROM [$(HO_DB)].dbo.T_GLAC g
    UNION ALL
    SELECT N'001', 1, h.FinYear, h.GlAcc, h.ExpGlAcc, h.FullTitle, h.SortAcc, h.LevelNumber, h.CaluieType, h.OBalAmt, h.DebitsAmt, h.CreditsAmt, h.CBalAmt, h.LastTrnDate,
           h.DebitsAmt1,h.CreditsAmt1,h.DebitsAmt2,h.CreditsAmt2,h.DebitsAmt3,h.CreditsAmt3,h.DebitsAmt4,h.CreditsAmt4,h.DebitsAmt5,h.CreditsAmt5,h.DebitsAmt6,h.CreditsAmt6,
           h.DebitsAmt7,h.CreditsAmt7,h.DebitsAmt8,h.CreditsAmt8,h.DebitsAmt9,h.CreditsAmt9,h.DebitsAmt10,h.CreditsAmt10,h.DebitsAmt11,h.CreditsAmt11,h.DebitsAmt12,h.CreditsAmt12
    FROM [$(HO_DB)].dbo.T_GLACHIST h
    WHERE h.FinYear NOT IN (SELECT FinYear FROM [$(HO_DB)].dbo.T_GLAC)
    UNION ALL
    SELECT N'002', 0, g.FinYear, g.GlAcc, g.ExpGlAcc, g.FullTitle, g.SortAcc, g.LevelNumber, g.CaluieType, g.OBalAmt, g.DebitsAmt, g.CreditsAmt, g.CBalAmt, g.LastTrnDate,
           g.DebitsAmt1,g.CreditsAmt1,g.DebitsAmt2,g.CreditsAmt2,g.DebitsAmt3,g.CreditsAmt3,g.DebitsAmt4,g.CreditsAmt4,g.DebitsAmt5,g.CreditsAmt5,g.DebitsAmt6,g.CreditsAmt6,
           g.DebitsAmt7,g.CreditsAmt7,g.DebitsAmt8,g.CreditsAmt8,g.DebitsAmt9,g.CreditsAmt9,g.DebitsAmt10,g.CreditsAmt10,g.DebitsAmt11,g.CreditsAmt11,g.DebitsAmt12,g.CreditsAmt12
    FROM [$(BR_DB)].dbo.T_GLAC g
    UNION ALL
    SELECT N'002', 1, h.FinYear, h.GlAcc, h.ExpGlAcc, h.FullTitle, h.SortAcc, h.LevelNumber, h.CaluieType, h.OBalAmt, h.DebitsAmt, h.CreditsAmt, h.CBalAmt, h.LastTrnDate,
           h.DebitsAmt1,h.CreditsAmt1,h.DebitsAmt2,h.CreditsAmt2,h.DebitsAmt3,h.CreditsAmt3,h.DebitsAmt4,h.CreditsAmt4,h.DebitsAmt5,h.CreditsAmt5,h.DebitsAmt6,h.CreditsAmt6,
           h.DebitsAmt7,h.CreditsAmt7,h.DebitsAmt8,h.CreditsAmt8,h.DebitsAmt9,h.CreditsAmt9,h.DebitsAmt10,h.CreditsAmt10,h.DebitsAmt11,h.CreditsAmt11,h.DebitsAmt12,h.CreditsAmt12
    FROM [$(BR_DB)].dbo.T_GLACHIST h
    WHERE h.FinYear NOT IN (SELECT FinYear FROM [$(BR_DB)].dbo.T_GLAC)
)
SELECT * FROM src;
GO
/* Month-end GL balances: one row per branch, year, month (1-12), account.
   ClosingBal = OBalAmt + cumulative debits - cumulative credits up to that month.
   For the open (current) month the figures are month-to-date.            */
CREATE OR ALTER VIEW dbo.vw_GLBalances AS
WITH m AS (
    SELECT a.BranchCode, a.Closed, a.FinYear, a.GlAcc, a.ExpGlAcc, a.FullTitle, a.SortAcc, a.LevelNumber,
           a.CaluieType AS AccType, a.OBalAmt, v.MonthNo, v.Dr, v.Cr
    FROM dbo.vw_GLAccounts a
    CROSS APPLY (VALUES
        (1,a.DebitsAmt1,a.CreditsAmt1),(2,a.DebitsAmt2,a.CreditsAmt2),(3,a.DebitsAmt3,a.CreditsAmt3),
        (4,a.DebitsAmt4,a.CreditsAmt4),(5,a.DebitsAmt5,a.CreditsAmt5),(6,a.DebitsAmt6,a.CreditsAmt6),
        (7,a.DebitsAmt7,a.CreditsAmt7),(8,a.DebitsAmt8,a.CreditsAmt8),(9,a.DebitsAmt9,a.CreditsAmt9),
        (10,a.DebitsAmt10,a.CreditsAmt10),(11,a.DebitsAmt11,a.CreditsAmt11),(12,a.DebitsAmt12,a.CreditsAmt12)
    ) v(MonthNo, Dr, Cr)
)
SELECT BranchCode, Closed, FinYear, MonthNo, GlAcc, ExpGlAcc, FullTitle, SortAcc, LevelNumber, AccType,
       OBalAmt,
       Dr AS MonthDr,
       Cr AS MonthCr,
       SUM(Dr) OVER (PARTITION BY BranchCode, FinYear, GlAcc ORDER BY MonthNo ROWS UNBOUNDED PRECEDING) AS YtdDr,
       SUM(Cr) OVER (PARTITION BY BranchCode, FinYear, GlAcc ORDER BY MonthNo ROWS UNBOUNDED PRECEDING) AS YtdCr,
       OBalAmt + SUM(Dr - Cr) OVER (PARTITION BY BranchCode, FinYear, GlAcc ORDER BY MonthNo ROWS UNBOUNDED PRECEDING) AS ClosingBal
FROM m;
GO
