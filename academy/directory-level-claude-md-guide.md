# Directory-Level CLAUDE.md: Scoped AI Context for Modular Codebases

## What Is CLAUDE.md?

CLAUDE.md is a markdown file that Claude Code reads automatically to learn project-specific rules, conventions, and domain context. It functions as a persistent, version-controlled system prompt that lives alongside the code it governs. Unlike chat history or ad-hoc instructions, CLAUDE.md survives across sessions and is shared with every collaborator via source control. When Claude opens a file, it loads all applicable CLAUDE.md files to inform how it writes, reviews, and reasons about code in that area.

## The CLAUDE.md Hierarchy

Claude Code supports three tiers of CLAUDE.md, each with distinct loading behavior:

| Tier | Path | Loaded When | Purpose |
|------|------|-------------|---------|
| Root | `/CLAUDE.md` | Always | Global rules, framework warnings, file includes (`@AGENTS.md`) |
| User-local | `/.claude/CLAUDE.md` | Always (alongside root) | Project documentation: tech stack, structure, commands, conventions |
| Directory-scoped | `<any-dir>/CLAUDE.md` | Only when Claude operates on files within that directory subtree | Subsystem-specific contracts: schemas, naming, validation, caching |

Three mechanics govern how these tiers interact:

- **Additive loading** -- directory-scoped files supplement, never replace, the root and user-local tiers. Claude sees the union of all applicable files.
- **Path-based scoping** -- a CLAUDE.md at `src/app/api/` activates only when Claude touches files under `src/app/api/`. Working on `src/components/` does not load it.
- **Inheritance** -- deeper directories inherit everything from parent CLAUDE.md files. A hypothetical `src/app/api/movies/CLAUDE.md` would layer on top of `src/app/api/CLAUDE.md`.

## Real-World Example: API Route Conventions

This project's `src/app/api/CLAUDE.md` demonstrates directory-level scoping in practice. It defines six conventions that apply exclusively to API route handlers:

**REST Naming** -- plural nouns for collections (`/api/movies`), kebab-case for multi-word segments, nested sub-resources (`/api/movies/[id]/reviews`), no trailing slashes, no verbs in paths.

**Route Handler Structure** -- one `route.ts` per directory, export only supported HTTP methods, use `NextResponse.json()` for all responses.

**Post Object Schema** -- a typed contract defining fields (`id`, `title`, `category`, `author`, `rating`, `createdAt`, `updatedAt`) with types and descriptions, embedded directly in the CLAUDE.md rather than relying on Claude to infer from source.

**Response Contract** -- success returns data directly; errors return `{ "error": "..." }` with appropriate HTTP status codes (200, 201, 400, 404, 500).

**Caching** -- `Cache-Control: public, s-maxage=7200, stale-while-revalidate=3600` on GET responses; omit on mutations.

**Validation** -- validate at the handler boundary; return 400 for invalid input.

The proof is in the existing code. The project's `src/app/api/movies/route.ts` (18 lines) conforms to every one of these conventions -- `NextResponse.json()` responses, `Cache-Control` headers on the GET, error shape `{ error: "Failed to fetch posts" }` with status 500. This conformance is not coincidental; Claude generated this code with the directory-scoped CLAUDE.md loaded.

## Pros

- **Noise reduction** -- Claude's effective context window is not polluted with API conventions when editing a React component. Token budget is preserved for the task at hand.
- **Separation of concerns** -- mirrors how teams organize documentation. API conventions live next to API code, not in a monolithic root document.
- **Precision** -- subsystem-specific rules (schemas, response shapes, caching policies) are too detailed for a root file but too important to omit. Directory-scoped files hit the right granularity.
- **Scalability** -- as a monorepo grows, a single root CLAUDE.md becomes unwieldy. Each module or service owns its own AI instructions.
- **Composability** -- teams author their CLAUDE.md files independently without merge conflicts in a shared root.

## Cons

- **Discovery overhead** -- no global manifest lists all CLAUDE.md files. Contributors may not know a directory-scoped file exists until they work in that subtree.
- **Duplication risk** -- if similar conventions span multiple directories, content may be copied rather than shared. Only root-level files support `@`-includes.
- **Maintenance burden** -- when a shared convention changes (e.g., response schema evolves), every directory-scoped file referencing it must be updated independently.
- **Over-segmentation** -- a CLAUDE.md per leaf directory can fragment context, leaving Claude with incomplete information when a task spans multiple directories.

## Best Practices

1. **Start in root, extract when it hurts.** Keep all conventions in the root or user-local CLAUDE.md initially. Extract a directory-scoped file only when the root exceeds ~200 lines or a subsystem has conventions irrelevant to the rest of the codebase.

2. **Place at architectural boundaries.** Target module or service boundaries: `src/app/api/`, `packages/auth/`, `src/workers/`. Avoid leaf directories unless they have truly distinct conventions.

3. **Keep files self-contained.** Include domain schemas, response contracts, naming rules, and validation expectations -- everything Claude needs to generate correct code without cross-referencing external documents.

4. **Document the hierarchy.** Add a note in your root CLAUDE.md listing directory-scoped files so contributors know they exist.

5. **Version in PRs.** Treat CLAUDE.md changes like code changes. When a schema evolves, the CLAUDE.md update belongs in the same pull request.

6. **Test conformance.** After writing a directory-scoped CLAUDE.md, ask Claude to generate code in that directory and verify it follows the documented conventions.

7. **Avoid contradictions.** Ensure directory-scoped content supplements the root without conflicting. If the root says "wrap responses in `{ data: ... }`" but a subdirectory says "return data directly," Claude will see both and may produce inconsistent output.
