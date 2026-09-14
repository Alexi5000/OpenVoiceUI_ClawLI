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

## Why This Exists

Building a voice-first UI from scratch in enterprise AI is a notorious six-month engineering sinkhole.

Engineering teams spend months drowning in audio pipelines, Web Speech vs. streaming Deepgram buffers, sentence boundary heuristics, audio queue flushes, WebSocket reconnect budgets, and barge-in handling before their models write a single line of business logic.

**TechTide AI** operates on a direct rule: **Stop waiting on the 12-month deck. Run the six-week LEAP sprint.**

**`OpenVoiceUI_ClawLI`** is our production voice and canvas interface layer for the **ClawLI** multi-agent framework. By pairing a zero-build vanilla ES module shell with deep agent orchestration, we bypass the audio plumbing trap and ship talking, visual agent councils in weeks instead of quarters.

> 📖 **Read the complete case narrative:** [The Six-Week Voice Council: How TechTide AI Cracked the Audio-Plumbing Trap](docs/story/alex-hero-story.md)

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

## Upstream Contributions

TechTide actively hardens and contributes foundational improvements back to the upstream [`MCERQUA/OpenVoiceUI-public`](https://github.com/MCERQUA/OpenVoiceUI-public) repository:

| PR | Title | Description | Status |
|:---|:---|:---|:---|
| **[#320](https://github.com/MCERQUA/OpenVoiceUI/pull/320)** | **ARIA Accessibility** | Comprehensive ARIA attributes and screen-reader accessibility across AppShell modals and controls | **Merged** |
| **[#321](https://github.com/MCERQUA/OpenVoiceUI/pull/321)** | **Config Extraction** | Extracted hardcoded template variables into clean constant modules (`src/core/constants.js`) | **Merged** |
| **[#322](https://github.com/MCERQUA/OpenVoiceUI/pull/322)** | **IDE Module Resolution** | Root `jsconfig.json` path mappings for instant VS Code and Cursor IDE code intelligence | **Merged** |

---

## Core Contributors

* **Alex Cinovoj** ([@Alexi5000](https://github.com/Alexi5000)): Lead Architect, TechTide AI Founder (Voice Council design, ClawLI integration, upstream PRs #320, #321, #322).
* **Marco Cerqua** ([@MCERQUA](https://github.com/MCERQUA)): Original Creator and Core Maintainer of OpenVoiceUI.
* **Claude Nexus** (Mentropic / Anthropic): AI Systems Architect (Voice Council protocols, system prompt engineering, multi-agent pipelines).
* **Gemini** (Google DeepMind / Antigravity): AI Systems Architect (Three-tier synchronization, Windows runtime hardening, test verification, copywriting overhaul).

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for detailed attribution and technical history.

---

## License

MIT License &bull; Copyright (c) 2026 TechTide AI and OpenVoiceUI Contributors.
