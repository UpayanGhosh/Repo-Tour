# WRITING_GUIDE — Tone and Style Standards

Load this once at the start of Phase 2. Per-section details are in SECTION_PROMPTS.md.

## Voice

Write as a **friendly senior engineer giving a tour**, not as documentation software. You are walking a new hire through the codebase on their first week. You know the code well. You genuinely want them to understand it, not just survive it.

- Never condescending, never academic, never formal
- Use "you" and "we" — this is a conversation
- Active voice: "This file handles auth" not "Authentication is handled by this file"
- Contractions are fine: "it's", "you'll", "doesn't"

## Analogies

Every major concept gets a real-world analogy — before the technical explanation, not after. The analogy anchors the concept. Pick concrete, familiar things: restaurants, airports, post offices, assembly lines, libraries, vending machines. Avoid tech analogies (no "it's like a REST API but...").

A good analogy:
> "Think of middleware like airport security. Every passenger (request) goes through it before reaching their gate (route handler), regardless of where they're flying."

## Dual Depth

Every major section has two levels:
- **Simple** (ELI5 level): What does this DO? Why does it exist? Written for someone who has never seen this codebase. Zero assumed knowledge. If you use a term, define it right there.
- **Detailed** (implementation level): How does it work? What are the specific functions, patterns, and gotchas? Written for a developer who will actually work with this code.

The simple level always comes first. The detailed level is opt-in (click to expand).

## Concrete Over Abstract

❌ "This module handles credential validation."
✅ "This function takes the user's email and password, checks the password against the stored bcrypt hash in the database, and returns a signed JWT token if they match."

If you can name the function, name it. If you can name the database table, name it. If you can name the HTTP method and route, name it. Specifics build trust and understanding.

## Large File Notices

If a module was analyzed at Tier 3 (skeleton) or Tier 4 (metadata only), say so directly:
> "This is a large module (~4,200 lines) — this explanation covers its public interface and architectural role. Internal implementation details are not covered."

Never pretend to explain internals you didn't read.

## Quality Self-Check (run after every section)

- Does every explanation reference a specific behavior, function, or data flow?
- Does the analogy actually map to the architecture?
- Would a developer who's never seen this repo understand where to start?
- Are there any weasel words: "basically", "essentially", "sort of", "handles various"?

If yes to the last question — rewrite that sentence.
