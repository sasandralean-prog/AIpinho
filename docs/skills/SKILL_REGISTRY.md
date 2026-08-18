# Skill Registry

The registry is local and config-driven.

Default root:

```text
config/skills/registry
```

Override for tests or isolated environments:

```text
AIPINHO_SKILL_REGISTRY_ROOT=<path>
```

Files per skill:

- `skill.yaml`: canonical manifest.
- `skill.json`: generated mirror for inspection.
- `README.md`: human description.
- `tests.json`: placeholder for skill-specific validation notes.

The registry also writes:

```text
config/skills/registry/skills_index.json
```

Enable/disable changes are persisted through the registry and backed up under `backups`.
