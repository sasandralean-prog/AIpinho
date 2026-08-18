# Sprint H Runtime Analysis

TaskRun remains the execution source of truth.

Canonical runtime inputs:

- `TaskRun.status`
- `TaskRun.plan.steps`
- `TaskRun.current_step_id`
- `TaskRun.approval_id`
- `TaskRun.policy_snapshot`
- `TaskRunResult`
- `TaskRunEvent`
- Universal artifact registry rows linked by task/run id

Progress rule:

- Progress is derived from real plan steps.
- Completed units are steps with status `completed` or `skipped`.
- Total units are the plan step count.
- Completed result forces 100 percent only when the runtime result is terminal completed.
- ETA is `None` unless a real estimator exists. No timer-based fake ETA was added.

Terminal truth:

- Completed, failed, blocked and cancelled are derived from `TaskRunResult` first, then from `TaskRun.status`.
- Missing outputs keep `safe_to_report_success=false`.

