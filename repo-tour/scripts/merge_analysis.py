#!/usr/bin/env python3
"""merge_analysis.py — Merges script outputs into unified repo-analysis.json. Budget: 3500 tokens output."""

import sys
import json
import argparse
from pathlib import Path


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def truncate(obj, max_chars: int = 200):
    """Recursively truncate strings in a data structure."""
    if isinstance(obj, str):
        return obj[:max_chars]
    elif isinstance(obj, list):
        return [truncate(item, max_chars) for item in obj]
    elif isinstance(obj, dict):
        return {k: truncate(v, max_chars) for k, v in obj.items()}
    return obj


def load_json(path: str, label: str) -> dict:
    if not path:
        return {}
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception as e:
        print(f'Warning: Could not load {label} from {path}: {e}', file=sys.stderr)
        return {}


def merge(scan: dict, stack: dict, entries: dict, deps: dict, budget: int = 3500) -> dict:
    merged = {
        'meta': scan.get('meta', {}),
        'stack': stack.get('stack', {}),
        'entry_points': entries.get('entry_points', []),
        'critical_modules': deps.get('critical_modules', []),
        'clusters': deps.get('clusters', []),
        'external_deps_top10': deps.get('external_deps_top10', []),
        'top_dirs': scan.get('top_dirs', []),
        'readme_excerpt': scan.get('readme_excerpt', ''),
        'git_info': scan.get('git_info', {}),
        'files_by_size': scan.get('files_by_size', {}),
        'mega_files': scan.get('mega_files', []),
        'skip_candidates': scan.get('skip_candidates', []),
        'workflows': [],            # Filled by Sonnet in Phase 1
        'glossary_candidates': [], # Filled by Sonnet after reading modules
        'circular_warnings': deps.get('circular_warnings', []),
        '_meta': {
            'token_estimate': 0,
            'within_budget': True,
            'budget': budget
        }
    }

    # Deduplication: remove skip_candidates from critical_modules
    skip_set = set(merged['skip_candidates'])
    merged['critical_modules'] = [
        m for m in merged['critical_modules']
        if m.get('path', '') not in skip_set
    ]

    # Truncate strings
    merged = truncate(merged)

    # Estimate tokens
    output_str = json.dumps(merged)
    token_est = estimate_tokens(output_str)

    # Budget enforcement: trim lowest-complexity modules first
    if token_est > budget:
        modules = sorted(merged['critical_modules'], key=lambda m: m.get('complexity', 0))
        while token_est > budget and modules:
            modules.pop(0)
            merged['critical_modules'] = modules
            output_str = json.dumps(merged)
            token_est = estimate_tokens(output_str)

    merged['_meta']['token_estimate'] = token_est
    merged['_meta']['within_budget'] = token_est <= budget
    return merged


def main():
    parser = argparse.ArgumentParser(description='Merge analysis outputs into repo-analysis.json')
    parser.add_argument('--scan', help='Path to scan_repo.py output JSON')
    parser.add_argument('--stack', help='Path to detect_stack.py output JSON')
    parser.add_argument('--entries', help='Path to find_entry_points.py output JSON')
    parser.add_argument('--deps', help='Path to map_dependencies.py output JSON')
    parser.add_argument('--budget', type=int, default=3500, help='Max token budget for output')
    parser.add_argument('--output', help='Output file path (default: stdout)')
    args = parser.parse_args()

    scan = load_json(args.scan, 'scan')
    stack = load_json(args.stack, 'stack')
    entries = load_json(args.entries, 'entries')
    deps = load_json(args.deps, 'deps')

    result = merge(scan, stack, entries, deps, args.budget)

    output_str = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(output_str, encoding='utf-8')
        print(f'Wrote {len(output_str)} chars to {args.output}', file=sys.stderr)
        stats = {
            'output_file': args.output,
            'token_estimate': result['_meta']['token_estimate'],
            'within_budget': result['_meta']['within_budget'],
            'budget': result['_meta']['budget'],
            'modules_count': len(result['critical_modules']),
            'clusters_count': len(result['clusters'])
        }
        print(json.dumps(stats))
    else:
        print(output_str)


if __name__ == '__main__':
    main()
