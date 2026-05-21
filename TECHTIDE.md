# TechTide AI — Why This Fork Exists

## The Problem

Voice is the natural interface for agent interaction, but building a voice-first UI from scratch is a 6-month project. Every team reinvents STT → LLM → TTS pipelines, audio ducking, wake words, and canvas rendering. Meanwhile, the agent can't see, hear, or speak until all that plumbing is done.

## Why OpenVoiceUI

OpenVoiceUI gives agents a voice shell out of the box — plug in any LLM, pick a TTS provider, and the agent can talk. The canvas system means it can show things too. We use it as the ClawLI voice interface layer so agent builders focus on logic, not I/O.

We use OpenVoiceUI internally at TechTide as the voice interface for our ClawLI agent framework. When clients need agents that can speak, listen, and display content, OpenVoiceUI provides the entire audio/visual shell.

## What TechTide Uses This For

- **ClawLI voice interface** — The primary voice I/O layer for ClawLI agents, handling STT, TTS, and audio routing
- **Agent demos** — Interactive voice demos for client presentations with live canvas displays
- **Multi-modal agents** — Agents that combine voice input with visual output (code, diagrams, 3D models)
- **Rapid prototyping** — Spin up a talking agent in minutes using the provider-agnostic architecture

## Upstream Contributions

We contribute accessibility, code quality, and developer experience improvements back to the upstream project:

| PR | Description |
|----|-------------|
| [#320](https://github.com/MCERQUA/OpenVoiceUI/pull/320) | Add ARIA attributes for screen reader accessibility |
| [#321](https://github.com/MCERQUA/OpenVoiceUI/pull/321) | Extract hardcoded config from AppShell template into constants module |
| [#322](https://github.com/MCERQUA/OpenVoiceUI/pull/322) | Add jsconfig.json for IDE module resolution |

## Architecture Notes

OpenVoiceUI is a Flask + vanilla JS application with:
- **Frontend** (`src/`): Vanilla ES modules — AppShell, EventBus, Config, VoiceSession
- **Backend** (`routes/`): Flask blueprints — conversation, canvas, music, profiles, plugins
- **Providers** (`providers/`, `tts_providers/`): Pluggable STT/TTS — Supertonic, Hume EVI, Groq, Deepgram
- **Shell** (`src/shell/`): Bridge modules — orchestrator, transcript, waveform, camera, canvas
- **Config** (`config/`): YAML-based with env var overrides and feature flags

Key strengths:
- **Provider-agnostic**: Swap STT/TTS/LLM without changing application code
- **Canvas system**: Full-screen iframe display for agent-generated content
- **Event-driven**: Decoupled modules communicate via EventBus pub/sub
- **Face system**: Animated face with emotion states, eye tracking, waveform mouth
- **Music integration**: AI-controlled music playback with intelligent ducking

---

*This fork is maintained by [TechTide AI](https://github.com/TechTideOhio) as part of our agent voice interface infrastructure stack.*
