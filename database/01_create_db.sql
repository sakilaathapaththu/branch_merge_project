/*  01_create_db.sql – create the consolidated reporting database.
    Run with sqlcmd (see database/README.md). Safe to re-run.          */
IF DB_ID(N'$(CONS_DB)') IS NULL
    CREATE DATABASE [$(CONS_DB)];
GO
USE [$(CONS_DB)];
GO
IF OBJECT_ID(N'dbo.BranchMap') IS NULL
    CREATE TABLE dbo.BranchMap (
        BranchCode   char(3)       NOT NULL PRIMARY KEY,
        BranchName   nvarchar(100) NOT NULL,
        SourceDb     sysname       NOT NULL
    );
GO
MERGE dbo.BranchMap AS t
USING (VALUES (N'001', N'Head Office',       N'$(HO_DB)'),
              (N'002', N'Mahapitiya Branch', N'$(BR_DB)')) AS s(BranchCode, BranchName, SourceDb)
ON t.BranchCode = s.BranchCode
WHEN MATCHED THEN UPDATE SET BranchName = s.BranchName, SourceDb = s.SourceDb
WHEN NOT MATCHED THEN INSERT VALUES (s.BranchCode, s.BranchName, s.SourceDb);
GO
