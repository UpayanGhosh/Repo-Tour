#!/usr/bin/env python3
"""map_dependencies.py — Dependency graph + classification + scoring. Budget: ~1500 tokens output."""

import os
import sys
import json
import re
from pathlib import Path
from collections import defaultdict

SKIP_DIRS = {
    'node_modules', '.git', 'vendor', 'dist', 'build', '__pycache__',
    '.next', 'target', '.venv', 'venv', '.tox', 'coverage',
    '.nyc_output', '.cache'
}

SKIP_EXTS = {'.json', '.lock', '.md', '.txt', '.yaml', '.yml', '.toml',
             '.css', '.scss', '.less', '.html', '.svg', '.png', '.jpg',
             '.jpeg', '.gif', '.ico', '.woff', '.woff2', '.ttf', '.eot'}

ROLE_PATTERNS = {
    'test': [r'test', r'spec', r'__test__', r'__mock__'],
    'config': [r'config', r'settings', r'\.env', r'env\.'],
    'migration': [r'migrat', r'schema.*change'],
    'route': [r'route', r'router', r'routing'],
    'controller': [r'controller', r'handler', r'resolver'],
    'model': [r'model', r'entity', r'schema', r'types?\.'],
    'service': [r'service', r'usecase', r'use_case', r'business'],
    'middleware': [r'middleware', r'interceptor', r'guard'],
    'utility': [r'util', r'helper', r'common', r'shared', r'lib'],
    'static_asset': [r'\.(css|scss|less|svg|png|jpg|gif)$'],
    'documentation': [r'\.md$', r'\.rst$', r'\.txt$'],
    'build': [r'webpack|rollup|vite|esbuild|babel|tsconfig'],
    'ci_cd': [r'\.github', r'\.travis', r'\.circleci', r'jenkins'],
    'type_definition': [r'\.d\.ts$', r'types?/', r'interfaces?/'],
}

IMPORT_PATTERNS = {
    'TypeScript': [
        r'''from\s+['"]([^'"]+)['"]''',
        r'''require\s*\(\s*['"]([^'"]+)['"]\s*\)'''
    ],
    'JavaScript': [
        r'''from\s+['"]([^'"]+)['"]''',
        r'''require\s*\(\s*['"]([^'"]+)['"]\s*\)'''
    ],
    'Python': [
        r'''from\s+([\w.]+)\s+import''',
        r'''import\s+([\w.]+)'''
    ],
    'Go': [
        r'''"([^"]+)"'''
    ],
    'Rust': [
        r'''use\s+([\w:]+)''',
        r'''mod\s+(\w+)'''
    ],
    'Java': [
        r'''import\s+([\w.]+);'''
    ],
    'C#': [
        r'''using\s+([\w.]+);'''
    ],
}


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def count_lines(path: str) -> int:
    try:
        with open(path, 'rb') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def classify_role(rel_path: str, content_head: str = '') -> str:
    p = rel_path.lower().replace('\\', '/')
    for role, patterns in ROLE_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, p, re.IGNORECASE):
                return role
    return 'service'


def estimate_complexity(loc: int, imports: list, exports_count: int, content: str) -> float:
    # Nesting depth: count indentation levels
    lines = content.split('\n')
    max_depth = 0
    for line in lines[:200]:
        stripped = line.lstrip()
        if stripped:
            depth = (len(line) - len(stripped)) // 2
            max_depth = max(max_depth, depth)
    nesting = min(max_depth, 8)

    score = loc * 1.0 + len(imports) * 0.5 + exports_count * 0.3 + nesting * 0.2
    # Normalize to 0-10 scale: assume max around 500 LOC + 20 imports + 15 exports
    max_score = 500 + 20 * 0.5 + 15 * 0.3 + 8 * 0.2
    return round(min(10.0, score / max_score * 10), 1)


def parse_imports(content: str, language: str, rel_path: str, root: Path) -> list:
    patterns = IMPORT_PATTERNS.get(language, IMPORT_PATTERNS['JavaScript'])
    raw_imports = []
    for pat in patterns:
        raw_imports.extend(re.findall(pat, content[:5000]))

    resolved = []
    for imp in raw_imports:
        if imp.startswith('.'):
            # Relative import — resolve to path
            base = (root / rel_path).parent / imp
            # Try common extensions
            for ext in ('.ts', '.tsx', '.js', '.jsx', '.py', '.go', '.rs'):
                candidate = Path(str(base) + ext)
                if candidate.exists():
                    resolved.append(os.path.relpath(str(candidate), str(root)).replace('\\', '/'))
                    break
            else:
                resolved.append(imp)
        elif not imp.startswith('/') and '/' not in imp and '.' not in imp:
            # Internal package (Go/Python style)
            resolved.append(imp[:100])
        # Skip external packages (no path separator in npm-style, no . in Go pkg, etc.)
    return list(set(resolved))[:20]


def count_exports(content: str, language: str) -> int:
    patterns = {
        'TypeScript': r'export\s+(default\s+)?(function|class|const|let|var|interface|type|enum)\s+',
        'JavaScript': r'export\s+(default\s+)?(function|class|const|let|var)\s+',
        'Python': r'^def\s+\w+|^class\s+\w+',
        'Go': r'^func\s+[A-Z]\w+',
        'Rust': r'^pub\s+(fn|struct|enum|trait|impl)\s+',
        'Java': r'public\s+(static\s+)?(class|interface|enum|void|\w+)\s+\w+',
        'C#': r'public\s+(static\s+)?(class|interface|enum|void|\w+)\s+\w+',
    }
    pat = patterns.get(language, patterns['JavaScript'])
    return len(re.findall(pat, content, re.MULTILINE))


def determine_read_tier(loc: int) -> str:
    if loc < 500:
        return 'direct'
    elif loc < 3000:
        return 'strategic'
    elif loc < 10000:
        return 'skeleton'
    return 'metadata'


def map_dependencies(repo_path: str, language: str = None, max_modules: int = 15) -> dict:
    root = Path(repo_path).resolve()

    # Auto-detect language if not provided
    if not language:
        if (root / 'package.json').exists():
            language = 'TypeScript' if (root / 'tsconfig.json').exists() else 'JavaScript'
        elif (root / 'go.mod').exists():
            language = 'Go'
        elif (root / 'Cargo.toml').exists():
            language = 'Rust'
        elif list(root.rglob('*.csproj')):
            language = 'C#'
        elif any((root / f).exists() for f in ['requirements.txt', 'pyproject.toml', 'setup.py']):
            language = 'Python'
        elif any((root / f).exists() for f in ['pom.xml', 'build.gradle']):
            language = 'Java'
        else:
            language = 'JavaScript'

    ext_map = {
        'TypeScript': ['.ts', '.tsx'],
        'JavaScript': ['.js', '.jsx', '.mjs'],
        'Python': ['.py'],
        'Go': ['.go'],
        'Rust': ['.rs'],
        'Java': ['.java'],
        'Kotlin': ['.kt'],
        'C#': ['.cs'],
        'Ruby': ['.rb'],
        'PHP': ['.php'],
    }
    valid_exts = ext_map.get(language, ['.js', '.ts', '.py'])

    modules = {}

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext not in valid_exts:
                continue
            fpath = Path(dirpath) / fname
            rel = os.path.relpath(str(fpath), str(root)).replace('\\', '/')

            # Skip test / config / generated files
            role = classify_role(rel)
            if role in ('test', 'config', 'static_asset', 'documentation',
                        'build', 'ci_cd', 'type_definition', 'migration'):
                continue

            loc = count_lines(str(fpath))
            if loc < 50:
                continue

            try:
                content = fpath.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                content = ''

            imports = parse_imports(content, language, rel, root)
            exports = count_exports(content, language)
            complexity = estimate_complexity(loc, imports, exports, content[:3000])

            modules[rel] = {
                'path': rel,
                'imports': imports,
                'imported_by': [],
                'role': role,
                'loc': loc,
                'complexity': complexity,
                'read_tier': determine_read_tier(loc)
            }

    # Build imported_by relationships
    for path, mod in modules.items():
        for imp in mod['imports']:
            if imp in modules:
                modules[imp]['imported_by'].append(path)

    # Sort by complexity descending, cap at max_modules
    sorted_modules = sorted(modules.values(), key=lambda m: -m['complexity'])
    critical = sorted_modules[:max_modules]

    # Trim imports/imported_by lists
    for m in critical:
        m['imports'] = m['imports'][:10]
        m['imported_by'] = m['imported_by'][:10]

    # Detect clusters
    clusters = _detect_clusters(critical)

    # External deps from package files
    external_deps = _get_external_deps(root, language)

    # Circular warnings (simple detection)
    circular_warnings = _find_circular(modules)

    result = {
        'critical_modules': critical,
        'clusters': clusters,
        'external_deps_top10': external_deps[:10],
        'circular_warnings': circular_warnings[:5],
        '_token_estimate': 0
    }

    output_str = json.dumps(result)
    result['_token_estimate'] = estimate_tokens(output_str)
    return result


def _detect_clusters(modules: list) -> list:
    """Group modules into clusters based on shared directory prefixes."""
    prefix_groups = defaultdict(list)
    for m in modules:
        parts = m['path'].split('/')
        # Use directory path (exclude filename), max 2 levels deep
        dir_parts = parts[:-1]  # strip filename
        if len(dir_parts) >= 2:
            prefix = dir_parts[0] + '/' + dir_parts[1]
        elif len(dir_parts) == 1:
            prefix = dir_parts[0]
        else:
            prefix = 'root'
        prefix_groups[prefix].append(m['path'])

    clusters = []
    for prefix, files in sorted(prefix_groups.items(), key=lambda x: -len(x[1])):
        if len(files) >= 2:
            name = prefix.split('/')[-1].replace('-', ' ').replace('_', ' ').title()
            clusters.append({'name': name + ' System', 'files': files[:10]})
        if len(clusters) >= 6:
            break

    return clusters


def _get_external_deps(root: Path, language: str) -> list:
    deps = []
    PURPOSE_MAP = {
        'express': 'http-server', 'fastify': 'http-server', 'koa': 'http-server',
        'next': 'full-stack-framework', 'react': 'ui-library', 'vue': 'ui-library',
        'prisma': 'orm', 'mongoose': 'odm', 'sequelize': 'orm', 'typeorm': 'orm',
        'jest': 'testing', 'vitest': 'testing', 'mocha': 'testing',
        'winston': 'logging', 'pino': 'logging', 'bunyan': 'logging',
        'axios': 'http-client', 'node-fetch': 'http-client', 'got': 'http-client',
        'zod': 'validation', 'joi': 'validation', 'yup': 'validation',
        'jsonwebtoken': 'auth', 'passport': 'auth', 'bcrypt': 'crypto',
        'redis': 'cache', 'ioredis': 'cache',
        'bull': 'queue', 'bullmq': 'queue', 'agenda': 'scheduler',
        'stripe': 'payments', 'twilio': 'messaging',
        'dotenv': 'config', 'config': 'config', 'convict': 'config',
        'lodash': 'utility', 'ramda': 'utility', 'dayjs': 'date', 'luxon': 'date',
        'socket.io': 'websocket', 'ws': 'websocket',
        'graphql': 'api-layer', 'apollo-server': 'api-layer',
        'swagger': 'api-docs', 'openapi': 'api-docs',
        'django': 'web-framework', 'flask': 'web-framework', 'fastapi': 'web-framework',
        'sqlalchemy': 'orm', 'alembic': 'migrations', 'celery': 'task-queue',
        'pytest': 'testing', 'pydantic': 'validation',
        'gin': 'http-server', 'echo': 'http-server', 'fiber': 'http-server',
        'actix-web': 'http-server', 'axum': 'http-server', 'rocket': 'http-server',
        'serde': 'serialization', 'tokio': 'async-runtime',
    }

    pkg = root / 'package.json'
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding='utf-8', errors='ignore'))
            for name in list(data.get('dependencies', {}).keys())[:20]:
                clean = name.lstrip('@').split('/')[0] if name.startswith('@') else name
                purpose = PURPOSE_MAP.get(clean, PURPOSE_MAP.get(name, 'library'))
                deps.append({'name': name[:50], 'purpose': purpose})
        except Exception:
            pass

    req = root / 'requirements.txt'
    if req.exists():
        try:
            for line in req.read_text(encoding='utf-8', errors='ignore').splitlines():
                name = re.split(r'[>=<!]', line)[0].strip().lower()
                if name and not name.startswith('#'):
                    purpose = PURPOSE_MAP.get(name, 'library')
                    deps.append({'name': name[:50], 'purpose': purpose})
        except Exception:
            pass

    return deps[:10]


def _find_circular(modules: dict) -> list:
    """Simple circular dependency detection via DFS."""
    warnings = []
    visited = set()
    rec_stack = set()

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        for imp in modules.get(node, {}).get('imports', []):
            if imp not in modules:
                continue
            if imp not in visited:
                dfs(imp, path + [imp])
            elif imp in rec_stack:
                cycle = path[path.index(imp):]
                warnings.append(' -> '.join(cycle[:5]))

    for node in list(modules.keys())[:50]:
        if node not in visited:
            dfs(node, [node])
        if len(warnings) >= 5:
            break

    return list(set(warnings))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: map_dependencies.py <repo_path> [--language LANG] [--max-modules N]', file=sys.stderr)
        sys.exit(1)

    lang = None
    max_mods = 15
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '--language' and i + 1 < len(args):
            lang = args[i + 1]
            i += 2
        elif args[i] == '--max-modules' and i + 1 < len(args):
            max_mods = int(args[i + 1])
            i += 2
        else:
            i += 1

    output = map_dependencies(sys.argv[1], lang, max_mods)
    print(json.dumps(output, indent=2))
