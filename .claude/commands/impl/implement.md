Implement a change following coding standards and checklists.

**Usage**: `/impl:implement <description, TRD reference, or ticket>`

## Steps

1. **Assess scope**:
   - If a TRD exists (from `/plan:plan`), follow it
   - If no TRD and the change touches 3+ layers or needs new tables, suggest running `/plan:plan` first
   - Otherwise, proceed directly
2. **Load checklists** from `skills/checklists/` based on what you're building:
   - Routes → security, api-contract, business-logic, data-integrity
   - SQL/migrations → security, schema
   - Temporal → temporal, business-logic, data-integrity
   - Models → api-contract
3. **Build** in dependency order (per `rules/coding-patterns.md`):
   - models → SQL → errors → activities → workflows → worker config → routes → tests
4. **Commit** — `git add <specific-files> && git commit`
   - Pre-commit hooks validate on staged files

## Rules

- Follow `rules/coding-patterns.md` for implementation order and forbidden patterns
- Load `skills/impl/<skill>.md` for domain-specific patterns when needed
- For large features with a TRD, execute layers sequentially with checkpoint commits
