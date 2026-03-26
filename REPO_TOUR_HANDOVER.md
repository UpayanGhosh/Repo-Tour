# RepoTour — Complete Build Handover for Claude Code

> **Read this entire file before writing any code.** This is the complete specification for building a Claude Code skill called `repo-tour` that turns any repository into an interactive explainer website. Everything you need — architecture, constraints, code specs, agent definitions, templates — is in this single document.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Constraints (Non-Negotiable)](#2-architecture-constraints)
3. [Directory Structure](#3-directory-structure)
4. [Build Sequence](#4-build-sequence)
5. [Sprint 1: Scaffold + Scripts + Agents](#5-sprint-1)
6. [Sprint 2: Reference Documents](#6-sprint-2)
7. [Sprint 3: Website Templates + Generator](#7-sprint-3)
8. [Sprint 4: Integration Testing + Calibration](#8-sprint-4)
9. [Sprint 5: Open Source Package](#9-sprint-5)
10. [Appendix A: Agent Definitions](#appendix-a)
11. [Appendix B: Token Budgets](#appendix-b)
12. [Appendix C: File Size Tiers](#appendix-c)
13. [Appendix D: Section Content Schemas](#appendix-d)
14. [Appendix E: generate_site.py Architecture](#appendix-e)

---

## 1. Project Overview

**Name**: `repo-tour`
**Tagline**: "Drop a repo. Get a guided tour."

**What it does**: A Claude Code skill (Skills 2.0 compliant) that analyzes any codebase and generates a self-contained, interactive, static website that explains the entire project — architecture, workflows, data flows, module responsibilities — as if a senior engineer is walking a new hire through the codebase.

**The output**: A single `index.html` file (no build step, no dependencies except Mermaid CDN) that can be opened locally or deployed to Vercel/Netlify/GitHub Pages.

**Target**: Open source, Apache 2.0, GitHub — designed to earn stars.

**Pipeline**: `SCAN → EXPLAIN → GENERATE → PACKAGE`
- SCAN: Python scripts + Haiku subagents analyze the repo (deterministic + cheap LLM)
- EXPLAIN: Sonnet generates explanatory content section-by-section (quality LLM)
- GENERATE: Python script assembles the website from templates + content (zero LLM)
- PACKAGE: Deliver the output folder with deploy instructions

---

## 2. Architecture Constraints

These are non-negotiable. Every decision in this build must respect these constraints.

### Constraint 1: Token Optimization — Disk as Memory

**Never hold more than one phase's working data in context at a time.** Each phase writes structured output to disk. The next phase reads ONLY what it needs from disk.

```
Phase 1 scripts → repo-analysis.json (on disk)
                   ↓ (read SELECTIVELY via extract_section.py)
Phase 2 loop   → site-content/*.json (one file per section, on disk)
                   ↓ (generate_site.py reads from disk)
Phase 3 script → index.html (on disk)
```

### Constraint 2: 32k Output Ceiling

No single LLM generation call may produce more than ~4000 tokens of output. Content generation happens in a loop of 9 focused section calls, not one monolithic call.

### Constraint 3: Model Pyramid

```
         OPUS (optional)  — Quality review gate
           │
         SONNET           — Orchestrator + content writer  
           │
    HAIKU  HAIKU  HAIKU   — Worker swarm (file reading, summarization)
```

- Haiku subagents do ALL file reading and summarization (~70% of tokens)
- Sonnet orchestrates and writes explanatory content (~25% of tokens)
- Opus does optional quality review (~5% of tokens)
- **Sonnet NEVER reads raw source files during content generation** — it reads Haiku's pre-digested summaries

### Constraint 4: Large File Safety

Every file-reading agent must check `wc -l` FIRST, then use the appropriate reading tier:
- Tier 1 (< 500 lines): Read entire file
- Tier 2 (500-3000 lines): Strategic extraction (head/grep/sed/tail)
- Tier 3 (3000-10000 lines): Skeleton only (signatures + counts)
- Tier 4 (10000+ lines): Metadata only (line count + generated check)

NEVER attempt to read a file over 3000 lines in full.

### Constraint 5: Progressive Disclosure

- SKILL.md: under 150 lines of instructions. References `references/` for deep details.
- Reference files: read on-demand, ONE section at a time.
- Templates: loaded only during Phase 3 by the Python script.
- Agents: defined in `agents/`, invoked by Sonnet as needed.

### Constraint 6: Zero External Dependencies

- All Python scripts: standard library ONLY. Zero pip installs.
- Generated website: single HTML file, only external dep is Mermaid.js CDN (with graceful fallback).
- The skill directory must be under 500KB (excluding test-cases).

### Constraint 7: Graceful Fallback

If Haiku subagent dispatch fails (older Claude Code version, model unavailable), the pipeline falls back to Sonnet doing all file reading directly. The pipeline MUST work in both modes. Test this.

### Constraint 8: Iterative File Building

When writing template files (index.html, styles.css, app.js, generate_site.py), NEVER write more than 200 lines in a single tool call. Build files in chunks of 100-200 lines using create_file for the first chunk and str_replace/append for subsequent chunks. This avoids hitting output limits during development.

---

## 3. Directory Structure

```
repo-tour/
├── SKILL.md                            # Core orchestrator (Sonnet)
├── LICENSE.txt                         # Apache 2.0
├── agents/                             # Haiku subagent definitions
│   ├── smoke-test.md                   # Subagent capability verification
│   ├── file-reader.md                  # Bulk file analysis (model: haiku)
│   ├── workflow-verifier.md            # Workflow trace verification (model: haiku)
│   └── section-preloader.md            # Pre-reads files before Sonnet writes (model: haiku)
├── references/
│   ├── ANALYSIS_GUIDE.md               # Phase 1 methodology + repo-analysis.json schema
│   ├── SECTION_PROMPTS.md              # Per-section generation prompts (one section at a time)
│   ├── WRITING_GUIDE.md                # General tone + style standards (~300 words)
│   ├── WEBSITE_SPEC.md                 # Full website specification
│   └── TECH_STACK_PROFILES.md          # Framework-specific analysis hints
├── templates/
│   ├── index.html                      # HTML shell with {{PLACEHOLDER}} markers
│   ├── styles.css                      # Complete stylesheet (dark/light, responsive)
│   └── app.js                          # Navigation, search, toggles, Mermaid, dark mode
├── scripts/
│   ├── scan_repo.py                    # Repo structure scanner (budget: ~800 tokens output)
│   ├── detect_stack.py                 # Tech stack detection (budget: ~400 tokens)
│   ├── find_entry_points.py            # Entry point finder (budget: ~500 tokens)
│   ├── map_dependencies.py             # Dependency graph + classification + scoring (budget: ~1500 tokens)
│   ├── merge_analysis.py               # Merges script outputs, enforces token budget
│   ├── extract_section.py              # Extracts section-relevant slice from analysis
│   ├── generate_site.py                # Assembles final website (zero LLM, unlimited output)
│   └── calibrate.py                    # Token budget calibration tool for testing
├── test-cases/
│   └── repos.md                        # Links to test repos of varying sizes
└── README.md                           # GitHub README (for the open-source repo)
```

---

## 4. Build Sequence

Execute sprints sequentially. **After each sprint, pause and show me what you built before proceeding.**

---

## 5. Sprint 1: Scaffold + Scripts + Agents

### Step 1.0: Create the full directory structure

Create every directory and placeholder files. Use `mkdir -p` for nested directories.

### Step 1.1: Subagent Smoke Test

Create `agents/smoke-test.md` and test it FIRST before building anything else:

```yaml
---
name: smoke-test
description: Verify subagent dispatch works
model: haiku
allowed-tools: Bash(echo *) Bash(wc *)
context: fork
---

Run these commands and report results as JSON:
1. echo "haiku-alive"  
2. echo "model-routing-works"

Output: {"status": "ok", "model": "haiku"}
Stay under 50 tokens.
```

Invoke this agent. If it succeeds: the pyramid architecture is viable, proceed with Haiku agents. If it fails: note the error, set a flag `FALLBACK_MODE=true` in a comment at the top of SKILL.md, and plan for Sonnet to do all file reading directly. Continue building either way.

### Step 1.2: Create the Haiku Subagent Definitions

Create three agents in `agents/`. Full specs are in [Appendix A](#appendix-a). Summary:

**`agents/file-reader.md`** (model: haiku, context: fork)
- Receives file paths in batches of 3-5
- FIRST checks `wc -l` for every file, then applies the tiered reading strategy (Appendix C)
- Outputs JSON: path, role, 2-sentence summary, function signatures, imports, gotchas
- Hard cap: 400 tokens per file, 3000 tokens total
- allowed-tools: Read Grep Glob Bash(wc *) Bash(head *) Bash(tail *) Bash(sed *) Bash(grep *)

**`agents/workflow-verifier.md`** (model: haiku, context: fork)
- Receives workflow steps ({file, function} pairs)
- Greps for function first, reads only 20 lines around it. NEVER reads full large files.
- Hard cap: 100 tokens per step, 1500 total
- allowed-tools: Read Grep Bash(wc *) Bash(sed *) Bash(grep *)

**`agents/section-preloader.md`** (model: haiku, context: fork)
- Receives section name + file paths, produces behavioral briefings
- Same tiered reading strategy as file-reader
- Flags large_file: true for Tier 3 files, mega_file: true for Tier 4
- Hard cap: 150 tokens per file, 2000 total
- allowed-tools: Read Grep Glob Bash(wc *) Bash(head *) Bash(tail *) Bash(sed *) Bash(grep *)

### Step 1.3: Create the Python Analysis Scripts

All scripts must:
- Use only Python standard library (zero pip dependencies)
- Accept repo path as first CLI argument
- Output valid JSON to stdout
- Include `estimate_tokens(text)` function (1 token ≈ 4 chars)
- Report `_token_estimate` in output
- Respect the output token budgets in [Appendix B](#appendix-b)
- Truncate any string field to 200 chars max
- Handle errors gracefully (missing files, binary files, encoding issues)
- Skip these directories: node_modules, .git, vendor, dist, build, __pycache__, .next, target, .venv, venv, .tox, coverage, .nyc_output, .cache

**`scripts/scan_repo.py`** — Budget: ~800 tokens output

Takes a repo path. Outputs JSON:
```json
{
  "meta": {
    "name": "repo-name",
    "total_files": 187,
    "total_loc": 12400
  },
  "top_dirs": ["src/", "lib/", "tests/", "config/"],
  "key_files": {
    "package_json": true, "dockerfile": true, "ci_config": true,
    "readme": true, "requirements_txt": false, "cargo_toml": false,
    "go_mod": false, "makefile": true, "docker_compose": false,
    "env_example": true
  },
  "file_counts_by_ext": {"ts": 89, "json": 24, "md": 8, "yml": 5},
  "files_by_size": {
    "small": 142, "medium": 38, "large": 12, "xlarge": 3, "mega": 1
  },
  "mega_files": [
    {"path": "src/generated/types.ts", "lines": 48000, "likely_generated": true}
  ],
  "skip_candidates": ["src/generated/types.ts", "vendor/lodash.min.js"],
  "readme_excerpt": "A REST API for managing...(first 200 chars)",
  "git_info": {
    "recent_commits": ["fix auth bug", "add pagination", "initial commit"],
    "branch_count": 4
  },
  "_token_estimate": 780
}
```

Specific requirements:
- Directory tree: first 2 levels only, max 30 entries
- File counts: top 8 extensions only
- LOC: approximate (sample if >1000 files)
- Detect minified files: line count < 5 AND max line length > 1000 chars → add to skip_candidates
- File size tiers: small (<500 lines), medium (500-3000), large (3000-10000), mega (10000+)

**`scripts/detect_stack.py`** — Budget: ~400 tokens output

Takes a repo path. Outputs JSON:
```json
{
  "stack": {
    "primary_language": "TypeScript",
    "framework": "Express",
    "runtime": "Node.js",
    "database": "PostgreSQL (via Prisma)",
    "test_framework": "Jest",
    "build_tool": "esbuild",
    "ci": "GitHub Actions",
    "package_manager": "pnpm",
    "dep_count": {"prod": 24, "dev": 18}
  },
  "_token_estimate": 350
}
```

Detection strategy:
- Check config files: package.json, pyproject.toml, Cargo.toml, go.mod, pom.xml, build.gradle, *.csproj
- Framework detection via dependency names and import patterns:
  - JS/TS: express, next, react, vue, angular, nestjs, fastify in package.json
  - Python: django, flask, fastapi in requirements.txt/pyproject.toml/setup.py
  - Java: spring-boot in pom.xml, build.gradle
  - Go: gin, echo in go.mod
  - Rust: actix, rocket, axum in Cargo.toml
  - C#: Microsoft.AspNetCore in *.csproj

**`scripts/find_entry_points.py`** — Budget: ~500 tokens output

Takes a repo path + optional stack JSON (piped from detect_stack). Outputs JSON:
```json
{
  "entry_points": [
    {"file": "src/index.ts", "type": "server_start", "hint": "Express app.listen"},
    {"file": "src/routes/index.ts", "type": "route_root", "hint": "Router mounting"},
    {"file": "src/workers/queue.ts", "type": "background", "hint": "Bull queue processor"}
  ],
  "_token_estimate": 420
}
```

Max 10 entry points. Types: server_start, app_root, route_root, cli_entry, background, test_runner.
Look for: main.py, index.js/ts, app.py, main.go, src/main.rs, App.tsx, manage.py, Procfile.

**`scripts/map_dependencies.py`** — Budget: ~1500 tokens output

Takes a repo path + language info. This is the heaviest script. Outputs JSON:
```json
{
  "critical_modules": [
    {
      "path": "src/services/auth.ts",
      "imports": ["src/lib/db.ts", "src/lib/jwt.ts"],
      "imported_by": ["src/routes/auth.ts", "src/middleware/auth.ts"],
      "role": "service",
      "loc": 245,
      "complexity": 8.2,
      "read_tier": "direct"
    }
  ],
  "clusters": [
    {"name": "auth-system", "files": ["src/services/auth.ts", "src/lib/jwt.ts", "src/middleware/auth.ts"]}
  ],
  "external_deps_top10": [
    {"name": "express", "purpose": "http-server"},
    {"name": "prisma", "purpose": "orm"}
  ],
  "circular_warnings": [],
  "_token_estimate": 1400
}
```

Only output files above complexity threshold. Max 15 modules (controlled by `--max-modules` flag). Skip test files, config files, type definitions, and utilities under 50 LOC. Max 6 clusters.

Import parsing strategy by language:
- JS/TS: regex for `import ... from '...'`, `require('...')`
- Python: regex for `from ... import`, `import ...`
- Go: regex for `import "..."` blocks
- Rust: regex for `use ...;`, `mod ...;`
- Java: regex for `import ...;`
- C#: regex for `using ...;`

File classification roles: config, route, controller, model, service, utility, test, migration, static_asset, documentation, build, ci_cd, middleware, type_definition.

Complexity scoring: LOC × 1.0 + import_count × 0.5 + export_count × 0.3 + (nesting_depth_estimate × 0.2). Normalize to 0-10 scale.

**`scripts/merge_analysis.py`** — Budget: 3500 tokens output

Takes individual script outputs and produces unified `repo-analysis.json`:

```bash
python scripts/merge_analysis.py \
  --scan /tmp/rt_scan.json \
  --stack /tmp/rt_stack.json \
  --entries /tmp/rt_entries.json \
  --deps /tmp/rt_deps.json \
  --budget 3500
```

Features:
- Deduplicates redundant info across scripts
- `--budget N` flag: if estimated tokens exceed budget, trim lowest-complexity modules first
- Outputs `_meta.token_estimate` and `_meta.within_budget` fields
- Final schema: `{meta, stack, entry_points, critical_modules, clusters, external_deps_top10, top_dirs, readme_excerpt, git_info, files_by_size, mega_files, skip_candidates, glossary_candidates}`
- `glossary_candidates` is initially empty — Sonnet fills this after reading modules

**`scripts/extract_section.py`** — Utility for Phase 2

Extracts only the fields needed for a specific section:

```bash
python scripts/extract_section.py <section_name> repo-analysis.json [--batch N --batch-size M]
```

Section → fields mapping:
- `overview` → meta, readme_excerpt, entry_points[:2]
- `architecture` → clusters, entry_points, critical_modules (paths + roles only)
- `tech_stack` → stack
- `entry_points` → entry_points
- `modules` → critical_modules (paged with --batch and --batch-size, default batch-size 8)
- `workflows` → workflows (field added by Sonnet in Phase 1)
- `directory_guide` → top_dirs
- `glossary` → glossary_candidates, stack

**`scripts/calibrate.py`** — Testing utility

Runs all Phase 1 scripts on a given repo and reports:
- Actual output size in chars and estimated tokens for each script
- Whether each script's output fits its budget
- Pass/fail per script and overall

```bash
python scripts/calibrate.py /path/to/repo
```

### Step 1.4: Create SKILL.md

The SKILL.md is the orchestrator. It runs on Sonnet. Keep it under 150 lines. Here's the structure:

```yaml
---
name: repo-tour
description: >
  Generate an interactive explainer website for any codebase. Use when the user
  asks to explain a repository, generate documentation, create a codebase tour,
  onboard onto a new project, or understand how a codebase works. Also trigger
  when the user says "explain this repo", "how does this codebase work",
  "generate docs", "create a walkthrough", "help me understand this code",
  or "onboard me onto this codebase". Works with any programming language.
---
```

SKILL.md body must include these sections (concise — deep details go in references/):

1. **Pipeline overview** — 4 phases in 2 sentences each
2. **Compatibility check** — Run smoke-test agent first. Set FALLBACK_MODE if it fails.
3. **Phase 1: SCAN** — Run Python scripts, dispatch Haiku file-reader agents in parallel batches, Sonnet synthesizes analysis + traces workflows, write `repo-analysis.json`
4. **Phase 2: EXPLAIN** — Section-by-section loop. For each section: run extract_section.py, dispatch section-preloader Haiku agent for relevant files, read section prompt from SECTION_PROMPTS.md (ONE section only), generate content JSON, write to site-content/{name}.json
5. **Phase 3: GENERATE** — Run generate_site.py (one bash command)
6. **Phase 4: PACKAGE** — Report stats, provide deploy commands
7. **Scope calibration** — Adjust depth by repo size (<50, 50-500, 500-2000, 2000+ files)
8. **Quality checklist** — Verify before delivering
9. **Haiku dispatch rules** — How to batch files, when Sonnet should read directly, retry-with-specificity pattern

Reference these files for deep details:
- `references/ANALYSIS_GUIDE.md` for Phase 1 methodology
- `references/SECTION_PROMPTS.md` for Phase 2 per-section instructions
- `references/WRITING_GUIDE.md` for tone and style
- `references/WEBSITE_SPEC.md` for Phase 3 website spec
- `references/TECH_STACK_PROFILES.md` for framework-specific analysis

### Step 1.5: Test Sprint 1

- Run `scripts/scan_repo.py` on this repo-tour directory itself
- Run `scripts/detect_stack.py` on it
- Run `scripts/calibrate.py` on it (if there's enough to scan)
- Verify all JSON outputs are valid and within budget
- Verify smoke-test agent works (or note fallback mode)

**Pause here. Show me what you built. Wait for my approval before Sprint 2.**

---

## 6. Sprint 2: Reference Documents

Write these reference files. Claude reads them on-demand during skill execution.

### `references/ANALYSIS_GUIDE.md`

Phase 1 detailed methodology:
- How to run scripts and pipe outputs to merge_analysis.py
- Token budget enforcement: total repo-analysis.json must be under 3500 tokens (~14000 chars)
- How Sonnet reads the top 10-15 modules after Haiku summarizes them (dispatch Haiku file-reader agents in batches)
- Strategy for identifying key workflows: trace from entry points through import chains, look for common patterns (request → route → service → DB, CLI → command → handler → output)
- Workflow identification output format: Sonnet adds a `workflows` field to repo-analysis.json with [{name, trigger, steps: [{file, function, action}]}]
- Edge cases: monorepos (ask user which package), no clear entry point (look at package.json scripts, Makefile targets), polyglot repos (analyze the primary language first)
- The complete repo-analysis.json schema with field descriptions
- Batching strategy: files > 3000 lines get solo batches, mixed small/medium = batch of 3-4, all small = batch of 5
- Targeted deep-read pattern: if a critical module was skeleton-analyzed and the summary is insufficient, send a targeted Haiku agent to read just the 3-5 most important functions with specific questions

### `references/SECTION_PROMPTS.md`

**This is the most critical file for token optimization.** Per-section generation prompts that Claude reads ONE AT A TIME.

Structure each section with:
- **"What to Read from Analysis"** — exact extract_section.py command
- **"Pre-Read"** — what the section-preloader agent should read and summarize
- **"Your Task"** — exact JSON schema to generate
- **"Writing Rules"** — tone, word limits, quality rules
- **"Token Budget"** — max output tokens
- **"Example Output"** — one concrete good example

Sections and their budgets:

| Section | Output Budget | Pre-Read Needed? |
|---------|--------------|-----------------|
| overview | ~800 tokens | No (uses Phase 1 data) |
| architecture | ~1500 tokens | No (uses Phase 1 clusters) |
| tech_stack | ~1000 tokens | No (uses Phase 1 stack) |
| entry_points | ~1200 tokens | Yes — read each entry point file |
| modules_batch (per batch of 8) | ~3500 tokens | Yes — read each module in batch |
| workflows | ~2500 tokens | Yes — verify each workflow step |
| directory_guide | ~800 tokens | No |
| glossary_getting_started | ~1200 tokens | Yes — read CI/Docker/Makefile for setup commands |

Per-module word caps: simple_explanation max 80 words, detailed_explanation max 200 words, gotchas max 40 words.

Per-workflow step cap: max 100 words per step, max 8 steps per workflow.

Writing rules to include in every section prompt:
- Tone: Friendly senior engineer, never condescending, never academic
- Start every major concept with a real-world analogy
- Every section has "simple" (ELI5) and "detailed" (implementation-level) content
- No assumed knowledge — define jargon inline or link to glossary
- Concrete over abstract: "This function takes the user's email, checks it against the database, and returns a token" beats "This module handles credential validation"
- For modules analyzed at Tier 3/4 (large files): "This is a large module (~N lines) — this explanation covers its role and public interface, not internal implementation details."

Quality self-check after each section:
- Does every module explanation reference a specific behavior?
- Are analogies concrete?
- If a briefing was too vague, dispatch a targeted Haiku agent with specific questions (retry-with-specificity)

### `references/WRITING_GUIDE.md`

Short (~300 words). General tone and style standards that apply everywhere. This is loaded once at the start of Phase 2 for overall guidance. The per-section details are in SECTION_PROMPTS.md.

### `references/WEBSITE_SPEC.md`

Full spec for the generated website:
- Single-page application, single index.html, zero build step
- Semantic HTML5, accessible (ARIA labels, keyboard nav, focus states)
- Navigation: fixed sidebar (desktop), drawer (mobile), with active state tracking via IntersectionObserver
- Simple/Detailed toggle on every major section (default: simple, click to expand)
- Search: client-side full-text search across all sections, modal overlay, keyboard shortcut (Ctrl+K)
- Mermaid.js for architecture + sequence diagrams (CDN import, graceful fallback showing raw code if offline)
- Dark/light mode: detect system preference, allow manual override, persist choice
- Color scheme: auto-determined by primary language (blue for TS/JS, green for Python, orange for Rust, cyan for Go, red for Java, purple for C#, slate for default)
- Typography: Google Fonts CDN — distinctive heading font + clean body font (suggest Fraunces/DM Sans or Playfair Display/Outfit, but don't repeat the same pairing every time)
- Responsive: sidebar collapses on mobile, content stacks vertically
- Print stylesheet: clean, readable, hides navigation and toggles
- "Deploy This" dropdown: copy-to-clipboard commands for Vercel, Netlify, GitHub Pages
- Clickable architecture diagram: clicking a node scrolls to that module's section

### `references/TECH_STACK_PROFILES.md`

Framework-specific analysis hints. For each supported framework:
- Where to find routes, models, controllers, config, middleware, DB schemas
- Import/require patterns
- Common project structure conventions
- Key files to prioritize

Cover at minimum: Express, Next.js, React, Vue, Django, Flask, FastAPI, Spring Boot, Go (standard layout), Rust (Cargo), ASP.NET Core.

**Pause here. Show me Sprint 2 before proceeding to Sprint 3.**

---

## 7. Sprint 3: Website Templates + Generator

This is the most design-critical sprint. The generated website must look professional, not like generic AI docs.

**CRITICAL BUILD RULE**: Build every file iteratively. Never write more than 200 lines in a single tool call. Use create_file for the first chunk, then str_replace to add subsequent sections. This prevents hitting output limits.

### Step 3.1: `templates/index.html` (~200-300 lines)

HTML shell with semantic structure. All content areas are empty `{{PLACEHOLDER}}` markers that generate_site.py fills. Build in 1-2 chunks.

Structure:
```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{PROJECT_NAME}} — RepoTour</title>
  <link href="https://fonts.googleapis.com/css2?family=..." rel="stylesheet">
  <style>{{CSS}}</style>
</head>
<body>
  <nav id="sidebar">
    <div class="sidebar-header">
      <h1>{{PROJECT_NAME}}</h1>
      <button id="theme-toggle" aria-label="Toggle dark mode">...</button>
    </div>
    <div class="sidebar-nav">{{NAV}}</div>
  </nav>
  
  <main id="content">
    <div id="search-bar">...</div>
    
    {{OVERVIEW}}
    {{ARCHITECTURE}}
    {{TECH_STACK}}
    {{ENTRY_POINTS}}
    {{MODULES}}
    {{WORKFLOWS}}
    {{DIRECTORY_GUIDE}}
    {{GLOSSARY}}
    {{GETTING_STARTED}}
    
    <footer>
      Generated by <a href="https://github.com/upayan/repo-tour">RepoTour</a>
      <div class="deploy-dropdown">...</div>
    </footer>
  </main>
  
  <div id="search-modal" hidden>...</div>
  
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <script>{{SEARCH_INDEX}}</script>
  <script>{{JS}}</script>
</body>
</html>
```

### Step 3.2: `templates/styles.css` (~600-800 lines)

Build in 4 chunks (~150-200 lines each):

**Chunk 1**: CSS custom properties (light + dark mode) + base typography + layout grid
- CSS variables: --bg-primary, --bg-secondary, --text-primary, --text-secondary, --accent, --border, etc.
- `[data-theme="dark"]` overrides for all variables
- Language-aware accent colors: `{{COLOR_VARS}}` placeholder that generate_site.py fills
- Google Fonts import reference
- Base typography: heading font + body font, sizes, weights, line-heights
- Layout: sidebar fixed left (280px) + main content area with max-width

**Chunk 2**: Navigation + sidebar styles
- Fixed sidebar, scrollable, active state highlighting
- Mobile drawer (transform: translateX off-screen, toggle class)
- Nav links with hover states and active indicators

**Chunk 3**: Content component styles
- Module cards (bordered, with depth toggle)
- Workflow trace (step indicators, connecting lines/dots)
- Mermaid diagram containers
- Simple/Detailed toggle button and hidden/shown states
- Code blocks with syntax-like coloring
- File tree (collapsible, indented)
- Glossary definition list
- Notice boxes (for large file warnings)

**Chunk 4**: Search modal + responsive + print + animations
- Search modal overlay with input and results
- Responsive breakpoints (768px for tablet, 480px for mobile)
- Print stylesheet (@media print — hide nav, show all content, single column)
- Subtle animations: fade-in on scroll, smooth section transitions

**Design direction**: Clean, editorial feel — like a well-designed technical book. Typography-forward. No generic AI docs aesthetic. Commit to a bold but refined look.

### Step 3.3: `templates/app.js` (~500-700 lines)

Build in 4 chunks (~125-175 lines each):

**Chunk 1**: Navigation + IntersectionObserver
- Track which section is in viewport
- Highlight active nav link
- Smooth scroll to section on nav click
- Mobile nav drawer toggle

**Chunk 2**: Search engine
- Build search index from SEARCH_INDEX global variable on page load
- Simple tokenized matching (split on spaces, match against index entries)
- Search modal: Ctrl+K to open, Escape to close
- Render results with section name + snippet + click to scroll

**Chunk 3**: Toggle system + Mermaid init
- Simple/Detailed toggle: click button → toggle hidden attribute on sibling divs
- Remember preference in a JS variable (NOT localStorage — not available in sandboxed environments)
- Initialize Mermaid on page load with theme matching dark/light mode
- Architecture diagram click handlers: node click → scroll to module section

**Chunk 4**: Dark mode + deploy dropdown + print
- Dark/light toggle: detect prefers-color-scheme, set data-theme attribute
- Manual toggle overrides system preference (stored in JS variable)
- Deploy dropdown: show/hide menu with copy-to-clipboard for Vercel/Netlify/GitHub Pages commands
- Print button
- Mermaid re-render on theme change

### Step 3.4: `scripts/generate_site.py` (~300-400 lines)

Build in 3 chunks (~100-130 lines each). Full architecture is in [Appendix E](#appendix-e).

**Chunk 1**: Main function + file loading + template injection
- parse_args() with --analysis, --content-dir, --templates, --output
- load_json, load_templates, load_all_content (merges module batches)
- assemble() function: reads templates, replaces all {{PLACEHOLDER}} markers
- Color scheme determination from primary language

**Chunk 2**: Per-section HTML generators
- gen_overview(), gen_architecture(), gen_tech_stack(), gen_entry_points()
- gen_modules() — most complex: module cards with simple/detailed, relationships, gotchas, large file notices
- gen_workflows() — step-by-step with Mermaid sequence diagram blocks
- gen_directory_guide(), gen_glossary(), gen_getting_started()
- All use html.escape() for safety. All are pure Python string formatting.

**Chunk 3**: Search index builder + navigation builder + output writing
- build_search_index(): tokenize all text content, create {section, text, id} entries
- build_navigation(): generate sidebar HTML from section names + module list
- get_language_colors(): return CSS variable overrides for the primary language
- write_readme(): generate a README.md for the output folder with view/deploy instructions
- Print stats JSON to stdout

### Step 3.5: Test Sprint 3

- Run generate_site.py with a sample content JSON (create a minimal test fixture)
- Verify the generated index.html opens in a browser conceptually (check structure)
- Verify CSS chunk compilation (no syntax errors — all chunks form valid CSS)
- Verify JS chunk compilation (no syntax errors — all chunks form valid JS)

**Pause here. Show me Sprint 3 before proceeding.**

---

## 8. Sprint 4: Integration Testing + Calibration

### Step 4.1: End-to-End Test

Pick a small real-world repo to test against. Good candidates:
- A local directory with 20-50 files (create a simple Express or Flask app if needed)
- Or use the repo-tour directory itself as the test subject

Run the full pipeline:
1. Run Phase 1 scripts → verify repo-analysis.json is valid and within budget
2. Run Phase 2 section loop → verify all site-content/*.json files are created
3. Run Phase 3 generate_site.py → verify index.html is generated
4. Read the first 50 lines and last 20 lines of the generated HTML to verify structure

### Step 4.2: Calibration

Run `scripts/calibrate.py` on the test repo. Check:
- Are all script outputs within their token budgets?
- Which budgets are too tight? Too generous?
- Adjust the budgets in the scripts based on real data.

### Step 4.3: Fix Issues

Expect issues. Common ones:
- Import parsing regex doesn't catch all patterns for a language
- Complexity scoring produces unexpected rankings
- A section's content is too thin or too verbose
- HTML template has layout issues
- Search index doesn't include all text

Fix each issue found. Re-run the pipeline after fixes.

### Step 4.4: Test on 2-3 More Repos

If possible, test on repos of different sizes and languages:
- A Python project (Flask/FastAPI)
- A larger TypeScript project
- A repo with some large files (> 1000 lines)

**Pause here. Show me test results before Sprint 5.**

---

## 9. Sprint 5: Open Source Package

### Step 5.1: GitHub README.md

Create `README.md` in the repo-tour root (NOT inside the skill):

Sections:
- Hero: project name + tagline + one-line description
- What It Does: 3-sentence explanation + "before/after" description
- Installation: how to install as a Claude Code skill
- Usage: `repo-tour /path/to/repo` or "explain this repo"
- What You Get: description of the generated website sections
- Supported Languages: table of Tier 1 (full support), Tier 2 (good), Tier 3 (basic)
- How It Works: brief pipeline description (scan → explain → generate)
- Configuration: environment variable for quality mode (REPO_TOUR_QUALITY=high for Opus review)
- Contributing: link to CONTRIBUTING.md
- License: Apache 2.0

### Step 5.2: LICENSE.txt

Standard Apache 2.0 license text.

### Step 5.3: test-cases/repos.md

List of recommended test repos:
- Small: express hello-world example
- Medium: a FastAPI project, a Koa project
- Large: strapi, django
- Edge cases: repo with generated files, monorepo

### Step 5.4: Final SKILL.md Review

Re-read the final SKILL.md and verify:
- Description triggers correctly for common phrasings
- All file paths reference the correct locations
- Pipeline steps are clear and ordered
- Fallback mode instructions are included
- Under 150 lines

### Step 5.5: Package Verification

Verify the complete skill directory:
- `ls -la repo-tour/` shows all expected files
- No file over 50KB (except maybe generate_site.py)
- Total skill directory under 500KB
- All Python scripts run without errors on `python scripts/scan_repo.py --help`

---

## Appendix A: Agent Definitions

### agents/smoke-test.md
```yaml
---
name: smoke-test
description: Verify subagent dispatch and model routing works
model: haiku
allowed-tools: Bash(echo *)
context: fork
---
Run: echo "haiku-agent-alive"
Output exactly: {"status": "ok"}
Nothing else. Under 20 tokens.
```

### agents/file-reader.md
```yaml
---
name: file-reader
description: Reads source files and produces structured summaries for codebase analysis. Use for bulk file analysis during repo scanning.
model: haiku
allowed-tools: Read Grep Glob Bash(wc *) Bash(head *) Bash(tail *) Bash(sed *) Bash(grep *)
context: fork
---
You are a file analysis agent. You receive a list of file paths and produce structured JSON summaries.

## MANDATORY FIRST STEP: Check File Size
For EVERY file, before reading ANY content, run:
    wc -l < "file_path"

Then apply the reading tier:

**Under 500 lines (Tier 1)**: Read the entire file. Summarize normally.

**500-3000 lines (Tier 2)**: Strategic read. Do NOT read the whole file:
1. head -50 (imports, module declaration)
2. grep -n for function/method/class signatures
3. sed -n to read 10 lines around the 5 most important-looking functions
4. tail -20 (exports, main block)
5. grep -n for key patterns (error handling, DB queries, API calls, auth)
Note: "Strategic extraction — N lines."

**3000-10000 lines (Tier 3)**: Skeleton only:
1. head -30 (file header)
2. grep -c for total function/class count
3. grep -n for all signatures (list, don't read bodies)
4. Top-level docstring if present
Report: "Skeleton analysis — N lines, ~M functions."

**Over 10000 lines (Tier 4)**: Metadata only. Do NOT read content:
1. wc -l (line count)
2. head -5 (file type identification)
3. grep -c for function count
4. Check first 10 lines for "generated"/"auto-generated"/"DO NOT EDIT"
Report: "Metadata only — N lines. [Generated/Monolithic]. Not analyzed."

## Output Format (JSON array)
[
  {
    "path": "src/services/auth.ts",
    "role": "service",
    "summary": "Two sentences describing what this file does.",
    "functions": [{"name": "login", "params": ["email", "password"]}],
    "imports": ["src/lib/db.ts", "src/lib/jwt.ts"],
    "gotcha": "One sentence about non-obvious behavior. Optional.",
    "read_tier": 1,
    "lines": 245
  }
]

## Rules
- MAX 400 tokens per file in output
- MAX 3000 tokens total output
- Skip binary files, images, lock files (just note "skipped: binary/lock")
- If a file has >10 exported functions, list top 10 by importance
- Do NOT include raw code — only summaries and signatures
- Truncate any string to 200 chars max
```

### agents/workflow-verifier.md
```yaml
---
name: workflow-verifier
description: Traces a workflow through source files and verifies each step exists. Use for validating identified workflows.
model: haiku
allowed-tools: Read Grep Bash(wc *) Bash(sed *) Bash(grep *)
context: fork
---
You verify workflow steps by checking actual source code.

For each step ({file, function}):
1. grep -n "function_name" file_path (find the function)
2. If found in a file under 3000 lines: read 20 lines around that line number
3. If found in a file over 3000 lines: just report the grep match line
4. If NOT found: report as unverifiable, suggest closest match
5. Describe what the function does in 1-2 sentences

Output JSON:
{
  "workflow_name": "...",
  "verified": true/false,
  "steps": [
    {"file": "...", "function": "...", "exists": true, "description": "1-2 sentences", "calls_next": "..."}
  ],
  "issues": ["list of problems found"]
}

Rules:
- MAX 100 tokens per step
- MAX 1500 tokens total
- NEVER read a full large file to verify one function
```

### agents/section-preloader.md
```yaml
---
name: section-preloader
description: Pre-reads source files relevant to a website section and produces compressed briefings for the content writer. Use before generating each content section.
model: haiku
allowed-tools: Read Grep Glob Bash(wc *) Bash(head *) Bash(tail *) Bash(sed *) Bash(grep *)
context: fork
---
You prepare briefings for a content writer. You receive a section name and file paths.

Apply the same tiered reading strategy as file-reader (check wc -l first).

Output JSON:
{
  "section": "modules_batch_0",
  "briefing": [
    {
      "path": "src/services/auth.ts",
      "key_behaviors": "What the code DOES, described in plain language. 2-3 sentences.",
      "patterns_used": "Design patterns, architectural choices",
      "gotchas": "Non-obvious behavior, edge cases, common mistakes",
      "connects_to": "Which modules it depends on and who depends on it",
      "large_file": false,
      "read_tier": 1
    }
  ]
}

Rules:
- Focus on BEHAVIOR not syntax
- MAX 150 tokens per file
- MAX 2000 tokens total
- Flag large_file: true for Tier 3 files
- Flag mega_file: true for Tier 4 files
- The content writer will NOT read raw files — your briefing IS their source material
```

---

## Appendix B: Token Budgets

### Phase 1 Script Output Budgets

| Script | Max Output Tokens | Max Chars (~) |
|--------|------------------|---------------|
| scan_repo.py | 800 | 3200 |
| detect_stack.py | 400 | 1600 |
| find_entry_points.py | 500 | 2000 |
| map_dependencies.py | 1500 | 6000 |
| merge_analysis.py (total) | 3500 | 14000 |

### Phase 2 Section Generation Budgets

| Section | Max Output Tokens | Haiku Pre-Read? |
|---------|------------------|----------------|
| overview | 800 | No |
| architecture | 1500 | No |
| tech_stack | 1000 | No |
| entry_points | 1200 | Yes |
| modules (per batch of 8) | 3500 | Yes |
| workflows | 2500 | Yes |
| directory_guide | 800 | No |
| glossary_getting_started | 1200 | Yes (for setup commands) |

### Phase 2 Context Window Budget Per Section

| Component | Tokens |
|-----------|--------|
| SKILL.md (loaded) | ~600 |
| Section prompt (from SECTION_PROMPTS.md) | ~400 |
| Analysis slice (from extract_section.py) | ~500 |
| Haiku pre-read briefing | ~800 |
| Generated output | ~3000 |
| **Peak total** | **~5300** |

---

## Appendix C: File Size Tiers

| Tier | Lines | Token Estimate | Reading Strategy | Agent Behavior |
|------|-------|---------------|-----------------|----------------|
| 1 | < 500 | < 2000 | Read entire file | Full summary |
| 2 | 500-3000 | 2000-12000 | head + grep + sed + tail | Strategic extraction, labeled |
| 3 | 3000-10000 | 12000-40000 | Signatures + structure only | Skeleton, flagged as large_file |
| 4 | 10000+ | 40000+ | Metadata only, no content read | Line count + generated check |

Auto-skip (never sent to agents):
- Minified files: < 5 lines AND max line length > 1000 chars
- Binary files: images, fonts, compiled assets
- Lock files: package-lock.json, yarn.lock, Cargo.lock, poetry.lock, go.sum
- Generated code with "DO NOT EDIT" / "auto-generated" in first 10 lines (still mentioned in architecture as "generated code")
- Vendor directories

---

## Appendix D: Section Content Schemas

### overview.json
```json
{
  "summary": "2-3 sentences a non-developer could understand. Max 150 words.",
  "audience": "Who uses this and why. 1 sentence.",
  "approach": "Core technical approach in plain language. 1-2 sentences."
}
```

### architecture.json
```json
{
  "analogy": "Real-world analogy for the system. 2-3 sentences.",
  "layers": [
    {"name": "Layer Name", "responsibility": "What this layer does", "key_files": ["path1"]}
  ],
  "mermaid": "graph TD\n  A[Client] --> B[API Layer]\n  ..."
}
```

### tech_stack.json
```json
[
  {"name": "Express", "role": "Web Framework", "why": "Handles HTTP routing and middleware. Chosen for its simplicity and massive ecosystem."}
]
```

### entry_points.json
```json
[
  {"file": "src/index.ts", "trigger": "Server startup", "narrative": "When you run `npm start`, this file runs first. It creates the Express app, loads middleware, mounts routes, and starts listening on port 3000."}
]
```

### modules_batch_N.json
```json
[
  {
    "path": "src/services/auth.ts",
    "name": "Auth Service",
    "simple_explanation": "Max 80 words. What it does and why it exists.",
    "detailed_explanation": "Max 200 words. How it works internally.",
    "depends_on": ["src/lib/db.ts"],
    "depended_by": ["src/routes/auth.ts"],
    "gotchas": "Max 40 words. Optional.",
    "large_file": false
  }
]
```

### workflows.json
```json
{
  "workflows": [
    {
      "name": "User Authentication",
      "trigger": "POST /api/auth/login",
      "steps": [
        {"file": "src/routes/auth.ts", "function": "handleLogin", "narrative": "Max 100 words per step."}
      ],
      "mermaid": "sequenceDiagram\n  Client->>AuthRoute: POST /login\n  ..."
    }
  ]
}
```

### directory_guide.json
```json
[
  {"path": "src/", "purpose": "Core application code", "when_to_look_here": "Start here if you're trying to understand what the app does."}
]
```

### glossary_getting_started.json
```json
{
  "glossary": [
    {"term": "Middleware", "definition": "A function that intercepts every request before it reaches the route handler. Used for auth checks, logging, and error handling."}
  ],
  "getting_started": {
    "clone": "git clone ...",
    "install": "npm install",
    "env_vars": [{"name": "DATABASE_URL", "description": "PostgreSQL connection string"}],
    "run": "npm run dev",
    "first_tasks": ["Try creating a new user via POST /api/auth/signup", "Check the test suite with npm test"]
  }
}
```

---

## Appendix E: generate_site.py Architecture

The site assembler is a pure Python script. No LLM involved. It reads content JSON from disk and produces HTML through string formatting. It can produce arbitrarily large output with zero token limits.

Core functions:
1. `load_all_content(content_dir)` — loads all site-content/*.json, merges module batches
2. `assemble(templates, sections_html, nav, search_index, colors, analysis)` — replaces all {{PLACEHOLDER}} markers in template
3. Per-section HTML generators: `gen_overview()`, `gen_architecture()`, `gen_tech_stack()`, `gen_entry_points()`, `gen_modules()`, `gen_workflows()`, `gen_directory_guide()`, `gen_glossary()`, `gen_getting_started()`
4. `build_search_index(content)` — tokenizes all text, creates search entries
5. `build_navigation(sections, modules)` — generates sidebar HTML
6. `get_language_colors(language)` — returns CSS variable overrides

Key properties:
- Every function uses `html.escape()` for all user-generated content
- Module generator handles `large_file` and `mega_file` flags with appropriate notices
- Mermaid diagrams are wrapped in `<div class="mermaid">` blocks
- Search index is output as a JS global variable
- Color scheme CSS variables are injected based on primary language
- Output is always a single self-contained index.html with inlined CSS and JS

---

## Final Checklist Before Starting

- [ ] Read this entire document before writing any code
- [ ] Start with Sprint 1, step by step
- [ ] Run smoke-test agent FIRST to validate subagent capability
- [ ] Build files iteratively — never more than 200 lines per tool call
- [ ] Test after each sprint — don't proceed without verification
- [ ] Respect token budgets in every script
- [ ] Every Haiku agent checks `wc -l` before reading any file
- [ ] Sonnet never reads raw source files during Phase 2 — only Haiku briefings
- [ ] generate_site.py does ALL HTML assembly — zero LLM involvement in Phase 3
- [ ] Pause after each sprint and show me what you built