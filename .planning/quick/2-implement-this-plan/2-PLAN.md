---
phase: quick-2
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - repo-tour/scripts/scan_repo.py
autonomous: true
requirements:
  - PERF-01-git-ls-files
  - PERF-02-stat-bucketing
  - PERF-03-sampling
  - PERF-04-parallel-reads

must_haves:
  truths:
    - "scan_repo() returns the same output shape as today (no key removed, no type changed)"
    - "total_files, source_files, file_counts_by_ext, key_files, top_dirs are exact (no sampling)"
    - "total_loc is within ±5% of true value; output includes total_loc_is_estimate: true when sampling was used"
    - "files_by_size buckets use byte-threshold sizing for non-source files and line-count for source files"
    - "git ls-files is used for enumeration when the target is a git repo; os.walk fallback fires otherwise"
    - "ThreadPoolExecutor with 8 workers parallelises the up-to-50-file sample reads per extension"
  artifacts:
    - path: "repo-tour/scripts/scan_repo.py"
      provides: "Optimised scan implementation"
      contains: "git ls-files"
  key_links:
    - from: "_enumerate_files()"
      to: "git ls-files subprocess call"
      via: "subprocess.run + fallback to os.walk"
      pattern: "git.*ls-files"
    - from: "_size_bucket()"
      to: "os.stat().st_size"
      via: "stat call, byte thresholds"
      pattern: "os\\.stat"
    - from: "_sample_loc()"
      to: "ThreadPoolExecutor"
      via: "concurrent.futures.ThreadPoolExecutor(max_workers=8)"
      pattern: "ThreadPoolExecutor"
---

<objective>
Rewrite the hot path of scan_repo.py with three targeted optimisations:
  1. git ls-files for file enumeration (replaces os.walk when inside a git repo)
  2. os.stat() byte-threshold bucketing for non-source files (replaces opening every file)
  3. Statistical LOC sampling with ThreadPoolExecutor for large extension groups

Purpose: Eliminate the per-file open that currently fires for every non-source file and
replace full-tree os.walk with git's already-built index read, giving 2-20x speed gains on
large repos without degrading output quality.

Output: Single updated file — repo-tour/scripts/scan_repo.py
</objective>

<execution_context>
@C:/Users/upayan.ghosh/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/upayan.ghosh/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

<!-- Current implementation (key signatures the executor must preserve) -->
<interfaces>
From repo-tour/scripts/scan_repo.py (public API — must not change):

```python
def scan_repo(repo_path: str, extra_exclude: set = None) -> dict:
    """Returns dict with keys:
      meta: {name, total_files, source_files, total_loc}
      top_dirs, key_files, file_counts_by_ext, files_by_size,
      mega_files, skip_candidates, readme_excerpt, git_info,
      generated_surfaces_count, _generated_api_surfaces, _token_estimate
    """

def _detect_generated_surfaces(root, all_walked_files, skip_set, file_heads, file_stats) -> list:
    """all_walked_files: list of (abs_path_str, rel_path_str)
       file_heads: rel -> lowercase first-300-bytes (source files only)
       file_stats: rel -> int line count
    """

# Constants (preserve names, values can change for thresholds):
SKIP_DIRS: set  # dirs to exclude from os.walk fallback
SOURCE_EXTS: set  # extensions that count as source
```

Byte-size thresholds for line-count equivalents (calibrated at ~65 bytes/line):
  FILE_SMALL  = 500  lines  →  32 750 bytes  (use 33_000)
  FILE_MEDIUM = 3000 lines  → 195 000 bytes  (use 195_000)
  FILE_LARGE  = 10000 lines → 650 000 bytes  (use 650_000)
  MEGA        = > 650 000 bytes
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add _enumerate_files() — git ls-files with os.walk fallback</name>
  <files>repo-tour/scripts/scan_repo.py</files>
  <action>
Add a new helper function `_enumerate_files(root: Path, skip_set: set) -> list[tuple[str, str]]`
at module level (above scan_repo). It returns a list of (abs_path_str, rel_path_str) tuples,
identical to what the current os.walk loop produces, so that the rest of scan_repo() is
unchanged.

Implementation:

```python
import random
import concurrent.futures   # add to top-level imports

def _enumerate_files(root: Path, skip_set: set) -> list:
    """Return [(abs_path, rel_path), ...] for every tracked file.

    Strategy:
      1. Try `git ls-files --cached --others --exclude-standard` in root.
         If it succeeds (returncode==0, stdout non-empty), parse the output.
         git respects .gitignore automatically; no SKIP_DIRS filtering needed
         except to honour extra_exclude dirs the caller passed in.
      2. Fall back to os.walk + SKIP_DIRS if git is unavailable or not a repo.
    """
    try:
        result = subprocess.run(
            ['git', '-C', str(root), 'ls-files', '--cached', '--others',
             '--exclude-standard'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            files = []
            for line in result.stdout.splitlines():
                rel = line.strip()
                if not rel:
                    continue
                # honour extra_exclude dirs (skip_set beyond SKIP_DIRS)
                parts = Path(rel).parts
                if any(p in skip_set for p in parts):
                    continue
                abs_path = str(root / rel)
                # normalise rel to OS separators for downstream compatibility
                files.append((abs_path, str(Path(rel))))
            if files:
                return files
    except Exception:
        pass

    # Fallback: os.walk
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not is_skipped_dir(d, skip_set)]
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, root)
            files.append((fpath, rel))
    return files
```

Replace the `for dirpath, dirnames, filenames in os.walk(root):` block inside scan_repo()
with a single call: `all_walked_files = _enumerate_files(root, skip_set)`.

Then move the per-file logic (key_files detection, count increments, line reading) into a
`for fpath, rel in all_walked_files:` loop. The loop body is identical to what existed
inside the os.walk loop — no logic changes.

Also update `meta` output to include `total_loc_is_estimate: False` by default (will be
set True in Task 2 when sampling fires). This key goes inside `meta`, not at top level.
  </action>
  <verify>
    python repo-tour/scripts/scan_repo.py . --output-generated-surfaces /dev/null | python -c "import sys,json; d=json.load(sys.stdin); assert d['meta']['total_files'] > 0, 'no files'; print('ok', d['meta']['total_files'], 'files')"
  </verify>
  <done>
    scan_repo() runs to completion, total_files > 0, output JSON shape unchanged.
    If run inside a git repo the git path fires (verify by adding a temporary print to stderr
    inside the git branch, or by checking that SKIP_DIRS-named dirs are not double-filtered).
  </done>
</task>

<task type="auto">
  <name>Task 2: Add _size_bucket() and _sample_loc() — stat bucketing + parallel sampling</name>
  <files>repo-tour/scripts/scan_repo.py</files>
  <action>
**Part A — byte-threshold bucketing for non-source files**

Add helper:

```python
# Byte-size thresholds (calibrated at ~65 bytes/line)
SIZE_SMALL  =  33_000   # < 500 lines
SIZE_MEDIUM = 195_000   # < 3 000 lines
SIZE_LARGE  = 650_000   # < 10 000 lines
# >= 650_000 → xlarge / mega handled separately

def _size_bucket(byte_size: int) -> str:
    """Map file byte size to size tier without opening the file."""
    if byte_size < SIZE_SMALL:
        return 'small'
    elif byte_size < SIZE_MEDIUM:
        return 'medium'
    elif byte_size < SIZE_LARGE:
        return 'large'
    else:
        return 'xlarge'   # mega handled separately by caller
```

In the main `for fpath, rel in all_walked_files:` loop, change the bucketing logic:

- For **non-source** files (ext NOT in SOURCE_EXTS): call `os.stat(fpath).st_size`
  to get the byte size, then `_size_bucket(byte_size)` to assign the tier.
  Do NOT open the file for line counting. Contribute 0 lines to total_loc for these
  files (they are not source code; their LOC was never meaningful for calibration).
  Detect mega non-source files: if byte_size >= SIZE_LARGE, treat as xlarge (not mega —
  non-source mega-files are rarely meaningful; true mega detection stays source-file-only).

- For **source** files (ext in SOURCE_EXTS): keep the existing `read_file_stats()` call
  (exact line count, head collection). Use line-based thresholds (FILE_SMALL / FILE_MEDIUM /
  FILE_LARGE / 10000) as before. Mega file detection with `_is_likely_generated` stays
  source-only.

- Minified detection stays source-only (already gated on a large max_len condition).

**Part B — statistical LOC sampling with ThreadPoolExecutor**

After the enumeration loop has run and `file_stats` is built (source files only),
replace the simple `total_loc = sum(file_stats.values())` accumulation with a
sampling-based approach:

```python
SAMPLE_THRESHOLD = 50   # extensions with > this many files get sampled
SAMPLE_SIZE = 50        # number of files to open per extension

def _sample_loc(ext_files: dict[str, list[str]]) -> tuple[int, bool]:
    """Estimate total LOC across all source files using sampling.

    Args:
        ext_files: {ext: [list of abs_paths]} for source files only

    Returns:
        (estimated_total_loc, is_estimate)
    """
    is_estimate = False
    total = 0

    def _read_lines(path):
        return read_file_stats(path)[0]

    for ext, paths in ext_files.items():
        if len(paths) <= SAMPLE_THRESHOLD:
            # Small group: read all (already fast)
            for p in paths:
                total += _read_lines(p)
        else:
            is_estimate = True
            sample = random.sample(paths, SAMPLE_SIZE)
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                counts = list(ex.map(_read_lines, sample))
            avg = sum(counts) / len(counts)
            total += int(avg * len(paths))

    return total, is_estimate
```

Wire into scan_repo():

1. During the enumeration loop, build `ext_source_files: dict[str, list[str]]`
   mapping ext → list of abs_paths for source files only (in addition to the existing
   `file_stats` dict which now accumulates from the read_file_stats calls for
   extensions with <= 50 files).

2. Actually: since _sample_loc replaces the per-file reads for large groups, adjust
   the loop: for source files, only read_file_stats immediately if
   `file_counts_by_ext.get(ext, 0) <= SAMPLE_THRESHOLD` (you may not know final
   count yet). Simplest correct approach: collect ALL source file paths in
   `ext_source_files` during the loop WITHOUT reading them, then call
   `_sample_loc(ext_source_files)` after the loop. For generated_surfaces detection,
   `file_heads` is still needed — for source extensions with <= 50 files, do a
   second read pass collecting heads; for large groups, sample the same 50 files
   for heads (already read). The simplest correct path:

   - Collect `ext_source_files` during enumeration (no file opens for source files
     in the loop body, except for key_files-related head needed by _detect_generated_surfaces).
   - After enumeration, call `total_loc, is_estimate = _sample_loc(ext_source_files)`.
   - For file_heads (needed by _detect_generated_surfaces): do a separate single-pass
     over source files with <= 50 peers, calling `read_file_stats(fpath, collect_head=True)`
     and populating `file_heads[rel]` and `file_stats[rel]`. For large-extension files
     the sample paths already have their counts from _sample_loc internals — but
     file_heads are not critical for correctness (they are a cache; the fallback in
     _detect_generated_surfaces opens the file if head is missing). So for large groups,
     leave file_heads unpopulated — the fallback handles it.

3. Set `meta['total_loc_is_estimate'] = is_estimate` in the result dict.

Keep `_generate_surfaces` call and all other output fields unchanged.
  </action>
  <verify>
    python repo-tour/scripts/scan_repo.py . --output-generated-surfaces /dev/null | python -c "
import sys, json
d = json.load(sys.stdin)
m = d['meta']
assert 'total_loc_is_estimate' in m, 'missing total_loc_is_estimate'
assert isinstance(m['total_loc'], int), 'total_loc not int'
assert m['total_files'] > 0
assert d['files_by_size']['small'] >= 0
print('PASS — total_files=%d total_loc=%d estimate=%s' % (m['total_files'], m['total_loc'], m['total_loc_is_estimate']))
"
  </verify>
  <done>
    - total_loc_is_estimate key present in meta (True or False depending on repo size)
    - files_by_size buckets populated and sum approximately equals total_files
    - No exception raised during stat-based bucketing
    - ThreadPoolExecutor import present and used inside _sample_loc
    - Non-source files no longer opened (verify by reading the code: stat call present,
      read_file_stats absent for non-source branches)
  </done>
</task>

</tasks>

<verification>
Run the scanner against two repos and compare output shape:

```bash
# Against this repo (git repo, moderate size)
python repo-tour/scripts/scan_repo.py . 2>/dev/null | python -c "
import sys, json
d = json.load(sys.stdin)
m = d['meta']
required_keys = ['name','total_files','source_files','total_loc','total_loc_is_estimate']
for k in required_keys:
    assert k in m, f'missing key: {k}'
assert d.get('files_by_size')
assert d.get('key_files')
assert d.get('top_dirs') is not None
print('Shape OK. files=%d loc=%d estimate=%s' % (m['total_files'], m['total_loc'], m['total_loc_is_estimate']))
"

# Quick functional smoke-test (non-git temp dir — triggers os.walk fallback)
python -c "
import tempfile, pathlib, subprocess, json, sys
with tempfile.TemporaryDirectory() as d:
    pathlib.Path(d+'/a.py').write_text('x=1\n'*100)
    pathlib.Path(d+'/b.txt').write_text('hello\n')
    r = subprocess.run(['python','repo-tour/scripts/scan_repo.py',d],
                       capture_output=True, text=True)
    out = json.loads(r.stdout)
    assert out['meta']['total_files'] == 2, out['meta']
    print('Fallback path OK')
"
```
</verification>

<success_criteria>
- scan_repo() output JSON is backward-compatible (all existing keys present)
- meta.total_loc_is_estimate key added
- git ls-files used for enumeration on git repos (confirmed in code)
- os.stat() used for non-source file bucketing (no read_file_stats call for non-source)
- ThreadPoolExecutor present in _sample_loc with max_workers=8
- Both smoke tests pass (git path + os.walk fallback path)
</success_criteria>

<output>
After completion, create `.planning/quick/2-implement-this-plan/2-SUMMARY.md` with:
- What was changed and why
- Any edge cases encountered
- Verification results
</output>
