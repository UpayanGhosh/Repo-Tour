#!/usr/bin/env python3
"""extract_section.py — Extracts section-relevant slice from repo-analysis.json."""

import sys
import json
import argparse
from pathlib import Path

SECTION_FIELDS = {
    'overview': ['meta', 'readme_excerpt', 'entry_points'],
    'architecture': ['clusters', 'entry_points', 'critical_modules'],
    'tech_stack': ['stack'],
    'entry_points': ['entry_points'],
    'modules': ['critical_modules'],
    'workflows': ['workflows'],
    'cross_cutting': ['clusters', 'stack', 'entry_points'],
    'directory_guide': ['top_dirs'],
    'glossary': ['glossary_candidates', 'stack'],
    'getting_started': ['git_info', 'stack', 'readme_excerpt'],
    'cookbook': ['stack', 'entry_points', 'critical_modules', 'top_dirs'],
    'feature_index': [],  # served from sidecar file; returns empty dict from analysis
}


def extract_section(analysis: dict, section: str,
                    batch: int = 0, batch_size: int = 8) -> dict:
    fields = SECTION_FIELDS.get(section, list(analysis.keys()))
    result = {}

    for field in fields:
        if field not in analysis:
            continue
        val = analysis[field]

        # Special handling for paginated sections
        if field == 'critical_modules' and section == 'modules':
            start = batch * batch_size
            end = start + batch_size
            val = val[start:end]
            result['_batch_info'] = {
                'batch': batch,
                'batch_size': batch_size,
                'total_modules': len(analysis.get('critical_modules', [])),
                'total_batches': max(1, -(-len(analysis.get('critical_modules', [])) // batch_size))
            }
        elif field == 'entry_points' and section == 'overview':
            val = val[:2]  # Only first 2 entry points for overview
        elif field == 'critical_modules' and section == 'architecture':
            # For architecture, only include path and role (not full details)
            val = [{'path': m.get('path', ''), 'role': m.get('role', '')} for m in val]

        result[field] = val

    return result


def main():
    parser = argparse.ArgumentParser(description='Extract section slice from repo-analysis.json')
    parser.add_argument('section', help='Section name (overview, architecture, tech_stack, entry_points, modules, workflows, cross_cutting, directory_guide, glossary, getting_started, cookbook, feature_index)')
    parser.add_argument('analysis_file', help='Path to repo-analysis.json')
    parser.add_argument('--batch', type=int, default=0, help='Batch number (for modules section, 0-indexed)')
    parser.add_argument('--batch-size', type=int, default=8, help='Batch size (default: 8)')
    parser.add_argument('--feature-index-file', help='Path to feature-index.json sidecar (used when section=feature_index)')
    args = parser.parse_args()

    try:
        analysis = json.loads(Path(args.analysis_file).read_text(encoding='utf-8'))
    except Exception as e:
        print(f'Error reading {args.analysis_file}: {e}', file=sys.stderr)
        sys.exit(1)

    if args.section not in SECTION_FIELDS:
        print(f'Unknown section: {args.section}', file=sys.stderr)
        print(f'Valid sections: {", ".join(SECTION_FIELDS.keys())}', file=sys.stderr)
        sys.exit(1)

    # feature_index: read from sidecar file
    if args.section == 'feature_index':
        sidecar_path = args.feature_index_file
        if not sidecar_path:
            # Try default location alongside analysis_file
            sidecar_path = str(Path(args.analysis_file).parent / 'feature-index.json')
        try:
            result = json.loads(Path(sidecar_path).read_text(encoding='utf-8'))
        except Exception as e:
            print(f'Error reading feature-index sidecar {sidecar_path}: {e}', file=sys.stderr)
            result = []
        print(json.dumps(result, indent=2))
        return

    result = extract_section(analysis, args.section, args.batch, args.batch_size)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
