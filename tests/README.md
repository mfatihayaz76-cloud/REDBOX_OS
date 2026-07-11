# PHASE 9 Baseline Regression Harness

This directory contains the REDBOX OS PHASE 11 read-only regression harness for the verified PHASE 9 baseline contract.

Protected baseline:

`backups/PHASE9_FINAL_20260709_144106`

The harness opens the live database at `database/redbox_os.db` in SQLite read-only URI mode. It does not import runtime modules, does not import `app.py`, and does not import `database.db`, because runtime startup code may initialize or modify schema state.

No migration or import scripts are executed by this harness.

Run:

`.venv/bin/python -m unittest tests.test_phase9_baseline -v`

If any test fails, stop development. Do not auto-correct the database. Compare the failure against:

`backups/PHASE9_FINAL_20260709_144106/BASELINE_MANIFEST.txt`

Investigate evidence before any data correction.
