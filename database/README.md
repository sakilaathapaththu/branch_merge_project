# MB_Consolidated database

Read-only views over both MBWin branch databases. Nothing here writes to MBWin.

```sh
# local (defaults: SAKILA\SQLEXPRESS, the 20261031 restore names)
sh database/deploy.sh

# production names
DB_SERVER=MYSERVER HO_DB=MicroBanker_ho BR_DB=MicroBanker_br sh database/deploy.sh

# optional read-only login for the backend
sqlcmd -S <server> -E -i database/03_security.sql \
  -v CONS_DB=MB_Consolidated HO_DB=... BR_DB=... RO_PASSWORD="<strong password>"
```

All scripts can be re-run safely (`CREATE OR ALTER`). Both source DBs must be on the same SQL
instance as MB_Consolidated. If they're not, use a linked server.
