# Constitution

**Version**: 1.0.0
**Status**: Ratified
**Project**: crypto-bot

## Principles

### I. Research-First
Before proposing or implementing any change, understand the actual codebase,
conventions, and constraints. Read the relevant files; do not speculate about
unread code. Use search/explore agents for discovery, and external references
(librarian/Context7) for unfamiliar libraries.

### II. Specify & Plan
Every non-trivial feature flows through the Spec Kit pipeline:
`specify → plan → tasks → implement → converge`. A feature is not started
without a spec and an approved plan.

### III. Task Decomposition
Break work into small, independently testable tasks (max ~3 conceptual steps
each). Track progress with an explicit todo list. Multi-step work is never
"black box".

### IV. Test-Driven Development (TDD)
Write or extend tests that encode the requirement before/with implementation.
Existing automated suites must remain green after changes. Do not delete failing
tests to make a build pass.

### V. Specification-Driven Development (SDD)
Implementation follows the spec's user stories, functional requirements (FR-*),
and success criteria (SC-*). Every FR/SC maps to a verifiable outcome.

### VI. Coding Discipline
Prefer the smallest correct change. Match existing project patterns. No new
dependencies without reason. No premature abstraction; duplication > premature
abstraction. No `as any` / `@ts-ignore` type suppression.

### VII. Linter & Safety Gate
Code must pass the project linter (Biome for the dashboard, Ruff for Python)
and type checks (pyright) with no new errors. Validate at system boundaries;
trust framework guarantees internally.

## Workflow (GitFlow)

- `main`/`master` = production. `develop` = integration.
- Features branch from `develop` as `feature/<name>`.
- Fixes branch as `hotfix/<name>`; chores as `chore/<name>`.
- No commit or push without explicit user request. No auto-merge.
- PRs target `develop`; review before merge.

## Quality Gates (non-negotiable)

1. Tests pass (no regression).
2. Linter clean (no new violations).
3. Spec requirements satisfied (FR/SC verified).
4. Changes are minimal and intent-preserving.
