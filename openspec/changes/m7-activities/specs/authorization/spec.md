# Delta for authorization

## ADDED Requirements

### Requirement: Grades Endpoints Map Custom Actions to Capabilities

Grades views MUST use `WorkspacePermission` `capability_map`: `list`/`retrieve`/`matrix`→`view_workspace`; `create`/`bulk`→`edit_content`. Literal `matrix`/`bulk` MUST NOT reach `has_permission`.

#### Scenario: Matrix/bulk mapping

- GIVEN actions `matrix` and `bulk`
- WHEN permission evaluates
- THEN caps MUST be `view_workspace` and `edit_content` respectively

#### Scenario: Cap denials

- GIVEN Membership lacking `edit_content` or `view_workspace`
- WHEN write (`POST …/activities/`, `PUT …/scores/bulk/`) or read (`GET …/activities/`, `GET …/scores/matrix/`)
- THEN MUST deny before grades I/O

---

**Source**: M7 Actividades (`m7-activities`)
