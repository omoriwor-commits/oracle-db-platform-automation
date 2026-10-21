#!/usr/bin/env bash
# Local-node RMAN launcher. Cleanup is opt-in and starts only after backup success.
# Usage: RMAN_SID=RAC1 rman_backup.sh 0|1|arch [--cleanup]
# Exit: 0 success, 1 RMAN/SQL failure, 2 preflight/identity error, 3 usage,
# 4 overlap on this host. Live backup/restore validation remains pending.
set -u
set -o pipefail
umask 077
LEVEL="${1:-}"
CLEANUP="${2:-}"
case "$LEVEL" in 0|1|arch) ;; *) echo "Usage: $0 0|1|arch [--cleanup]" >&2; exit 3;; esac
if [ "$#" -gt 2 ] || { [ -n "$CLEANUP" ] && [ "$CLEANUP" != --cleanup ]; }; then
  echo "Usage: $0 0|1|arch [--cleanup]" >&2; exit 3
fi
export ORACLE_HOME="${ORACLE_HOME:-/u01/app/oracle/product/23.26/dbhome_1}"
export ORACLE_BASE="${ORACLE_BASE:-/u01/app/oracle}"
export ORACLE_SID="${RMAN_SID:-${ORACLE_SID:-}}"
export PATH="$ORACLE_HOME/bin:/usr/bin:/bin"
export NLS_DATE_FORMAT="YYYY-MM-DD HH24:MI:SS"
unset TWO_TASK LOCAL
DB="${RMAN_DB_UNIQUE_NAME:-RAC}"
LOGDIR="${RMAN_LOG_DIR:-/home/oracle/rman/logs}"
case "$DB:$ORACLE_SID" in *[!A-Za-z0-9_+.$#:-]*|:|*:) echo "Invalid/missing DB or SID" >&2; exit 2;; esac
if [ -z "$DB" ] || [ -z "$ORACLE_SID" ]; then echo "Set RMAN_SID and DB identity explicitly" >&2; exit 2; fi
for binary in rman sqlplus srvctl; do
  [ -x "$ORACLE_HOME/bin/$binary" ] || { echo "Missing Oracle tool: $binary" >&2; exit 2; }
done
case "$LOGDIR" in /*) ;; *) echo "RMAN_LOG_DIR must be absolute" >&2; exit 2;; esac
if [ -L "$LOGDIR" ] || ! mkdir -p "$LOGDIR" || [ ! -O "$LOGDIR" ] ||
   [ "$(stat -c %a "$LOGDIR")" != 700 ]; then
  echo "Log directory must be owned by this user, mode 0700, and not a symlink" >&2; exit 2
fi
LOCK="$LOGDIR/.backup.lock"
if [ -L "$LOCK" ] || { [ -e "$LOCK" ] && { [ ! -f "$LOCK" ] || [ ! -O "$LOCK" ]; }; }; then
  echo "Unsafe local lock file" >&2; exit 2
fi
exec 9>"$LOCK" || exit 2
if ! flock -n 9; then echo "Another backup holds the local lock" >&2; exit 4; fi
# This lock is local only. Keep a single scheduling owner until cluster coordination exists.
LOG="$(mktemp "$LOGDIR/${DB}_${LEVEL}_$(date +%Y%m%d_%H%M%S)_XXXXXX.log")" || exit 2
note() { printf '%s %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG"; }
if ! "$ORACLE_HOME/bin/srvctl" status instance -db "$DB" -instance "$ORACLE_SID" >>"$LOG" 2>&1; then
  note "Instance status query failed"; exit 2
fi
IDENTITY="$("$ORACLE_HOME/bin/sqlplus" -L -s / as sysdba <<'SQL'
whenever oserror exit failure rollback
whenever sqlerror exit failure rollback
set heading off feedback off pages 0 verify off echo off lines 32767 trimspool on
select d.db_unique_name||'|'||i.instance_name||'|'||i.status||'|'||d.open_mode from v$database d cross join v$instance i;
exit success rollback
SQL
)"
SQL_RC=$?
printf '%s\n' "$IDENTITY" >>"$LOG"
IDENTITY="$(printf '%s\n' "$IDENTITY" | sed '/^[[:space:]]*$/d;s/^[[:space:]]*//;s/[[:space:]]*$//')"
if [ "$SQL_RC" -ne 0 ] || [ "$IDENTITY" != "$DB|$ORACLE_SID|OPEN|READ WRITE" ]; then
  note "Database identity/open-mode validation failed"; exit 2
fi
case "$LEVEL" in
  0) BODY="BACKUP INCREMENTAL LEVEL 0 DATABASE TAG 'L0_${DB}' PLUS ARCHIVELOG TAG 'ARCH_${DB}';";;
  1) BODY="BACKUP INCREMENTAL LEVEL 1 DATABASE TAG 'L1_${DB}' PLUS ARCHIVELOG TAG 'ARCH_${DB}';";;
  arch) BODY="SQL 'ALTER SYSTEM ARCHIVE LOG CURRENT';
BACKUP ARCHIVELOG ALL NOT BACKED UP 1 TIMES TAG 'ARCH_${DB}';";;
esac
note "Starting level $LEVEL backup of $DB from $ORACLE_SID"
"$ORACLE_HOME/bin/rman" target / >>"$LOG" 2>&1 <<EOF
SET ECHO ON;
RUN {
  CROSSCHECK BACKUP;
  CROSSCHECK ARCHIVELOG ALL;
  $BODY
}
LIST BACKUP SUMMARY;
EXIT;
EOF
RC=$?
if [ "$RC" -ne 0 ] || grep -Eq 'RMAN-00569|ORA-[0-9]+' "$LOG"; then
  note "FAILED backup (rman exit $RC); cleanup was not started"; exit 1
fi
note "Backup command completed; restore validation is a separate required check"
if [ "$CLEANUP" = --cleanup ]; then
  note "Starting explicitly requested cleanup under the reviewed retention policy"
  "$ORACLE_HOME/bin/rman" target / >>"$LOG" 2>&1 <<'RMAN'
DELETE NOPROMPT OBSOLETE;
EXIT;
RMAN
  RC=$?
  if [ "$RC" -ne 0 ] || grep -Eq 'RMAN-00569|ORA-[0-9]+' "$LOG"; then
    note "FAILED cleanup (rman exit $RC)"; exit 1
  fi
else
  note "Cleanup disabled; review retention and downstream consumers before --cleanup"
fi
note "Completed; log $LOG"
exit 0
