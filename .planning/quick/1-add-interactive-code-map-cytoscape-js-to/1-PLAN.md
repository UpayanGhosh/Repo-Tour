---
phase: quick-1-code-map
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - repo-tour/scripts/build_graph.py
  - repo-tour/scripts/generate_site.py
  - repo-tour/templates/index.html
  - repo-tour/SKILL.md
  - repo-tour/references/ANALYSIS_GUIDE.md
autonomous: true
requirements:
  - CODE-MAP-01
must_haves:
  truths:
    - "Running `python build_graph.py <repo> --language TypeScript --max-nodes 200 --output graph-data.json` produces valid graph-data.json with nodes, edges, and folder_expansions keys"
    - "Running `python generate_site.py --analysis ... --content-dir ... --templates ... --output ... --graph graph-data.json` produces index.html that contains a Code Map section with a Cytoscape.js canvas"
    - "The Code Map section renders an interactive node-edge graph with hover tooltips, search, role-filter chips, and folder expand on click"
    - "If graph-data.json is not passed, the site generates normally with no Code Map section and no error"
    - "Cytoscape.js is loaded from CDN in index.html; if it fails to load, a static fallback table of top nodes renders instead"
    - "graph-data.json never enters LLM context — it is produced by build_graph.py and consumed directly by generate_site.py"
  artifacts:
    - path: "repo-tour/scripts/build_graph.py"
      provides: "Zero-dep Python CLI that walks a repo, parses imports, scores connectivity, reduces to max-nodes, outputs graph-data.json"
      exports: ["main CLI entrypoint: build_graph.py <repo_path> --language ... --max-nodes ... --output ..."]
    - path: "repo-tour/scripts/generate_site.py"
      provides: "Updated site generator with gen_code_map() + --graph CLI arg + CODE_MAP injection in assemble()"
      contains: "gen_code_map, --graph, CODE_MAP"
    - path: "repo-tour/templates/index.html"
      provides: "Template with Cytoscape CDN script tag and {{CODE_MAP}} placeholder after {{ARCHITECTURE}}"
      contains: "cytoscape@3.30.4, {{CODE_MAP}}"
  key_links:
    - from: "repo-tour/scripts/build_graph.py"
      to: "graph-data.json"
      via: "json.dump at end of main()"
      pattern: "json\\.dump"
    - from: "repo-tour/scripts/generate_site.py"
      to: "gen_code_map"
      via: "--graph CLI arg loaded in main(), passed to gen_code_map()"
      pattern: "args\\.graph"
    - from: "gen_code_map"
      to: "{{CODE_MAP}} in assemble()"
      via: "sections_html['code_map'] key"
      pattern: "CODE_MAP"
    - from: "templates/index.html"
      to: "Cytoscape canvas"
      via: "{{CODE_MAP}} placeholder replaced with generated section HTML"
      pattern: "\\{\\{CODE_MAP\\}\\}"
---

<objective>
Add an interactive Code Map section — a Cytoscape.js dependency graph — to the RepoTour generated website. The feature follows a strict two-tier pipeline: build_graph.py (new) processes the repo and outputs graph-data.json, which generate_site.py reads directly and embeds as inline JS. Graph data never enters LLM context.

Purpose: Give developers a visual Obsidian-style map of their codebase as part of the generated site, with zero additional LLM cost.
Output: build_graph.py script, updated generate_site.py with gen_code_map(), updated index.html template, updated SKILL.md and ANALYSIS_GUIDE.md, synced to ~/.claude/skills/tldr/.
</objective>

<execution_context>
@C:/Users/upayan.ghosh/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/upayan.ghosh/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@repo-tour/SKILL.md
@repo-tour/scripts/generate_site.py
@repo-tour/templates/index.html
@repo-tour/references/ANALYSIS_GUIDE.md

<interfaces>
<!-- Key patterns from existing generate_site.py that build_graph.py and new gen_code_map() must match -->

From repo-tour/scripts/generate_site.py:

```python
# parse_args() pattern — new --graph arg must follow this style:
def parse_args():
    p = argparse.ArgumentParser(...)
    p.add_argument('--analysis',    required=True, ...)
    p.add_argument('--content-dir', required=True, ...)
    p.add_argument('--templates',   required=True, ...)
    p.add_argument('--output',      required=True, ...)
    return p.parse_args()
# Add: p.add_argument('--graph', required=False, default=None, help='Path to graph-data.json from build_graph.py')

# gen_* function signature pattern:
def gen_overview(data):      # data = content dict or None
    if not data:
        return ''
    return '''<section class="section" id="...">...</section>'''

# gen_code_map must follow same pattern:
def gen_code_map(graph_data, modules_content):
    if not graph_data:
        return ''
    # ... returns full HTML section string

# assemble() replacements dict — add after '{{ARCHITECTURE}}':
'{{CODE_MAP}}': sections_html.get('code_map', ''),

# main() sections_html dict — add after 'mindmap':
'code_map': gen_code_map(graph_data, content.get('modules')),

# main() build sequence:
graph_data = None
if args.graph:
    graph_data = load_json(args.graph)

# build_navigation() SECTION_MAP list — add entry:
('code_map', 'code-map', 'Code Map'),
# Show only when graph_data is truthy — add has_codemap param like has_mindmap
```

From repo-tour/templates/index.html (lines 70-82):
```html
{{OVERVIEW}}
{{ARCHITECTURE}}
{{MINDMAP}}          <!-- existing -->
{{CROSS_CUTTING}}
...
{{COOKBOOK}}
```
New placement: `{{CODE_MAP}}` goes immediately after `{{ARCHITECTURE}}` and before `{{MINDMAP}}`.

Cytoscape CDN tag goes after any existing D3 script tag:
```html
<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.30.4/dist/cytoscape.min.js"
        onerror="window.CYTOSCAPE_FAILED=true"></script>
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create repo-tour/scripts/build_graph.py</name>
  <files>repo-tour/scripts/build_graph.py</files>
  <action>
Create a new file `repo-tour/scripts/build_graph.py` — a stdlib-only Python CLI that walks a repo and outputs graph-data.json. No pip dependencies.

**CLI interface:**
```
python build_graph.py <repo_path> --language TypeScript --max-nodes 200 --output graph-data.json [--include-tests] [--min-connections N]
```

**Implementation structure:**

1. **Constants / config block**
   - SKIP_DIRS: `{'node_modules', '.git', 'vendor', 'dist', 'build', '__pycache__', '.next', 'target', 'bin', 'obj', '.repotour'}`
   - SOURCE_EXTENSIONS per language (fall back to common set if language not matched)
   - ROLE_PATTERNS: dict mapping role name → list of path substring patterns:
     - service: `['/service', '/services/', 'Service.', 'service.']`
     - route: `['/route', '/routes/', '/router', '/controllers/', '/api/', 'route.', 'Route.', 'Controller.']`
     - model: `['/model', '/models/', '/entity', '/entities/', 'Model.', 'Entity.', '.model.', 'schema.', 'Schema.']`
     - utility: `['/util', '/utils/', '/helpers/', '/lib/', 'util.', 'helper.', 'helpers.']`
     - config: `['/config', '/configs/', '.config.', 'config.', 'Config.', 'settings.', '.env']`
     - middleware: `['/middleware', '/middlewares/', 'Middleware.', 'middleware.']`
     - test: `['/test', '/tests/', '/spec', '/__tests__/', '.test.', '.spec.', '_test.', '_spec.']`
     - migration: `['/migration', '/migrations/', 'migration.', 'Migration.']`
     - build: `['webpack', 'rollup', 'vite', 'babel', 'jest.config', 'tsconfig', 'package.json', 'Makefile', 'Dockerfile', 'Cargo.toml', 'pom.xml', 'build.gradle']`
   - ROLE_COLORS (hue values for OKLCH): `{'service': 262, 'route': 200, 'model': 145, 'utility': 240, 'config': 60, 'middleware': 290, 'test': 220, 'migration': 320, 'build': 30, 'folder': 50}`
   - SCALE_THRESHOLDS: `[(50, 'all'), (300, 'nontrivial'), (1000, 'connected'), (5000, 'top150'), (float('inf'), 'top200')]`

2. **`count_lines(path)`** — open with errors='ignore', count non-blank lines, return int

3. **`classify_role(rel_path)`** — iterate ROLE_PATTERNS, return first matching role, default 'utility'

4. **`collect_files(repo_path, language, include_tests)`**
   - Walk with os.walk, skip SKIP_DIRS by modifying dirs in-place
   - Filter by extension for the given language (if unknown language, use broad set: `.py .js .ts .jsx .tsx .go .rs .java .kt .cs .rb .php .cpp .c .h`)
   - If not include_tests: skip files where classify_role returns 'test'
   - Return list of dicts: `{'path': abs_path, 'rel': rel_path, 'loc': count_lines(abs_path), 'role': classify_role(rel_path)}`

5. **Import parsers** — one function per language family, each returns list of import strings:
   - `parse_imports_js(content, rel_path)` — regex: `(?:import|from)\s+['"]([^'"]+)['"]` and `require\(['"]([^'"]+)['"]\)` — collect all matches
   - `parse_imports_python(content, rel_path)` — regex: `^from\s+([\w.]+)\s+import` and `^import\s+([\w.,\s]+)` per line
   - `parse_imports_go(content, rel_path)` — extract import blocks and single imports: `"([^"]+)"`
   - `parse_imports_rust(content, rel_path)` — `^use\s+([\w:]+)` and `^mod\s+(\w+)` per line
   - `parse_imports_java(content, rel_path)` — `^import\s+([\w.]+);` per line
   - `parse_imports_csharp(content, rel_path)` — `^using\s+([\w.]+);` per line
   - Dispatcher `parse_imports(content, rel_path, language)` — routes to correct parser

6. **`resolve_import(import_str, source_rel, all_rel_paths_set)`**
   - If import starts with `.` (relative): join with source file's directory, normalize, try to find in all_rel_paths_set with .ts/.tsx/.js/.jsx/.py extensions appended
   - If import contains `/` and doesn't start with `@` (non-npm absolute): try matching against all_rel_paths_set by suffix
   - Otherwise: return None (external/npm dep, skip)
   - Return resolved rel_path string or None

7. **`build_adjacency(files, language)`**
   - For each file: read content (errors='ignore'), call parse_imports(), call resolve_import() for each
   - Build dict: `{rel_path: set_of_target_rel_paths}`
   - Return adjacency dict

8. **`score_connectivity(files, adjacency)`**
   - For each file compute in_degree (how many others import it), out_degree (how many it imports)
   - bidirectional = count of pairs where both A→B and B→A
   - connectivity = in_degree + out_degree + 2 * bidirectional
   - Return dict: `{rel_path: connectivity_score}`

9. **`select_nodes(files, scores, max_nodes, scale_strategy)`**
   - Determine strategy from SCALE_THRESHOLDS based on total file count
   - 'all': keep everything
   - 'nontrivial': keep files with loc > 20 and role not in ('test', 'config', 'build')
   - 'connected': keep files with connectivity >= min_connections (default 2)
   - 'top150': sort by score desc, keep top 150
   - 'top200': sort by score desc, keep top 200, cap at max_nodes param
   - Always honour max_nodes as hard cap (sort by score if needed)
   - Return (selected_set, collapsed_set) where collapsed = all_files - selected

10. **`build_folder_nodes(collapsed_set, adjacency, selected_set, files_meta)`**
    - Group collapsed files by their immediate parent directory (`os.path.dirname(rel_path)`)
    - For each folder: sum LOC, sum connectivity, collect children metadata
    - Folder node id: `f"folder:{dir_path}"`
    - Inherited edges: for each collapsed file in folder, for each of its adjacency targets that IS in selected_set → add edge from folder node to target (deduplicated)
    - Return list of folder_node dicts and list of folder_edge dicts

11. **`build_output(selected_files, folder_nodes, adjacency, selected_set, files_meta, scores, folder_expansions)`**
    - Compute tiers: connectivity >= 10 → 'critical', >= 4 → 'important', >= 1 → 'connected', else → 'isolated'
    - Nodes list: for each selected file → `{"id": rel_path, "label": os.path.basename(rel_path), "fullPath": rel_path, "role": role, "loc": loc, "connectivity": score, "tier": tier, "cluster": os.path.dirname(rel_path), "directory": os.path.dirname(rel_path), "type": "file"}`
    - Folder nodes appended with `"type": "folder"`, `"tier": "folder"`, `"childCount": N`
    - Edges list: for each (src, dst) in adjacency where both src and dst in selected_set → `{"source": src, "target": dst, "weight": 1}`. Deduplicate. Increment weight for duplicates.
    - Folder edges appended from build_folder_nodes output
    - folder_expansions dict: `{"folder:X": {"nodes": [...], "edges": [...]}}`
    - _meta: `{"total_files_scanned": N, "nodes_in_graph": M, "edges_in_graph": E, "files_collapsed_into_folders": K, "output_size_kb": 0}` (size filled after json.dumps)

12. **`progressive_cap(output, max_kb=500)`**
    - Serialize to JSON, check size
    - While size > max_kb * 1024 AND nodes > 30: remove 10% lowest-connectivity non-folder nodes, fold them into folder nodes (merge with existing folder node or create new one), re-serialize
    - Return final output dict

13. **`main()`**
    - argparse: positional `repo_path`, `--language` (default 'TypeScript'), `--max-nodes` (default 200, int), `--output` (default 'graph-data.json'), `--include-tests` (store_true), `--min-connections` (default 1, int)
    - Call collect_files → build_adjacency → score_connectivity → select_nodes → build_folder_nodes → build_output → progressive_cap
    - Update `_meta.output_size_kb` with actual size
    - Write JSON to --output path
    - Print summary to stderr: `f"Scanned {total} files → {nodes} nodes, {edges} edges ({size_kb}KB)"`

**Edge case handling:**
- Files that cannot be read (permissions): skip silently
- Circular imports: adjacency is fine (set), no infinite loops
- Empty repo: output valid JSON with empty nodes/edges
- Single file: one node, no edges
</action>
  <verify>
    <automated>cd "C:/Users/upayan.ghosh/Desktop/Skill" && python repo-tour/scripts/build_graph.py . --language Python --max-nodes 50 --output /tmp/test-graph-data.json && python -c "import json; d=json.load(open('/tmp/test-graph-data.json')); assert 'nodes' in d and 'edges' in d and '_meta' in d and 'folder_expansions' in d, f'Missing keys: {list(d.keys())}'; print('OK — nodes:', d['_meta']['nodes_in_graph'], 'edges:', d['_meta']['edges_in_graph'], 'size:', d['_meta']['output_size_kb'], 'KB')"</automated>
  </verify>
  <done>build_graph.py exists, runs without error on the skill repo itself, produces valid graph-data.json with all required keys (_meta, nodes, edges, folder_expansions), nodes have id/label/fullPath/role/loc/connectivity/tier/cluster/directory/type fields, edges have source/target/weight fields</done>
</task>

<task type="auto">
  <name>Task 2: Update generate_site.py — add gen_code_map() and --graph arg</name>
  <files>repo-tour/scripts/generate_site.py</files>
  <action>
Modify `repo-tour/scripts/generate_site.py` with targeted additions. Read the file first, then apply changes.

**Change 1 — parse_args():** Add optional `--graph` argument after existing args:
```python
p.add_argument('--graph', required=False, default=None,
               help='Path to graph-data.json produced by build_graph.py (optional)')
```

**Change 2 — Add gen_code_map() function** after gen_mindmap() (around line 670 area, before gen_cookbook). This function generates a full self-contained HTML section:

```python
def gen_code_map(graph_data, modules_content):
    """Build interactive Cytoscape.js code dependency map section."""
    if not graph_data:
        return ''

    nodes = graph_data.get('nodes', [])
    edges = graph_data.get('edges', [])
    meta  = graph_data.get('_meta', {})
    folder_expansions = graph_data.get('folder_expansions', {})

    if not nodes:
        return ''

    # Build modules lookup: path → simple_explanation
    mod_lookup = {}
    if modules_content:
        mods = modules_content if isinstance(modules_content, list) else []
        for m in mods:
            p = m.get('path', '')
            if p:
                mod_lookup[p] = m.get('behavior', '') or m.get('simple_explanation', '') or ''

    # Enrich nodes with simple_explanation
    enriched_nodes = []
    for n in nodes:
        nd = dict(n)
        nd['simple_explanation'] = mod_lookup.get(n.get('fullPath', ''), '')
        enriched_nodes.append(nd)

    # Role → OKLCH hue map
    ROLE_HUES = {
        'service': 262, 'route': 200, 'model': 145, 'utility': 240,
        'config': 60,   'middleware': 290, 'test': 220, 'migration': 320,
        'build': 30,    'folder': 50,
    }

    # Gather distinct roles for filter chips
    roles = sorted({n.get('role', 'utility') for n in enriched_nodes})

    # Build filter chips HTML
    chip_items = ''.join(
        f'<button class="cm-chip" data-role="{e(r)}" style="--chip-hue:{ROLE_HUES.get(r, 240)}" aria-pressed="true">{e(r)}</button>'
        for r in roles
    )

    # Build stats bar
    stats_html = (
        f'<span class="cm-stat">{meta.get("nodes_in_graph", len(nodes))} nodes</span>'
        f'<span class="cm-stat">{meta.get("edges_in_graph", len(edges))} edges</span>'
        f'<span class="cm-stat">{meta.get("total_files_scanned", "?")} files scanned</span>'
    )
    if meta.get('files_collapsed_into_folders', 0):
        stats_html += f'<span class="cm-stat">{meta["files_collapsed_into_folders"]} collapsed into folders</span>'

    # Serialize graph data for inline JS
    cy_nodes = [
        {'data': {
            'id': n['id'],
            'label': n.get('label', n['id']),
            'fullPath': n.get('fullPath', n['id']),
            'role': n.get('role', 'utility'),
            'loc': n.get('loc', 0),
            'connectivity': n.get('connectivity', 0),
            'tier': n.get('tier', 'isolated'),
            'type': n.get('type', 'file'),
            'childCount': n.get('childCount', 0),
            'simple_explanation': n.get('simple_explanation', ''),
        }}
        for n in enriched_nodes
    ]
    cy_edges = [
        {'data': {
            'id': f'e-{i}',
            'source': eg['source'],
            'target': eg['target'],
            'weight': eg.get('weight', 1),
        }}
        for i, eg in enumerate(edges)
    ]

    graph_json     = json.dumps({'nodes': cy_nodes, 'edges': cy_edges}, separators=(',', ':'))
    expansion_json = json.dumps(folder_expansions, separators=(',', ':'))
    role_hues_json = json.dumps(ROLE_HUES)

    # Inline JS — full Cytoscape init + interactions
    # The JS is a multi-line string embedded directly in the returned HTML section.
    inline_js = f"""
(function(){{
  if(window.CYTOSCAPE_FAILED||typeof cytoscape==='undefined'){{
    // Fallback: static table
    var nodes=GRAPH_DATA.nodes.map(function(n){{return n.data;}});
    nodes.sort(function(a,b){{return b.connectivity-a.connectivity;}});
    var rows=nodes.slice(0,50).map(function(n){{
      return '<tr><td>'+n.fullPath+'</td><td>'+n.role+'</td><td>'+n.loc+'</td><td>'+n.connectivity+'</td></tr>';
    }}).join('');
    document.getElementById('code-map-fallback').innerHTML=
      '<table style="width:100%;border-collapse:collapse;font-size:0.8rem"><thead><tr><th>File</th><th>Role</th><th>LOC</th><th>Connections</th></tr></thead><tbody>'+rows+'</tbody></table>';
    document.getElementById('code-map-canvas-wrap').style.display='none';
    document.getElementById('code-map-fallback').style.display='block';
    return;
  }}

  var ROLE_HUES={role_hues_json};
  function roleColor(role){{
    var h=ROLE_HUES[role]||240;
    return 'oklch(58% 0.18 '+h+')';
  }}
  function roleColorSubtle(role){{
    var h=ROLE_HUES[role]||240;
    return 'oklch(94% 0.04 '+h+')';
  }}

  var cy=cytoscape({{
    container: document.getElementById('code-map-cy'),
    elements: GRAPH_DATA,
    style: [
      {{
        selector: 'node[type="file"]',
        style: {{
          'label': 'data(label)',
          'width': 'mapData(connectivity, 1, 20, 18, 52)',
          'height': 'mapData(connectivity, 1, 20, 18, 52)',
          'background-color': function(ele){{ return roleColor(ele.data('role')); }},
          'color': 'var(--text-secondary)',
          'font-size': 9,
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 4,
          'text-max-width': 80,
          'text-wrap': 'ellipsis',
          'border-width': 0,
          'border-color': 'transparent',
          'z-index': 10,
        }}
      }},
      {{
        selector: 'node[type="folder"]',
        style: {{
          'label': 'data(label)',
          'shape': 'diamond',
          'width': 'mapData(connectivity, 1, 30, 28, 64)',
          'height': 'mapData(connectivity, 1, 30, 28, 64)',
          'background-color': function(ele){{ return roleColor(ele.data('role')); }},
          'border-width': 2,
          'border-style': 'dashed',
          'border-color': function(ele){{ return roleColor(ele.data('role')); }},
          'opacity': 0.75,
          'color': 'var(--text-secondary)',
          'font-size': 9,
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 4,
          'z-index': 5,
        }}
      }},
      {{
        selector: 'edge',
        style: {{
          'width': 1,
          'opacity': 0.35,
          'line-color': 'var(--text-secondary)',
          'target-arrow-color': 'var(--text-secondary)',
          'target-arrow-shape': 'triangle',
          'arrow-scale': 0.7,
          'curve-style': 'bezier',
          'z-index': 1,
        }}
      }},
      {{
        selector: '.highlighted',
        style: {{
          'border-width': 2.5,
          'border-color': 'oklch(78% 0.18 80)',
          'opacity': 1,
          'z-index': 999,
        }}
      }},
      {{
        selector: '.faded',
        style: {{ 'opacity': 0.08 }}
      }},
      {{
        selector: '.search-match',
        style: {{
          'border-width': 2.5,
          'border-color': 'oklch(58% 0.22 25)',
          'opacity': 1,
          'z-index': 999,
        }}
      }},
    ],
    layout: {{
      name: 'cose',
      nodeRepulsion: 4500,
      idealEdgeLength: 120,
      gravity: 0.8,
      numIter: 1000,
      animate: true,
      animationDuration: 800,
      fit: true,
      padding: 40,
    }},
  }});

  // Tooltip
  var tooltip=document.getElementById('code-map-tooltip');
  cy.on('mouseover','node',function(evt){{
    var n=evt.target.data();
    var expl=n.simple_explanation?'<p style="margin:4px 0 0;color:var(--text-secondary);font-size:0.78rem">'+n.simple_explanation+'</p>':'';
    tooltip.innerHTML='<strong style="font-size:0.85rem">'+n.label+'</strong>'
      +'<br><span style="color:var(--text-secondary);font-size:0.78rem">'+n.fullPath+'</span>'
      +'<br><span style="font-size:0.78rem">'+n.role+' · '+n.loc+' LOC · '+n.connectivity+' connections</span>'
      +expl;
    tooltip.style.display='block';
    cy.elements().addClass('faded');
    evt.target.removeClass('faded').addClass('highlighted');
    evt.target.neighborhood().removeClass('faded').addClass('highlighted');
  }});
  cy.on('mouseout','node',function(){{
    tooltip.style.display='none';
    cy.elements().removeClass('faded highlighted');
  }});
  document.getElementById('code-map-canvas-wrap').addEventListener('mousemove',function(e){{
    if(tooltip.style.display==='block'){{
      tooltip.style.left=(e.offsetX+14)+'px';
      tooltip.style.top=(e.offsetY+14)+'px';
    }}
  }});

  // Click: scroll to module section or expand folder
  cy.on('tap','node',function(evt){{
    var n=evt.target.data();
    if(n.type==='folder'){{
      var fid='folder:'+n.id.replace(/^folder:/,'');
      var exp=FOLDER_EXPANSIONS[fid]||FOLDER_EXPANSIONS[n.id];
      if(!exp)return;
      var toAdd=[];
      (exp.nodes||[]).forEach(function(nd){{
        if(!cy.getElementById(nd.id).length){{
          toAdd.push({{data:{{id:nd.id,label:nd.label||nd.id.split('/').pop(),fullPath:nd.id,role:nd.role||'utility',loc:nd.loc||0,connectivity:nd.connectivity||0,tier:nd.tier||'isolated',type:'file',childCount:0,simple_explanation:''}}}});
        }}
      }});
      (exp.edges||[]).forEach(function(eg,i){{
        toAdd.push({{data:{{id:'exp-'+i+'-'+eg.source+'-'+eg.target,source:eg.source,target:eg.target,weight:eg.weight||1}}}});
      }});
      if(toAdd.length){{
        cy.add(toAdd);
        cy.layout({{name:'cose',animate:true,animationDuration:600,fit:false,padding:40,nodeRepulsion:4500,idealEdgeLength:120}}).run();
      }}
    }} else {{
      var slug=n.fullPath.replace(/[/\\.]/g,'-').toLowerCase();
      var el=document.getElementById('module-'+slug);
      if(el)el.scrollIntoView({{behavior:'smooth'}});
    }}
  }});

  // Search (debounced 200ms)
  var searchTimer;
  document.getElementById('cm-search').addEventListener('input',function(){{
    clearTimeout(searchTimer);
    var q=this.value.trim().toLowerCase();
    searchTimer=setTimeout(function(){{
      cy.elements().removeClass('search-match faded');
      if(!q)return;
      cy.nodes().forEach(function(n){{
        var match=n.data('label').toLowerCase().includes(q)||n.data('fullPath').toLowerCase().includes(q);
        if(match)n.addClass('search-match');
        else n.addClass('faded');
      }});
    }},200);
  }});

  // Filter chips
  var activeRoles=new Set({json.dumps(roles)});
  document.querySelectorAll('.cm-chip').forEach(function(chip){{
    chip.addEventListener('click',function(){{
      var role=this.dataset.role;
      var pressed=this.getAttribute('aria-pressed')==='true';
      if(pressed){{
        activeRoles.delete(role);
        this.setAttribute('aria-pressed','false');
        this.style.opacity='0.4';
      }}else{{
        activeRoles.add(role);
        this.setAttribute('aria-pressed','true');
        this.style.opacity='1';
      }}
      cy.nodes().forEach(function(n){{
        if(activeRoles.has(n.data('role')))n.removeClass('faded');
        else n.addClass('faded');
      }});
    }});
  }});

  // Layout toggle
  var layoutMode='cose';
  document.getElementById('cm-layout-toggle').addEventListener('click',function(){{
    layoutMode=layoutMode==='cose'?'breadthfirst':'cose';
    this.textContent=layoutMode==='cose'?'Switch to Grid':'Switch to Force';
    var opts=layoutMode==='cose'
      ?{{name:'cose',animate:true,nodeRepulsion:4500,idealEdgeLength:120,gravity:0.8,numIter:1000}}
      :{{name:'breadthfirst',animate:true,spacingFactor:1.5}};
    cy.layout(opts).run();
  }});

  // Fit button
  document.getElementById('cm-fit').addEventListener('click',function(){{ cy.fit(40); }});

  // Fullscreen
  var wrap=document.getElementById('code-map-canvas-wrap');
  document.getElementById('cm-fullscreen').addEventListener('click',function(){{
    wrap.classList.toggle('cm-fullscreen-mode');
    var isFs=wrap.classList.contains('cm-fullscreen-mode');
    this.textContent=isFs?'Exit Fullscreen':'Fullscreen';
    setTimeout(function(){{ cy.fit(40); }},200);
  }});
  document.addEventListener('keydown',function(e){{
    if(e.key==='Escape'){{
      wrap.classList.remove('cm-fullscreen-mode');
      document.getElementById('cm-fullscreen').textContent='Fullscreen';
      setTimeout(function(){{cy.fit(40);}},200);
    }}
  }});

}})();
"""

    # Legend items HTML
    legend_items = ''.join(
        f'<span class="cm-legend-item"><span class="cm-legend-dot" style="background:oklch(58% 0.18 {ROLE_HUES.get(r, 240)}deg)"></span>{e(r)}</span>'
        for r in roles
    )

    return f'''<section class="section" id="code-map">
  <p class="section-label">Code Map</p>
  <h2 class="section-title">Dependency Graph</h2>
  <p style="font-size:0.9rem;color:var(--text-secondary);margin-bottom:1rem">
    Every important file is a node. Every import is an edge. Hover to inspect, click a file to jump to its module doc, click a folder node to expand it.
  </p>

  <!-- Controls bar -->
  <div style="display:flex;flex-wrap:wrap;gap:0.5rem;align-items:center;margin-bottom:0.75rem">
    <input id="cm-search" type="search" placeholder="Search files..." aria-label="Search code map nodes"
      style="flex:1;min-width:140px;max-width:220px;padding:0.3rem 0.6rem;border:1px solid var(--border);border-radius:6px;font-size:0.82rem;background:var(--surface);color:var(--text-primary)">
    <div style="display:flex;flex-wrap:wrap;gap:0.35rem;align-items:center">{chip_items}</div>
    <div style="margin-left:auto;display:flex;gap:0.4rem">
      <button id="cm-layout-toggle" class="cm-ctrl-btn" title="Toggle layout algorithm">Switch to Grid</button>
      <button id="cm-fit" class="cm-ctrl-btn" title="Fit graph to viewport">Fit</button>
      <button id="cm-fullscreen" class="cm-ctrl-btn" title="Toggle fullscreen (Esc to exit)">Fullscreen</button>
    </div>
  </div>

  <!-- Stats -->
  <div style="display:flex;flex-wrap:wrap;gap:0.6rem;margin-bottom:0.75rem;font-size:0.78rem;color:var(--text-secondary)">{stats_html}</div>

  <!-- Canvas wrapper -->
  <div id="code-map-canvas-wrap" style="position:relative;border:1px solid var(--border);border-radius:8px;overflow:hidden">
    <div id="code-map-cy" style="width:100%;height:480px;background:var(--surface)"></div>
    <div id="code-map-tooltip" style="display:none;position:absolute;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:0.6rem 0.75rem;max-width:280px;pointer-events:none;z-index:100;box-shadow:0 4px 12px rgba(0,0,0,0.15)"></div>
  </div>

  <!-- Fallback for no Cytoscape -->
  <div id="code-map-fallback" style="display:none"></div>

  <!-- Legend -->
  <div style="display:flex;flex-wrap:wrap;gap:0.5rem;margin-top:0.75rem;font-size:0.78rem;color:var(--text-secondary);align-items:center">
    <span style="font-weight:500">Roles:</span>{legend_items}
    <span style="margin-left:0.5rem">&#9670; = folder node (click to expand)</span>
  </div>

  <style>
    .cm-chip{{padding:0.2rem 0.55rem;border:1.5px solid oklch(58% 0.18 calc(var(--chip-hue)*1deg));border-radius:999px;font-size:0.75rem;background:transparent;color:var(--text-primary);cursor:pointer;transition:opacity 0.15s}}
    .cm-ctrl-btn{{padding:0.25rem 0.6rem;border:1px solid var(--border);border-radius:6px;font-size:0.78rem;background:var(--surface);color:var(--text-primary);cursor:pointer}}
    .cm-ctrl-btn:hover{{background:var(--surface-hover,var(--surface));border-color:var(--accent)}}
    .cm-legend-item{{display:inline-flex;align-items:center;gap:0.3rem}}
    .cm-legend-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
    .cm-stat::after{{content:" |";margin-left:0.4rem;color:var(--border)}}
    .cm-stat:last-child::after{{content:""}}
    #code-map-canvas-wrap.cm-fullscreen-mode{{position:fixed;inset:0;z-index:9999;border-radius:0;border:none;height:100vh!important}}
    #code-map-canvas-wrap.cm-fullscreen-mode #code-map-cy{{height:100vh!important}}
  </style>

  <script>
    var GRAPH_DATA={graph_json};
    var FOLDER_EXPANSIONS={expansion_json};
    {inline_js}
  </script>
</section>'''
```

**Change 3 — build_navigation():** Add code_map entry to SECTION_MAP and add `has_codemap` parameter:
- Change signature to: `def build_navigation(content, has_mindmap=False, has_codemap=False):`
- Add to SECTION_MAP after the mindmap entry: `('code_map', 'code-map', 'Code Map'),`
- In the auto_show logic, add: `or (key == 'code_map' and has_codemap)`

**Change 4 — assemble():** Add to replacements dict after `'{{MINDMAP}}'`:
```python
'{{CODE_MAP}}':        sections_html.get('code_map', ''),
```

**Change 5 — main():**
- After `analysis = load_json(args.analysis)`, add:
  ```python
  graph_data = load_json(args.graph) if args.graph else None
  ```
- In sections_html dict, add after `'mindmap': mindmap_html,`:
  ```python
  'code_map':       gen_code_map(graph_data, content.get('modules')),
  ```
- Update build_navigation call:
  ```python
  nav_html = build_navigation(content, has_mindmap=bool(mindmap_html), has_codemap=bool(graph_data))
  ```
</action>
  <verify>
    <automated>cd "C:/Users/upayan.ghosh/Desktop/Skill" && python -c "import ast, sys; ast.parse(open('repo-tour/scripts/generate_site.py').read()); print('Syntax OK')" && python repo-tour/scripts/generate_site.py --help 2>&1 | grep -q "\-\-graph" && echo "--graph arg present"</automated>
  </verify>
  <done>generate_site.py parses without syntax errors, --graph argument appears in --help output, gen_code_map function is defined, CODE_MAP appears in assemble() replacements dict, sections_html dict includes code_map key</done>
</task>

<task type="auto">
  <name>Task 3: Update index.html, SKILL.md, ANALYSIS_GUIDE.md, and sync to ~/.claude/skills/tldr/</name>
  <files>
    repo-tour/templates/index.html
    repo-tour/SKILL.md
    repo-tour/references/ANALYSIS_GUIDE.md
  </files>
  <action>
Make three targeted file updates, then sync to the installed skill directory.

**Update 1 — repo-tour/templates/index.html:**

Read the file first. Make two changes:

a) Add the Cytoscape CDN script tag. Find the closing `</head>` tag or any existing CDN script tags in the `<head>` / just before `</body>`. Insert after any existing D3 script tag, or just before the closing `</body>` tag if no D3 tag exists:
```html
<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.30.4/dist/cytoscape.min.js" onerror="window.CYTOSCAPE_FAILED=true"></script>
```

b) Add `{{CODE_MAP}}` placeholder. In the body, find:
```
{{ARCHITECTURE}}
```
Insert `{{CODE_MAP}}` on the line immediately after `{{ARCHITECTURE}}` (before `{{MINDMAP}}`):
```
{{ARCHITECTURE}}
        {{CODE_MAP}}
        {{MINDMAP}}
```

**Update 2 — repo-tour/SKILL.md:**

Read the file first. Make two changes:

a) In Phase 1 SCAN section, after the `python map_dependencies.py ... > $WORK/rt_deps.json` block, add:
```
python scripts/build_graph.py <REPO> --language <LANG> --max-nodes 200 --output $WORK/graph-data.json
```
With a comment line before it: `# Build dependency graph for Code Map (runs separately — graph-data.json does NOT merge into repo-analysis.json)`

b) In Phase 3 GENERATE section, update the `python scripts/generate_site.py \` command block to add `--graph $WORK/graph-data.json \` as the last argument before the closing (or after `--output $WORK/site/`).

**Update 3 — repo-tour/references/ANALYSIS_GUIDE.md:**

Read the file first. In the `## Pipeline: Running the Scripts` section, after the `python map_dependencies.py` block, add:
```
python build_graph.py $REPO --language <LANG> --max-nodes 200 --output $WORK/graph-data.json
```
With a note: `# Produces graph-data.json for the Code Map website section. NOT merged into repo-analysis.json — consumed directly by generate_site.py.`

**Sync to ~/.claude/skills/tldr/:**

After all three files are updated, sync them to the installed skill location using Read then Write:

1. Read `repo-tour/SKILL.md` → Write to `C:/Users/upayan.ghosh/.claude/skills/tldr/SKILL.md`
2. Read `repo-tour/templates/index.html` → Write to `C:/Users/upayan.ghosh/.claude/skills/tldr/templates/index.html`
3. Read `repo-tour/references/ANALYSIS_GUIDE.md` → Write to `C:/Users/upayan.ghosh/.claude/skills/tldr/references/ANALYSIS_GUIDE.md`

Do NOT use shell cp/copy commands — use the Read then Write pattern exclusively.
</action>
  <verify>
    <automated>cd "C:/Users/upayan.ghosh/Desktop/Skill" && python -c "
content = open('repo-tour/templates/index.html').read()
assert '{{CODE_MAP}}' in content, 'Missing CODE_MAP placeholder in index.html'
assert 'cytoscape@3.30.4' in content, 'Missing Cytoscape CDN tag in index.html'
skill = open('repo-tour/SKILL.md').read()
assert 'build_graph.py' in skill, 'Missing build_graph.py in SKILL.md'
assert '--graph' in skill, 'Missing --graph in SKILL.md Phase 3'
guide = open('repo-tour/references/ANALYSIS_GUIDE.md').read()
assert 'build_graph.py' in guide, 'Missing build_graph.py in ANALYSIS_GUIDE.md'
synced = open('C:/Users/upayan.ghosh/.claude/skills/tldr/SKILL.md').read()
assert 'build_graph.py' in synced, 'SKILL.md not synced to ~/.claude/skills/tldr/'
print('All checks passed')
"</automated>
  </verify>
  <done>index.html has {{CODE_MAP}} placeholder after {{ARCHITECTURE}} and Cytoscape CDN script tag; SKILL.md has build_graph.py in Phase 1 and --graph in Phase 3 generate command; ANALYSIS_GUIDE.md mentions build_graph.py; all three files synced to ~/.claude/skills/tldr/</done>
</task>

</tasks>

<verification>
End-to-end smoke test — run build_graph.py on the skill repo itself, then generate_site.py with --graph to produce a site, and verify the output contains a Code Map section:

```bash
cd repo-tour/scripts
python build_graph.py "C:/Users/upayan.ghosh/Desktop/Skill" --language Python --max-nodes 50 --output /tmp/test-graph.json
# verify /tmp/test-graph.json has nodes > 0
python -c "import json; d=json.load(open('/tmp/test-graph.json')); assert d['_meta']['nodes_in_graph'] > 0"
# verify generate_site.py accepts --graph (syntax/arg check only — no full site build needed for CI)
python generate_site.py --help | grep -q "\-\-graph"
```

Check index.html template has both `{{CODE_MAP}}` and `cytoscape@3.30.4`.
</verification>

<success_criteria>
- `build_graph.py` runs on any repo, outputs valid graph-data.json with nodes/edges/folder_expansions/_meta
- `generate_site.py --graph graph-data.json` produces a site with a `<section id="code-map">` containing a Cytoscape canvas
- Without `--graph`, site generates normally with no Code Map section and no errors
- Code Map section has: search input, role filter chips, fit/fullscreen/layout-toggle buttons, tooltip on hover, folder expansion on click, static fallback table if Cytoscape fails to load
- SKILL.md Phase 1 lists build_graph.py; Phase 3 generate command includes `--graph`
- All changed files synced to `~/.claude/skills/tldr/`
</success_criteria>

<output>
After completion, create `.planning/quick/1-add-interactive-code-map-cytoscape-js-to/1-SUMMARY.md` with what was built, key decisions made, and any deviations from the plan.
</output>
