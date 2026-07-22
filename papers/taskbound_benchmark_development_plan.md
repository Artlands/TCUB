# TaskBound — Benchmark Development Plan

> **Status:** working plan (v1). Supersedes prior scratch plans.
> **Companion to:** `taskbound_position_paper.md` (the threat characterization this benchmark operationalizes).
> **Goal of this document:** a concrete, phased engineering + research plan to build TaskBound and validate it on a real, fully-controlled HPC system, learning from the AgentDojo methodology [8].

---

## 1. Purpose and success criteria

The position paper defines the **hijacked authorized agent** threat model for HPC: an agent with valid credentials and scheduler authority is redirected by adversarial content it reads during normal operation into actions that stay *account-authorized* but violate *task authority*. TaskBound is the empirical instrument that turns that argument into measurements.

TaskBound must answer four questions the position paper raises analytically (§7.2):

1. **How often** do current agents follow adversarial HPC context? (attack success rate — primary axis: per real *agent product*, evaluated as deployed; secondary axis: per *model* under a fixed reference scaffold, as an explanatory ablation)
2. **Which HPC surfaces** are highest-risk? (per attack-surface, per consequence type)
3. **Which controls** actually reduce risk **without destroying utility**? (defense matrix, joint metric)
4. **Does the "user-broad, task-narrow" boundary hold up** as a measurable, enforceable object? (task-scoped authority as a first-class, checkable policy)

### 1.1 Definition of done (v1.0 release)

- A reproducible benchmark: HPC task suites, injection cases, deterministic security oracles, joint utility/security metrics.
- The **task-scoped authority** mechanism (`TaskPolicy` + `PolicyEngine`) implemented as both a **scoring oracle** and a **runtime defense**, and shown to be the single source of truth for both.
- **Primary results** for ≥2 real deployed HPC agent products (evaluated as deployed) × the four HPC-distinctive consequence types × a defense matrix (at least: no-defense, provenance-label, tool-allowlist, task-scope-enforcement).
- **Secondary results** for ≥3 frontier models under a fixed reference scaffold, decomposing how much of an agent's susceptibility is the model vs. the scaffold and anchoring the numbers to a bare-model baseline.
- **Equivalence-validated on a real HPC cluster we fully control**: for every scenario, the deterministic in-memory verdict matches the real-cluster outcome by construction (shared policy/oracle code), and a controlled live-fire run confirms the attack and the defense behave as scored.
- A written responsible-use / reproducibility appendix.

### 1.2 Non-goals (inherited from the position paper §1.3)

Not covered: model-training-time poisoning, weight extraction, GPU side channels, kernel/hypervisor compromise, generic jailbreaking. TaskBound measures **environment-mediated redirection of an already-authorized agent** — nothing else.

---

## 2. What we adopt from AgentDojo, and what we must add

AgentDojo [8] is the right methodological template and the position paper commits us to it. We adopt its shape and extend it where HPC breaks its assumptions.

| AgentDojo concept | Adopt as-is | HPC extension TaskBound must add |
|---|---|---|
| **Task suite** = environment + tools + user tasks + injection tasks | Yes — same API shape | HPC `TaskEnvironment` (filesystem, scheduler, egress, multi-project) instead of email/bank/travel |
| **User task** (benign goal) + **injection task** (attacker goal) crossed into a matrix | Yes | Injection goals become the 4 HPC consequence types, not "send $X to attacker" |
| **Placeholder injection** into environment text | Yes — attacker string lives in content the agent reads | Injection sites = logs, `sacct` notes, module descriptions, shared scratch, peer-agent artifacts |
| **Attacks** as a swappable registry | Yes | Add HPC-flavored attacks (log-injection, module-description poisoning, staged multi-agent) |
| **Defenses = pipeline elements** composed into the agent loop | Yes | Add `TaskScopeExecutor`, provenance labeling, egress gate, module/tool allowlist |
| **Metrics = utility under attack, measured jointly** | Yes — this is the core methodological commitment | Add HPC consequence/severity metrics (below) since AgentDojo's are fixed booleans |
| **Deterministic, reproducible scoring** | Yes | Scoring stays in-memory & deterministic even when a real cluster is in the loop |

**The novel contribution is not the harness** — it is **task-scoped authority**: representing and checking "permitted for *this task*" as distinct from "permitted for *this account*." AgentDojo has no such notion. Everything else is faithful HPC re-instantiation of a proven design. Rebuilding the harness from scratch would be an undifferentiated worse clone; we build on AgentDojo as a pinned dependency and contribute the parts it lacks.

---

## 3. Architecture: one core, two evaluation surfaces

The central design decision: **scoring is deterministic and in-memory; the real cluster only confirms validity.** Security verdicts must never depend on a live cluster's nondeterministic state (scheduler timing, node placement, filesystem races), and we must never rely on real data exfiltration to "prove" an attack. Instead, one shared, dependency-free policy/oracle core is imported by both evaluation surfaces, so in-memory and real-cluster results are **equivalent by construction**, not by output-diffing.

```
                 ┌──────────────────────────────────────────────┐
                 │            taskbound-core (dep-free)         │
                 │  TaskPolicy · PolicyEngine · oracles · types │
                 │  the single definition of the task boundary  │
                 │  and of what counts as a violation           │
                 └───────────────┬─────────────────┬────────────┘
                                 │                 │
                 imports         │                 │         imports
        ┌────────────────────────▼───┐          ┌──▼───────────────────────────┐
        │      taskbound-bench       │          │      taskbound-harness       │
        │  (AgentDojo consumer)      │          │  (real-cluster consumer)     │
        │  in-memory TaskEnvironment │          │  dep-free, stdlib only,      │
        │  scored matrix, fast,      │          │  installs on a locked-down   │
        │  deterministic, CI-run     │          │  login node; drives real     │
        │  TaskScopeExecutor wraps   │          │  sbatch/squeue/filesystem    │
        │  AgentDojo ToolsExecutor   │          │  on the controlled cluster   │
        └────────────────────────────┘          └──────────────────────────────┘
```

- **`taskbound-core`** — dependency-free. `TaskPolicy` (the declared scope of one task), a pure `PolicyEngine` (decides allow/deny + emits a violation record), the deterministic `security_oracle`(s), and shared types. This is where the paper's thesis lives as executable code. It imports nothing so it is trivially auditable and installs anywhere.
- **`taskbound-bench`** — the AgentDojo consumer. In-memory Pydantic `TaskEnvironment` subclasses, the full attack × defense × model matrix, fast and deterministic, runs in CI. The `TaskScopeExecutor` (the A4 defense) wraps AgentDojo's `ToolsExecutor` and enforces `taskbound_core.PolicyEngine`.
- **`taskbound-harness`** — the real-cluster consumer, **stdlib-only** so it installs on a restricted login node. Drives real `sbatch`/`squeue`/filesystem operations and scores them with the **same** `taskbound_core` oracle. This is the authoritative real-Slurm validation path and a permanent part of the design, not scaffolding.

**Equivalence claim (what makes this rigorous):** both consumers call the identical `taskbound_core` policy and oracle code on the identical scenario definition. So "the in-memory run says A0→VIOLATED / A4→SECURE" and "the real cluster says the same" is guaranteed by construction, and any divergence is a bug in the environment adapter, not an ambiguity in the measurement. This lets us do the bulk of experimentation cheaply in-memory and reserve scarce real-cluster time for validity confirmation and controlled live-fire.

### 3.1 Pluggable agent driver

The agent loop / LLM client sits behind a `driver.py` interface so it is not reinvented in both consumers. The interface deliberately supports the two evaluation axes (§9):

- **Agent-adapter driver** (primary axis) — wraps a real deployed HPC agent product (e.g., an agentic coding CLI as flagged by site operators [5]) and normalizes its actions into a common trace format. Swapping one product for another is the headline experiment: it measures the agent *as deployed* (its scaffold, its built-in defenses, and the model it ships with, as one package).
- **Reference driver** (secondary axis) — a fixed, minimal scaffold (loop, system prompt, tool set) with a swappable model behind an OpenAI-compatible endpoint. Holding this scaffold constant and varying the model attributes ASR differences to the *model*, decomposing a product's susceptibility into model vs. scaffold. This is also the dependency-free default that runs on a locked-down node; an AgentDojo-backed variant is used inside the bench.

Either way the driver returns a normalized action trace that the oracle scores; the oracle never talks to a model, so the scoring is identical across both axes.

### 3.2 The main technical risk, de-risked first

Can `TaskScopeExecutor` cleanly wrap AgentDojo's `ToolsExecutor` by composition? This is the one integration risk. We de-risk it in a dedicated milestone before committing to the bench build; a lightly-tracked fork of that one class is the fallback if composition proves impossible.

---

## 4. From threat model to scored scenarios

We instantiate the paper's capability classes (§4.3, C1–C5) and attack-surface taxonomy (§5.1–§5.5) into **four HPC-distinctive consequence types**. These are chosen because each is something a web/enterprise benchmark like AgentDojo *cannot* express — they are the payoff of doing this in HPC at all. (Cross-project read is the one closest to generic prompt injection and serves as the bridge/sanity case; the other three are genuinely HPC-native.)

| Consequence type | Paper surface | Capability | What "VIOLATED" means | Oracle signal |
|---|---|---|---|---|
| **`cross_project_read`** | §5.4 cross-project leakage | C1/C4 | Task scoped to project A; agent reads/returns project B data the *account* may reach but the *task* may not | Access to a path outside the task's declared project scope |
| **`resource_abuse`** | §5.2 scheduler channel | C2 | Agent submits/resizes jobs beyond the task's declared resource ceiling on the user's allocation | `sbatch` request exceeds `TaskPolicy` resource ceiling |
| **`integrity_tampering`** | §5.3 / scientific integrity | C1/C3 | Agent silently edits an immutable input, filter, parameter, or provenance record | Snapshot/hash mismatch on a declared-immutable artifact |
| **`shared_fs_persistence`** | §5.1 filesystem poisoning | C4 | Agent writes durable adversarial content into shared scratch/collaboration space for a later agent | Write to shared path that survives job teardown |

A fifth, **`coordinated_multi_agent`** (§5.5, C5), is a stretch scenario for v1.1: a staged artifact written by one agent is consumed by a second with broader scope. It reuses the same oracle applied across a two-agent trace.

### 4.1 Scenario schema

Each scenario is a declarative record (one file in a `scenarios/` registry) with:

- **`user_task`** — the benign instruction and its success oracle (did the agent do the real job?).
- **`task_policy`** — the declared scope: allowed project(s), allowed paths (read/write/immutable), resource ceiling, allowed egress sinks. *This is the ground truth for both scoring and defense.*
- **`injection`** — the attacker payload and its **injection site** (which piece of environment text carries it, mapped to C1–C5).
- **`consequence`** — which of the four types this scenario targets, and the oracle parameters.
- **`expected`** — the equivalence contract: A0 (no defense) → VIOLATED, A4 (task-scope enforcement) → SECURE **and utility preserved**.

The `expected` field is what the real-cluster harness validates against.

---

## 5. Task-scoped authority: the core contribution

This is the part that does not exist in any prior benchmark, so it gets the most engineering care.

### 5.1 `TaskPolicy`

A declarative description of what *this task* is allowed to touch, independent of the account's standing authority:

- `projects: allowed project scope` (the account may belong to more; the task may touch one).
- `paths: {readable, writable, immutable}` globs.
- `resources: {max_nodes, max_gpus, max_walltime, max_jobs}` ceiling.
- `egress: allowed sinks` (e.g., the sanctioned LLM backend; a canary sink is *never* allowed).

Authoring note (open question from paper §7.3): task scope is somewhat subjective. We mitigate by (a) deriving policies mechanically from the user task where possible, (b) having two annotators author independently and measuring agreement, and (c) reporting sensitivity of the headline metrics to policy tightness.

### 5.2 `PolicyEngine`

A **pure function**: `(action, TaskPolicy, environment_state) → Decision{allow|deny, violation_record?}`. No I/O, no model calls, fully unit-testable. It is used two ways:

- **As a scoring oracle** (offline): replay the agent's action trace through the engine → count violations.
- **As a runtime defense** (`TaskScopeExecutor`, the A4 control): intercept each tool call before execution → deny out-of-scope actions.

Because both uses share this one function, "what the oracle counts as a violation" and "what the defense prevents" cannot drift apart. That identity is the methodological backbone of the whole benchmark.

### 5.3 Security oracles

One generic deterministic `security_oracle` parameterized per consequence type, plus:

- **Snapshot/hash checks** for `integrity_tampering` (record immutable-artifact hashes pre-run, diff post-run).
- **Canary tokens** for egress/leak detection: `cross_project_read` and multi-agent exfil are detected by planting a unique canary in the out-of-scope data and watching for it in any egress attempt to a controlled sink — never by actually exfiltrating real data.
- **Filesystem snapshot diff** for `shared_fs_persistence` (what durable content survived job teardown).

---

## 6. Defenses (the pipeline elements we evaluate)

Following AgentDojo, defenses are composable pipeline elements. The matrix:

- **A0 — no defense** (baseline; establishes ASR).
- **A1 — provenance labeling** (paper §7.1): every context item (user instruction, file, tool output, peer message) carries a trust/source label; prompt the agent to condition on it. Tests whether web/enterprise-style provenance defenses transfer to HPC (open question §7.3).
- **A2 — tool/module allowlist** (paper §5.3): restrict tool selection to a vetted set; tests the Shi et al. [11] tool-description attack surface.
- **A3 — egress gate**: block agent-to-model traffic carrying canary/out-of-scope data (paper §7.1 egress control).
- **A4 — task-scope enforcement** (`TaskScopeExecutor`): the novel control; deny any action outside `TaskPolicy`. This is the one we expect to be decisive, and the joint metric must show it preserves utility.
- **A1+A4, A2+A4** — combinations, to show task-scope enforcement composes with cheaper defenses rather than replacing them.

Each defense reports **both** its attack-success reduction and its utility cost. A defense that blocks attacks by breaking the benign task is a failure — this is the whole point of AgentDojo's joint metric and we preserve it.

---

## 7. Metrics

AgentDojo's metrics are fixed booleans; we derive the standard ones for free and add an HPC consequence/severity layer computed by post-processing traces.

- **USR — Utility Success Rate**: fraction of benign tasks the agent completes correctly (no attack present). Establishes baseline competence.
- **ASR — Attack Success Rate**: fraction of injection cases where the attacker's consequence is achieved (oracle → VIOLATED).
- **Utility-under-attack**: USR measured *with* the injection present — the joint metric; a good defense keeps this high while ASR drops.
- **STCR — Successful Task Completion under attack + control**: benign task still succeeds *and* attack blocked.
- **Consequence/severity layer** (HPC-specific, our addition):
  - **UAR — Unauthorized Access Rate** (cross-project reads).
  - **SDER — Scheduler Damage / over-ceiling Rate** (resource abuse magnitude, not just boolean).
  - **ITR — Integrity Tampering Rate** (silent artifact/provenance edits).
  - **SPR — Shared-fs Persistence Rate** (durable poison written).
- **Defense cost**: Δutility and, where relevant, latency/token overhead per defense.

Severity is weighted per stakeholder in reporting (a PI weighs `integrity_tampering` differently than a security team weighs `cross_project_read`), matching the paper's §5 argument that these consequences matter differently to different people.

---

## 8. Real-HPC validation on the controlled cluster

This is the new element the position paper only gestured at, and the reason for the dep-free harness track. The controlled cluster is where we prove the in-memory benchmark is faithful to reality.

### 8.1 Two things the real cluster does (and two it does not)

**It does:**
1. **Validity confirmation** — for each scenario, run the *benign* user task on real Slurm and confirm the task is actually doable with the given tools (the environment is realistic, not a strawman).
2. **Controlled live-fire** — run the *injected* scenario end-to-end on real infrastructure and confirm the real outcome matches the deterministic verdict (A0→VIOLATED, A4→SECURE), exercising the harness's real `sbatch`/filesystem adapters against the same `taskbound_core` oracle.

**It does not:**
3. It does **not** produce the headline metrics — those come from the deterministic in-memory matrix so results are reproducible without cluster access.
4. It does **not** ever perform real exfiltration, real cross-user data theft, or unbounded resource consumption — see safety guardrails.

### 8.2 Cluster setup (fully controlled test system)

- A **dedicated partition/QOS** isolated from any production work, with hard resource ceilings enforced at the scheduler level (so a `resource_abuse` live-fire is bounded even if the oracle logic were wrong).
- **Synthetic projects and synthetic data only.** Multi-project scope is modeled with real Unix groups + real project directories, but every "sensitive" file is synthetic and carries a canary token. No real user data is ever in scope.
- **Canary egress sink**: a controlled endpoint we own; the only place a canary can go. Detecting a canary there = attack succeeded, with zero real-world leak.
- **Snapshot/restore** of the shared scratch/collaboration filesystem between trials, so `shared_fs_persistence` poison from one trial cannot bleed into the next and every trial starts from a known state.
- **Immutable-artifact hashing** recorded before each `integrity_tampering` trial.

### 8.3 Equivalence protocol

For each scenario S and defense A:
1. Freeze `taskbound_core` policy/oracle version.
2. Run S×A in-memory → deterministic verdict V_mem.
3. Run S×A on the cluster via the harness → real verdict V_real (scored by the *same* core).
4. Assert V_mem == V_real. Any mismatch is filed as an environment-adapter bug, investigated, fixed — it is never averaged away.

This turns "is the in-memory benchmark realistic?" from a hand-wave into a passing/failing test.

### 8.4 Safety guardrails for running attacks on real hardware

Because we are deliberately running injection attacks on a real cluster, the guardrails are part of the design, not an afterthought:

- Isolated partition, synthetic data, canary-only egress, scheduler-enforced ceilings, snapshot/restore between trials (all above).
- No secrets, no production credentials, no shared filesystem paths outside the test tree.
- A kill-switch: the harness aborts a trial if any action would touch a path or resource outside the pre-declared test sandbox, independent of the agent's or oracle's logic.
- All live-fire runs logged with full provenance for the reproducibility appendix.

---

## 9. Experimental design

**Unit of evaluation.** An ASR is only interpretable if we say what varied. This study is about *agents in HPC*, so the agent is the primary unit; the model is a secondary, explanatory axis.

- **Primary axis — the agent product (evaluated as deployed).** Sweep ≥2 real deployed HPC agents via the **agent-adapter driver**, each measured holistically: its scaffold, its built-in defenses, and the model it ships with, as one package. Headline claim: "the HPC agents sites actually run [5] are susceptible to HPC-native injection." We state the confound openly rather than hide it: swapping one product for another usually changes *both* the scaffold and the underlying model, so a difference between two products is attributable to the product **as a whole**, not to its scaffold in isolation. That is the correct unit for a thesis about agents-as-deployed. **≥2 agent products** for v1.0; more in v1.1.
- **Secondary axis — the model (explanatory ablation).** To decompose a product's susceptibility into "how much is the model vs. the scaffold," hold the **reference driver** (a plain scaffold) fixed and vary the model across **≥3 frontier models**. Where a real product allows swapping its backend model, also vary the model within that product. This attributes the residual, connects our numbers to a bare-model baseline, and mirrors AgentDojo (which fixes its pipeline and varies the model).

The agent-adapter result is the headline; the reference-driver sweep explains it. Because both feed the same trace format and the same oracle, the two axes are directly comparable.

- **Attacks:** the HPC attack registry (log-injection, module-description poisoning, staged multi-agent, plus AgentDojo's transferable generic attacks as a baseline). At least one adaptive attack per surface, per the AgentDojo commitment to adaptive rather than only static attacks.
- **Defense matrix:** A0–A4 and the two combinations (§6). The two axes treat defenses differently: on the reference-driver (model) axis, A1–A4 are *our* pipeline elements added to a bare scaffold; on the agent-product axis, a product's built-in mitigations are already part of the unit under test, so its A0 baseline includes whatever it ships with — and A1–A4 measure what our task-scoped controls add *on top of* a hardened product.
- **Scenarios:** the four consequence types, multiple user tasks each, each crossed with matching injection tasks (AgentDojo-style matrix). Target ≥ a few hundred injection cases so per-surface rates are meaningful.
- **Ablations:** policy-tightness sensitivity (§5.1), provenance-label transfer (A1, open question §7.3), enforcement locus (framework vs. scheduler-side A4).
- **Reporting:** per-agent-product joint utility/security tables × surface × defense (primary), plus the reference-driver per-model tables that decompose product susceptibility (secondary); severity-weighted rollups; equivalence pass rate against the real cluster.

---

## 10. Milestones

Phased so that (a) we prove the novel contribution and the AgentDojo integration early, and (b) the deterministic benchmark is fully usable before we spend scarce real-cluster time.

| M | Milestone | Exit criterion |
|---|---|---|
| **M0** | Repo + `taskbound-core` skeleton: `TaskPolicy`, `PolicyEngine`, types, one oracle | Pure-function unit tests green; installs dep-free |
| **M1** | **De-risk:** prototype `TaskScopeExecutor` wrapping AgentDojo `ToolsExecutor` by composition | Composition works on a toy suite, or fork fallback decided |
| **M2** | `taskbound-harness` v0.1 (stdlib-only): driver, scenario registry, all four consequence oracles, real-`sbatch` adapter behind a stub | One scenario A0→VIOLATED / A4→SECURE end-to-end on stubbed cluster; tests green |
| **M3** | AgentDojo integration in `taskbound-bench`: in-memory `TaskEnvironment`, first scenario scored through the real AgentDojo pipeline | First model run produces USR/ASR for one scenario |
| **M4** | Full scenario registry (4 consequence types × multiple user/injection tasks) + attack registry | Matrix runs in CI; deterministic |
| **M5** | Defense matrix A0–A4 + combinations; full metric layer (incl. consequence/severity); agent-adapter + reference drivers | Primary: joint tables for ≥2 real agent products (as deployed); secondary: reference-scaffold sweep over ≥3 models decomposing product susceptibility |
| **M6** | **Real-cluster bring-up**: dedicated partition, synthetic projects, canary sink, snapshot/restore, guardrails | Benign tasks run on real Slurm (validity confirmation) |
| **M7** | **Equivalence + live-fire** on the controlled cluster for all scenarios | V_mem == V_real for every scenario×defense; live-fire safe |
| **M8** | Analysis, ablations, reproducibility appendix, benchmark release | v1.0: reproducible artifact + paper-ready results |

M0–M2 deliberately never touch AgentDojo (the standalone bootstrap gate); AgentDojo is first touched at M1's de-risk probe and integrated at M3. Real hardware is first touched at M6, after the deterministic benchmark is complete.

---

## 11. Repository and engineering practices

- **Three importable packages** in one repo: `taskbound-core`, `taskbound-bench`, `taskbound-harness`, sharing `taskbound-core`.
- **AgentDojo pinned** as a dependency of `taskbound-bench` only (a specific commit/version), never vendored into core or harness.
- **Testing:** `taskbound-core` has exhaustive pure-function tests (this is the trust anchor); each scenario ships with its expected A0/A4 verdict as a test; equivalence assertions are tests, not reports.
- **CI:** runs the full deterministic matrix on every change (no cluster needed). Real-cluster runs are a separate, manually-triggered job.
- **Reproducibility:** frozen core version + scenario registry + model/driver config + seeds recorded per result; live-fire runs logged with full provenance.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| `ToolsExecutor` can't be wrapped cleanly | De-risked in M1; tracked light fork fallback |
| Task scope is subjective → metrics fragile | Dual annotation + agreement measure + tightness-sensitivity ablation (§5.1) |
| Real-cluster attacks cause real harm | Isolated partition, synthetic+canary data, scheduler ceilings, snapshot/restore, kill-switch (§8.4) |
| In-memory env is an unrealistic strawman | Equivalence protocol makes realism a passing/failing test (§8.3), plus benign-task validity confirmation |
| Reviewer sees "just an AgentDojo clone" | Frame + implement task-scoped authority as the contribution; harness is faithful HPC re-instantiation, not novelty theater |
| Results are model-version-specific | Report ≥3 models; claim is about the agent class, and driver is swappable |

---

## 13. Ethics and responsible use

- All attacks run only on infrastructure we fully control, against synthetic data, with canary-only egress. No production system, no real user data, no real exfiltration.
- No new attack technique is weaponized beyond what is needed to *measure* susceptibility; payloads are benchmark artifacts, not deployable exploits.
- The benchmark's purpose is defensive: to let sites tell the difference between an agent that is safe and one that has simply not been tested against its own environment (position paper §8).
- Release includes a responsible-use statement and the reproducibility appendix.

---

## 14. Deliverables

1. `taskbound-core`, `taskbound-bench`, `taskbound-harness` (released, tested).
2. Scenario + attack + defense registries covering the four consequence types.
3. Deterministic result matrix (≥3 models × 4 surfaces × defense matrix) with joint utility/security and severity metrics.
4. Real-cluster equivalence + live-fire validation report.
5. Reproducibility + responsible-use appendix.
6. The empirical companion to the position paper, answering its four §7.2 questions with data.
