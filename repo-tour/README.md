# tldr-skill — Instant Codebase Intelligence for AI Coding Agents

> **Too Long, Didn't Read?** Now you don't have to.

`tldr-skill` is an AI agent skill that turns any codebase — regardless of language or framework — into a fully interactive, self-hosted explainer website in minutes. Works with [Claude Code](https://claude.ai/code), [OpenCode](https://opencode.ai), [Gemini CLI](https://geminicli.com), and [Codex CLI](https://openai.com/codex/). Point it at a repo, say two words, and get a living onboarding document that new developers can actually use.

---

## What it generates

A single `index.html` with no external dependencies (except optional CDN scripts) containing:

| Section | What's inside |
|---|---|
| **Overview** | Plain-English summary a non-developer could understand |
| **Architecture** | Layer diagram, real-world analogy, Mermaid flowchart |
| **Code Map** | Interactive Cytoscape.js dependency graph — every file is a node, every import is an edge. Zoom, pan, drag, search, filter by role, click to navigate |
| **Directory Mind Map** | D3.js radial tree of the actual directory structure, colored by file extension |
| **Cross-Cutting Concerns** | Auth, error handling, logging, testing strategy |
| **Tech Stack** | Every technology with why it was chosen for this specific project |
| **Entry Points** | What runs when, with end-to-end narrative walkthroughs |
| **Modules** | Every important file explained: what it does, how it works, gotchas |
| **Workflows** | Step-by-step request traces with Mermaid sequence diagrams |
| **Directory Guide** | What lives where and when to look there |
| **Getting Started** | Clone → install → run, env vars, Day 1 / Week 1 learning path |
| **Developer Cookbook** | Task-based recipes: "How do I add a new route?" with real file paths and copy-paste code |

Built-in: full-text search (Cmd/Ctrl+K), dark/light mode, three-column layout, mobile-responsive, right-side TOC with scrollspy.

---

## Compatibility

| Tool | Compatible? | Notes |
|---|---|---|
| **Claude Code** | ✅ Native | Built for this — full support |
| **OpenCode** | ✅ Native | Explicitly supports Anthropic-style skills, drop-in compatible |
| **Gemini CLI** | ✅ Compatible | Same Agent Skills open standard, different install path |
| **Codex CLI** | ⚠️ Partial | Python scripts work; needs a thin plugin wrapper for auto-trigger |

> The Python pipeline scripts are pure standard library — they run identically regardless of which AI tool orchestrates them.

---

## Install

### Claude Code

#### macOS / Linux

```bash
# Via npm (recommended — installs automatically)
npx tldr-skill

# Manual
git clone https://github.com/UpayanGhosh/tldr-skill
cp -r tldr-skill/repo-tour ~/.claude/skills/tldr

# Verify
ls ~/.claude/skills/tldr/SKILL.md
```

#### Windows

```powershell
# Via npm (recommended)
npx tldr-skill

# Manual
git clone https://github.com/UpayanGhosh/tldr-skill
xcopy /E /I tldr-skill\repo-tour %USERPROFILE%\.claude\skills\tldr

# Verify
dir %USERPROFILE%\.claude\skills\tldr\SKILL.md
```

**Trigger:** Open Claude Code in any repo → type `/tldr` or say `"explain this repo"`.

---

### OpenCode

OpenCode natively supports Anthropic-compatible skills — no adaptation needed, pure drop-in.

#### macOS / Linux

```bash
git clone https://github.com/UpayanGhosh/tldr-skill
mkdir -p ~/.config/opencode/skills
cp -r tldr-skill/repo-tour ~/.config/opencode/skills/tldr

# Verify
ls ~/.config/opencode/skills/tldr/SKILL.md
```

#### Windows

```powershell
git clone https://github.com/UpayanGhosh/tldr-skill
mkdir -p %APPDATA%\opencode\skills
xcopy /E /I tldr-skill\repo-tour %APPDATA%\opencode\skills\tldr

# Verify
dir %APPDATA%\opencode\skills\tldr\SKILL.md
```

**Trigger:** Type `/tldr` or say `"explain this repo"`. OpenCode discovers skills from `~/.config/opencode/skills/` at startup.

---

### Gemini CLI

Gemini CLI uses the same Agent Skills open standard. Install to `~/.gemini/skills/` or the `~/.agents/skills/` cross-tool alias.

#### macOS / Linux

```bash
git clone https://github.com/UpayanGhosh/tldr-skill

# Option A — Gemini-specific path
mkdir -p ~/.gemini/skills
cp -r tldr-skill/repo-tour ~/.gemini/skills/tldr

# Option B — cross-tool alias (works for Gemini, OpenCode, and others simultaneously)
mkdir -p ~/.agents/skills
cp -r tldr-skill/repo-tour ~/.agents/skills/tldr

# Verify
ls ~/.gemini/skills/tldr/SKILL.md
```

#### Windows

```powershell
git clone https://github.com/UpayanGhosh/tldr-skill

# Option A — Gemini-specific path
mkdir -p %USERPROFILE%\.gemini\skills
xcopy /E /I tldr-skill\repo-tour %USERPROFILE%\.gemini\skills\tldr

# Option B — cross-tool alias
mkdir -p %USERPROFILE%\.agents\skills
xcopy /E /I tldr-skill\repo-tour %USERPROFILE%\.agents\skills\tldr

# Verify
dir %USERPROFILE%\.gemini\skills\tldr\SKILL.md
```

**Trigger:** Type `/tldr` or say `"explain this repo"`. Gemini CLI auto-discovers skills in `~/.gemini/skills/`.

---

### Codex CLI (OpenAI)

Codex uses a different plugin manifest. The Python scripts work perfectly — only the auto-trigger needs a wrapper file.

#### Step 1 — Clone

```bash
git clone https://github.com/UpayanGhosh/tldr-skill
```

#### Step 2 — Install

**macOS / Linux:**
```bash
mkdir -p ~/.codex/plugins/tldr/.codex-plugin
cp -r tldr-skill/repo-tour/. ~/.codex/plugins/tldr/
cp tldr-skill/repo-tour/.codex-plugin/plugin.json ~/.codex/plugins/tldr/.codex-plugin/

# Enable
codex plugin enable tldr
```

**Windows:**
```powershell
mkdir -p %USERPROFILE%\.codex\plugins\tldr\.codex-plugin
xcopy /E /I tldr-skill\repo-tour %USERPROFILE%\.codex\plugins\tldr
copy tldr-skill\repo-tour\.codex-plugin\plugin.json %USERPROFILE%\.codex\plugins\tldr\.codex-plugin\plugin.json

# Enable
codex plugin enable tldr
```

**Trigger:** Type `/tldr` in Codex or say `"explain this repo"`.

---

### Install for all tools at once

Use the `~/.agents/skills/` shared alias — recognised by Gemini CLI, OpenCode, and others. Then separately install for Claude Code and Codex.

**macOS / Linux:**
```bash
git clone https://github.com/UpayanGhosh/tldr-skill

# Shared alias (Gemini + OpenCode + others)
mkdir -p ~/.agents/skills
cp -r tldr-skill/repo-tour ~/.agents/skills/tldr

# Claude Code
mkdir -p ~/.claude/skills
cp -r tldr-skill/repo-tour ~/.claude/skills/tldr
```

**Windows:**
```powershell
git clone https://github.com/UpayanGhosh/tldr-skill

# Shared alias (Gemini + OpenCode + others)
mkdir -p %USERPROFILE%\.agents\skills
xcopy /E /I tldr-skill\repo-tour %USERPROFILE%\.agents\skills\tldr

# Claude Code
mkdir -p %USERPROFILE%\.claude\skills
xcopy /E /I tldr-skill\repo-tour %USERPROFILE%\.claude\skills\tldr
```

---

## Usage

Navigate to any repository in your terminal, open Claude Code, and say:

```
explain this repo
```

or

```
/tldr
```

or any natural phrasing:

- `"how does this codebase work"`
- `"onboard me onto this project"`
- `"generate docs for this repo"`
- `"create a codebase tour"`

Claude runs the full pipeline autonomously. No configuration required.

---

## Output

All generated files land in `{your-repo}/.repotour/`:

```
your-repo/
└── .repotour/
    ├── rt_scan.json          # raw scan data
    ├── rt_stack.json         # detected tech stack
    ├── repo-analysis.json    # merged analysis (LLM budget-capped)
    ├── graph-data.json       # dependency graph (unlimited size)
    ├── feature-index.json    # full file index (sidecar)
    ├── site-content/         # generated JSON per section
    │   ├── overview.json
    │   ├── architecture.json
    │   ├── modules_batch_0.json
    │   └── ...
    └── site/
        └── index.html        ← open this
```

Open locally:
```bash
open .repotour/site/index.html        # macOS
start .repotour/site/index.html       # Windows
xdg-open .repotour/site/index.html   # Linux
```

Or deploy instantly:
```bash
npx vercel .repotour/site/            # Vercel
npx netlify deploy --dir .repotour/site/  # Netlify
gh-pages -d .repotour/site/           # GitHub Pages
```

Add `.repotour/` to `.gitignore` if you don't want to commit generated output.

---

## How it works

The pipeline has four phases:

```
SCAN → EXPLAIN → GENERATE → PACKAGE
```

### Phase 1: SCAN (scripts, zero LLM cost)

Seven Python scripts analyse the repository without any AI involvement:

| Script | What it does |
|---|---|
| `scan_repo.py` | Walks the repo, counts files by extension, detects key files, reads README excerpt, gets git info |
| `detect_stack.py` | Detects language, framework, runtime, database, test framework, monorepo type |
| `find_entry_points.py` | Locates application entry points (main files, route registrations, CLI commands) |
| `map_dependencies.py` | Builds import graph, identifies critical modules and clusters by domain |
| `build_graph.py` | Scans ALL imports for the Cytoscape Code Map — outputs `graph-data.json` which **never enters any LLM context** |
| `merge_analysis.py` | Merges all outputs into `repo-analysis.json`, enforces a 3500-token budget |
| `validate_content.py` | Validates all `site-content/*.json` before site generation (run between phases 2 and 3) |

**Two-tier data pipeline** — the key architectural decision:

```
Scripts → repo-analysis.json (3500 token cap) → Claude reads this
Scripts → graph-data.json   (no size limit)   → Python reads this directly
                                                  LLM never sees graph data
```

### Phase 2: EXPLAIN (Claude Sonnet + Haiku agents)

Claude generates human-readable content for each section using a parallel agent swarm:

- **Tier 0**: One Haiku bootstrapper call builds a module partition map
- **Tier 1**: Parallel Haiku agents (batches of 3-5 files) read source files and return structured JSON briefings
- **Tier 1.5**: Haiku with extended thinking for ambiguous files
- **Tier 2**: Sonnet synthesises briefings into section content
- **Sonnet never reads raw source files** — only Haiku briefings

Sections with a **REQUIRED pre-read** gate won't be written until a preloader agent confirms the source files. If skipped, sections are marked `unverified: true` visually.

### Phase 3: GENERATE (Python, zero LLM cost)

`generate_site.py` assembles the final HTML from templates and content JSON. Pure Python — no AI, no network calls, unlimited output size.

### Phase 4: PACKAGE

Reports stats and provides deploy commands. Output is always at `{repo}/.repotour/site/index.html`.

---

## Language & framework support

**Languages**: TypeScript · JavaScript · Python · Go · Rust · Java · Kotlin · C# · Ruby · PHP · C/C++ · Dart · Swift · Scala · Elixir

**Frameworks with tailored analysis**:
- **Angular** — lazy routes, NgRx store, interceptors, guards, standalone components
- **React / Next.js** — server components, hooks, context, RSC patterns
- **Express / Node.js** — middleware chain, router mounting, error handlers
- **ASP.NET Core** — DI container, MediatR/CQRS, EF Core, middleware pipeline
- **Spring Boot** — `@Bean` scanning, JPA repositories, `@Profile` configs, SecurityFilterChain
- **Django / FastAPI** — URL patterns, Pydantic schemas, Celery tasks, custom managers
- **Go** — interface implementations, `cmd/` structure, service mesh patterns
- **Nx / Turborepo** — monorepo workspace-aware analysis

**Cookbook recipes** (framework-specific "How do I...?" tasks):
- Angular (8 recipes) · React (6) · Express (5) · ASP.NET Core (8) · Spring Boot (7) · Django/FastAPI (7) · Go (6)

---

## Cost model

For a typical enterprise codebase (1,000 source files):

| Phase | Model | Cost |
|---|---|---|
| Phase 1 scripts | None | $0.00 |
| Tier 0 bootstrapper | Haiku | ~$0.001 |
| Tier 1 file reading (parallel) | Haiku | ~$0.30 |
| Tier 2 synthesis | Sonnet | ~$0.12 |
| Phase 3 generation | None | $0.00 |
| Code Map (graph-data.json) | **None** | **$0.00** |
| **Total** | | **~$0.42** |

Compare: all-Sonnet equivalent would cost $2.50–$7.50 for the same repo.

---

## Scope calibration

The skill automatically adjusts depth based on repository size:

| Source files | Strategy |
|---|---|
| < 50 | Full analysis of all files |
| 50–500 | Top 20 modules by complexity |
| 500–2,000 | Top 15 modules, skip test/config |
| 2,000+ | Top 10 modules, aggregate patterns |

> **Note**: Use `source_files` (not `total_files`) for calibration on compiled-language repos. `bin/` and `obj/` folders are excluded by default, but C# or Java repos can still have 10x more total files than actual source files.

---

## Build artifact exclusion

For .NET, Java, Go, and C++ repos, build output directories are excluded by default:

```
Excluded by default: node_modules  .git  vendor  dist  build  __pycache__
                     .next  target  bin  obj  out  artifacts  .gradle  packages
```

For additional exclusions:
```bash
python scan_repo.py <REPO> --exclude "Generated,Migrations,wwwroot"
```

---

## Interactive Code Map

The Code Map section is powered by **Cytoscape.js** and built entirely from `build_graph.py` — zero LLM tokens:

- **Physics layout** (cose): organic clustering with spring forces, 1000 iterations
- **Node sizing**: proportional to `lines of code`
- **Node coloring**: by role (service · route · model · utility · config · middleware · test · migration)
- **Hover**: fades unconnected nodes to 8%, highlights neighbours in amber, shows tooltip with file summary
- **Click file node**: scrolls to its detailed explanation in the Modules section
- **Click folder node**: expands into its child files with animated re-layout
- **Search**: debounced live search across all node labels and paths
- **Filter chips**: toggle visibility by role type
- **Fullscreen**: Escape to exit, auto-refit
- **Layout toggle**: cose ↔ breadthfirst

For enterprise repos (1,000+ files), the graph automatically groups low-connectivity files into expandable folder nodes — keeping the initial view manageable (~200 nodes) while allowing full drill-down.

---

## Directory Mind Map

Separate from the Code Map, the Directory Mind Map is a **D3.js v7 radial tree** of the actual filesystem structure:

- Root = project name (centre)
- Branches = real directories (`src/`, `api/`, `tests/`...)
- Leaves = actual files, colored by extension (TypeScript=blue, Python=green, C#=purple, Go=cyan, Rust=orange...)
- Click any folder to expand/collapse its contents
- Directories show with trailing `/` to distinguish from files
- Zoom + pan, Expand All / Collapse buttons

---

## File structure

```
~/.claude/skills/tldr/
├── SKILL.md                    ← skill entrypoint (Claude reads this)
├── agents/
│   ├── smoke-test.md           ← compatibility check
│   ├── file-reader.md          ← Haiku file reading agent (Tier 1)
│   ├── file-reader-thinking.md ← Haiku with extended thinking (Tier 1.5)
│   ├── section-preloader.md    ← pre-reads source files before section generation
│   └── workflow-verifier.md    ← verifies workflow steps exist in source
├── references/
│   ├── ANALYSIS_GUIDE.md       ← Phase 1 methodology, model tiers, empty scan recovery
│   ├── SECTION_PROMPTS.md      ← per-section schemas, token budgets, writing rules
│   ├── TECH_STACK_PROFILES.md  ← framework-specific file priorities and patterns
│   ├── WEBSITE_SPEC.md         ← HTML/CSS layout specification
│   └── WRITING_GUIDE.md        ← tone, style, and quality standards
├── scripts/
│   ├── scan_repo.py            ← repo walker, file stats, README, git info
│   ├── detect_stack.py         ← language/framework/monorepo detection
│   ├── find_entry_points.py    ← entry point discovery
│   ├── map_dependencies.py     ← import graph, critical modules, clusters
│   ├── build_graph.py          ← full dependency graph for Code Map (no LLM)
│   ├── merge_analysis.py       ← merges all scripts into repo-analysis.json
│   ├── extract_section.py      ← slices repo-analysis.json per section
│   ├── validate_content.py     ← validates site-content/*.json before generation
│   ├── generate_site.py        ← assembles final HTML (zero LLM)
│   └── calibrate.py            ← token budget calibration helper
└── templates/
    ├── index.html              ← three-column layout, search modal, scrollspy
    └── styles.css              ← OKLCH design system, Geist fonts, dark/light theme
```

---

## Design system

The generated website uses a consistent visual system:

- **Fonts**: Geist Sans (UI) + Geist Mono (code) — Vercel's purpose-built developer tool fonts
- **Colors**: OKLCH semantic tokens (perceptually uniform, accessible contrast)
- **Layout**: 240px sidebar + 680px content + 220px right TOC
- **Code blocks**: always dark (no theme inversion)
- **Grid**: 8px base unit, 150ms transitions
- **Dark mode**: full support via `data-theme` attribute toggle

---

## Requirements

- **Claude Code** (any version)
- **Python 3.8+** (standard library only — no pip installs required)
- **Node.js 14+** (only for `npx tldr-skill` install; not needed at runtime)
- **Git** (optional — used for commit history and branch info)

The generated `index.html` requires no server — open it directly in any browser.

---

## Troubleshooting

### "critical_modules is empty after scan"
Build artifacts are likely inflating the file count. Check: `source_files` vs `total_files` in `rt_scan.json`. Use `--exclude` to filter custom directories.

### "readme_excerpt is too short or says TODO"
The skill falls back to `git log --oneline -10` and top-level directory names. The overview will note this.

### UnicodeDecodeError on Windows
All scripts use `encoding='utf-8', errors='replace'` — this should not occur. If it does, check that your terminal is UTF-8 (`chcp 65001`).

### Code Map shows fewer than 20 nodes
The repo may have very few inter-file connections. Try `--min-connections 1` or `--include-tests` when running `build_graph.py` manually.

### D3 Mind Map shows fallback text list
D3.js CDN failed to load. Check network connectivity. The fallback shows the top-level directory names as a text list.

---

## Contributing

Pull requests and issues welcome. After cloning and making changes, sync to the installed skill:

```bash
cp -r scripts ~/.claude/skills/tldr/
cp -r templates ~/.claude/skills/tldr/
cp -r references ~/.claude/skills/tldr/
cp SKILL.md ~/.claude/skills/tldr/
```

---

## License

Apache 2.0 — see [LICENSE.txt](LICENSE.txt)
