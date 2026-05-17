# ADR-002: Triple-tag tweets with Themes, Signal, Source

**Status:** Accepted (1-week trial)
**Date:** 2026-05-17
**Deciders:** @Seven74AI

## Context

Twitter digests needed categorization. Three dimensions emerged:

1. **Theme** — what the tweet is about (Agent UX, Bitcoin, TypeScript…)
2. **Signal** — what type of information it carries (🔴 Signal, 🟡 Insight, 🟢 Discussion, ⚪ Link/Ref)
3. **Source** — who is speaking and in what role (Builder, Curator, Analyst, Community)

## Decision

Tag every tweet with all three dimensions for a 1-week trial. After testing, pick the most useful dimension(s) based on actual usage patterns.

Each dimension serves a different reader need:
- **Theme** → "show me everything about Bitcoin"
- **Signal** → "show me only announcements"
- **Source** → "show me what builders are saying"

## Consequences

**Easier:**
- Readers can filter by what they care about
- GitHub Pages supports all three filter axes
- Notion properties map naturally to these dimensions

**Harder:**
- LLM tagging cost (3 decisions per tweet)
- Tag granularity debates (is this "Insight" or "Discussion"?)
- Maintenance burden if dimensions evolve
