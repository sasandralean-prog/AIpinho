# Gemini Adapter v1

Implemented by:

- `GeminiExternalAdapter`
- `ExternalAdapterRegistry`

Generic endpoint:

- `POST /api/v1/external/adapters/{adapter_id}/review`

Adapter id available:

- `gemini`

Outputs:

- Human output: friendly text based on provider output.
- Machine output: `ExternalReviewCreateRequest` compatible with `external_review.v1`.

Important:

- No `/api/v1/external/gemini/*` route was created.
- No execution authority is granted to the adapter.
- AIpinho stores the review and decides what to do later.

