#!/usr/bin/env python3
"""scan_repo.py — Repo structure scanner. Budget: ~800 tokens output."""

import os
import sys
import json
import fnmatch
import random
import subprocess
import concurrent.futures
from pathlib import Path

CHUNK_SIZE = 65536  # 64 KB — fast binary chunk reads (~7x faster than line-by-line)

# Default dirs to always skip — includes compiled-language output folders (bin/, obj/)
# that would otherwise inflate file counts 10x on .NET and Java repos.
# Also covers common monorepo tooling dirs (.turbo, .nx) and generated output dirs
# (generated, __generated__) that can contain thousands of files in pnpm/Nx/Turborepo repos.
SKIP_DIRS = {
    'node_modules', '.git', 'vendor', 'dist', 'build', '__pycache__',
    '.next', 'target', '.venv', 'venv', '.tox', 'coverage',
    '.nyc_output', '.cache', '.idea', '.vscode',
    'bin', 'obj', 'out', 'artifacts', '.gradle', 'gradle',
    'packages',  # NuGet packages restore dir
    # Monorepo tooling caches
    '.turbo', '.nx', '.moon',
    # Generated output directories
    'generated', 'gen', 'proto-gen',
    # Test/coverage output
    'lcov-report', 'test-results', 'playwright-report',
    # Compiled output
    'storybook-static', '.svelte-kit',
}

# Extensions that count as source files (for calibration, not total_files)
SOURCE_EXTS = {
    'ts', 'tsx', 'js', 'jsx', 'mjs', 'cjs',
    'py', 'go', 'rs', 'cs', 'java', 'kt', 'swift',
    'rb', 'php', 'scala', 'clj', 'ex', 'exs',
    'cpp', 'c', 'h', 'hpp', 'cc',
    'dart', 'elm', 'ml', 'fs', 'fsx',
}

FILE_SMALL = 500
FILE_MEDIUM = 3000
FILE_LARGE = 10000


# Byte-size thresholds (calibrated at ~65 bytes/line)
SIZE_SMALL  =  33_000   # < 500 lines
SIZE_MEDIUM = 195_000   # < 3 000 lines
SIZE_LARGE  = 650_000   # < 10 000 lines
# >= 650_000 → xlarge / mega handled separately

SAMPLE_THRESHOLD = 50   # extensions with > this many source files get sampled
SAMPLE_SIZE = 50        # number of files to open per extension when sampling


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def is_skipped_dir(name: str, skip_set: set = None) -> bool:
    s = skip_set if skip_set is not None else SKIP_DIRS
    return name in s or name.startswith('.')


def read_file_stats(path: str, collect_head: bool = False) -> tuple:
    """Read a file once and return (line_count, max_line_length, head_text).

    Uses 64 KB chunk reads with buf.count(b'\\n') — ~7x faster than
    line-by-line iteration for large files.  When collect_head=True the
    first 300 bytes are decoded and returned as a lowercase string so
    callers can check for generated-file markers without a second open.
    head_text is None when collect_head=False.
    """
    try:
        lines = 0
        max_len = 0
        head_text = None

        with open(path, 'rb') as f:
            if collect_head:
                first = f.read(300)
                head_text = first.decode('utf-8', errors='ignore').lower()
                lines += first.count(b'\n')
                for seg in first.split(b'\n'):
                    if len(seg) > max_len:
                        max_len = len(seg)
            while True:
                buf = f.read(CHUNK_SIZE)
                if not buf:
                    break
                lines += buf.count(b'\n')
                for seg in buf.split(b'\n'):
                    if len(seg) > max_len:
                        max_len = len(seg)

        return lines, max_len, head_text
    except Exception:
        return 0, 0, None


def count_lines(path: str) -> int:
    """Legacy shim — delegates to read_file_stats() to avoid breaking callers."""
    return read_file_stats(path)[0]


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


def _sample_loc(ext_files: dict) -> tuple:
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
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                counts = list(ex.map(_read_lines, paths))
            total += sum(counts)
        else:
            is_estimate = True
            sample = random.sample(paths, SAMPLE_SIZE)
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                counts = list(ex.map(_read_lines, sample))
            avg = sum(counts) / len(counts)
            total += int(avg * len(paths))

    return total, is_estimate


def scan_repo(repo_path: str, extra_exclude: set = None) -> dict:
    """Scan a repository and return structured analysis data.

    Args:
        repo_path: Path to the repository root.
        extra_exclude: Additional directory names to skip (e.g. {'migrations', 'generated'}).
                       Combined with the default SKIP_DIRS set.
    """
    root = Path(repo_path).resolve()
    name = root.name

    skip_set = SKIP_DIRS | (extra_exclude or set())

    total_files = 0
    source_files = 0   # source-language files only (for scope calibration)
    total_loc = 0
    file_counts_by_ext = {}
    files_by_size = {'small': 0, 'medium': 0, 'large': 0, 'xlarge': 0, 'mega': 0}
    mega_files = []
    skip_candidates = []
    top_dirs = []
    # Collected during the main walk — passed to _detect_generated_surfaces so it
    # does not need to re-traverse the tree.
    all_walked_files: list = []  # list of (abs_path_str, rel_path_str)
    file_heads: dict = {}        # rel_path -> lowercase first-300-bytes (source files only)
    file_stats: dict = {}        # rel_path -> line count
    key_files = {
        'package_json': False, 'dockerfile': False, 'ci_config': False,
        'readme': False, 'requirements_txt': False, 'cargo_toml': False,
        'go_mod': False, 'makefile': False, 'docker_compose': False,
        'env_example': False
    }

    # Directory tree: first 2 levels, max 30 entries
    seen_dirs = set()
    dir_entry_count = 0
    for item in sorted(root.iterdir()):
        if dir_entry_count >= 30:
            break
        if item.is_dir() and not is_skipped_dir(item.name, skip_set):
            top_dirs.append(item.name + '/')
            dir_entry_count += 1
            seen_dirs.add(item.name)
            # Level 2
            try:
                for sub in sorted(item.iterdir()):
                    if dir_entry_count >= 30:
                        break
                    if sub.is_dir() and not is_skipped_dir(sub.name, skip_set):
                        top_dirs.append(item.name + '/' + sub.name + '/')
                        dir_entry_count += 1
            except PermissionError:
                pass

    # Enumerate files — git ls-files when inside a git repo, os.walk otherwise.
    all_walked_files = _enumerate_files(root, skip_set)

    # ext → list of abs_paths for source files (used by _sample_loc after the loop)
    ext_source_files: dict = {}

    for fpath, rel in all_walked_files:
        fname = os.path.basename(fpath)
        ext = Path(fname).suffix.lstrip('.').lower()

        # Key file detection
        fname_lower = fname.lower()
        if fname_lower == 'package.json':
            key_files['package_json'] = True
        elif fname_lower in ('dockerfile', 'dockerfile.prod', 'dockerfile.dev'):
            key_files['dockerfile'] = True
        elif fname_lower in ('.env.example', '.env.sample', '.env.template'):
            key_files['env_example'] = True
        elif fname_lower in ('makefile', 'makefile.mk'):
            key_files['makefile'] = True
        elif fname_lower in ('docker-compose.yml', 'docker-compose.yaml'):
            key_files['docker_compose'] = True
        elif fname_lower in ('requirements.txt', 'requirements-dev.txt'):
            key_files['requirements_txt'] = True
        elif fname_lower == 'cargo.toml':
            key_files['cargo_toml'] = True
        elif fname_lower == 'go.mod':
            key_files['go_mod'] = True
        elif fname_lower.startswith('readme'):
            key_files['readme'] = True
        elif fname_lower in ('.github', 'ci.yml', 'ci.yaml') or '.github' in fpath:
            key_files['ci_config'] = True
        elif fname_lower in ('workflow.yml', 'workflow.yaml', '.travis.yml',
                              '.circleci/config.yml', 'azure-pipelines.yml'):
            key_files['ci_config'] = True

        if ext in ('yml', 'yaml') and '.github' in fpath:
            key_files['ci_config'] = True

        # Count
        total_files += 1
        is_src = ext in SOURCE_EXTS
        if is_src:
            source_files += 1
        if ext:
            file_counts_by_ext[ext] = file_counts_by_ext.get(ext, 0) + 1

        if is_src:
            # Collect path for post-loop LOC sampling
            if ext not in ext_source_files:
                ext_source_files[ext] = []
            ext_source_files[ext].append(fpath)
        else:
            # Non-source files: stat-based bucket — no file open needed.
            try:
                byte_size = os.stat(fpath).st_size
                bucket = _size_bucket(byte_size)
                files_by_size[bucket] += 1
            except Exception:
                files_by_size['small'] += 1

    # Post-loop: compute LOC via sampling and collect file_heads / file_stats
    # for source files. For extensions with <= SAMPLE_THRESHOLD files we read
    # them all (already fast). For large groups _sample_loc samples 50 files.
    total_loc, is_estimate = _sample_loc(ext_source_files)

    # Populate file_heads and file_stats (needed by _detect_generated_surfaces).
    # For small extensions: read with collect_head=True.
    # For large extensions: leave heads empty — _detect_generated_surfaces has a
    # per-file fallback open for any missing entries.
    for ext, paths in ext_source_files.items():
        if len(paths) <= SAMPLE_THRESHOLD:
            for fpath in paths:
                rel = os.path.relpath(fpath, root)
                try:
                    lines, max_len, head = read_file_stats(fpath, collect_head=True)
                    file_stats[rel] = lines
                    if head is not None:
                        file_heads[rel] = head

                    # Minified detection
                    if lines < 5 and max_len > 1000:
                        skip_candidates.append(rel[:200])

                    # Size bucket (source files use line-count thresholds)
                    if lines < FILE_SMALL:
                        files_by_size['small'] += 1
                    elif lines < FILE_MEDIUM:
                        files_by_size['medium'] += 1
                    elif lines < FILE_LARGE:
                        files_by_size['large'] += 1
                    elif lines < 10000:
                        files_by_size['xlarge'] += 1
                    else:
                        files_by_size['mega'] += 1
                        mega_files.append({
                            'path': rel[:200],
                            'lines': lines,
                            'likely_generated': _is_likely_generated(fpath, head_text=head)
                        })
                        skip_candidates.append(rel[:200])
                except Exception:
                    files_by_size['small'] += 1
        else:
            # Large extension group: assign xlarge bucket for all as approximation;
            # exact per-file line counts were sampled (not stored per-file) so use
            # a lightweight stat-based bucket for size distribution.
            for fpath in paths:
                rel = os.path.relpath(fpath, root)
                try:
                    byte_size = os.stat(fpath).st_size
                    bucket = _size_bucket(byte_size)
                    if bucket == 'xlarge':
                        # Check if truly mega (>= SIZE_LARGE) — treat as xlarge not mega
                        # for source files in large groups (exact detection only for small groups)
                        files_by_size['xlarge'] += 1
                    else:
                        files_by_size[bucket] += 1
                except Exception:
                    files_by_size['small'] += 1

    # Top 8 extensions
    top_exts = sorted(file_counts_by_ext.items(), key=lambda x: -x[1])[:8]
    file_counts_by_ext = dict(top_exts)

    # README excerpt
    readme_excerpt = ''
    for candidate in ('README.md', 'README.txt', 'README.rst', 'README'):
        rpath = root / candidate
        if rpath.exists():
            try:
                readme_excerpt = rpath.read_text(encoding='utf-8', errors='ignore')[:200]
            except Exception:
                pass
            break

    # Git info
    git_info = _get_git_info(str(root))

    # Generated file detection — reuses already-walked file list to avoid
    # any additional tree traversal.
    generated_api_surfaces = _detect_generated_surfaces(
        root, all_walked_files, skip_set, file_heads, file_stats
    )
    generated_surfaces_count = len(generated_api_surfaces)

    result = {
        'meta': {
            'name': name,
            'total_files': total_files,
            'source_files': source_files,   # source-language files only; use this for scope calibration
            'total_loc': total_loc,
            'total_loc_is_estimate': is_estimate,
        },
        'top_dirs': top_dirs[:30],
        'key_files': key_files,
        'file_counts_by_ext': file_counts_by_ext,
        'files_by_size': files_by_size,
        'mega_files': mega_files[:10],
        'skip_candidates': list(set(skip_candidates))[:20],
        'readme_excerpt': readme_excerpt,
        'git_info': git_info,
        'generated_surfaces_count': generated_surfaces_count,
        '_generated_api_surfaces': generated_api_surfaces,  # written to sidecar
        '_token_estimate': 0
    }

    output_str = json.dumps(result)
    result['_token_estimate'] = estimate_tokens(output_str)
    return result


def _is_likely_generated(fpath: str, head_text: str = None) -> bool:
    markers = ('generated', 'auto-generated', 'do not edit', 'autogenerated')
    if head_text is not None:
        return any(m in head_text for m in markers)
    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            head = f.read(500).lower()
            return any(m in head for m in markers)
    except Exception:
        return False


def _detect_generated_surfaces(
    root: Path,
    all_walked_files: list,
    skip_set: set,
    file_heads: dict = None,
    file_stats: dict = None,
) -> list:
    """Detect generated API surface files in a single O(n) pass.

    Uses the file list already collected by scan_repo() — no additional
    directory traversal.  file_heads (rel→lowercase head text) and
    file_stats (rel→line count) eliminate secondary file opens for the
    first-line marker check and LOC lookup.
    """
    import re as _re

    if file_heads is None:
        file_heads = {}
    if file_stats is None:
        file_stats = {}

    FIRST_LINE_MARKERS = [
        ('DO NOT EDIT', 'first-line-marker'),
        ('auto-generated', 'first-line-marker'),
        ('Code generated by', 'first-line-marker'),
        ('// @generated', 'first-line-marker'),
        ('# This file was automatically generated', 'first-line-marker'),
    ]

    # Filename-only suffix extracted from '**/<pattern>' globs — matched
    # with fnmatch against just the filename, avoiding full-tree glob calls.
    GENERATED_GLOB_SUFFIXES = [
        ('*.pb.ts',        'protobuf',           '**/*.pb.ts'),
        ('*.pb.go',        'protobuf',           '**/*.pb.go'),
        ('*_pb2.py',       'protobuf',           '**/*_pb2.py'),
        ('*_pb2_grpc.py',  'protobuf',           '**/*_pb2_grpc.py'),
        ('*_grpc.py',      'protobuf',           '**/*_grpc.py'),
        ('*.generated.ts', 'Angular-schematics', '**/*.generated.ts'),
        ('*.generated.cs', 'other',              '**/*.generated.cs'),
    ]

    MIGRATION_PATTERNS = [
        r'^\d{4}_\d{2}_\d{2}',
        r'^\d{14}_',
        r'^V\d+__',
        r'^\d+_',
    ]

    SOURCE_EXTS_MARKER = {'.ts', '.tsx', '.js', '.py', '.go', '.cs', '.java', '.kt', '.rb', '.php'}

    surfaces = []
    seen_paths = set()

    def grep_endpoints(fpath):
        endpoints = []
        patterns = [
            r'this\.http\.(get|post|put|delete|patch)\(',
            r'func\s+\(s \*\w+\)\s+\w+\(',
            r'def\s+\w+\(self',
            r'rpc\s+\w+\s*\(',
            r'@(Get|Post|Put|Delete|Patch)Mapping',
        ]
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    for pat in patterns:
                        if _re.search(pat, line):
                            endpoints.append(line.strip()[:120])
                            break
                    if len(endpoints) >= 20:
                        break
        except Exception:
            pass
        return endpoints

    # Single pass over the pre-walked file list — no os.walk / rglob / glob.
    for fpath, rel in all_walked_files:
        if len(surfaces) >= 200:
            break

        fname = os.path.basename(fpath)
        fname_lower = fname.lower()
        rel_posix = rel.replace('\\', '/')

        if rel_posix in seen_paths:
            continue

        rel_parts = Path(rel_posix).parts
        ext = os.path.splitext(fname)[1].lower()
        added = False

        # 1. nswag.json → NSwag/OpenAPI config
        if fname_lower == 'nswag.json':
            seen_paths.add(rel_posix)
            surfaces.append({
                'path': rel_posix,
                'generator_hint': 'NSwag/OpenAPI',
                'source_spec': None,
                'endpoints': [],
                'loc': 0,
                'note': 'nswag.json config file — generated TypeScript clients in same directory',
            })
            added = True

        # 2. Filename glob patterns (protobuf, Angular schematics, etc.)
        if not added:
            for suffix, hint, pattern in GENERATED_GLOB_SUFFIXES:
                if fnmatch.fnmatch(fname_lower, suffix):
                    seen_paths.add(rel_posix)
                    surfaces.append({
                        'path': rel_posix,
                        'generator_hint': hint,
                        'source_spec': None,
                        'endpoints': grep_endpoints(fpath),
                        'loc': file_stats.get(rel, 0),
                        'note': f'Pattern match: {pattern}',
                    })
                    added = True
                    break

        # 3. __generated__ directory (GraphQL-codegen output)
        if not added and '__generated__' in rel_parts:
            seen_paths.add(rel_posix)
            surfaces.append({
                'path': rel_posix,
                'generator_hint': 'GraphQL-codegen',
                'source_spec': None,
                'endpoints': grep_endpoints(fpath),
                'loc': file_stats.get(rel, 0),
                'note': 'Found in __generated__/ directory',
            })
            added = True

        # 4. First-line generated markers (source files only)
        #    Use pre-cached head from main walk — no file open needed.
        if not added and ext in SOURCE_EXTS_MARKER:
            head = file_heads.get(rel)
            if head is None:
                # Fallback for files not collected during the main walk.
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                        head = fh.read(300).lower()
                except Exception:
                    head = ''
            for marker, hint in FIRST_LINE_MARKERS:
                if marker.lower() in head:
                    seen_paths.add(rel_posix)
                    surfaces.append({
                        'path': rel_posix,
                        'generator_hint': hint,
                        'source_spec': None,
                        'endpoints': grep_endpoints(fpath),
                        'loc': file_stats.get(rel, 0),
                        'note': 'First-line generated marker detected',
                    })
                    added = True
                    break

        # 5. ORM migration files (timestamped filenames inside migrations/ dirs)
        if not added and 'migrations' in rel_parts:
            if any(_re.match(pat, fname) for pat in MIGRATION_PATTERNS):
                seen_paths.add(rel_posix)
                surfaces.append({
                    'path': rel_posix,
                    'generator_hint': 'ORM-migration',
                    'source_spec': None,
                    'endpoints': [],
                    'loc': file_stats.get(rel, 0),
                    'note': 'Timestamped migration file',
                })

    return surfaces


def _get_git_info(repo_path: str) -> dict:
    info = {'recent_commits': [], 'branch_count': 0}
    try:
        result = subprocess.run(
            ['git', '-C', repo_path, 'log', '--oneline', '-5'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            commits = [line.split(' ', 1)[1] if ' ' in line else line
                       for line in result.stdout.strip().splitlines()]
            info['recent_commits'] = [c[:100] for c in commits]
    except Exception:
        pass
    try:
        result = subprocess.run(
            ['git', '-C', repo_path, 'branch', '-a'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info['branch_count'] = len([l for l in result.stdout.splitlines() if l.strip()])
    except Exception:
        pass
    return info


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: scan_repo.py <repo_path> [--exclude DIR1,DIR2,...] [--output-generated-surfaces PATH]', file=sys.stderr)
        sys.exit(1)

    generated_surfaces_out = None
    extra_exclude: set = set()
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '--output-generated-surfaces' and i + 1 < len(args):
            generated_surfaces_out = args[i + 1]
            i += 2
        elif args[i] == '--exclude' and i + 1 < len(args):
            extra_exclude = {d.strip() for d in args[i + 1].split(',')}
            i += 2
        else:
            i += 1

    output = scan_repo(sys.argv[1], extra_exclude=extra_exclude)

    if generated_surfaces_out:
        surfaces = output.pop('_generated_api_surfaces', [])
        Path(generated_surfaces_out).write_text(json.dumps(surfaces, indent=2), encoding='utf-8')
        print(f'Wrote generated surfaces ({len(surfaces)} entries) to {generated_surfaces_out}', file=sys.stderr)
    else:
        output.pop('_generated_api_surfaces', None)

    print(json.dumps(output, indent=2))
