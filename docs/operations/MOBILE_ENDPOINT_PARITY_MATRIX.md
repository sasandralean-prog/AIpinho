# Mobile Endpoint Parity Matrix

| state | endpoint | mobile normal | mobile details | raw | actions |
| --- | --- | --- | --- | --- | --- |
| idle | idle | human status | ids, policy, evidence and trace when available | hidden_by_default | download if artifact_id exists |
| running | running | human status | ids, policy, evidence and trace when available | hidden_by_default | download if artifact_id exists |
| pending_approval | pending_approval | human status | ids, policy, evidence and trace when available | hidden_by_default | approve/cancel |
| pending_validation | pending_validation | human status | ids, policy, evidence and trace when available | hidden_by_default | download if artifact_id exists |
| validating | validating | human status | ids, policy, evidence and trace when available | hidden_by_default | download if artifact_id exists |
| completed | completed | human status | ids, policy, evidence and trace when available | hidden_by_default | download if artifact_id exists |
| completed_with_warnings | completed_with_warnings | human status | ids, policy, evidence and trace when available | hidden_by_default | download if artifact_id exists |
| degraded | degraded | human status | ids, policy, evidence and trace when available | hidden_by_default | download if artifact_id exists |
| blocked | blocked | human blocked reason | ids, policy, evidence and trace when available | hidden_by_default | download if artifact_id exists |
| failed | failed | human status | ids, policy, evidence and trace when available | hidden_by_default | download if artifact_id exists |
| validation_failed | validation_failed | human status | ids, policy, evidence and trace when available | hidden_by_default | download if artifact_id exists |

Blocked must not render as healthy. Completed requires validation when the operation contract requires it. Raw remains hidden by default.
