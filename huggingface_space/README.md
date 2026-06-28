---
title: Voice Clone Studio
emoji: 🎙️
colorFrom: purple
colorTo: indigo
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
---

# Voice Clone Studio — Hugging Face Space (ZeroGPU)

Clone a voice and generate speech with Chatterbox TTS, on a **free on-demand GPU**.

## How this Space is set up
- **SDK:** Gradio
- **Hardware:** **ZeroGPU** (select it in *Settings ▸ Hardware ▸ ZeroGPU*). The
  `@spaces.GPU` decorator on `generate()` requests a GPU only while generating.

## Notes
- Storage on a free Space is **ephemeral** — saved voice profiles reset when the
  Space restarts/rebuilds. For permanent profiles, attach Persistent Storage
  (Settings) or back them with a Hugging Face Dataset.
- First generation downloads the model (~1 min). After that, GPU generation is fast.
