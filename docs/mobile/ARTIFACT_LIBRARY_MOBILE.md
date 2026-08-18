# Mobile Artifact Library

Endpoint:

`GET /api/v1/mobile/view-model/artifact-library`

The mobile view-model contains:

- recent artifact cards;
- filters;
- status;
- origin;
- size;
- download action only when `status=ready`;
- preview/details/context actions;
- `raw_default_visible=false`.

The UI must send Authorization headers for downloads and must not open raw protected URLs in a public browser.
