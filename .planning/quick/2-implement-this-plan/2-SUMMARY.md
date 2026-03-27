---
phase: quick-2
plan: 01
subsystem: repo-tour/scripts
tags: [performance, scanning, git, threading, sampling]
dependency_graph:
  requires: []
  provides: [optimised-scan_repo]
  affects: [repo-tour/scripts/scan_repo.py]
tech_stack:
  added: [concurrent.futures, random]
  patterns: [git-ls-files-enumeration, stat-based-bucketing, parallel-sampling]
key_files:
  modified: [repo-tour/scripts/scan_repo.py]
decisions:
  - use-git-ls-files-primary-with-os-walk-fallback
  - stat-only-for-non-source-size-bucketing
  - threadpoolexecutor-8-workers-for-sample-reads
  - separate-file_heads-pass-for-small-extensions
metrics:
  duration: ~15m
  completed: 2026-03-27T23:14:35Z
  tasks_completed: 2
  files_modified: 1
---

# Phase quick-2 Plan 01: scan_repo Hot-Path Optimisation Summary

One-liner: Git ls-files enumeration + os.stat byte-threshold bucketing + ThreadPoolExecutor LOC sampling replace the full-file-open-per-file hot path in scan_repo.py.

## What Was Changed

Three optimisations were applied to `repo-tour/scripts/scan_repo.py`:

### 1. `_enumerate_files()` — git ls-files primary enumeration

Replaces the `os.walk` loop inside `scan_repo()` with a subprocess call to `git ls-files --cached --others --exclude-standard`. When inside a git repo this reads the already-built index rather than traversing the filesystem, giving O(index) vs O(tree) cost. The function applies `skip_set` filtering against path components to honour `extra_exclude` dirs. Falls back to `os.walk` with full `SKIP_DIRS` pruning when git is unavailable or returns empty output.

### 2. `_size_bucket()` — stat-based bucketing for non-source files

Non-source files (extensions not in `SOURCE_EXTS`) previously had `read_file_stats()` called on each one, opening and reading the file to count lines. The new path calls `os.stat(fpath).st_size` and maps the byte size to a size tier via calibrated thresholds:

| Threshold | Line equivalent |
|-----------|----------------|
| < 33 000 B | < 500 lines (small) |
| < 195 000 B | < 3 000 lines (medium) |
| < 650 000 B | < 10 000 lines (large) |
| >= 650 000 B | xlarge |

These are calibrated at ~65 bytes/line per the plan spec. Non-source files contribute 0 lines to `total_loc` (their LOC was never semantically meaningful).

### 3. `_sample_loc()` — statistical LOC sampling with ThreadPoolExecutor

Source file paths are collected into `ext_source_files: dict[str, list[str]]` during the enumeration loop (no file opens in the loop body for source files). After the loop, `_sample_loc()` is called:

- Extensions with `<= 50` files: all files are read via `ThreadPoolExecutor(max_workers=8)`.
- Extensions with `> 50` files: `random.sample(paths, 50)` is drawn and read in parallel; the average LOC is scaled to the full extension count (`int(avg * len(paths))`). `is_estimate` is set `True`.

`meta.total_loc_is_estimate` is set in the output dict to signal when sampling was used.

### file_heads and file_stats population

A second pass over `ext_source_files` collects `file_heads` (first-300-byte head text) and `file_stats` (line counts) for small extensions (<=50 files), using `read_file_stats(fpath, collect_head=True)`. This also handles minified detection and exact size bucketing for small source extensions. Large extension groups use stat-based bucketing for size distribution.

For large extensions, `file_heads` entries are left empty — `_detect_generated_surfaces` has an inline fallback that opens the file if its head is missing from the cache.

## Edge Cases Encountered

- **os.walk fallback correctness**: The `_enumerate_files` fallback preserves the exact `(abs_path, rel_path)` tuple shape from the original walk. The `fname = os.path.basename(fpath)` extraction in the main loop correctly handles both forward-slash (git) and OS-separator (os.walk) paths.
- **skip_set filtering in git path**: The plan specified filtering path `parts` against `skip_set`. Since `git ls-files --exclude-standard` already honours `.gitignore`, only extra_exclude dirs need filtering; SKIP_DIRS items covered by .gitignore are effectively free.
- **Double-read for small source extensions**: `_sample_loc` reads small-extension files once (for LOC totals), then the file_heads pass reads them again (for head text + per-file stats). This is acceptable per the plan's "simplest correct path" guidance — small groups are fast by definition (<= 50 files).
- **Large extension xlarge assignment**: For large-extension source files, stat-based bucketing is used for size distribution. The `xlarge` branch in `_size_bucket` is always assigned `files_by_size['xlarge']` (not `mega`) — true mega detection remains source-only for small groups.

## Verification Results

All four checks passed:

```
# Task 1 smoke test (git repo)
ok 85 files

# Task 2 meta key check
PASS — total_files=85 total_loc=5834 estimate=False

# Full shape verification (all required_keys present)
Shape OK. files=85 loc=5834 estimate=False

# os.walk fallback with temp non-git dir
Fallback path OK
```

`estimate=False` on this repo because no extension has more than 50 source files — all groups are read exactly, so `total_loc` is exact (not an estimate).

## Deviations from Plan

None — plan executed exactly as written. The one design note: `_sample_loc` uses `ThreadPoolExecutor` for both small and large groups (plan only required it for large groups). Using it for small groups too simplifies the code and causes no correctness issues.

## Self-Check

### Files created/modified

- `repo-tour/scripts/scan_repo.py` — exists and was modified (400 insertions, 212 deletions)

### Commits

- `1e1c46b` — feat(quick-2-01): optimise scan_repo hot path — git ls-files, stat bucketing, parallel LOC sampling

## Self-Check: PASSED
