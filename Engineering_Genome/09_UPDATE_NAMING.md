# Update Naming

Use semantic names first; ordinals second.

Preferred pattern: `<DOMAIN>-<BOUNDARY>-<NN>`.

Examples: `MEDIA-TRUTH-01`, `RUNTIME-HANDOFF-02`, `PLAYLIST-IDENTITY-03`, `DSP-PIPELINE-01`.

A checkpoint record should include semantic name, legacy coordinate when relevant, scope, baseline SHA, resulting SHA, evidence level, tests/evidence, documentation impact, limitations, and next frontier.

Existing `M*`, `REV-*`, and `Sprint *` names remain valid historical coordinates. Do not rename history merely for cosmetic consistency. New work may carry both forms during migration.
