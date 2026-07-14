# Trusted Credentials, Untrusted Behavior: A Case for Studying Hijacked Authorized Agents in HPC

> **Paper type:** position / vision paper
> **Status:** draft — author list, venue, and final title to be finalized before submission
> **Companion effort:** this position paper motivates a forthcoming benchmark and empirical study, working name **HPC-AgentSec** (see `hpc_agentsec_benchmark_paper_draft.md` and `hpc_agentsec_benchmark_development_plan.md` in this repository)

## Abstract

Large language model (LLM) agents are beginning to operate inside high-performance computing (HPC) environments: monitoring Slurm jobs, debugging failed builds, analyzing simulation output, and orchestrating multi-stage scientific workflows. These agents run with the credentials and scheduler authority of the users who launch them. That is precisely what makes them dangerous in a new way. An HPC agent does not need a stolen password or a kernel exploit to cause harm — it only needs to read a poisoned log, a compromised tool description, or a message from another agent, and it can be redirected into actions that remain fully authenticated and authorized at the account level while violating the boundary of the task it was asked to perform. We call this the **hijacked authorized agent** problem. We argue that this problem is not adequately addressed by either of the two literatures it sits between. LLM-agent security research has produced strong general threat models, benchmarks, and mechanisms for indirect prompt injection and tool misuse, but almost entirely in web, enterprise, and personal-assistant settings — not in scheduler-managed, multi-project, shared-filesystem environments. HPC security research has produced mature controls for identity, isolation, and workflow security, but assumes a human is the source of intent behind every authenticated action — an assumption that no longer holds once an LLM agent is interposed between the user and the cluster. This paper defines the hijacked authorized agent threat model for HPC, taxonomizes the HPC-specific attack surfaces it creates, analyzes why existing HPC controls do not close the gap, and lays out a research agenda — including an empirical benchmark now in development — for studying and mitigating it.

---

## 1. Introduction

HPC systems are becoming interactive scientific environments rather than purely batch-oriented ones. Users increasingly delegate routine but consequential work — reading logs, repairing job scripts, installing software, summarizing large output directories, and steering multi-stage simulations — to LLM agents that can read files, invoke command-line tools, call scheduler commands, and communicate with local or remote model backends. This is not speculative: agent frameworks have already been connected to real HPC resource managers and tested on production-scale scientific workflows [1, 2, 4], multi-agent systems have been used to automate HPC software compilation and deployment [3], and HPC centers are already publishing user guidance about agentic coding tools appearing on their clusters [5]. The trajectory is toward more autonomy, not less.

This creates a security problem that does not fit cleanly into either of the two bodies of work that study its component parts.

LLM-agent security research has established that agents which consume untrusted external content can be manipulated through indirect prompt injection [6], that tool-using agents fail in high-stakes ways even when reasonably careful [7], that these failures can be measured with realistic tasks and adaptive attacks [8], and that the attack surface extends to tool selection [11] and inter-agent/inter-protocol communication [9, 10]. But the settings in which this is studied — email clients, e-banking, travel booking, Slack, generic tool sandboxes — do not have schedulers, shared parallel filesystems, project-scoped multi-tenant storage, or the notion that a valid user account may span multiple projects while a given task should not.

HPC security research has, separately, built mature answers to "who can access what": zone-based reference architectures for access, management, compute, and storage [13]; enforced per-user separation of processes, filesystem access, network traffic, and accelerators [12]; and federated identity and zero-trust designs that unify authentication and access control across AI and HPC infrastructure [14]. All of this assumes that the entity making a decision behind an authenticated session is a human, or software the human directly and deterministically controls. None of it asks whether a *sequence of authorized actions*, taken by software that reads adversarial content as part of its normal operation, correctly reflects what the user or the site intended.

The hijacked authorized agent threat model exists in the space between these two literatures: **the identity is real, the credentials are valid, the authorization is technically correct — and the behavior is not what anyone intended.**

### 1.1 Thesis

We argue three things in this paper:

1. **The threat is structurally different from generic prompt injection**, because HPC introduces authority and persistence dimensions — scheduler-mediated resource consumption, multi-project account scope, shared and durable parallel-filesystem state, and scientific-integrity/provenance requirements — that general agent-security settings do not have and that determine what "unsafe" even means in this domain.
2. **Neither literature currently measures it.** LLM-agent security benchmarks do not model scheduler authority or shared HPC storage; HPC security controls do not model semantic redirection of an authenticated agent.
3. **The gap is closing on its own schedule, not ours.** HPC agents are being deployed for real workflows now [1, 2, 3, 4], and site operators are already worried enough to write informal guidance about it [5], which means the research community has a limited window to characterize the threat before ad hoc, under-evaluated mitigations become the de facto standard.

### 1.2 Contributions

1. A precise definition of the **hijacked authorized agent** threat model for HPC, distinguishing it from conventional privilege escalation and from generic indirect prompt injection (§4).
2. A **taxonomy of HPC-specific attack surfaces**: shared parallel-filesystem poisoning, scheduler-induced log and co-location channels, tool/module/MCP poisoning, cross-project data leakage, and coordinated multi-agent exfiltration (§5).
3. A **defense-gap analysis** showing which existing HPC and agent-security controls detect, partially detect, or miss each attack surface (§6).
4. A **research agenda**, including the security requirements a trustworthy HPC-agent platform would need to satisfy, and a pointer to an empirical benchmark (HPC-AgentSec) now under development to measure the problem this paper defines (§7).

### 1.3 Scope and non-goals

This paper is a threat characterization and research agenda, not an empirical evaluation. It does not report attack success rates, does not claim a specific model or agent framework is unsafe, and does not propose a complete defense. It also does not attempt to cover model-training-time poisoning, weight extraction, GPU microarchitectural side channels, kernel/hypervisor compromise, or general content-safety jailbreaking — these are real concerns but orthogonal to the specific claim here, which is about environment-mediated redirection of an agent that already holds valid credentials.

---

## 2. Background

### 2.1 LLM agents are entering HPC

Recent systems work demonstrates that the connection between LLM agents and HPC resources is now a functioning integration path rather than a hypothetical one. Ma et al. connect LangChain/LangGraph agents to HPC resources through Parsl and demonstrate agent-driven molecular dynamics workflows on ALCF's Polaris system [1]. Rosendo et al. describe a modular AI-agent architecture — an LLM interface, multi-agent decision-making, programmable facility APIs, and provenance-aware infrastructure — deployed for cross-facility autonomous experimentation between ORNL's Manufacturing Demonstration Facility and its Oak Ridge Leadership Computing Facility [2]. Mondesire et al. report a multi-agent LLM system that autonomously builds and repairs over 200 HPC software packages, reading compiler errors and build logs and iteratively revising build scripts [3] — a workflow that, by construction, feeds tool and compiler output directly into an agent's decision loop. Dawson et al.'s LARA-HPC frames the open problem explicitly: agentic systems can automate scientific workflows on supercomputers, but correctness, reproducibility, and *safe interaction with computational resources* remain unresolved deployment obstacles [4]. And outside the research literature, HPC centers are already responding to organic adoption: Aalto's scientific computing group documents that users have started running Claude Code and OpenAI Codex against their Triton cluster for coding assistance and Slurm job management, and explicitly flags prompt injection, malicious skills, external repositories, and code/data confidentiality as live concerns for site operators, not hypothetical ones [5].

Taken together, this literature establishes that agentic HPC is real and growing, but its focus is capability and architecture — provenance, reproducibility, orchestration — rather than adversarial robustness. None of these papers evaluates what happens when the content an agent reads during normal operation is adversarial.

### 2.2 LLM-agent security: known attack mechanisms

The mechanism side of this problem is well studied outside HPC. Greshake et al. established indirect prompt injection as a practical attack class: adversarial instructions embedded in content an LLM-integrated application retrieves — not content the user typed — can hijack the application's behavior, exfiltrate data, and persist across sessions [6]. Ruan et al.'s ToolEmu shows that tool-using agents fail in materially harmful ways at a non-trivial rate even under careful evaluation, using an LM-emulated sandbox to make this measurable without needing to instantiate every real tool [7]. Debenedetti et al.'s AgentDojo operationalizes this further into a reusable benchmark: 97 realistic tasks and 629 security test cases spanning email, banking, travel, and workspace domains, explicitly designed to measure *utility under attack* jointly with attack success rather than either alone [8] — a methodological choice we adopt for the HPC setting (§7.2). More recent work extends the attack surface: Ferrag et al. catalog over thirty attack techniques across input manipulation, model compromise, system/privacy attacks, and inter-agent protocol exploits (MCP, ACP, ANP, A2A) [9], and Wang et al.'s systematization of prompt-injection threats highlights that many existing defenses and benchmarks implicitly assume an agent should distrust its environment — an assumption that breaks down for agents, like HPC agents, that are *authorized to rely on* runtime observations such as file contents, logs, and tool output as a normal part of the job [10]. Shi et al. show that the vulnerability extends specifically to tool selection: a malicious tool document, crafted without white-box access to the target model, can be optimized to make an agent consistently choose an attacker-controlled tool over legitimate alternatives [11] — a mechanism that maps directly onto HPC module systems, shared scripts, and MCP-based tool servers (§5.3).

This literature gives HPC a vocabulary of mechanisms — indirect injection, tool-output poisoning, tool-selection manipulation, protocol-level exploits — but its benchmarks and case studies are built around web and enterprise semantics: an email inbox, a bank account, a travel itinerary. None of it encodes what it means for an agent to hold scheduler authority, to have legitimate access to more than one project while a task should touch only one, or to interact with filesystem state that persists across jobs, users, and other agents.

### 2.3 HPC security: established controls and their assumptions

HPC security has, in parallel, matured its own answers to a different question. NIST SP 800-223 defines a zone-based reference architecture — access, management, compute, and storage zones — that standardizes how HPC sites reason about and communicate their security posture, and analyzes HPC-specific threats against it [13]. Prout et al. describe enhanced user separation deployed at the MIT Lincoln Laboratory Supercomputing Center: enforced isolation of processes, filesystem access, network traffic, and accelerators, designed so that each of over a thousand users effectively experiences a personal HPC system [12]. Alam et al. describe a federated single-sign-on and zero-trust co-design spanning AI and HPC digital research infrastructure, unifying multi-factor authentication and time-limited role-based access across heterogeneous facilities [14].

These are all strong, deployed answers to *who is allowed to do what*. They are not designed to, and do not, answer a different question: given that an action was performed by a correctly authenticated, correctly authorized account, was the *intent* behind that action the user's, or was it injected by something the agent read along the way? A POSIX permission check, a scheduler accounting record, or a zero-trust access decision has no way to distinguish "the user asked for this" from "the agent was told to do this by a poisoned log file the user never saw." That distinction is exactly what the hijacked authorized agent threat model is about.

---

## 3. The Gap

Putting §2.1–§2.3 together: agentic-HPC research shows agents are being connected to real scheduler and filesystem resources, but treats adversarial robustness as future work rather than a present concern. LLM-agent security research shows that agents consuming untrusted content can be manipulated in serious ways, and has built benchmark methodology for measuring it, but has not modeled scheduler authority, project-scoped multi-tenancy, shared parallel storage, or scientific-integrity consequences. HPC security research shows that access, identity, and isolation can be rigorously engineered and audited, but assumes the authenticated actor's intent is trustworthy by construction.

No existing work systematically characterizes what happens at the intersection: an LLM agent, holding valid HPC credentials and scheduler authority, redirected by content it encountered during normal, authorized operation. To the best of our knowledge, this is the first paper to make that intersection the primary object of study.

---

## 4. Threat Model: The Hijacked Authorized Agent

### 4.1 Definition

An agent is **hijacked** when adversarial content encountered during normal operation — a file it read, a log it inspected, a tool's output, a message from a peer agent — causes it to perform an action that violates the scope of its assigned task, while every individual action it takes remains within what the user's account and the agent's granted tool access technically permit. The agent does not escalate privilege in the conventional sense: it does not need root, does not need to bypass POSIX permissions, and does not need to steal a credential. It needs only to be redirected while remaining, at every step, "authorized."

This is what separates the threat from ordinary indirect prompt injection as usually presented: in HPC, the account performing the hijacked action frequently has *broader* standing authority than the task requires — for example, legitimate membership in several projects — so a hijacked action can look, to a system-level audit log, identical to an unusual-but-permitted request from a trusted user. The security-relevant boundary is not the account's authority; it is the *task's* authority, and no conventional HPC control currently represents that boundary as a first-class, checkable object.

### 4.2 Assumptions

- the user intentionally and legitimately launches the agent for a specific task;
- the agent has valid, correctly provisioned access to its assigned workspace and tools;
- the cluster control plane, scheduler, and any benchmark or monitoring harness are trusted;
- the attacker does not have root access and does not modify model weights;
- the attacker's only foothold is the ability to influence content the agent will read, execute, or receive during normal operation — a file, a log, a tool's output, shared state, or a message from another agent.

### 4.3 Attacker capability classes

| Class | Capability | Representative HPC source |
|---|---|---|
| C1 | Write or influence a scientific artifact the agent will read | simulation log, metadata field, README, result file |
| C2 | Influence scheduler-adjacent output | job stdout/stderr, wrapper diagnostics, accounting note |
| C3 | Control a tool's description or output | build helper, converter, module description, MCP tool server |
| C4 | Write to shared node or filesystem state | scratch space, cache, shared collaboration path |
| C5 | Control or hijack a peer agent | inter-agent message, staged intermediate artifact |

A rigorous case for this threat model requires that each capability class be minimal and explicit — an attack that silently assumes a stronger foothold than it declares is not evidence for the "authorized agent" framing, it is evidence for a conventional access-control failure, and the two should not be conflated.

---

## 5. HPC-Specific Attack Surface Taxonomy

General agent-security work already covers the *mechanism* dimension of these attacks (injection, poisoning, protocol exploits — §2.2). What is missing is the HPC-specific *surface* through which the mechanism reaches the agent and the *consequence* that follows. We separate the two deliberately, because equating every injection channel with the same outcome collapses distinctions — data theft, resource abuse, and silent scientific corruption — that matter differently to different stakeholders (a PI cares about corrupted results in a way a security team cares about credential theft).

**5.1 Shared parallel-filesystem poisoning.** HPC storage is durable and shared across jobs, users, and time in a way that a web session's context window is not. An adversarial instruction written into a shared scratch path, a cache, or a collaboration directory can wait — persisting past the job or session that created it — for any later agent, possibly belonging to a different user, to read it. This is a fundamentally different persistence model from a single poisoned document in an email inbox.

**5.2 Scheduler-induced co-location and log injection.** Job stdout/stderr, `sacct`-style accounting notes, and wrapper diagnostics are scheduler-adjacent text that an HPC agent is *expected* to read as part of its job — diagnosing a failure requires reading the failure's own output. An attacker who can influence what a co-located or related job writes to shared or predictable output paths gains a channel directly into the debugging agent's context, and the consequence is not limited to data exposure: it extends to submitting, resizing, or resubmitting jobs against the user's own allocation.

**5.3 Tool, module, and MCP poisoning.** HPC workflows depend on rich, often user- or community-maintained software stacks: environment modules, build tools, post-processing scripts, and increasingly MCP-based tool servers. Shi et al.'s demonstration that a tool's *description* — not just its output — can be optimized to manipulate an agent's tool-selection process [11] maps directly onto this surface: a poisoned module description or MCP tool manifest can redirect an agent toward an attacker-preferred action without ever touching the agent's runtime output.

**5.4 Cross-project data leakage.** A defining feature of HPC accounts is that a single user frequently has legitimate standing access to multiple projects or datasets, while any given task should touch only one. This is the concrete instantiation of the "user-broad, task-narrow" authority gap that §4.1 identifies as structural to the threat model, and it has no analogue in single-tenant consumer-agent settings.

**5.5 Coordinated multi-agent exfiltration.** As multi-agent HPC workflows become more common — planners delegating to worker agents, one agent preparing data for another [2, 3] — a compromised or poisoned intermediate artifact written by one agent can be consumed by a second agent with different, and possibly broader, access. Data can then cross a trust boundary without any single agent's individual actions looking anomalous in isolation, and it can leave the cluster through a channel that is not obviously malicious: a normal, encrypted request to an LLM backend the agent is authorized to use.

---

## 6. Why Existing Controls Are Insufficient

| Existing control | What it verifies | What it misses for hijacked agents |
|---|---|---|
| Authentication / SSO / zero-trust identity [14] | Who is the user | Whether the *intent* behind an authenticated action was the user's or was injected |
| POSIX permissions, zone-based access architecture [13] | Which files/zones the account may reach | Whether the *task* should reach them, when the account legitimately can |
| Scheduler accounting and quotas | How much was consumed and by whom | Whether the consumption was requested by the user or induced by poisoned content |
| Enforced user/process/network separation [12] | Isolation between different users' work | Redirection *within* one user's own authorized session |
| Filesystem/network auditing, DLP | What left, over which channel | Egress through a channel the agent is authorized to use, e.g. a normal LLM API call |
| Per-agent action logging | What the agent did | *Why* — whether an action traces to legitimate task intent or to adversarial content the agent consumed |

The pattern across every row is the same: existing HPC controls are built to answer "was this action within the account's authority," and they answer it correctly. They are not built to answer "was this action within the *task's* authority," which is the question the hijacked authorized agent threat model raises, and none of the standard audit surfaces — accounting logs, POSIX ACLs, network allowlists — carry the information needed to answer it after the fact unless the agent framework itself records task-scoped provenance as a first-class signal.

---

## 7. Research Agenda

### 7.1 Security requirements for HPC-agent platforms

The gap analysis in §6 motivates a concrete list of properties an HPC-agent platform would need in order to make hijacked-agent incidents detectable or preventable, rather than indistinguishable from legitimate broad-account activity:

- **Task-scoped authority**, enforced independently of the account's standing access — the platform must be able to represent and check "permitted for this task" as distinct from "permitted for this account."
- **Provenance-aware context handling** — every piece of content entering an agent's context (user instruction, file content, tool output, peer-agent message) should carry a trust/source label the agent's decision process can condition on.
- **Egress control** for agent-to-model traffic, since data can leave through a channel — an LLM API call — that is authorized and encrypted by default and therefore invisible to conventional network monitoring aimed at exfiltration.
- **Shared-filesystem hygiene**, given that scratch and collaboration storage persists adversarial content across jobs, users, and agents in a way session-scoped web contexts do not.
- **Tool and module trust**, extending existing software-supply-chain practice to cover tool *descriptions* and MCP manifests, not just binaries.
- **Scheduler-aware containment**, so that a hijacked agent cannot translate a context-level compromise into unbounded resource consumption against the user's allocation.
- **Cross-agent correlation**, so that staged, multi-hop exfiltration across cooperating agents is visible as a single event rather than several individually unremarkable ones.

### 7.2 Toward a benchmark: HPC-AgentSec

A threat model and a taxonomy motivate but do not by themselves measure anything. The natural next step — already underway as a companion effort — is an empirical benchmark that operationalizes §4 and §5 into realistic tasks, task-scoped policies, injected attack cases, deterministic security oracles, and joint utility/security metrics, following the general methodology established by AgentDojo [8] but built around HPC-native semantics: Slurm-mediated scheduler actions, project-scoped filesystem policy, and scientific-integrity oracles that check for silent parameter, filter, or provenance tampering rather than only data exposure. That effort (working name **HPC-AgentSec**; see the companion benchmark paper draft and development plan in this repository) is scoped to answer, empirically, the questions this position paper raises analytically: how often current agents follow adversarial HPC context, which infrastructure surfaces are highest-risk, and which existing or proposed controls actually reduce risk without destroying utility.

### 7.3 Open questions

Beyond the benchmark itself, several questions remain open and are, in our view, worth independent study:

- How should "task scope" be authored and validated when it is inherently somewhat subjective, and how much does that subjectivity affect the reliability of security measurements built on it?
- Do defenses that work well in web/enterprise agent settings (structured provenance labels, tool allowlists) transfer to HPC's scheduler and filesystem semantics, or do they need HPC-specific redesign?
- What is the right locus of enforcement — the agent framework, the scheduler, the filesystem, or a dedicated runtime monitor — for task-scoped policy, given that HPC sites differ widely in what they can modify?
- As multi-agent scientific workflows become more common, how should cross-agent trust be represented so that staged exfiltration is detectable without requiring every agent to fully trust every other agent's output?

---

## 8. Conclusion

LLM agents are being connected to real HPC schedulers, filesystems, and scientific workflows now, and HPC sites are already noticing and worrying about it [1, 2, 3, 5]. The security question this raises — what happens when a correctly authenticated, correctly authorized agent is redirected by adversarial content it encounters during normal operation — is not answered by either of the literatures adjacent to it. LLM-agent security research has the mechanisms but not the HPC-specific surfaces or consequences; HPC security research has the access-control rigor but not a way to represent task-scoped intent beneath account-level authority. We have defined the hijacked authorized agent threat model to name this gap precisely, taxonomized the HPC-specific attack surfaces that follow from it, shown why existing controls do not close it, and outlined a research agenda — including an empirical benchmark now in development — to study and eventually mitigate it. The goal is not to declare HPC agents unsafe; it is to make sure the field can tell the difference between an agent that is safe and one that has simply not yet been tested against its own environment.

---

## References

[1] Heng Ma, Alexander Brace, Carlo Siebenschuh, Greg Pauloski, Ian Foster, and Arvind Ramanathan. Connecting Large Language Model Agent to High Performance Computing Resource. arXiv:2502.12280, 2025.

[2] Daniel Rosendo, Stephen DeWitt, Renan Souza, Phillipe Austria, Tirthankar Ghosal, Marshall McDonnell, Ross Miller, Tyler Skluzacek, James Haley, Bruno Turcksin, Jesse McGaha, Benjamin Mintz, Feiyi Wang, Mallikarjun Shankar, Sarp Oral, and Rafael Ferreira da Silva. AI Agents for Enabling Autonomous Experiments at ORNL's HPC and Manufacturing User Facilities. In *Proceedings of the SC'25 Workshops (SCW '25)*, 2025.

[3] Sean Mondesire, Emmanuel Nsiye, Bulent Soykan, and Glenn Martin. Automating HPC Software Compilation, Deployment, and Error Resolution through an LLM-based Multi-Agent System. In *Practice and Experience in Advanced Research Computing (PEARC '25)*, 2025. Best Paper, Systems and System Software track.

[4] William Dawson, Louis Beal, Yoann Curé, Giuseppe Fisicaro, Dorian Rolland, and Luigi Genovese. LARA: Validation-Driven Agentic Supercomputer Workflows for Atomistic Modeling. arXiv:2604.22571, 2026.

[5] Aalto Scientific Computing. AI Agents on HPC. Aalto Triton user documentation. https://scicomp.aalto.fi/triton/usage/ai-agents/ (accessed 2026).

[6] Kai Greshake, Sahar Abdelnabi, Shailesh Mishra, Christoph Endres, Thorsten Holz, and Mario Fritz. Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection. In *Proceedings of the 16th ACM Workshop on Artificial Intelligence and Security (AISec '23)*, 2023. arXiv:2302.12173.

[7] Yangjun Ruan, Honghua Dong, Andrew Wang, Silviu Pitis, Yongchao Zhou, Jimmy Ba, Yann Dubois, Chris J. Maddison, and Tatsunori Hashimoto. Identifying the Risks of LM Agents with an LM-Emulated Sandbox. In *International Conference on Learning Representations (ICLR)*, 2024 (Spotlight). arXiv:2309.15817.

[8] Edoardo Debenedetti, Jie Zhang, Mislav Balunović, Luca Beurer-Kellner, Marc Fischer, and Florian Tramèr. AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents. In *Advances in Neural Information Processing Systems (NeurIPS)*, 2024. arXiv:2406.13352.

[9] Mohamed Amine Ferrag, Merouane Debbah, Leandros Maglaras, et al. From Prompt Injections to Protocol Exploits: Threats in LLM-Powered AI Agents Workflows. arXiv:2506.23260, 2025.

[10] Peiran Wang, Xinfeng Li, Chong Xiang, Jinghuai Zhang, Ying Li, Lixia Zhang, Xiaofeng Wang, and Yuan Tian. The Landscape of Prompt Injection Threats in LLM Agents: From Taxonomy to Analysis. arXiv:2602.10453, 2026.

[11] Jiawen Shi, Zenghui Yuan, Guiyao Tie, Pan Zhou, Neil Zhenqiang Gong, and Lichao Sun. Prompt Injection Attack to Tool Selection in LLM Agents. In *Network and Distributed System Security Symposium (NDSS)*, 2026. arXiv:2504.19793.

[12] Andrew Prout, Albert Reuther, Michael Houle, Michael Jones, Peter Michaleas, LaToya Anderson, William Arcand, Bill Bergeron, David Bestor, Alex Bonn, Daniel Burrill, Chansup Byun, Vijay Gadepally, Matthew Hubbell, Hayden Jananthan, Piotr Luszczek, Lauren Milechin, Guillermo Morales, Julie Mullen, Antonio Rosa, Charles Yee, and Jeremy Kepner. HPC with Enhanced User Separation. In *S-HPC Workshop, SC'24*, 2024. arXiv:2409.10770.

[13] National Institute of Standards and Technology. Special Publication 800-223: High-Performance Computing (HPC) Security: Architecture, Threat Analysis, and Security Posture. NIST, 2024.

[14] Sadaf R. Alam, Christopher Woods, Matt Williams, Dave Moore, Isaac Prior, Ethan Williams, Anna Price, James Womack, Simon McIntosh-Smith, Fan Yang-Turner, Matt Pryor, and Ilja Livenson. Federated Single Sign-On and Zero Trust Co-design for AI and HPC Digital Research Infrastructures. In *Proceedings of the SC'24 Workshops (SCW '24)*, 2024. arXiv:2410.18411.
