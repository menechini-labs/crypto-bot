# Tasks: [FEATURE]

**For**: `specs/[###-feature]/spec.md`
**Date**: [DATE]
**Branch**: `[feature/...]`

**Input**: Feature specification and plan from `/specs/[###-feature]/`

## Format

```text
- [ ] [TaskID] [P?] [Story?] Description with file path
```

- Checkbox: ALWAYS start with `- [ ]`
- Task ID: T001, T002... sequential in execution order
- [P]: parallelizable (different files, no deps on incomplete tasks)
- [Story]: US1, US2... (user story phases only; setup/foundation/polish have none)

## Phase 1 — Setup

(Environment, scaffolding, branch creation)

## Phase 2 — Foundational

(Blocking prerequisites shared by all stories — e.g., centralized tokens)

## Phase 3+ — User Stories (priority order)

Each: story goal, independent test criteria, implementation tasks.

## Final Phase — Polish & Cross-Cutting

(States styling, lint/type, constitution restore, cross-surface review)
