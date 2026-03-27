#!/usr/bin/env python3
"""build_graph.py — Zero-dep Python CLI that walks a repo, parses imports,
scores connectivity, reduces to max-nodes, outputs graph-data.json.

Usage:
    python build_graph.py <repo_path> --language TypeScript --max-nodes 200 --output graph-data.json [--include-tests] [--min-connections N]
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path

# ============================================================
# Constants / Config
# ============================================================

SKIP_DIRS = {
    'node_modules', '.git', 'vendor', 'dist', 'build', '__pycache__',
    '.next', 'target', 'bin', 'obj', '.repotour',
}

# Source extensions per language (lowercase)
SOURCE_EXTENSIONS = {
    'typescript':   {'.ts', '.tsx'},
    'javascript':   {'.js', '.jsx', '.mjs', '.cjs'},
    'python':       {'.py', '.ipynb'},   # .ipynb = Jupyter notebooks (JSON blobs, parsed separately)
    'go':           {'.go'},
    'rust':         {'.rs'},
    'java':         {'.java'},
    'kotlin':       {'.kt', '.kts'},
    'csharp':       {'.cs'},
    'ruby':         {'.rb'},
    'php':          {'.php'},
    'cpp':          {'.cpp', '.cc', '.cxx', '.h', '.hpp'},
    'c':            {'.c', '.h'},
}

FALLBACK_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs',
    '.java', '.kt', '.cs', '.rb', '.php', '.cpp', '.c', '.h',
}

ROLE_PATTERNS = {
    'service':    ['/service', '/services/', 'Service.', 'service.'],
    'route':      ['/route', '/routes/', '/router', '/controllers/', '/api/', 'route.', 'Route.', 'Controller.'],
    'model':      ['/model', '/models/', '/entity', '/entities/', 'Model.', 'Entity.', '.model.', 'schema.', 'Schema.'],
    'utility':    ['/util', '/utils/', '/helpers/', '/lib/', 'util.', 'helper.', 'helpers.'],
    'config':     ['/config', '/configs/', '.config.', 'config.', 'Config.', 'settings.', '.env'],
    'middleware': ['/middleware', '/middlewares/', 'Middleware.', 'middleware.'],
    'test':       ['/test', '/tests/', '/spec', '/__tests__/', '.test.', '.spec.', '_test.', '_spec.'],
    'migration':  ['/migration', '/migrations/', 'migration.', 'Migration.'],
    'build':      ['webpack', 'rollup', 'vite', 'babel', 'jest.config', 'tsconfig',
                   'package.json', 'Makefile', 'Dockerfile', 'Cargo.toml', 'pom.xml', 'build.gradle'],
}

# OKLCH hue values
ROLE_COLORS = {
    'service': 262, 'route': 200, 'model': 145, 'utility': 240,
    'config': 60, 'middleware': 290, 'test': 220, 'migration': 320,
    'build': 30, 'folder': 50,
}

SCALE_THRESHOLDS = [
    (50,             'all'),
    (300,            'nontrivial'),
    (1000,           'connected'),
    (5000,           'top150'),
    (float('inf'),   'top200'),
]


# ============================================================
# Utility functions
# ============================================================

def count_lines(path):
    """Count non-blank lines in a file, ignoring read errors.
    For .ipynb files, counts only lines inside code cells (not the JSON wrapper).
    """
    if path.endswith('.ipynb'):
        return _count_notebook_code_lines(path)
    try:
        with open(path, encoding='utf-8', errors='ignore') as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def _count_notebook_code_lines(path):
    """Count actual code lines across all code cells in a Jupyter notebook."""
    try:
        import json as _json
        with open(path, encoding='utf-8', errors='ignore') as f:
            nb = _json.load(f)
        total = 0
        for cell in nb.get('cells', []):
            if cell.get('cell_type') != 'code':
                continue
            source = cell.get('source', [])
            if isinstance(source, list):
                source = ''.join(source)
            total += sum(1 for line in source.splitlines() if line.strip())
        return total
    except Exception:
        return 0


def classify_role(rel_path):
    """Return the first matching role for a file path, defaulting to 'utility'."""
    for role, patterns in ROLE_PATTERNS.items():
        for pat in patterns:
            if pat in rel_path:
                return role
    return 'utility'


def collect_files(repo_path, language, include_tests):
    """Walk repo, return list of file metadata dicts."""
    lang_key = language.lower()
    extensions = SOURCE_EXTENSIONS.get(lang_key, FALLBACK_EXTENSIONS)
    files = []

    for dirpath, dirnames, filenames in os.walk(repo_path):
        # Prune skip dirs in-place so os.walk doesn't recurse into them
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]

        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in extensions:
                continue

            abs_path = os.path.join(dirpath, fname)
            try:
                rel_path = os.path.relpath(abs_path, repo_path).replace('\\', '/')
            except ValueError:
                continue

            role = classify_role(rel_path)
            if not include_tests and role == 'test':
                continue

            files.append({
                'path': abs_path,
                'rel':  rel_path,
                'loc':  count_lines(abs_path),
                'role': role,
            })

    return files


# ============================================================
# Import parsers
# ============================================================

def parse_imports_js(content, rel_path):
    """Extract import strings from JS/TS content."""
    imports = []
    # ES import/from and dynamic import
    for m in re.finditer(r'(?:import|from)\s+[\'"]([^\'"]+)[\'"]', content):
        imports.append(m.group(1))
    # require()
    for m in re.finditer(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', content):
        imports.append(m.group(1))
    return imports


def parse_imports_python(content, rel_path):
    """Extract import strings from Python source content."""
    imports = []
    for line in content.splitlines():
        line = line.strip()
        m = re.match(r'^from\s+([\w.]+)\s+import', line)
        if m:
            imports.append(m.group(1))
            continue
        m = re.match(r'^import\s+([\w.,\s]+)', line)
        if m:
            for part in m.group(1).split(','):
                imports.append(part.strip().split()[0])
    return imports


def parse_imports_notebook(path):
    """Extract import strings from a Jupyter notebook (.ipynb).

    .ipynb files are JSON — the source code lives inside cells[].source
    (a list of strings or a single string). We extract all code cells,
    concatenate their source, and run the standard Python import parser.
    """
    imports = []
    try:
        import json as _json
        with open(path, encoding='utf-8', errors='ignore') as f:
            nb = _json.load(f)
        for cell in nb.get('cells', []):
            if cell.get('cell_type') != 'code':
                continue
            source = cell.get('source', [])
            if isinstance(source, list):
                source = ''.join(source)
            if source.strip():
                imports.extend(parse_imports_python(source, path))
    except Exception:
        pass
    return imports


def parse_imports_go(content, rel_path):
    """Extract import strings from Go content."""
    imports = []
    # Multi-line import block
    block_m = re.search(r'import\s*\(([^)]+)\)', content, re.DOTALL)
    if block_m:
        for m in re.finditer(r'"([^"]+)"', block_m.group(1)):
            imports.append(m.group(1))
    # Single-line imports
    for m in re.finditer(r'import\s+"([^"]+)"', content):
        imports.append(m.group(1))
    return imports


def parse_imports_rust(content, rel_path):
    """Extract import strings from Rust content."""
    imports = []
    for line in content.splitlines():
        line = line.strip()
        m = re.match(r'^use\s+([\w:]+)', line)
        if m:
            imports.append(m.group(1))
            continue
        m = re.match(r'^mod\s+(\w+)', line)
        if m:
            imports.append(m.group(1))
    return imports


def parse_imports_java(content, rel_path):
    """Extract import strings from Java content."""
    imports = []
    for line in content.splitlines():
        m = re.match(r'^import\s+([\w.]+);', line.strip())
        if m:
            imports.append(m.group(1))
    return imports


def parse_imports_csharp(content, rel_path):
    """Extract import strings from C# content."""
    imports = []
    for line in content.splitlines():
        m = re.match(r'^using\s+([\w.]+);', line.strip())
        if m:
            imports.append(m.group(1))
    return imports


def parse_imports(content, rel_path, language):
    """Dispatch to the correct import parser based on language and file extension.

    .ipynb files are handled specially — they are JSON blobs and need their
    own parser regardless of the declared language.
    """
    # Jupyter notebooks must be handled by path, not language, because their
    # content is JSON (not Python source). parse_imports_notebook() reads the
    # file directly rather than using the pre-read content string.
    if rel_path.endswith('.ipynb'):
        return parse_imports_notebook(rel_path)

    lang_key = language.lower()
    if lang_key in ('typescript', 'javascript'):
        return parse_imports_js(content, rel_path)
    elif lang_key == 'python':
        return parse_imports_python(content, rel_path)
    elif lang_key == 'go':
        return parse_imports_go(content, rel_path)
    elif lang_key == 'rust':
        return parse_imports_rust(content, rel_path)
    elif lang_key in ('java', 'kotlin'):
        return parse_imports_java(content, rel_path)
    elif lang_key == 'csharp':
        return parse_imports_csharp(content, rel_path)
    else:
        # Default: try JS-style
        return parse_imports_js(content, rel_path)


# ============================================================
# Import resolution
# ============================================================

def resolve_import(import_str, source_rel, all_rel_paths_set):
    """Resolve an import string to a rel_path in the repo, or None if external."""
    if not import_str:
        return None

    # Only resolve relative imports (starting with . or ..)
    if import_str.startswith('./') or import_str.startswith('../'):
        source_dir = os.path.dirname(source_rel)
        # Normalize to forward slashes
        joined = os.path.normpath(os.path.join(source_dir, import_str)).replace('\\', '/')
        # Try as-is first
        if joined in all_rel_paths_set:
            return joined
        # Try common extensions
        for ext in ('.ts', '.tsx', '.js', '.jsx', '.py', '/index.ts', '/index.js', '/index.tsx', '/index.jsx'):
            candidate = joined + ext
            if candidate in all_rel_paths_set:
                return candidate
        return None

    # Non-relative but contains slash and not an npm-scoped package (@org/pkg)
    if '/' in import_str and not import_str.startswith('@'):
        # Try to match by suffix
        for rel in all_rel_paths_set:
            if rel.endswith(import_str) or import_str in rel:
                return rel
        return None

    # External / npm / stdlib — skip
    return None


# ============================================================
# Graph construction
# ============================================================

def build_adjacency(files, language):
    """Build adjacency dict: {rel_path: set_of_target_rel_paths}."""
    all_rel_paths_set = {f['rel'] for f in files}
    adjacency = {f['rel']: set() for f in files}

    for file_meta in files:
        # Jupyter notebooks are JSON — parse_imports_notebook reads the file
        # directly using the absolute path. Skip the normal content read.
        if file_meta['rel'].endswith('.ipynb'):
            imports = parse_imports_notebook(file_meta['path'])
        else:
            try:
                with open(file_meta['path'], encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
            except Exception:
                continue
            imports = parse_imports(content, file_meta['rel'], language)
        for imp in imports:
            target = resolve_import(imp, file_meta['rel'], all_rel_paths_set)
            if target and target != file_meta['rel']:
                adjacency[file_meta['rel']].add(target)

    return adjacency


def score_connectivity(files, adjacency):
    """Score each file by in_degree + out_degree + 2 * bidirectional."""
    all_rels = {f['rel'] for f in files}
    in_degree  = {rel: 0 for rel in all_rels}
    out_degree = {rel: 0 for rel in all_rels}

    for src, targets in adjacency.items():
        for tgt in targets:
            if tgt in all_rels:
                out_degree[src] += 1
                in_degree[tgt] += 1

    scores = {}
    for rel in all_rels:
        bi = sum(
            1 for tgt in adjacency.get(rel, set())
            if rel in adjacency.get(tgt, set())
        )
        scores[rel] = in_degree[rel] + out_degree[rel] + 2 * bi

    return scores


def select_nodes(files, scores, max_nodes, min_connections):
    """Select nodes based on scale strategy and max_nodes cap."""
    total = len(files)

    # Determine strategy from thresholds
    strategy = 'top200'
    for threshold, strat in SCALE_THRESHOLDS:
        if total <= threshold:
            strategy = strat
            break

    if strategy == 'all':
        selected_rels = {f['rel'] for f in files}
    elif strategy == 'nontrivial':
        selected_rels = {
            f['rel'] for f in files
            if f['loc'] > 20 and f['role'] not in ('test', 'config', 'build')
        }
    elif strategy == 'connected':
        selected_rels = {
            f['rel'] for f in files
            if scores.get(f['rel'], 0) >= max(min_connections, 2)
        }
    elif strategy == 'top150':
        sorted_files = sorted(files, key=lambda f: scores.get(f['rel'], 0), reverse=True)
        selected_rels = {f['rel'] for f in sorted_files[:150]}
    else:  # top200
        sorted_files = sorted(files, key=lambda f: scores.get(f['rel'], 0), reverse=True)
        selected_rels = {f['rel'] for f in sorted_files[:200]}

    # Hard cap at max_nodes
    if len(selected_rels) > max_nodes:
        sorted_by_score = sorted(selected_rels, key=lambda r: scores.get(r, 0), reverse=True)
        selected_rels = set(sorted_by_score[:max_nodes])

    collapsed_set = {f['rel'] for f in files} - selected_rels
    return selected_rels, collapsed_set


def build_folder_nodes(collapsed_set, adjacency, selected_set, files_meta):
    """Group collapsed files into folder nodes with inherited edges."""
    files_by_folder = {}
    meta_by_rel = {f['rel']: f for f in files_meta}

    for rel in collapsed_set:
        folder = os.path.dirname(rel).replace('\\', '/')
        if folder not in files_by_folder:
            files_by_folder[folder] = []
        files_by_folder[folder].append(rel)

    folder_nodes = []
    folder_edges = []
    seen_edges = set()

    for folder, rels in files_by_folder.items():
        total_loc  = sum(meta_by_rel[r]['loc'] for r in rels if r in meta_by_rel)
        total_conn = sum(meta_by_rel[r].get('connectivity', 0) for r in rels if r in meta_by_rel)
        folder_id  = f'folder:{folder}'
        children   = [
            {
                'id':           r,
                'label':        os.path.basename(r),
                'role':         meta_by_rel[r]['role'] if r in meta_by_rel else 'utility',
                'loc':          meta_by_rel[r]['loc'] if r in meta_by_rel else 0,
                'connectivity': meta_by_rel[r].get('connectivity', 0) if r in meta_by_rel else 0,
                'tier':         meta_by_rel[r].get('tier', 'isolated') if r in meta_by_rel else 'isolated',
            }
            for r in rels
        ]

        folder_nodes.append({
            'id':           folder_id,
            'label':        os.path.basename(folder) or folder,
            'fullPath':     folder,
            'role':         'folder',
            'loc':          total_loc,
            'connectivity': total_conn,
            'tier':         'folder',
            'type':         'folder',
            'childCount':   len(rels),
            'cluster':      os.path.dirname(folder).replace('\\', '/'),
            'directory':    os.path.dirname(folder).replace('\\', '/'),
            'children_meta': children,
        })

        # Inherited edges: collapsed file → selected target
        for rel in rels:
            for target in adjacency.get(rel, set()):
                if target in selected_set:
                    edge_key = (folder_id, target)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        folder_edges.append({
                            'source': folder_id,
                            'target': target,
                            'weight': 1,
                        })

    return folder_nodes, folder_edges


def compute_tier(connectivity):
    """Classify connectivity score into tier."""
    if connectivity >= 10:
        return 'critical'
    elif connectivity >= 4:
        return 'important'
    elif connectivity >= 1:
        return 'connected'
    else:
        return 'isolated'


def build_output(selected_files, folder_nodes, adjacency, selected_set, files_meta, scores, folder_edges):
    """Build the final output dict."""
    meta_by_rel = {f['rel']: f for f in files_meta}

    # Enrich scores onto meta
    for f in files_meta:
        f['connectivity'] = scores.get(f['rel'], 0)
        f['tier'] = compute_tier(f['connectivity'])

    # Build file nodes
    nodes = []
    for f in selected_files:
        rel = f['rel']
        conn = scores.get(rel, 0)
        nodes.append({
            'id':           rel,
            'label':        os.path.basename(rel),
            'fullPath':     rel,
            'role':         f['role'],
            'loc':          f['loc'],
            'connectivity': conn,
            'tier':         compute_tier(conn),
            'cluster':      os.path.dirname(rel).replace('\\', '/'),
            'directory':    os.path.dirname(rel).replace('\\', '/'),
            'type':         'file',
        })

    # Append folder nodes
    for fn in folder_nodes:
        nodes.append({k: v for k, v in fn.items() if k != 'children_meta'})

    # Build edges between selected nodes
    seen_edges = set()
    edges = []
    edge_weight = {}
    for src, targets in adjacency.items():
        if src not in selected_set:
            continue
        for tgt in targets:
            if tgt not in selected_set:
                continue
            key = (src, tgt)
            if key in seen_edges:
                edge_weight[key] = edge_weight.get(key, 1) + 1
            else:
                seen_edges.add(key)
                edge_weight[key] = 1

    for (src, tgt), weight in edge_weight.items():
        edges.append({'source': src, 'target': tgt, 'weight': weight})

    # Append folder edges
    for fe in folder_edges:
        edges.append(fe)

    # Build folder_expansions
    folder_expansions = {}
    for fn in folder_nodes:
        children = fn.get('children_meta', [])
        exp_edges = []
        for child in children:
            for tgt in adjacency.get(child['id'], set()):
                exp_edges.append({'source': child['id'], 'target': tgt, 'weight': 1})
        folder_expansions[fn['id']] = {
            'nodes': children,
            'edges': exp_edges,
        }

    meta_block = {
        'total_files_scanned':        len(files_meta),
        'nodes_in_graph':             len(nodes),
        'edges_in_graph':             len(edges),
        'files_collapsed_into_folders': sum(fn['childCount'] for fn in folder_nodes),
        'output_size_kb':             0,
    }

    return {
        'nodes':             nodes,
        'edges':             edges,
        'folder_expansions': folder_expansions,
        '_meta':             meta_block,
    }


def progressive_cap(output, max_kb=500):
    """Progressively remove lowest-connectivity nodes if output > max_kb."""
    serialized = json.dumps(output, separators=(',', ':'))
    size = len(serialized.encode('utf-8'))

    while size > max_kb * 1024 and len(output['nodes']) > 30:
        # Find non-folder nodes sorted by connectivity ascending
        file_nodes = [n for n in output['nodes'] if n.get('type') != 'folder']
        if not file_nodes:
            break
        file_nodes.sort(key=lambda n: n.get('connectivity', 0))
        to_remove_count = max(1, len(file_nodes) // 10)
        remove_set = {n['id'] for n in file_nodes[:to_remove_count]}

        # Fold them into folder nodes
        by_folder = {}
        for nid in remove_set:
            folder = os.path.dirname(nid).replace('\\', '/')
            if folder not in by_folder:
                by_folder[folder] = []
            by_folder[folder].append(nid)

        for folder, rels in by_folder.items():
            folder_id = f'folder:{folder}'
            # Find or create folder node
            existing = next((n for n in output['nodes'] if n['id'] == folder_id), None)
            if existing:
                existing['childCount'] = existing.get('childCount', 0) + len(rels)
            else:
                output['nodes'].append({
                    'id':           folder_id,
                    'label':        os.path.basename(folder) or folder,
                    'fullPath':     folder,
                    'role':         'folder',
                    'loc':          0,
                    'connectivity': 0,
                    'tier':         'folder',
                    'type':         'folder',
                    'childCount':   len(rels),
                    'cluster':      os.path.dirname(folder).replace('\\', '/'),
                    'directory':    os.path.dirname(folder).replace('\\', '/'),
                })

        # Remove folded nodes and their edges
        output['nodes'] = [n for n in output['nodes'] if n['id'] not in remove_set]
        output['edges'] = [
            e for e in output['edges']
            if e['source'] not in remove_set and e['target'] not in remove_set
        ]

        output['_meta']['nodes_in_graph'] = len(output['nodes'])
        output['_meta']['edges_in_graph'] = len(output['edges'])

        serialized = json.dumps(output, separators=(',', ':'))
        size = len(serialized.encode('utf-8'))

    return output


# ============================================================
# main()
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Build a dependency graph for the Code Map website section.'
    )
    parser.add_argument('repo_path',          help='Absolute path to the target repository')
    parser.add_argument('--language',         default='TypeScript', help='Primary language (default: TypeScript)')
    parser.add_argument('--max-nodes',        default=200, type=int, help='Max nodes in output graph (default: 200)')
    parser.add_argument('--output',           default='graph-data.json', help='Output JSON path (default: graph-data.json)')
    parser.add_argument('--include-tests',    action='store_true', help='Include test files in graph')
    parser.add_argument('--min-connections',  default=1, type=int, help='Min connections for connected strategy (default: 1)')
    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo_path)

    # Collect files
    files = collect_files(repo_path, args.language, args.include_tests)

    if not files:
        output = {
            'nodes': [], 'edges': [], 'folder_expansions': {},
            '_meta': {'total_files_scanned': 0, 'nodes_in_graph': 0,
                      'edges_in_graph': 0, 'files_collapsed_into_folders': 0, 'output_size_kb': 0},
        }
        Path(args.output).write_text(json.dumps(output, indent=2), encoding='utf-8')
        print(f'Scanned 0 files → 0 nodes, 0 edges (0KB)', file=sys.stderr)
        return

    # Build graph
    adjacency  = build_adjacency(files, args.language)
    scores     = score_connectivity(files, adjacency)

    # Enrich files with scores/tier
    for f in files:
        f['connectivity'] = scores.get(f['rel'], 0)
        f['tier'] = compute_tier(f['connectivity'])

    selected_set, collapsed_set = select_nodes(files, scores, args.max_nodes, args.min_connections)

    selected_files = [f for f in files if f['rel'] in selected_set]
    folder_nodes, folder_edges = build_folder_nodes(collapsed_set, adjacency, selected_set, files)

    output = build_output(
        selected_files, folder_nodes, adjacency, selected_set, files, scores, folder_edges
    )

    # Progressive cap
    output = progressive_cap(output, max_kb=500)

    # Serialize and compute size
    serialized = json.dumps(output, indent=2)
    size_kb = round(len(serialized.encode('utf-8')) / 1024, 1)
    output['_meta']['output_size_kb'] = size_kb

    # Write output
    Path(args.output).write_text(json.dumps(output, indent=2), encoding='utf-8')

    total     = output['_meta']['total_files_scanned']
    nodes_out = output['_meta']['nodes_in_graph']
    edges_out = output['_meta']['edges_in_graph']
    print(f'Scanned {total} files → {nodes_out} nodes, {edges_out} edges ({size_kb}KB)', file=sys.stderr)


if __name__ == '__main__':
    main()
