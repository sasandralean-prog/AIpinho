# Template Picker Mobile Contract

Backend endpoint:

`GET /api/v1/templates/mobile/view-model`

The response is read-only and contains:

- screen title
- registry status
- compact template cards
- `raw_default_visible=false`

Mobile should render templates as selectable project-generation options, not as direct filesystem actions. Actual generation must still pass through the sandbox Project Factory and governed Tool Gateway.
