# ADR-001: Use Notion for digests and journal

**Status:** Accepted
**Date:** 2026-05-17
**Deciders:** @Seven74AI

## Context

We needed persistent, searchable storage for:
1. Daily Twitter digests (Dev/AI + Crypto lists)
2. Weekly Hermes management journal

Options considered:
- **Notion** — database + API + views (calendar, filter, search)
- **Obsidian** — local markdown, strong search but sync friction
- **Plain markdown on GitHub** — simple but no structured queries

## Decision

Use **Notion** as the central knowledge hub under a "Hermes Sevenai" root page. Each vertical (digests, journal) gets its own inline database with typed properties.

GitHub Pages handles public-facing timeline display. Notion is the system of record.

## Consequences

**Easier:**
- Filter by date, category, impact, tags
- Calendar view for daily digests
- Full-text search across all entries
- API-driven writes from cron jobs

**Harder:**
- Notion API v2025-09-03 has quirks (data_source vs database, property names)
- Internal integrations can't create workspace-level pages
- No offline access
