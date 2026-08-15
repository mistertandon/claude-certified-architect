# API Routes

Conventions for all Next.js API route handlers under `src/app/api/`.

## REST Endpoint Naming

- Use **plural nouns** for resource collections: `/api/posts`, `/api/genres`.
- Use **kebab-case** for multi-word segments: `/api/post-categories`, not `/api/postCategories`.
- Nest sub-resources under their parent: `/api/posts/[id]/comments`.
- No trailing slashes. No verbs in paths — the HTTP method conveys the action.

## Route Handler Structure

- One `route.ts` per directory. Export only the HTTP methods the endpoint supports (`GET`, `POST`, `PUT`, `DELETE`).
- Use `NextResponse.json()` for all responses.

## Post Object Structure

```json
{
  "id": 1,
  "name": "Getting Started with React Hooks",
  "category": "Frontend",
  "author": "Alice Johnson",
  "rating": 5,
  "lastUpdateTime": "2026-03-15T14:20:00Z"
}
```

| Field            | Type     | Description                        |
|------------------|----------|------------------------------------|
| `id`             | `number` | Unique identifier                  |
| `name`           | `string` | Post name                          |
| `category`       | `string` | Topic category (e.g. "Frontend")   |
| `author`         | `string` | Author's full name                 |
| `rating`         | `number` | Rating from 1–5                    |
| `lastUpdateTime` | `string` | ISO 8601 last-updated timestamp    |

## Response Schema

All JSON responses follow this shape:

**Success** — return the resource or array directly:
```json
{ "id": 1, "title": "..." }
```
or
```json
[{ "id": 1, "title": "..." }]
```

**Error** — return an `error` string with the appropriate HTTP status:
```json
{ "error": "Failed to fetch posts" }
```

Status codes: `200` success, `201` created, `400` bad request, `404` not found, `500` server error.

## Caching

Set `Cache-Control` headers on GET responses for public data:
```
Cache-Control: public, s-maxage=7200, stale-while-revalidate=3600
```

Omit caching headers on mutations and authenticated endpoints.

## Validation

- Validate request bodies and query params at the handler boundary before passing to lib functions.
- Return `400` with a descriptive `error` message for invalid input.
