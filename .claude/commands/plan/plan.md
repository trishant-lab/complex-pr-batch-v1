Create a Technical Requirements Document for a feature or change.

**Usage**: `/plan:plan <description or PRD>`

## Steps

1. **Analyze** — parse requirements, scan affected layers in `app/routes/`, `app/models/`, `app/sql/`, `app/cli/temporal/`
2. **Generate TRD** using `templates/trd.md`:
   - API design (routes, models)
   - Data model + migrations
   - Temporal workflows/activities (if needed)
   - Error handling
   - Testing strategy
3. **Generate implementation order** — following dependency flow from `rules/coding-patterns.md`
4. **Present** TRD to user

Save approved TRD to `docs/plans/<slug>-trd.md`.

## Rules

- Do not write any code — only produce the plan
- Wait for explicit user approval before handing off to `/impl:implement`
- For small changes (single file), a brief TRD is fine
