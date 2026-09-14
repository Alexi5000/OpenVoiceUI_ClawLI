# Implementation Plan: OpenClaw Multi-Agent Orchestration System

## Architecture Overview

Two-tier system:
1. **OpenVoiceUI** (port 5001) — Voice interface. ONLY Prime, Veronica, Rose have voice.
2. **OpenClaw Dashboard** (port 18789) — All agents. Department leads, squad leads, and 100+ specialists live here. The voice council delegates to them via OpenClaw native `sessions_spawn`, `subagents`, and `agentToAgent` tools.

No Mastra. No LangGraph. Pure OpenClaw agent infrastructure.

---

## Phase 1: Foundation — Enable Multi-Agent Infrastructure

### 1a. Enable agent-to-agent communication in `openclaw.json`
- Set `tools.agentToAgent.enabled: true`
- Build allowlist for all agents that need cross-communication
- Increase `maxConcurrent` to 8 and `subagents.maxConcurrent` to 16 (fleet of 100+ needs headroom)

### 1b. Create global shared skills directory
- `mkdir ~/.openclaw/skills` for skills available to ALL agents
- Install key ClawHub/skills.sh skills: `coding-agent`, `github`, `gh-issues`, `healthcheck`

### 1c. Create agent factory script
- Python script at `setup/create-agent.py`
- Takes: agent_id, display_name, emoji, role description, domain, reports_to, team
- Creates: workspace with IDENTITY.md, SOUL.md, AGENTS.md, USER.md, TOOLS.md
- Registers agent via `openclaw agents add`
- Sets identity via `openclaw agents set-identity`
- Creates workspace-level `skills/` directory for domain-specific skills

---

## Phase 2: Department Leads (4 agents)

### 2a. Bobby — Coding Lead 💻
- Agent ID: `bobby`
- Reports to: Prime (via Veronica oversight)
- Workspace skills: coding-agent, github, gh-issues
- SOUL.md: Senior coding lead; coordinates development; ensures quality and conventions
- AGENTS.md: Protocol for delegating to 26 specialists via `sessions_spawn`
- Custom skill: `coding-delegation` — knows the full specialist roster, routes tasks by domain

### 2b. Shane — UX/UI Lead 🎨
- Agent ID: `shane`
- Reports to: Prime (via Veronica oversight)
- Workspace skills: coding-agent (for frontend work), github
- SOUL.md: Senior UX/UI lead; design quality and consistency; user-first
- AGENTS.md: Protocol for delegating to 38 design specialists
- Custom skill: `design-delegation` — routes UX/UI tasks to the right specialist

### 2c. Marc — DevOps Lead 🔧
- Agent ID: `marc`
- Reports to: Prime (via Veronica oversight)
- Workspace skills: healthcheck, github, coding-agent
- SOUL.md: DevOps lead; infrastructure and reliability; coordinates ops and security
- AGENTS.md: Protocol for delegating to 38 ops specialists
- Custom skill: `devops-delegation` — routes infra/ops tasks by domain

### 2d. Shannon — Security Lead 🔒
- Agent ID: `shannon`
- Reports to: Prime (can be invoked by Bobby's Security Pentester or Marc's Security Auditor)
- Workspace skills: healthcheck
- SOUL.md: Autonomous AI pentester; "no exploit, no report"; orange-to-red identity
- AGENTS.md: 13-agent pipeline protocol (pre-recon → recon → vuln analysis → exploitation → report)
- Custom skill: `pentest-pipeline` — orchestrates the security testing pipeline

---

## Phase 3: Squad Leads (15 sub-orchestrators)

Each created via the factory script. Each gets:
- Own workspace with IDENTITY.md, SOUL.md, AGENTS.md
- Domain-specific delegation protocol in AGENTS.md
- Workspace-level skills relevant to their domain

### Bobby's Squad Leads:
- `mobile-lead` — Mobile development (React Native, iOS, Android)
- `ai-lead` — AI systems (Vector DB, Prompt, RAG)
- `legacy-lead` — Legacy modernization (Refactoring, Migration, Tests)

### Shane's Squad Leads:
- `marketing-lead` — Marketing design (Email, Landing Page, Social)
- `research-lead` — UX research (User Journey, A/B Test, Persona)
- `content-lead` — Content/copy (SEO, Copywriter, Localization)
- `design-system-lead` — Design systems (Tokens, Storybook, Patterns)
- `mobile-ux-lead` — Mobile UX (iOS UX, Android UX, Gesture)
- `data-viz-lead` — Data visualization (Charts, Dashboards, Infographics)

### Marc's Squad Leads:
- `sre-lead` — Site reliability (Incident, Chaos, SLO)
- `dataops-lead` — Data operations (Pipeline, Quality, ETL)
- `platform-lead` — Platform engineering (Service Mesh, API Gateway, Config)
- `compliance-lead` — Compliance/governance (Policy, Audit, Vuln Scan)
- `network-lead` — Edge/networking (CDN, Edge, DNS/LB)
- `mlops-lead` — MLOps (Model Deploy, Feature Store, Experiment)

---

## Phase 4: Specialists (100+ agents)

Created in batches via the factory script. Each specialist gets:
- Minimal workspace (IDENTITY.md, SOUL.md with domain expertise)
- Reports-to chain defined in AGENTS.md
- Domain-specific tools/skills as available

### Bobby's 26 specialists:
React, Vue, Backend, Code Reviewer, Test Engineer, Git Master, Database Expert, API Designer, Doc Writer, Rapid React Builder, Motion/Scroll, Three.js/WebGL, App Data, Security Pentester (delegates to Shannon), React Native, iOS Native, Android Native, Vector DB, Prompt Engineer, RAG Architect, Refactoring, Legacy Migrator, Test Coverage, Rust, WASM

### Shane's 38 specialists:
Frontend Designer, Design Extractor, Perf Auditor, Theme, Responsive, Component Builder, Browser Tester, Animation, Accessibility, Email Designer, Landing Page, Social Asset, User Journey, A/B Test, Persona, SEO, Copywriter, Localization, Token Manager, Storybook, Pattern Librarian, iOS UX, Android UX, Gesture, Chart, Dashboard Designer, Infographic, 3D Asset Optimizer, Shader, Micro Frontend, SSR/SSG, PWA

### Marc's 38 specialists:
Docker, Kubernetes, Terraform, CI/CD, Cloud Architect, Monitoring, Security Auditor (delegates to Shannon), Database Admin, Deploy Master, Incident Commander, Chaos Engineer, SLO Manager, Pipeline Engineer, Data Quality, ETL Builder, FinOps, Cost Optimizer, Service Mesh, API Gateway, Config Manager, Policy Enforcer, Audit Trail, Vulnerability Scanner + stubs (Backup/DR, Log Analyst, Secrets Manager)

### Shannon's 13 pipeline agents:
Pre-Recon, Recon, Vuln Analyst (5 parallel), Exploitation (5 parallel), Report Generator

---

## Phase 5: Wire Delegation Protocol

### 5a. Update Prime/Veronica/Rose system prompts
- Add knowledge of the department leads (Bobby, Shane, Marc, Shannon)
- Prime delegates strategic tasks: "Bobby, handle the frontend refactor"
- Veronica oversees execution and requests status reports
- Rose counsels on team dynamics and prioritization

### 5b. Create delegation skills for department leads
Each lead gets a workspace skill that:
- Lists their squad leads and specialists
- Provides routing logic (which specialist handles what)
- Uses `sessions_spawn` to delegate tasks
- Reports results back up the chain

### 5c. Configure session key hierarchy
- Prime: `voice-prime-1` (voice session)
- Bobby: `agent:bobby:task-{uuid}` (spawned by Prime/Veronica)
- Bobby's specialists: `agent:react-specialist:task-{uuid}` (spawned by Bobby)
- Separate session stores prevent context bleed

---

## Files Created/Modified

### New files:
- `setup/create-agent.py` — Agent factory script
- `setup/agents-manifest.json` — Full registry of all agents with metadata
- `~/.openclaw/agents/{id}/workspace/IDENTITY.md` — Per agent
- `~/.openclaw/agents/{id}/workspace/SOUL.md` — Per agent
- `~/.openclaw/agents/{id}/workspace/AGENTS.md` — Per agent
- `~/.openclaw/agents/{id}/workspace/skills/` — Domain skills per agent

### Modified files:
- `~/.openclaw/openclaw.json` — agentToAgent enabled, concurrency limits, agent list
- `prompts/prime-system-prompt.md` — Add department lead delegation knowledge
- `prompts/veronica-system-prompt.md` — Add oversight protocol
- `prompts/rose-system-prompt.md` — Add counseling awareness of the org

---

## Execution Order

1. Phase 1 first (foundation) — ~15 min
2. Phase 2 next (4 department leads) — ~30 min
3. Phase 5a immediately after (wire delegation into voice council) — ~15 min
4. Phase 3 (15 squad leads) — ~30 min
5. Phase 4 (100+ specialists in batches) — ~60 min
6. Phase 5b-c (delegation skills and session config) — ~30 min

Total estimated: ~3 hours of implementation work, done incrementally.
