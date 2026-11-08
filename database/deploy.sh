#!/usr/bin/env sh
# Create/refresh MB_Consolidated. Override names for production, e.g.
#   HO_DB=MicroBanker_ho BR_DB=MicroBanker_br ./database/deploy.sh
set -e
cd "$(dirname "$0")"
SERVER="${DB_SERVER:-SAKILA\\SQLEXPRESS}"
HO_DB="${HO_DB:-MicroBanker_ho_BeforeEOM_20261031}"
BR_DB="${BR_DB:-MicroBanker_br_EOM_20261031}"
CONS_DB="${CONS_DB:-MB_Consolidated}"
for f in 01_create_db.sql 02_views_gl.sql 02_views_ops.sql 04_auth.sql; do
  echo "-> $f"
  sqlcmd -S "$SERVER" -E -b -v HO_DB="$HO_DB" BR_DB="$BR_DB" CONS_DB="$CONS_DB" -i "$f"
done
echo "Done. Run 03_security.sql separately with -v RO_PASSWORD=..."
