#!/usr/bin/env python3
"""scan_repo.py — Repo structure scanner. Budget: ~800 tokens output."""

import os
import sys
import json
import subprocess
from pathlib import Path

SKIP_DIRS = {
    'node_modules', '.git', 'vendor', 'dist', 'build', '__pycache__',
    '.next', 'target', '.venv', 'venv', '.tox', 'coverage',
    '.nyc_output', '.cache', '.idea', '.vscode'
}

FILE_SMALL = 500
FILE_MEDIUM = 3000
FILE_LARGE = 10000


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def is_skipped_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith('.')


def count_lines(path: str) -> int:
    try:
        with open(path, 'rb') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def max_line_length(path: str) -> int:
    try:
        with open(path, 'rb') as f:
            return max((len(line) for line in f), default=0)
    except Exception:
        return 0


def scan_repo(repo_path: str) -> dict:
    root = Path(repo_path).resolve()
    name = root.name

    total_files = 0
    total_loc = 0
    file_counts_by_ext = {}
    files_by_size = {'small': 0, 'medium': 0, 'large': 0, 'xlarge': 0, 'mega': 0}
    mega_files = []
    skip_candidates = []
    top_dirs = []
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
        if item.is_dir() and not is_skipped_dir(item.name):
            top_dirs.append(item.name + '/')
            dir_entry_count += 1
            seen_dirs.add(item.name)
            # Level 2
            try:
                for sub in sorted(item.iterdir()):
                    if dir_entry_count >= 30:
                        break
                    if sub.is_dir() and not is_skipped_dir(sub.name):
                        top_dirs.append(item.name + '/' + sub.name + '/')
                        dir_entry_count += 1
            except PermissionError:
                pass

    # Walk repo
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not is_skipped_dir(d)]
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, root)
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
            if ext:
                file_counts_by_ext[ext] = file_counts_by_ext.get(ext, 0) + 1

            # Line count + size tier
            try:
                lines = count_lines(fpath)
                total_loc += lines

                # Minified detection
                if lines < 5 and max_line_length(fpath) > 1000:
                    skip_candidates.append(rel[:200])

                if lines < FILE_SMALL:
                    files_by_size['small'] += 1
                elif lines < FILE_MEDIUM:
                    files_by_size['medium'] += 1
                elif lines < FILE_LARGE:
                    files_by_size['large'] += 1
                    files_by_size['xlarge'] += 0  # not xlarge
                elif lines < 10000:
                    files_by_size['xlarge'] += 1
                else:
                    files_by_size['mega'] += 1
                    mega_files.append({
                        'path': rel[:200],
                        'lines': lines,
                        'likely_generated': _is_likely_generated(fpath)
                    })
                    skip_candidates.append(rel[:200])
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

    result = {
        'meta': {
            'name': name,
            'total_files': total_files,
            'total_loc': total_loc
        },
        'top_dirs': top_dirs[:30],
        'key_files': key_files,
        'file_counts_by_ext': file_counts_by_ext,
        'files_by_size': files_by_size,
        'mega_files': mega_files[:10],
        'skip_candidates': list(set(skip_candidates))[:20],
        'readme_excerpt': readme_excerpt,
        'git_info': git_info,
        '_token_estimate': 0
    }

    output_str = json.dumps(result)
    result['_token_estimate'] = estimate_tokens(output_str)
    return result


def _is_likely_generated(fpath: str) -> bool:
    markers = ('generated', 'auto-generated', 'do not edit', 'autogenerated')
    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            head = f.read(500).lower()
            return any(m in head for m in markers)
    except Exception:
        return False


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
        print('Usage: scan_repo.py <repo_path>', file=sys.stderr)
        sys.exit(1)
    output = scan_repo(sys.argv[1])
    print(json.dumps(output, indent=2))
