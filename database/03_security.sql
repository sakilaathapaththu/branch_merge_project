/*  03_security.sql – read-only login for the backend.
    Pass the password on the command line:  -v RO_PASSWORD="..."
    Never commit a real password.                                           */
USE master;
GO
IF SUSER_ID(N'branchmerge_ro') IS NULL
    CREATE LOGIN branchmerge_ro WITH PASSWORD = N'$(RO_PASSWORD)', CHECK_POLICY = ON;
GO
USE [$(CONS_DB)];
IF USER_ID(N'branchmerge_ro') IS NULL CREATE USER branchmerge_ro FOR LOGIN branchmerge_ro;
ALTER ROLE db_datareader ADD MEMBER branchmerge_ro;
GO
USE [$(HO_DB)];
IF USER_ID(N'branchmerge_ro') IS NULL CREATE USER branchmerge_ro FOR LOGIN branchmerge_ro;
ALTER ROLE db_datareader ADD MEMBER branchmerge_ro;
GO
USE [$(BR_DB)];
IF USER_ID(N'branchmerge_ro') IS NULL CREATE USER branchmerge_ro FOR LOGIN branchmerge_ro;
ALTER ROLE db_datareader ADD MEMBER branchmerge_ro;
GO
