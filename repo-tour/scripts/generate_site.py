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
# Index 0 = Geist (primary, purpose-built for dev tools)
FONT_PAIRINGS = [
    ('Geist:wght@300..700&family=Geist+Mono:wght@300..600', 'Geist', 'Geist', 'Geist'),
    ('Playfair+Display:wght@400;600;700', 'Outfit:wght@300;400;500;600', 'Playfair Display', 'Outfit'),
    ('Syne:wght@400;600;700;800', 'Inter:wght@300;400;500', 'Syne', 'Inter'),
    ('Cormorant:ital,wght@0,400;0,600;0,700;1,400', 'Plus+Jakarta+Sans:wght@300;400;500;600', 'Cormorant', 'Plus Jakarta Sans'),
]


def parse_args():
    p = argparse.ArgumentParser(description='Generate RepoTour website from content JSON')
    p.add_argument('--analysis',    required=True, help='Path to repo-analysis.json')
    p.add_argument('--content-dir', required=True, help='Directory with site-content/*.json files')
    p.add_argument('--templates',   required=True, help='Path to templates/ directory')
    p.add_argument('--output',      required=True, help='Output directory')
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
    url = f'https://fonts.googleapis.com/css2?family={pair[0]}&family={pair[1]}&display=swap'
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
        mermaid_html = f'<div class="mermaid-wrap"><div class="mermaid" data-clickable="true" data-diagram="{e(data["mermaid"])}"></div></div>'

    return f'''<section class="section" id="architecture">
  <p class="section-label">Architecture</p>
  <h2 class="section-title">How is it organized?</h2>
  {f'<p style="font-size:1rem;color:var(--text-secondary);margin-bottom:1.5rem;font-style:italic">{e(data.get("analogy",""))}</p>' if data.get("analogy") else ""}
  {mermaid_html}
  <h3 style="margin-top:1.5rem;margin-bottom:1rem">Layers</h3>
  {layers_html}
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
        steps_html = ''
        for step in (wf.get('steps') or []):
            steps_html += f'''<div class="workflow-step">
      <div class="step-connector"><div class="step-dot"></div><div class="step-line"></div></div>
      <div class="step-body">
        <div class="step-file">{e(step.get("file",""))}</div>
        <div class="step-function">{e(step.get("function",""))}</div>
        <div class="step-narrative">{e(step.get("narrative",""))}</div>
      </div>
    </div>'''

        mermaid_html = ''
        if wf.get('mermaid'):
            mermaid_html = f'<div class="mermaid-wrap"><div class="mermaid" data-diagram="{e(wf["mermaid"])}"></div></div>'

        wf_html += f'''<div class="workflow">
    <h3>{e(wf.get("name",""))}</h3>
    <div class="workflow-trigger">{e(wf.get("trigger",""))}</div>
    {mermaid_html}
    <div class="workflow-steps">{steps_html}</div>
  </div>'''

    return f'''<section class="section" id="workflows">
  <p class="section-label">Workflows</p>
  <h2 class="section-title">How does it behave?</h2>
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
    """Build a D3.js radial mind map from repo-analysis.json. Zero LLM — pure Python."""
    if not analysis:
        return ''
    meta = analysis.get('meta') or {}
    project_name = meta.get('name', 'Project')
    entry_points = analysis.get('entry_points') or []
    clusters = analysis.get('clusters') or []
    critical_modules = analysis.get('critical_modules') or []
    external_deps = analysis.get('external_deps_top10') or []
    top_dirs = analysis.get('top_dirs') or []
    stack = analysis.get('stack') or {}

    module_paths = {m.get('path', '') for m in critical_modules}

    def slug(path):
        return path.replace('/', '-').replace('.', '-').replace('\\', '-').lower()

    # Build JSON tree for D3
    children = []

    # 1. Entry Points
    if entry_points:
        ep_kids = [
            {'name': ep.get('file', '').replace('\\', '/').split('/')[-1] or ep.get('file', ''),
             'type': 'leaf', 'href': '#entry-points'}
            for ep in entry_points[:10] if ep.get('file')
        ]
        if ep_kids:
            children.append({'name': 'Entry Points', 'type': 'category',
                             'count': len(ep_kids), 'children': ep_kids})

    # 2. Module clusters
    for cluster in clusters[:12]:
        cname = cluster.get('name', 'Modules')
        files = cluster.get('files') or []
        c_kids = []
        for f in files[:15]:
            fname = f.replace('\\', '/').split('/')[-1] or f
            href = '#module-' + slug(f) if f in module_paths else '#modules'
            c_kids.append({'name': fname, 'type': 'module', 'href': href})
        if c_kids:
            children.append({'name': cname, 'type': 'cluster',
                             'count': len(files), 'children': c_kids})

    # Fallback: no clusters
    if not clusters and critical_modules:
        mod_kids = [
            {'name': m.get('path', '').replace('\\', '/').split('/')[-1] or m.get('path', ''),
             'type': 'module', 'href': '#module-' + slug(m.get('path', ''))}
            for m in critical_modules[:20]
        ]
        if mod_kids:
            children.append({'name': 'Modules', 'type': 'category',
                             'count': len(mod_kids), 'children': mod_kids})

    # 3. Tech Stack
    stack_kids = []
    for k in ('framework', 'primary_language', 'runtime', 'database',
               'test_framework', 'package_manager', 'build_tool'):
        v = stack.get(k)
        if v:
            stack_kids.append({'name': v, 'type': 'leaf', 'href': '#tech-stack'})
    for dep in external_deps[:6]:
        n = dep.get('name', '')
        if n:
            stack_kids.append({'name': n, 'type': 'leaf', 'href': '#tech-stack'})
    if stack_kids:
        children.append({'name': 'Tech Stack', 'type': 'category',
                         'count': len(stack_kids), 'children': stack_kids})

    # 4. Directories
    if top_dirs:
        dir_kids = [
            {'name': d, 'type': 'leaf', 'href': '#directory-guide'}
            for d in top_dirs[:15]
        ]
        children.append({'name': 'Directories', 'type': 'category',
                         'count': len(top_dirs), 'children': dir_kids})

    if not children:
        return ''

    tree_data = {'name': project_name, 'type': 'root', 'children': children}
    tree_json = json.dumps(tree_data)
    total = meta.get('total_files', 0)
    stats_str = f'{total:,} files · ' if total else ''
    fallback_items = ''.join(
        f'<li>{e(c["name"])} ({c.get("count", len(c.get("children", [])))} items)</li>'
        for c in children
    )

    return f'''<section class="section" id="codebase-map">
  <p class="section-label">Codebase Map</p>
  <h2 class="section-title">Codebase at a glance</h2>
  <p style="color:var(--text-secondary);font-size:0.875rem;margin-bottom:1rem">{e(stats_str)}click nodes to expand · scroll to zoom · drag to pan</p>
  <div id="mm-wrap" style="position:relative;width:100%;height:580px;border-radius:12px;overflow:hidden;background:var(--bg-surface);border:1px solid var(--border)">
    <svg id="mm-svg" style="width:100%;height:100%"></svg>
    <div id="mm-fallback" style="display:none;padding:1.5rem">
      <p style="font-size:0.875rem;color:var(--text-secondary);margin-bottom:0.75rem">Structure overview:</p>
      <ul style="font-size:0.875rem;color:var(--text-secondary)">{fallback_items}</ul>
    </div>
    <div style="position:absolute;bottom:0.75rem;right:0.75rem;display:flex;gap:0.4rem">
      <button onclick="mmReset()" style="background:var(--bg-primary);border:1px solid var(--border);color:var(--text-secondary);border-radius:6px;padding:0.25rem 0.6rem;font-size:0.72rem;cursor:pointer;line-height:1.4">Reset</button>
      <button onclick="mmExpand()" style="background:var(--bg-primary);border:1px solid var(--border);color:var(--text-secondary);border-radius:6px;padding:0.25rem 0.6rem;font-size:0.72rem;cursor:pointer;line-height:1.4">Expand All</button>
      <button onclick="mmCollapse()" style="background:var(--bg-primary);border:1px solid var(--border);color:var(--text-secondary);border-radius:6px;padding:0.25rem 0.6rem;font-size:0.72rem;cursor:pointer;line-height:1.4">Collapse</button>
    </div>
  </div>
  <script>
(function(){{
var TREE={tree_json};
var W=900,H=900,R=310;
var BC=['oklch(58% 0.20 262)','oklch(62% 0.19 145)','oklch(64% 0.19 30)','oklch(60% 0.18 320)','oklch(55% 0.17 200)','oklch(63% 0.16 60)','oklch(60% 0.20 290)','oklch(62% 0.19 170)','oklch(64% 0.18 10)','oklch(61% 0.17 240)','oklch(63% 0.16 100)','oklch(62% 0.20 350)'];
function trav(d,fn){{fn(d);var ch=d.children||d._ch||[];ch.forEach(function(c){{trav(c,fn);}});}}
function init(){{
  if(typeof d3==='undefined'){{document.getElementById('mm-fallback').style.display='block';document.getElementById('mm-svg').style.display='none';return;}}
  var svg=d3.select('#mm-svg').attr('viewBox',[-W/2,-H/2,W,H]);
  var zb=d3.zoom().scaleExtent([0.2,4]).on('zoom',function(ev){{g.attr('transform',ev.transform);}});
  svg.call(zb);
  var g=svg.append('g');
  var gL=g.append('g').attr('fill','none').attr('stroke-opacity',0.45).attr('stroke-width',1.5);
  var gN=g.append('g').attr('cursor','pointer');
  var tl=d3.tree().size([2*Math.PI,R]).separation(function(a,b){{return(a.parent===b.parent?1:2)/a.depth;}});
  var root=d3.hierarchy(TREE);
  var uid=0;
  root.each(function(d){{d.id=uid++;d._ch=d.children?d.children.slice():null;if(d.depth>0)d.children=null;}});
  if(root._ch){{root.children=root._ch;root._ch=null;}}
  trav(root,function(d){{if(d.depth===1){{var sib=root.children||root._ch||[];d._bi=sib.indexOf(d);}}else if(d.depth>1){{d._bi=d.parent._bi;}}}});
  function col(d){{return d.depth===0?'oklch(54% 0.22 262)':BC[((d._bi||0)%BC.length+BC.length)%BC.length];}}
  function pt(x,y){{var a=x-Math.PI/2;return[y*Math.cos(a),y*Math.sin(a)];}}
  root.x0=0;root.y0=0;
  function upd(src){{
    tl(root);
    var dur=450,nodes=root.descendants().reverse(),links=root.links();
    var lk=gL.selectAll('path.mml').data(links,function(d){{return d.target.id;}});
    var le=lk.enter().append('path').attr('class','mml').attr('d',function(){{var p=pt(src.x0||0,src.y0||0);return'M'+p+'L'+p;}});
    lk.merge(le).transition().duration(dur).ease(d3.easeCubicInOut)
      .attr('stroke',function(d){{return col(d.target);}})
      .attr('d',function(d){{return d3.linkRadial().angle(function(n){{return n.x;}}).radius(function(n){{return n.y;}})(d);}});
    lk.exit().transition().duration(dur).attr('d',function(){{var p=pt(src.x||0,src.y||0);return'M'+p+'L'+p;}}).remove();
    var nd=gN.selectAll('g.mmn').data(nodes,function(d){{return d.id;}});
    var ne=nd.enter().append('g').attr('class','mmn')
      .attr('transform',function(){{var p=pt(src.x0||0,src.y0||0);return'translate('+p+')';}} )
      .attr('opacity',0)
      .on('click',function(ev,d){{
        ev.stopPropagation();
        if(d._ch){{d.children=d.children?null:d._ch;upd(d);}}
        else if(d.data.href){{var el=document.querySelector(d.data.href);if(el)el.scrollIntoView({{behavior:'smooth',block:'start'}});}}
      }});
    ne.append('circle');
    ne.append('text').attr('class','mmt');
    var nm=nd.merge(ne);
    nm.transition().duration(dur).ease(d3.easeCubicInOut)
      .attr('transform',function(d){{var p=pt(d.x,d.y);return'translate('+p+')';}} )
      .attr('opacity',1);
    nm.select('circle').transition().duration(dur)
      .attr('r',function(d){{return d.depth===0?12:d._ch?6:3.5;}})
      .attr('fill',function(d){{return(d.children||d.depth===0)?col(d):d._ch?col(d):'var(--bg-surface)';}})
      .attr('stroke',function(d){{return col(d);}}).attr('stroke-width',2);
    nm.select('text.mmt')
      .attr('dy','0.31em')
      .attr('x',function(d){{if(d.depth===0)return 0;return(d.x<Math.PI)?11:-11;}})
      .attr('text-anchor',function(d){{if(d.depth===0)return'middle';return(d.x<Math.PI)?'start':'end';}})
      .attr('transform',function(d){{if(d.depth===0)return null;return(d.x>=Math.PI)?'rotate(180)':null;}})
      .attr('font-size',function(d){{return d.depth===0?'13px':d.depth===1?'11px':'9.5px';}})
      .attr('font-weight',function(d){{return d.depth<=1?'600':'400';}})
      .attr('fill','var(--text-primary)')
      .text(function(d){{var n=d.data.name||'';return n.length>30?n.slice(0,28)+'\u2026':n;}});
    nd.exit().transition().duration(dur)
      .attr('transform',function(){{var p=pt(src.x||0,src.y||0);return'translate('+p+')';}} ).attr('opacity',0).remove();
    root.each(function(d){{d.x0=d.x;d.y0=d.y;}});
  }}
  upd(root);
  window.mmReset=function(){{svg.transition().duration(400).call(zb.transform,d3.zoomIdentity);}};
  window.mmExpand=function(){{trav(root,function(d){{if(d._ch)d.children=d._ch;}});upd(root);}};
  window.mmCollapse=function(){{trav(root,function(d){{if(d.depth>0&&d._ch)d.children=null;}});if(root._ch){{root.children=root._ch;root._ch=null;}}upd(root);}};
  new MutationObserver(function(){{
    gN.selectAll('text.mmt').attr('fill','var(--text-primary)');
  }}).observe(document.documentElement,{{attributes:true,attributeFilter:['data-theme']}});
}}
if(typeof d3!=='undefined'){{init();}}
else{{
  var ds=document.querySelector('script[src*="d3"]');
  if(ds){{ds.addEventListener('load',init);}}
  setTimeout(function(){{if(typeof d3==='undefined'){{document.getElementById('mm-fallback').style.display='block';document.getElementById('mm-svg').style.display='none';}}}},5000);
}}
}})();
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


def build_navigation(content, has_mindmap=False):
    """Generate sidebar navigation HTML."""
    SECTION_MAP = [
        ('overview',       'overview',       'Overview'),
        ('architecture',   'architecture',   'Architecture'),
        ('mindmap',        'codebase-map',   'Codebase Map'),
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
        auto_show = key in ('glossary_getting_started',) or (key == 'mindmap' and has_mindmap)
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
Generated by [RepoTour](https://github.com/upayan/repo-tour)
"""
    (Path(output_dir) / 'README.md').write_text(readme, encoding='utf-8')


def main():
    args = parse_args()

    # Load inputs
    analysis = load_json(args.analysis)
    templates = load_templates(args.templates)
    content = load_all_content(args.content_dir)

    project_name = (analysis.get('meta') or {}).get('name', 'Project')

    # Generate per-section HTML
    mindmap_html = gen_mindmap(analysis)
    sections_html = {
        'overview':       gen_overview(content.get('overview')),
        'architecture':   gen_architecture(content.get('architecture')),
        'mindmap':        mindmap_html,
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
    nav_html = build_navigation(content, has_mindmap=bool(mindmap_html))
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
