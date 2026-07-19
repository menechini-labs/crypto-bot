---
status: blocked
---

# BMad Dev Auto Result

Status: blocked
Blocking condition: unclear intent

## Summary

Invoked `bmad-dev-auto` against project `crypto-bot`. Activation completed:
- Workflow block resolved (no prepend/append steps, no custom overrides).
- Config loaded: `communication_language=English`, `document_output_language=English`, `user_skill_level=intermediate`, `project_name=crypto-bot`.
- No `**/project-context.md` found; loaded nothing as persistent fact.
- Git: clean tree on branch `feature/epics-and-stories`.

## Why blocked

Step 01 (clarify-and-route) requires the invocation prompt to carry enough intent
to identify what to implement (a spec file with recognizable status, a story/ticket
ID, a file path, or a concrete description). The supplied prompt was:

> "foi aplicado não backend e no frontend as 1 etapas" (plus the instruction to use this skill)

This is a garbled fragment with no actionable target. No spec file, story number,
ticket ID, or implementable description was provided. Per step-01 rules, the workflow
HALTs with `blocked` / `unclear intent`.

## What I need to proceed

One of:
1. A spec file path with a recognizable `status` frontmatter (`draft`, `ready-for-dev`, `in-progress`, `in-review`, `done`), OR
2. A story/ticket identifier (e.g. `story-1-3`, `gh-47`), OR
3. A concrete description of the change to implement (backend/frontend, which feature, which epic).

Note: the user's message mentioned "backend" and "frontend" and "1 etapa" — if the intent
is to apply a change to one or both, please clarify the exact change and target so the
workflow can route correctly.
