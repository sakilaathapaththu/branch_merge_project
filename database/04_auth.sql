/*  04_auth.sql – application users (stored in MB_Consolidated, never in MBWin).
    Safe to re-run.                                                         */
USE [$(CONS_DB)];
GO
IF OBJECT_ID(N'dbo.AppUsers') IS NULL
    CREATE TABLE dbo.AppUsers (
        Username     nvarchar(50)  NOT NULL PRIMARY KEY,
        FullName     nvarchar(100) NOT NULL,
        PasswordHash nvarchar(255) NOT NULL,
        Role         nvarchar(10)  NOT NULL CONSTRAINT CK_AppUsers_Role   CHECK (Role IN (N'admin', N'viewer')),
        Branch       nvarchar(3)   NOT NULL CONSTRAINT CK_AppUsers_Branch CHECK (Branch IN (N'all', N'001', N'002')),
        Active       bit           NOT NULL DEFAULT 1,
        CreatedAt    datetime2(0)  NOT NULL DEFAULT SYSDATETIME(),
        LastLoginAt  datetime2(0)  NULL
    );
GO
/* The backend login may only change this one table. */
IF USER_ID(N'branchmerge_ro') IS NOT NULL
    GRANT SELECT, INSERT, UPDATE ON dbo.AppUsers TO branchmerge_ro;
GO
