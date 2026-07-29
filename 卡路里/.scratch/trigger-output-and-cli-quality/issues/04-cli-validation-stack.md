# 04 — CLI 校验全栈 + ADR-0004(weight-goal flag + argparse type 检查)

**What to build:**
When a user types `<subcommand> --help`, they get argparse usage and exit code 0 (no DB write, no traceback). When they pass a malformed value (e.g., `weight-goal --weight-goal abc`), they get a clear single-line error pointing to the flag — not an `int()` traceback or silent garbage write to the DB. This is the root-cause fix for Issue 6's symptom class.

**Blocked by:** 01 — test isolation infra must exist so this ticket's tests run safely.

**Status:** resolved

- [ ] `calorie_tracker.py` `weight-goal` subcommand no longer accepts positional `<kg> [deadline]`; it requires `--weight-goal <float>` and `--deadline <YYYY-MM-DD>` flags
- [ ] All `calorie_tracker.py` subcommands that take numeric args use `argparse type=float` / `type=int` (covers Issue 6's `int('--days')`, `int('--help')` patterns)
- [ ] Every subcommand that defines a parser automatically supports `--help` (argparse native behavior; verified by running `<cmd> --help` and asserting exit code 0)
- [ ] `calorie_tracker.py list-products` defaults to LIMIT 200 (Q5 part 1)
- [ ] A `--legacy-positional` flag is added to `weight-goal` as a temporary escape hatch, prints a deprecation warning to stderr, and is documented in `--help` text as "deprecated, will be removed 2026-10-29"
- [ ] `tests/test_cli_validation.py` covers at least: (a) `calorie_tracker.py weight-goal --help` → exit 0, stdout contains "usage:"; (b) `calorie_tracker.py weight-goal --weight-goal abc` → exit non-zero, stderr mentions "invalid float"; (c) `calorie_tracker.py weight-goal --weight-goal 73 --deadline 2026-12-31` → exit 0, stdout contains "id=" (success receipt per V1.0 §02 第②特性); (d) `calorie_tracker.py list-products --help` → exit 0; (e) `calorie_tracker.py list-products` → returns 200 rows by default
- [ ] `docs/adr/0004-cli-flag-化.md` written per ADR-FORMAT with Status: accepted, recording: (a) why `--weight-goal --deadline` flags not positional; (b) the 3-month deprecation window for `--legacy-positional`; (c) why we keep argparse instead of click/typer
- [ ] No regression: existing tests in `tests/test_redesign.py` and `tests/test_diet_update_meal.py` still pass against the new CLI surface