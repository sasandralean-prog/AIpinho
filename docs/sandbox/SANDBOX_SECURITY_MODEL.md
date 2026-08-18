# Sandbox Security Model

The security boundary is the resolved sandbox root plus the selected workspace root.

Controls:
- relative-path validation before resolution;
- containment check after resolution;
- existing symlink target containment;
- no free shell;
- network/destructive command deny patterns;
- token-protected artifact download;
- raw hidden by default;
- cleanup preview;
- per-task trace.

The sandbox is a productive execution boundary, not a replacement for workspace roles, Policy Kernel or Approval outside the sandbox.
