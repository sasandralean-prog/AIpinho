# Command Profile Model

Command Profiles are governed command recipes used as suggestions for validation/build/test flows.

Fields:

- `command_id`
- `label`
- `command`
- `working_directory_role`
- `category`
- `risk_level`
- `requires_approval`
- `allowed_execution_modes`
- `timeout_seconds`
- `expected_outputs`
- `success_patterns`
- `failure_patterns`
- `redaction_required`

Commands are not free shell. They must pass Tool Gateway, shell policy, workspace resolution, audit, timeout and validation.

