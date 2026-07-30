# Demo Mode Specification

## Purpose

Defines the anonymous demo surface: Redis-backed throttle counters, per-view rate
limits, session TTL + leaf-first reap, DEMO_DEPLOY hosting-posture gate, and
showcase persona seed contracts.

## Requirements

### Requirement: Redis Cache Backend Is Required Before Any Throttle Counter Is Active

The system MUST configure a Redis `CACHES` backend before any rate-limit view is
served. A LocMemCache or in-process default cache MUST NOT be used for throttle
counters when multiple gunicorn workers or Celery processes are active, because
per-process counters cannot enforce a shared rate.

#### Scenario: Rate limit is shared across workers

- GIVEN the demo surface runs with two or more gunicorn workers
- WHEN two requests from the same IP arrive on different workers
- THEN both MUST decrement from the same shared Redis counter
- AND the per-IP limit MUST be enforced across all workers

#### Scenario: Missing Redis cache is surfaced at startup

- GIVEN `CACHES` defaults to `LocMemCache` and demo throttle views are registered
- WHEN the application boots in a multi-process context
- THEN the system SHOULD emit a configuration warning or error

### Requirement: Anonymous Demo Surface Has Independent Per-View Rate Limits

The system MUST apply a per-IP `AnonRateThrottle` to the three demo views with
independent scopes and the following default ceilings: `personas` — 60 req/h/IP;
session `create` — 5 req/h/IP; session `poll` — 120 req/h/IP. Exhausting one
scope MUST NOT consume or affect another scope's counter.

#### Scenario: Repeated session create is rejected at the limit

- GIVEN a caller has POSTed to the demo session-create endpoint 5 times within one hour from one IP
- WHEN the caller attempts a sixth POST
- THEN the response MUST be 429
- AND no new demo tenant MUST be provisioned

#### Scenario: Poll exhaustion does not force create to 429

- GIVEN a caller has exhausted the `poll` scope limit
- WHEN the caller submits a session `create` request
- THEN the `create` counter MUST be evaluated independently
- AND the `create` request MUST NOT be rejected solely due to poll exhaustion

### Requirement: Demo Session TTL Is Enforced and Sessions Are Reaped Leaf-First Under Workspace Scope

The system MUST support a `DEMO_SESSION_TTL_HOURS` setting (default: 24). A
scheduled Celery-beat task MUST reap `DemoSession` rows whose
`created_at` + TTL has elapsed, running at most once per hour when `DEMO_DEPLOY`
is on. Reap MUST operate inside the session's workspace scope and MUST NOT touch
rows outside that workspace. Deletion MUST proceed in this order to satisfy
`PROTECT` foreign-key constraints:
`LessonPlan` → `Student` → group/ciclo/school → `Workspace` → demo `User` → `DemoSession`.

#### Scenario: Expired teacher_full-shaped tenant is removed without ProtectedError

- GIVEN a `DemoSession` older than `DEMO_SESSION_TTL_HOURS` whose workspace contains `LessonPlan` rows referencing `Group` rows
- WHEN the reap task runs
- THEN all rows MUST be deleted in leaf-first order without raising a constraint error
- AND the `DemoSession` row MUST no longer exist

#### Scenario: Unexpired session is left untouched

- GIVEN a `DemoSession` whose `created_at` + TTL has not yet elapsed
- WHEN the reap task runs
- THEN the session and its workspace rows MUST remain unmodified

#### Scenario: Reap does not touch rows outside the expired session's workspace

- GIVEN two demo workspaces exist; one is expired, one is not
- WHEN the reap task runs
- THEN only the expired session's workspace rows MUST be deleted
- AND the active workspace MUST remain intact

### Requirement: DEMO_DEPLOY Flag Enforces Hardened Hosting Posture

The system MUST support a `DEMO_DEPLOY` boolean setting (default: `False`). At
application startup, if `DEMO_DEPLOY` is `True` and `DEBUG` is also `True`, the
system MUST abort with an explicit error and MUST NOT serve any request. When
`DEMO_DEPLOY` is on, Celery beat MUST be treated as a required process. The
required hosting posture MUST be documented in `.env.example` and in the
roadmap's open Q4 resolution.

#### Scenario: DEMO_DEPLOY + DEBUG=True fails boot

- GIVEN `DEMO_DEPLOY=True` and `DEBUG=True`
- WHEN the application process starts
- THEN startup MUST be aborted with a descriptive error message
- AND no HTTP request MUST be served

#### Scenario: DEMO_DEPLOY + DEBUG=False boots normally

- GIVEN `DEMO_DEPLOY=True` and `DEBUG=False`
- WHEN the application process starts
- THEN the application MUST reach a serving state without error

### Requirement: Showcase Persona Seeds P1 Provenance Fields With Zero LLM Calls

The `showcase` persona MUST be seeded from a fixture that writes `LessonPlan` rows
directly, without invoking the LLM. Each seeded row MUST carry `provider`,
`model_name`, a tokens usage metric, and `generated_at`. The columns `cost_micros`
and `duration_ms` MUST NOT be required or populated by the seed. The persona
renderer MUST display a grounding indicator (✓ when no hallucinated PDAs are
flagged, ⚠ when one or more are flagged) and the provenance fields for each plan.

#### Scenario: Showcase renders grounding and provenance without generations

- GIVEN the `showcase` persona is provisioned from its fixture seed
- WHEN a visitor loads the showcase view
- THEN each plan MUST show a grounding indicator and `provider`, `model_name`, `generated_at`
- AND no LLM call MUST have been made during provisioning

#### Scenario: Seeded plans are in ready status

- GIVEN the showcase provisioner has completed
- WHEN the `LessonPlan` rows for the showcase workspace are inspected
- THEN all seeded rows MUST have `status=ready`
- AND `cost_micros` and `duration_ms` MUST be absent or null
