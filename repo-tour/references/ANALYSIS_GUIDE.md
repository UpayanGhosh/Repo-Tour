# ANALYSIS_GUIDE — Phase 1 Methodology

## Pipeline: Running the Scripts

Run all scripts from the `scripts/` directory (inside the skill folder). Use `{REPO}/.repotour/` for all intermediate files — avoids the Windows /tmp path split where bash `/tmp` and Python `/tmp` resolve to different directories.

```bash
REPO=/path/to/target-repo
WORK=$REPO/.repotour
mkdir -p $WORK

python scan_repo.py $REPO > $WORK/rt_scan.json
python detect_stack.py $REPO > $WORK/rt_stack.json
python find_entry_points.py $REPO $WORK/rt_stack.json > $WORK/rt_entries.json
python map_dependencies.py $REPO \
  --language $(python -c "import json; print(json.load(open('$WORK/rt_stack.json'))['stack']['primary_language'])") \
  --max-modules 15 \
  --output-feature-index $WORK/feature-index.json > $WORK/rt_deps.json

python merge_analysis.py \
  --scan $WORK/rt_scan.json \
  --stack $WORK/rt_stack.json \
  --entries $WORK/rt_entries.json \
  --deps $WORK/rt_deps.json \
  --budget 3500 \
  --output $WORK/repo-analysis.json
```

Check `_meta.within_budget` in `$WORK/repo-analysis.json`. If `false`, reduce `--max-modules`.

**Scope calibration**: Use `meta.source_files` (source-language files only, after exclusions) — NOT `meta.total_files`. On .NET or Java repos with `bin/` or `target/` present, `total_files` can be 10x the actual source file count.

## Empty Scan Recovery

If `critical_modules: []` or `clusters: []` after the pipeline:

1. **Likely cause**: Build artifacts still present (check: is `meta.source_files` << `meta.total_files`?).
   Add `--exclude` if needed: `python scan_repo.py $REPO --exclude "Generated,Migrations"`

2. **Fallback module seeds**: Find project manifests and use them as module seeds:
   - .NET: `*.csproj`, `*.sln`, `Program.cs`, `Startup.cs`
   - Java/Spring: `pom.xml`, `build.gradle`, `*Application.java`
   - Angular: `*.module.ts`, `app.component.ts`
   - Go: `go.mod`, `main.go`, `cmd/*/main.go`
   - Python: `pyproject.toml`, `setup.py`, `wsgi.py`, `asgi.py`

3. **Fallback clusters**: Use top-level directories as cluster names instead of import graph.

If `readme_excerpt` contains "TODO" or is under 50 characters:
- Run `git log --oneline -10` and use commit messages as the project narrative
- Derive purpose from directory structure (e.g. `Controllers/`, `Services/`, `Models/` → MVC web API)

## Token Budget Enforcement

**Hard limit**: `repo-analysis.json` must be under 3500 tokens (~14000 chars).

`merge_analysis.py` enforces this automatically by trimming lowest-complexity modules. Verify:
```bash
python -c "import json; d=json.load(open('repo-analysis.json')); print(d['_meta'])"
```

## Tier 0: Bootstrapper (One Call Before Swarm)

Before dispatching file-reader agents, dispatch ONE Haiku call with:
- Input: directory tree listing + config files only (package.json, pyproject.toml, go.mod, pom.xml, Cargo.toml, go.work, nx.json, turbo.json)
- Output: module partition map — which files belong to which domain cluster (~500-1000 tokens)
- Purpose: enables EXPLICIT file assignment to each Haiku worker (eliminates cold-start)
- Cost: ~50-100 input tokens, ~500 output tokens — negligible

The partition map determines the file lists passed to each Tier 1 agent.
Never let Tier 1 agents discover their own file scope.

## Haiku File-Reader Dispatch Strategy

After scripts complete, dispatch `agents/file-reader.md` to summarize critical modules.

Dispatch 10-15 file-reader agents simultaneously, each with an EXPLICIT non-overlapping file list from the Tier 0 partition map. Never let agents discover their own scope.

**Batching rules**:
- Files < 500 lines (Tier 1): batch up to 10 per agent call
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

## Confidence-Based Model Escalation

Tier 1 (Haiku): All filtered files. If output contains needs_review: true → escalate.
Tier 1.5 (Haiku + thinking, budget_tokens: 2000): Files flagged by Tier 1, single-file scope only.
Tier 2 (Sonnet): Multi-file scope, security-critical, entry points, files still flagged after 1.5.
Tier 3 (Sonnet + high effort): Final synthesis only. Never sees raw source code.

Haiku timeout: 90 seconds per agent. Error sentinel: {"path": "...", "status": "error|timeout", "needs_review": true}
Fallback threshold: If >40% of dispatched agents return error/timeout, abort and fall back to sequential batch-5.

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

Max 3 workflows for repos under 500 files; max 8 for 500-2000 files; max 12 for 2000+ files. Max 8 steps each. Keep action descriptions under 50 chars.

Workflow count by repo size:
| Repo size    | Max workflows | Selection strategy                                    |
|--------------|---------------|-------------------------------------------------------|
| < 500 files  | 3             | The 3 most important user-facing flows                |
| 500-2000     | 8             | 1 per major cluster (capped at 8)                     |
| 2000+ files  | 12            | Framework-aware: auth + main data flow + create/update + feature-specific flows |

Framework-aware workflow priorities:
- Angular: route activation → component → service → HTTP → response
- Spring Boot: HTTP → Controller → Service → Repository → DB
- .NET (MediatR): HTTP → Controller → IMediator.Send() → IRequestHandler → Repository → DB
- Django: URL conf → view → serializer → queryset → DB + signal side effects
- Go: HTTP → handler → middleware chain → service → repository → DB

## Glossary Candidates

After reading module summaries, add domain-specific terms to `glossary_candidates`:
```json
"glossary_candidates": ["JWT", "middleware", "ORM", "queue worker", "hydration"]
```

Only add terms a new hire would need defined. Max 15 terms.

## Edge Cases

**Monorepo**: If `detect_stack.py` returns `stack.monorepo.type != "none"` (Nx, Turborepo, pnpm-workspaces, etc.), do NOT ask the user. Instead:
1. Read `stack.monorepo.packages` — enumerate all workspace packages with their paths and types
2. Identify the primary consumer app (type: "app") vs shared libraries (type: "lib")
3. Document ALL packages in the feature index and architecture, not just one
4. For the Modules section, focus on the primary app + its most-used shared libs
5. The Codebase Map section will show the full workspace package tree automatically

If `stack.monorepo.type == "none"` but `top_dirs` contains `packages/`, `apps/`, `libs/`, or `services/`, treat it as an undeclared workspace and document all top-level subdirectories as packages.

**No clear entry point**: Check `package.json scripts`, `Makefile` targets, `Procfile`. If still unclear, note it in the overview section: "Entry points unclear — this may be a library or utility package."

**Polyglot repos**: Analyze the primary language first (highest file count by extension). Note secondary languages in `stack.additional_languages`.

**Generated code**: Files with "DO NOT EDIT" / "auto-generated" in first 10 lines — these are captured in `generated-surfaces.json` (sidecar file) with their API surface extracted from type signatures and exports. Do NOT skip them. Do NOT document their internals. DO document what they expose:
- NSwag/OpenAPI clients: list the available API operations (method names)
- Protobuf stubs: list the service methods and message types
- GraphQL codegen: list the generated query hooks/operations
- ORM migrations: note the migration history (timestamps + brief descriptions)
Include in the architecture as "Generated API Layer" with a reference to the source spec.

## Sidecar Files

Sidecar files (written alongside repo-analysis.json, NOT inside it):

### feature-index.json
Schema: `[{"path": "string", "name": "string", "role": "string", "loc": int, "cluster": "string"}]`
Generated by: `map_dependencies.py --output-feature-index feature-index.json`
Up to 500 entries (uncapped module list — covers entire codebase).
Used by: Phase 2 Cookbook section (grounding check), Codebase Map website section.

### generated-surfaces.json
Schema:
```json
[{
  "path": "string",
  "generator_hint": "NSwag/OpenAPI|protobuf|GraphQL-codegen|openapi-generator|orm-migration|other",
  "source_spec": "string|null",  // path to .proto, openapi.yaml, schema.graphql, etc.
  "endpoints": ["string"],       // operation/method names extracted from exports
  "loc": 0,
  "note": "string"               // e.g. "Generated from UserService OpenAPI spec. Edit source spec, not this file."
}]
```
Generated by: `scan_repo.py --output-generated-surfaces generated-surfaces.json`
Detection signals (in order of confidence):
1. NSwag: `nswag.json` in repo root or `src/`, TypeScript files with `NSwagStudio` comment
2. Protobuf: `*.pb.ts`, `*.pb.go`, `*_pb2.py`, `*_grpc.py`, `*_pb.d.ts`
3. GraphQL codegen: `__generated__/` directory, `// @generated` header comment
4. OpenAPI generator: files with `openapi-generator` in first 5 lines
5. ORM migrations: files in `migrations/` with timestamp prefix (e.g. `0001_`, `20240101_`)
6. Generic: "DO NOT EDIT" or "auto-generated" in first 10 lines
Used by: Phase 2 Generated APIs section, Architecture section.

Only summary stats go into repo-analysis.json:
```json
"feature_index_summary": {"total_modules": 847, "clusters": 12},
"generated_surfaces_count": 3
```

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
