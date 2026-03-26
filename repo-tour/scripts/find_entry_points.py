#!/usr/bin/env python3
"""find_entry_points.py — Entry point finder. Budget: ~500 tokens output."""

import os
import sys
import json
import re
from pathlib import Path

SKIP_DIRS = {
    'node_modules', '.git', 'vendor', 'dist', 'build', '__pycache__',
    '.next', 'target', '.venv', 'venv', '.tox', 'coverage',
    '.nyc_output', '.cache'
}

ENTRY_TYPES = {
    'server_start', 'app_root', 'route_root', 'cli_entry',
    'background', 'test_runner'
}


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def find_entry_points(repo_path: str, stack_json: dict = None) -> dict:
    root = Path(repo_path).resolve()
    language = 'Unknown'
    framework = None

    if stack_json:
        s = stack_json.get('stack', {})
        language = s.get('primary_language', 'Unknown')
        framework = s.get('framework')

    candidates = []

    # Known entry point filenames by language
    entry_names = {
        'TypeScript': ['index.ts', 'main.ts', 'server.ts', 'app.ts', 'cli.ts'],
        'JavaScript': ['index.js', 'main.js', 'server.js', 'app.js', 'cli.js'],
        'Python': ['main.py', 'app.py', 'manage.py', 'run.py', 'wsgi.py', 'asgi.py', 'cli.py', '__main__.py'],
        'Go': ['main.go'],
        'Rust': ['main.rs'],
        'Java': ['Application.java', 'Main.java', 'App.java'],
        'Kotlin': ['Application.kt', 'Main.kt', 'App.kt'],
        'C#': ['Program.cs', 'Startup.cs'],
        'Ruby': ['config.ru', 'app.rb', 'server.rb'],
        'PHP': ['index.php', 'public/index.php', 'artisan'],
    }

    # Procfile detection
    procfile = root / 'Procfile'
    if procfile.exists():
        try:
            content = procfile.read_text(encoding='utf-8', errors='ignore')
            for line in content.splitlines():
                if ':' in line:
                    proc_type, cmd = line.split(':', 1)
                    candidates.append({
                        'file': 'Procfile',
                        'type': 'server_start',
                        'hint': f'{proc_type.strip()}: {cmd.strip()[:100]}'
                    })
        except Exception:
            pass

    # package.json scripts
    pkg = root / 'package.json'
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding='utf-8', errors='ignore'))
            scripts = data.get('scripts', {})
            main_field = data.get('main', '')
            if main_field:
                candidates.append({
                    'file': main_field[:200],
                    'type': 'app_root',
                    'hint': 'package.json "main" field'
                })
            for script_name in ('start', 'dev', 'serve'):
                if script_name in scripts:
                    candidates.append({
                        'file': 'package.json',
                        'type': 'server_start',
                        'hint': f'npm {script_name}: {scripts[script_name][:100]}'
                    })
                    break
        except Exception:
            pass

    # Makefile targets
    makefile = root / 'Makefile'
    if makefile.exists():
        try:
            content = makefile.read_text(encoding='utf-8', errors='ignore')
            run_targets = re.findall(r'^(run|start|serve|dev)\s*:', content, re.MULTILINE)
            if run_targets:
                candidates.append({
                    'file': 'Makefile',
                    'type': 'server_start',
                    'hint': f'make {run_targets[0]}'
                })
        except Exception:
            pass

    # Scan for entry point files
    names_to_check = entry_names.get(language, [])
    if not names_to_check:
        # Fallback: common across all
        names_to_check = ['index.js', 'index.ts', 'main.py', 'main.go', 'main.rs', 'index.php']

    found_paths = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        rel_dir = os.path.relpath(dirpath, root)
        depth = len(Path(rel_dir).parts)
        if depth > 4:
            continue
        for fname in filenames:
            if fname in names_to_check:
                fpath = Path(dirpath) / fname
                rel = os.path.relpath(str(fpath), str(root))
                if rel not in found_paths:
                    found_paths.add(rel)
                    entry_type, hint = _classify_entry(str(fpath), language, framework)
                    candidates.append({
                        'file': rel.replace('\\', '/'),
                        'type': entry_type,
                        'hint': hint
                    })

    # Route root detection: files with 'routes' or 'router' in name or path
    route_patterns = re.compile(r'(routes?|router|routing)', re.IGNORECASE)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        for fname in filenames:
            if route_patterns.search(fname) and _is_code_file(fname, language):
                fpath = Path(dirpath) / fname
                rel = os.path.relpath(str(fpath), str(root)).replace('\\', '/')
                if rel not in found_paths:
                    found_paths.add(rel)
                    candidates.append({
                        'file': rel,
                        'type': 'route_root',
                        'hint': 'Route configuration file'
                    })

    # Background worker detection
    worker_patterns = re.compile(r'(worker|queue|job|task|scheduler|cron)', re.IGNORECASE)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        for fname in filenames:
            if worker_patterns.search(fname) and _is_code_file(fname, language):
                fpath = Path(dirpath) / fname
                rel = os.path.relpath(str(fpath), str(root)).replace('\\', '/')
                if rel not in found_paths:
                    found_paths.add(rel)
                    candidates.append({
                        'file': rel,
                        'type': 'background',
                        'hint': 'Background worker or queue processor'
                    })

    # CLI detection
    cli_patterns = re.compile(r'^(cli|cmd|command|bin)', re.IGNORECASE)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        for fname in filenames:
            if cli_patterns.search(fname) and _is_code_file(fname, language):
                fpath = Path(dirpath) / fname
                rel = os.path.relpath(str(fpath), str(root)).replace('\\', '/')
                if rel not in found_paths:
                    found_paths.add(rel)
                    candidates.append({
                        'file': rel,
                        'type': 'cli_entry',
                        'hint': 'CLI entry point'
                    })

    # Python: scan for files with if __name__ == '__main__'
    if language == 'Python':
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
            for fname in filenames:
                if not fname.endswith('.py'):
                    continue
                fpath = Path(dirpath) / fname
                rel = os.path.relpath(str(fpath), str(root)).replace('\\', '/')
                if rel in found_paths:
                    continue
                try:
                    content = fpath.read_text(encoding='utf-8', errors='ignore')
                    if re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]', content):
                        found_paths.add(rel)
                        entry_type, hint = _classify_entry(str(fpath), language, framework)
                        candidates.append({'file': rel, 'type': entry_type, 'hint': hint})
                except Exception:
                    pass

    # Deduplicate and cap at 10
    seen = set()
    unique = []
    for c in candidates:
        key = c['file']
        if key not in seen:
            seen.add(key)
            unique.append(c)
        if len(unique) >= 10:
            break

    result = {'entry_points': unique, '_token_estimate': 0}
    output_str = json.dumps(result)
    result['_token_estimate'] = estimate_tokens(output_str)
    return result


def _classify_entry(fpath: str, language: str, framework: str) -> tuple:
    try:
        content = Path(fpath).read_text(encoding='utf-8', errors='ignore')[:2000]
    except Exception:
        return 'app_root', 'Entry point file'

    fname = Path(fpath).name.lower()

    # Server start patterns
    server_patterns = [
        (r'app\.listen\s*\(', 'Express app.listen'),
        (r'uvicorn\.run|app\.run\s*\(', 'ASGI/WSGI server start'),
        (r'http\.ListenAndServe', 'Go HTTP server'),
        (r'HttpServer::new|HttpServer::bind', 'Rust HTTP server'),
        (r'ApplicationContext\.run|SpringApplication\.run', 'Spring Boot startup'),
        (r'\.run\(\s*host', 'FastAPI/Flask server start'),
        (r'createServer|fastify\(\)', 'Node.js server'),
    ]
    for pattern, hint in server_patterns:
        if re.search(pattern, content):
            return 'server_start', hint

    # CLI patterns
    if re.search(r'click\.|typer\.|argparse\.|commander\.|yargs\.|clap::', content):
        return 'cli_entry', 'CLI argument parsing'

    if fname == 'manage.py':
        return 'cli_entry', 'Django management commands'

    # Background patterns
    if re.search(r'celery|bull|sidekiq|resque|queue\.|worker\.|cron', content, re.IGNORECASE):
        return 'background', 'Background task processor'

    # Route root
    if re.search(r'router\.|Router\(|routes\.|createRouter|@Controller|@Route', content):
        return 'route_root', 'Router/route configuration'

    return 'app_root', 'Application entry point'


def _is_code_file(fname: str, language: str) -> bool:
    ext = Path(fname).suffix.lower()
    code_exts = {
        'TypeScript': ['.ts', '.tsx'],
        'JavaScript': ['.js', '.jsx', '.mjs', '.cjs'],
        'Python': ['.py'],
        'Go': ['.go'],
        'Rust': ['.rs'],
        'Java': ['.java'],
        'Kotlin': ['.kt'],
        'C#': ['.cs'],
        'Ruby': ['.rb'],
        'PHP': ['.php'],
    }
    valid_exts = code_exts.get(language, ['.js', '.ts', '.py', '.go', '.rs', '.java'])
    return ext in valid_exts


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: find_entry_points.py <repo_path> [stack.json]', file=sys.stderr)
        sys.exit(1)
    stack = None
    if len(sys.argv) >= 3:
        try:
            stack = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
        except Exception:
            pass
    output = find_entry_points(sys.argv[1], stack)
    print(json.dumps(output, indent=2))
