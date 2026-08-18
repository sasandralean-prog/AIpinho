# Mobile Project Selector

Mobile uses:

- `GET /api/v1/mobile/view-model/projects`

The payload includes:

- screen state;
- active project id;
- profiles;
- stack;
- source workspace id;
- target workspace id;
- validation profile id;
- warnings.

The mobile UI must treat this as selection context. It must not grant file write, shell, network or patch rights without Policy Kernel and Tool Gateway.

