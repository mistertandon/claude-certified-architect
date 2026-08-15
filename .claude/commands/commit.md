# Smart Commit

Analyze the current working tree changes and create a well-crafted commit. Do NOT push to the remote.

## Steps

1. **Gather context** — run these in parallel:
   - `git status` (never use `-uall`) to see staged, unstaged, and untracked files.
   - `git diff` and `git diff --cached` to see the actual changes.
   - `git log --oneline -10` to learn the repo's commit message style.

2. **Analyze the changes** — determine:
   - What kind of change this is: feature, fix, refactor, test, docs, chore, style, perf, ci, build.
   - Which area of the codebase is affected.
   - The intent behind the changes (the "why", not just the "what").

3. **Stage files** — add all relevant changed and untracked files by name. Do NOT use `git add -A` or `git add .`. Exclude files that look like they contain secrets (`.env`, credentials, tokens).

4. **Draft a commit message** following these rules:
   - Use conventional commit format: `type(scope): description`
   - First line under 72 characters, imperative mood ("add", "fix", "update", not "added", "fixed", "updated").
   - If the change is non-trivial, add a blank line then a body with bullet points explaining what and why.
   - End with `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`.

5. **Commit** — create the commit using a HEREDOC for the message. Then run `git status` to confirm success.

6. **Report** — show the user the commit hash, message, and files included. Remind them the commit was NOT pushed.

## Important

- Do NOT push to the remote. The user will push manually.
- Do NOT amend any existing commit.
- Do NOT use `git add -A` or `git add .` — stage files by name.
- If there are no changes to commit, say so and stop.
- If you spot files that may contain secrets, warn the user and exclude them.
