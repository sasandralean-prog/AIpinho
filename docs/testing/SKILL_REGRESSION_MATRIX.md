# Skill Regression Matrix

Run:

```powershell
python tests\multi_agent\run_multi_agent_regression.py --skills
```

Coverage:

- manifest registry seed;
- mobile sanitized view;
- fake secret rejection;
- source-readonly write rejection;
- governed report execution;
- missing capability block;
- disabled skill block;
- validation evidence;
- trace raw hidden by default.

Promote every production skill bug into this matrix before adding more skill features.
