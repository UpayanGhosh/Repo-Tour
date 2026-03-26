#!/usr/bin/env python3
"""detect_stack.py — Tech stack detection. Budget: ~400 tokens output."""

import os
import sys
import json
import re
from pathlib import Path


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def detect_stack(repo_path: str) -> dict:
    root = Path(repo_path).resolve()
    stack = {
        'primary_language': 'Unknown',
        'framework': None,
        'runtime': None,
        'database': None,
        'test_framework': None,
        'build_tool': None,
        'ci': None,
        'package_manager': None,
        'dep_count': {'prod': 0, 'dev': 0}
    }

    # --- JavaScript / TypeScript ---
    pkg = root / 'package.json'
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding='utf-8', errors='ignore'))
        except Exception:
            data = {}

        deps = data.get('dependencies', {})
        dev_deps = data.get('devDependencies', {})
        stack['dep_count'] = {'prod': len(deps), 'dev': len(dev_deps)}
        all_deps = {**deps, **dev_deps}
        all_keys = set(all_deps.keys())

        # Language
        if any(k in all_keys for k in ('typescript', 'ts-node', '@types/node')):
            stack['primary_language'] = 'TypeScript'
        else:
            stack['primary_language'] = 'JavaScript'

        # Runtime
        if 'node' in (data.get('engines') or {}):
            stack['runtime'] = 'Node.js'
        else:
            stack['runtime'] = 'Node.js'

        # Framework
        fw_map = {
            'next': 'Next.js', 'react': 'React', 'vue': 'Vue.js',
            '@angular/core': 'Angular', '@nestjs/core': 'NestJS',
            'fastify': 'Fastify', 'express': 'Express', 'koa': 'Koa',
            'hapi': 'Hapi', 'nuxt': 'Nuxt.js', 'remix': 'Remix',
            'astro': 'Astro', 'svelte': 'Svelte', '@sveltejs/kit': 'SvelteKit'
        }
        for key, name in fw_map.items():
            if key in all_keys:
                stack['framework'] = name
                break

        # Database
        db_map = {
            'prisma': 'PostgreSQL (via Prisma)', '@prisma/client': 'PostgreSQL (via Prisma)',
            'mongoose': 'MongoDB (via Mongoose)', 'pg': 'PostgreSQL',
            'mysql2': 'MySQL', 'mysql': 'MySQL', 'better-sqlite3': 'SQLite',
            'sqlite3': 'SQLite', 'sequelize': 'SQL (via Sequelize)',
            'typeorm': 'SQL (via TypeORM)', 'drizzle-orm': 'SQL (via Drizzle)',
            'mongodb': 'MongoDB', 'redis': 'Redis', 'ioredis': 'Redis'
        }
        for key, name in db_map.items():
            if key in all_keys:
                stack['database'] = name
                break

        # Test
        test_map = {
            'jest': 'Jest', 'vitest': 'Vitest', 'mocha': 'Mocha',
            'jasmine': 'Jasmine', '@playwright/test': 'Playwright',
            'cypress': 'Cypress', 'ava': 'AVA'
        }
        for key, name in test_map.items():
            if key in all_keys:
                stack['test_framework'] = name
                break

        # Build tool
        build_map = {
            'esbuild': 'esbuild', 'vite': 'Vite', 'webpack': 'Webpack',
            'rollup': 'Rollup', 'parcel': 'Parcel', 'turbopack': 'Turbopack',
            '@swc/core': 'SWC', 'tsup': 'tsup'
        }
        for key, name in build_map.items():
            if key in all_keys:
                stack['build_tool'] = name
                break

        # Package manager
        if (root / 'pnpm-lock.yaml').exists():
            stack['package_manager'] = 'pnpm'
        elif (root / 'yarn.lock').exists():
            stack['package_manager'] = 'yarn'
        elif (root / 'bun.lockb').exists():
            stack['package_manager'] = 'bun'
        else:
            stack['package_manager'] = 'npm'

    # --- Python ---
    elif _file_exists_any(root, ['requirements.txt', 'pyproject.toml', 'setup.py', 'setup.cfg', 'Pipfile']):
        stack['primary_language'] = 'Python'
        stack['runtime'] = 'Python'

        deps_text = ''
        for fname in ('requirements.txt', 'requirements-dev.txt'):
            f = root / fname
            if f.exists():
                deps_text += f.read_text(encoding='utf-8', errors='ignore').lower()

        pyproject = root / 'pyproject.toml'
        if pyproject.exists():
            deps_text += pyproject.read_text(encoding='utf-8', errors='ignore').lower()

        setup_py = root / 'setup.py'
        if setup_py.exists():
            deps_text += setup_py.read_text(encoding='utf-8', errors='ignore').lower()

        py_fw = [
            ('django', 'Django'), ('flask', 'Flask'), ('fastapi', 'FastAPI'),
            ('tornado', 'Tornado'), ('aiohttp', 'aiohttp'), ('starlette', 'Starlette'),
            ('sanic', 'Sanic'), ('bottle', 'Bottle')
        ]
        for key, name in py_fw:
            if key in deps_text:
                stack['framework'] = name
                break

        py_db = [
            ('sqlalchemy', 'SQL (via SQLAlchemy)'), ('django.db', 'Django ORM'),
            ('pymongo', 'MongoDB'), ('motor', 'MongoDB (async)'),
            ('psycopg2', 'PostgreSQL'), ('asyncpg', 'PostgreSQL (async)'),
            ('pymysql', 'MySQL'), ('tortoise', 'SQL (via Tortoise ORM)')
        ]
        for key, name in py_db:
            if key in deps_text:
                stack['database'] = name
                break

        py_test = [
            ('pytest', 'pytest'), ('unittest', 'unittest'),
            ('nose', 'nose'), ('hypothesis', 'hypothesis+pytest')
        ]
        for key, name in py_test:
            if key in deps_text:
                stack['test_framework'] = name
                break

        if (root / 'Pipfile').exists():
            stack['package_manager'] = 'pipenv'
        elif pyproject.exists() and 'poetry' in pyproject.read_text(encoding='utf-8', errors='ignore').lower():
            stack['package_manager'] = 'poetry'
        else:
            stack['package_manager'] = 'pip'

    # --- Go ---
    elif (root / 'go.mod').exists():
        stack['primary_language'] = 'Go'
        stack['runtime'] = 'Go'
        go_text = (root / 'go.mod').read_text(encoding='utf-8', errors='ignore').lower()
        go_fw = [
            ('github.com/gin-gonic/gin', 'Gin'), ('github.com/labstack/echo', 'Echo'),
            ('github.com/gofiber/fiber', 'Fiber'), ('github.com/go-chi/chi', 'Chi'),
            ('github.com/gorilla/mux', 'Gorilla Mux')
        ]
        for key, name in go_fw:
            if key in go_text:
                stack['framework'] = name
                break
        stack['build_tool'] = 'go build'
        stack['test_framework'] = 'go test'

    # --- Rust ---
    elif (root / 'Cargo.toml').exists():
        stack['primary_language'] = 'Rust'
        stack['runtime'] = 'Rust'
        cargo_text = (root / 'Cargo.toml').read_text(encoding='utf-8', errors='ignore').lower()
        rust_fw = [
            ('actix-web', 'Actix Web'), ('rocket', 'Rocket'),
            ('axum', 'Axum'), ('warp', 'Warp'), ('tide', 'Tide')
        ]
        for key, name in rust_fw:
            if key in cargo_text:
                stack['framework'] = name
                break
        stack['build_tool'] = 'cargo'
        stack['test_framework'] = 'cargo test'

    # --- Java ---
    elif _file_exists_any(root, ['pom.xml', 'build.gradle', 'build.gradle.kts']):
        stack['runtime'] = 'JVM'
        pom = root / 'pom.xml'
        gradle = root / 'build.gradle'
        gradle_kts = root / 'build.gradle.kts'
        text = ''
        if pom.exists():
            text = pom.read_text(encoding='utf-8', errors='ignore').lower()
            stack['build_tool'] = 'Maven'
        elif gradle_kts.exists():
            text = gradle_kts.read_text(encoding='utf-8', errors='ignore').lower()
            stack['build_tool'] = 'Gradle'
            stack['primary_language'] = 'Kotlin'
        elif gradle.exists():
            text = gradle.read_text(encoding='utf-8', errors='ignore').lower()
            stack['build_tool'] = 'Gradle'

        if 'kotlin' in text or gradle_kts.exists():
            stack['primary_language'] = 'Kotlin'
        else:
            stack['primary_language'] = 'Java'

        if 'spring-boot' in text or 'spring.boot' in text:
            stack['framework'] = 'Spring Boot'
        elif 'quarkus' in text:
            stack['framework'] = 'Quarkus'
        elif 'micronaut' in text:
            stack['framework'] = 'Micronaut'

        if 'junit' in text:
            stack['test_framework'] = 'JUnit'

    # --- C# ---
    elif list(root.rglob('*.csproj')):
        stack['primary_language'] = 'C#'
        stack['runtime'] = '.NET'
        csproj_files = list(root.rglob('*.csproj'))
        text = ''
        for f in csproj_files[:3]:
            text += f.read_text(encoding='utf-8', errors='ignore').lower()
        if 'microsoft.aspnetcore' in text:
            stack['framework'] = 'ASP.NET Core'
        stack['build_tool'] = 'dotnet'
        if 'xunit' in text:
            stack['test_framework'] = 'xUnit'
        elif 'nunit' in text:
            stack['test_framework'] = 'NUnit'
        elif 'mstest' in text:
            stack['test_framework'] = 'MSTest'

    # --- Ruby ---
    elif (root / 'Gemfile').exists():
        stack['primary_language'] = 'Ruby'
        stack['runtime'] = 'Ruby'
        gemfile = (root / 'Gemfile').read_text(encoding='utf-8', errors='ignore').lower()
        if 'rails' in gemfile:
            stack['framework'] = 'Ruby on Rails'
        elif 'sinatra' in gemfile:
            stack['framework'] = 'Sinatra'
        stack['package_manager'] = 'bundler'
        if 'rspec' in gemfile:
            stack['test_framework'] = 'RSpec'
        elif 'minitest' in gemfile:
            stack['test_framework'] = 'minitest'

    # --- PHP ---
    elif (root / 'composer.json').exists():
        stack['primary_language'] = 'PHP'
        stack['runtime'] = 'PHP'
        try:
            data = json.loads((root / 'composer.json').read_text(encoding='utf-8', errors='ignore'))
            reqs = {**data.get('require', {}), **data.get('require-dev', {})}
            if 'laravel/framework' in reqs:
                stack['framework'] = 'Laravel'
            elif 'symfony/symfony' in reqs or any('symfony' in k for k in reqs):
                stack['framework'] = 'Symfony'
        except Exception:
            pass
        stack['package_manager'] = 'Composer'

    # --- File-extension fallback when no config files found ---
    if stack['primary_language'] == 'Unknown':
        ext_counts = {}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in
                           {'node_modules', '.git', 'vendor', 'dist', 'build', '__pycache__',
                            '.next', 'target', '.venv', 'venv', '.tox'}]
            for fname in filenames:
                ext = Path(fname).suffix.lower()
                if ext:
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
        lang_from_ext = {
            '.py': ('Python', 'Python'), '.js': ('JavaScript', 'Node.js'),
            '.ts': ('TypeScript', 'Node.js'), '.go': ('Go', 'Go'),
            '.rs': ('Rust', 'Rust'), '.java': ('Java', 'JVM'),
            '.kt': ('Kotlin', 'JVM'), '.cs': ('C#', '.NET'),
            '.rb': ('Ruby', 'Ruby'), '.php': ('PHP', 'PHP'),
        }
        if ext_counts:
            top_ext = max(ext_counts, key=lambda e: ext_counts[e] if e in lang_from_ext else 0)
            if top_ext in lang_from_ext:
                stack['primary_language'], stack['runtime'] = lang_from_ext[top_ext]

    # CI detection
    if (root / '.github' / 'workflows').exists():
        stack['ci'] = 'GitHub Actions'
    elif (root / '.travis.yml').exists():
        stack['ci'] = 'Travis CI'
    elif (root / '.circleci' / 'config.yml').exists():
        stack['ci'] = 'CircleCI'
    elif (root / 'azure-pipelines.yml').exists():
        stack['ci'] = 'Azure Pipelines'
    elif (root / 'Jenkinsfile').exists():
        stack['ci'] = 'Jenkins'
    elif (root / '.gitlab-ci.yml').exists():
        stack['ci'] = 'GitLab CI'

    result = {'stack': stack, '_token_estimate': 0}
    output_str = json.dumps(result)
    result['_token_estimate'] = estimate_tokens(output_str)
    return result


def _file_exists_any(root: Path, names: list) -> bool:
    return any((root / n).exists() for n in names)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: detect_stack.py <repo_path>', file=sys.stderr)
        sys.exit(1)
    output = detect_stack(sys.argv[1])
    print(json.dumps(output, indent=2))
