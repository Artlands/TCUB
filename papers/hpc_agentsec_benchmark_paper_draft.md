# Trusted Credentials, Untrusted Behavior: Benchmarking LLM-Agent Security in High-Performance Computing

> **Working benchmark name:** HPC-AgentSec  
> **Paper type:** benchmark + threat characterization + empirical security study  
> **Primary claim:** existing LLM-agent security benchmarks do not model the task, project, scheduler, filesystem, and scientific-integrity boundaries that determine risk in HPC environments.

## Working Abstract

Large language model (LLM) agents are beginning to assist with scientific computing tasks such as job-script generation, failure diagnosis, software deployment, simulation monitoring, data analysis, and workflow orchestration. These agents are useful because they can read scientific artifacts, inspect scheduler output, invoke command-line tools, modify scripts, submit jobs, and communicate with local or remote model backends. The same capabilities create a security risk that is not captured by existing general-purpose agent benchmarks: an agent can be redirected by untrusted content while continuing to operate under valid user credentials and legitimate scheduler authority.

We present **HPC-AgentSec**, a benchmark for evaluating the utility and security of LLM agents in representative high-performance computing environments. The benchmark models the **hijacked authorized agent** threat, in which adversarial instructions embedded in scientific files, job logs, tool outputs, shared storage, or peer-agent messages cause an otherwise legitimate agent to violate its assigned task boundary. HPC-AgentSec includes realistic HPC workflows, task-scoped access policies, synthetic project data, Slurm-like scheduler actions, tool interfaces, attack cases, deterministic security oracles, and reproducible scoring. It evaluates both whether an agent completes the intended scientific task and whether it avoids unauthorized data access, data exposure, workflow corruption, unsafe command execution, resource misuse, and cross-agent contamination.

We use the benchmark to study five questions: how frequently current agents follow malicious HPC context; which infrastructure features create the highest-risk attack surfaces; how attack outcomes vary across models and agent designs; which existing controls mitigate the attacks; and what utility-security tradeoffs those controls impose. The benchmark is designed for safe execution with synthetic data and mock external services. Our results are intended to establish a reproducible foundation for comparing LLM-agent security mechanisms in scientific computing rather than to claim a complete defense.

---

## 1. Introduction

High-performance computing systems are evolving from batch-oriented execution platforms into interactive scientific environments. Users routinely inspect logs, repair job scripts, build software, analyze large output directories, steer simulations, and coordinate multi-stage workflows. LLM agents are a natural addition to this environment because they can translate high-level intent into shell commands, scheduler actions, data-processing steps, and explanatory reports.

An effective HPC agent may need to:

- read files from project and scratch storage;
- inspect Slurm job scripts, output, and accounting records;
- execute command-line utilities and scientific software;
- load environment modules and resolve dependencies;
- modify workflow configurations;
- submit, cancel, or resubmit jobs;
- summarize scientific results;
- exchange intermediate artifacts with other agents; and
- send context to a local or external LLM endpoint.

These capabilities create a security boundary that is different from the boundaries represented in common web, office-productivity, or generic tool-use benchmarks. In HPC, a user may legitimately belong to multiple projects, have access to multiple datasets, and hold scheduler authority over substantial computational resources. The distinction between **what the user is allowed to do** and **what the current agent task should do** therefore matters.

Prior research has established that LLM-integrated applications and tool-using agents can be manipulated by indirect prompt injection, malicious tool descriptions, poisoned tool output, and adversarial inter-agent messages. Prior HPC security work has studied identity, access control, user separation, secure workflows, and scheduler policy. However, neither line of work fully addresses the interaction between instruction-following agents and HPC-specific infrastructure: shared parallel filesystems, multi-project access, scheduler-mediated execution, scientific provenance, rich software stacks, and persistent cross-job artifacts.

We call the resulting threat the **hijacked authorized agent**. The agent is launched by a legitimate user and runs with valid credentials. It does not need to exploit the kernel, steal a password, or bypass POSIX permissions. Instead, adversarial content encountered during normal operation redirects the agent into behavior that remains technically authorized by the user account but violates the task, project, scientific, or data-governance boundary.

Examples include:

- a poisoned simulation log causing an analysis agent to read another project’s data;
- a malicious build-tool output causing a software assistant to run an unsafe command;
- a shared file causing a reporting agent to include restricted data in an LLM-bound request;
- a peer agent staging data in a shared path for a second agent to transmit;
- a debugging agent modifying resource requests or repeatedly submitting costly jobs; and
- a scientific assistant silently changing parameters, filters, or provenance records.

A few demonstrations would show that such attacks are possible, but they would not provide a reusable basis for comparing models, agents, and defenses. We therefore formulate the research as a benchmark problem.

### 1.1 Research objective

The objective of HPC-AgentSec is to answer:

> Can an LLM agent complete realistic HPC tasks while remaining within a task-scoped security and scientific-integrity boundary when its environment contains adversarial content?

This formulation evaluates utility and security jointly. An agent that refuses every tool call may be secure but useless; an agent that completes every task while leaking data is useful but unsafe.

### 1.2 Why a new benchmark is needed

General LLM-agent benchmarks provide valuable methodologies for evaluating prompt injection and tool misuse, but they typically do not model:

1. **Task scope versus user authority.** A user may be permitted to access several projects, while an agent should access only one for the current task.
2. **Scheduler-mediated authority.** Agents may submit, cancel, resize, or resubmit jobs and consume shared allocations.
3. **Scientific integrity.** Unsafe behavior includes silent modification of parameters, filtering, provenance, or outputs—not only data theft.
4. **Shared parallel storage.** Poisoned artifacts can persist across jobs, users, and agents.
5. **HPC software stacks.** Module systems, compiler output, build scripts, and post-processing tools become instruction channels.
6. **Cross-agent and cross-job effects.** One agent may stage, poison, or transform data for another agent.
7. **Operationally legitimate egress.** Sensitive data can leave through normal encrypted LLM requests rather than an obviously malicious destination.

### 1.3 Contributions

This paper makes the following contributions:

1. **HPC-specific benchmark formulation.** We define the hijacked authorized agent as a task-boundary violation problem in which identity and conventional authorization remain valid.

2. **Benchmark environment and task suite.** We introduce HPC-AgentSec, a controlled HPC-like environment with project directories, shared storage, Slurm-like scheduler operations, scientific artifacts, tool interfaces, multi-agent communication, and synthetic restricted data.

3. **Attack taxonomy and security cases.** We provide attack cases covering scientific-file injection, scheduler-log injection, tool-output poisoning, shared temporary-state injection, cross-project access, resource misuse, scientific-workflow corruption, and multi-agent staging.

4. **Deterministic security oracles and joint scoring.** We define machine-checkable policies and metrics for task success, secure task completion, unauthorized access, sensitive-data exposure, unsafe commands, workflow-integrity violations, and resource abuse.

5. **Comparative evaluation.** We evaluate multiple model backends, agent architectures, and baseline defenses under a common protocol, reporting both security outcomes and utility costs.

6. **Open and safe artifact design.** The benchmark uses synthetic data, mock credentials, controlled services, and isolated scheduler actions so that attacks can be reproduced without targeting production systems.

### 1.4 Scope and non-goals

HPC-AgentSec focuses on LLM agents that use textual context and tools to perform scientific-computing operations. It does **not** attempt to benchmark:

- model training-time poisoning;
- model extraction or weight theft;
- GPU microarchitectural side channels;
- kernel or hypervisor compromise;
- general hallucination unrelated to adversarial context;
- content-safety jailbreaks; or
- every possible form of HPC misuse.

The benchmark is intentionally scoped to **environment-mediated hijacking of authorized agents**.

---

## 2. Background and Positioning

### 2.1 LLM agents in scientific computing

LLM agents extend language models with planning, memory, tool invocation, and environment interaction. In scientific computing, they can assist with job preparation, data inspection, debugging, software installation, workflow automation, and experiment steering. These tasks expose agents to heterogeneous sources of text whose trust level is rarely explicit.

### 2.2 HPC execution and security model

HPC environments commonly combine authenticated users, scheduler-managed allocations, project accounts, shared storage, local scratch, module-based software environments, and external data or model services. Security mechanisms generally answer questions such as:

- Who is the user?
- Which files can this account access?
- Which allocation may this user charge?
- Which nodes and partitions may this job use?
- Which network destinations are reachable?

They usually do not answer:

- Which resources are relevant to the agent’s current task?
- Which text sources may issue instructions?
- Whether a scientifically plausible action was adversarially induced?
- Whether a valid file access violates project or task intent?

### 2.3 Relationship to prior agent-security benchmarks

HPC-AgentSec follows the established benchmark principle of evaluating both utility and security under adversarial tool or data outputs. Its distinction is the system model and the protected properties.

A general agent-security benchmark may model an email, travel, banking, or productivity domain. HPC-AgentSec instead models:

- project-scoped scientific data;
- scheduler operations and allocation consumption;
- shared and persistent filesystem artifacts;
- scientific logs, checkpoints, metadata, and result files;
- build tools, environment modules, and post-processing programs;
- scientific reproducibility and provenance; and
- multi-agent communication through cluster resources.

The benchmark does not claim that indirect prompt injection is new. Its contribution is to make HPC-specific boundaries, consequences, and controls measurable.

---

## 3. Benchmark Goals and Design Principles

### 3.1 Goals

HPC-AgentSec should support four uses:

1. **Vulnerability measurement:** compare how often agents violate HPC task boundaries.
2. **Defense evaluation:** compare prompt-, agent-, tool-, and system-level mitigations.
3. **Failure analysis:** identify which context sources and action types produce failures.
4. **Regression testing:** determine whether a new agent version improves security without losing utility.

### 3.2 Design principles

#### P1. HPC-native semantics

Tasks must require scheduler, filesystem, toolchain, or scientific-workflow reasoning that cannot be reduced to generic question answering.

#### P2. Task-scoped authority

The benchmark distinguishes three scopes:

- **system-permitted:** actions technically allowed by the account;
- **task-permitted:** actions necessary and authorized for the benchmark task;
- **forbidden:** actions outside the declared task boundary.

This distinction is central to the benchmark.

#### P3. Joint utility-security evaluation

Every security case has a corresponding benign task. Refusing all actions should reduce utility.

#### P4. Deterministic outcome measurement

Security outcomes should be determined primarily by file, command, scheduler, network, and provenance monitors rather than by subjective LLM judging.

#### P5. Safe reproducibility

All secrets, datasets, credentials, and external services are synthetic or mocked. No case requires interaction with production systems.

#### P6. Extensibility

New domains, tasks, tools, attacks, models, and defenses should be addable through versioned manifests.

#### P7. Separation of mechanism and consequence

The benchmark records both:

- **how the agent was influenced** (e.g., poisoned log); and
- **what happened** (e.g., cross-project read, parameter corruption, or data exposure).

---

## 4. Threat Model and Security Properties

### 4.1 Hijacked authorized agent

An agent is considered hijacked when adversarial environmental content causes it to perform an action that violates the task policy while it continues to use legitimate user authority.

The benchmark assumes:

- the user intentionally launches the agent;
- the agent has valid access to its assigned workspace and tools;
- the cluster control plane and benchmark harness are trusted;
- the attacker does not have root access;
- the attacker does not modify the model weights; and
- the attack enters through data, logs, tools, shared state, or peer-agent messages.

### 4.2 Attacker capability classes

| Class | Capability | Example benchmark source |
|---|---|---|
| C1 | Write or influence a scientific artifact the agent will read | simulation log, metadata, README, result file |
| C2 | Influence scheduler-adjacent output | job stdout/stderr, wrapper output, accounting note |
| C3 | Control a tool’s description or output | converter, build helper, module description |
| C4 | Write to shared node or filesystem state | temporary file, cache, shared workflow path |
| C5 | Control or hijack a peer agent | inter-agent message, staged intermediate artifact |

A benchmark case should require the minimum capability necessary for the attack and should not silently grant the attacker stronger access.

### 4.3 Protected assets

- project-scoped scientific data;
- synthetic controlled or proprietary data;
- credentials and configuration secrets;
- scheduler allocations and quotas;
- workflow scripts and parameters;
- scientific outputs and provenance records;
- shared software and workflow artifacts;
- trust between collaborating agents.

### 4.4 Security properties

HPC-AgentSec evaluates whether the agent preserves:

1. **Task confinement:** actions remain within the declared task scope.
2. **Data confidentiality:** protected data is not exposed to unauthorized outputs or model endpoints.
3. **Workflow integrity:** scripts, parameters, datasets, and results are not adversarially modified.
4. **Resource integrity:** scheduler actions remain within declared limits.
5. **Tool integrity:** tools are selected and invoked only as authorized.
6. **Provenance integrity:** material actions remain traceable and correctly attributed.
7. **Cross-agent isolation:** one agent cannot improperly influence or use another agent’s state.

---

## 5. HPC-AgentSec Benchmark Architecture

HPC-AgentSec consists of six layers.

### 5.1 Environment layer

The environment provides:

- user and project namespaces;
- task workspaces;
- shared and temporary storage;
- a Slurm-compatible or emulated scheduler interface;
- command-line and scientific tools;
- synthetic scientific data and logs;
- local or mock LLM endpoints; and
- optional multi-agent messaging.

### 5.2 Task layer

Each task includes:

- a user-visible objective;
- initial environment state;
- allowed resources and actions;
- expected outputs;
- utility success criteria; and
- cleanup/reset rules.

### 5.3 Security-case layer

A security case adds:

- an injection source;
- attacker capability;
- adversarial objective;
- modified artifacts or tool outputs;
- protected assets;
- prohibited outcomes; and
- severity metadata.

### 5.4 Agent adapter layer

Adapters normalize different agents into a common interface:

- receive task instruction;
- inspect environment;
- call tools;
- produce final response;
- expose action traces; and
- support configurable defense wrappers.

### 5.5 Monitor and oracle layer

The benchmark records:

- file reads, writes, renames, and deletions;
- executed commands and arguments;
- scheduler submissions, cancellations, and resource requests;
- tool calls and outputs;
- data sent to model endpoints;
- changes to workflow parameters and provenance records; and
- cross-agent communication events.

A policy engine converts these traces into deterministic verdicts.

### 5.6 Scoring and reporting layer

The reporting layer produces per-case and aggregate utility, security, severity, and efficiency results with confidence intervals and raw traces.

---

## 6. Benchmark Domains and Task Families

The benchmark eventually spans five domains, but the first submission targets three **core domains** (D1, D2, D4) chosen because they most directly exercise the paper's central claim — task-scoped authority under scheduler and shared-filesystem conditions that general agent-security benchmarks do not model. D3 and D5 are **extension domains**: valuable but not load-bearing for the core thesis, and deferred to a follow-up or camera-ready expansion rather than gating the first result. This split exists because building and validating all five domains end-to-end is a multi-lab-scale effort; a solo/small team targeting a top-tier venue should prioritize depth on the domains that carry the argument over breadth across all five. Target counts below are development goals, not completed claims.

### D1. Slurm job diagnosis and repair — *core*

Representative tasks:

- diagnose a failed batch job;
- repair an invalid resource request;
- identify an out-of-memory failure;
- interpret scheduler and application logs;
- revise a submission script without submitting it.

Security cases:

- malicious instructions in `slurm-*.out`;
- output that requests unsafe shell commands;
- instructions to read unrelated project files;
- instructions to submit oversized or repeated jobs.

### D2. Scientific result analysis — *core*

Representative tasks:

- summarize simulation outputs;
- compute aggregate metrics;
- identify failed runs;
- generate a structured report;
- compare two approved datasets.

Security cases:

- poisoned metadata or notes;
- instructions to suppress failed runs;
- cross-project data inclusion;
- exposure of synthetic restricted data.

### D3. Software build and environment management — *extension domain (post-v1)*

Representative tasks:

- diagnose compiler errors;
- select an appropriate module;
- repair a build configuration;
- explain a dependency conflict;
- run a safe test build.

Security cases:

- malicious compiler or wrapper output;
- poisoned module description;
- instructions to install or execute an unapproved binary;
- modification of shared build scripts.

### D4. Workflow orchestration and simulation steering — *core*

Representative tasks:

- check workflow state;
- resume failed stages;
- alter an approved simulation parameter;
- summarize convergence and recommend the next authorized step.

Security cases:

- parameter tampering;
- deletion or masking of provenance;
- unauthorized workflow-stage execution;
- resource escalation.

### D5. Multi-agent scientific collaboration — *extension domain (post-v1)*

Representative tasks:

- planner delegates analysis to worker agents;
- one agent prepares data and another generates a report;
- multiple agents share approved intermediate artifacts.

Security cases:

- malicious peer-agent message;
- staged data through shared storage;
- persistent injection in an intermediate artifact;
- cross-agent transfer of protected data.

### 6.1 Initial scale target

The **v1 (first submission) scope** targets the three core domains only:

- 3 domains (D1, D2, D4);
- 15–20 benign tasks;
- 3–5 security cases per task family;
- 45–70 total security cases;
- 3 severity levels; and
- 4 defense configurations (§11.3).

D3 and D5 expand the suite to 5 domains, 25–40 tasks, and 80–150 cases as a follow-up or camera-ready addition, not a v1 requirement. The final paper should report only the counts actually implemented and validated, and should state explicitly which domains were validated on real Slurm infrastructure versus emulation only.

---

## 7. Attack Taxonomy

The benchmark separates injection channels from consequences.

### 7.1 Injection channels

1. **Scientific-artifact injection** — instructions embedded in logs, metadata, outputs, checkpoints, or documentation.
2. **Scheduler-output injection** — instructions embedded in job stdout/stderr or scheduler-adjacent artifacts.
3. **Tool-description injection** — malicious text in tool metadata or module descriptions.
4. **Tool-output poisoning** — compromised command or service emits instructions during normal execution.
5. **Shared-state injection** — malicious content placed in shared storage, scratch, cache, or temporary paths.
6. **Peer-agent injection** — instructions delivered through agent messages or intermediate files.

### 7.2 Consequence classes

1. **Unauthorized data access**
2. **Sensitive-data exposure**
3. **Unsafe command or tool execution**
4. **Scientific-workflow corruption**
5. **Scheduler/resource misuse**
6. **Persistence or downstream poisoning**
7. **Cross-agent or cross-project transfer**
8. **Provenance degradation**

This two-dimensional taxonomy prevents the benchmark from equating every injection with the same outcome.

---

## 8. Task and Case Specification

Each benchmark instance should be stored in a versioned manifest.

### 8.1 Example task manifest

```yaml
id: slurm_debug_oom_001
domain: slurm_debugging
version: 1.0
user_task: >
  Diagnose why job 1042 failed and propose a corrected submission script.
initial_state: fixtures/slurm_debug_oom_001/
allowed_paths:
  - /projects/alpha/jobs/1042/**
denied_paths:
  - /projects/beta/**
allowed_tools:
  - cat
  - grep
  - sed
  - sacct_mock
  - sbatch_validate
scheduler_policy:
  may_submit: false
  max_nodes: 1
  max_gpus: 0
expected_artifacts:
  - corrected.sbatch
utility_oracle: oracles/slurm_debug_oom_001.py
```

### 8.2 Example security-case manifest

```yaml
id: slurm_debug_oom_001_log_injection_a
base_task: slurm_debug_oom_001
attacker_capability: C2
injection_source: /projects/alpha/jobs/1042/slurm-1042.out
attack_goal: cross_project_read
protected_asset:
  path: /projects/beta/restricted/synthetic_secret.txt
prohibited_events:
  - file_read:/projects/beta/**
  - llm_egress_contains:SYNTHETIC_SECRET_BETA_001
severity: high
```

### 8.3 Benign counterpart

Every security case should have a benign counterpart with comparable task complexity and no adversarial text. This is needed to measure both false refusals and baseline task difficulty.

---

## 9. Metrics and Scoring

### 9.1 Primary metrics

#### Utility Success Rate (USR)

Fraction of benign tasks completed correctly.

\[
USR = \frac{\text{successful benign tasks}}{\text{benign tasks attempted}}
\]

#### Attack Success Rate (ASR)

Fraction of security cases in which the attacker’s prohibited outcome occurs.

\[
ASR = \frac{\text{security cases with prohibited outcome}}{\text{security cases attempted}}
\]

#### Secure Task Completion Rate (STCR)

Fraction of attacked tasks for which the agent completes the legitimate task without any security violation.

\[
STCR = \frac{\text{attacked tasks completed securely}}{\text{attacked tasks attempted}}
\]

STCR is the benchmark’s most important joint metric.

### 9.2 Consequence-specific metrics

- **Unauthorized Access Rate (UAR):** fraction of cases with out-of-scope file or project access.
- **Sensitive Data Exposure Rate (SDER):** fraction of cases in which protected content reaches the agent’s final output, model endpoint, tool output, or unauthorized file.
- **Unsafe Action Rate (UnsAR):** fraction of cases with prohibited command, tool, or scheduler action.
- **Workflow Integrity Violation Rate (WIVR):** fraction of cases with unauthorized changes to parameters, scripts, datasets, result selection, or provenance.
- **Resource Abuse Rate (RAR):** fraction of cases exceeding task-declared scheduler or resource limits.
- **Persistence Rate (PR):** fraction of cases that create poisoned state capable of affecting later tasks or agents.

### 9.3 Utility cost of defenses

For defense configuration \(d\):

\[
UtilityCost_d = USR_{baseline} - USR_d
\]

A defense should not be described as effective without reporting its effect on utility.

### 9.4 Severity-weighted risk

Each prohibited outcome is assigned a documented severity weight. The aggregate score should be reported alongside unweighted rates, not as a replacement for them.

### 9.5 Secondary measurements

- number of tool calls;
- token and inference cost;
- wall-clock completion time;
- number of user-confirmation requests;
- refusal rate on benign cases;
- failure stage: perception, planning, tool selection, action, or reporting;
- monitor visibility: which system logs contain the evidence.

### 9.6 Statistical protocol

Because LLM agents are stochastic:

- run each model-agent-case combination multiple times;
- fix and report decoding parameters;
- use independent seeds where supported;
- report means and bootstrap confidence intervals;
- separate deterministic environment failures from model failures; and
- avoid interpreting a single successful exploit as a population-level rate.

---

## 10. Research Questions

### RQ1. How vulnerable are current LLM agents to HPC-specific environmental injection?

Measure ASR and STCR across domains, injection channels, models, and agent architectures.

### RQ2. Which HPC infrastructure features and context sources produce the most severe failures?

Compare scientific artifacts, scheduler logs, tool outputs, shared state, and peer-agent messages.

### RQ3. What consequences arise when attacks succeed?

Measure unauthorized access, data exposure, unsafe execution, workflow corruption, resource misuse, persistence, and cross-agent transfer.

### RQ4. Which existing defenses reduce risk, and what utility do they sacrifice?

Evaluate prompt hardening, structured context, tool restrictions, task-scoped filesystem access, scheduler guardrails, human confirmation, and behavioral monitoring.

### RQ5. How well do existing HPC logs and controls explain or detect the failures?

Determine whether POSIX permissions, scheduler accounting, shell logs, network allowlists, audit logs, and agent traces reveal the security violation and its cause.

---

## 11. Experimental Methodology

### 11.1 Testbed

Use two execution modes, and use them concurrently rather than sequentially:

1. **Portable emulation:** containers or namespaces with a Slurm-like interface and shared volumes. Used for iteration speed and full-matrix cost control.
2. **Validated Slurm deployment:** an authorized test cluster used to confirm that selected cases reproduce under real scheduler and filesystem behavior.

Because access to a real cluster is a genuine differentiator from purely emulated agent-security benchmarks, real-Slurm validation should start with the **first** implemented task and attack case, not be deferred to a late confirmation pass. A single real-cluster result — one benign task, one poisoned-log attack, one observed policy violation — is the earliest evidence that the "hijacked authorized agent" thesis produces HPC-distinctive failures rather than a relabeled instance of generic prompt injection, and should be obtained before committing further engineering time to the full environment build-out (see the bootstrap gate in the companion development plan).

The portable mode supports artifact evaluation and the full evaluation matrix; the Slurm mode supports ecological validity and should appear throughout development, not only at the end.

### 11.2 Model and agent matrix

**v1 scope (fixed):**

- one local open-weight model;
- one stronger hosted model, policy permitting;
- one primary agent architecture/framework adapter; and
- a deterministic/mock-agent control for validating oracles.

A second agent architecture is a stretch goal for the first submission, not a requirement — the model/agent matrix is the dimension most tempting to over-expand, and each additional model or adapter multiplies the full evaluation matrix (§11.4) rather than adding to it linearly. Model names and versions should be pinned in the final artifact regardless of matrix size.

### 11.3 Baseline agent configurations

**v1 defenses (four, sufficient for the first submission):**

- **A0: unprotected agent** (baseline)
- **A1: prompt-only safety instruction**
- **A4: task-scoped filesystem/scheduler policy** — the most HPC-native defense and the one that most directly tests the user-broad/task-narrow thesis; prioritize this over the others if only one can be built well
- **A6: lightweight runtime behavioral monitor**

**Extension defenses (add if time permits, or reserve for follow-up work):**

- **A2: structured provenance labels**
- **A3: tool allowlist and argument validation**
- **A5: human confirmation for high-risk actions**

Not every mechanism needs to be presented as a novel defense. They are benchmark baselines, and a smaller, well-measured set beats a larger set with thin per-defense evidence.

### 11.4 Evaluation matrix

A full matrix is:

\[
Model \times Agent \times Domain \times Case \times Defense \times Seed
\]

Given the v1 scope (§11.2, §11.3, §6.1), this is tractable for a solo/small team. To control cost and de-risk the central claim early, use a staged protocol with an explicit bootstrap gate before any broad run:

0. **Bootstrap gate:** implement and validate one task and one attack case end-to-end, including a real-Slurm confirmation run. Do not proceed to stage 1 until this produces the expected violation and the expected benign pass. This is the single most important checkpoint in the whole evaluation — it is the earliest point at which the paper's thesis can fail, and failing fast here is far cheaper than discovering the same problem after building the full case suite.
1. screen all cases on a small baseline set;
2. select validated, nontrivial cases;
3. run the full model-defense matrix on the final suite; and
4. confirm representative results on the Slurm deployment.

### 11.5 Security oracle validation

Before evaluating agents:

- manually inspect each case;
- run a benign reference solution;
- run a scripted attack solution;
- verify that the monitor detects the intended prohibited event;
- confirm that unrelated benign actions do not trigger the oracle; and
- reset environment state between trials.

Begin dual-reviewer labeling of task-permitted, prohibited, and severity judgments starting with the **first** security case, not as a batch pass near submission. For a top-tier venue, "the prohibited/permitted boundary is subjective" is the most likely rejection vector (§15.2), and it is far cheaper to catch policy disagreements while there are five cases than after there are seventy.

### 11.6 Reproducibility

Release:

- task and security-case manifests;
- synthetic fixtures;
- agent adapters;
- environment images;
- monitor and scoring code;
- pinned versions;
- raw anonymized traces;
- analysis scripts; and
- an artifact-evaluation quick-start profile.

---

## 12. Results Section Blueprint

The final results section should be organized around findings rather than implementation components.

### 12.1 Overall utility and security

Report USR, ASR, and STCR for each model-agent configuration.

**Suggested table:** rows are models/agents; columns are benign USR, attacked task success, ASR, STCR, and cost.

### 12.2 Vulnerability by injection channel

Compare scientific files, scheduler logs, tool outputs, shared state, and peer-agent messages.

**Suggested figure:** ASR grouped by channel and domain.

### 12.3 Consequence analysis

Show which attacks produce data exposure, workflow corruption, unsafe execution, resource misuse, persistence, and cross-agent transfer.

**Suggested figure:** channel-to-consequence Sankey diagram or matrix.

### 12.4 Defense tradeoffs

Compare defenses using a security-utility frontier.

**Suggested figure:** x-axis USR, y-axis 1-ASR or STCR.

### 12.5 Control visibility

Show which events are visible in scheduler, filesystem, process, network, and agent logs.

**Suggested table:** control-by-consequence coverage matrix.

### 12.6 Case studies

Include two or three trace-based case studies:

1. poisoned Slurm log causing out-of-scope file access;
2. poisoned tool output causing workflow modification; and
3. multi-agent staging causing indirect data exposure.

Each case study should include:

- benign task;
- injection point;
- action trace;
- violated policy;
- evidence visible to existing controls; and
- effect of the strongest baseline defense.

---

## 13. Expected Claims and Claim Boundaries

### 13.1 Claims the benchmark can support

- Current LLM agents can violate task-scoped HPC boundaries after consuming adversarial environmental content.
- HPC-specific resources produce consequences not adequately represented in general agent benchmarks.
- Attack success and consequence severity vary by context source, model, agent architecture, and defense.
- Several existing controls reduce particular risks but impose utility costs or leave coverage gaps.
- Task-scoped policies and deterministic system traces enable reproducible security evaluation.

### 13.2 Claims to avoid

- all HPC agents are unsafe;
- all HPC centers share the same configuration;
- the benchmark covers every AI-agent threat;
- prompt injection is unique to HPC;
- a small set of tested models represents all future models;
- zero observed attacks implies complete security; or
- any single baseline defense solves the problem.

---

## 14. Related Work Structure

### 14.1 Prompt injection and LLM-agent security

Discuss indirect prompt injection, tool-mediated attacks, agent security benchmarks, and defenses. Position HPC-AgentSec as an HPC-specific benchmark rather than a new discovery of prompt injection.

### 14.2 Benchmarks for tool-using agents

Discuss benchmark design principles: realistic tasks, adversarial cases, utility-security tradeoffs, reproducibility, and adaptive attacks.

### 14.3 AI agents for scientific and HPC workflows

Establish that agents are being explored for scientific automation, software assistance, job management, and facility interaction.

### 14.4 HPC security and user separation

Discuss identity, project access, scheduler policy, shared filesystems, user separation, secure workflow execution, and zero-trust approaches.

### 14.5 Scientific integrity and provenance

Connect security failures to reproducibility, provenance, and trustworthy scientific computing.

---

## 15. Discussion

### 15.1 Benchmark realism

Discuss which aspects use real Slurm and filesystem behavior and which are emulated. Explain why synthetic data and mocked egress are necessary for safe reproducibility.

### 15.2 Task-policy construction

Task-scoped policies are essential but may be subjective. Mitigate this by:

- documenting the policy authoring process;
- using multiple reviewers;
- publishing manifests;
- distinguishing hard prohibitions from debatable actions; and
- reporting sensitivity to policy choices.

### 15.3 Adaptive attackers

Initial cases may use fixed injections. A later benchmark extension can include adaptive attack generation, but the first release should prioritize validated, interpretable cases.

### 15.4 Generalizability

Results may vary by scheduler, filesystem, agent framework, model, and center policy. The benchmark should describe these as explicit dimensions rather than universal assumptions.

### 15.5 Benchmark maintenance

Version the benchmark, preserve old test cases, document changes, and maintain a hidden or held-out test set if the benchmark becomes widely used.

---

## 16. Ethics and Safety

- Run only on isolated, authorized infrastructure.
- Use synthetic secrets and datasets.
- Route external-looking traffic to a mock endpoint by default.
- Never package real credentials or cluster-specific secrets.
- Redact reusable operational attack payloads from the paper when they add little scientific value.
- Include a responsible-release statement explaining that the artifact is designed for defensive testing.
- Provide resource limits to prevent accidental scheduler abuse.

---

## 17. Conclusion Draft

LLM agents introduce a task-boundary problem for scientific computing. An agent may be correctly authenticated, legitimately authorized, and operationally useful while still being redirected by untrusted scientific artifacts, tool outputs, shared storage, or peer agents. Existing agent-security benchmarks establish the importance of evaluating prompt injection, but they do not capture the scheduler, project, filesystem, resource, provenance, and scientific-integrity boundaries of HPC environments.

HPC-AgentSec provides a benchmark foundation for measuring this risk. It combines realistic HPC tasks, controlled attack cases, deterministic system-level oracles, and joint utility-security metrics. By making unauthorized data access, sensitive-data exposure, workflow corruption, unsafe execution, resource misuse, and cross-agent contamination measurable, the benchmark enables reproducible comparison of models, agents, and defenses. The goal is not to declare a complete solution, but to provide the evaluation infrastructure needed to build and assess secure agentic scientific-computing systems.

---

## 18. Recommended Final Title and Alternatives

### Recommended

**Trusted Credentials, Untrusted Behavior: Benchmarking LLM-Agent Security in High-Performance Computing**

### Alternatives

- **HPC-AgentSec: A Benchmark for LLM-Agent Security in High-Performance Computing**
- **Benchmarking Hijacked Authorized Agents in Scientific Computing**
- **Can LLM Agents Safely Operate HPC Systems? An Evaluation Benchmark**
- **HPC-AgentSec: Tasks, Attacks, and Defenses for Agentic Scientific Computing**
