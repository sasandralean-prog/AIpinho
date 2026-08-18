# Asset Placeholder Generation

When a prompt requests assets such as `sapo.png` or `encanamento.png`, the sandbox template may create safe placeholder equivalents rather than binary images.

Current Android output uses vector drawable XML placeholders because they are:

- text-reviewable;
- deterministic;
- compact;
- safe for sandbox ZIP export;
- build-friendly when Android tooling is available.

This placeholder system must remain generic. It must not create special logic for one game, project, sprite name or test prompt.

