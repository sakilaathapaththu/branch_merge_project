/*  02_views_ops.sql – customers, accounts, loans and transactions.
    Keys clash across branches (4,190 CIDs, 43 Acc numbers), so every
    row is identified by BranchCode + original key.                        */
USE [$(CONS_DB)];
GO
CREATE OR ALTER VIEW dbo.vw_Customers AS
SELECT N'001' AS BranchCode, CID, Nid, DisplayName, Name1, Initials, GenderType, BirthDate, Mobile1, RegisterDate, StatusType
FROM [$(HO_DB)].dbo.T_CIF
UNION ALL
SELECT N'002', CID, Nid, DisplayName, Name1, Initials, GenderType, BirthDate, Mobile1, RegisterDate, StatusType
FROM [$(BR_DB)].dbo.T_CIF;
GO
/* Deposit and loan accounts (savings, time deposits, loans) in one list. */
CREATE OR ALTER VIEW dbo.vw_Accounts AS
SELECT N'001' AS BranchCode, N'SV' AS Module, Acc, PrType, AccName, GLCode, AccStatus, OpenDate, BalAmt FROM [$(HO_DB)].dbo.T_SVACC
UNION ALL SELECT N'001', N'TD', Acc, PrType, AccName, GLCode, AccStatus, OpenDate, BalAmt FROM [$(HO_DB)].dbo.T_TDACC
UNION ALL SELECT N'001', N'LN', Acc, PrType, NULL,    GLCode, AccStatus, OpenDate, BalAmt FROM [$(HO_DB)].dbo.T_LNACC
UNION ALL SELECT N'002', N'SV', Acc, PrType, AccName, GLCode, AccStatus, OpenDate, BalAmt FROM [$(BR_DB)].dbo.T_SVACC
UNION ALL SELECT N'002', N'TD', Acc, PrType, AccName, GLCode, AccStatus, OpenDate, BalAmt FROM [$(BR_DB)].dbo.T_TDACC
UNION ALL SELECT N'002', N'LN', Acc, PrType, NULL,    GLCode, AccStatus, OpenDate, BalAmt FROM [$(BR_DB)].dbo.T_LNACC;
GO
CREATE OR ALTER VIEW dbo.vw_Loans AS
SELECT N'001' AS BranchCode, Acc, PrType, GLCode, AccStatus, OpenDate, MatDate, GrantedAmt, PrincipalAmt, BalAmt, IntRate, OduePriAmt, OdueIntAmt, LateDaysNo, Provision
FROM [$(HO_DB)].dbo.T_LNACC
UNION ALL
SELECT N'002', Acc, PrType, GLCode, AccStatus, OpenDate, MatDate, GrantedAmt, PrincipalAmt, BalAmt, IntRate, OduePriAmt, OdueIntAmt, LateDaysNo, Provision
FROM [$(BR_DB)].dbo.T_LNACC;
GO
/* Posted customer/GL transactions (history). */
CREATE OR ALTER VIEW dbo.vw_Transactions AS
SELECT N'001' AS BranchCode, Recid, TrnDate, ValueDate, Acc, AppType, TrnType, TrnDesc, TrnAmt, BalAmt, CID, GLCode, Tlr, CancelledByTrn
FROM [$(HO_DB)].dbo.T_TRNHIST
UNION ALL
SELECT N'002', Recid, TrnDate, ValueDate, Acc, AppType, TrnType, TrnDesc, TrnAmt, BalAmt, CID, GLCode, Tlr, CancelledByTrn
FROM [$(BR_DB)].dbo.T_TRNHIST;
GO
