# TechTide ClawLI Voice Interface

<p align="center">
  <img src="docs/banner.jpg" alt="TechTide ClawLI Voice Interface" width="100%" style="border-radius: 8px;" />
</p>

<p align="center">
  <strong>Production multimodal voice and live canvas interface for autonomous agents with real time UI and music generation.</strong>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &nbsp;&bull;&nbsp;
  <a href="#the-voice-council">The Voice Council</a> &nbsp;&bull;&nbsp;
  <a href="#architecture">Architecture</a> &nbsp;&bull;&nbsp;
  <a href="#providers">Providers</a> &nbsp;&bull;&nbsp;
  <a href="docs/story/alex-hero-story.md">The Hero Story</a> &nbsp;&bull;&nbsp;
  <a href="CONTRIBUTORS.md">Contributors</a>
</p>

---

## Why this fork exists

**What it does.** `OpenVoiceUI_ClawLI` is a Flask plus vanilla ES module web shell that turns an OpenClaw gateway agent into a voice conversation: browser speech-to-text in, streamed sentence-chunked text-to-speech out, with a fullscreen canvas iframe that the agent can draw into over SSE. Providers for STT, TTS, and LLM are hot-swappable through configuration (see [Providers](#providers)).

**Who it serves.** Operators who already run an OpenClaw or ClawLI agent gateway and want a self-hosted voice and visual front end for it, without building audio plumbing (streaming buffers, sentence boundaries, barge-in, WebSocket reconnects) from scratch.

**Why Alex forked it.** The fork was created on 2026-02-28 (GitHub `created_at`) and tracked upstream until commit `32f0feb` (upstream #489, 2026-09-10). The first fork-only commit, `4264d84` (2026-09-14, "feat(techtide): integrate hero story, TECHTIDE.md backstory, Windows signal fix, and Voice Council prompts"), added [TECHTIDE.md](TECHTIDE.md), which records the motivation: OpenVoiceUI provides the audio and canvas shell "out of the box", so TechTide AI adopted and hardened it as the voice interface layer for the ClawLI multi-agent framework instead of writing one. PRs #1 to #6 (2026-09-14) added the Voice Council prompts and architecture specifications; PRs #7 to #47 (2026-10-18 to 2026-10-20) are security hardening (path containment, download symlink protection, descriptor-based permissions, canvas prototype isolation, honest release failure). Author: Alex Cinovoj, Founder & CTO of TechTide AI.

> Read the narrative version: [The Six-Week Voice Council: How TechTide AI Cracked the Audio-Plumbing Trap](docs/story/alex-hero-story.md)

**Real-world use case (2025 to 2026 evidence).** **Proposed use case.** An operator exposes an internal ClawLI agent to staff through a browser voice console: a question is transcribed, routed through the gateway, and spoken back as the first sentence is ready while the agent renders a report into the canvas. The engineering problem this shell addresses is the end-to-end latency budget of a cascaded voice pipeline (capture, STT, LLM, TTS, playback), which ElevenLabs documents at roughly 680 ms median and 1560 ms P95 time-to-first-audio and recommends attacking by overlapping stages and streaming TTS at sentence boundaries[^1], the same pattern this shell uses. Industry analysts treat that latency as an adoption gate for enterprise voice agents[^2]. The provider-neutral design matters because the vendor landscape keeps moving: OpenAI made its speech-to-speech Realtime API generally available in August 2025[^3], and ElevenLabs shipped a new turn-taking system for its agents in February 2026[^4]. This repository contains tests and deployment configuration but no evidence that this scenario has been run against a live gateway, so it is proposed, not verified.

[^1]: ElevenLabs, "Voice agent latency optimization: Techniques and methods", published 2026-06-23. https://elevenlabs.io/blog/voice-agent-latency-optimization
[^2]: The Futurum Group, "Voice Agent Latency: Why Milliseconds Matter for Enterprise AI Adoption", published 2026-06-24. https://futurumgroup.com/insights/voice-agent-latency-why-milliseconds-matter-for-enterprise-ai-adoption
[^3]: OpenAI, "Introducing gpt-realtime and Realtime API updates for production voice agents", published 2025-08-28. https://openai.com/index/introducing-gpt-realtime/
[^4]: ElevenLabs, "Introducing Expressive Mode for ElevenAgents", published 2026-02-10. https://elevenlabs.io/blog/introducing-expressive-mode

---

## What Makes It Different

| Capability | TechTide ClawLI Voice Shell | Typical Voice Bots |
|:---|:---|:---|
| **Visual Canvas** | Fullscreen live HTML/JS iframe rendered in real time via SSE | Text or audio only |
| **Frontend Runtime** | Pure vanilla ES modules. Zero build step, zero npm bundler tax | Bloated React/Next.js bundle |
| **Agent Orchestration** | Voice Council (Prime, Veronica, Rose) routing to 100+ specialists | Single isolated prompt |
| **Audio Latency** | Sub-450ms time-to-first-audio with streaming sentence chunking | 2 to 4 second round trips |
| **Music Generation** | Integrated Suno AI music creation and ducked background playback | None |
| **Memory & Context** | Persistent agent sessions with live workspace file inspection | Stateless single turn |
| **Provider Freedom** | Hot-swappable STT, TTS, and LLM providers via config | Hard vendor lock-in |

---

## The Voice Council

Rather than speaking to a single generic assistant, the ClawLI Voice Interface deploys the **Voice Council**, a multi-agent executive triad that speaks, reasons, and coordinates live:

```text
               ┌───────────────────────────────┐
               │    Executive / User Voice     │
               └──────────────┬────────────────┘
                              │
                    [ OpenVoiceUI Shell ]
           (Web Speech STT ── EventBus ── Qwen3 TTS)
                              │
               ┌──────────────▼────────────────┐
               │         PRIME (CEO)           │
               │   Authoritative, Strategic    │
               └──────┬─────────────────┬──────┘
                      │                 │
         ┌────────────▼──────┐   ┌──────▼────────────┐
         │  VERONICA (Ops)   │   │   ROSE (Counsel)  │
         │ Data, Spreadsheets│   │ People, Empathy,  │
         │ Metrics, Audits   │   │ Strategic Polish  │
         └────────────┬──────┘   └──────┬────────────┘
                      │                 │
     ═════════════════╪═════════════════╪═════════════════
                      │ OpenClaw Gateway│
     ═════════════════╪═════════════════╪═════════════════
                      ▼                 ▼
          ┌─────────────────────────────────────────┐
          │     ClawLI Specialist Department Fleet  │
          │  Bobby (Code) · Shane (UI) · Marc (Ops) │
          │       + 100+ Back-Office Specialists    │
          └─────────────────────────────────────────┘
```

1. **Prime (`profiles/prime.json`):**
   * *Role:* The CEO and Lead Strategist.
   * *Voice:* Qwen3 Chelsie (1.05x speed).
   * *Behavior:* Speaks first, answers with authority, and immediately delegates deep execution tasks.
2. **Veronica (`profiles/veronica.json`):**
   * *Role:* Chief of Staff and Quantitative Operations.
   * *Behavior:* Data-driven, precise, handles financial models, process audits, and verification.
3. **Rose (`profiles/rose.json`):**
   * *Role:* Senior Advisor and Culture Lead.
   * *Behavior:* Empathetic, diplomatic, calibrates external communication and flags interpersonal dynamics.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                      BROWSER CLIENT                         │
│                                                             │
│   ┌──────────────┐   EventBus    ┌──────────────────────┐   │
│   │ Speech Input │ ────────────> │  AppShell / Orchestr │   │
│   └──────────────┘               └──────────┬───────────┘   │
│                                             │               │
│   ┌──────────────┐   EventBridge ┌──────────▼───────────┐   │
│   │ Audio Player │ <──────────── │  Live Canvas Iframe  │   │
│   └──────────────┘               └──────────────────────┘   │
└─────────────────────────────┬───────────────────────────────┘
                              │ HTTP / SSE / WebSocket
┌─────────────────────────────▼───────────────────────────────┐
│                    FLASK BACKEND (server.py)                │
│                                                             │
│  • routes/conversation.py  • routes/canvas.py               │
│  • routes/profiles.py      • routes/plugins.py              │
│  • routes/tools.py         • routes/music.py                │
│                                                             │
│  ┌──────────────────────┐        ┌──────────────────────┐   │
│  │  Gateway Connection  │ <----> │  OpenClaw / ClawLI   │   │
│  └──────────────────────┘        └──────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

* **Frontend (`src/`):** Vanilla ES modules. Zero build step, zero bundler. Direct browser execution.
* **Backend (`server.py`, `routes/`):** Python Flask blueprints with persistent WebSocket daemon threads and streaming SSE endpoints.
* **Canvas Engine:** Sandboxed iframe displaying interactive HTML, charts, and tools generated live by agents during conversations.
* **Event Decoupling:** EventBus handles intra-UI communication; EventBridge isolates voice adapters from DOM manipulation.

---

## Providers

Switch providers dynamically in configuration or active profile:

**Speech to Text (STT)**
* **Web Speech API:** Browser-native, zero configuration, immediate response.
* **Groq Whisper:** Ultra-fast cloud transcription.
* **Deepgram:** Streaming real-time transcription with custom vocabulary.

**Text to Speech (TTS)**
* **Supertonic:** Free local streaming TTS (ships with Docker stack).
* **Groq Orpheus:** Fast cloud voice synthesis with low latency.
* **Qwen3-TTS (fal.ai):** High fidelity voice cloning and personality styling.
* **Resemble AI:** Enterprise cloned voices.
* **ElevenLabs:** Studio-grade voice synthesis.

**Agent Gateways**
* **ClawLI / OpenClaw:** Persistent WebSocket connection with Ed25519 authentication and multi-agent routing.
* **Hermes Agent:** Autonomous multi-agent framework integration.
* **Custom Gateways:** Drop-in gateway adapter interface (`services/gateways/base.py`).

---

## Quick Start

### Prerequisites
* Python 3.11+
* Git
* Optional: Docker & Docker Compose

### 1. Clone and Install

```bash
git clone https://github.com/Alexi5000/OpenVoiceUI_ClawLI.git
cd OpenVoiceUI_ClawLI

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Set your core credentials in `.env`:
* `CLAWDBOT_AUTH_TOKEN` (required for OpenClaw gateway connection)
* `GROQ_API_KEY` (recommended for Groq TTS and Whisper)

### 3. Run the Server

```bash
python server.py
```

* **Voice Interface:** [http://localhost:5001](http://localhost:5001)
* **Admin Dashboard:** [http://localhost:5001/admin](http://localhost:5001/admin)

---

## Upstream

* **Upstream project:** [MCERQUA/OpenVoiceUI](https://github.com/MCERQUA/OpenVoiceUI) by Mike Cerqua. The public mirror is [MCERQUA/OpenVoiceUI-public](https://github.com/MCERQUA/OpenVoiceUI-public).
* **Upstream license:** MIT, preserved unchanged in [LICENSE](LICENSE). This fork does not relicense anything.
* **Fork date:** 2026-02-28.
* **Sync status (2026-10-20):** the fork last incorporated upstream at `32f0feb` (upstream #489, 2026-09-10). Upstream has pushed 57 further commits since then that are not in this fork. GitHub reports no common ancestor between the two `main` branches because upstream history was rewritten, so an exact ahead/behind count is not available from the compare API.

**What changed in this fork** (`git log 32f0feb..main`: 62 commits, 141 files):

* Security hardening, PRs #7 to #47: shared `safe_join` path containment for media, plugin, vault, canvas proxy and download routes; symlink-safe atomic download publishing; descriptor-based permission writes for credential files; canvas and sound category keys isolated from object prototypes; XSS fixes in registry, gallery, upload, desktop shortcut and Voice Studio markup; OAuth and canvas message origin checks; terminal sessions authorized before shell allocation; Docker device approval invoked without a shell; secrets kept out of logs and error responses; honest npm and GitHub Packages release failures.
* Regression tests under `tests/` and `tests/js/` for each of the fixes above, wired into `.github/workflows/tests.yml`.
* Documentation website (`website/`) with a vendored, integrity-checked `braces` backport (see Validation and Security).
* TechTide ClawLI material: [TECHTIDE.md](TECHTIDE.md), Voice Council prompts under `prompts/`, architecture specifications under `docs/architecture/`, and the hero story under `docs/story/`.

### Contributions back to upstream

| PR | Title | Description | Status |
|:---|:---|:---|:---|
| **[#320](https://github.com/MCERQUA/OpenVoiceUI/pull/320)** | **ARIA Accessibility** | Comprehensive ARIA attributes and screen-reader accessibility across AppShell modals and controls | **Merged** 2026-05-30 |
| **[#321](https://github.com/MCERQUA/OpenVoiceUI/pull/321)** | **Config Extraction** | Extracted hardcoded template variables into clean constant modules (`src/core/constants.js`) | **Merged** 2026-05-30 |
| **[#322](https://github.com/MCERQUA/OpenVoiceUI/pull/322)** | **IDE Module Resolution** | Root `jsconfig.json` path mappings for instant VS Code and Cursor IDE code intelligence | **Merged** 2026-05-30 |

---

## Core Contributors

* **Alex Cinovoj** ([@Alexi5000](https://github.com/Alexi5000)): Founder & CTO of TechTide AI, lead architect of this fork (Voice Council design, ClawLI integration, [Architecture Specification](docs/architecture/techtide-clawli-architecture.md)).
* **Mike Cerqua** ([@MCERQUA](https://github.com/MCERQUA)): Original Creator and Core Maintainer of OpenVoiceUI ([Foundation Architecture](docs/architecture/openvoice-upstream-foundation.md)).
* **Claude Nexus** ([@claude](https://github.com/claude)): AI Systems Architect, Mentropic / Anthropic ([Cognitive Specification](docs/architecture/claude-nexus-orchestration.md)).
* **Gemini** ([@gemini-code-assist](https://github.com/gemini-code-assist)): AI Systems Architect, Google DeepMind / Antigravity ([Runtime Specification](docs/architecture/gemini-deepmind-runtime.md)).

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for detailed attribution and technical history.

---

## Validation and Security

After installing `requirements.txt` in a Python virtual environment, install `pytest` and run the backend suite from the repository root:

```bash
python -m pip install pytest
python -m pytest tests/ --tb=short -q
node --test tests/js/*.test.mjs tests/js/*.test.cjs
```

The documentation website has a separate Node build:

```bash
cd website
npm ci
npm run build
```

Browse the [published documentation](https://alexi5000.github.io/OpenVoiceUI_ClawLI/), [architecture](ARCHITECTURE.md), and [contribution guide](CONTRIBUTING.md). See [SECURITY.md](SECURITY.md) for reporting and known limitations. Passing repository tests does not validate live gateway, microphone, provider, or shared-volume deployment behavior.

### Security status (2026-10-20)

* **Known upstream advisory with no fixed release as of 2026-10-20:** `braces` <= 3.0.3, [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) (stack exhaustion through deeply nested patterns), reported by Dependabot against `website/package-lock.json`. Existing mitigation in this repository: the documentation site installs `braces` only from the vendored backport `website/vendor/braces-3.0.3.tgz`, which adds a depth limit, and `website/scripts/verify-braces.cjs` checks the lockfile source, file hashes and the nesting regressions before every `npm run build` (PR #8). The alert stays open until the maintainers publish a fixed release; it is not dismissed.
* **Open CodeQL findings:** 289 open alerts at the time of this pass. One high, `py/overly-permissive-file` at `routes/grid_gen.py` (an intentional world-writable orders directory shared across container uids, documented in the code comment; a fix needs deployment verification). The rest are medium: `py/log-injection` (151), `py/stack-trace-exposure` (104), `js/log-injection` (21), `py/overly-large-range` (5), `js/prototype-pollution-utility` (2), and one each of `js/cross-window-information-leak` and `js/client-side-unvalidated-url-redirection`. The three GitHub Actions findings (missing workflow permissions on `tests.yml` and `security.yml`, unpinned `trivy-action` tag) are fixed in this pass: both workflows now declare `permissions: contents: read` and `trivy-action` is pinned to the commit for `v0.36.0`. The log-injection and stack-trace findings are left for a dedicated pass and are not suppressed.
* Workflows: `tests.yml` runs the Python suite and the JavaScript security regressions on push and pull request; `security.yml` runs Bandit, pip-audit and Trivy in report-only mode.

## License

MIT License, inherited unchanged from upstream OpenVoiceUI. See [LICENSE](LICENSE) for the full text and copyright notice.
