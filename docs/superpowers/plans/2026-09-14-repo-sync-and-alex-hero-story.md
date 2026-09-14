# OpenVoiceUI Sync & Alex Cinovoj Hero Story Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finalize and verify the full three-tier repository sync, maintain Windows runtime stability, validate custom Voice Council profiles, and research and author a definitive, production-grade hero story document chronicling Alex Cinovoj's real-world journey from client problem to OpenVoiceUI / ClawLI solution.

**Architecture:** 
1. Maintain local Windows signal compatibility in `server.py` and verify all profile schemas against `profiles/manager.py`.
2. Clean up any lingering temporary or unneeded artifacts across the repository.
3. Structure and author a deep-dive, authentic narrative (`docs/story/alex-hero-story.md` and `TECHTIDE.md`) strictly reflecting Alex's voice profile: direct, blunt, builder-to-builder, grounded in production scars and the LEAP sprint framework.
4. Run automated test suites to confirm full green status.

**Tech Stack:** Python 3.11+, Flask, Pytest, OpenVoiceUI ES Modules, Git, GitHub CLI.

## Global Constraints

- Never use bare `print()` in server code; use `logger`.
- No new frontend build step, framework, or bundler — respect vanilla ES modules.
- Preserve all user custom profiles (`prime.json`, `rose.json`, `veronica.json`) and system prompts (`*-system-prompt.md`).
- Voice profile rules: direct, builder register, specific numbers, named tools, contractions, no corporate fluff or engagement bait.
- Verify with automated tests before claiming completion.

---

### Task 1: Windows Runtime Compatibility & Tree Cleanliness

**Files:**
- Modify: `server.py:2600-2608`
- Verify: `c:\Users\Admin\TechTide\Apps\OpenVoice_ClawLi\server.py`

**Interfaces:**
- Consumes: Python standard library `signal` module.
- Produces: Safe startup on Windows without throwing `AttributeError: module 'signal' has no attribute 'SIGHUP'`.

- [ ] **Step 1: Verify Windows signal guard in `server.py`**

Confirm line 2603 contains:
```python
    signal.signal(signal.SIGTERM, _handle_sigterm)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
```

- [ ] **Step 2: Compile `server.py` to ensure syntax integrity**

Run: `python -m py_compile server.py`
Expected: Returncode 0 with no errors.

- [ ] **Step 3: Verify clean git status and branch alignment**

Run: `git status` and `git branch -vv`
Expected: On branch `main`, up to date with `origin/main` (at `32f0feb`). Only expected modifications and untracked custom profiles/prompts present.

---

### Task 2: Validate Multi-Agent Profiles & Custom Council

**Files:**
- Test: `tests/test_profiles.py`
- Test: `tests/test_profile_manager.py`
- Inspect: `profiles/prime.json`
- Inspect: `profiles/rose.json`
- Inspect: `profiles/veronica.json`

**Interfaces:**
- Consumes: `profiles/schema.json`, `profiles/manager.py:ProfileManager`.
- Produces: Valid JSON schema compliance for Prime, Rose, and Veronica.

- [ ] **Step 1: Run profile schema validation test**

Run: `python -m pytest tests/test_profiles.py -v`
Expected: PASS (all profiles match schema).

- [ ] **Step 2: Run ProfileManager functional tests**

Run: `python -m pytest tests/test_profile_manager.py -v`
Expected: PASS.

---

### Task 3: Deep Research & Author Alex Cinovoj's Hero Story

**Files:**
- Create: `docs/story/alex-hero-story.md`
- Create / Update: `TECHTIDE.md`

**Interfaces:**
- Consumes:
  - TechTide company structure & positioning (`COMPANY-STRUCTURE.md`, `BRAND.md`)
  - Alex Cinovoj voice profile (`alex-cinovoj.md`)
  - TechTide fork notes (`origin/techtide/build-out:TECHTIDE.md`)
  - Upstream contributions (PRs #320, #321, #322)
  - The LEAP framework & client delivery methodology
- Produces:
  - Comprehensive, rich, multi-chapter case narrative detailing why OpenVoiceUI was chosen, how the audio/visual shell solved the 6-month plumbing trap, and how ClawLI and OpenVoiceUI shipped in a 6-week sprint.

- [ ] **Step 1: Draft the canonical Hero Story document**

Author `docs/story/alex-hero-story.md` covering:
1. The Hook: The 6-Month Audio Plumbing Trap vs. The 6-Week LEAP Sprint.
2. The Builder Behind It: Alex Cinovoj, immigrant grit, DevOps production scars, Columbus Ohio.
3. The Client Crisis: Mid-market client needing a talking, interactive multi-agent system (Voice Council) — and why traditional chat windows failed.
4. The Discovery: Finding OpenVoiceUI, evaluating the decoupled Flask + vanilla JS architecture, EventBus, and Canvas subsystem.
5. The Solution Architecture: Pairing ClawLI with OpenVoiceUI — Prime (the CEO), Veronica (the Analyst), Rose (the Counselor).
6. Upstream Contributions: TechTide's PRs #320, #321, #322 and open-source symbiosis.
7. The Outcome: Delivering in production, moving the needle for the client, and cementing TechTide's voice interface standard.

- [ ] **Step 2: Sync and enhance `TECHTIDE.md` at repo root**

Create/update `TECHTIDE.md` with updated fork documentation, cross-referencing `docs/story/alex-hero-story.md`.

- [ ] **Step 3: Verify markdown formatting, links, and tone**

Inspect and verify against Alex's voice profile hard rules (no corporate fluff, numbers-anchored, declarative).

---

### Task 4: Final Verification & Clean-up

**Files:**
- Audit: All modified and created files across the repository.

- [ ] **Step 1: Run full test suite for touched subsystems**

Run: `python -m pytest tests/test_profiles.py tests/test_profile_manager.py tests/test_stream_exit_flushes_tts.py -v`
Expected: All tests PASS.

- [ ] **Step 2: Final Git status check**

Run: `git status`
Expected: Working tree clean of unwanted artifacts, only intended tracked additions and user profiles remain.
