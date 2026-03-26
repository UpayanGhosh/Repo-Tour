#!/usr/bin/env python3
import json, os
from pathlib import Path

base = Path('C:/Users/upayan.ghosh/Desktop/Skill/integration-test')
sc = base / 'site-content'
sc.mkdir(exist_ok=True)
d = json.loads((base / 'repo-analysis.json').read_text())

# overview
(sc / 'overview.json').write_text(json.dumps({
    'summary': 'RepoTour is a Claude Code skill that analyzes any codebase and generates a self-contained interactive website explaining the entire project — architecture, workflows, data flows, and module responsibilities — as if a senior engineer is walking a new hire through the code.',
    'audience': 'Developers onboarding to new projects, open-source maintainers, and teams who want living documentation.',
    'approach': 'A Python pipeline scans the repo (deterministic scripts), Haiku subagents summarize files cheaply, and Sonnet writes explanatory content section-by-section. A final Python script assembles everything into a single index.html with no build step required.'
}))

# architecture
(sc / 'architecture.json').write_text(json.dumps({
    'analogy': 'Think of RepoTour like a documentary film crew visiting a factory. The scripts/ folder is the camera crew that observes and records everything. The agents/ folder is the editing suite that compresses hours of footage into highlights. The references/ folder is the script that guides the story. The templates/ folder is the final cut that gets published.',
    'layers': [
        {'name': 'Analysis Layer', 'responsibility': 'Python scripts scan repo structure, detect stack, find entry points, map imports', 'key_files': ['scripts/scan_repo.py', 'scripts/detect_stack.py', 'scripts/map_dependencies.py']},
        {'name': 'Agent Layer', 'responsibility': 'Haiku subagents read files and produce compressed briefings for Sonnet', 'key_files': ['agents/file-reader.md', 'agents/section-preloader.md', 'agents/workflow-verifier.md']},
        {'name': 'Content Layer', 'responsibility': 'Sonnet reads briefings and writes section JSON using prompts from references/', 'key_files': ['SKILL.md', 'references/SECTION_PROMPTS.md', 'references/WRITING_GUIDE.md']},
        {'name': 'Assembly Layer', 'responsibility': 'generate_site.py reads all content JSON and produces the final index.html', 'key_files': ['scripts/generate_site.py', 'templates/index.html', 'templates/styles.css']},
    ],
    'mermaid': 'graph TD\n  Repo[Target Repo] --> Scripts[Analysis Scripts]\n  Scripts --> Analysis[repo-analysis.json]\n  Analysis --> Haiku[Haiku Agents]\n  Haiku --> Briefings[File Briefings]\n  Briefings --> Sonnet[Sonnet Orchestrator]\n  Sonnet --> Content[site-content JSON]\n  Content --> Generator[generate_site.py]\n  Generator --> Site[index.html]'
}))

# tech stack
(sc / 'tech_stack.json').write_text(json.dumps([
    {'name': 'Python stdlib', 'role': 'Analysis Engine', 'why': 'All 7 analysis scripts use zero pip dependencies. RepoTour installs instantly with no virtualenv — just Python 3.8+.'},
    {'name': 'Claude Haiku', 'role': 'File Analysis Agents', 'why': 'Haiku reads and summarizes source files cheaply. At ~70% of token usage, using Haiku vs Sonnet for file reading dramatically reduces cost per tour.'},
    {'name': 'Claude Sonnet', 'role': 'Content Orchestrator', 'why': 'Sonnet reads Haiku briefings and writes the explanatory content for each section. It never reads raw source files — only pre-digested summaries.'},
    {'name': 'Mermaid.js', 'role': 'Diagram Renderer', 'why': 'The only external CDN dependency in the generated website. Gracefully falls back to raw code blocks if offline.'},
]))

# entry points
eps = d.get('entry_points', [])[:5]
ep_content = [
    {'file': ep['file'], 'trigger': f'python {ep["file"]} <args>',
     'narrative': f'Run directly from the command line. Accepts a repo path as the first argument and outputs structured JSON to stdout. Part of the Phase 1 analysis pipeline — results are piped to merge_analysis.py.'}
    for ep in eps
]
(sc / 'entry_points.json').write_text(json.dumps(ep_content))

# modules batch 0
mods = d.get('critical_modules', [])
batch = []
for m in mods[:6]:
    name = m['path'].split('/')[-1].replace('.py', '').replace('_', ' ').title()
    batch.append({
        'path': m['path'], 'name': name, 'role': m['role'],
        'simple_explanation': f'This script is part of the Phase 1 analysis pipeline. It scans the target repository and outputs structured JSON that feeds into the final site generator.',
        'detailed_explanation': f'Accepts a repo path as first CLI argument. Uses only Python standard library — no pip installs. Outputs valid JSON to stdout with a _token_estimate field tracking how close it is to its budget. Errors are handled gracefully: binary files are skipped, encoding errors fall back to utf-8 with replace.',
        'depends_on': m.get('imports', [])[:3],
        'depended_by': m.get('imported_by', [])[:3],
        'gotchas': None,
        'large_file': m.get('read_tier', 'direct') in ('skeleton', 'metadata')
    })
(sc / 'modules_batch_0.json').write_text(json.dumps(batch))

# workflows
(sc / 'workflows.json').write_text(json.dumps({'workflows': [{
    'name': 'Full Pipeline Run',
    'trigger': 'User: "explain this repo" / "generate a tour"',
    'steps': [
        {'file': 'scripts/scan_repo.py', 'function': 'scan_repo', 'narrative': 'First script to run. Walks the directory tree collecting file counts, extensions, size tiers, and a README excerpt. Outputs ~800 token JSON.'},
        {'file': 'scripts/detect_stack.py', 'function': 'detect_stack', 'narrative': 'Reads config files to identify the primary language, framework, runtime, and package manager.'},
        {'file': 'scripts/merge_analysis.py', 'function': 'merge', 'narrative': 'Combines all four script outputs into repo-analysis.json under 3500 tokens. Trims lowest-complexity modules if over budget.'},
        {'file': 'scripts/generate_site.py', 'function': 'main', 'narrative': 'Reads repo-analysis.json and all site-content/*.json files, builds search index and sidebar nav, then writes the final self-contained index.html.'},
    ],
    'mermaid': 'sequenceDiagram\n  actor User\n  User->>SKILL.md: explain this repo\n  SKILL.md->>scan_repo.py: python scan_repo.py <path>\n  scan_repo.py-->>SKILL.md: scan.json\n  SKILL.md->>merge_analysis.py: merge all outputs\n  merge_analysis.py-->>SKILL.md: repo-analysis.json\n  SKILL.md->>Haiku: dispatch file-reader agents\n  Haiku-->>SKILL.md: file briefings\n  SKILL.md->>Sonnet: generate section content\n  Sonnet-->>SKILL.md: site-content JSON\n  SKILL.md->>generate_site.py: assemble site\n  generate_site.py-->>User: index.html'
}]}))

# directory guide
(sc / 'directory_guide.json').write_text(json.dumps([
    {'path': 'agents/', 'purpose': 'Haiku subagent definition files. Each defines a specialized file-reading or verification task.', 'when_to_look_here': 'If you need to understand or modify how file-reader, workflow-verifier, or section-preloader agents work.'},
    {'path': 'scripts/', 'purpose': 'Seven Python analysis scripts (Phase 1) plus the site generator (Phase 3). All stdlib, zero dependencies.', 'when_to_look_here': 'Start here if you want to understand or extend how repos are scanned.'},
    {'path': 'references/', 'purpose': 'Deep reference documents read on-demand by Sonnet during skill execution.', 'when_to_look_here': 'If you want to change writing style, section prompts, or the website structure spec.'},
    {'path': 'templates/', 'purpose': 'HTML/CSS/JS templates for the generated website. styles.css contains the full design system.', 'when_to_look_here': 'If you want to change the look and feel of the generated tour.'},
    {'path': 'test-cases/', 'purpose': 'Links to recommended test repos of varying sizes and languages.', 'when_to_look_here': 'When you want to run a real end-to-end test against a known repo.'},
]))

# glossary + getting started
(sc / 'glossary_getting_started.json').write_text(json.dumps({
    'glossary': [
        {'term': 'Haiku agent', 'definition': 'A subagent running on Claude Haiku. Used for bulk file reading and summarization — cheaper than Sonnet, dispatched in parallel batches of 3-5 files.'},
        {'term': 'Token budget', 'definition': 'A hard cap on output tokens for each script and section. Enforced by merge_analysis.py — lowest-complexity modules are trimmed first if over budget.'},
        {'term': 'Read tier', 'definition': 'How deeply a file is analyzed based on line count. Tier 1 (<500 lines): full read. Tier 2 (500-3000): strategic extraction. Tier 3 (3000-10k): skeleton only. Tier 4 (10k+): metadata only.'},
        {'term': 'repo-analysis.json', 'definition': 'The output of Phase 1 — a single JSON file under 3500 tokens containing everything Sonnet needs to generate the tour without re-reading the source repo.'},
        {'term': 'Fallback mode', 'definition': 'If Haiku dispatch fails (older Claude Code version), Sonnet reads files directly using the same tiered strategy. Set FALLBACK_MODE=true in SKILL.md.'},
        {'term': 'Disk as memory', 'definition': 'Each phase writes output to disk. The next phase reads only what it needs. This prevents context window overflow on large repos.'},
    ],
    'getting_started': {
        'clone': 'git clone https://github.com/upayan/repo-tour',
        'install': '# No install needed — pure Python 3.8+ stdlib',
        'env_vars': [],
        'run': '# In Claude Code:\n# "explain this repo" or "explain /path/to/your/repo"',
        'first_tasks': [
            'Run python scripts/calibrate.py /path/to/any/repo to check script budgets',
            'Open agents/smoke-test.md and dispatch it as a subagent to verify Haiku routing',
            'Try python scripts/scan_repo.py . on any local project to see the JSON output',
        ]
    }
}))

print('All content files written successfully')
