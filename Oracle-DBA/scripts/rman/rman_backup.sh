#!/bin/bash
# rman_backup.sh - RMAN backups for the RAC lab database (Oracle 26ai, two nodes).
#
# Usage (as oracle):  rman_backup.sh 0|1|arch
#   0     incremental level 0 (full) database + archivelogs
#   1     incremental level 1 database + archivelogs
#   arch  archivelogs not yet backed up
#
# Backups go to the Fast Recovery Area (+FRA) on shared ASM storage, so either
# node can restore them. Retention, compression, parallelism, controlfile
# autobackup and the archivelog deletion policy come from the one-time
# CONFIGURE settings, not from this script.
#
# Exit codes: 0 success, 1 RMAN errors, 2 local instance not open, 3 usage,
# 4 another backup already running.

set -u

LEVEL="${1:-}"
case "$LEVEL" in
  0|1|arch) ;;
  *) echo "Usage: $0 0|1|arch" >&2; exit 3 ;;
esac

export ORACLE_HOME=/u01/app/oracle/product/23.26/dbhome_1
export ORACLE_BASE=/u01/app/oracle
export PATH="$ORACLE_HOME/bin:/usr/bin:/bin"
export NLS_DATE_FORMAT="YYYY-MM-DD HH24:MI:SS"

DB=RAC
# Instance name follows the node: racnode1 -> RAC1, racnode2 -> RAC2.
NODE_NUM="$(hostname -s | grep -o '[0-9]*$')"
export ORACLE_SID="${DB}${NODE_NUM}"

LOGDIR=/home/oracle/rman/logs
LOG="$LOGDIR/${DB}_${LEVEL}_$(date +%Y%m%d_%H%M%S).log"
LOCK="/tmp/rman_${DB}.lock"
KEEP_LOG_DAYS=30

mkdir -p "$LOGDIR"

note() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; logger -t "rman_${DB}" "$*"; }

# One backup at a time across all levels.
exec 9>"$LOCK"
if ! flock -n 9; then
  note "Skipped level $LEVEL: another RMAN backup holds $LOCK"
  exit 4
fi

# Only run if this node's instance is open.
if ! srvctl status instance -db "$DB" -instance "$ORACLE_SID" | grep -q "is running"; then
  note "FAILED level $LEVEL: instance $ORACLE_SID is not running on $(hostname -s)"
  exit 2
fi

case "$LEVEL" in
  0)    BODY="BACKUP INCREMENTAL LEVEL 0 DATABASE TAG 'L0_${DB}' PLUS ARCHIVELOG TAG 'ARCH_${DB}';" ;;
  1)    BODY="BACKUP INCREMENTAL LEVEL 1 DATABASE TAG 'L1_${DB}' PLUS ARCHIVELOG TAG 'ARCH_${DB}';" ;;
  arch) BODY="SQL 'ALTER SYSTEM ARCHIVE LOG CURRENT';
BACKUP ARCHIVELOG ALL NOT BACKED UP 1 TIMES TAG 'ARCH_${DB}';" ;;
esac

note "Starting level $LEVEL backup of $DB from $ORACLE_SID"

rman target / >>"$LOG" 2>&1 <<EOF
SET ECHO ON;
CROSSCHECK BACKUP;
CROSSCHECK ARCHIVELOG ALL;
$BODY
DELETE NOPROMPT OBSOLETE;
LIST BACKUP SUMMARY COMPLETED AFTER 'SYSDATE-1';
EXIT;
EOF
RC=$?

# RMAN can return 0 with errors in the log, so check both.
if [ "$RC" -ne 0 ] || grep -qE '^(RMAN|ORA)-[0-9]+' "$LOG"; then
  note "FAILED level $LEVEL (rman exit $RC); see $LOG"
  exit 1
fi

note "Completed level $LEVEL backup of $DB; log $LOG"

find "$LOGDIR" -name "${DB}_*.log" -mtime +"$KEEP_LOG_DAYS" -delete
exit 0
