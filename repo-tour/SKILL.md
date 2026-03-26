---
name: tldr
description: >
  Generate an interactive explainer website for any codebase. Use when the user
  asks to explain a repository, generate documentation, create a codebase tour,
  onboard onto a new project, or understand how a codebase works. Also trigger
  when the user says "explain this repo", "how does this codebase work",
  "generate docs", "create a walkthrough", "help me understand this code",
  or "onboard me onto this codebase". Works with any programming language.
---

# RepoTour Orchestrator

**Pipeline**: SCAN → EXPLAIN → GENERATE → PACKAGE
Deep details: see `references/` files. Read ONE reference at a time as needed.

## 0. Compatibility Check

Dispatch `agents/smoke-test.md` FIRST. If it returns `{"status": "ok"}`, proceed normally.
If it fails: add `# FALLBACK_MODE=true` comment here and do all file reading directly with Sonnet (no Haiku agents). Continue either way.

## Phase 1: SCAN

Run from `repo-tour/scripts/` directory. Replace `<REPO>` with the target repo path.

```bash
python scan_repo.py <REPO> > /tmp/rt_scan.json
python detect_stack.py <REPO> > /tmp/rt_stack.json
python find_entry_points.py <REPO> /tmp/rt_stack.json > /tmp/rt_entries.json
python map_dependencies.py <REPO> --language <LANG> > /tmp/rt_deps.json
python merge_analysis.py --scan /tmp/rt_scan.json --stack /tmp/rt_stack.json \
  --entries /tmp/rt_entries.json --deps /tmp/rt_deps.json \
  --budget 3500 --output repo-analysis.json
```

After scripts complete, dispatch `agents/file-reader.md` in batches:
- Tier 1/2 files: batch 3-5 files per agent call
- Tier 3 files (>3000 lines): solo batches
- Tier 4 files (>10000 lines): skip (metadata already captured)

Synthesize results + trace 2-3 key workflows. Add `workflows` and `glossary_candidates` fields to `repo-analysis.json`.
See `references/ANALYSIS_GUIDE.md` for full methodology and workflow identification strategy.

## Phase 2: EXPLAIN

Loop through sections. For each section:
1. Run `extract_section.py <section> repo-analysis.json` for data slice
2. For sections needing pre-read: dispatch `agents/section-preloader.md` with relevant files
3. Read the ONE relevant section from `references/SECTION_PROMPTS.md`
4. Generate content JSON — max 4000 tokens output
5. Write to `site-content/<section>.json`

Sections (in order): overview, architecture, cross_cutting, tech_stack, entry_points, modules (batched), workflows, directory_guide, glossary_getting_started, cookbook

**Sonnet NEVER reads raw source files during Phase 2 — only Haiku briefings.**
See `references/SECTION_PROMPTS.md` for per-section schemas and token budgets.
See `references/WRITING_GUIDE.md` for tone and style standards.

## Phase 3: GENERATE

```bash
python scripts/generate_site.py \
  --analysis repo-analysis.json \
  --content-dir site-content/ \
  --templates repo-tour/templates/ \
  --output output/
```

Zero LLM involvement. Pure Python HTML assembly. Unlimited output size.
See `references/WEBSITE_SPEC.md` for the full website specification.

## Phase 4: PACKAGE

Report stats: files scanned, sections generated, output size.
Provide deploy commands:
- **Local**: `open output/index.html`
- **Vercel**: `npx vercel output/`
- **Netlify**: `npx netlify deploy --dir output/`
- **GitHub Pages**: `gh-pages -d output/`

## Scope Calibration

| Repo size | Strategy |
|-----------|----------|
| < 50 files | Scan all files, full module analysis |
| 50-500 files | Top 20 modules by complexity |
| 500-2000 files | Top 15 modules, skip test/config files |
| 2000+ files | Top 10 modules, aggregate patterns, note as large repo |

## Quality Checklist

Before delivering output:
- [ ] repo-analysis.json under 3500 tokens
- [ ] All 10 site-content/*.json files exist and are valid JSON (including cross_cutting.json and cookbook.json)
- [ ] index.html opens without errors
- [ ] Every module has a specific behavior description (not generic)
- [ ] All mermaid diagrams use valid syntax
- [ ] Search index includes all major sections
- [ ] Simple/detailed toggle works on key sections
- [ ] Cookbook has 5-8 recipes with real file paths (not placeholder names)
- [ ] Getting started learning_path names specific files and features (not generic "explore the code")

## Haiku Dispatch Rules

**Batch strategy**:
- All files under 500 lines → batch of 5
- Mix of small/medium → batch of 3-4
- Any file over 3000 lines → solo batch

**Fallback (retry-with-specificity)**:
If a briefing is too vague, send a targeted Haiku agent with specific questions:
"In `<file>`, find the `<function>` function and answer: [specific questions]"

**FALLBACK_MODE** (if Haiku unavailable):
Sonnet reads files directly using the same tiered strategy. Check wc -l first. Never read files >3000 lines in full.
See `references/TECH_STACK_PROFILES.md` for framework-specific file priorities.
