# Sprint 20 Dogfood Plan

## Objective

Validate AIpinho in a controlled real-project workflow:

- inspect a source-readonly project;
- identify a small reliability issue;
- produce a governed plan;
- deny writes into source-readonly;
- create a fixed target-mutable copy;
- run governed validation;
- publish an authenticated artifact report;
- expose a truthful mobile/agent state.

## Workspaces

- `dogfood20_source_readonly`: controlled fixture used only as analysis source.
- `dogfood20_target_mutable`: controlled mutable output project.
- `dogfood20_protected`: protected negative-control workspace.
- `dogfood20_forbidden`: forbidden negative-control workspace.

The workspaces are registered through the workspace registries and tool gateway policies. No project-specific routing rule was added.

## Execution Path

1. Create or reuse a multi-agent session.
2. Read and list files from source-readonly.
3. Attempt one negative write into source-readonly and expect a policy block.
4. Create a patch preview for target-mutable.
5. Create the target project files through governed file creation.
6. Run test shell in the target workspace.
7. Record validation.
8. Create a report artifact.
9. Verify the mobile view-model state and artifact download endpoint.

## Expected Acceptance

- Source hash before and after remains identical.
- Target project contains the corrected implementation and tests.
- Governed shell test passes.
- Artifact download requires token.
- Historical tool blocks do not make a completed run appear blocked.

