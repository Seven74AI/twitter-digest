# ADR-003: Multi-profile kanban teams for autonomous projects

**Status:** Accepted
**Date:** 2026-05-17
**Deciders:** @Seven74AI

## Context

Projects need autonomous, self-correcting teams that can work without constant human oversight. The pattern: a planner decomposes work, coders implement, reviewers catch bugs and spawn follow-up tasks.

Options:
- Single profile doing everything → too slow, no quality gate
- Manual task assignment → doesn't scale
- Kanban with dispatcher + dedicated profiles → self-running

## Decision

Each project gets a 3-profile team (planner, coder, reviewer) registered as Hermes profiles. The kanban dispatcher spawns workers when tasks hit `ready`. Review-required creates review tasks automatically.

Example teams:
- `twitter-planner / twitter-coder / twitter-reviewer`
- `music-planner / music-coder / music-reviewer`

## Consequences

**Easier:**
- Self-correcting: reviewer finds bugs → auto-creates fix tasks
- No context accumulation (each task = fresh session)
- Survives gateway restarts (tasks persist in SQLite)

**Harder:**
- Requires gateway running for dispatcher
- OOM killer can kill workers if no swap (see Journal: OOM/swap)
- Profile model costs scale with concurrency
