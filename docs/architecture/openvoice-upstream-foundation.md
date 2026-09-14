# OpenVoiceUI Upstream Architectural Foundation

## 1. Overview

OpenVoiceUI was conceived and engineered by Mike Cerqua as a universal, lightweight voice and canvas shell for autonomous AI agents.

This document records the foundational architecture inherited by downstream distributions, including TechTide ClawLI.

---

## 2. Fundamental Design Principles

1. **Lightweight Frontend Core**: Built with pure vanilla JavaScript ES modules without bundlers, compilation steps, or heavy framework overhead.
2. **Abstract Base Class (ABC) Registries**: Voice synthesis, transcription, and gateway communication adhere to strict abstract contracts.
3. **Pluggable Gateways**: Decoupled agent backend communication supporting OpenClaw, direct WebSockets, and custom gateway plugins.
4. **Isolated Canvas Runtimes**: Live visual pages operate within structured sandboxes to safeguard parent application state.

---

## 3. Collaboration Across Distributions

OpenVoiceUI thrives through collaborative development across upstream maintainers and specialized production forks:

* Upstream repository: [MCERQUA/OpenVoiceUI-public](https://github.com/MCERQUA/OpenVoiceUI-public)
* Production distribution: [Alexi5000/OpenVoiceUI_ClawLI](https://github.com/Alexi5000/OpenVoiceUI_ClawLI)

Author: Mike Cerqua (@MCERQUA), OpenVoiceUI Creator and Lead Architect.
