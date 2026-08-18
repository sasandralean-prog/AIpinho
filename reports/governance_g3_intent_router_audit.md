# Governance G3 Intent, Router, and Model Routing Audit

- Audit type: governance_topology_audit
- Generated UTC: 2026-06-26T07:31:34.299Z
- Checkpoint: G3_INTENT_ROUTER_AUDIT_READY

| Finding | Severity |
| --- | --- |
| Router precedence is dispersed across ApprovalCommand, PermissionGrant, OperationRouter, PromptIntelligence, Continue regexes, and agent routers. | P0 |
| PermissionGrant now has negation/readonly guards but still executes before the operation router. | P1 |
| Session diagnostic must stay explicit because sprint prompts contain diagnostic/preview/evidence words. | P1 |
| Workspace permission query exists in chat but must be mirrored by all channels. | P1 |
| Continue has independent side-effect regexes and policy config. | P1 |

Recommended precedence for Block B:

1. explicit approval/deny/cancel command
2. explicit read-only/planning intent and negative constraints
3. workspace registry/query
4. positive permission grant
5. explicit config change
6. project/workspace bootstrap
7. patch/write
8. shell/build/test
9. explicit session diagnostic
10. conversation

Rules: negation beats positive match; planning beats permission grant; workspace query must not become conversation; create-folder with ask policy must create approval or structured denial; approval commands must run before conversational routing.
