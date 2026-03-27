# Project State

**Project:** repo-tour (tldr-skill)
**Last activity:** 2026-03-28 - Completed quick task 2: implement this plan (Verified)

## Current Status

Active development on v1.x feature additions.

Latest commit: `2aac122` — feat(quick-1-code-map-01): update index.html, SKILL.md, ANALYSIS_GUIDE.md for Code Map

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 1 | Add Interactive Code Map (Cytoscape.js) to repo-tour skill — zero-LLM graph pipeline | 2026-03-27 | 43911f0 | | [1-add-interactive-code-map-cytoscape-js-to](.planning/quick/1-add-interactive-code-map-cytoscape-js-to/) |
| 2 | Optimise scan_repo hot path — git ls-files enumeration, stat bucketing, parallel LOC sampling | 2026-03-28 | 1e1c46b | Verified | [2-implement-this-plan](.planning/quick/2-implement-this-plan/) |

## Key Decisions

- graph-data.json never enters LLM context (script-to-script pipeline only)
- Relative-only import resolution in build_graph.py (./  and ../ only)
- Cytoscape CDN with onerror fallback to static table
- git ls-files primary enumeration with os.walk fallback for non-git dirs
- stat-only byte-threshold bucketing for non-source files (no file opens)
- ThreadPoolExecutor(max_workers=8) used for all source file LOC reads in _sample_loc

## Blockers/Concerns

None.
