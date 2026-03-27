#!/usr/bin/env python3
"""check_resume.py — Detects existing tldr output and reports what can be skipped.

Usage:
    python check_resume.py <REPO> <WORK_DIR>

Outputs JSON to stdout:
{
  "mode": "fresh" | "resume" | "partial",
  "phase1_skip": bool,       -- skip all Phase 1 scripts and file reading
  "graph_skip": bool,        -- skip build_graph.py
  "sections_skip": [...],    -- Phase 2 sections already generated
  "sections_missing": [...], -- Phase 2 sections that need generating
  "heads_match": bool,
  "git_head_stored": str | null,
  "git_head_current": str | null,
  "phase1_reason": str
}

Exit codes: 0 always (errors embedded in JSON).
"""

import json
import sys
import subprocess
from pathlib import Path

ALL_SECTIONS = [
    'overview', 'architecture', 'cross_cutting', 'tech_stack',
    'entry_points', 'modules', 'workflows', 'directory_guide',
    'glossary_getting_started', 'cookbook',
]


def get_git_head(repo_path: Path) -> str | None:
    try:
        result = subprocess.run(
            ['git', '-C', str(repo_path), 'rev-parse', 'HEAD'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            'mode': 'fresh', 'phase1_skip': False, 'graph_skip': False,
            'sections_skip': [], 'sections_missing': ALL_SECTIONS,
            'heads_match': False, 'git_head_stored': None, 'git_head_current': None,
            'phase1_reason': 'Usage error — expected: check_resume.py <REPO> <WORK_DIR>',
        }))
        sys.exit(0)

    repo = Path(sys.argv[1]).resolve()
    work = Path(sys.argv[2]).resolve()

    analysis_path = work / 'repo-analysis.json'
    graph_path    = work / 'graph-data.json'
    content_dir   = work / 'site-content'

    current_head = get_git_head(repo)

    # ── Fresh run: no prior analysis ──────────────────────────────────────────
    if not analysis_path.exists():
        print(json.dumps({
            'mode': 'fresh',
            'phase1_skip': False,
            'graph_skip': False,
            'sections_skip': [],
            'sections_missing': ALL_SECTIONS,
            'heads_match': False,
            'git_head_stored': None,
            'git_head_current': current_head,
            'phase1_reason': 'No existing repo-analysis.json — running full pipeline.',
        }))
        return

    # ── Parse stored analysis ─────────────────────────────────────────────────
    try:
        analysis = json.loads(analysis_path.read_text(encoding='utf-8'))
    except Exception as exc:
        print(json.dumps({
            'mode': 'fresh',
            'phase1_skip': False,
            'graph_skip': False,
            'sections_skip': [],
            'sections_missing': ALL_SECTIONS,
            'heads_match': False,
            'git_head_stored': None,
            'git_head_current': current_head,
            'phase1_reason': f'Existing repo-analysis.json is corrupt ({exc}) — re-running.',
        }))
        return

    stored_head  = analysis.get('_meta', {}).get('git_head')
    heads_match  = bool(stored_head and current_head and stored_head == current_head)

    # ── Determine skip scope ──────────────────────────────────────────────────
    phase1_skip  = heads_match
    graph_skip   = heads_match and graph_path.exists()

    sections_skip    = []
    sections_missing = []
    for sec in ALL_SECTIONS:
        if heads_match and (content_dir / f'{sec}.json').exists():
            sections_skip.append(sec)
        else:
            sections_missing.append(sec)

    if heads_match:
        short = stored_head[:8] if stored_head else 'unknown'
        reason = f'repo-analysis.json exists and git HEAD matches ({short}) — skipping Phase 1.'
    else:
        stored_short  = stored_head[:8]  if stored_head  else 'none'
        current_short = current_head[:8] if current_head else 'unknown'
        reason = f'git HEAD changed ({stored_short} → {current_short}) — re-running Phase 1.'

    if not heads_match:
        mode = 'fresh'
    elif sections_missing:
        mode = 'partial'
    else:
        mode = 'resume'

    print(json.dumps({
        'mode': mode,
        'phase1_skip': phase1_skip,
        'graph_skip': graph_skip,
        'sections_skip': sections_skip,
        'sections_missing': sections_missing,
        'heads_match': heads_match,
        'git_head_stored': stored_head,
        'git_head_current': current_head,
        'phase1_reason': reason,
    }))


if __name__ == '__main__':
    main()
