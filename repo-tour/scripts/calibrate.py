#!/usr/bin/env python3
"""calibrate.py — Token budget calibration tool. Runs all Phase 1 scripts and reports results."""

import sys
import json
import subprocess
import tempfile
import os
from pathlib import Path

BUDGETS = {
    'scan_repo': 800,
    'detect_stack': 400,
    'find_entry_points': 500,
    'map_dependencies': 1500,
    'merge_analysis': 3500,
}

SCRIPTS_DIR = Path(__file__).parent


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def run_script(script_name: str, args: list) -> tuple:
    """Returns (stdout, stderr, returncode)."""
    script_path = SCRIPTS_DIR / f'{script_name}.py'
    cmd = [sys.executable, str(script_path)] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return '', 'TIMEOUT', 1
    except Exception as e:
        return '', str(e), 1


def calibrate(repo_path: str):
    repo_path = os.path.abspath(repo_path)
    print(f'\n=== RepoTour Calibration Report ===')
    print(f'Repo: {repo_path}\n')

    results = {}
    tmp_files = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        # --- scan_repo ---
        print('Running scan_repo.py...')
        stdout, stderr, rc = run_script('scan_repo', [repo_path])
        _report('scan_repo', stdout, stderr, rc, BUDGETS['scan_repo'], results)
        scan_file = os.path.join(tmpdir, 'scan.json')
        if rc == 0:
            Path(scan_file).write_text(stdout, encoding='utf-8')
            tmp_files['scan'] = scan_file

        # --- detect_stack ---
        print('Running detect_stack.py...')
        stdout, stderr, rc = run_script('detect_stack', [repo_path])
        _report('detect_stack', stdout, stderr, rc, BUDGETS['detect_stack'], results)
        stack_file = os.path.join(tmpdir, 'stack.json')
        if rc == 0:
            Path(stack_file).write_text(stdout, encoding='utf-8')
            tmp_files['stack'] = stack_file

        # --- find_entry_points ---
        print('Running find_entry_points.py...')
        ep_args = [repo_path]
        if 'stack' in tmp_files:
            ep_args.append(tmp_files['stack'])
        stdout, stderr, rc = run_script('find_entry_points', ep_args)
        _report('find_entry_points', stdout, stderr, rc, BUDGETS['find_entry_points'], results)
        entries_file = os.path.join(tmpdir, 'entries.json')
        if rc == 0:
            Path(entries_file).write_text(stdout, encoding='utf-8')
            tmp_files['entries'] = entries_file

        # --- map_dependencies ---
        print('Running map_dependencies.py...')
        lang = None
        if 'stack' in tmp_files:
            try:
                stack_data = json.loads(Path(tmp_files['stack']).read_text(encoding='utf-8'))
                lang = stack_data.get('stack', {}).get('primary_language')
            except Exception:
                pass

        dep_args = [repo_path]
        if lang:
            dep_args += ['--language', lang]
        stdout, stderr, rc = run_script('map_dependencies', dep_args)
        _report('map_dependencies', stdout, stderr, rc, BUDGETS['map_dependencies'], results)
        deps_file = os.path.join(tmpdir, 'deps.json')
        if rc == 0:
            Path(deps_file).write_text(stdout, encoding='utf-8')
            tmp_files['deps'] = deps_file

        # --- merge_analysis ---
        print('Running merge_analysis.py...')
        merge_args = []
        for flag, key in [('--scan', 'scan'), ('--stack', 'stack'),
                           ('--entries', 'entries'), ('--deps', 'deps')]:
            if key in tmp_files:
                merge_args += [flag, tmp_files[key]]

        stdout, stderr, rc = run_script('merge_analysis', merge_args)
        _report('merge_analysis', stdout, stderr, rc, BUDGETS['merge_analysis'], results)

        # --- Summary ---
        print('\n=== Summary ===')
        all_pass = True
        for script, info in results.items():
            status = 'PASS' if info['within_budget'] and info['success'] else 'FAIL'
            if status == 'FAIL':
                all_pass = False
            tokens = info.get('tokens', 0)
            budget = info.get('budget', 0)
            print(f'  {status:4} {script:25} {tokens:5} tokens / {budget} budget ({info.get("chars", 0)} chars)')

        print(f'\nOverall: {"ALL PASS" if all_pass else "SOME FAILURES"}')
        print('===================================\n')

        return results


def _report(name: str, stdout: str, stderr: str, rc: int, budget: int, results: dict):
    success = rc == 0
    tokens = estimate_tokens(stdout) if success else 0
    chars = len(stdout) if success else 0
    within_budget = success and tokens <= budget

    results[name] = {
        'success': success,
        'tokens': tokens,
        'chars': chars,
        'budget': budget,
        'within_budget': within_budget,
        'error': stderr[:200] if not success else None
    }

    status = 'OK' if within_budget else ('ERROR' if not success else 'OVER BUDGET')
    print(f'  [{status}] {tokens} tokens ({chars} chars) — budget: {budget}')
    if stderr and not success:
        print(f'  Stderr: {stderr[:200]}')

    # Validate JSON
    if success:
        try:
            json.loads(stdout)
        except json.JSONDecodeError as e:
            print(f'  WARNING: Invalid JSON output: {e}')
            results[name]['valid_json'] = False
        else:
            results[name]['valid_json'] = True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: calibrate.py <repo_path>', file=sys.stderr)
        sys.exit(1)
    calibrate(sys.argv[1])
