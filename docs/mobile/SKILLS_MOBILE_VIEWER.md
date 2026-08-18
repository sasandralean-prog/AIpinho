# Skills Mobile Viewer

Endpoint:

```text
GET /api/v1/mobile/view-model/skills
```

Normal mode should show:

- skill name;
- category;
- status;
- risk level;
- required capabilities;
- warnings.

Normal mode must not show:

- raw manifest internals;
- tokens;
- raw/debug payloads;
- direct dangerous actions.

The dashboard also includes an internal skills card pointing to this endpoint.
