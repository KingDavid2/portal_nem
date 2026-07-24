## Exploration: M5a Frontend Design System + Re-skin

### Current State
The frontend is a Next.js 16 App Router application using React 19, Tailwind CSS v4, Base UI, CVA, Lucide, and shadcn conventions. `globals.css` still uses neutral stock tokens and `layout.tsx` loads Geist; the authenticated shell is a max-width page with a horizontal navigation bar. Existing API modules, hooks, and CRUD/lesson-plan screens already provide working behavior, while the UI layer contains only Button, Input, Label, Table, and DataTable primitives.

`designs/teachers.pen` is the visual source of truth: it has no variables, but defines 10 reusable components and 25 screens using Inter, `#F7F7F9` page background, white surfaces, `#666CFF` primary, `#72E128` success, `#FF4D49` destructive, `#262B43` ink variants, and subtle card shadows. The reusable component structure matches the M5a scope: Nav Item, Stat Card, Status Chip, Estado Button, Avatar, Form Field, PDA Row, Paso Row, Contenido Card, and Momento Card.

### Affected Areas
- `frontend/src/app/globals.css` — replace neutral token values with the Pencil palette, expose success and shadow utilities, and keep Tailwind v4 CSS-first token registration.
- `frontend/src/app/layout.tsx` — replace Geist with Inter through `next/font/google` and update root metadata/language only where needed for the reskin.
- `frontend/src/app/(app)/layout.tsx` — preserve auth and active-workspace gates while replacing the top navigation with the 260px sidebar shell.
- `frontend/src/components/ui/` — add `card`, `nav-item`, form/status/avatar/stat/progress primitives and composite lesson-plan cards following existing Base UI/CVA conventions.
- `frontend/src/app/login/page.tsx` and `frontend/src/app/(app)/{students,schools,school-years,groups,planeaciones}/` — re-skin existing screens and factor the shared cascading-select presentation without changing request behavior.
- `frontend/src/lib/api/*` — protected boundary: no public API signatures, headers, fallback strings, query parameters, polling timeout, or error contracts may change.
- `backend/` — explicitly out of scope and must remain unchanged.

### Approaches
1. **Token-first, component-first chained migration** — implement D1–D5 foundation deliveries, then migrate login, CRUD, and lesson-plan screens in D6–D8.
   - Pros: Matches dependency order, keeps every delivery below the 400-line review budget, and prevents bespoke reskin styles.
   - Cons: Requires temporary coexistence of old and new screen styling while deliveries land.
   - Effort: Medium.

2. **Screen-by-screen restyling before extraction** — reskin each page directly, then extract common patterns afterward.
   - Pros: Faster first visible page.
   - Cons: Duplicates styles, creates refactor churn, and violates the design-system objective for M6–M9.
   - Effort: High.

### Recommendation
Use the token-first, component-first chained migration. Convert the hardcoded Pencil values to semantic CSS tokens in D1, introduce the sidebar and reusable primitives before screen work, and compose the two composite cards from PDA/Paso rows. Preserve page hooks, API calls, and all data-state logic; M5a is a visual/system extraction, not a behavior or backend change.

### Risks
- Replacing the app shell can accidentally bypass or regress authentication/workspace gating; retain the current gate branches unchanged and alter only the post-gate composition.
- Tailwind v4 is CSS-first, so tokens belong in `@theme inline`/CSS variables rather than a Tailwind configuration file.
- The design uses hardcoded colors and no Pencil variables; the implementation must establish a semantic token layer without treating the `.pen` file as code.
- Composite cards and lesson-plan loading/generation states can exceed a delivery budget if not kept to D4/D5/D8 boundaries.
- Login localization must not alter authentication behavior; only presentation and Spanish copy are in scope.
- M5b auth screens and the rich curriculum picker remain out of scope because their backend/data dependencies do not exist.

### Ready for Proposal
Yes. The scope, target design components, delivery sequence, protected API boundary, and verification commands are sufficiently defined. The proposal should retain the eight D1–D8 deliveries, explicitly exclude M5b and the rich picker, and require Pencil MCP visual comparison for each re-skinned delivery.
