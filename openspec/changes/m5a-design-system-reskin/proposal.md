# Proposal: M5a Frontend Design System and Re-skin

## Intent

Replace thin, inconsistent styling with the reusable visual system in `designs/teachers.pen`. Existing authentication, workspace, CRUD, and lesson-plan behavior remains unchanged while later milestones gain shared primitives.

## Scope

### In Scope
- Extract semantic brand tokens, Inter typography, shadows, and radii using Tailwind v4 CSS-first conventions.
- Replace the authenticated top navigation with a 260px sidebar while preserving auth and workspace gates.
- Build the 10 Pencil components plus `Card`, then re-skin existing screens.
- Deliver exactly eight dependency-ordered, chained slices, each at or below 400 changed lines:
  - D1 tokens + Inter; D2 sidebar + Nav Item; D3 Card/Form Field/Avatar/Status Chip; D4 Stat Card/Estado Button/PDA Row/Paso Row.
  - D5 Contenido Card/Momento Card; D6 login; D7 school CRUD; D8 planeaciones.

### Out of Scope
- M5b signup, email verification, invitation acceptance, or any new auth/backend capability.
- The curriculum-backed rich content/PDA picker; M5a retains the simple generation form.
- Changes to backend code, API behavior, data models, or contracts in `frontend/src/lib/api/*`.

## Capabilities

### New Capabilities
- `frontend-design-system`: Semantic visual tokens, reusable UI primitives, sidebar shell, and faithful composition of existing screens from the Pencil source of truth.

### Modified Capabilities
- None. Existing frontend, authentication, school-structure, and planeaciones requirements remain behaviorally unchanged.

## Approach

Use the token-first, component-first D1–D8 chain. Establish foundations before migrating screens, follow existing Base UI/`base-nova`, CVA, and `cn()` patterns, and compare every visual delivery against `teachers.pen` through Pencil MCP. Preserve hooks and data-state logic.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `frontend/src/app/{globals.css,layout.tsx}` | Modified | Brand tokens and Inter |
| `frontend/src/app/(app)/layout.tsx` | Modified | Sidebar shell with unchanged gates |
| `frontend/src/components/ui/` | New/Modified | Shared primitives and composites |
| `frontend/src/app/login/`, `frontend/src/app/(app)/` | Modified | Existing screen re-skins |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Auth/workspace regression | Medium | Preserve gate branches and protected API contracts |
| Styling drift or oversized slices | Medium | Pencil comparison and per-delivery 400-line gate |
| Tailwind/Base UI mismatch | Low | Use CSS-first tokens and existing conventions |

## Rollback Plan

Revert only the affected D1–D8 delivery commit, preserving earlier foundation slices. No migration or backend rollback is required.

## Dependencies

- `designs/teachers.pen` and Pencil MCP inspection.
- Existing frontend stack and behavior.

## Success Criteria

- [ ] All D1–D8 slices stay within 400 changed lines and pass frontend tests, lint, and build.
- [ ] Re-skinned screens match Pencil references and use shared primitives without bespoke restyling.
- [ ] `frontend/src/lib/api/*` contracts and all backend files remain unchanged.
