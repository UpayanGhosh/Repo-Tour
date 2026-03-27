#!/usr/bin/env python3
"""generate_site.py — Assembles final website from templates + content JSON. Zero LLM. Unlimited output."""

import os
import sys
import json
import html
import argparse
import glob
from pathlib import Path

# ============================================================
# CHUNK 1: Main + File Loading + Template Injection
# ============================================================

LANGUAGE_COLORS = {
    'TypeScript':   'oklch(58% 0.20 250)',   # blue
    'JavaScript':   'oklch(75% 0.18 90)',    # yellow
    'Python':       'oklch(65% 0.18 145)',   # green
    'Rust':         'oklch(65% 0.20 35)',    # orange
    'Go':           'oklch(65% 0.18 200)',   # cyan
    'Java':         'oklch(58% 0.22 25)',    # red
    'Kotlin':       'oklch(60% 0.20 290)',   # purple
    'C#':           'oklch(60% 0.20 290)',   # purple
    'Ruby':         'oklch(58% 0.22 10)',    # rose
    'PHP':          'oklch(60% 0.18 270)',   # indigo
}

# Typography pairings keyed by project name hash mod 4
# Each tuple: (heading_family_query, body_family_query, heading_css_name, body_css_name)
# JetBrains Mono is appended to every URL automatically in get_font_pairing().
FONT_PAIRINGS = [
    # 0: Fraunces (warm optical serif) + Figtree (rounded humanist sans)
    (
        'Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300',
        'Figtree:wght@300;400;500;600',
        'Fraunces',
        'Figtree',
    ),
    # 1: DM Serif Display + DM Sans — Google's own refined editorial pair
    (
        'DM+Serif+Display:ital@0;1',
        'DM+Sans:ital,opsz,wght@0,9..40,300..600;1,9..40,300',
        'DM Serif Display',
        'DM Sans',
    ),
    # 2: Instrument Serif + Instrument Sans — contemporary, clean, Figma-ish
    (
        'Instrument+Serif:ital@0;1',
        'Instrument+Sans:ital,wght@0,400;0,500;0,600;1,400',
        'Instrument Serif',
        'Instrument Sans',
    ),
    # 3: Libre Baskerville + Jost — scholarly warmth + clean geometric
    (
        'Libre+Baskerville:ital,wght@0,400;0,700;1,400',
        'Jost:ital,wght@0,300;0,400;0,500;0,600;1,400',
        'Libre Baskerville',
        'Jost',
    ),
]


def parse_args():
    p = argparse.ArgumentParser(description='Generate RepoTour website from content JSON')
    p.add_argument('--analysis',    required=True, help='Path to repo-analysis.json')
    p.add_argument('--content-dir', required=True, help='Directory with site-content/*.json files')
    p.add_argument('--templates',   required=True, help='Path to templates/ directory')
    p.add_argument('--output',      required=True, help='Output directory')
    p.add_argument('--graph',       required=False, default=None,
                   help='Path to graph-data.json produced by build_graph.py (optional)')
    return p.parse_args()


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception as e:
        print(f'Warning: could not load {path}: {e}', file=sys.stderr)
        return {}


def load_templates(templates_dir):
    td = Path(templates_dir)
    return {
        'html': (td / 'index.html').read_text(encoding='utf-8'),
        'css':  (td / 'styles.css').read_text(encoding='utf-8'),
        'js':   (td / 'app.js').read_text(encoding='utf-8'),
    }


def load_all_content(content_dir):
    """Load all site-content/*.json files; merge module batches into one list."""
    cd = Path(content_dir)
    content = {}
    module_batches = {}

    for f in sorted(cd.glob('*.json')):
        name = f.stem
        data = load_json(str(f))
        if name.startswith('modules_batch_'):
            idx = int(name.split('_')[-1])
            module_batches[idx] = data
        else:
            content[name] = data

    # Merge module batches in order
    if module_batches:
        all_modules = []
        for i in sorted(module_batches.keys()):
            batch = module_batches[i]
            if isinstance(batch, list):
                all_modules.extend(batch)
        content['modules'] = all_modules

    return content


def get_font_pairing(project_name):
    idx = sum(ord(c) for c in project_name) % len(FONT_PAIRINGS)
    pair = FONT_PAIRINGS[idx]
    url = (
        'https://fonts.googleapis.com/css2'
        f'?family={pair[0]}'
        f'&family={pair[1]}'
        '&family=JetBrains+Mono:wght@400;500'
        '&display=swap'
    )
    return url, pair[2], pair[3]


def get_color_vars(language):
    val = LANGUAGE_COLORS.get(language, 'oklch(55% 0.08 264)')
    return f':root{{--accent:{val};--accent-dim:oklch(from {val} calc(l - 0.06) c h);--accent-subtle:oklch(from {val} calc(l + 0.38) calc(c * 0.2) h);}}'


def assemble(templates, sections_html, nav_html, search_index_js, analysis, project_name):
    """Replace all {{PLACEHOLDER}} markers in the HTML template."""
    lang = (analysis.get('stack') or {}).get('primary_language', 'Unknown')
    font_url, font_heading, font_body = get_font_pairing(project_name)
    color_vars = get_color_vars(lang)

    out = templates['html']
    replacements = {
        '{{PROJECT_NAME}}':    html.escape(project_name),
        '{{CSS}}':             templates['css'],
        '{{JS}}':              templates['js'],
        '{{COLOR_VARS}}':      color_vars,
        '{{NAV}}':             nav_html,
        '{{OVERVIEW}}':        sections_html.get('overview', ''),
        '{{ARCHITECTURE}}':    sections_html.get('architecture', ''),
        '{{MINDMAP}}':         sections_html.get('mindmap', ''),
        '{{CODE_MAP}}':        sections_html.get('code_map', ''),
        '{{CROSS_CUTTING}}':   sections_html.get('cross_cutting', ''),
        '{{TECH_STACK}}':      sections_html.get('tech_stack', ''),
        '{{ENTRY_POINTS}}':    sections_html.get('entry_points', ''),
        '{{MODULES}}':         sections_html.get('modules', ''),
        '{{WORKFLOWS}}':       sections_html.get('workflows', ''),
        '{{DIRECTORY_GUIDE}}': sections_html.get('directory_guide', ''),
        '{{GLOSSARY}}':        sections_html.get('glossary', ''),
        '{{GETTING_STARTED}}': sections_html.get('getting_started', ''),
        '{{COOKBOOK}}':        sections_html.get('cookbook', ''),
        '{{SEARCH_INDEX}}':    search_index_js,
        '{{FONT_URL}}':        font_url,
        '{{FONT_HEADING}}':    font_heading,
        '{{FONT_BODY}}':       font_body,
    }
    for key, val in replacements.items():
        out = out.replace(key, val)
    return out


# ============================================================
# CHUNK 2: Per-Section HTML Generators
# ============================================================

def e(s):
    """html.escape shorthand."""
    return html.escape(str(s)) if s is not None else ''


def gen_overview(data):
    if not data:
        return ''
    return f'''<section class="section" id="overview">
  <p class="section-label">Overview</p>
  <h2 class="section-title">What is this project?</h2>
  <p style="font-size:1.1rem;line-height:1.7;color:var(--text-primary)">{e(data.get("summary",""))}</p>
  {f'<p><strong>Audience:</strong> {e(data.get("audience",""))}</p>' if data.get("audience") else ""}
  {f'<p><strong>Approach:</strong> {e(data.get("approach",""))}</p>' if data.get("approach") else ""}
</section>'''


def gen_architecture(data):
    if not data:
        return ''
    layers_html = ''
    for layer in (data.get('layers') or []):
        files_html = ''.join(f'<span class="relation-chip">{e(f)}</span>' for f in (layer.get('key_files') or [])[:4])
        layers_html += f'''<div class="module-card" style="margin-bottom:0.75rem">
    <div class="module-name">{e(layer.get("name",""))}</div>
    <p style="font-size:0.875rem;color:var(--text-secondary);margin:0.3rem 0 0.5rem">{e(layer.get("responsibility",""))}</p>
    <div class="module-relations">{files_html}</div>
  </div>'''

    mermaid_html = ''
    if data.get('mermaid'):
        mermaid_html = f'<div class="mermaid-wrap mermaid-hero"><div class="mermaid" data-clickable="true" data-diagram="{e(data["mermaid"])}"></div></div>'

    return f'''<section class="section" id="architecture">
  <p class="section-label">Architecture</p>
  <h2 class="section-title">How is it organized?</h2>
  {f'<p style="font-size:1rem;color:var(--text-secondary);margin-bottom:1.5rem;font-style:italic">{e(data.get("analogy",""))}</p>' if data.get("analogy") else ""}
  {mermaid_html}
  {('<h3 style="margin-top:1.5rem;margin-bottom:1rem">Layers</h3>' + layers_html) if layers_html else ""}
</section>'''


def gen_tech_stack(data):
    if not data:
        return ''
    items = data if isinstance(data, list) else []
    cards = ''.join(f'''<div class="stack-card">
    <div class="stack-card-role">{e(item.get("role",""))}</div>
    <div class="stack-card-name">{e(item.get("name",""))}</div>
    <p class="stack-card-why">{e(item.get("why",""))}</p>
  </div>''' for item in items)
    return f'''<section class="section" id="tech-stack">
  <p class="section-label">Tech Stack</p>
  <h2 class="section-title">What's it built with?</h2>
  <div class="stack-grid">{cards}</div>
</section>'''


def gen_entry_points(data):
    if not data:
        return ''
    items = data if isinstance(data, list) else []
    cards = ''
    for ep in items:
        cards += f'''<div class="module-card">
    <div class="module-card-header">
      <div>
        <div class="module-name">{e(ep.get("file",""))}</div>
        <div class="module-path">Trigger: {e(ep.get("trigger",""))}</div>
      </div>
    </div>
    <p style="font-size:0.875rem;color:var(--text-secondary)">{e(ep.get("narrative",""))}</p>
  </div>'''
    return f'''<section class="section" id="entry-points">
  <p class="section-label">Entry Points</p>
  <h2 class="section-title">Where does it start?</h2>
  <div class="modules-grid" style="margin-top:1rem">{cards}</div>
</section>'''


def gen_modules(data):
    if not data:
        return ''
    modules = data if isinstance(data, list) else []
    cards = ''
    for mod in modules:
        badge = f'<span class="module-role-badge">{e(mod.get("role",""))}</span>' if mod.get('role') else ''
        large_notice = ''
        if mod.get('mega_file'):
            large_notice = '<div class="large-file-notice">Generated or monolithic file — not analyzed in detail.</div>'
        elif mod.get('large_file'):
            large_notice = '<div class="large-file-notice">Large module — explanation covers public interface only.</div>'

        depends_on = ''.join(f'<span class="relation-chip">{e(d)}</span>' for d in (mod.get("depends_on") or [])[:6])
        depended_by = ''.join(f'<span class="relation-chip">{e(d)}</span>' for d in (mod.get("depended_by") or [])[:6])
        relations_html = ''
        if depends_on or depended_by:
            relations_html = f'''<div class="module-relations">
      {f'<span class="relation-label">uses →</span>{depends_on}' if depends_on else ""}
      {f'<span class="relation-label" style="margin-left:0.5rem">used by ←</span>{depended_by}' if depended_by else ""}
    </div>'''

        gotcha_html = f'<div class="module-gotcha">{e(mod.get("gotchas",""))}</div>' if mod.get('gotchas') else ''

        slug = mod.get('path', '').replace('/', '-').replace('.', '-').lower()
        has_detail = bool(mod.get('detailed_explanation'))
        toggle = '<button class="toggle-btn">Show Details</button>' if has_detail else ''
        detail_block = f'<div class="detail-view"><p style="font-size:0.875rem;color:var(--text-secondary)">{e(mod.get("detailed_explanation",""))}</p></div>' if has_detail else ''

        cards += f'''<div class="module-card" id="module-{e(slug)}" data-toggleable="true">
    <div class="module-card-header">
      <div>
        <div class="module-name">{e(mod.get("name") or mod.get("path",""))}</div>
        <div class="module-path">{e(mod.get("path",""))}</div>
      </div>
      {badge}
    </div>
    {toggle}
    <div class="simple-view">
      <p style="font-size:0.875rem;color:var(--text-secondary)">{e(mod.get("simple_explanation",""))}</p>
    </div>
    {detail_block}
    {large_notice}
    {gotcha_html}
    {relations_html}
  </div>'''

    return f'''<section class="section" id="modules">
  <p class="section-label">Modules</p>
  <h2 class="section-title">Key files explained</h2>
  <div class="modules-grid" style="margin-top:1rem">{cards}</div>
</section>'''


def gen_workflows(data):
    if not data:
        return ''
    workflows = (data.get('workflows') or []) if isinstance(data, dict) else []
    wf_html = ''
    for wf in workflows:
        # Horizontal call-chain strip
        flow_strip = ''
        summary = wf.get('steps_summary') or []
        if summary:
            nodes = ''.join(
                f'<span class="flow-node">{e(s)}</span>'
                + ('<span class="flow-arrow">&#8594;</span>' if i < len(summary) - 1 else '')
                for i, s in enumerate(summary)
            )
            flow_strip = f'<div class="flow-strip">{nodes}</div>'

        mermaid_html = ''
        if wf.get('mermaid'):
            mermaid_html = f'<div class="mermaid-wrap mermaid-hero"><div class="mermaid" data-diagram="{e(wf["mermaid"])}"></div></div>'

        wf_html += f'''<div class="workflow">
    <h3>{e(wf.get("name",""))}</h3>
    <div class="workflow-trigger">{e(wf.get("trigger",""))}</div>
    {flow_strip}
    {mermaid_html}
  </div>'''

    return f'''<section class="section" id="workflows">
  <p class="section-label">Request Flows</p>
  <h2 class="section-title">How does a request travel?</h2>
  {wf_html}
</section>'''


def gen_directory_guide(data):
    if not data:
        return ''
    items = data if isinstance(data, list) else []
    rows = ''.join(f'''<div class="dir-item">
    <div class="dir-path">{e(d.get("path",""))}</div>
    <div class="dir-purpose">{e(d.get("purpose",""))}</div>
    {f'<div class="dir-when">{e(d.get("when_to_look_here",""))}</div>' if d.get("when_to_look_here") else ""}
  </div>''' for d in items)
    return f'''<section class="section" id="directory-guide">
  <p class="section-label">Directory Guide</p>
  <h2 class="section-title">Where is everything?</h2>
  <div class="dir-list">{rows}</div>
</section>'''


def gen_glossary(data):
    if not data:
        return ''
    glossary = (data.get('glossary') or []) if isinstance(data, dict) else []
    terms_html = ''.join(f'''<div class="glossary-item">
    <div class="glossary-term">{e(item.get("term",""))}</div>
    <div class="glossary-def">{e(item.get("definition",""))}</div>
  </div>''' for item in glossary)
    return f'''<section class="section" id="glossary">
  <p class="section-label">Glossary</p>
  <h2 class="section-title">Terminology</h2>
  <div class="glossary-grid">{terms_html}</div>
</section>'''


def gen_getting_started(data):
    if not data:
        return ''
    gs = (data.get('getting_started') or {}) if isinstance(data, dict) else {}
    steps = []
    if gs.get('clone'):
        steps.append(('Clone', f'<pre><code>{e(gs["clone"])}</code></pre>'))
    if gs.get('install'):
        steps.append(('Install', f'<pre><code>{e(gs["install"])}</code></pre>'))
    if gs.get('env_vars'):
        rows = ''.join(f'<tr><td>{e(v.get("name",""))}</td><td>{e(v.get("description",""))}</td></tr>'
                       for v in gs['env_vars'])
        steps.append(('Configure env', f'<table class="env-vars-table"><thead><tr><th>Variable</th><th>Description</th></tr></thead><tbody>{rows}</tbody></table>'))
    if gs.get('run'):
        steps.append(('Run', f'<pre><code>{e(gs["run"])}</code></pre>'))
    if gs.get('first_tasks'):
        tasks = ''.join(f'<li>{e(t)}</li>' for t in gs['first_tasks'])
        steps.append(('First steps', f'<ul class="first-tasks">{tasks}</ul>'))

    steps_html = ''.join(f'''<div class="setup-step">
    <div class="setup-num">{i+1}</div>
    <div style="flex:1"><strong>{e(label)}</strong>{content}</div>
  </div>''' for i, (label, content) in enumerate(steps))

    # Learning path (day 1 / week 1)
    lp = gs.get('learning_path') or {}
    learning_path_html = ''
    if lp:
        day1 = lp.get('day_1') or []
        week1 = lp.get('week_1') or []
        day1_items = ''.join(f'<li>{e(item)}</li>' for item in day1)
        week1_items = ''.join(f'<li>{e(item)}</li>' for item in week1)
        learning_path_html = f'''<div class="learning-path">
    <h3 style="margin-top:1.5rem;margin-bottom:0.75rem">Learning Path</h3>
    <div class="learning-path-grid">
      {f'<div class="learning-phase"><div class="learning-phase-label">Day 1 — Orientation</div><ul class="learning-list">{day1_items}</ul></div>' if day1_items else ""}
      {f'<div class="learning-phase"><div class="learning-phase-label">Week 1 — First Contributions</div><ul class="learning-list">{week1_items}</ul></div>' if week1_items else ""}
    </div>
  </div>'''

    return f'''<section class="section" id="getting-started">
  <p class="section-label">Getting Started</p>
  <h2 class="section-title">How do I run it?</h2>
  <div class="setup-steps">{steps_html}</div>
  {learning_path_html}
</section>'''


def gen_mindmap(analysis):
    """Build a D3.js radial mind map showing the REAL directory structure.

    The mind map radiates from the project root outward:
      root → top-level dirs → subdirs → files
    Colored by file extension. Collapses at depth > 1 by default.
    Zero LLM — pure Python tree construction from known file paths.
    """
    if not analysis:
        return ''
    meta = analysis.get('meta') or {}
    project_name = meta.get('name', 'Project')
    entry_points = analysis.get('entry_points') or []
    critical_modules = analysis.get('critical_modules') or []
    top_dirs = analysis.get('top_dirs') or []

    def norm(p):
        return p.replace('\\', '/').strip('/')

    # ── Collect every known file path ────────────────────────────────────────
    all_paths = []
    seen = set()
    for ep in entry_points:
        p = norm(ep.get('file', ''))
        if p and p not in seen:
            all_paths.append(p); seen.add(p)
    for m in critical_modules:
        p = norm(m.get('path', ''))
        if p and p not in seen:
            all_paths.append(p); seen.add(p)

    # ── Build real directory tree from path strings ──────────────────────────
    # tree_node = {'name': str, 'type': 'root'|'dir'|'file', 'ext': str, '_ch': {}}
    root_node = {'name': project_name, 'type': 'root', '_ch': {}}

    # Seed directories from top_dirs so even dirs with no critical files appear
    for d in top_dirs[:25]:
        parts = [p for p in norm(d).split('/') if p]
        node = root_node
        for part in parts[:3]:          # max 3 levels from top_dirs
            if part not in node['_ch']:
                node['_ch'][part] = {'name': part, 'type': 'dir', '_ch': {}}
            node = node['_ch'][part]

    # Insert actual files (max depth 5 to keep tree manageable)
    for path in all_paths:
        parts = [p for p in path.split('/') if p]
        if not parts:
            continue
        parts = parts[:5]
        node = root_node
        for i, part in enumerate(parts):
            if i == len(parts) - 1:     # leaf = file
                ext = part.rsplit('.', 1)[-1].lower() if '.' in part else ''
                node['_ch'][part] = {'name': part, 'type': 'file', 'ext': ext, '_ch': {}}
            else:                        # intermediate = directory
                if part not in node['_ch']:
                    node['_ch'][part] = {'name': part, 'type': 'dir', '_ch': {}}
                node = node['_ch'][part]

    # ── Convert to D3-compatible hierarchy dict ───────────────────────────────
    def to_d3(node, depth=0, max_depth=5):
        result = {'name': node['name'], 'type': node['type']}
        if node.get('ext'):
            result['ext'] = node['ext']
        kids = list(node['_ch'].values())
        # Sort: dirs first, then files alphabetically
        kids.sort(key=lambda k: (0 if k['type'] == 'dir' else 1, k['name'].lower()))
        if kids and depth < max_depth:
            result['children'] = [to_d3(k, depth + 1, max_depth) for k in kids]
        elif kids:
            result['_count'] = len(kids)
        return result

    tree = to_d3(root_node)
    if not tree.get('children'):
        return ''

    tree_json = json.dumps(tree)
    source = meta.get('source_files', 0)
    total = meta.get('total_files', 0)
    stats = (f'{source:,} source files' if source else
             f'{total:,} files' if total else '')
    stats_suffix = ' · ' if stats else ''

    top_names = [c['name'] for c in (tree.get('children') or [])]
    fallback_items = ''.join(f'<li>{e(n)}/</li>' for n in top_names[:12])

    return f'''<section class="section" id="codebase-map">
  <p class="section-label">Codebase Map</p>
  <h2 class="section-title">Directory structure</h2>
  <p style="color:var(--text-secondary);font-size:0.875rem;margin-bottom:1.25rem">{e(stats + stats_suffix)}click any folder to expand or collapse</p>
  <div style="border-radius:14px;border:1px solid var(--border-subtle);overflow:hidden;background:var(--bg-surface)">
    <!-- Toolbar -->
    <div style="display:flex;align-items:center;gap:0.75rem;padding:0.875rem 1.125rem;border-bottom:1px solid var(--border-subtle)">
      <svg width="18" height="18" viewBox="0 0 20 20" fill="none" style="flex-shrink:0;color:var(--accent)">
        <path d="M2 5a2 2 0 012-2h3.586a1 1 0 01.707.293L9.707 4.707A1 1 0 0010.414 5H16a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V5z" fill="currentColor" opacity="0.9"/>
      </svg>
      <span style="font-size:0.9rem;font-weight:600;color:var(--text-primary)">{e(project_name)}</span>
      <span style="font-size:0.78rem;color:var(--text-tertiary,var(--text-secondary))">{e(stats)}</span>
      <div style="margin-left:auto;display:flex;gap:0.5rem">
        <button onclick="mmExpandAll()" style="background:transparent;border:1px solid var(--border-subtle);color:var(--text-secondary);border-radius:7px;padding:0.3rem 0.75rem;font-size:0.75rem;cursor:pointer;transition:all 0.15s;font-family:inherit" onmouseover="this.style.background='var(--bg-elevated,var(--bg-page))'" onmouseout="this.style.background='transparent'">Expand all</button>
        <button onclick="mmCollapseAll()" style="background:transparent;border:1px solid var(--border-subtle);color:var(--text-secondary);border-radius:7px;padding:0.3rem 0.75rem;font-size:0.75rem;cursor:pointer;transition:all 0.15s;font-family:inherit" onmouseover="this.style.background='var(--bg-elevated,var(--bg-page))'" onmouseout="this.style.background='transparent'">Collapse</button>
      </div>
    </div>
    <!-- Tree -->
    <div id="mm-tree" style="max-height:520px;overflow-y:auto;padding:0.5rem 0.5rem"></div>
    <div id="mm-fallback" style="display:none;padding:1.5rem">
      <ul style="font-size:0.875rem;color:var(--text-secondary);padding-left:1.25rem">{fallback_items}</ul>
    </div>
  </div>
  <style>
.mm-folder-row{{display:flex;align-items:center;gap:0;padding:0.28rem 0.625rem;border-radius:8px;cursor:pointer;user-select:none;transition:background 0.13s;}}
.mm-folder-row:hover{{background:var(--bg-page)}}
.mm-file-row{{display:flex;align-items:center;gap:0;padding:0.22rem 0.625rem;border-radius:6px;cursor:default;}}
.mm-file-row:hover{{background:var(--bg-page)}}
.mm-chevron{{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;margin-right:4px;flex-shrink:0;transition:transform 0.18s cubic-bezier(0.4,0,0.2,1);color:var(--text-secondary);opacity:0.6}}
.mm-chevron svg{{width:10px;height:10px}}
.mm-children{{overflow:hidden;transition:max-height 0.22s cubic-bezier(0.4,0,0.2,1),opacity 0.18s;}}
.mm-ext-badge{{font-size:0.65rem;font-weight:500;padding:1px 6px;border-radius:4px;margin-left:auto;flex-shrink:0;letter-spacing:0.02em;opacity:0.8}}
  </style>
  <script>
(function(){{
var TREE={tree_json};
var EC={{
  ts:'#3b82f6',tsx:'#3b82f6',
  js:'#f59e0b',jsx:'#f59e0b',mjs:'#f59e0b',cjs:'#f59e0b',
  py:'#10b981',
  cs:'#8b5cf6',
  java:'#f97316',kt:'#a855f7',
  go:'#06b6d4',
  rs:'#ef4444',
  rb:'#e11d48',php:'#6366f1',
  html:'#f97316',css:'#38bdf8',scss:'#ec4899',sass:'#ec4899',
  json:'#64748b',yaml:'#84cc16',yml:'#84cc16',toml:'#84cc16',
  md:'#6b7280',mdx:'#6b7280',
  vue:'#22c55e',svelte:'#f97316',
  dart:'#06b6d4',swift:'#f97316',
  sql:'#6366f1',
  sh:'#10b981',bash:'#10b981',lock:'#9ca3af',
  gitignore:'#9ca3af',env:'#f59e0b'
}};
function ec(ext){{return EC[ext||'']||'#9ca3af';}}

// Folder SVG icon
var FOLDER_SVG='<svg width="16" height="16" viewBox="0 0 20 20" fill="none" style="flex-shrink:0;margin-right:6px"><path d="M2 6a2 2 0 012-2h3.172a2 2 0 011.414.586l.828.828A2 2 0 0010.828 6H16a2 2 0 012 2v7a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" fill="%s" opacity="0.85"/></svg>';
var FILE_SVG='<svg width="14" height="14" viewBox="0 0 20 20" fill="none" style="flex-shrink:0;margin-right:7px"><path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" fill="%s" opacity="0.75"/></svg>';

function folderColor(depth){{
  var palette=['#f59e0b','#3b82f6','#10b981','#8b5cf6','#f97316'];
  return palette[depth%palette.length];
}}

function buildHTML(node,depth){{
  if(node.type==='root'){{
    return(node.children||[]).map(function(c){{return buildHTML(c,0);}}).join('');
  }}
  var pl=depth*20+8;
  if(node.type==='dir'){{
    var kids=(node.children||[]).map(function(c){{return buildHTML(c,depth+1);}}).join('');
    var fc=folderColor(depth);
    var ficon=FOLDER_SVG.replace('%s',encodeURIComponent(fc));
    var cnt=(node.children||[]).length||(node._count||0);
    var cntBadge=cnt?'<span style="font-size:0.68rem;color:var(--text-secondary);margin-left:6px;opacity:0.55">'+cnt+'</span>':'';
    return '<div class="mm-dir-wrap">'
      +'<div class="mm-folder-row" style="padding-left:'+pl+'px" onclick="mmToggle(this.parentElement)">'
      +'<span class="mm-chevron"><svg viewBox="0 0 10 10" fill="currentColor"><path d="M3 2l4 3-4 3V2z"/></svg></span>'
      +ficon
      +'<span style="font-size:0.875rem;font-weight:500;color:var(--text-primary)">'+node.name+'</span>'
      +cntBadge
      +'</div>'
      +'<div class="mm-children">'+kids+'</div>'
      +'</div>';
  }}
  // file
  var color=ec(node.ext);
  var ficon=FILE_SVG.replace('%s',encodeURIComponent(color));
  var badge=node.ext?'<span class="mm-ext-badge" style="color:'+color+';background:'+color+'1a">'+node.ext+'</span>':'';
  return '<div class="mm-file-row" style="padding-left:'+(pl+20)+'px">'
    +ficon
    +'<span style="font-size:0.84rem;color:var(--text-secondary)">'+node.name+'</span>'
    +badge
    +'</div>';
}}

function mmToggle(wrap){{
  var ch=wrap.querySelector('.mm-children');
  var chevron=wrap.querySelector('.mm-chevron');
  if(!ch)return;
  var open=ch.dataset.open==='1';
  if(open){{
    ch.style.maxHeight='0px';ch.style.opacity='0';
    ch.dataset.open='0';
    if(chevron)chevron.style.transform='';
  }}else{{
    ch.style.maxHeight=ch.scrollHeight+'px';ch.style.opacity='1';
    ch.dataset.open='1';
    if(chevron)chevron.style.transform='rotate(90deg)';
    // After transition expand to auto so content can grow further
    ch.addEventListener('transitionend',function h(){{
      if(ch.dataset.open==='1')ch.style.maxHeight='none';
      ch.removeEventListener('transitionend',h);
    }});
  }}
}}

window.mmExpandAll=function(){{
  document.querySelectorAll('#mm-tree .mm-children').forEach(function(el){{
    el.style.maxHeight='none';el.style.opacity='1';el.dataset.open='1';
  }});
  document.querySelectorAll('#mm-tree .mm-chevron').forEach(function(el){{
    el.style.transform='rotate(90deg)';
  }});
}};
window.mmCollapseAll=function(){{
  document.querySelectorAll('#mm-tree .mm-children').forEach(function(el){{
    // Keep depth-0 open
    var row=el.previousElementSibling;
    if(row){{
      var pad=parseInt(row.style.paddingLeft||0);
      if(pad>8){{el.style.maxHeight='0px';el.style.opacity='0';el.dataset.open='0';}}
    }}
  }});
  document.querySelectorAll('#mm-tree .mm-chevron').forEach(function(el){{
    var row=el.closest('.mm-folder-row');
    if(row&&parseInt(row.style.paddingLeft||0)>8)el.style.transform='';
  }});
}};

var container=document.getElementById('mm-tree');
if(container){{
  container.innerHTML=buildHTML(TREE,0);
  // Open depth-0 directories by default
  container.querySelectorAll(':scope>.mm-dir-wrap').forEach(function(wrap){{
    var ch=wrap.querySelector('.mm-children');
    var chevron=wrap.querySelector('.mm-chevron');
    if(ch){{ch.style.maxHeight='none';ch.style.opacity='1';ch.dataset.open='1';}}
    if(chevron)chevron.style.transform='rotate(90deg)';
  }});
}}
}})();
  </script>
</section>'''


def gen_code_map(graph_data, modules_content):
    """Build interactive D3 forceSimulation code dependency map — Obsidian-style."""
    if not graph_data:
        return ''

    nodes            = graph_data.get('nodes', [])
    edges            = graph_data.get('edges', [])
    meta             = graph_data.get('_meta', {})
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

    # Obsidian-style node colors — warm purples as base, hue shifts per role
    ROLE_COLORS = {
        'service':    '#7c6fcd',   # Obsidian signature purple
        'route':      '#6fa3d4',   # cool blue (entry paths)
        'model':      '#6fcd99',   # soft green (data)
        'utility':    '#9e8ecf',   # muted lavender
        'config':     '#c9b86c',   # warm gold (settings)
        'middleware': '#a06fcd',   # deeper purple (cross-cutting)
        'test':       '#6f8fcd',   # steel blue (test files)
        'migration':  '#cd6fa8',   # rose-purple (data changes)
        'build':      '#cd9a6f',   # warm amber (tooling)
        'folder':     '#b0a0e8',   # soft lavender (folder nodes)
        'default':    '#8c8cb0',   # neutral purple-gray
    }
    # Also keep hues for chip borders (approx degrees)
    ROLE_HUES = {
        'service': 262, 'route': 210, 'model': 155, 'utility': 265,
        'config': 50,   'middleware': 280, 'test': 220, 'migration': 320,
        'build': 30,    'folder': 255,
    }

    # Gather distinct roles for filter chips
    roles = sorted({n.get('role', 'utility') for n in enriched_nodes})

    # Build filter chips HTML
    chip_items = ''.join(
        f'<button class="cm-chip" data-role="{e(r)}" style="--chip-hue:{ROLE_HUES.get(r, 240)}" aria-pressed="true">{e(r)}</button>'
        for r in roles
    )

    # Build stats line
    node_count = meta.get('nodes_in_graph', len(nodes))
    edge_count = meta.get('edges_in_graph', len(edges))
    stats_subtitle = f'{node_count} nodes \u00b7 {edge_count} edges \u00b7 click to explore \u00b7 drag to rearrange'
    stats_html = (
        f'<span class="cm-stat">{node_count} nodes</span>'
        f'<span class="cm-stat">{edge_count} edges</span>'
        f'<span class="cm-stat">{meta.get("total_files_scanned", "?")} files scanned</span>'
    )
    if meta.get('files_collapsed_into_folders', 0):
        stats_html += f'<span class="cm-stat">{meta["files_collapsed_into_folders"]} collapsed into folders</span>'

    # Serialize graph data for inline JS (flat arrays, no Cytoscape wrapper)
    d3_nodes = [
        {
            'id':                 n['id'],
            'label':              n.get('label', n['id']),
            'fullPath':           n.get('fullPath', n['id']),
            'role':               n.get('role', 'utility'),
            'loc':                n.get('loc', 0),
            'connectivity':       n.get('connectivity', 0),
            'tier':               n.get('tier', 'isolated'),
            'type':               n.get('type', 'file'),
            'childCount':         n.get('childCount', 0),
            'simple_explanation': n.get('simple_explanation', ''),
        }
        for n in enriched_nodes
    ]
    d3_edges = [
        {
            'id':     f'e-{i}',
            'source': eg['source'],
            'target': eg['target'],
            'weight': eg.get('weight', 1),
        }
        for i, eg in enumerate(edges)
    ]

    graph_json     = json.dumps({'nodes': d3_nodes, 'edges': d3_edges}, separators=(',', ':'))
    expansion_json = json.dumps(folder_expansions, separators=(',', ':'))
    role_colors_json = json.dumps(ROLE_COLORS)
    roles_json     = json.dumps(roles)

    inline_js = f"""
function cmShowFallback(){{
  var ns=GRAPH_DATA.nodes.slice().sort(function(a,b){{return b.connectivity-a.connectivity;}});
  var rows=ns.slice(0,30).map(function(n){{
    return '<tr><td style="padding:4px 8px;border-bottom:1px solid var(--border-subtle)">'+n.fullPath+'</td>'
      +'<td style="padding:4px 8px;border-bottom:1px solid var(--border-subtle)">'+n.role+'</td>'
      +'<td style="padding:4px 8px;border-bottom:1px solid var(--border-subtle);text-align:right">'+n.connectivity+'</td></tr>';
  }}).join('');
  document.getElementById('code-map-fallback').innerHTML=
    '<table style="width:100%;border-collapse:collapse;font-size:0.8rem">'
    +'<thead><tr>'
    +'<th style="padding:6px 8px;border-bottom:2px solid var(--border-subtle);text-align:left">File</th>'
    +'<th style="padding:6px 8px;border-bottom:2px solid var(--border-subtle);text-align:left">Role</th>'
    +'<th style="padding:6px 8px;border-bottom:2px solid var(--border-subtle);text-align:right">Connections</th>'
    +'</tr></thead><tbody>'+rows+'</tbody></table>';
  document.getElementById('cm-wrap').style.display='none';
  document.getElementById('code-map-fallback').style.display='block';
}}
var _cmInitDone=false;
function cmInit(){{
  if(_cmInitDone)return;
  if(window.D3_FAILED){{cmShowFallback();return;}}
  if(typeof d3==='undefined'){{
    // D3 <script> is at end of body — not yet in DOM when this runs.
    // window 'load' fires after all body scripts have executed, so d3 is guaranteed available.
    window.addEventListener('load',cmInit);
    return;
  }}
  _cmInitDone=true;
(function(){{

  var ROLE_COLORS={role_colors_json};
  function roleColor(role){{
    return ROLE_COLORS[role]||ROLE_COLORS['default'];
  }}

  // Clamp helper
  function clamp(v,lo,hi){{return Math.max(lo,Math.min(hi,v));}}

  // Node radius: proportional to connectivity, folder nodes larger
  function nodeR(d){{
    if(d.type==='folder'){{
      return clamp(14+d.connectivity*1.2,14,28);
    }}
    return clamp(4+d.connectivity*1.5,5,18);
  }}

  var wrap=document.getElementById('cm-wrap');
  var svg=d3.select('#cm-svg');
  var W=wrap.clientWidth||900;
  var H=620;

  // SVG defs: soft halo glow (Obsidian-style — subtle, not harsh)
  var defs=svg.select('defs');
  // Resting glow — soft halo at low opacity
  defs.append('filter')
    .attr('id','node-glow')
    .attr('x','-60%').attr('y','-60%')
    .attr('width','220%').attr('height','220%')
    .html('<feGaussianBlur in="SourceGraphic" stdDeviation="2.8" result="blur"/>'
      +'<feColorMatrix in="blur" type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 0.42 0" result="softBlur"/>'
      +'<feMerge>'
      +'<feMergeNode in="softBlur"/>'
      +'<feMergeNode in="SourceGraphic"/>'
      +'</feMerge>');
  // Hover glow — slightly wider halo, still controlled
  defs.append('filter')
    .attr('id','node-glow-hover')
    .attr('x','-80%').attr('y','-80%')
    .attr('width','260%').attr('height','260%')
    .html('<feGaussianBlur in="SourceGraphic" stdDeviation="5" result="blur"/>'
      +'<feColorMatrix in="blur" type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 0.65 0" result="softBlur"/>'
      +'<feMerge>'
      +'<feMergeNode in="softBlur"/>'
      +'<feMergeNode in="SourceGraphic"/>'
      +'</feMerge>');

  // Zoom container
  var zoomG=svg.append('g').attr('class','cm-zoom-root');
  var edgeG=zoomG.append('g').attr('class','cm-edges');
  var nodeG=zoomG.append('g').attr('class','cm-nodes');
  var labelG=zoomG.append('g').attr('class','cm-labels');

  // Zoom behaviour
  var zoom=d3.zoom()
    .scaleExtent([0.1,8])
    .on('zoom',function(event){{
      zoomG.attr('transform',event.transform);
    }});
  svg.call(zoom);

  // Deep-copy nodes/edges (D3 mutates them)
  var nodes=GRAPH_DATA.nodes.map(function(n){{return Object.assign({{}},n);}});
  var edges=GRAPH_DATA.edges.map(function(eg){{return Object.assign({{}},eg);}});

  // Build adjacency for hover highlight
  var adjSet={{}};
  edges.forEach(function(eg){{
    var s=eg.source.id||eg.source;
    var t=eg.target.id||eg.target;
    adjSet[s+':'+t]=true;
    adjSet[t+':'+s]=true;
  }});

  // D3 force simulation — Obsidian-style organic clustering
  var sim=d3.forceSimulation(nodes)
    .force('link',d3.forceLink(edges).id(function(d){{return d.id;}}).distance(75).strength(0.2))
    .force('charge',d3.forceManyBody().strength(-130).distanceMin(8).distanceMax(380))
    .force('center',d3.forceCenter(W/2,H/2).strength(0.04))
    .force('collide',d3.forceCollide().radius(function(d){{return nodeR(d)+6;}}).strength(0.7))
    .alphaDecay(0.012)
    .velocityDecay(0.25);

  // Pre-settle: run 120 ticks for rough placement, animate the rest for organic feel
  sim.stop();
  for(var t=0;t<120;t++)sim.tick();

  // Draw edges — uniform muted purple-blue like Obsidian
  var edgeSel=edgeG.selectAll('line')
    .data(edges).enter().append('line')
    .attr('class','cm-edge')
    .attr('stroke-width',0.7)
    .attr('stroke-opacity',0.38)
    .attr('stroke','#4a4080');

  // Draw nodes
  var nodeSel=nodeG.selectAll('circle')
    .data(nodes).enter().append('circle')
    .attr('class','cm-node')
    .attr('r',function(d){{return nodeR(d);}})
    .attr('fill',function(d){{return roleColor(d.role);}})
    .attr('fill-opacity',function(d){{return d.type==='folder'?0.95:0.85;}})
    .attr('stroke',function(d){{return roleColor(d.role);}})
    .attr('stroke-width',1.5)
    .attr('filter','url(#node-glow)')
    .style('cursor','pointer')
    .call(d3.drag()
      .on('start',function(event,d){{
        if(!event.active)sim.alphaTarget(0.3).restart();
        d.fx=d.x;d.fy=d.y;
      }})
      .on('drag',function(event,d){{d.fx=event.x;d.fy=event.y;}})
      .on('end',function(event,d){{
        if(!event.active)sim.alphaTarget(0);
        d.fx=null;d.fy=null;
      }})
    );

  // Draw labels — Obsidian light gray, whisper-soft
  var alwaysLabelThreshold=3;
  var labelSel=labelG.selectAll('text')
    .data(nodes).enter().append('text')
    .attr('class','cm-label')
    .attr('dy',function(d){{return nodeR(d)+11;}})
    .attr('text-anchor','middle')
    .attr('font-size',9.5)
    .attr('fill','#afaaca')
    .attr('pointer-events','none')
    .attr('opacity',function(d){{return d.connectivity>=alwaysLabelThreshold?0.85:0;}})
    .text(function(d){{
      var lbl=d.label||d.id;
      return lbl.length>20?lbl.slice(0,19)+'\u2026':lbl;
    }});

  // Position update on tick
  sim.on('tick',function(){{
    edgeSel
      .attr('x1',function(d){{return d.source.x;}})
      .attr('y1',function(d){{return d.source.y;}})
      .attr('x2',function(d){{return d.target.x;}})
      .attr('y2',function(d){{return d.target.y;}});
    nodeSel
      .attr('cx',function(d){{return d.x;}})
      .attr('cy',function(d){{return d.y;}});
    labelSel
      .attr('x',function(d){{return d.x;}})
      .attr('y',function(d){{return d.y;}});
  }});

  // Let remaining ticks animate — slow organic settle
  sim.alpha(0.6).restart();

  // Tooltip
  var tooltip=document.getElementById('code-map-tooltip');

  // Hover interactions
  nodeSel.on('mouseenter',function(event,d){{
    var isDark=document.documentElement.getAttribute('data-theme')==='dark';
    // Fade all
    nodeSel.attr('opacity',0.08);
    edgeSel.attr('stroke-opacity',0.05);
    labelSel.attr('opacity',0);
    // Highlight this node
    d3.select(this)
      .attr('opacity',1)
      .attr('stroke-width',2.5)
      .attr('filter','url(#node-glow-hover)');
    // Highlight connected edges + neighbors
    var thisId=d.id;
    edgeSel.filter(function(eg){{
      var s=eg.source.id||eg.source;
      var t=eg.target.id||eg.target;
      return s===thisId||t===thisId;
    }}).attr('stroke-opacity',0.7);
    nodeSel.filter(function(nd){{
      return nd.id!==thisId&&(adjSet[thisId+':'+nd.id]||adjSet[nd.id+':'+thisId]);
    }}).attr('opacity',1);
    // Label for hovered
    labelSel.filter(function(nd){{return nd.id===thisId;}}).attr('opacity',1);

    // Tooltip
    var expl=d.simple_explanation
      ?'<p style="margin:4px 0 0;color:var(--text-secondary);font-size:0.78rem">'+d.simple_explanation+'</p>':'';
    tooltip.innerHTML='<strong style="font-size:0.85rem">'+d.label+'</strong>'
      +'<br><span style="color:var(--text-secondary);font-size:0.78rem">'+d.fullPath+'</span>'
      +'<br><span style="font-size:0.78rem">'+d.role+' \u00b7 '+d.loc+' LOC \u00b7 '+d.connectivity+' connections</span>'
      +expl;
    tooltip.style.display='block';
  }});

  nodeSel.on('mousemove',function(event){{
    var rect=wrap.getBoundingClientRect();
    tooltip.style.left=(event.clientX-rect.left+14)+'px';
    tooltip.style.top=(event.clientY-rect.top+14)+'px';
  }});

  nodeSel.on('mouseleave',function(){{
    tooltip.style.display='none';
    nodeSel.attr('opacity',1).attr('stroke-width',1.5).attr('filter','url(#node-glow)');
    edgeSel.attr('stroke-opacity',0.38);
    labelSel.attr('opacity',function(d){{return d.connectivity>=alwaysLabelThreshold?0.85:0;}});
  }});

  // Click: scroll to module OR expand folder
  nodeSel.on('click',function(event,d){{
    event.stopPropagation();
    if(d.type==='folder'){{
      var fid='folder:'+d.id.replace(/^folder:/,'');
      var exp=FOLDER_EXPANSIONS[fid]||FOLDER_EXPANSIONS[d.id];
      if(!exp)return;
      var existingIds={{}};
      nodes.forEach(function(n){{existingIds[n.id]=true;}});
      var newNodes=[];
      var newEdges=[];
      (exp.nodes||[]).forEach(function(nd){{
        if(!existingIds[nd.id]){{
          var nn=Object.assign({{}},nd,{{x:d.x+(Math.random()-0.5)*60,y:d.y+(Math.random()-0.5)*60}});
          newNodes.push(nn);
        }}
      }});
      (exp.edges||[]).forEach(function(eg,i){{
        newEdges.push({{id:'exp-'+i+'-'+eg.source+'-'+eg.target,source:eg.source,target:eg.target,weight:eg.weight||1}});
      }});
      if(newNodes.length){{
        newNodes.forEach(function(n){{nodes.push(n);}});
        newEdges.forEach(function(eg){{edges.push(eg);}});
        rebuildGraph();
      }}
    }} else {{
      var slug=d.fullPath.replace(/[/\\.]/g,'-').toLowerCase();
      var el=document.getElementById('module-'+slug);
      if(el)el.scrollIntoView({{behavior:'smooth'}});
    }}
  }});

  // Rebuild graph (after folder expansion)
  function rebuildGraph(){{
    edgeSel.remove();
    nodeSel.remove();
    labelSel.remove();
    // re-run (recursive call simplified — just re-init)
    location.reload(); // simplest stable approach for expansion
  }}

  // Code map canvas stays dark regardless of site theme (Obsidian is always dark)
  // No theme toggle listener needed — background is fixed.

  // Search (debounced 200ms)
  var searchTimer;
  document.getElementById('cm-search').addEventListener('input',function(){{
    clearTimeout(searchTimer);
    var q=this.value.trim().toLowerCase();
    searchTimer=setTimeout(function(){{
      if(!q){{
        nodeSel.attr('opacity',1).attr('filter','url(#node-glow)');
        edgeSel.attr('stroke-opacity',0.38);
        labelSel.attr('opacity',function(d){{return d.connectivity>=alwaysLabelThreshold?0.85:0;}});
        return;
      }}
      nodeSel.attr('opacity',function(d){{
        var match=(d.label||'').toLowerCase().includes(q)||(d.fullPath||'').toLowerCase().includes(q);
        return match?1:0.06;
      }}).attr('filter',function(d){{
        var match=(d.label||'').toLowerCase().includes(q)||(d.fullPath||'').toLowerCase().includes(q);
        return match?'url(#node-glow-hover)':'url(#node-glow)';
      }});
      edgeSel.attr('stroke-opacity',0.06);
      labelSel.attr('opacity',function(d){{
        var match=(d.label||'').toLowerCase().includes(q)||(d.fullPath||'').toLowerCase().includes(q);
        return match?1:0;
      }});
    }},200);
  }});

  // Role filter chips
  var activeRoles=new Set({roles_json});
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
      nodeSel.attr('opacity',function(d){{return activeRoles.has(d.role)?1:0.05;}});
      edgeSel.attr('stroke-opacity',function(d){{
        var s=d.source.role||'utility';
        var t=d.target.role||'utility';
        return (activeRoles.has(s)&&activeRoles.has(t))?0.38:0.04;
      }});
    }});
  }});

  // Fit view button
  document.getElementById('cm-fit').addEventListener('click',function(){{
    var bounds=zoomG.node().getBBox();
    if(!bounds.width||!bounds.height)return;
    var pad=40;
    var scale=Math.min((W-pad*2)/bounds.width,(H-pad*2)/bounds.height,2);
    var tx=W/2-scale*(bounds.x+bounds.width/2);
    var ty=H/2-scale*(bounds.y+bounds.height/2);
    svg.transition().duration(400).call(zoom.transform,d3.zoomIdentity.translate(tx,ty).scale(scale));
  }});

  // Reheat simulation
  document.getElementById('cm-reheat').addEventListener('click',function(){{
    sim.alpha(0.5).restart();
  }});

  // Fullscreen
  document.getElementById('cm-fullscreen').addEventListener('click',function(){{
    wrap.classList.toggle('cm-fullscreen-mode');
    var isFs=wrap.classList.contains('cm-fullscreen-mode');
    this.textContent=isFs?'Exit Fullscreen':'Fullscreen';
    if(isFs){{
      svg.attr('height','100vh');
    }}else{{
      svg.attr('height','620');
    }}
  }});
  document.addEventListener('keydown',function(ev){{
    if(ev.key==='Escape'&&wrap.classList.contains('cm-fullscreen-mode')){{
      wrap.classList.remove('cm-fullscreen-mode');
      document.getElementById('cm-fullscreen').textContent='Fullscreen';
      svg.attr('height','620');
    }}
  }});

}})();
}}
cmInit();
"""

    # Legend items HTML
    legend_items = ''.join(
        f'<span class="cm-legend-item"><span class="cm-legend-dot" style="background:{ROLE_COLORS.get(r, ROLE_COLORS["default"])}"></span>{e(r)}</span>'
        for r in roles
    )

    # Obsidian dark canvas — charcoal base with subtle nebula gradient
    canvas_bg = '#1e1e1e'
    canvas_style = (
        'background:radial-gradient(ellipse at 25% 35%,rgba(100,80,200,0.07) 0%,transparent 55%),'
        'radial-gradient(ellipse at 75% 65%,rgba(60,80,180,0.05) 0%,transparent 50%),'
        '#1e1e1e'
    )

    return f'''<section class="section" id="code-map">
  <p class="section-label">Code Map</p>
  <h2 class="section-title">Dependency graph</h2>
  <p class="section-subtitle" style="font-size:0.9rem;color:var(--text-secondary);margin-bottom:0.5rem">{e(stats_subtitle)}</p>

  <!-- Controls bar -->
  <div style="display:flex;flex-wrap:wrap;gap:0.5rem;align-items:center;margin-bottom:0.75rem">
    <input id="cm-search" type="search" placeholder="Search files..." aria-label="Search code map nodes"
      style="flex:1;min-width:140px;max-width:220px;padding:0.3rem 0.6rem;border:1px solid var(--border-subtle);border-radius:6px;font-size:0.82rem;background:var(--bg-surface);color:var(--text-primary)">
    <div style="display:flex;flex-wrap:wrap;gap:0.35rem;align-items:center">{chip_items}</div>
    <div style="margin-left:auto;display:flex;gap:0.4rem">
      <button id="cm-reheat" class="cm-ctrl-btn" title="Reheat simulation">Reheat</button>
      <button id="cm-fit" class="cm-ctrl-btn" title="Fit graph to viewport">Fit</button>
      <button id="cm-fullscreen" class="cm-ctrl-btn" title="Toggle fullscreen (Esc to exit)">Fullscreen</button>
    </div>
  </div>

  <!-- Stats -->
  <div style="display:flex;flex-wrap:wrap;gap:0.6rem;margin-bottom:0.75rem;font-size:0.78rem;color:var(--text-secondary)">{stats_html}</div>

  <!-- Canvas wrapper -->
  <div id="cm-wrap" style="position:relative;width:100%;height:620px;border-radius:12px;overflow:hidden;{canvas_style}">
    <svg id="cm-svg" width="100%" height="620" style="display:block">
      <defs></defs>
    </svg>
    <div id="code-map-tooltip" style="display:none;position:absolute;background:rgba(13,17,23,0.92);border:1px solid rgba(255,255,255,0.12);color:#e6edf3;border-radius:8px;padding:0.55rem 0.75rem;max-width:300px;pointer-events:none;z-index:100;box-shadow:0 4px 20px rgba(0,0,0,0.4);font-size:0.82rem;line-height:1.5;backdrop-filter:blur(4px)"></div>
  </div>

  <!-- Fallback for no D3 -->
  <div id="code-map-fallback" style="display:none;margin-top:1rem"></div>

  <!-- Legend -->
  <div style="display:flex;flex-wrap:wrap;gap:0.5rem;margin-top:0.75rem;font-size:0.78rem;color:var(--text-secondary);align-items:center">
    <span style="font-weight:500">Roles:</span>{legend_items}
    <span style="margin-left:0.5rem">circle size = connectivity</span>
  </div>

  <style>
    .cm-chip{{padding:0.2rem 0.55rem;border:1.5px solid oklch(58% 0.18 calc(var(--chip-hue)*1deg));border-radius:999px;font-size:0.75rem;background:transparent;color:var(--text-primary);cursor:pointer;transition:opacity 0.15s}}
    .cm-ctrl-btn{{padding:0.25rem 0.6rem;border:1px solid var(--border-subtle);border-radius:6px;font-size:0.78rem;background:var(--bg-surface);color:var(--text-primary);cursor:pointer}}
    .cm-ctrl-btn:hover{{background:var(--bg-page);border-color:var(--accent)}}
    .cm-legend-item{{display:inline-flex;align-items:center;gap:0.3rem}}
    .cm-legend-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
    .cm-stat::after{{content:" |";margin-left:0.4rem;color:var(--border-subtle)}}
    .cm-stat:last-child::after{{content:""}}
    #cm-wrap.cm-fullscreen-mode{{position:fixed;inset:0;z-index:9999;border-radius:0;height:100vh!important;width:100vw!important}}
    #cm-wrap.cm-fullscreen-mode #cm-svg{{height:100vh!important}}
  </style>

  <script>
    var GRAPH_DATA={graph_json};
    var FOLDER_EXPANSIONS={expansion_json};
    {inline_js}
  </script>
</section>'''


def gen_cookbook(data):
    if not data:
        return ''
    recipes = (data.get('recipes') or []) if isinstance(data, dict) else []
    if not recipes:
        return ''

    framework = (data.get('framework') or '') if isinstance(data, dict) else ''
    subtitle = f'Common tasks in {e(framework)}' if framework else 'Common developer tasks'

    recipe_cards = ''
    for i, recipe in enumerate(recipes):
        steps_html = ''.join(
            f'<li class="recipe-step">{e(step)}</li>'
            for step in (recipe.get('steps') or [])
        )
        files_html = ''.join(
            f'<span class="relation-chip">{e(f)}</span>'
            for f in (recipe.get('files_to_touch') or [])[:5]
        )
        code_hint = recipe.get('code_hint', '')
        code_block = f'<pre class="recipe-code"><code>{e(code_hint)}</code></pre>' if code_hint else ''

        recipe_cards += f'''<div class="recipe-card" id="recipe-{i}">
    <div class="recipe-title">{e(recipe.get("title",""))}</div>
    <ol class="recipe-steps">{steps_html}</ol>
    {code_block}
    {f'<div class="recipe-files"><span class="relation-label">touch →</span>{files_html}</div>' if files_html else ""}
  </div>'''

    return f'''<section class="section" id="cookbook">
  <p class="section-label">Developer Cookbook</p>
  <h2 class="section-title">How do I...?</h2>
  <p style="color:var(--text-secondary);margin-bottom:1.5rem">{subtitle}</p>
  <div class="cookbook-grid">{recipe_cards}</div>
</section>'''


def gen_cross_cutting(data):
    if not data:
        return ''

    def _topic_block(label, topic_data):
        if not topic_data:
            return ''
        simple = e(topic_data.get('simple_explanation') or topic_data.get('strategy') or
                   topic_data.get('library') or topic_data.get('unit_framework') or
                   topic_data.get('mechanism') or topic_data.get('pattern') or '')
        detailed = e(topic_data.get('detailed_explanation') or '')
        mermaid_html = ''
        if topic_data.get('mermaid'):
            mermaid_html = f'<div class="mermaid-wrap"><div class="mermaid" data-diagram="{e(topic_data["mermaid"])}"></div></div>'
        files_html = ''
        for fkey in ('guard_files', 'key_files'):
            files = topic_data.get(fkey) or []
            if files:
                chips = ''.join(f'<span class="relation-chip">{e(f)}</span>' for f in files[:6])
                files_html = f'<div class="module-relations"><span class="relation-label">files →</span>{chips}</div>'
                break
        return f'''<div class="module-card" style="margin-bottom:0.75rem">
    <div class="module-name">{e(label)}</div>
    <p style="font-size:0.875rem;color:var(--text-secondary);margin:0.3rem 0 0.5rem">{simple}</p>
    {f'<p style="font-size:0.82rem;color:var(--text-secondary)">{detailed}</p>' if detailed else ""}
    {mermaid_html}
    {files_html}
  </div>'''

    blocks = ''
    if data.get('auth_authz'):
        aa = data['auth_authz']
        mechanism = e(aa.get('mechanism', ''))
        blocks += _topic_block(f'Auth / AuthZ ({mechanism})' if mechanism else 'Auth / AuthZ', aa)
    if data.get('error_handling'):
        blocks += _topic_block('Error Handling', data['error_handling'])
    if data.get('logging_observability'):
        blocks += _topic_block('Logging & Observability', data['logging_observability'])
    if data.get('testing_strategy'):
        blocks += _topic_block('Testing Strategy', data['testing_strategy'])

    if not blocks:
        return ''

    return f'''<section class="section" id="cross-cutting">
  <p class="section-label">Cross-Cutting Concerns</p>
  <h2 class="section-title">How does it handle auth, errors, logging, and testing?</h2>
  <div class="modules-grid" style="margin-top:1rem">{blocks}</div>
</section>'''


# ============================================================
# CHUNK 3: Search Index + Navigation + Output + main()
# ============================================================

def build_search_index(content):
    """Tokenize all text content into searchable entries."""
    entries = []

    def add(section, text, element_id=''):
        if not text or not text.strip():
            return
        entries.append({
            'id': element_id,
            'section': section,
            'text': text[:400],
            'snippet': text[:120]
        })

    # Overview
    ov = content.get('overview', {})
    if ov:
        add('Overview', (ov.get('summary', '') + ' ' + ov.get('approach', '')).strip(), 'overview')

    # Architecture
    arch = content.get('architecture', {})
    if arch:
        add('Architecture', arch.get('analogy', ''), 'architecture')
        for layer in (arch.get('layers') or []):
            add('Architecture — ' + layer.get('name', ''), layer.get('responsibility', ''), 'architecture')

    # Tech stack
    for item in (content.get('tech_stack') or []):
        add('Tech Stack — ' + item.get('name', ''), item.get('why', ''), 'tech-stack')

    # Entry points
    for ep in (content.get('entry_points') or []):
        add('Entry Points — ' + ep.get('file', ''), ep.get('narrative', ''), 'entry-points')

    # Modules
    for mod in (content.get('modules') or []):
        slug = mod.get('path', '').replace('/', '-').replace('.', '-').lower()
        text = ' '.join(filter(None, [
            mod.get('simple_explanation', ''),
            mod.get('detailed_explanation', '')
        ]))
        add('Module — ' + (mod.get('name') or mod.get('path', '')), text, 'module-' + slug)

    # Workflows
    wf_data = content.get('workflows', {})
    for wf in ((wf_data.get('workflows') or []) if isinstance(wf_data, dict) else []):
        for step in (wf.get('steps') or []):
            add('Workflow — ' + wf.get('name', ''), step.get('narrative', ''), 'workflows')

    # Directory guide
    for d in (content.get('directory_guide') or []):
        add('Directory — ' + d.get('path', ''), d.get('purpose', ''), 'directory-guide')

    # Glossary
    gsg = content.get('glossary_getting_started', {})
    if isinstance(gsg, dict):
        for item in (gsg.get('glossary') or []):
            add('Glossary — ' + item.get('term', ''), item.get('definition', ''), 'glossary')

    # Cross-cutting concerns
    cc = content.get('cross_cutting', {})
    if isinstance(cc, dict):
        for key, label in [('auth_authz', 'Auth/AuthZ'), ('error_handling', 'Error Handling'),
                           ('logging_observability', 'Logging & Observability'),
                           ('testing_strategy', 'Testing Strategy')]:
            topic = cc.get(key) or {}
            if isinstance(topic, dict):
                text = ' '.join(filter(None, [
                    topic.get('simple_explanation', ''),
                    topic.get('detailed_explanation', ''),
                    topic.get('strategy', ''),
                    topic.get('pattern', ''),
                    topic.get('library', ''),
                ]))
                if text:
                    add('Cross-Cutting — ' + label, text, 'cross-cutting')

    # Cookbook
    cb = content.get('cookbook', {})
    if isinstance(cb, dict):
        for recipe in (cb.get('recipes') or []):
            text = ' '.join(filter(None, [recipe.get('title', ''), ' '.join(recipe.get('steps') or [])]))
            add('Cookbook — ' + recipe.get('title', ''), text, 'cookbook')

    return json.dumps(entries)


def build_navigation(content, has_mindmap=False, has_codemap=False):
    """Generate sidebar navigation HTML."""
    SECTION_MAP = [
        ('overview',       'overview',       'Overview'),
        ('architecture',   'architecture',   'Architecture'),
        ('mindmap',        'codebase-map',   'Codebase Map'),
        ('code_map',       'code-map',       'Code Map'),
        ('cross_cutting',  'cross-cutting',  'Cross-Cutting Concerns'),
        ('tech_stack',     'tech-stack',     'Tech Stack'),
        ('entry_points',   'entry-points',   'Entry Points'),
        ('modules',        'modules',        'Modules'),
        ('workflows',      'workflows',      'Workflows'),
        ('directory_guide','directory-guide','Directory Guide'),
        ('glossary_getting_started', 'glossary', 'Glossary'),
        ('glossary_getting_started', 'getting-started', 'Getting Started'),
        ('cookbook',                 'cookbook',         'Developer Cookbook'),
    ]

    nav = ''
    seen = set()
    for key, anchor, label in SECTION_MAP:
        auto_show = (
            key in ('glossary_getting_started',)
            or (key == 'mindmap' and has_mindmap)
            or (key == 'code_map' and has_codemap)
        )
        if key in content or auto_show:
            if anchor in seen:
                continue
            seen.add(anchor)
            nav += f'<a href="#{anchor}" class="nav-link" data-section="{anchor}">{html.escape(label)}</a>\n'

    # Module sub-links
    modules = content.get('modules') or []
    if modules:
        module_links = ''
        for mod in modules[:12]:
            name = mod.get('name') or mod.get('path', '')
            slug = mod.get('path', '').replace('/', '-').replace('.', '-').lower()
            module_links += f'<a href="#module-{html.escape(slug)}" class="nav-link nav-link-sub">{html.escape(name[:30])}</a>\n'
        if module_links:
            nav = nav.replace(
                'class="nav-link" data-section="modules"',
                'class="nav-link nav-group-toggle" data-section="modules"'
            )
            nav += f'<div class="nav-group-children">\n{module_links}</div>\n'

    return nav


def write_extra_artifacts(output_dir, analysis, content):
    """Write catalog-info.yaml, .claudeignore.recommended, and CLAUDE.md.snippet."""
    out = Path(output_dir)
    meta = analysis.get('meta') or {}
    stack = analysis.get('stack') or {}
    entry_points = analysis.get('entry_points') or []
    clusters = analysis.get('clusters') or []
    external_deps = analysis.get('external_deps_top10') or []
    skip_candidates = analysis.get('skip_candidates') or []
    overview = content.get('overview') or {}

    project_name = meta.get('name', 'unknown')
    language = stack.get('primary_language', 'Unknown')
    framework = stack.get('framework', '')
    tags = [t for t in [language.lower(), framework.lower() if framework else None] if t]

    # Infer component type from entry points
    ep_types = [ep.get('type', '') for ep in entry_points]
    comp_type = 'service'
    if any('web' in t or 'http' in t or 'server' in t for t in ep_types):
        comp_type = 'service'
    elif any('lib' in t for t in ep_types):
        comp_type = 'library'

    # catalog-info.yaml (Backstage-compatible)
    summary_first_sentence = ''
    if overview.get('summary'):
        parts = str(overview['summary']).split('.')
        summary_first_sentence = parts[0].strip() + '.' if parts else str(overview['summary'])[:120]

    deps_list = '\n'.join(f'  - {e(d.get("name", ""))}' for d in external_deps[:8] if d.get('name'))
    tags_list = '\n'.join(f'  - {t}' for t in tags[:6])

    # Try to infer owner from CODEOWNERS
    owner = 'unknown'
    codeowners_candidates = [
        Path(analysis.get('_repo_path', '')) / 'CODEOWNERS',
        Path(analysis.get('_repo_path', '')) / '.github' / 'CODEOWNERS',
    ]
    for cp in codeowners_candidates:
        try:
            first_line = cp.read_text(encoding='utf-8', errors='ignore').strip().splitlines()
            if first_line:
                parts = first_line[0].split()
                if len(parts) >= 2:
                    owner = parts[1].lstrip('@')
                    break
        except Exception:
            pass

    catalog_yaml = f"""apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: {project_name}
  description: {summary_first_sentence or f'{project_name} service'}
  tags:
{tags_list if tags_list else '  - unknown'}
spec:
  type: {comp_type}
  lifecycle: production
  owner: {owner}
  dependsOn:
{deps_list if deps_list else '  []'}
"""
    try:
        (out / 'catalog-info.yaml').write_text(catalog_yaml, encoding='utf-8')
    except Exception as e_:
        print(f'Warning: could not write catalog-info.yaml: {e_}', file=sys.stderr)

    # .claudeignore.recommended
    ignore_lines = ['# Auto-generated by RepoTour — review before use', '']
    # Lock files / package manager artifacts
    ignore_lines += ['# Lock files and package manager artifacts', 'package-lock.json', 'yarn.lock',
                     'pnpm-lock.yaml', 'bun.lockb', 'Gemfile.lock', 'Cargo.lock',
                     'poetry.lock', 'Pipfile.lock', '']
    # Build output dirs
    ignore_lines += ['# Build outputs', 'dist/', 'build/', 'target/', '.next/', 'out/', '.nuxt/',
                     '__pycache__/', '*.pyc', '*.pyo', '']
    # Generated code
    ignore_lines += ['# Generated files', '__generated__/', '*.generated.ts', '*.pb.ts', '*.pb.go',
                     '*_pb2.py', '']
    # Large / noisy files from skip_candidates
    if skip_candidates:
        ignore_lines += ['# Large or minified files detected in this repo']
        for f in skip_candidates[:10]:
            ignore_lines.append(str(f))
        ignore_lines.append('')

    try:
        (out / '.claudeignore.recommended').write_text('\n'.join(ignore_lines), encoding='utf-8')
    except Exception as e_:
        print(f'Warning: could not write .claudeignore.recommended: {e_}', file=sys.stderr)

    # CLAUDE.md.snippet
    ep_lines = '\n'.join(f'- {ep.get("file", "")} ({ep.get("trigger", "")})' for ep in entry_points[:3])
    cluster_lines = '\n'.join(f'- {cl.get("name", "")}: {", ".join(cl.get("files", [])[:3])}' for cl in clusters[:6])
    test_fw = stack.get('test_framework', 'unknown')
    db = stack.get('database', '')
    ci = stack.get('ci', '')

    snippet_lines = [
        f'# {project_name} — CLAUDE.md snippet (auto-generated by RepoTour)',
        '',
        '## Tech Stack',
        f'- Language: {language}',
    ]
    if framework:
        snippet_lines.append(f'- Framework: {framework}')
    if db:
        snippet_lines.append(f'- Database: {db}')
    if test_fw and test_fw != 'unknown':
        snippet_lines.append(f'- Tests: {test_fw}')
    if ci:
        snippet_lines.append(f'- CI: {ci}')

    snippet_lines += ['', '## Entry Points']
    snippet_lines.append(ep_lines or '- (none detected)')

    snippet_lines += ['', '## Module Boundaries']
    snippet_lines.append(cluster_lines or '- (no clusters detected)')

    snippet_lines += [
        '',
        '## Architecture (3 sentences)',
        f'This is a {language} {framework or "application"}. ' +
        (f'It has {meta.get("total_files", 0)} total files across {len(clusters)} logical clusters. ' if clusters else '') +
        'See full tour for detailed architecture, workflows, and developer cookbook.',
        '',
        '## Compaction instructions',
        'When context gets long: summarize completed tasks, keep active file paths, preserve error messages.',
    ]

    try:
        (out / 'CLAUDE.md.snippet').write_text('\n'.join(snippet_lines), encoding='utf-8')
    except Exception as e_:
        print(f'Warning: could not write CLAUDE.md.snippet: {e_}', file=sys.stderr)


def write_readme(output_dir, project_name):
    """Write a README.md for the output folder."""
    readme = f"""# {project_name} — RepoTour

This is an auto-generated codebase tour for **{project_name}**.

## View

Open `index.html` in your browser:
```
open index.html
```

## Deploy

**Vercel**: `npx vercel .`
**Netlify**: `npx netlify deploy --dir .`
**GitHub Pages**: `npx gh-pages -d .`

---
Generated by [RepoTour](https://github.com/UpayanGhosh/tldr-skill)
"""
    (Path(output_dir) / 'README.md').write_text(readme, encoding='utf-8')


def main():
    args = parse_args()

    # Load inputs
    analysis = load_json(args.analysis)
    templates = load_templates(args.templates)
    content = load_all_content(args.content_dir)

    project_name = (analysis.get('meta') or {}).get('name', 'Project')

    # Load optional graph data
    graph_data = load_json(args.graph) if args.graph else None

    # Generate per-section HTML
    mindmap_html = gen_mindmap(analysis)
    sections_html = {
        'overview':       gen_overview(content.get('overview')),
        'architecture':   gen_architecture(content.get('architecture')),
        'mindmap':        mindmap_html,
        'code_map':       gen_code_map(graph_data, content.get('modules')),
        'cross_cutting':  gen_cross_cutting(content.get('cross_cutting')),
        'tech_stack':     gen_tech_stack(content.get('tech_stack')),
        'entry_points':   gen_entry_points(content.get('entry_points')),
        'modules':        gen_modules(content.get('modules')),
        'workflows':      gen_workflows(content.get('workflows')),
        'directory_guide':gen_directory_guide(content.get('directory_guide')),
        'glossary':       gen_glossary(content.get('glossary_getting_started')),
        'getting_started':gen_getting_started(content.get('glossary_getting_started')),
        'cookbook':       gen_cookbook(content.get('cookbook')),
    }

    # Build navigation + search index
    nav_html = build_navigation(content, has_mindmap=bool(mindmap_html), has_codemap=bool(graph_data))
    search_index_js = build_search_index(content)

    # Assemble
    output_html = assemble(templates, sections_html, nav_html, search_index_js, analysis, project_name)

    # Write output
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'index.html'
    out_file.write_text(output_html, encoding='utf-8')
    write_readme(str(out_dir), project_name)
    write_extra_artifacts(str(out_dir), analysis, content)

    # Stats
    stats = {
        'output_file': str(out_file),
        'size_bytes': len(output_html.encode('utf-8')),
        'size_kb': round(len(output_html.encode('utf-8')) / 1024, 1),
        'sections_generated': [k for k, v in sections_html.items() if v],
        'modules_count': len(content.get('modules') or []),
        'search_entries': len(json.loads(search_index_js)),
        'project_name': project_name,
    }
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    main()
