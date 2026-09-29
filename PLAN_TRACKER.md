# Vachan — Plan Tracker

The running log of implementation work. It is the single source of truth for **what has been attempted, what happened, and what is safe to do next.** Tasks are drawn from the build order in [`vachan-plan.md`](vachan-plan.md) §64 (phases P0–P9) and its feature register (§15).

> New here? Read [`AGENTS.md`](AGENTS.md) first, then this file.

---

## How this works (read before touching anything)

1. **One task in flight at a time.** Never start a second task while one is `IN PROGRESS`. The whole point is a clean, reviewable trail.
2. **A task starts only after it is marked `GO`.** Proposing a task (`PROPOSED`) is not permission to build it. Work begins **only** once the owner has set the status to `GO` in this file. If you believe the next task is obvious, still wait for `GO`.
3. **Log as you go — especially the messy parts.** When a task is attempted, capture in its entry:
   - what was actually done (vs. what the plan said);
   - anything that **couldn't** be done, and why;
   - any **shortcut** taken (and the debt it leaves);
   - any **alternative** discovered during implementation that differs from the plan — flag it so the plan/`AGENTS.md` can be updated;
   - blockers, open questions, and follow-ups.
4. **Close before you open.** A task must reach `DONE` (or `BLOCKED`/`DEFERRED` with a reason) before the next one is proposed and given `GO`.
5. **Deviations are decisions.** If implementation reveals a better path than `vachan-plan.md`, record it here and note whether the plan was updated. The tracker is allowed to overrule the plan — but only in writing.

## Status legend

| Status | Meaning |
|---|---|
| `PROPOSED` | Written up, awaiting go-ahead. **Do not build.** |
| `GO` | Approved to start. Exactly one task should be `GO`/`IN PROGRESS` at a time. |
| `IN PROGRESS` | Being worked on now. |
| `DONE` | Complete; exit criteria met (note which, from the plan). |
| `BLOCKED` | Cannot proceed; reason + what's needed to unblock recorded. |
| `DEFERRED` / `CUT` | Intentionally postponed or dropped (e.g. via the §65 cut line); reason recorded. |

## Entry template (copy this per task)

```
### T<n> — <short title>   ·   <plan ref, e.g. P1 / F3>
- Status: PROPOSED | GO | IN PROGRESS | DONE | BLOCKED | DEFERRED
- Owner: <name>            Dates: opened <YYYY-MM-DD> · updated <YYYY-MM-DD>
- Goal: <one line — what "done" means, tied to the plan's exit criteria>
- Done / changed: <what was actually built>
- Couldn't do / shortcuts: <gaps, debt, anything skipped>
- Alternative found: <if implementation diverged from the plan — and was the plan updated?>
- Blockers / follow-ups: <what's next or what's needed>
```

---

## Current task

**None.** Nothing is `GO` yet. The first task to propose is **P0 — walking skeleton** (`vachan-plan.md` §64.2). Propose it here, get a `GO`, then begin.

## Task log

*(empty — the first entry goes here once P0 is proposed)*
