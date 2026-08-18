# Role Contracts

GR2 migrates role decisions to explicit governed role contracts.

The existing YAML role files remain as source configuration, but operational
authorization is derived from `RoleContract` objects.

## Schemas

- `RoleContract`
- `RoleCapability`
- `RolePermission`
- `RoleRestriction`
- `RoleLifecycle`
- `RoleExecutionPolicy`

## Boundary

Role contracts do not enable tools, writes, patches, skills, or runtime
execution. Those remain clamped by policy until later governed runtime sprints.
