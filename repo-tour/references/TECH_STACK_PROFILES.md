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
