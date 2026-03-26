# ANALYSIS_GUIDE — Phase 1 Methodology

## Pipeline: Running the Scripts

Run all scripts from the `repo-tour/scripts/` directory. Use a temp directory for intermediates:

```bash
REPO=/path/to/target-repo
TMP=/tmp/rt_$$

python scan_repo.py $REPO > $TMP_scan.json
python detect_stack.py $REPO > $TMP_stack.json
python find_entry_points.py $REPO $TMP_stack.json > $TMP_entries.json
python map_dependencies.py $REPO \
  --language $(python -c "import json; print(json.load(open('$TMP_stack.json'))['stack']['primary_language'])") \
  --max-modules 15 > $TMP_deps.json

python merge_analysis.py \
  --scan $TMP_scan.json \
  --stack $TMP_stack.json \
  --entries $TMP_entries.json \
  --deps $TMP_deps.json \
  --budget 3500 \
  --output repo-analysis.json
```

Check `_meta.within_budget` in `repo-analysis.json`. If `false`, reduce `--max-modules`.

## Token Budget Enforcement

**Hard limit**: `repo-analysis.json` must be under 3500 tokens (~14000 chars).

`merge_analysis.py` enforces this automatically by trimming lowest-complexity modules. Verify:
```bash
python -c "import json; d=json.load(open('repo-analysis.json')); print(d['_meta'])"
```

## Haiku File-Reader Dispatch Strategy

After scripts complete, dispatch `agents/file-reader.md` to summarize critical modules.

**Batching rules**:
- Files < 500 lines (Tier 1): batch up to 5 per agent call
- Files 500-3000 lines (Tier 2): batch up to 3-4 per agent call
- Files 3000-10000 lines (Tier 3): solo batch (1 file per call)
- Files > 10000 lines (Tier 4): DO NOT dispatch — metadata already captured by scripts

Pass file paths from `critical_modules[].path` in repo-analysis.json. Example prompt:

```
Analyze these files: src/services/auth.ts, src/lib/jwt.ts, src/middleware/auth.ts
[paste agents/file-reader.md instructions]
```

**Targeted deep-read pattern**: If a critical module's summary is insufficient (too vague, missing behavior details), send a targeted follow-up:
```
In src/services/auth.ts, find the `verifyToken` and `createSession` functions.
Answer: (1) What does verifyToken do on failure? (2) What does createSession store?
Keep response under 200 tokens.
```

## Workflow Identification

Trace 2-3 key workflows from entry points through import chains. Look for:

**Common patterns**:
- HTTP: `request → router → middleware → controller → service → DB → response`
- CLI: `parse args → command handler → business logic → output`
- Background: `trigger (cron/event) → queue → worker → DB/external API`
- Event: `event emitter → listener → handler → side effect`

**How to identify**:
1. Start from entry_points in repo-analysis.json
2. Follow import chains in critical_modules
3. Look for patterns: auth checks, DB queries, external API calls, cache reads
4. Use `agents/workflow-verifier.md` to confirm function existence if uncertain

**Output format** — add to `repo-analysis.json` after Haiku analysis:
```json
"workflows": [
  {
    "name": "User Login",
    "trigger": "POST /api/auth/login",
    "steps": [
      {"file": "src/routes/auth.ts", "function": "handleLogin", "action": "Validates request body, extracts email/password"},
      {"file": "src/services/auth.ts", "function": "login", "action": "Checks credentials against DB, issues JWT"},
      {"file": "src/lib/jwt.ts", "function": "signToken", "action": "Creates signed JWT with 7-day expiry"}
    ]
  }
]
```

Max 3 workflows. Max 8 steps per workflow. Keep action descriptions under 50 chars.

## Glossary Candidates

After reading module summaries, add domain-specific terms to `glossary_candidates`:
```json
"glossary_candidates": ["JWT", "middleware", "ORM", "queue worker", "hydration"]
```

Only add terms a new hire would need defined. Max 15 terms.

## Edge Cases

**Monorepo**: If `top_dirs` contains `packages/`, `apps/`, `libs/`, or `services/`, ask the user:
> "This looks like a monorepo with [N] packages. Which package should I focus on, or should I document the whole repo?"

**No clear entry point**: Check `package.json scripts`, `Makefile` targets, `Procfile`. If still unclear, note it in the overview section: "Entry points unclear — this may be a library or utility package."

**Polyglot repos**: Analyze the primary language first (highest file count by extension). Note secondary languages in `stack.additional_languages`.

**Generated code**: Files with "DO NOT EDIT" / "auto-generated" in first 10 lines — include in architecture as "Generated code (do not document internals)" but skip for module analysis.

## Full repo-analysis.json Schema

```json
{
  "meta": {"name": "string", "total_files": int, "total_loc": int},
  "stack": {
    "primary_language": "string",
    "framework": "string|null",
    "runtime": "string|null",
    "database": "string|null",
    "test_framework": "string|null",
    "build_tool": "string|null",
    "ci": "string|null",
    "package_manager": "string|null",
    "dep_count": {"prod": int, "dev": int}
  },
  "entry_points": [
    {"file": "string", "type": "server_start|app_root|route_root|cli_entry|background|test_runner", "hint": "string"}
  ],
  "critical_modules": [
    {
      "path": "string",
      "imports": ["string"],
      "imported_by": ["string"],
      "role": "service|route|controller|model|middleware|utility|...",
      "loc": int,
      "complexity": float,
      "read_tier": "direct|strategic|skeleton|metadata"
    }
  ],
  "clusters": [{"name": "string", "files": ["string"]}],
  "external_deps_top10": [{"name": "string", "purpose": "string"}],
  "top_dirs": ["string"],
  "readme_excerpt": "string (max 200 chars)",
  "git_info": {"recent_commits": ["string"], "branch_count": int},
  "files_by_size": {"small": int, "medium": int, "large": int, "xlarge": int, "mega": int},
  "mega_files": [{"path": "string", "lines": int, "likely_generated": bool}],
  "skip_candidates": ["string"],
  "workflows": [
    {
      "name": "string",
      "trigger": "string",
      "steps": [{"file": "string", "function": "string", "action": "string"}]
    }
  ],
  "glossary_candidates": ["string"],
  "circular_warnings": ["string"],
  "_meta": {"token_estimate": int, "within_budget": bool, "budget": int}
}
```
