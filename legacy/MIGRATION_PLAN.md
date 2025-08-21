# Migration Plan

Source repo modules → new locations:

- `scraper/wiktionary_*` → `apps/intake-worker/sources/wiktionary/`
- `subagents/phonetics_*` → `apps/profile-builder/` and `packages/utils/`
- `subagents/grammar_*` → `apps/text-lane/` enrichment step
- `database/schema.sql` → `infra/db/migrations/`
- `utils/*` → `packages/utils/`

Process:
1) Copy code into `legacy/` for review.
2) Move file by file into the target location.
3) Add tests and delete legacy copy.
