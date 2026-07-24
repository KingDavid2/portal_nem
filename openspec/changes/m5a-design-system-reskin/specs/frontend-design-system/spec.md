# Frontend Design System Specification

## Purpose

Define the `teachers.pen` system without changing behavior, API contracts, or backend code.

## Requirements

### Requirement: Semantic Tokens and Typography
The frontend MUST expose CSS-first Tailwind v4 semantic tokens for background `#F7F7F9`, card/popover `#FFFFFF`, primary `#666CFF` with white foreground, success `#72E128`, destructive `#FF4D49`, ink/border variants, specified radii, and card shadow. The application MUST use Inter.

#### Scenario: Token-driven styling
- GIVEN a shared primitive is rendered
- WHEN it needs a color, radius, or shadow
- THEN it resolves through semantic tokens
- AND it does not require a bespoke Pencil hex value

#### Scenario: Inter application
- GIVEN an application page renders
- WHEN typography inherits from the root layout
- THEN its font family is Inter

### Requirement: Authenticated Sidebar Shell
The authenticated shell MUST render a 260px left sidebar and Nav Item after existing auth and active-workspace gates pass. It MUST preserve their outcomes and navigation destinations.

#### Scenario: Authorized workspace user
- GIVEN an authenticated user with an active workspace
- WHEN an app route renders
- THEN the sidebar shell and navigation items display

#### Scenario: Missing gate prerequisite
- GIVEN the auth or workspace gate does not pass
- WHEN an app route renders
- THEN its gate branch is preserved
- AND the sidebar does not bypass it

### Requirement: Reusable Pencil Components
The system MUST provide Card, Nav Item, Form Field, Avatar, Status Chip, Stat Card, Estado Button, PDA Row, Paso Row, Contenido Card, and Momento Card. Contenido Card and Momento Card MUST compose row primitives and accept slots rather than duplicate row presentation.

#### Scenario: Component coverage
- GIVEN a screen needs a listed Pencil pattern
- WHEN it imports the shared component
- THEN that component is available from the UI layer

#### Scenario: Composite composition
- GIVEN a Contenido Card or Momento Card presents PDA or paso data
- WHEN it renders
- THEN it uses the corresponding shared row primitive

### Requirement: Existing Screen Re-skins
Login, students, schools, school-years, groups, and planeaciones MUST use the shared system while preserving routes, data states, and request behavior. Login copy MUST be Spanish. Planeaciones MUST retain its simple generation form and MUST NOT add the rich curriculum picker.

#### Scenario: Existing CRUD interaction
- GIVEN a user performs an existing CRUD or cascading-select interaction
- WHEN the re-skinned screen is used
- THEN the same request and state behavior occurs

#### Scenario: Lesson-plan generation
- GIVEN a user opens the generation form
- WHEN the re-skinned screen renders
- THEN the simple form remains available
- AND no curriculum-backed picker is shown

### Requirement: Protected Contract Boundaries
M5a MUST NOT modify backend files or add backend/auth capability. It MUST NOT change public APIs in `frontend/src/lib/api/*`, including signatures, the Spanish fallback string, `?format=docx`, the 3000ms poll constant, CSRF, `X-Workspace-Id`, or `MissingWorkspaceError` behavior.

#### Scenario: Contract regression check
- GIVEN the M5a change is inspected
- WHEN API and backend diffs are evaluated
- THEN protected frontend API behavior is unchanged
- AND the backend diff is empty

### Requirement: Visual and Delivery Gates
Each D1–D8 delivery MUST be dependency ordered and contain no more than 400 changed lines: D1 tokens/Inter; D2 sidebar/Nav Item; D3 Card/Form Field/Avatar/Status Chip; D4 Stat Card/Estado Button/PDA Row/Paso Row; D5 composite cards; D6 login; D7 school CRUD; D8 planeaciones. Each re-skin MUST be compared with its `teachers.pen` frame and pass frontend tests, lint, and production build.

#### Scenario: Slice acceptance
- GIVEN any D1–D8 delivery is ready for review
- WHEN its diff and verification are checked
- THEN it is within 400 changed lines, respects dependencies, and passes required checks

#### Scenario: Visual comparison
- GIVEN a re-skinned screen delivery runs
- WHEN its screenshot is compared to the Pencil frame
- THEN material drift is resolved with shared primitives
- AND another screen needs no bespoke restyling
