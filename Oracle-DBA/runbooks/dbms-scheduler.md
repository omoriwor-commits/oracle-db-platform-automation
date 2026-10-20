# Oracle DBMS_SCHEDULER: programs, schedules and jobs

**Last updated:** 2026-10-20.  
**Status:** Reference reviewed against Oracle 26ai documentation; runtime tests pending. No Scheduler objects were created or executed by this publication.

Preserves the supplied scheduling topics for later database/cloud operations and automation. Scheduler complements cron: choose ownership, availability and recovery requirements per task. Database-down monitoring and host recovery must not depend solely on a job inside the unavailable database. Existing cron/RMAN procedures are not replaced by this reference.

## 1. Context and execution prerequisites

Use a dedicated authorized schema in the intended PDB, such as RACPDB1. Check that the example names do not already exist. Own-schema job creation requires CREATE JOB; Scheduler-object privileges granted through roles are not honored by the package. Avoid CREATE ANY JOB for a local exercise.

```sql
SHOW CON_NAME;
SHOW USER
SHOW PARAMETER job_queue_processes
SELECT sessiontimezone, dbtimezone FROM dual;
```

Background execution requires an available/open database/PDB and worker capacity. JOB_QUEUE_PROCESSES=0 disables Scheduler background jobs; check root/PDB settings and RAC placement. [JOB_QUEUE_PROCESSES](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/JOB_QUEUE_PROCESSES.html).

Named programs/schedules support reuse; inline job definitions are also valid. Neither pattern is universally mandatory. Examples below use a harmless NULL action, not schema statistics gathering or an RMAN backup.

## 2. Program

```sql
BEGIN
  DBMS_SCHEDULER.CREATE_PROGRAM(
    program_name => 'DEMO_PLSQL_PROGRAM',
    program_type => 'PLSQL_BLOCK',
    program_action => 'BEGIN NULL; END;',
    enabled => TRUE,
    comments => 'Disposable Scheduler demonstration; no application action');
END;
/
```

Enabling a program does not schedule execution; a job is still required. No redundant ENABLE call is needed after enabled=>TRUE.

### Stored-procedure arguments: separate alternative

Create only if this disposable procedure name is unused:

```sql
CREATE PROCEDURE sched_demo_proc(p_label IN VARCHAR2) AS
BEGIN
  NULL;
END;
/

BEGIN
  DBMS_SCHEDULER.CREATE_PROGRAM(
    program_name => 'DEMO_STORED_PROGRAM',
    program_type => 'STORED_PROCEDURE',
    program_action => 'SCHED_DEMO_PROC',
    number_of_arguments => 1,
    enabled => FALSE);
  DBMS_SCHEDULER.DEFINE_PROGRAM_ARGUMENT(
    program_name => 'DEMO_STORED_PROGRAM',
    argument_position => 1,
    argument_name => 'P_LABEL',
    argument_type => 'VARCHAR2',
    default_value => 'LAB');
  DBMS_SCHEDULER.ENABLE('DEMO_STORED_PROGRAM');
END;
/
```

For real statistics work, use a reviewed wrapper with explicit schema and options. Do not keep the source example's SYS default for a purported HR task. Confirm privileges, statistics preferences and existing automatic maintenance before scheduling additional collection.

## 3. Schedule and calendar review

Example timezone is explicitly America/Chicago, not an assertion about the lab host. Adjust region/start date deliberately; test daylight-saving boundaries.

```sql
BEGIN
  DBMS_SCHEDULER.CREATE_SCHEDULE(
    schedule_name => 'DEMO_HOURLY_SCHED',
    start_date => TO_TIMESTAMP_TZ(
      '2026-10-20 00:00:00 America/Chicago', 'YYYY-MM-DD HH24:MI:SS TZR'),
    repeat_interval => 'FREQ=HOURLY;BYMINUTE=0;BYSECOND=0',
    end_date => NULL,
    comments => 'Hourly at minute and second zero in selected timezone');
END;
/
```

| Intended recurrence | Calendar expression |
|---|---|
| Daily midnight | `FREQ=DAILY;BYHOUR=0;BYMINUTE=0;BYSECOND=0` |
| Daily 16:00 | `FREQ=DAILY;BYHOUR=16;BYMINUTE=0;BYSECOND=0` |
| Hourly at :10 | `FREQ=HOURLY;BYMINUTE=10;BYSECOND=0` |
| Every five minutes | `FREQ=MINUTELY;INTERVAL=5;BYSECOND=0` |
| Monday and Thursday 21:00 | `FREQ=WEEKLY;BYDAY=MON,THU;BYHOUR=21;BYMINUTE=0;BYSECOND=0` |
| First Friday of each quarter at 09:00 | `FREQ=MONTHLY;BYMONTH=1,4,7,10;BYDAY=1FRI;BYHOUR=9;BYMINUTE=0;BYSECOND=0` |

The old weekly expression used a comma instead of a semicolon after WEEKLY. BYDAY=FRI in January/April/July/October selects every Friday in those months, not one Friday per quarter.

Preview timestamps without creating or enabling a job:

```sql
SET SERVEROUTPUT ON
DECLARE
  v_start TIMESTAMP WITH TIME ZONE := TO_TIMESTAMP_TZ(
    '2026-10-20 00:00:00 America/Chicago', 'YYYY-MM-DD HH24:MI:SS TZR');
  v_after TIMESTAMP WITH TIME ZONE := v_start;
  v_next TIMESTAMP WITH TIME ZONE;
BEGIN
  FOR i IN 1..6 LOOP
    DBMS_SCHEDULER.EVALUATE_CALENDAR_STRING(
      calendar_string => 'FREQ=HOURLY;BYMINUTE=0;BYSECOND=0',
      start_date => v_start, return_date_after => v_after,
      next_run_date => v_next);
    DBMS_OUTPUT.PUT_LINE(TO_CHAR(v_next, 'YYYY-MM-DD HH24:MI:SS TZR TZH:TZM'));
    v_after := v_next;
  END LOOP;
END;
/
```

## 4. Job: create disabled and retain definition

```sql
BEGIN
  DBMS_SCHEDULER.CREATE_JOB(
    job_name => 'DEMO_SCHED_JOB',
    program_name => 'DEMO_PLSQL_PROGRAM',
    schedule_name => 'DEMO_HOURLY_SCHED',
    enabled => FALSE,
    auto_drop => FALSE,
    comments => 'Disabled until deliberate lab validation');
  DBMS_SCHEDULER.SET_ATTRIBUTE(
    name => 'DEMO_SCHED_JOB', attribute => 'logging_level',
    value => DBMS_SCHEDULER.LOGGING_RUNS);
END;
/
```

Manual test alternatives, **one at a time**:

```sql
-- Foreground diagnostic: waits and returns errors to this session.
BEGIN
  DBMS_SCHEDULER.RUN_JOB('DEMO_SCHED_JOB', use_current_session => TRUE);
END;
/
```

```sql
-- Background test: return does not establish completion; inspect run logs.
BEGIN
  DBMS_SCHEDULER.RUN_JOB('DEMO_SCHED_JOB', use_current_session => FALSE);
END;
/
```

RUN_JOB can run a disabled valid job. Foreground runs do not update normal job counters/state or appear in running-job views; use a background test to validate coordinator execution. A foreground call can overlap a scheduled run, so test non-idempotent actions carefully. [DBMS_SCHEDULER API](https://docs.oracle.com/en/database/oracle/oracle-database/26/arpls/DBMS_SCHEDULER.html).

Enable recurring execution only after reviewing the next date/action:

```sql
BEGIN DBMS_SCHEDULER.ENABLE('DEMO_SCHED_JOB'); END;
/
```

## 5. Inspection and outcomes

```sql
SELECT program_name, program_type, enabled FROM user_scheduler_programs
WHERE program_name LIKE 'DEMO%';

SELECT schedule_name, start_date, repeat_interval FROM user_scheduler_schedules
WHERE schedule_name = 'DEMO_HOURLY_SCHED';

SELECT job_name, enabled, state, program_name, schedule_name,
       next_run_date, last_start_date, run_count, failure_count
FROM user_scheduler_jobs WHERE job_name = 'DEMO_SCHED_JOB';

SELECT job_name, session_id, running_instance, elapsed_time
FROM user_scheduler_running_jobs WHERE job_name = 'DEMO_SCHED_JOB';

SELECT log_id, TO_CHAR(log_date, 'YYYY-MM-DD HH24:MI:SS TZH:TZM') log_timestamp,
       job_name, status, error#, actual_start_date, run_duration, additional_info
FROM user_scheduler_job_run_details
WHERE job_name = 'DEMO_SCHED_JOB' ORDER BY log_id DESC;
```

Use MI for minutes; MM is month. Running-job views show current runs, not progress percentage. JOBS.STATE describes lifecycle/scheduling; JOB_RUN_DETAILS.STATUS describes an individual run. Successful runs need not leave a repeating job in SUCCEEDED state. Use owner-scoped DBA views only with authorized access. [Scheduler job states](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/ALL_SCHEDULER_JOBS.html).

## 6. Availability, external jobs and cleanup

Do not promise replay of every schedule missed during downtime. Assess lateness, schedule_limit, end dates, enabled state, recovery/retry settings and available workers; verify actual logs. Recovery requires idempotent actions and reconciliation, not just a recurrence string.

External EXECUTABLE programs need host-specific paths, permissions, environment, external-job privileges and an approved OS credential. Remote execution also needs configured destinations/agents. Do not enable a backup executable merely by copying its path into CREATE_PROGRAM. Keep credential secrets out of scripts/Git; use supported credential management. On RAC, verify eligible-node script/storage availability or intentional service placement. Avoid duplicate backup schedules across cron and Scheduler. [Scheduler administration and external jobs](https://docs.oracle.com/en/database/oracle/oracle-database/26/admin/scheduling-jobs-with-oracle-scheduler.html).

To retire this disposable exercise, first disable it and check for active runs:

```sql
BEGIN DBMS_SCHEDULER.DISABLE('DEMO_SCHED_JOB'); END;
/
```

Disabling is not proof an active run stopped. After confirming no active run or shared dependencies, remove in dependency order, without force:

```sql
BEGIN
  DBMS_SCHEDULER.DROP_JOB('DEMO_SCHED_JOB');
  DBMS_SCHEDULER.DROP_PROGRAM('DEMO_PLSQL_PROGRAM');
  DBMS_SCHEDULER.DROP_SCHEDULE('DEMO_HOURLY_SCHED');
END;
/
```

If the stored-procedure alternative was created, separately verify it is unused before dropping DEMO_STORED_PROGRAM and SCHED_DEMO_PROC. Retain required logs before any cleanup.

**Pending evidence:** calendar evaluation, foreground/background outcomes, scheduled run, persistence/logging and checked cleanup. A successful NULL-action demonstration would validate scheduling mechanics only, not statistics gathering or RMAN recovery.

Provenance: rewritten from the supplied Scheduler administration notes. Promotional text/images and article prose are not republished. No historical run or new automated implementation is claimed.

- [Oracle DBA runbook index](README.md)
