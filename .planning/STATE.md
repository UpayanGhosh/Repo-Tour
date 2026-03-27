# Project State

**Project:** repo-tour (tldr-skill)
**Last activity:** 2026-03-27 - Added interactive Code Map (Cytoscape.js dependency graph)

## Current Status

Active development on v1.x feature additions.

Latest commit: `2aac122` — feat(quick-1-code-map-01): update index.html, SKILL.md, ANALYSIS_GUIDE.md for Code Map

## Completed Quick Tasks

- quick-1: Interactive Code Map (Cytoscape.js) — build_graph.py + gen_code_map() + template updates

## Key Decisions

- graph-data.json never enters LLM context (script-to-script pipeline only)
- Relative-only import resolution in build_graph.py (./  and ../ only)
- Cytoscape CDN with onerror fallback to static table

## Blockers/Concerns

None.
