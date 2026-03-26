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

Run from the `scripts/` directory (inside the skill folder). Replace `<REPO>` with the absolute path to the target repo.

**Working directory**: Use `{REPO}/.repotour/` for all intermediate files — this keeps everything together and avoids the /tmp path split on Windows.

```bash
mkdir -p <REPO>/.repotour
WORK=<REPO>/.repotour

python scan_repo.py <REPO> > $WORK/rt_scan.json
python detect_stack.py <REPO> > $WORK/rt_stack.json
python find_entry_points.py <REPO> $WORK/rt_stack.json > $WORK/rt_entries.json
python map_dependencies.py <REPO> --language <LANG> \
  --output-feature-index $WORK/feature-index.json > $WORK/rt_deps.json
python merge_analysis.py --scan $WORK/rt_scan.json --stack $WORK/rt_stack.json \
  --entries $WORK/rt_entries.json --deps $WORK/rt_deps.json \
  --budget 3500 --output $WORK/repo-analysis.json
```

**For compiled-language repos (.NET, Java, Go, C++)**: Build artifacts inflate file counts. Add `--exclude` to filter them:
```bash
# .NET repos: bin/ and obj/ are already excluded by default in scan_repo.py
# Java/Maven: target/ is already excluded by default
# Custom exclusions: python scan_repo.py <REPO> --exclude "generated,migrations"
```

**Sanity check after scan** — verify `source_files` (not `total_files`) for scope calibration:
```bash
python -c "import json; d=json.load(open('$WORK/rt_scan.json')); print('source_files:', d['meta']['source_files'], '| total_files:', d['meta']['total_files'])"
```
If `source_files` is less than 10% of `total_files`, build artifacts may still be present. Add `--exclude` flags.

**Empty scan fallbacks** (if `critical_modules: []` after scripts):
1. Look for project manifest files: `*.csproj`, `*.sln`, `pom.xml`, `build.gradle`, `*.module.ts`, `Cargo.toml`
2. Use these as module seeds — read them directly as Tier 1 files
3. Derive cluster names from top-level directories instead of import graph

**README fallback** (if `readme_excerpt` contains "TODO" or is under 50 chars):
1. Run `git log --oneline -10` to get recent commit messages
2. Use top-level directory names as the structural overview
3. Note in `overview.json`: "README is minimal — overview derived from git history and folder structure"

After scripts complete, dispatch `agents/file-reader.md` in batches:
- Tier 1/2 files: batch 3-5 files per agent call
- Tier 3 files (>3000 lines): solo batches
- Tier 4 files (>10000 lines): skip (metadata already captured)

Synthesize results + trace 2-3 key workflows. Add `workflows` and `glossary_candidates` fields to `$WORK/repo-analysis.json`.
See `references/ANALYSIS_GUIDE.md` for full methodology and workflow identification strategy.

## Phase 2: EXPLAIN

Loop through sections. For each section:
1. Run `extract_section.py <section> $WORK/repo-analysis.json` for data slice
2. For sections marked **REQUIRED pre-read**: dispatch `agents/section-preloader.md` FIRST. Do NOT write the section until the preloader returns. If you skip the preloader, set `"unverified": true` in the output JSON so the site can flag it visually.
3. Read the ONE relevant section from `references/SECTION_PROMPTS.md`
4. Generate content JSON — max 4000 tokens output
5. Write to `$WORK/site-content/<section>.json`

Sections (in order): overview, architecture, cross_cutting, tech_stack, entry_points, modules (batched), workflows, directory_guide, glossary_getting_started, cookbook

**Sonnet NEVER reads raw source files during Phase 2 — only Haiku briefings.**
See `references/SECTION_PROMPTS.md` for per-section schemas and token budgets.
See `references/WRITING_GUIDE.md` for tone and style standards.

## Phase 2.5: VALIDATE (before generating)

Run the validation gate before Phase 3 to catch missing fields early:

```bash
python scripts/validate_content.py --content-dir $WORK/site-content/
```

Fix any `[✗]` failures before proceeding. A broken JSON at this stage produces a broken or empty section in the output with no diagnostic.

## Phase 3: GENERATE

```bash
python scripts/generate_site.py \
  --analysis $WORK/repo-analysis.json \
  --content-dir $WORK/site-content/ \
  --templates templates/ \
  --output $WORK/site/
```

Zero LLM involvement. Pure Python HTML assembly. Unlimited output size.
See `references/WEBSITE_SPEC.md` for the full website specification.

## Phase 4: PACKAGE

Output is at: `{REPO}/.repotour/site/index.html`

Report stats: source files scanned, sections generated, output size.
Provide deploy commands:
- **Local**: `open <REPO>/.repotour/site/index.html`
- **Vercel**: `npx vercel <REPO>/.repotour/site/`
- **Netlify**: `npx netlify deploy --dir <REPO>/.repotour/site/`
- **GitHub Pages**: `gh-pages -d <REPO>/.repotour/site/`

Add `<REPO>/.repotour/` to `.gitignore` if you don't want to commit the generated output.

## Scope Calibration

Use `source_files` (from `meta.source_files` in rt_scan.json), NOT `total_files`. Build artifacts inflate `total_files` dramatically on compiled-language repos.

| Source files | Strategy |
|--------------|----------|
| < 50 | Scan all files, full module analysis |
| 50–500 | Top 20 modules by complexity |
| 500–2000 | Top 15 modules, skip test/config files |
| 2000+ | Top 10 modules, aggregate patterns, note as large repo |

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
