# Golden Path Matrix

| id | operation | task | workspace | approval | validation | artifact | mobile |
| --- | --- | --- | --- | --- | --- | --- | --- |
| simple_chat | simple_chat | no task | no workspace | no approval | not required | none | clean chat answer |
| simple_chat_with_artifact | artifact_request | no task by default | artifact store only | no approval | artifact validation | artifact links | download card |
| readonly_analysis | readonly_analysis | task or operation | read only | none unless policy requires | analysis validation | none | summary |
| readonly_analysis_with_artifact_output | readonly_analysis_with_artifact_output | task | read source; write artifact store only | none unless broad scan policy requires | artifact/report validations | txt/zip artifact | summary plus download |
| target_workspace_patch_preview | patch_preview | task | read target no apply | approval later | preview validation | none | preview card |
| target_workspace_patch_apply | patch_apply | task | mutate target only | required | post apply validation | optional report | final state |
| shell_readonly | shell_command | task | read-only shell | maybe | exit/evidence | none | sanitized status |
| shell_test_or_build | shell_command | task | test/build category | required when side effects | exit/evidence | none | test status |
| blocked_write_to_readonly | blocked_policy_message | maybe task | blocked | none | block evidence | none | blocked with reason |
| destructive_shell_blocked | blocked_policy_message | task or preview | blocked | none | block evidence | none | blocked with reason |
| approval_required | approval_request | task | pending side effect | required | pending | none | approval action |
| approval_denied | approval_denied | task | no mutation | denied | terminal/blocked | none | denied state |
| validation_failed | validation_result | task | no success | depends | failed | maybe report | not completed |
| artifact_download | artifact_download | no task | artifact store only | token/header | integrity optional | downloaded file | download notification |
| mobile_endpoint_divergence_detection | diagnostic | regression candidate | none | none | divergence evidence | none | diagnostic warning |

These paths are certification targets. Tests must use fakes/fixtures and must not invoke real models by default.
