# Validation Profile Model

Validation Profiles define project-specific validation sequences without hardcoding project behavior in services.

Sequences:

- `default_validation_sequence`
- `quick_validation_sequence`
- `full_validation_sequence`
- `smoke_validation_sequence`

Evidence:

- command profile ids;
- file checks;
- artifact checks;
- report checks;
- required evidence refs.

Validation failure policies:

- `block_completion`
- `allow_completed_with_warnings`
- `require_human_review`
- `create_self_healing_candidate`

