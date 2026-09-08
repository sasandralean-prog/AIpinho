# AIpinho Engineering Workflow

## Default wave loop

```text
baseline
→ observed frontier
→ competing hypotheses
→ mandatory diagnostic
→ root-cause classification
→ bounded patch
→ focused tests
→ regressions
→ public/live diagnostic when required
→ clean validation rerun
→ issue register
→ verdict
→ next frontier
```

## Baseline consistency gate

Before starting a new wave, confirm:

- target implementation exists in the intended branch;
- current README/state/context agree on the validated frontier;
- reports and issue registers exist at the claimed proof scope;
- current repository heads are observed rather than remembered;
- historical or speculative documents are not silently treated as runtime authority;
- shared runtime/test resources have no conflicting active lease;
- the task execution class is explicit: repository-only, local-required, or hybrid.

If Git, code, reports, runtime evidence, and current knowledge disagree, preserve the contradiction and resolve it before widening scope.

## Diagnose before patch

Do not begin with “what patch makes the test pass?”

Use:

```text
symptom
→ evidence
→ competing hypotheses
→ disconfirming evidence
→ diagnostic
→ bounded correction
→ validation
→ consequence
```

## Priority policy

### P0

Truth, governance, terminality, corruption, false-success, authority confusion, or repository/knowledge contradictions that invalidate the baseline.

### P1

Structural runtime blockers, complexity/capacity failures, generic capability/binding defects, nondeterminism.

### P2

Observability/schema/projection defects that materially weaken diagnosis or validation.

### P3

Cosmetic/report formatting.

A proven bug is not automatically fixed. Keep evidence status, resolution status, and validation scope distinct.

## Proof classes

Distinguish:

```text
unit validated
regression validated
repository/cloud validated
live local diagnostic reached
clean live validation
final product/runtime proof
```

Never convert unit proof into public/live proof.

## Strategic Horizon namespace

The roadmap names `Horizon H1/H2/H3/H4`. These are planning categories from near-term to long-range. They are **not patch IDs or implementation tranches**.

Do not confuse them with the external Control Plane names:

```text
CONTROL-H1 / CONTROL-H2 / CONTROL-H3
```

Those are concrete Lúcio Shell/Control implementation and validation tranches. Always keep the namespace when ambiguity is possible.

## Git protocol

Normal repository engineering flow:

```text
observe/sync main
→ create agent/<agent>/<task> branch
→ implement
→ validate claimed scope
→ update only evidence-supported docs/reports
→ commit/push branch
→ review
→ merge validated work
→ reobserve main
```

Do not force-push or use destructive cleanup to manufacture synchronization.

Tracked synchronization means:

```text
tracked(local main) == tracked(origin/main)
```

It does not mean deleting ignored/untracked local overlay such as `.env*`, models, caches, corpora, runtime state, or raw evidence.

## Three repository roles

### AIpinho

```text
sasandralean-prog/AIpinho
```

Runtime/application source of truth. Product/runtime success is owned by AIpinho contracts, runtime, validation/completion, and SpeakerTruth.

### AIpinho-FireTest-Control

```text
sasandralean-prog/AIpinho-FireTest-Control
```

External governed operations/engineering layer. Current architecture includes Ed25519 principal authentication, local broker/sequence/replay, semantic engineering capabilities, Script Catalog hash binding, bounded execution, evidence/lifecycle, H1 account context, H2 delegated-agent surfaces, and CONTROL-H3 engineering governance.

Current progression at the 2026-09-07 continuity checkpoint:

```text
G3_BASELINE_VALIDATED
CONTROL-H1 through H1-E validated
CONTROL-H2 through H2-E validated
CONTROL-H3-A through H3-H accepted at defined scopes
CONTROL-H3-I E2E authority compression live accepted and independently reproduced
CONTROL-H3-J progressive FireTest re-entry started
```

The lower-layer execution invariant remains governed `current_session` execution under `aipinho-runner`/`CreateProcessW`, with fresh signed authority, replay protection, semantic/catalog binding, bounded runtime/output, non-elevation, secret scrubbing, containment, and structured evidence.

Control progress does not itself change AIpinho runtime truth.

### AIpinho-Envelope-Requests

```text
sasandralean-prog/AIpinho-Envelope-Requests
```

Unsigned request/intake transport. The local broker observes provenance, allocates sequence, signs locally, and publishes create-only signed Control envelopes. GitHub/request text is never signing authority.

## Current FireTest workflow

FireTest is in **progressive governed re-entry**, not unrestricted execution and not global READY.

CONTROL-H3-J1 has fresh narrow unit proof: Control run `33933759448` executed the admitted CVL/FireTest unit file and returned `19 passed`.

The later product FireTest B attempt, Control run `34059896495`, completed its governed diagnostic but the product request blocked before TaskRun creation:

```text
BLOCKED_PRE_TASK
PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED
task_run_id=null
SpeakerTruth.safe_to_report_success=false
Phases 2-6=skipped_due_to_prior_block
```

That is the latest product-facing boundary before reset.

## Clean reset workflow

The 2026-09-07 governed reset report establishes a cold, clean operational baseline:

```text
runtime/chat active=0
pending=0
orphaned=0
leases=0
hygiene candidates=0
old TaskRun and observer terminalized as cancelled
API/9088 offline
old Control runner stopped/disabled
Envelope runner retained
AIpinho tracked tree clean at main a4253226...
corpus present and unmodified
FFmpeg/FFprobe present on host
new FireTest not started
```

Treat this as hygiene success, not product success.

Before the next FireTest, acquire fresh coordination locks and deliberately start only the runtime/runner resources required by the new campaign.

## Dependency/tool evidence rule

Host installation is not enough.

The 06/09 FireTest execution context observed FFmpeg/FFprobe as unavailable, while the 07/09 reset observed them installed on the host. Therefore the next campaign must prove exact executable visibility and normal AIpinho capability admission in the governed execution context.

```text
installed != visible
visible != admitted
admitted != executed
executed != semantic success
```

## FireTest invariants

- no FireTest/Pinhoabacaxi/path/task-ID/row-count production special cases;
- `.m4a`, filename and path are not semantic Truth;
- the corpus path must be observed/bound, not baked into production logic;
- Phase 2 must not execute if Phase 1 blocks;
- green Control Actions is not product success;
- TaskRun existence is not completion;
- artifact/result existence is not fulfillment;
- a blocked terminal result can be correct governance;
- B3.5/B3.6 applicability-capacity evidence remains historical/open until newer evidence closes or supersedes it.

## Shared-resource coordination

For any work touching Control/runtime/FireTest resources, read in order:

1. Control `COMMUNICATION_SYNC_LUCIO.md`
2. Control `CURRENT_STATE.md`
3. Control `CONTEXT_PACK_LUCIO_SHELL.md`
4. Control `COMMUNICATION_SYNC.md`
5. current relevant report/evidence

Inspect active leases before mutation. A logical lock coordinates ownership; it never grants authority by itself.

## End-of-wave report

State:

- exact scope and execution class;
- repository/branch/head;
- observed root cause/frontier;
- changes made;
- tests and live evidence by proof class;
- runtime/product terminality and SpeakerTruth;
- P0/P1/P2 still open;
- FireTest status;
- Control operation/run/artifact identifiers when relevant;
- locks acquired/released;
- authority explicitly **not** granted;
- next bounded frontier.

A clean verdict is useful only when the evidence deserves it.
