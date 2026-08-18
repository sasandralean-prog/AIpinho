# Sandbox Project Factory

The Sandbox Project Factory creates new projects only inside governed sandbox tasks. It is intended for creative generation, prototypes, demos and downloadable project bundles.

Canonical endpoints:

- `POST /api/v1/sandbox/project-factory/classify`
- `POST /api/v1/sandbox/project-factory/generate`

The factory never writes to user workspaces directly. If the prompt references an external path without a registered workspace contract, the request is blocked with a safe sandbox alternative instead of pretending to inspect that path.

## Flow

1. Classify the prompt as sandbox project generation, artifact request, external workspace request or unsupported request.
2. Resolve a project type through generic intent signals.
3. Create a sandbox task and agent run.
4. Generate template files under the sandbox task directory.
5. Validate structure.
6. Export a token-protected ZIP artifact.
7. Return artifact metadata, evidence refs and human-safe final status.

## Current Project Types

- `android_kotlin`
- `python_cli`
- `python_simple_app`
- `static_web`
- `markdown_docs`
- `generic_files`

## Safety Rules

- No direct external workspace write.
- No path traversal.
- No public artifact URL.
- No token in URL.
- No false ready state when artifact generation fails.
- Template behavior must be generic and reusable, not prompt-specific.

