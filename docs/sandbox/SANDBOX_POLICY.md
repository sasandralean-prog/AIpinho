# Sandbox Policy

Configuration: `config/sandbox/sandbox_policy.yaml`.

Allowed by default:
- file read/write/append/modify/mkdir/list/copy/move;
- safe delete by moving content to sandbox trash;
- readonly, test, build and package shell categories;
- ZIP export through the authenticated artifact lifecycle;
- validation and trace inspection.

Blocked by default:
- absolute or traversing paths;
- symlink/junction escape;
- destructive and unknown shell;
- network shell;
- git commit/push;
- direct cleanup without preview;
- artifacts beyond the configured size limit.

Policy is deterministic because it protects filesystem, shell, secrets and cleanup boundaries. Product behavior remains outside this policy.
