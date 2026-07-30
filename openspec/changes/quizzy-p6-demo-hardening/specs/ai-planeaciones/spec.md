# Delta for AI Planeaciones

## ADDED Requirements

### Requirement: Generation Create Is Rate-Limited by Caller Scope, Independently of Monthly Quota

`LessonPlanViewSet.create` MUST enforce a scoped per-caller rate limit that is
evaluated before — and independently of — the workspace monthly generation quota.
Demo-guest callers MUST be limited to 3 generation requests per hour. Authenticated
teacher (non-demo) callers MUST be limited to 30 generation requests per hour. A
request rejected by this rate limit MUST return 429 and MUST NOT decrement or
consume any monthly quota count. The two scopes (demo-guest, teacher) MUST be
distinct; exhausting one MUST NOT affect the other.

#### Scenario: Demo guest hits the generation rate limit

- GIVEN a demo-guest caller has submitted 3 generation requests within one hour
- WHEN a fourth generation request is submitted
- THEN the response MUST be 429
- AND no new `LessonPlan` row MUST be created
- AND the caller's monthly quota `used` count MUST remain unchanged

#### Scenario: Teacher rate limit is separate from demo-guest limit

- GIVEN a teacher caller with a valid authenticated session
- WHEN the teacher submits up to 30 generation requests within one hour
- THEN all requests MUST be accepted (subject to quota and capability checks)
- AND the demo-guest rate counter MUST NOT be decremented

#### Scenario: Rate-limited 429 does not consume monthly quota

- GIVEN a demo-guest caller has reached the per-hour rate ceiling
- WHEN an additional generation request is rejected with 429
- THEN `GET /api/lesson-plans/quota/` MUST return the same `used` value as before the rejected request
