"""Exercise shell orchestration with fake Oracle tools; never run RMAN."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'rman_backup.sh'

class BackupTests(unittest.TestCase):
    def run_backup(self, scenario='success', cleanup=False, level='0'):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            binaries = home / 'bin'
            binaries.mkdir()
            programs = {
                'srvctl': '#!/bin/bash\nexit 0\n',
                'sqlplus': '''#!/bin/bash
cat >/dev/null
if [ "$SCENARIO" = wrong_db ]; then echo 'OTHER|RAC1|OPEN|READ WRITE'; else echo 'RAC|RAC1|OPEN|READ WRITE'; fi
''',
                'rman': '''#!/bin/bash
input=$(cat)
printf '%s\n' "$input" >> "$CAPTURE"
if [[ "$input" == *"DELETE NOPROMPT"* ]]; then
  if [ "$SCENARIO" = cleanup_fail ]; then echo 'RMAN-00569: error stack'; exit 1; fi
elif [ "$SCENARIO" = backup_fail ]; then
  echo 'RMAN-00569: error stack'; exit 1
elif [ "$SCENARIO" = zero_exit_error ]; then
  echo 'RMAN-00569: error stack'; exit 0
fi
exit 0
'''}
            for name, body in programs.items():
                path = binaries / name
                path.write_text(body)
                path.chmod(0o700)
            capture = home / 'commands'
            env = os.environ.copy()
            env.update(ORACLE_HOME=tmp, RMAN_SID='RAC1', RMAN_DB_UNIQUE_NAME='RAC',
                       RMAN_LOG_DIR=str(home/'logs'), CAPTURE=str(capture), SCENARIO=scenario)
            args = ['/bin/bash', str(SCRIPT), level] + (['--cleanup'] if cleanup else [])
            result = subprocess.run(args, env=env, text=True, capture_output=True, timeout=10)
            commands = capture.read_text() if capture.exists() else ''
            permissions = [p.stat().st_mode & 0o777 for p in (home/'logs').glob('*.log')]
            return result, commands, permissions

    def test_default_never_deletes(self):
        result, commands, modes = self.run_backup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('DELETE NOPROMPT', commands)
        self.assertTrue(modes)
        self.assertTrue(all(mode == 0o600 for mode in modes))

    def test_backup_failure_prevents_cleanup(self):
        result, commands, _ = self.run_backup('backup_fail', cleanup=True)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('DELETE NOPROMPT', commands)

    def test_error_banner_with_zero_exit_prevents_cleanup(self):
        result, commands, _ = self.run_backup('zero_exit_error', cleanup=True)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('DELETE NOPROMPT', commands)

    def test_cleanup_runs_only_after_success(self):
        result, commands, _ = self.run_backup(cleanup=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(commands.index('BACKUP INCREMENTAL'), commands.index('DELETE NOPROMPT'))
        self.assertIn('RUN {', commands)

    def test_cleanup_failure_is_not_success(self):
        self.assertEqual(self.run_backup('cleanup_fail', cleanup=True)[0].returncode, 1)

    def test_wrong_database_cannot_start_backup(self):
        result, commands, _ = self.run_backup('wrong_db')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(commands, '')

    def test_archivelog_mode(self):
        result, commands, _ = self.run_backup(level='arch')
        self.assertEqual(result.returncode, 0)
        self.assertIn('BACKUP ARCHIVELOG ALL NOT BACKED UP 1 TIMES', commands)

if __name__ == '__main__':
    unittest.main()
