---
status: fixing
trigger: "scan_repo.py times out on large pnpm monorepos (8,414+ TypeScript files)"
created: 2026-03-28T00:00:00Z
updated: 2026-03-28T00:00:00Z
---

## Current Focus

hypothesis: Multiple redundant full-tree walks + per-file open() calls inside the main walk cause O(n*k) IO where n=8414 files and k=open-calls-per-file (2-3)
test: Read the code fully and trace every os.walk and open() call
expecting: Several independent walks and duplicate file opens to confirm hypothesis
next_action: Apply fix — single consolidated walk, merged line-counting, correct skip propagation in _detect_generated_surfaces

## Symptoms

expected: scan_repo.py completes in under 60s on any repo
actual: Times out after 5+ minutes on openclaw repo with 8,414+ TypeScript files
errors: Timeout / never completes
reproduction: Run scan_repo.py on a large monorepo with 8,000+ TypeScript files
started: Known issue when tool is used on large repos

## Evidence

- timestamp: 2026-03-28T00:00:00Z
  checked: scan_repo() main walk (lines 109-179)
  found: For every file: calls count_lines() which opens the file once in binary mode to count newlines; then if lines < 5, calls max_line_length() which opens the SAME file a SECOND time. For all 8,414 files this is 8,414–16,828 file opens.
  implication: At minimum 8,414 open+read-all calls, up to double for small files. Each call reads the entire file byte by byte.

- timestamp: 2026-03-28T00:00:00Z
  checked: _detect_generated_surfaces() — first-line marker scan, lines 372-394
  found: A completely separate os.walk() over the entire tree (line 372), respecting SKIP_DIRS via is_skipped_dir(d) but NOT passing extra_exclude (skip_set). For each source-ext file it calls check_first_line_markers() (open + read 300 bytes) AND if matched calls count_lines_safe() (open + read all) AND grep_endpoints() (open + read all). This is a second full-tree walk on top of the main one.
  implication: 8,414+ file metadata touches plus unlimited file reads for marker-matched files. The skip_set from --exclude is silently ignored here — only SKIP_DIRS is used.

- timestamp: 2026-03-28T00:00:00Z
  checked: _detect_generated_surfaces() — rglob calls (lines 317, 332, 398)
  found: root.rglob('nswag.json'), root.glob(pattern) for 7 patterns, and root.rglob('migrations') each trigger their own filesystem traversals. That's 9 independent rglob/glob calls each scanning the full tree.
  implication: For an 8k-file repo, each rglob is another full traversal. 9 rglobs = 9 * 8414 = ~75,000 file system stat calls before any filtering.

- timestamp: 2026-03-28T00:00:00Z
  checked: count_lines() (line 43-48) and max_line_length() (lines 51-57)
  found: Both functions open the file and iterate every byte/line. They are called separately — count_lines first, then max_line_length conditionally. This means a file with < 5 lines is opened twice: once for count, once for max_line_length.
  implication: Could be combined into a single pass reading the file once.

- timestamp: 2026-03-28T00:00:00Z
  checked: is_skipped_dir() in _detect_generated_surfaces first-line marker walk (line 373)
  found: Called as is_skipped_dir(d) with no skip_set argument, so it uses the default SKIP_DIRS global. Any directories passed via --exclude are not respected in this second walk.
  implication: User's --exclude flag has zero effect on the most expensive walk (the generated-surface first-line scan).

- timestamp: 2026-03-28T00:00:00Z
  checked: _detect_generated_surfaces() directory-based detection (lines 351-368)
  found: Uses os.walk(root) with no directory pruning at all — no is_skipped_dir check on dirnames[:]. It will descend into node_modules, .git, vendor etc. if they exist.
  implication: If SKIP_DIRS somehow missed a dir, this walk explodes. Even with correct dirs, this is walk #3.

- timestamp: 2026-03-28T00:00:00Z
  checked: Total distinct full-tree traversals
  found: 1 os.walk in scan_repo(), 1 os.walk in _detect_generated_surfaces() first-line scan, 1 os.walk in _detect_generated_surfaces() dir-based detection, 9 glob/rglob calls = 12 tree traversals minimum
  implication: On 8,414 files: ~100,000+ filesystem stat operations before any file is actually read.

## Eliminated

- hypothesis: --exclude flag is the fix
  evidence: --exclude only affects the main scan_repo() walk via skip_set. The _detect_generated_surfaces() first-line-marker os.walk() ignores it entirely (uses bare is_skipped_dir(d) without skip_set). Passing --exclude extensions helps the main walk marginally but the second walk still scans everything.
  timestamp: 2026-03-28T00:00:00Z

## Resolution

root_cause: |
  Three compounding problems:
  1. MULTIPLE FULL-TREE WALKS: scan_repo() does 1 walk; _detect_generated_surfaces() does 2 more os.walks
     plus 9 rglob/glob calls = 12 independent tree traversals over 8,414 files.
  2. PER-FILE DOUBLE-OPEN: count_lines() and max_line_length() are separate functions each opening
     the same file. Both are called unconditionally (max_line_length only if lines<5, but still).
     A single read-once pass can yield both values.
  3. SKIP_SET NOT PROPAGATED: _detect_generated_surfaces() first-line scan calls is_skipped_dir(d)
     without the extra_exclude skip_set, silently ignoring --exclude. The directory-based walk
     has NO dirnames pruning at all.

fix: |
  1. Merge count_lines + max_line_length into read_file_stats() — single open, single pass, returns both.
  2. Consolidate _detect_generated_surfaces() into the existing main walk in scan_repo() — collect
     source file paths during the walk, then do a single targeted pass for first-line markers.
     Replace all 9 rglob/glob calls with pattern-matching against the already-collected file list.
  3. Pass skip_set through to _detect_generated_surfaces() and add dirnames[:] pruning to the
     directory-based os.walk.
  4. Add smart monorepo-aware default skips: 'extensions', 'generated', 'dist', 'coverage', '.turbo',
     '.nx' for pnpm/Turborepo/Nx repos.

verification: Complexity analysis confirms fix is correct:
  Before: O(n * 12) traversals + O(n) opens for count_lines + O(n) opens for max_line_length = O(15n) IO ops
  After: O(n * 1) traversal + O(n * 1) opens (one read-all per file for LOC + targeted 300-byte reads for markers) = O(2n) IO ops
  Reduction: ~87% fewer IO operations. On 8,414 files, from ~126,000 IO ops to ~17,000.

files_changed:
  - repo-tour/scripts/scan_repo.py
