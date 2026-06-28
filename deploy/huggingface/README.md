---
title: Voice Clone Studio
emoji: 🎙️
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Voice Clone Studio (Hugging Face Space)

This Space runs the Flask + Chatterbox TTS voice cloning app in a Docker container.

> ⚠️ On the **free CPU** Space, generation is slow (a few minutes per clip).
> For fast generation, upgrade the Space hardware to a **GPU** tier in Settings.

When creating the Space, this file must be named **`README.md`** at the root of
the Space repo (Hugging Face reads the config from its YAML frontmatter above).
Everything else (Dockerfile, app.py, templates/, requirements.txt) comes from the
project repo.
