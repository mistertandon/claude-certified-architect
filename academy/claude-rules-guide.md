# Claude Code Rules: Governing AI-Generated Code at the File Level

## What Are Rules?

Rules are markdown files stored in `.claude/rules/` that Claude Code loads automatically based on **glob patterns**. Unlike CLAUDE.md (which is path-scoped and always loaded or loaded per-directory), rules are **file-type-scoped** -- they activate only when Claude operates on files matching their glob. This makes rules the right mechanism for encoding conventions that are tied to a file category (tests, migrations, configs) rather than a directory subtree.

A rule file has two parts: **frontmatter** (metadata + globs) and **body** (the conventions).

```
---
description: <what this rule covers>
globs: ["<glob-pattern-1>", "<glob-pattern-2>"]
---

<conventions as markdown>
```

## Rules vs. CLAUDE.md: When to Use Which

| Dimension | CLAUDE.md | Rules |
|-----------|-----------|-------|
| Activation | Path-based (directory subtree) | Glob-based (file pattern) |
| Scope | Architectural boundaries (`src/app/api/`) | File categories (`**/*.test.tsx`) |
| Use case | API contracts, module conventions, schemas | Testing style, migration patterns, config templates |
| Loading | Always (root) or when touching that directory | Only when the matched file is the operation target |

Rules complement CLAUDE.md. A directory-scoped CLAUDE.md governs *where* code lives; a rule governs *how* a class of files is written regardless of location.

## Anatomy of a Rule: `testing.md`

The project's `.claude/rules/testing.md` demonstrates the pattern. Its frontmatter targets all test files across the codebase:

```yaml
globs: ["**/*.test.tsx", "**/*.test.ts", "**/*.spec.tsx", "**/*.spec.ts"]
```

The body defines four convention groups. Each is examined below, mapped to the actual `PostCard.test.tsx` that Claude generated under these rules.

---

### 1. Test Naming

**Rule**: Use `describe("<ComponentName>")` as the outer block. Name `it()` by behavior, not by field.

**In practice** (`PostCard.test.tsx`):

```typescript
describe("PostCard", () => {
  it("renders post heading and metadata", () => { ... });
  it("renders category, rating, and date as meta items", () => { ... });
  it("renders without crashing when fields are empty or zero", () => { ... });
});
```

The outer `describe` names the component. Each `it()` names a **behavior** ("renders post heading and metadata") not a field ("renders the post name"). A single render is not split into per-field tests -- heading and author are asserted together because they represent one behavior: *the component displays its primary content*.

### 2. Assertion Style

**Rule**: Max 2 `expect` per test. Prefer role-based queries over CSS selectors. Do not test class names or DOM structure.

**In practice**:

```typescript
// Role-based query -- tests the semantic heading, not a CSS class
expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent("The Matrix");

// Content query -- tests what the user sees, not the DOM node wrapping it
expect(screen.getByText("Wachowski Sisters")).toBeInTheDocument();
```

Every test in `PostCard.test.tsx` stays at or below the 2-assertion cap. No test references `styles.card`, `styles.metaItem`, or any CSS module class -- despite the component using them heavily. The tests verify **what users see**, not how the DOM is structured.

### 3. Fixture Usage

**Rule**: One base fixture per `describe`. Use spread for edge-case variations. Never duplicate a full fixture for one field change.

**In practice**:

```typescript
// Single base fixture at describe scope
const mockPost: Post = {
  id: 1,
  name: "The Matrix",
  author: "Wachowski Sisters",
  category: "Sci-Fi",
  rating: 9,
  lastUpdateTime: "2024-01-15",
};

// Edge case via spread -- only the fields under test change
const edgeCasePost: Post = { ...mockPost, name: "", rating: 0 };
```

The edge-case test overrides exactly `name` and `rating` -- the two fields whose boundary behavior it validates. Every other field inherits from `mockPost`, keeping the test focused and the diff between normal and edge case immediately visible.

### 4. What to Test

**Rule**: Test rendered content, conditional rendering, edge cases (empty strings, zero values). Do not test CSS classes, DOM structure, or that React renders props.

**In practice**: The three tests cover:

| Test | Convention Demonstrated |
|------|------------------------|
| `renders post heading and metadata` | Rendered content -- verifies the component displays its primary data |
| `renders category, rating, and date as meta items` | Rendered content -- verifies secondary metadata appears |
| `renders without crashing when fields are empty or zero` | Edge cases -- `name: ""` (empty string) and `rating: 0` (falsy number) |

Notably absent: no test checks that `className={styles.card}` is applied, no test counts the number of `<span>` elements, no test re-renders with `{ ...mockPost, author: "Different Author" }` just to assert a different string appears -- that would test React, not the component.

---

## Why Rules Matter for AI Solution Architects

Rules address a specific failure mode in AI-assisted development: **convention drift**. Without rules, each Claude session starts with zero knowledge of your testing philosophy, naming standards, or assertion boundaries. The AI defaults to its training distribution -- which may produce tests with 8 assertions, CSS class checks, and per-field test splitting.

Rules solve this by injecting conventions **at the point of generation**, not after. The feedback loop is:

```
Developer writes rule --> Claude loads rule on matching files --> Generated code conforms --> PR review validates
```

For architects designing AI-augmented workflows, rules offer three properties:

1. **Deterministic activation** -- glob matching is predictable; there is no ambiguity about which rules apply to which files.
2. **Composability** -- multiple rules can target the same glob. A `testing.md` rule and a `accessibility.md` rule can both match `**/*.test.tsx` and Claude sees the union.
3. **Version control** -- rules ship with the code. When conventions evolve, the rule update and the code update land in the same PR.

## Quick-Start Checklist

1. Create `.claude/rules/` in your project root.
2. Add a rule file with frontmatter (`description`, `globs`) and body (conventions as markdown).
3. Keep rules **prescriptive and concise** -- state what to do and what not to do. Avoid explanatory prose.
4. Map each convention to a concrete example from existing code so the rule is unambiguous.
5. Validate by asking Claude to generate a file matching the glob and inspecting conformance.
