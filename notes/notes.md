##     Trusted Credentials, Untrusted Behavior: Characterizing LLM-Agent Threats in High-Performance Computing

Prior work studies LLM-agent security mostly in web, enterprise, tool-use, and benchmark environments; prior HPC security work studies identity, isolation, workflow security, and multi-tenancy; and recent HPC-agent work studies productivity, automation, and scientific workflows. But there is very little work that systematically characterizes how LLM-agent threats manifest in HPC’s shared-filesystem, scheduler-managed, multi-user, multi-project environment.

### Literature Study

1. Closest literature: AI agents are entering HPC, but security is not the main focus

There are now several papers showing that LLM agents are plausible in HPC/scientific-computing workflows.

One relevant paper is “Connecting Large Language Model Agent to High Performance Computing Resource”, which connects LangChain/LangGraph agents to HPC resources through Parsl and tests molecular-dynamics workflows on ALCF Polaris. This supports your motivation that agents may need access to real HPC execution resources, not just toy tools.  

Another close paper is “AI Agents for Enabling Autonomous Experiments at ORNL’s HPC and Manufacturing User Facilities.” It proposes a modular AI-agent architecture integrating an LLM interface, multi-agent decision making, programmable facility APIs, and provenance-aware infrastructure for autonomous cross-facility experimentation. This is highly relevant because it shows agents being considered for real facility-level scientific workflows, but its emphasis is architecture, provenance, and reproducibility rather than adversarial threat characterization.  

There is also “Automating HPC Software Compilation, Deployment, and Error Resolution through an LLM-based Multi-Agent System” from PEARC 2025. It directly supports the idea that multi-agent systems may be used for HPC software deployment and debugging — exactly the kind of workflow where agents may read logs, invoke tools, edit files, and interact with schedulers.  

Recent work such as LARA-HPC argues that agentic systems could automate scientific workflows on supercomputers, while noting deployment challenges around correctness, reproducibility, and safe interaction with computational resources. This is useful background, but it still does not appear to systematically study prompt injection, shared-filesystem poisoning, co-location attacks, or LLM API exfiltration in HPC.  

A practical signal also comes from Aalto’s “AI Agents on HPC” user guidance, which says users have started using Claude Code or OpenAI Codex for coding assistance, Slurm monitoring, and job management, and it explicitly warns about prompt injection, malicious skills, external repositories, and code/data confidentiality. This is not a research paper, but it is valuable evidence that HPC sites are already seeing these tools and are worried about exactly the risk direction you want to study.  

**Takeaway**: There is enough literature to justify that AI agents are entering HPC, but the existing work mostly treats them as productivity/scientific-workflow tools. That leaves room for a paper focused on security consequences.

2. LLM-agent security literature is active, but mostly not HPC-specific

The foundational paper here is Greshake et al., “Not What You’ve Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.” It argues that LLM-integrated applications blur the boundary between data and instructions, and shows that adversarial prompts embedded in retrieved data can manipulate applications, steal data, and influence API calls. This is directly relevant to your threat model, but the setting is general LLM-integrated applications rather than HPC clusters.  

ToolEmu is also highly relevant. It evaluates risks in LM agents with tool use and shows that even the safest evaluated agent still had severe failures in a significant fraction of cases. This supports your claim that tool-using agents can leak private data or cause harmful actions, but again the benchmark is broad and tool-centric rather than scheduler/filesystem/HPC-centric.  

AgentDojo is another key benchmark. It provides realistic tasks, security test cases, and adaptive attacks for evaluating prompt-injection attacks and defenses in agents. It is very relevant methodologically: your HPC threat-characterization paper could be presented as an HPC-specific analogue or extension of this benchmark style.  

There is also a growing survey literature. “From Prompt Injections to Protocol Exploits” provides a unified threat model for LLM-agent ecosystems, covering host-to-tool and agent-to-agent communication and cataloging many attack techniques, including protocol-level vulnerabilities. This is important related work because your paper should not claim general novelty for LLM-agent threats; instead, it should claim domain-specific novelty for HPC.  

A recent SoK, “The Landscape of Prompt Injection Threats in LLM Agents,” is especially useful because it says existing defenses and benchmarks often overlook context-dependent tasks where agents are authorized to rely on runtime environmental observations. That point maps well to HPC: an HPC agent must inspect files, logs, scheduler output, job states, and tool results, so simply suppressing external context is not practical.  

Tool-selection attacks are also relevant. ToolHijacker shows that malicious tool documents can manipulate an agent’s tool-selection process, forcing it to choose attacker-preferred tools. This maps naturally to HPC module environments, user-installed scripts, shared software stacks, MCP servers, and “skills” used by coding agents.  

**Takeaway**: The agent-security literature gives you threat mechanisms — indirect prompt injection, tool poisoning, protocol exploits, tool-selection manipulation, data exfiltration — but it does not deeply study how those mechanisms interact with HPC-specific infrastructure.

3. HPC security literature exists, but it mostly assumes human users or conventional software

The most relevant HPC-security paper I found is “HPC with Enhanced User Separation.” It discusses techniques deployed at MIT Lincoln Laboratory Supercomputing Center to enforce separation across processes, filesystem access, network traffic, and accelerators, aiming to make each user feel like they are running on a personal HPC system. This is highly relevant because it confirms that process/filesystem/network separation is an active HPC concern, but it is not specifically about LLM agents being semantically hijacked through untrusted data.  

NIST’s SP 800-223 High-Performance Computing Security is also useful background. It emphasizes HPC access zones, authentication, access rights, and filesystem security boundaries. This supports your discussion of conventional HPC security controls, but it does not directly address autonomous agents that inherit valid credentials and then misuse them due to prompt injection.  

“Federated Single Sign-On and Zero Trust Co-design for AI and HPC Digital Research Infrastructures” is useful because it explicitly links AI, HPC, identity and access management, zero trust, multi-factor authentication, and time-limited role-based access. However, it focuses on identity/access-control architecture, not the problem of a valid authenticated agent being redirected by poisoned inputs.  

There is also work on Secure HPC workflows for privacy-sensitive data, including secure partitions, encryption, and strict workflow security models. This is relevant for sensitive-data contexts, but it is still not about LLM-agent instruction hijacking or task-level behavioral misuse.  

**Takeaway**: HPC security has strong work on isolation, identity, secure workflows, and zero trust, but less on semantic control-flow attacks where the software is authenticated, authorized, and behaving through a valid user account but has been manipulated by adversarial language/data.

4. Relevant Papers

| Cluster | Papers / sources | How to use them |
| --- | --- | --- |
| AI agents for HPC/science | Connecting LLM Agent to HPC Resource; ORNL autonomous experiments; PEARC 2025 LLM multi-agent HPC compilation; LARA-HPC | Establish that agentic HPC is realistic and emerging. |
| LLM-agent security | Greshake indirect prompt injection; ToolEmu; AgentDojo; ToolHijacker; MCP/protocol-exploit survey; prompt-injection SoK | Establish known attack mechanisms and benchmarks. |
| HPC security | NIST SP 800-223; HPC with Enhanced User Separation; Secure HPC; federated SSO/zero-trust for AI+HPC | Establish existing HPC defenses and explain why they do not cover hijacked authorized agents. |

### The Gap

Existing LLM-agent security research studies prompt injection, tool poisoning, protocol exploits, and agent hijacking, but primarily in web, enterprise, personal-assistant, software-development, or synthetic benchmark settings. Existing HPC security research studies identity, access control, workflow security, user separation, and multi-tenancy, but generally assumes human-driven jobs or conventional software. Existing HPC-agent research demonstrates LLM agents for scientific workflows, compilation, simulation, and autonomous experiments, but does not systematically characterize the security risks created when such agents operate inside shared, scheduler-managed HPC environments.

### Contribution
1. Threat model: Define the hijacked authorized agent in HPC: an agent with valid user credentials and scheduler authorization that is redirected by untrusted data, tool outputs, or shared infrastructure.
2. Taxonomy: Identify HPC-specific attack surfaces: shared parallel filesystem poisoning, scheduler-induced co-location, tool/module/MCP poisoning, cross-project data leakage, and coordinated multi-agent exfiltration.
3. Proof-of-concept demonstrations: Show attacks on representative HPC-agent workflows: Slurm monitoring, job-script debugging, simulation-output analysis, software build troubleshooting, and multi-agent workflow orchestration.
4. Defense gap analysis: Evaluate which existing controls detect or miss these attacks: authentication, POSIX permissions, Slurm accounting, filesystem auditing, DLP, network monitoring, sandboxing, and per-agent logging.
5. Security requirements: Derive requirements for future HPC-agent platforms: task-scoped authority, provenance-aware context handling, egress control, shared-filesystem hygiene, tool trust, scheduler-aware containment, and cross-agent correlation.

To the best of our knowledge, this is the first systematic characterization of LLM-agent security threats in scheduler-managed, shared-filesystem HPC environments.

