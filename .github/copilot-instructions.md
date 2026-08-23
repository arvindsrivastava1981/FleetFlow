# VahanKhata Agent Rules

## Routing and Token Budget
- Read `APP_MINDMAP.md` first. Use exact paths and architecture; do not map the repository broadly.
- Form one local hypothesis and one falsifiable check from the nearest implementation, then edit.
- Read only relevant sections. Do not reread unchanged files or repeat searches after finding the needed path or symbol.
- Use one focused edit, followed immediately by one focused validation. Expand scope only when that check gives new evidence.
- Never repeat the same tool call, command, or edit after an unchanged failure. Make one local repair and rerun once; then stop and report the blocker.
- Keep diffs minimal: normally one file and under 100 changed lines. Do not reformat unrelated code.
- Skip greetings, progress narration, full-file dumps, and speculative alternatives. Final responses contain only result, validation, and blockers.

## Repository
- Python 3.12, FastAPI, uvicorn, psycopg2, reportlab, and python-dotenv.
- Active app: `fleet  flow_interactive_demo.py`; frontend HTML is server-rendered with Tailwind CDN.
- PostgreSQL/Neon only. Use `psycopg2`, `%s` placeholders, and `fmt_dt(dt)` for timestamps.
- No ORM, Alembic, SQLite, or application DDL. Schema changes require `database/schema.sql`, `/database/incremental.sql`, and `APP_MINDMAP.md` for route/schema/core-flow changes.
- Do not add dependencies without approval or leave placeholders/TODOs.
- Preserve user changes. Do not run, stage, push, commit, reset, or suggest Git commands.

## Editing and Validation
- Verify the target path exists before editing; use `apply_patch` for manual changes.
- Follow existing style. Add comments only for non-obvious logic; default to ASCII.
- Prefer a narrow syntax check or focused test. Use compact output flags where supported, such as `pytest -q --tb=line`.
- Do not start persistent servers or watchers. Report when required validation cannot run.
