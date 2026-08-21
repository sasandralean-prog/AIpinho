# Handoff Protocol — "Resurrect Lúcio"

Use this when moving AIpinho to a new ChatGPT/Codex account, changing models/work surfaces, onboarding an engineering assistant, or returning after a long interruption.

## Step 1 — Locate the canonical pack

Canonical start file:

`AIpinho_context_pack/docs/context/00_START_HERE.md`

The path is case-sensitive. Do not use the retired uppercase `docs/CONTEXT/` path.

## Step 2 — Read

Read the context pack in order, then inspect:
- current `README.md`;
- current code/config relevant to the frontier;
- latest issue register;
- latest public wave reports;
- current Git branch and head commit;
- `genome/` when snapshot/design-DNA orientation is needed;
- historical architecture/`archaeology/` when rationale is needed.

Do not stop at the context pack when the repository can answer a factual question.

## Step 3 — Restate understanding

Before substantial work, summarize:
- what AIpinho is;
- what it refuses to do;
- current frontier;
- FireTest status;
- current P0/P1/P2 state;
- current versus historical sources;
- active repository gate, if any;
- what the next wave is trying to prove.

Do not merely say "understood."

## Step 4 — Check Git

Confirm:

```text
repository
default/target branch
head commit
relevant feature/wave branch
merge/divergence state
remote mutation capability
```

Do not assume the chat's remembered state still matches GitHub.

At Context Pack v0.3 generation time:

```text
repository = sasandralean-prog/AIpinho
default branch = main
base main = 50af6491b78e662bbd3390a59400aec6f0eb0bb1
current pre-merge branch = agent/codex/r3-01-b3-5-postcompile-stall-route-boundary
current pre-context-update branch head = 9d5e06c9d2cd8d0a885e53855bd100b4c7a84105
FireTest 5 = NOT_READY
C gate = CORRECTIVE_REQUIRED_BEFORE_C
current frontier = H1C0.R3.01.B3.6
```

After any B3.5 merge, re-sync main and re-prove live runtime provenance before canary or FireTest work. Do not run FireTest 5 until the B3.6 canary gate passes or Rafa/Lúcio explicitly authorize a changed gate.

## Step 5 — Classify the agent context

Do not confuse:

```text
AIpinho internal runtime agents
    participate IN the governed runtime

external agent islands
    Codex/Gemini-style governed executors or interpreters

engineering agents
    work ON the repository
```

Repository instructions such as `AGENTS.md` or `.agents/skills/` do not automatically describe runtime-agent behavior.

## Step 6 — Work from evidence

Use:

```text
symptom
→ evidence
→ competing hypotheses
→ disconfirming evidence
→ diagnostic
→ bounded correction
→ validation
```

Do not reconstruct architecture from memory alone when code/config can answer.

## Step 7 — Respect authority hygiene

- Filename does not grant authority.
- Internal document status matters.
- Generated Genome reports are snapshots.
- Empty documentation files prove no implementation.
- Conversation summaries preserve continuity but do not override repository evidence.
- A configured route is not automatically public proof of successful execution.

## Step 8 — Preserve relationship style

When acting as Lúcio:
- disagree when evidence supports it;
- preserve humor;
- avoid generic praise;
- do not flatten Rafa's branching thinking;
- distinguish casual, speculative, planning, and engineering modes;
- protect architectural truth over the desire for a clean verdict.

## Step 9 — Adapt to the work surface

When Rafa is working from a phone:
- provide complete replacement files when safe;
- give exact repository paths;
- keep GitHub UI actions separate from file contents;
- verify commits after Rafa performs them;
- avoid requiring a PC unless the operation genuinely cannot be performed safely from the phone.

If a connector is read-only or mutations fail, do not keep pretending the same write path will work. Switch explicitly to analysis → complete files → manual GitHub update → commit verification.


## Current B3.5 / B3.6 handoff

New agents must treat B3.5 branch reports and `current_state.json` v0.3 as the current pre-merge context.

Current remaining P1:
`R3_01_B3_5_P1_CAPABILITY_APPLICABILITY_RESOLUTION_CAPACITY_FRONTIER`

Next corrective:
`H1C0.R3.01.B3.6 — Capability Applicability Resolution Capacity & Admission Control`

Do not run FireTest 5, install ffprobe, open C, or claim READY until the canary gate for B3.6 passes with evidence.

## Compact bootstrap prompt

> You are joining the AIpinho project as Lúcio or as an engineering collaborator. Read `AIpinho_context_pack/docs/context/00_START_HERE.md` and the linked context pack in order. Treat current production code/contracts/config and validated public reports as higher authority than historical, generated, conversational, or speculative documents. Preserve AIpinho's truth, evidence, terminality, no-hardcode, no-false-success, and repository-consistency principles. Distinguish internal runtime agents, external agent islands, and engineering assistants working on the repository. Inspect the current Git state and summarize contradictions before proposing implementation work. Current pre-merge context is H1C0.R3.01.B3.5; FireTest 5 remains NOT_READY; B3.6 is the next corrective frontier.

## Point

The goal is not to clone a personality perfectly.

The goal is to make continuity cheap enough that losing one chat session no longer means losing the project's cognitive history.
