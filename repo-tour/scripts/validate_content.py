#!/usr/bin/env python3
"""validate_content.py — Validates site-content/*.json files against expected schemas.

Run this BEFORE generate_site.py to catch missing or malformed fields early.
Prints a checklist: [✓] overview.json valid, [✗] modules_batch_0.json missing field: detailed_explanation

Usage:
    python validate_content.py --content-dir site-content/
    python validate_content.py --content-dir .repotour/site-content/
"""

import os
import sys
import json
import glob
import argparse
from pathlib import Path


# ── Schema definitions ────────────────────────────────────────────────────────
# Each entry: (file_pattern, required_fields, description)
# required_fields is a list of dot-notation paths.  Lists mean "array with at
# least one element having these fields".

SCHEMAS = {
    'overview.json': {
        'required': ['summary', 'audience', 'approach'],
        'types': {'summary': str, 'audience': str, 'approach': str},
    },
    'architecture.json': {
        'required': ['analogy', 'layers', 'mermaid'],
        'array_field': 'layers',
        'array_required': ['name', 'responsibility'],
    },
    'cross_cutting.json': {
        'required': [],          # all sub-fields optional (may be null)
        'optional': ['auth_authz', 'error_handling', 'logging_observability', 'testing_strategy'],
    },
    'tech_stack.json': {
        'is_array': True,
        'array_required': ['name', 'role', 'why'],
        'min_items': 1,
    },
    'entry_points.json': {
        'is_array': True,
        'array_required': ['file', 'trigger', 'narrative'],
        'min_items': 1,
    },
    'workflows.json': {
        'required': ['workflows'],
        'array_field': 'workflows',
        'array_required': ['name', 'trigger', 'steps'],
    },
    'directory_guide.json': {
        'is_array': True,
        'array_required': ['path', 'purpose'],
        'min_items': 1,
    },
    'glossary_getting_started.json': {
        'required': ['glossary', 'getting_started'],
        'nested': {
            'getting_started': ['clone', 'run'],
        },
    },
    'cookbook.json': {
        'required': ['recipes'],
        'array_field': 'recipes',
        'array_required': ['title', 'steps'],
        'min_array_items': 3,
    },
}

# modules_batch_*.json — validated separately
MODULE_BATCH_REQUIRED = ['path', 'name', 'simple_explanation', 'detailed_explanation']


def _get(obj, key):
    """Get nested key using dot notation."""
    parts = key.split('.')
    for p in parts:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(p)
    return obj


def validate_file(fpath: str) -> list[str]:
    """Return list of error strings (empty = valid)."""
    fname = Path(fpath).name
    errors = []

    try:
        with open(fpath, encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        return [f'Invalid JSON: {exc}']
    except Exception as exc:
        return [f'Cannot read file: {exc}']

    # modules_batch_*.json
    if fname.startswith('modules_batch_'):
        if not isinstance(data, list):
            return ['Expected JSON array']
        if len(data) == 0:
            errors.append('Array is empty — no modules generated')
        for i, item in enumerate(data):
            for field in MODULE_BATCH_REQUIRED:
                if not item.get(field):
                    errors.append(f'Item {i}: missing field: {field}')
        return errors

    schema = SCHEMAS.get(fname)
    if not schema:
        return []   # unknown file — skip

    is_array = schema.get('is_array', False)
    if is_array:
        if not isinstance(data, list):
            errors.append(f'Expected JSON array, got {type(data).__name__}')
            return errors
        min_items = schema.get('min_items', 1)
        if len(data) < min_items:
            errors.append(f'Array has {len(data)} items, expected at least {min_items}')
        for i, item in enumerate(data[:5]):
            for field in schema.get('array_required', []):
                if not item.get(field):
                    errors.append(f'Item {i}: missing field: {field}')
        return errors

    if not isinstance(data, dict):
        errors.append(f'Expected JSON object, got {type(data).__name__}')
        return errors

    # Required top-level fields
    for field in schema.get('required', []):
        val = data.get(field)
        if val is None:
            errors.append(f'missing field: {field}')
        elif isinstance(val, str) and not val.strip():
            errors.append(f'field is empty string: {field}')

    # Type checks
    for field, expected_type in schema.get('types', {}).items():
        val = data.get(field)
        if val is not None and not isinstance(val, expected_type):
            errors.append(f'{field}: expected {expected_type.__name__}, got {type(val).__name__}')

    # Array sub-field
    arr_field = schema.get('array_field')
    if arr_field:
        arr = data.get(arr_field)
        if arr is not None:
            if not isinstance(arr, list):
                errors.append(f'{arr_field}: expected array')
            elif len(arr) < schema.get('min_array_items', 1):
                errors.append(f'{arr_field}: has {len(arr)} items, expected at least {schema.get("min_array_items", 1)}')
            else:
                for i, item in enumerate(arr[:8]):
                    for field in schema.get('array_required', []):
                        if not (item or {}).get(field):
                            errors.append(f'{arr_field}[{i}]: missing field: {field}')

    # Nested required
    for parent, fields in schema.get('nested', {}).items():
        obj = data.get(parent)
        if obj and isinstance(obj, dict):
            for f in fields:
                if not obj.get(f):
                    errors.append(f'{parent}.{f}: missing or empty')

    return errors


def main():
    parser = argparse.ArgumentParser(description='Validate site-content/*.json before generate_site.py')
    parser.add_argument('--content-dir', required=True, help='Path to site-content/ directory')
    parser.add_argument('--strict', action='store_true', help='Exit 1 on any warning')
    args = parser.parse_args()

    content_dir = Path(args.content_dir)
    if not content_dir.exists():
        print(f'[ERROR] Content directory not found: {content_dir}', file=sys.stderr)
        sys.exit(1)

    json_files = sorted(content_dir.glob('*.json'))
    if not json_files:
        print(f'[ERROR] No JSON files found in {content_dir}', file=sys.stderr)
        sys.exit(1)

    # Check for expected files
    EXPECTED = set(SCHEMAS.keys()) | {'modules_batch_0.json'}
    found_names = {f.name for f in json_files}
    missing = []
    for expected in sorted(EXPECTED):
        if expected not in found_names and not expected.startswith('modules_batch'):
            missing.append(expected)

    has_modules = any(f.name.startswith('modules_batch_') for f in json_files)
    if not has_modules:
        missing.append('modules_batch_0.json')

    all_ok = True

    print(f'\nContent validation: {content_dir}\n')

    for fpath in json_files:
        errors = validate_file(str(fpath))
        if errors:
            all_ok = False
            print(f'  [✗] {fpath.name}')
            for err in errors:
                print(f'        → {err}')
        else:
            print(f'  [✓] {fpath.name}')

    if missing:
        all_ok = False
        print(f'\nMissing files:')
        for m in missing:
            print(f'  [✗] {m} — not generated')

    print()
    if all_ok:
        print('All content files valid. Safe to run generate_site.py.')
        sys.exit(0)
    else:
        print('Validation failed. Fix errors above before running generate_site.py.')
        sys.exit(1)


if __name__ == '__main__':
    main()
