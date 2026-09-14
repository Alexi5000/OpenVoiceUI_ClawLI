# TechTide AI: Why This Fork Exists

## Overview

**`OpenVoiceUI_ClawLI`** is TechTide AI's production voice-and-canvas interface shell for our **ClawLI** multi-agent framework.

Building a production voice interface from scratch is a notorious six-month engineering sinkhole (STT streaming, sentence chunking, audio ducking, WebSocket reconnection budgets, barge-in interruptibility, and real-time canvas iframe rendering). OpenVoiceUI provides that entire audio/visual shell out of the box with zero framework bloat (pure Python Flask backend + vanilla JavaScript ES modules frontend).

By adopting and hardening OpenVoiceUI, TechTide was able to deliver a full multi-agent Voice Council for client operations in a **six-week LEAP sprint** rather than burning months on audio plumbing.

> 📖 **Read the full backstory:** [The Six-Week Voice Council: How TechTide AI Cracked the Audio-Plumbing Trap](docs/story/alex-hero-story.md)

---

## What TechTide Uses This For

- **ClawLI Voice Interface:** The primary audio/visual I/O layer for ClawLI agents, routing streaming STT, LLM inference, and low-latency TTS.
- **The Voice Council:** A triad of executive voice agents: **Prime** (CEO / Lead Strategist), **Veronica** (Data & Operations), and **Rose** (Counsel & Client Nuance), who speak with unique cloned voices and delegate deep operational tasks to over 100+ back-office specialist agents.
- **Live Canvas Workspaces:** Dynamic, full-screen iframe rendering of client dashboards, live code diffs, interactive maps, and reports generated in real time as the agent speaks.
- **Interactive Client Demos:** Zero-latency executive demos showcasing autonomous multi-agent systems with voice conversation and synchronized visual displays.

---

## Upstream Contributions

TechTide believes in active open-source symbiosis. We have hardened and contributed core accessibility, architecture, and developer-experience improvements back to the upstream [`MCERQUA/OpenVoiceUI-public`](https://github.com/MCERQUA/OpenVoiceUI-public) repository:

| PR | Title | Contribution |
|:---|:---|:---|
| **[#320](https://github.com/MCERQUA/OpenVoiceUI/pull/320)** | **ARIA Accessibility** | Comprehensive ARIA attributes and screen-reader accessibility across mobile and desktop shells. |
| **[#321](https://github.com/MCERQUA/OpenVoiceUI/pull/321)** | **Config Extraction** | Modularized hardcoded AppShell variables into dedicated constant modules (`src/core/constants.js`). |
| **[#322](https://github.com/MCERQUA/OpenVoiceUI/pull/322)** | **IDE Module Resolution** | Added root `jsconfig.json` module path configuration for instant VS Code / Cursor IDE autocomplete. |

---

## Architecture Highlights

- **Frontend (`src/`):** Pure vanilla ES modules. No React/Vue/Svelte build steps, no bundlers, no npm compilation tax. Direct browser execution via `EventBus` pub/sub and `EventBridge` isolation.
- **Backend (`routes/`):** Modular Flask blueprints (`conversation.py`, `canvas.py`, `profiles.py`, `plugins.py`, `tools.py`).
- **Voice Providers (`providers/`, `tts_providers/`):** Pluggable, latency-optimized STT/TTS (Web Speech, Deepgram, Groq Orpheus, Supertonic, Qwen3-TTS).
- **Multi-Agent Roster:** Custom profiles located in `profiles/prime.json`, `profiles/rose.json`, and `profiles/veronica.json` paired with tailored system prompts in `prompts/`.
- **Operating Philosophy:** Lean, resilient, and built for production.

---

*Maintained by [TechTide AI](https://github.com/Alexi5000/OpenVoiceUI_ClawLI) (Columbus, Ohio) as part of our production agent interface infrastructure.*
