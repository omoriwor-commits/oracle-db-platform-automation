# SQL Tuning Advisor on a RAC Container Database

**Last updated:** 2026-10-19
**Status:** Planned exercise for my 26ai RAC lab (PDB RACPDB1). Not yet run; results will be added after the exercise.

The SQL Tuning Advisor runs the optimizer in tuning mode on one statement and recommends statistics, indexes, SQL profiles or rewrites. Running it on a chosen statement is the manual advisor (`DBMS_SQLTUNE`). Automatic SQL Tuning is a separate nightly maintenance task that tunes the top SQL by itself.

Licensing: the SQL Tuning Advisor needs the Tuning Pack (which requires the Diagnostics Pack) on Enterprise Edition. AWR needs the Diagnostics Pack.

## RAC and multitenant points

- Create the task in the PDB where the SQL runs (RACPDB1), not the CDB root.
- `create_tuning_task(sql_id => ...)` reads the cursor cache of the instance you're connected to. If the statement only ran on RAC2, connect to RAC2, or build the task from AWR snapshots.

## Exercise

Connect to RACPDB1 as a DBA user, in a scratch schema.

1. Build a slow query: a large table with no index on the filter column.

```sql
CREATE TABLE tune_demo AS
SELECT level id, MOD(level, 1000) cust_id, RPAD('x', 100, 'x') pad
FROM dual CONNECT BY level <= 500000;
EXEC DBMS_STATS.gather_table_stats(USER, 'TUNE_DEMO');

SELECT /* tune_demo_q */ COUNT(*) FROM tune_demo WHERE cust_id = 42;

SELECT sql_id, inst_id, executions, elapsed_time
FROM gv$sql WHERE sql_text LIKE 'SELECT /* tune_demo_q */%';
```

2. Create and run the task on the instance that has the cursor.

```sql
DECLARE
  l_task VARCHAR2(100);
BEGIN
  l_task := DBMS_SQLTUNE.create_tuning_task(
              sql_id     => '&sql_id',
              scope      => DBMS_SQLTUNE.scope_comprehensive,
              time_limit => 60,
              task_name  => 'tune_demo_task');
  DBMS_SQLTUNE.execute_tuning_task(task_name => 'tune_demo_task');
END;
/
SELECT task_name, status, execution_end FROM dba_advisor_tasks WHERE task_name = 'tune_demo_task';
```

3. Read the report. Use a large `LONG` setting or the report is cut off.

```sql
SET LONG 1000000 LONGCHUNKSIZE 1000000 LINESIZE 200 PAGESIZE 0
SELECT DBMS_SQLTUNE.report_tuning_task('tune_demo_task') FROM dual;
```

Expected: an index recommendation on `CUST_ID`, with the current and proposed plans.

4. Act on it and measure. Create the index, rerun the query and compare plans with `DBMS_XPLAN.display_cursor`. If the report proposes a SQL profile instead, accept it with `DBMS_SQLTUNE.accept_sql_profile(task_name => 'tune_demo_task', replace => TRUE)`, and know how to disable or drop it.

5. Clean up.

```sql
EXEC DBMS_SQLTUNE.drop_tuning_task('tune_demo_task');
DROP TABLE tune_demo PURGE;
```

## Automatic SQL Tuning

```sql
SELECT client_name, status FROM dba_autotask_client;
SELECT DBMS_AUTO_SQLTUNE.report_auto_tuning_task FROM dual;
```

On a new lab database the automatic report may be nearly empty, because there is no real workload yet.

## Results

To be added after the exercise: sql_id, instance, before and after elapsed time, the recommendation and what I accepted.
