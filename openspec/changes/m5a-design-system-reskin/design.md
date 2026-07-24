# Design: M5a Frontend Design System and Re-skin

## Technical Approach

Implement the `frontend-design-system` spec as eight dependency-ordered slices. `teachers.pen` remains the visual authority; React components translate its hardcoded values into semantic tokens and composable contracts. Existing hooks, mutations, routes, and data-state branches remain page-owned.

## Architecture Decisions

| Decision | Choice | Alternatives / rationale |
|---|---|---|
| Tailwind v4 tokens | Keep runtime values in `:root` and register utilities through `@theme inline`: `background` `oklch(0.9767 0.0026 286.35)`, `card/popover` white, `primary` `oklch(0.6082 0.2141 276.21)`, `success` `oklch(0.8120 0.2310 136.53)`, `destructive` `oklch(0.6724 0.2151 26.15)`, and ink `oklch(0.2960 0.0443 274.39)` with Pencil alpha levels. Add `--color-success`, `--shadow-card`, existing radius aliases, and sidebar aliases. | A Tailwind config is invalid for this CSS-first setup; raw hex in components would defeat semantic theming. |
| Typography | Load `Inter` with `next/font/google`, expose its variable as `--font-inter`, and map both `--font-sans` and `--font-heading` to it. Retain Geist Mono only if code typography still uses it. | CSS CDN/import adds a runtime request and loses Next font optimization. |
| Shell gates | Keep the current loading, unauthenticated, and missing-workspace early returns before shell composition. Only the successful branch becomes `aside[w-260] + main`; it includes the existing `WorkspaceSwitcher`, logout affordance, and unchanged `NAV_ITEMS`. | Wrapping gates inside the shell risks exposing application navigation before authorization/workspace readiness. The home switcher remains the prerequisite fallback. |
| Components | Follow `base-nova`: Base UI for interactive controls, semantic HTML for display-only pieces, CVA for state/size variants, and `cn()` for overrides. | Radix is not installed; monolithic screen components would duplicate presentation. |
| Composite ownership | `ContenidoCard` composes `PdaRow`; `MomentoCard` composes `PasoRow` and accepts header/action/body slots. Pages adapt API-shaped data into props. | Passing API models into UI components would couple the design system to transport contracts. |

## Component Contracts

All primitives forward `className` and relevant native attributes.

```ts
type Tone = "brand" | "success" | "neutral" | "danger";
type NavItemProps = { href: string; label: string; icon: LucideIcon; active?: boolean };
type FormFieldProps = { label: string; required?: boolean; help?: string; error?: string; children: ReactNode };
type StatusChipProps = { tone: Tone; children: ReactNode };
type AvatarProps = { name: string; size?: "sm" | "md" };
type StatCardProps = { label: string; value: ReactNode; caption?: string; icon?: ReactNode; tone?: Tone };
type EstadoButtonProps = ComponentProps<typeof Button> & { selected?: boolean };
type PdaRowProps = { children: ReactNode; featured?: boolean; selected?: boolean; onSelectedChange?: (v: boolean) => void };
type PasoRowProps = { number: number | string; children: ReactNode };
type ContenidoCardProps = { title: ReactNode; selected?: boolean; children: ReactNode; actions?: ReactNode };
type MomentoCardProps = { title: ReactNode; subtitle?: ReactNode; status?: ReactNode; actions?: ReactNode; children: ReactNode };
```

## File and Delivery Plan

| Slice | Changes |
|---|---|
| D1 | Modify `frontend/src/app/globals.css` and `frontend/src/app/layout.tsx`; add token/font RED assertions. |
| D2 | Modify `(app)/layout.tsx`, `workspace-switcher.tsx`; create `ui/nav-item.tsx`; test all three gates and active navigation. |
| D3 | Create `ui/{card,form-field,avatar,status-chip}.tsx` plus render/variant tests. |
| D4 | Create `ui/{stat-card,estado-button,pda-row,paso-row}.tsx` plus interaction/variant tests. |
| D5 | Create `ui/{contenido-card,momento-card}.tsx`; tests prove row composition and slots. |
| D6 | Re-skin `login/page.tsx` as the 460px Spanish card without changing `login(email,password)` or redirect behavior. |
| D7 | Create `components/school-context-filters.tsx`; migrate students, schools, school-years, and groups presentation while pages retain queries, selection resets, mutations, and errors. |
| D8 | Migrate planeaciones list/statuses, simple `generate-form`, detail/generating states, and `proyecto-viewer`; keep the current payload, polling, export, regenerate, and invented-PDA warning flows. |

## Verification

Each slice starts with a failing Vitest/jsdom contract or render test, then runs `npm test`, `npm run lint`, and `npm run build`. Before accepting D6–D8, compare running-screen screenshots with Pencil nodes `mhV91`, `al73`/`qeMf8`, `j8q40`, `FzQku`, and `WDWqT`; verify tokens/components eliminate bespoke Pencil hex values. Enforce `git diff --numstat` at ≤400 changed lines per slice, empty `backend/` diff, and unchanged `frontend/src/lib/api/*`. Final backend guard: `uv run manage.py makemigrations --check --dry-run`.

## Threat Matrix

N/A — no routing, shell-command, subprocess, VCS/PR automation, executable classification, or process-integration boundary is introduced.

## Migration / Rollout

No data migration or flag. Land D1–D8 in order; rollback is per-slice revert.

## Protected Boundaries

Do not modify backend/auth capability, API module public signatures, Spanish fallback text, `?format=docx`, the 3000ms polling constant, CSRF, `X-Workspace-Id`, or `MissingWorkspaceError`. M5b auth screens and the curriculum-backed picker remain excluded.

## Open Questions

None.
