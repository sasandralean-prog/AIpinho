# AIpinho PinhoForge Android Workbench Provider

## Purpose

Expose governed Android project analysis and allowlisted Android execution through the Tool Gateway.

## Tool Gateway tools

- `pinhoforge_android_project_detect`
- `pinhoforge_android_environment_readiness`
- `pinhoforge_android_gradle_task_list`
- `pinhoforge_android_gradle_task_execute`
- `pinhoforge_android_adb_devices`
- `pinhoforge_android_logcat_readonly`
- `pinhoforge_android_report_export`

## Guarantees

- External unregistered source scopes are blocked
- Unknown Gradle tasks are blocked
- `adb shell`, install, uninstall, push, pull and clear-data stay blocked
- Output is captured with truncation controls
- Reports and log exports become governed artifacts

## Notes

- Build success is never claimed without `exit_code` evidence.
- APK readiness is intentionally conservative and stays tied to real file existence in future bridge steps.
- Provider stays inside declared operations; it does not expose terminal freedom.

