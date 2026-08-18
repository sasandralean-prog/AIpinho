# Sandbox Regression Matrix

| Area | Positive | Negative |
| --- | --- | --- |
| Files | write/read/modify/list | traversal and outside write blocked |
| Shell | readonly/test/build | network/destructive/unknown blocked |
| Artifacts | ZIP registered with token endpoint | oversized export blocked |
| Cleanup | preview then apply | apply without preview blocked |
| Tool Gateway | metadata, validation and artifact linked | policy denial remains structured |
| Mobile | sandbox view-model and dashboard card | raw hidden by default |

Run:

```powershell
python -m pytest tests\sandbox tests\integration\test_sandbox_api.py tests\multi_agent\sandbox -q
python tests\multi_agent\run_multi_agent_regression.py --sandbox
```
