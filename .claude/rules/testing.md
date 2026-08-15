---
description: Test conventions for React component and utility tests
globs: ["**/*.test.tsx", "**/*.test.ts", "**/*.spec.tsx", "**/*.spec.ts"]
---

# Testing Conventions

## Test Naming

- Use `describe("<ComponentName>")` or `describe("<functionName>")` as the outer block.
- Name each `it()` by the behavior being tested, not the field or element: `it("renders post content and metadata")` not `it("renders the post name")`.
- One test per distinct behavior or edge case. Never split a single render into multiple tests that each check one field.

## Assertion Style

- Maximum 2 `expect` statements per test. If you need more, the test is covering multiple behaviors — split by behavior, not by field.
- Prefer role-based queries (`getByRole`, `getByLabelText`) over CSS class selectors (`querySelector(".className")`). CSS classes are implementation details.
- Do not test CSS class names, DOM structure, or element counts unless they represent a user-facing contract (e.g., accessibility roles, ARIA attributes).

## Fixture Usage

- Define one base fixture (`mockPost`, `mockUser`, etc.) per `describe` block at the top.
- Use spread syntax for edge-case variations: `{ ...mockPost, rating: 0 }`.
- Never create a full duplicate fixture just to change one field.
- Never write a test that merely re-renders with different data and re-asserts the same things — that tests the framework, not your code.

## What to Test

- **Do test**: rendered content, user interactions, conditional rendering, edge cases (empty strings, zero/null values, missing optional props), accessibility (roles, labels).
- **Do not test**: CSS class names, internal DOM structure, that React renders props (the framework already guarantees this), the same behavior with different data.
