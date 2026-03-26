# WEBSITE_SPEC — Generated Website Specification

## Overview

**Output**: Single `index.html` file — no build step, no npm, no server required.
**Deploy**: Open locally or push to Vercel / Netlify / GitHub Pages.
**External dependencies**: Mermaid.js CDN only (graceful offline fallback). Google Fonts CDN for typography.

## Structure

Single-page application. All sections are on one scrollable page. Navigation highlights the active section via IntersectionObserver.

```
Layout: fixed sidebar (240px left) + scrollable main content
Mobile: sidebar becomes a drawer (hidden off-screen, toggled by hamburger button)
Max content width: 680px, centered
```

## Navigation (Sidebar)

- Fixed left sidebar, always visible on desktop
- Lists all sections with scroll-to-section links
- Active section highlighted as user scrolls (IntersectionObserver)
- Module subsections collapsible under "Modules" parent link
- On mobile: transform: translateX(-240px) by default, toggled by hamburger button

## Sections (in order)

1. **Overview** — Project summary, audience, approach
2. **Architecture** — Analogy, layer diagram, Mermaid graph
3. **Cross-Cutting Concerns** — Auth/authz, error handling, logging/observability, testing strategy
4. **Tech Stack** — Card grid of technologies with role + why
5. **Entry Points** — How the app starts, flow narrative
6. **Modules** — Module cards with simple/detailed toggle
7. **Workflows** — Step-by-step traces with Mermaid sequence diagrams
8. **Directory Guide** — Folder purposes and when-to-look-here
9. **Glossary & Getting Started** — Term definitions + setup commands + day-1/week-1 learning path
10. **Developer Cookbook** — Task-based recipes: "How do I add a route?", "How do I call an API?", etc.

## Simple/Detailed Toggle

Every major section with dual-depth content has a toggle button:
- Default state: shows **simple** explanation
- Click "Show Details": reveals **detailed** explanation, hides simple
- Click "Show Overview": returns to simple
- State stored in JS variable (NOT localStorage — unavailable in sandboxed environments)
- Toggle button text changes to reflect current state

## Search

- **Shortcut**: Ctrl+K (or Cmd+K on Mac) opens search modal
- **Modal**: Full-screen overlay with search input, keyboard-navigable results
- **Engine**: Client-side. Tokenized search against a pre-built index injected as `window.SEARCH_INDEX`
- **Index structure**: `[{id, section, text, snippet}]`
- **Results**: Section name + 100-char snippet + click scrolls to section
- **Escape** closes modal

## Mermaid Diagrams

- Loaded from CDN: `https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js`
- Initialized with theme matching dark/light mode
- **Graceful fallback**: if Mermaid fails to load, show raw diagram code in a `<pre>` block
- **Clickable nodes** (architecture diagram only): clicking a module node scrolls to that module's card
- Re-initialize on theme change

## Dark / Light Mode

- On load: detect `prefers-color-scheme` media query
- Manual toggle: button in sidebar header, toggles `data-theme` attribute on `<html>`
- State stored in JS variable (no localStorage)
- Two complete color palettes via CSS custom properties on `[data-theme="dark"]`
- Mermaid theme switches to `dark` when dark mode active, `default` for light

## Color Scheme (Language-Aware)

`generate_site.py` injects CSS variable overrides based on primary language:

| Language | Accent Color | --accent value |
|----------|-------------|----------------|
| TypeScript / JavaScript | Blue | #3b82f6 |
| Python | Green | #22c55e |
| Rust | Orange | #f97316 |
| Go | Cyan | #06b6d4 |
| Java / Kotlin | Red | #ef4444 |
| C# | Purple | #a855f7 |
| Ruby | Rose | #f43f5e |
| PHP | Indigo | #6366f1 |
| Default | Slate | #64748b |

## Typography

Use Google Fonts. Pick a distinctive pairing — not the same one every time. Suggestions:
- Fraunces (headings) + DM Sans (body)
- Playfair Display (headings) + Outfit (body)
- Syne (headings) + Inter (body)
- Cormorant (headings) + Plus Jakarta Sans (body)

generate_site.py selects the pairing based on a hash of the project name, for variety.

Typography scale:
- H1: 2.25rem, heading font, weight 700
- H2: 1.75rem, heading font, weight 600
- H3: 1.25rem, heading font, weight 600
- Body: 1rem / 1.625 line-height, body font, weight 400
- Code: 0.875rem, monospace (system-ui-monospace stack)

## Responsive Breakpoints

- `> 1024px`: Full sidebar + content layout
- `768px - 1024px`: Sidebar narrower (240px)
- `< 768px`: Sidebar becomes drawer, hamburger button appears, content full-width

## Print Stylesheet

`@media print`:
- Hide sidebar, search bar, toggle buttons, deploy dropdown
- Show all content (expand all simple/detailed sections)
- Single column
- Page breaks before H2 sections
- Clean black-on-white typography

## Accessibility

- All interactive elements have ARIA labels
- Keyboard navigation: Tab through nav links, Enter to activate
- Focus states visible (outline: 2px solid accent)
- Search modal traps focus when open
- Color contrast meets WCAG AA

## "Deploy This" Dropdown

Footer button reveals copy-to-clipboard commands:
```
Vercel:       npx vercel output/
Netlify:      npx netlify deploy --dir output/
GitHub Pages: gh-pages -d output/
Local:        open output/index.html
```

Each command has a copy icon. Clicking copies to clipboard and shows "Copied!" for 2 seconds.

## Placeholder Markers (for generate_site.py)

The template uses `{{PLACEHOLDER}}` markers that generate_site.py replaces:

| Marker | Replaced with |
|--------|--------------|
| `{{PROJECT_NAME}}` | repo name |
| `{{CSS}}` | inlined styles.css content |
| `{{JS}}` | inlined app.js content |
| `{{COLOR_VARS}}` | language-specific CSS variable overrides |
| `{{NAV}}` | sidebar navigation HTML |
| `{{OVERVIEW}}` | overview section HTML |
| `{{ARCHITECTURE}}` | architecture section HTML |
| `{{CROSS_CUTTING}}` | cross-cutting concerns section HTML |
| `{{TECH_STACK}}` | tech stack section HTML |
| `{{ENTRY_POINTS}}` | entry points section HTML |
| `{{MODULES}}` | all module cards HTML |
| `{{WORKFLOWS}}` | workflow traces HTML |
| `{{DIRECTORY_GUIDE}}` | directory guide HTML |
| `{{GLOSSARY}}` | glossary section HTML |
| `{{GETTING_STARTED}}` | getting started section HTML |
| `{{COOKBOOK}}` | developer cookbook section HTML |
| `{{SEARCH_INDEX}}` | JS search index variable |
| `{{FONT_URL}}` | Google Fonts URL for chosen pairing |
| `{{FONT_HEADING}}` | heading font family name |
| `{{FONT_BODY}}` | body font family name |
