# SECTION_PROMPTS — Per-Section Generation Instructions

**Read ONE section at a time.** Jump directly to the section you're generating.

---

## Section: overview

**What to Read from Analysis**:
```bash
python extract_section.py overview repo-analysis.json
```

**Pre-Read**: None. Use Phase 1 data directly.

**Your Task**: Generate `site-content/overview.json`:
```json
{
  "summary": "2-3 sentences a non-developer could understand. What does this project DO for its users? Max 150 words.",
  "audience": "Who uses this software and why. 1 sentence.",
  "approach": "Core technical approach in plain language — no jargon. 1-2 sentences."
}
```

**Writing Rules**:
- Lead with what the software DOES for users, not how it's built
- Use a concrete analogy in the summary: "Think of it like a..."
- Mention the tech stack only in 'approach', and only if relevant to understanding
- Never start with "This is a..."

**Token Budget**: ~800 tokens output

**Example**:
```json
{
  "summary": "Listify is a real-time collaborative list manager — think Google Docs, but just for checklists. Teams use it to track project tasks, shared grocery lists, and anything else that needs to stay in sync across multiple people at once.",
  "audience": "Small teams and households who need a lightweight, no-friction way to share and update lists together.",
  "approach": "A Node.js server keeps lists in sync using WebSockets, persisting changes to PostgreSQL so nothing is lost if you close the tab."
}
```

---

## Section: architecture

**What to Read from Analysis**:
```bash
python extract_section.py architecture repo-analysis.json
```

**Pre-Read**: None. Use clusters and entry_points from Phase 1.

**Your Task**: Generate `site-content/architecture.json`:
```json
{
  "analogy": "Real-world analogy for how the system is organized. 2-3 sentences. Concrete — use a restaurant, factory, airport, post office, etc.",
  "layers": [
    {"name": "Layer Name", "responsibility": "What this layer does in one sentence", "key_files": ["path/to/file.ts"]}
  ],
  "mermaid": "graph TD\n  A[Client] --> B[API Gateway]\n  B --> C[Auth Middleware]\n  ..."
}
```

**Writing Rules**:
- Max 4-5 layers. Group clusters into meaningful architectural layers
- The analogy must map directly to the layers: "Just as a restaurant has a dining room, kitchen, and pantry, this app has..."
- Mermaid diagram: use `graph LR` (left-to-right) to show the request flow through layers. Include ALL major components — min 8, max 20 nodes. Node labels are plain English, not file paths. Show data stores with `[(Name)]` syntax.
- Layer names: plain English (e.g., "API Layer", "Business Logic", "Data Layer") — not folder names

**Token Budget**: ~1500 tokens output

**Example**:
```json
{
  "analogy": "Think of this app like a post office. The routes/ folder is the front desk — it receives and routes incoming requests. The services/ folder is the sorting room — it processes each request according to business rules. The models/ folder is the filing cabinet — it defines how information is stored and retrieved.",
  "layers": [
    {"name": "HTTP Layer", "responsibility": "Receives requests, validates input, returns responses", "key_files": ["src/routes/index.ts", "src/middleware/auth.ts"]},
    {"name": "Business Logic", "responsibility": "Core application rules and workflows", "key_files": ["src/services/auth.ts", "src/services/users.ts"]},
    {"name": "Data Layer", "responsibility": "Database access and data transformation", "key_files": ["src/models/user.ts", "src/lib/db.ts"]}
  ],
  "mermaid": "graph TD\n  Client --> Routes\n  Routes --> Middleware\n  Middleware --> Services\n  Services --> Models\n  Models --> Database[(PostgreSQL)]"
}
```

---

## Section: tech_stack

**What to Read from Analysis**:
```bash
python extract_section.py tech_stack repo-analysis.json
```

**Pre-Read**: None. Use Phase 1 stack data directly.

**Your Task**: Generate `site-content/tech_stack.json` as an array:
```json
[
  {
    "name": "Technology Name",
    "role": "Short role label (e.g., Web Framework, ORM, Test Runner)",
    "why": "What this technology does in this codebase specifically, and why it was likely chosen. 2-3 sentences. Be concrete — reference what it handles."
  }
]
```

**Writing Rules**:
- Max 10 technologies. Prioritize the most visible ones to a new developer
- "why" is not marketing copy — explain what this specific project uses it FOR
- For databases: mention the schema approach if detectable (relational, document, etc.)
- Skip trivial dev dependencies (formatters, linters) unless they're noteworthy

**Token Budget**: ~1000 tokens output

**Example**:
```json
[
  {"name": "Express", "role": "Web Framework", "why": "Handles all HTTP routing and request/response lifecycle. Chosen for its minimalist API and massive ecosystem — every route in the app is mounted through Express's router."},
  {"name": "Prisma", "role": "ORM", "why": "Translates TypeScript code into PostgreSQL queries and manages database migrations. The schema file in prisma/schema.prisma is the single source of truth for all data models."},
  {"name": "Jest", "role": "Test Runner", "why": "Runs the test suite in src/__tests__/. Tests are co-located with source files and run in parallel by default."}
]
```

---

## Section: entry_points

**What to Read from Analysis**:
```bash
python extract_section.py entry_points repo-analysis.json
```

**Pre-Read**: **REQUIRED** — dispatch `agents/section-preloader.md` with each entry point file. Do NOT write this section until the preloader agent returns. If you skip this, set `"unverified": true` in the output JSON.

**Your Task**: Generate `site-content/entry_points.json` as an array:
```json
[
  {
    "file": "path/to/file.ts",
    "trigger": "What causes this entry point to run (e.g., 'npm start', 'POST /api/login', 'cron every 5 min')",
    "narrative": "Walk through what happens when this entry point runs. Mention specific functions, what they set up, and where control flows next. Max 150 words."
  }
]
```

**Writing Rules**:
- Narrative tells a story: "When you run `npm start`, this file runs first. It creates..."
- Reference specific function names from the Haiku briefing
- End with "...and then hands off to [next thing]" to show flow continuation
- If the Haiku briefing was too vague for a large file: note "This is a [N]-line file — this covers its startup sequence only."

**Token Budget**: ~1200 tokens output

**Example**:
```json
[
  {
    "file": "src/index.ts",
    "trigger": "npm start / node dist/index.js",
    "narrative": "When you run `npm start`, this is the first file Node.js executes. It calls `loadConfig()` to read environment variables, then `connectDB()` to establish the PostgreSQL connection pool. Next, it creates the Express app, registers all middleware (logging, CORS, auth), and mounts the route tree from `src/routes/index.ts`. Finally, it calls `app.listen(3000)` and logs 'Server ready'. From here, every incoming request flows through the route tree."
  }
]
```

---

## Section: modules (batched)

**What to Read from Analysis**:
```bash
python extract_section.py modules repo-analysis.json --batch 0 --batch-size 8
# Increment --batch for each subsequent batch
```

**Pre-Read**: **REQUIRED** — dispatch `agents/section-preloader.md` with the file paths in this batch. Do NOT write this section until the preloader agent returns. If you skip this, set `"unverified": true` on each module object in the output.

**Your Task**: Generate `site-content/modules_batch_N.json` as an array (one object per module):
```json
[
  {
    "path": "src/services/auth.ts",
    "name": "Auth Service",
    "simple_explanation": "Max 80 words. What does this file DO? Use plain language — what problem does it solve?",
    "detailed_explanation": "Max 200 words. How does it work internally? What are its key functions? Any important patterns?",
    "depends_on": ["src/lib/db.ts", "src/lib/jwt.ts"],
    "depended_by": ["src/routes/auth.ts"],
    "gotchas": "Max 40 words. Optional — only include if there's genuinely non-obvious behavior.",
    "large_file": false
  }
]
```

**Writing Rules**:
- `name`: Human-readable (e.g., "Auth Service", "User Router", "Database Client") — not the filename
- `simple_explanation`: Start with "This file handles..." or "This is responsible for..." — then explain in terms of user-visible behavior
- `detailed_explanation`: Reference actual function names from the Haiku briefing. Mention patterns: "Uses the repository pattern", "Implements a singleton", etc.
- If `large_file: true` (Tier 3): add to simple_explanation: "This is a large module (~N lines) — this covers its public interface and role, not internal implementation details."
- If `mega_file: true` (Tier 4): simple_explanation only. Flag clearly: "Generated or monolithic file (~N lines). Not analyzed in detail."
- Per-module caps: simple max 80 words, detailed max 200 words, gotchas max 40 words

**Token Budget**: ~3500 tokens per batch of 8

**Quality self-check**: Does every `simple_explanation` reference a specific behavior (not just "handles X")? If a briefing was too vague, dispatch a targeted Haiku agent before writing.

**Example**:
```json
[
  {
    "path": "src/services/auth.ts",
    "name": "Auth Service",
    "simple_explanation": "This handles everything related to proving who a user is. When someone logs in, this file checks their email and password against the database. If correct, it creates a session token (JWT) that the client uses for all future requests. It also handles token refresh and logout.",
    "detailed_explanation": "The core functions are `login(email, password)`, `refreshToken(token)`, and `logout(userId)`. `login` uses bcrypt to compare the submitted password with the stored hash — it never stores plain-text passwords. On success, it calls `jwt.sign()` with a 7-day expiry and stores the refresh token in Redis for fast invalidation. `refreshToken` validates the existing token and issues a new one if it's within the renewal window. The service throws typed errors (`AuthError`, `TokenExpiredError`) that the route layer catches and converts to HTTP status codes.",
    "depends_on": ["src/lib/db.ts", "src/lib/jwt.ts", "src/lib/redis.ts"],
    "depended_by": ["src/routes/auth.ts", "src/middleware/auth.ts"],
    "gotchas": "Refresh tokens are stored in Redis with a 30-day TTL. If Redis is down, refresh will fail even for valid tokens.",
    "large_file": false
  }
]
```

---

## Section: workflows

**What to Read from Analysis**:
```bash
python extract_section.py workflows repo-analysis.json
```

**Pre-Read**: **REQUIRED** — dispatch `agents/workflow-verifier.md` for each workflow's steps to confirm they exist in source. Do NOT finalize workflow steps until verifier confirms the functions exist. If unverifiable, mark the step: `"(unverified)"` in the narrative.

**Your Task**: Generate `site-content/workflows.json`:
```json
{
  "workflows": [
    {
      "name": "Workflow Name",
      "trigger": "What starts this workflow (user action, event, cron, etc.)",
      "steps_summary": ["Entry Point", "Controller", "Service", "Repository", "Database"],
      "steps": [
        {
          "file": "src/routes/auth.ts",
          "function": "handleLogin",
          "narrative": "What happens in this step. Max 100 words. Write from the perspective of data flowing through."
        }
      ],
      "mermaid": "sequenceDiagram\n  actor User\n  User->>API: POST /login\n  API->>AuthService: login(email, password)\n  ..."
    }
  ]
}
```

**Writing Rules**:
- Max 3 workflows for repos under 500 files; max 8 for 500-2000 files; max 12 for 2000+ files. Max 8 steps each.
- `steps_summary`: Array of 3-6 short layer labels showing the call chain left-to-right. First = entry point, last = datastore or final output. Max 25 chars each. Example: `["POST /login", "AuthController", "AuthService", "UserRepo", "PostgreSQL"]`
- Mermaid: use `sequenceDiagram`. Actors: User/Client, then system components. Max 10 messages.
- If a step couldn't be verified by workflow-verifier: add "(unverified)" to the narrative
- Choose workflows that show the most important user-facing behaviors — prioritize: auth flow, main data fetch, a create/update mutation, and (for Angular) a lazy-loaded route activation

**Token Budget**: ~2500 tokens output

**Example** (single step shown):
```json
{
  "name": "User Authentication",
  "trigger": "User submits login form / POST /api/auth/login",
  "steps": [
    {
      "file": "src/routes/auth.ts",
      "function": "handleLogin",
      "narrative": "The request arrives here first. Express validates that `email` and `password` fields are present (using Zod schema validation). If validation fails, it returns a 400 immediately. Otherwise, it passes the credentials to `AuthService.login()` and awaits the result."
    }
  ],
  "steps_summary": ["POST /api/auth/login", "Router", "AuthService", "Database", "JWT token"],
  "mermaid": "sequenceDiagram\n  actor User\n  User->>Router: POST /api/auth/login\n  Router->>Validator: Zod schema check\n  Validator-->>Router: validated data\n  Router->>AuthService: login(email, password)\n  AuthService->>Database: find user by email\n  Database-->>AuthService: user record\n  AuthService->>AuthService: bcrypt.compare()\n  AuthService-->>Router: JWT token\n  Router-->>User: 200 {token}"
}
```

---

## Section: cross_cutting

**What to Read from Analysis**:
```bash
python extract_section.py cross_cutting repo-analysis.json
```

**Pre-Read**: **REQUIRED** — dispatch agents/section-preloader.md on:
- Auth middleware files (*.middleware.ts, *.guard.ts, *.interceptor.ts, *auth*, *security*)
- Error handling files (global error handlers, *error*, *exception*, *problem-details*)
- Logging setup files (logger init, correlation ID, *logging*, *telemetry*)
- Test config files (jest.config.*, pytest.ini, xunit.runner.xml, vitest.config.*)

**Your Task**: Generate site-content/cross_cutting.json:
```json
{
  "auth_authz": {
    "mechanism": "JWT|OAuth2|session|API key|mTLS|other",
    "pattern": "Where auth happens, what it protects, and how it is enforced. Max 100 words.",
    "guard_files": ["path/to/auth.middleware.ts"],
    "mermaid": "sequenceDiagram showing auth flow — max 8 messages"
  },
  "error_handling": {
    "strategy": "How errors are caught, classified, and propagated through the system. Max 80 words.",
    "key_files": ["path/to/error-handler.ts"],
    "conventions": "Typed errors vs generic? Where do errors surface to the caller?"
  },
  "logging_observability": {
    "library": "winston|serilog|zap|logrus|log4j|structlog|other",
    "structure": "Structured (JSON) vs text? What fields are always present (correlation ID, user ID, service)?",
    "tracing": "OpenTelemetry|Datadog|custom|none"
  },
  "testing_strategy": {
    "unit_framework": "jest|xunit|pytest|go test|junit|other",
    "integration": "How integration tests are structured and what they cover.",
    "e2e": "Playwright|Cypress|Selenium|none",
    "coverage_approach": "What coverage means in this codebase — % target, what is excluded?"
  }
}
```

**Writing Rules**:
- If a cross-cutting concern cannot be determined from the pre-read files, set its value to null
- Do not speculate — only document patterns that are actually present in the read files
- The auth mermaid diagram must show the actual middleware/guard files by name
- For testing_strategy: read one test file to understand patterns before writing

**Token Budget**: ~1500 tokens output

---

## Section: directory_guide

**What to Read from Analysis**:
```bash
python extract_section.py directory_guide repo-analysis.json
```

**Pre-Read**: None. Use top_dirs from Phase 1.

**Your Task**: Generate `site-content/directory_guide.json` as an array:
```json
[
  {
    "path": "src/",
    "purpose": "What lives here and why it's organized this way. 1-2 sentences.",
    "when_to_look_here": "If you're trying to [task], start here. 1 sentence."
  }
]
```

**Writing Rules**:
- Cover every top-level directory (skip .git, node_modules, vendor)
- `when_to_look_here` is the most useful field — make it actionable
- Group very small dirs: "tests/ and __mocks__/: test files and their mocks"
- Max 12 entries

**Token Budget**: ~800 tokens output

---

## Section: glossary_getting_started

**What to Read from Analysis**:
```bash
python extract_section.py glossary repo-analysis.json
python extract_section.py getting_started repo-analysis.json
```

**Pre-Read**: **REQUIRED** — dispatch `agents/section-preloader.md` on CI config, Dockerfile, Makefile, and README for setup commands. Do NOT write getting_started until the preloader confirms the setup commands. If you skip this, set `"unverified": true`.

**Your Task**: Generate `site-content/glossary_getting_started.json`:
```json
{
  "glossary": [
    {
      "term": "Term",
      "definition": "Plain-language definition in context of THIS codebase. 1-3 sentences. How is this term used here specifically?"
    }
  ],
  "getting_started": {
    "clone": "git clone <url>",
    "install": "npm install (or equivalent)",
    "env_vars": [
      {"name": "DATABASE_URL", "description": "PostgreSQL connection string. Format: postgresql://user:pass@localhost:5432/dbname"}
    ],
    "run": "npm run dev (or equivalent)",
    "first_tasks": [
      "Try [specific action] to verify the setup works",
      "Check [specific file] to understand [concept]"
    ],
    "learning_path": {
      "day_1": [
        "Read [specific file] — this is the root of the app",
        "Trace how [key feature] works by starting at [entry file]",
        "Understand the folder structure: [src/features/] contains one folder per major feature"
      ],
      "week_1": [
        "Add a small change to [specific area] to get comfortable with the pattern",
        "Trace a full [feature name] request from [entry point] to [data layer]",
        "Read [key service or module] — it's used everywhere"
      ]
    }
  }
}
```

**Writing Rules**:
- Glossary: 5-15 terms from `glossary_candidates`. Define in context — not dictionary definitions
- `getting_started.env_vars`: List every env var from `.env.example` with what it's for
- `getting_started.first_tasks`: Concrete, specific tasks — not "read the code"
- `getting_started.learning_path`: A structured onboarding sequence. Day 1 = orientation (understand the shape of the app). Week 1 = first contributions (make a small change, trace a real flow). Name specific files, folders, and features — never generic advice like "explore the codebase"
- If no `.env.example` exists: note "Check README for required environment variables"

**Token Budget**: ~1500 tokens output

---

## Section: cookbook

**What to Read from Analysis**:
```bash
python extract_section.py cookbook repo-analysis.json
```
This uses `stack.framework`, `entry_points`, `critical_modules`, and `top_dirs` to generate framework-aware recipes.

**Pre-Read**: Yes — dispatch `agents/section-preloader.md` with at minimum 5 file categories:
1. The routing file (where routes/endpoints are registered: app-routing.module.ts, routes/api.php, urls.py, router.go, Program.cs route registration)
2. A sample feature/controller (shows naming and structure conventions for new features)
3. A sample service (shows DI injection patterns and business logic conventions)
4. A sample data access file (repository, model, ORM usage patterns)
5. A middleware or guard file (if present — shows how cross-cutting concerns are applied)
6. The test file for one of the above (shows testing conventions)
7-10 (optional): Any files the Haiku tier flagged as "pattern-defining" for this codebase

**Grounding Check** (required before writing any recipe):
Before writing any recipe step, verify: does the file path you are referencing actually exist in the feature_index? If the sidecar feature-index.json is available, check it. If you cannot confirm a file exists, write the step in generic terms and note "(verify path for this repo)". Never invent file paths.

**Your Task**: Generate `site-content/cookbook.json`:
```json
{
  "framework": "Angular",
  "recipes": [
    {
      "title": "How do I add a new page/route?",
      "steps": [
        "Create the component: `ng generate component features/my-page`",
        "Register the route in `src/app/app-routing.module.ts`",
        "Add navigation link in `src/app/shell/sidebar/sidebar.component.html` if needed"
      ],
      "files_to_touch": ["src/app/app-routing.module.ts", "src/app/features/my-page/"],
      "code_hint": "{ path: 'my-page', loadComponent: () => import('./features/my-page/my-page.component').then(c => c.MyPageComponent) }",
      "files_verified": ["src/app/app-routing.module.ts"]
    }
  ]
}
```

**Writing Rules**:
- Generate 5-8 recipes. Pick the tasks a new dev will hit in their first 2 weeks
- Every recipe must reference ACTUAL file paths from this repo (from the Haiku briefing), not generic placeholders
- Steps should be specific and sequential — assume the dev has the repo running
- `code_hint` is the key pattern snippet they'll copy-paste — keep it under 3 lines, real code not pseudocode
- Framework-specific recipe sets:

**Angular recipes** (use when `stack.framework == "Angular"`):
1. How do I add a new page/route?
2. How do I create a reusable component?
3. How do I call a REST API from a component?
4. How do I add an auth guard to a route?
5. How do I share state between components?
6. How do I add a new HTTP interceptor?
7. How do I add a form with validation?
8. How do I dispatch an NgRx action? *(include only if NgRx detected)*

**React recipes** (use when `stack.framework == "React"` or `"Next.js"`):
1. How do I add a new page/route?
2. How do I fetch data in a component?
3. How do I share state across components?
4. How do I add a protected route?
5. How do I create a reusable hook?
6. How do I handle form submission?

**Express/Node recipes** (use when `stack.framework == "Express"`):
1. How do I add a new API endpoint?
2. How do I add authentication middleware to a route?
3. How do I add a new database model?
4. How do I add input validation?
5. How do I add a background job?

**ASP.NET Core recipes** (use when `stack.framework` contains "ASP.NET" or `stack.primary_language == "C#"`):
1. How do I add a new API endpoint?
2. How do I register a new service in the DI container?
3. How do I add a new Entity Framework entity and migration?
4. How do I add middleware to the pipeline?
5. How do I add a MediatR command/handler?
6. How do I add input validation (FluentValidation)?
7. How do I add a background service (IHostedService)?
8. How do I write an integration test?

**Spring Boot recipes** (use when `stack.framework` contains "Spring"):
1. How do I add a new REST endpoint?
2. How do I add a new Spring Bean/Service?
3. How do I add a JPA entity and repository?
4. How do I add request validation?
5. How do I add a Spring Security rule?
6. How do I write a test with @SpringBootTest?
7. How do I add a scheduled task?

**Django/FastAPI recipes** (use when `stack.framework` contains "Django" or "FastAPI"):
1. How do I add a new API endpoint or view?
2. How do I add a new database model?
3. How do I add a serializer (Django REST) or schema (FastAPI/Pydantic)?
4. How do I add URL routing?
5. How do I add a celery task?
6. How do I write a test?
7. How do I add a migration?

**Go recipes** (use when `stack.primary_language == "Go"`):
1. How do I add a new HTTP handler?
2. How do I add a new service struct and interface?
3. How do I add a database query (raw SQL or ORM)?
4. How do I add middleware to the router?
5. How do I write a unit test?
6. How do I add a background goroutine/worker?

**Generic fallback** (for any other framework):
1. How do I add a new feature?
2. How do I add a new API endpoint or route?
3. How do I run the tests?
4. How do I add configuration?
5. How do I debug a failing request?

**Token Budget**: ~2000 tokens output

**Quality self-check**: Does every step reference a real file path from THIS repo? Does `code_hint` show actual syntax (not `// TODO`)? Could a dev follow these steps without looking anything else up?
