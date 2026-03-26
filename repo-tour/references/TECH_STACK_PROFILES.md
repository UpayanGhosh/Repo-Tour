# TECH_STACK_PROFILES — Framework-Specific Analysis Hints

Use this during Phase 1 to prioritize which files to send to Haiku agents first.

---

## Express (Node.js / TypeScript)

**Where things live**:
- Routes: `src/routes/`, `routes/`, files matching `*router*`, `*routes*`
- Middleware: `src/middleware/`, files matching `*middleware*`, `*guard*`
- Controllers: `src/controllers/`, or inline in route files
- Services: `src/services/`
- Models/Schemas: `src/models/`, Prisma schema at `prisma/schema.prisma`, Mongoose models
- Config: `src/config/`, `config/`, `.env`, `src/lib/config.ts`
- DB connection: files matching `*db*`, `*database*`, `*prisma*`, `*mongoose*`

**Key patterns to look for**:
- `app.use(...)` — middleware mounting order matters
- `router.get/post/put/delete(...)` — route definitions
- `express.Router()` — sub-routers
- `next(err)` — error handling middleware (4 params)

**Entry point**: Usually `src/index.ts` or `server.ts`. Look for `app.listen()`

**Typical workflow**: HTTP request → middleware chain → route handler → service → DB

---

## Next.js (React / TypeScript)

**Where things live**:
- Pages (App Router): `app/` — each folder is a route, `page.tsx` is the UI, `layout.tsx` wraps children
- Pages (Pages Router): `pages/` — each file is a route, `_app.tsx` wraps all
- API Routes: `app/api/*/route.ts` or `pages/api/*.ts`
- Components: `components/`, `src/components/`
- Hooks: `hooks/`, `lib/hooks/`
- Server Actions: files with `'use server'` directive
- Static data / fetch: `lib/`, `utils/`, `data/`
- Styling: `styles/`, CSS Modules (`*.module.css`), Tailwind config

**Key patterns**:
- `'use client'` / `'use server'` directives — distinguish rendering boundary
- `generateStaticParams()` — static site generation
- `getServerSideProps()` / `getStaticProps()` — data fetching (Pages Router)
- Server Components (no useState, fetch directly)

**Entry point**: `app/layout.tsx` (root layout) or `pages/_app.tsx`

---

## React (SPA / Vite or CRA)

**Where things live**:
- Components: `src/components/`
- Pages/Views: `src/pages/`, `src/views/`, `src/screens/`
- State management: `src/store/`, `src/context/`, `src/redux/`, `src/zustand/`
- Hooks: `src/hooks/`
- API layer: `src/api/`, `src/services/`, `src/lib/api.ts`
- Types: `src/types/`, `src/interfaces/`
- Router: files with `createBrowserRouter`, `BrowserRouter`, `Routes` from react-router

**Key patterns**:
- `createContext` / `useContext` — shared state
- `useEffect` + fetch/axios — data fetching
- `useState`, `useReducer` — component state
- `React.memo`, `useMemo` — performance

**Entry point**: `src/main.tsx` or `src/index.tsx`

---

## Vue.js / Nuxt

**Where things live**:
- Components: `src/components/`, `components/`
- Views/Pages: `src/views/`, `pages/` (Nuxt auto-routing)
- Composables: `composables/`, `src/composables/`
- Store: `src/store/`, `stores/` (Pinia), `store/` (Vuex)
- Router: `src/router/index.ts`
- Plugins: `plugins/`

**Key patterns**:
- `defineComponent`, `setup()` — Composition API
- `ref()`, `reactive()`, `computed()` — reactivity
- `<script setup>` — shorthand Composition API
- `useNuxtApp()`, `useFetch()` — Nuxt composables

**Entry point**: `src/main.ts` (Vue SPA) or `nuxt.config.ts` + `app.vue` (Nuxt)

---

## Django (Python)

**Where things live**:
- URL routing: `urls.py` files at project and app level
- Views: `views.py` (function-based) or class-based views in `views.py`
- Models: `models.py` in each Django app
- Serializers (DRF): `serializers.py`
- Forms: `forms.py`
- Admin: `admin.py`
- Settings: `settings.py`, `settings/` directory
- Migrations: `migrations/` in each app

**Key patterns**:
- `path()`, `include()` — URL conf
- `@login_required`, `@permission_required` — auth decorators
- `QuerySet` methods: `.filter()`, `.select_related()`, `.prefetch_related()`
- `class Meta` in models — DB config

**Entry point**: `manage.py`, `wsgi.py`, `asgi.py`

**Signal usage map**: `@receiver(post_save, sender=Order)` means `OrderService.save()` triggers hidden side effects. Detect signals via `@receiver`, `post_save.connect()`, `pre_delete.connect()`. Document each signal: sender model, signal type (post_save/pre_delete/etc.), and side effect description. Signals create invisible dependencies that break when models are renamed or deleted.

**Celery task inventory**: `@shared_task` and `@app.task` functions are an async codebase embedded in Django. Detect in `tasks.py` files across all Django apps. Document for each task: task name (Python dotted path), retry logic (`max_retries`, `autoretry_for`), and expected execution time. Celery tasks are often untested and undocumented despite being business-critical.

**Custom manager/queryset documentation**: `MyModel.objects.active()` hides business rules. Document any non-standard manager methods defined via `Manager` subclass or `QuerySet` subclass with `as_manager()`. These methods encode business concepts (e.g., `active()`, `published()`, `for_user(user)`) that are invisible without reading the model file.

---

## Flask (Python)

**Where things live**:
- Routes: files with `@app.route()` or `@blueprint.route()`
- Blueprints: files with `Blueprint()` init
- Models: often with SQLAlchemy — `models.py`, `models/`
- Config: `config.py`, `app/config.py`, environment in `.env`
- Extensions: `extensions.py` (db, login_manager, migrate, etc.)
- Templates: `templates/` (Jinja2)

**Key patterns**:
- `@app.route('/path', methods=['GET', 'POST'])` — route definition
- `g`, `request`, `session` — Flask globals
- `db.Model` — SQLAlchemy model base class
- `app.config.from_object()` — config loading

**Entry point**: `app.py`, `run.py`, `wsgi.py`, or `app/__init__.py`

---

## FastAPI (Python)

**Where things live**:
- Routers: `routers/`, `api/`, files with `APIRouter()`
- Models/Schemas: `schemas/`, `models/` — Pydantic models
- Dependencies: `dependencies.py`, `deps.py` — `Depends()` callables
- Database: `database.py`, `db/`, `crud/`
- Config: `core/config.py`, `config.py` — often Pydantic `BaseSettings`
- Middleware: files passed to `app.add_middleware()`

**Key patterns**:
- `@router.get()`, `@router.post()` — route decorators
- `Depends()` — dependency injection (auth, DB sessions)
- `async def` routes — async first
- Pydantic models as request/response schemas
- `lifespan` context manager — startup/shutdown events

**Entry point**: `main.py`, `app/main.py`

---

## Spring Boot (Java / Kotlin)

**Where things live**:
- Controllers: classes annotated `@RestController` or `@Controller`
- Services: classes annotated `@Service`
- Repositories: interfaces extending `JpaRepository`, `CrudRepository`
- Entities/Models: classes annotated `@Entity`
- Config: classes annotated `@Configuration`, `application.yml`, `application.properties`
- DTOs: `dto/`, `model/` directories

**Key patterns**:
- `@Autowired` / constructor injection — dependency injection
- `@GetMapping`, `@PostMapping` — HTTP mappings
- `@Transactional` — transaction management
- `@Bean` — bean definition

**Entry point**: Class with `@SpringBootApplication` + `main()` calling `SpringApplication.run()`

**`@Profile` and `@ConditionalOnProperty` documentation**: `@Profile("prod")` means a bean only exists in production; `@ConditionalOnProperty(name="feature.x.enabled", havingValue="true")` means it only activates when a config flag is set. Detect via `@Profile`, `@ConditionalOnProperty`, `@ConditionalOnMissingBean`, `@ConditionalOnClass`. Document for each conditional bean: which profile/property activates it, what it replaces in other environments, and why. Critical for new devs who wonder why a bean exists in production but not locally.

**Spring Security config explanation pattern**: `SecurityFilterChain` is where authentication and authorization happen — always document it. The `@Bean SecurityFilterChain` method in your `@Configuration` class defines: which endpoints require authentication, which require specific roles (`hasRole("ADMIN")`), the auth mechanism (JWT filter, OAuth2, form login, HTTP Basic), and CSRF/CORS configuration. Document the filter order and which custom filters are added via `addFilterBefore` / `addFilterAfter`.

---

## Go (Standard Layout)

**Where things live**:
- Main packages: `cmd/` — one sub-directory per binary
- Library code: `internal/` — private packages, `pkg/` — public packages
- HTTP handlers: files with `http.HandleFunc()`, `mux.Handle()`, or framework router
- Models/Types: `internal/domain/`, `models/`, `types/`
- Storage: `internal/store/`, `internal/repository/`, `internal/db/`
- Config: `internal/config/`, `config.go`

**Key patterns**:
- `func main()` in `cmd/*/main.go`
- `http.ListenAndServe()` — server start
- `context.Context` — propagated through handlers
- Interfaces for dependencies — test-friendly design
- `init()` functions — package initialization

**Entry point**: `cmd/*/main.go` or `main.go`

---

## Rust (Cargo)

**Where things live**:
- Entry: `src/main.rs` (binary) or `src/lib.rs` (library)
- Modules: `src/` sub-modules declared via `mod` in `main.rs`/`lib.rs`
- Routes (web framework): `src/routes/`, handler functions
- Config: `src/config.rs`, `config/`
- Error types: `src/error.rs`, `src/errors/`
- DB: `src/db.rs`, `src/repository/`

**Key patterns**:
- `pub mod` — public module declarations
- `#[derive(Serialize, Deserialize)]` — serde for JSON
- `Result<T, E>` — error handling everywhere
- `async fn` + `tokio::main` — async runtime
- Middleware as `tower::Layer` (axum/tower)

**Entry point**: `src/main.rs` — look for `#[tokio::main]`

---

## Angular (TypeScript)

**Where things live**:
- App bootstrap: `src/main.ts` (calls `bootstrapApplication` or `platformBrowserDynamic`)
- Root module: `src/app/app.module.ts` (NgModule-based) or `src/app/app.config.ts` (standalone)
- Root routing: `src/app/app-routing.module.ts` or `src/app/app.routes.ts`
- Feature modules: `src/app/features/`, `src/app/modules/`, or `src/app/pages/` — each subfolder is a feature
- Components: files ending in `.component.ts` — always paired with `.component.html` and `.component.scss`
- Services: files ending in `.service.ts` — typically in `src/app/core/services/` or co-located with their feature
- Guards: files ending in `.guard.ts` — `src/app/core/guards/`
- Interceptors: files ending in `.interceptor.ts` — `src/app/core/interceptors/`
- Pipes: files ending in `.pipe.ts`
- Models/Interfaces: `src/app/core/models/`, `src/app/shared/models/`, or `src/app/models/`
- Shared: `src/app/shared/` — reusable components, pipes, directives used across features
- Core: `src/app/core/` — singleton services, guards, interceptors loaded once at app level
- NgRx store: `src/app/store/`, or co-located in feature folders as `*.actions.ts`, `*.reducer.ts`, `*.effects.ts`, `*.selectors.ts`
- Environments: `src/environments/environment.ts` (dev), `src/environments/environment.prod.ts`
- Config: `angular.json` (build config), `tsconfig.json`, `tsconfig.app.json`

**Key patterns**:
- `@NgModule({ declarations, imports, providers })` — module definition (classic)
- `@Component({ standalone: true, imports: [...] })` — standalone component (modern Angular 17+)
- `@Injectable({ providedIn: 'root' })` — singleton service via DI
- `@Injectable({ providedIn: FeatureModule })` — feature-scoped service
- `RouterModule.forRoot(routes)` / `RouterModule.forChild(routes)` — routing registration
- `loadChildren: () => import('./feature/feature.module').then(m => m.FeatureModule)` — lazy loading
- `loadComponent: () => import('./page/page.component').then(c => c.PageComponent)` — standalone lazy loading
- `CanActivate`, `CanActivateFn` — route guards for auth/permissions
- `HttpInterceptor` / `HttpInterceptorFn` — intercept HTTP requests (add auth headers, handle errors)
- `@Input()` / `@Output()` / `EventEmitter` — parent-child component communication
- `Subject`, `BehaviorSubject` from RxJS — service-to-component state sharing
- `AsyncPipe` — subscribe to Observables directly in templates
- `createReducer`, `createAction`, `createEffect`, `createSelector` — NgRx state management
- Signal-based: `signal()`, `computed()`, `effect()` — Angular 17+ reactivity primitives

**Entry point sequence**:
`src/main.ts` → bootstraps `AppModule` (or `AppComponent` standalone) → `AppRoutingModule` loads routes → initial route activates root component → lazy-loaded feature modules load on demand

**Typical workflow**:
HTTP request from component → `HttpClient` call in service → HTTP interceptor chain → backend API → response mapped through RxJS operators → component subscribes via AsyncPipe or `subscribe()`

**File naming conventions**:
`feature-name.component.ts`, `feature-name.service.ts`, `feature-name.guard.ts`, `feature-name.module.ts`, `feature-name.routes.ts`

---

## ASP.NET Core (C#)

**Where things live**:
- Controllers: `Controllers/` — classes inheriting `ControllerBase`
- Models/DTOs: `Models/`, `DTOs/`
- Services: `Services/` — registered in DI container
- Middleware: `Middleware/` — `IMiddleware` implementations
- Data/EF: `Data/`, `Repositories/` — `DbContext` subclass
- Config: `appsettings.json`, `appsettings.{Environment}.json`
- Program entry: `Program.cs` (modern minimal API) or `Startup.cs` (older pattern)

**Key patterns**:
- `builder.Services.AddScoped<>()` — DI registration
- `[ApiController]`, `[Route()]` — controller attributes
- `[HttpGet]`, `[HttpPost]` — action attributes
- `IOptions<T>` — typed configuration
- `DbContext.Set<T>()` — EF Core queries

**Entry point**: `Program.cs` — look for `WebApplication.CreateBuilder()` and `app.Run()`

---

## .NET Enterprise (CQRS/MediatR/DI)

**Where things live**:
- Commands: `Commands/`, `Application/Commands/` — classes implementing `IRequest<T>`
- Queries: `Queries/`, `Application/Queries/` — classes implementing `IRequest<T>` (read-only)
- Handlers: co-located with commands/queries — classes implementing `IRequestHandler<TRequest, TResponse>`
- Validators: `Validators/` — FluentValidation `AbstractValidator<T>` classes
- Mappings: `Mappings/`, `Profiles/` — AutoMapper `Profile` subclasses
- Controllers: `Controllers/` — thin; delegate immediately to `IMediator.Send()`
- Services: `Services/` — domain services registered in DI
- Repositories: `Repositories/` — data access, registered as `IRepository<T>`
- Config: `appsettings.json`, `appsettings.{Environment}.json`, classes bound via `IOptions<T>`
- Program entry: `Program.cs` — the DI composition root

**Key patterns**:
- `IMediator.Send(new CreateOrderCommand(...))` — all business operations go through MediatR
- `IRequest<T>` / `IRequestHandler<TRequest, TResponse>` — command/query handler contract
- DI lifecycle registrations in `Program.cs` — document WHICH lifecycle and WHY:
  - `AddSingleton<>()` — one instance for app lifetime (e.g., configuration, caches)
  - `AddScoped<>()` — one instance per HTTP request (e.g., DbContext, repositories) — CORRECTNESS-AFFECTING: sharing across requests causes bugs
  - `AddTransient<>()` — new instance each injection (e.g., lightweight stateless services)
- Middleware pipeline ORDER in `Program.cs` (order matters, rarely documented):
  - `app.UseExceptionHandler()` must come before `app.UseRouting()`
  - `app.UseAuthentication()` must come before `app.UseAuthorization()`
- `IOptions<T>` bound to `appsettings.json` sections — document which config class maps to which JSON path
- `[MediatR.Behaviors]` pipeline behaviors — cross-cutting concerns (logging, validation, transactions) registered as `IPipelineBehavior<,>`

**Entry point**: `Program.cs` → `WebApplication.CreateBuilder(args)` → service registrations → `app.UseMiddleware...` pipeline → `app.Run()`

**Typical workflow**: HTTP request → `Controller.Action()` → `IMediator.Send(command)` → `IPipelineBehavior` chain (validation → logging → transaction) → `IRequestHandler.Handle()` → repository → DB response

---

## Go Service Mesh (Large-Scale)

**Where things live**:
- Binaries: `cmd/` — one sub-directory per runnable binary (`cmd/api/`, `cmd/worker/`, `cmd/migrator/`)
- Private packages: `internal/` — not importable outside the module; domain logic lives here
- Public packages: `pkg/` — reusable packages safe to import by external modules
- API contracts: `api/` — `.proto` files (gRPC), OpenAPI specs (`*.yaml`), generated stubs
- Generated stubs: `*_grpc.pb.go`, `*.pb.go` — DO NOT document internals; document the `.proto` source instead
- Config: `internal/config/`, `config.go`, loaded via `os.Getenv` or `viper`
- Makefile: root `Makefile` — the Go team's primary workflow tool

**Key patterns**:
- Makefile targets — document EVERY target (Go teams live by Makefiles):
  - `make build` — compiles all binaries in `cmd/`
  - `make test` — runs unit tests with `-race` flag
  - `make generate` — runs `go generate ./...` (proto compilation, mocks, etc.)
  - `make docker` — builds container image
  - `make migrate` — applies DB migrations
- Concurrency patterns (document ownership explicitly):
  - Goroutine ownership: which function spawns it, which owns its lifetime
  - Channel ownership: which goroutine sends, which receives, buffer size and why
  - Shutdown sequence: `context.WithCancel(ctx)` passed to all goroutines; `cancel()` on `os.Signal`
- `go.work` multi-module workspace (Go 1.18+): if `go.work` exists at root, multiple `go.mod` files are in play — list all modules and their roles
- gRPC: `.proto` files in `api/` are the source of truth; generated `*_grpc.pb.go` are artifacts — document the proto service definitions, not the generated Go code
- `grpc.UnaryInterceptor` / `grpc.StreamInterceptor` — middleware chain for gRPC (auth, logging, tracing)

**Entry point**: `cmd/*/main.go` → `http.ListenAndServe()` (REST) or `grpc.NewServer()` (gRPC) → service initialization

**Typical workflow**: HTTP/gRPC request → handler → middleware/interceptor chain → service layer (`internal/`) → repository (`internal/store/`) → DB/external service

---

## PHP Laravel Enterprise

**Where things live**:
- Controllers: `app/Http/Controllers/` — thin; delegate to services
- Services: `app/Services/` — business logic layer
- Models: `app/Models/` — Eloquent ORM; contains scopes, accessors, mutators
- Jobs: `app/Jobs/` — async queue tasks (the hidden second codebase)
- Events: `app/Events/` — event classes dispatched throughout the app
- Listeners: `app/Listeners/` — react to events; invisible dependencies that can trigger side effects
- Policies/Gates: `app/Policies/` — authorization rules per model
- Form Requests: `app/Http/Requests/` — request validation classes
- Resources/Collections: `app/Http/Resources/` — API response transformers
- Service Providers: `app/Providers/` — DI registration hub (especially `AppServiceProvider.php`)
- Routes: `routes/api.php` (API routes), `routes/web.php` (web routes) — primary entry point documentation
- Config: `config/` — each file maps to a config key (e.g., `config/database.php`)
- Migrations: `database/migrations/` — timestamp-ordered schema changes

**Key patterns**:
- `AppServiceProvider.php` — where all DI bindings are registered: `$this->app->bind(Interface::class, Implementation::class)`
- Eloquent scopes: `scopeActive($query)` in models → called as `Model::active()` — business logic hidden in models; always document non-standard scope methods
- Eloquent accessors/mutators: `getFullNameAttribute()` / `setPasswordAttribute()` — transparent field transforms
- Jobs/Queues: `dispatch(new ProcessOrderJob($order))` — async tasks with retry logic; jobs in `app/Jobs/` are a separate async codebase
- Events + Listeners: `event(new OrderPlaced($order))` → listeners fire invisibly; document event → listener mappings in `EventServiceProvider.php`
- Facades: `Cache::get()`, `Queue::push()`, `Log::info()` — static-looking but DI-backed

**Entry point**: `public/index.php` → `bootstrap/app.php` → `Kernel` (HTTP or Console) → route dispatching via `routes/api.php` or `routes/web.php`

**Typical workflow**: HTTP request → `public/index.php` → middleware pipeline (auth, CORS, throttle) → Controller → Service → Eloquent Model → DB; async paths go via Job dispatch → queue worker → Job handler

---

## Rust Workspace (Multi-Crate)

**Where things live**:
- Workspace root: `Cargo.toml` with `[workspace]` section listing all member crates
- Crates: `crates/*/` or top-level `src/` for single-crate projects; each crate has its own `Cargo.toml`
- Binary crates: `src/main.rs` — executable entry points
- Library crates: `src/lib.rs` — reusable code, no `main()`
- Feature flags: `[features]` in `Cargo.toml` — conditional compilation affecting public API; document which features are enabled by default and what they gate
- Build scripts: `build.rs` at crate root — runs at compile time; must be documented (generates code, links native libraries, sets env vars for the build)
- Error types: `src/error.rs` or `src/errors/` — `thiserror` for library errors (typed, implement `std::error::Error`), `anyhow` for application errors (propagation convenience)

**Key patterns**:
- `Cargo.toml` `[features]` — `cargo build --features "feature-name"` changes the compiled public API; always document default-features and optional-features
- `build.rs` — if present, it runs before compilation; check what it generates (e.g., proto stubs, version strings, FFI bindings)
- Error propagation: `thiserror::Error` derive on library error enums; `anyhow::Result` / `?` operator for application code — understand which crates use which
- Async runtime: `#[tokio::main]` (Tokio, most common) or `#[async_std::main]` (async-std); look in binary crate's `Cargo.toml` for `tokio = { features = ["full"] }`
- Trait-based DI: dependencies injected as trait objects (`Box<dyn Repository>`) for testability
- `pub use` re-exports in `lib.rs` — shapes the public API; what's re-exported IS the public surface

**Entry point**: `src/main.rs` with `#[tokio::main]` (async binary) or `src/lib.rs` for library crates

**Typical workflow**: `main()` → runtime setup (tracing, config) → service initialization (DI wiring) → server bind (`axum::serve` / `tonic::transport::Server`) → request handling → service layer → repository (trait impl) → DB

---

## Nx Workspace

**Where things live**:
- Apps: `apps/` — deployable applications (Angular, React, Node, etc.); each has a `project.json`
- Libs: `libs/` — shared libraries; never deployed directly, always consumed by apps or other libs
- Tools: `tools/` — custom generators, executors, and workspace scripts
- Root config: `nx.json` — workspace-level settings, `targetDefaults`, `cacheableOperations`, `depConstraints`
- Per-project config: `project.json` in each app/lib — defines `targets` (build, test, lint, serve), `tags`, and executor config

**Key patterns**:
- `project.json` targets: each target maps to an executor (e.g., `@nx/angular:build`) with its options; these ARE the build commands
- Tag system: projects declare `"tags": ["scope:feature-name", "type:feature"]` — tags determine what can import what
  - `scope:*` tags: which feature domain a project belongs to
  - `type:feature` — smart component + state, can import ui/data-access/util
  - `type:ui` — presentational only, no business logic
  - `type:data-access` — state management, API calls
  - `type:util` — pure functions, no Angular/React deps
- `depConstraints` in `nx.json`: these ARE the architectural boundary documentation — e.g., `type:feature` can depend on `type:ui` but not vice versa. Always document the constraint rules.
- `nx affected`: before changing any shared lib, run `nx affected:graph` to see the blast radius — document which libs are most widely depended-upon (highest fan-in)
- Caching: `nx.json` `cacheableOperations` — tasks whose outputs are cached; understand before changing shared code

**Entry point**: `apps/*/src/main.ts` (Angular), `apps/*/src/index.tsx` (React), `apps/*/src/main.ts` (Node)

**Typical workflow**: `nx build my-app` → resolves `project.json` targets → executor runs → affected libs built first per dependency graph → output cached to `.nx/cache`

---

## Turborepo

**Where things live**:
- Apps: `apps/` — deployable applications; each has its own `package.json` with scripts
- Packages: `packages/` — shared code (UI library, config, TypeScript config, etc.)
- Root: `turbo.json` — the task dependency pipeline; `package.json` with `workspaces` field
- Common shared packages: `packages/ui/` (`@repo/ui`), `packages/config/` (`@repo/config`), `packages/tsconfig/` (`@repo/tsconfig`) — understand these before editing anything

**Key patterns**:
- `turbo.json` pipeline: defines task dependency order and caching rules
  - `"dependsOn": ["^build"]` — must build dependencies first (the `^` means "run in all deps first")
  - `"outputs": ["dist/**"]` — what gets cached; Turborepo won't re-run if outputs are unchanged
  - `"cache": false` — tasks that must always re-run (e.g., `dev`, `start`)
- Caching strategy: `turbo run build` skips rebuilding packages if their inputs haven't changed; cache keys based on file hashes + env vars listed in `globalEnv`
- Shared packages: `@repo/ui`, `@repo/config`, `@repo/tsconfig` are consumed by all apps — changes here affect every app; check `turbo affected` before editing
- `package.json` `workspaces`: glob patterns that tell the package manager which directories are packages (e.g., `["apps/*", "packages/*"]`)

**Entry point**: `apps/*/src/index.ts` or `apps/*/src/main.ts` per app; run via `turbo run dev` from workspace root

**Typical workflow**: `turbo run build` → reads pipeline from `turbo.json` → topological sort of tasks → runs tasks in parallel where no dependency → caches outputs → `apps/*/dist/` produced
