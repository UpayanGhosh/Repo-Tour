---
status: fixing
trigger: "Code Map section uses Cytoscape.js which produces a clinical, ugly graph. Replace with D3 forceSimulation + SVG glow filters to look like Obsidian's Graph View."
created: 2026-03-27T00:00:00Z
updated: 2026-03-27T00:00:00Z
---

## Current Focus

hypothesis: Cytoscape.js is used in gen_code_map() in generate_site.py (lines 675-1061). Root cause confirmed by user.
test: Replace entire Cytoscape implementation with D3 forceSimulation + SVG feGaussianBlur glow
expecting: Obsidian-style dark canvas graph with glowing nodes, organic physics, hover interactions
next_action: Implement D3 replacement in generate_site.py, remove Cytoscape CDN from templates/index.html

## Symptoms

expected: Obsidian-style force-directed graph — dark canvas, glowing nodes, organic clustering, bloom effect via SVG feGaussianBlur filter, D3 forceSimulation physics
actual: Cytoscape.js with COSE layout. Diamond shapes for folders. Gray OKLCH color palette. No glow/bloom. Clinical appearance.
errors: None — it renders, but looks wrong.
reproduction: Run the skill on any repo. Open the Code Map section. See Cytoscape.js graph with COSE layout.
started: Always been this way — Cytoscape was the initial implementation.

## Eliminated

- hypothesis: Maybe D3 is not already loaded
  evidence: D3 CDN is present in templates/index.html line 150 for the mind map section — no new dependency needed
  timestamp: 2026-03-27T00:00:00Z

## Evidence

- timestamp: 2026-03-27T00:00:00Z
  checked: generate_site.py lines 675-1061
  found: gen_code_map() uses cytoscape() function, COSE layout, diamond shapes for folders, no SVG glow filters
  implication: Full replacement required — no Cytoscape code to reuse

- timestamp: 2026-03-27T00:00:00Z
  checked: templates/index.html lines 153-155
  found: Cytoscape CDN tag present: `https://cdn.jsdelivr.net/npm/cytoscape@3.30.4/dist/cytoscape.min.js`
  implication: Must remove this CDN tag after replacing gen_code_map()

- timestamp: 2026-03-27T00:00:00Z
  checked: templates/index.html lines 149-151
  found: D3 CDN already loaded for mind map: `https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js`
  implication: Zero new CDN dependencies needed for D3 force graph

## Resolution

root_cause: gen_code_map() in generate_site.py uses Cytoscape.js (clinical biology-graph tool) instead of D3 forceSimulation (flexible, allows Obsidian-style aesthetics with SVG glow filters)
fix: Replace all Cytoscape code (lines 675-1061) with D3 forceSimulation implementation + remove Cytoscape CDN from templates/index.html
verification: pending
files_changed:
  - repo-tour/scripts/generate_site.py (gen_code_map function, lines 675-1061)
  - repo-tour/templates/index.html (remove Cytoscape CDN lines 153-155)
