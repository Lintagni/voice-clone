"""
Voice Clone Studio — Gradio app for Hugging Face Spaces (ZeroGPU).

Free on-demand GPU via the `spaces` library: the @GPU-decorated generate()
function gets a GPU allocated for its duration. Runs on CPU locally as a no-op.

Same two-section workflow as the Flask app:
  ① Create Voice Profile (upload + name + optional transcript, save/delete)
  ② Generate Audio (pick profile, paste script, tune, generate, download)
"""

import os
import re
import glob
import uuid
import shutil
from datetime import datetime

import torch
import numpy as np
import soundfile as sf
import gradio as gr

# ZeroGPU decorator — real GPU on HF Spaces, transparent no-op locally.
try:
    import spaces

    gpu = spaces.GPU(duration=120)
except Exception:  # not on ZeroGPU / package missing -> run inline
    def gpu(fn):
        return fn

# --------------------------------------------------------------------------- #
PROFILE_DIR = "profiles"
OUTPUT_DIR = "outputs"
for _d in (PROFILE_DIR, OUTPUT_DIR):
    os.makedirs(_d, exist_ok=True)

ALLOWED = {"wav", "mp3", "flac", "ogg", "m4a"}
CHUNK_MAX = 280
GAP_SECONDS = 0.35

_model = None


def get_model():
    global _model
    if _model is None:
        from chatterbox.tts import ChatterboxTTS

        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = ChatterboxTTS.from_pretrained(device=device)
    return _model


# ---- profile helpers ------------------------------------------------------ #
def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", (name or "").strip()).strip("_")


def profile_audio_path(name: str):
    safe = _safe(name)
    if not safe:
        return None
    for ext in ALLOWED:
        p = os.path.join(PROFILE_DIR, f"{safe}.{ext}")
        if os.path.exists(p):
            return p
    return None


def list_profile_names():
    names, seen = [], set()
    for p in sorted(glob.glob(os.path.join(PROFILE_DIR, "*.*"))):
        base, ext = os.path.splitext(os.path.basename(p))
        if ext.lstrip(".").lower() in ALLOWED and base not in seen:
            seen.add(base)
            names.append(base)
    return names


def save_profile(name, audio_path, transcript):
    safe = _safe(name)
    if not safe:
        return gr.update(), gr.update(), "❌ Please enter a profile name."
    if not audio_path:
        return gr.update(), gr.update(), "❌ Please upload a reference clip."
    ext = os.path.splitext(audio_path)[1].lstrip(".").lower()
    if ext not in ALLOWED:
        ext = "wav"
    for old in glob.glob(os.path.join(PROFILE_DIR, safe + ".*")):
        try:
            os.remove(old)
        except OSError:
            pass
    shutil.copy(audio_path, os.path.join(PROFILE_DIR, f"{safe}.{ext}"))
    if (transcript or "").strip():
        with open(os.path.join(PROFILE_DIR, f"{safe}.txt"), "w", encoding="utf-8") as fh:
            fh.write(transcript.strip())
    names = list_profile_names()
    return (
        gr.update(choices=names, value=safe),
        gr.update(choices=names, value=safe),
        f"✅ Saved voice profile “{safe}”.",
    )


def delete_profile(name):
    safe = _safe(name)
    for f in glob.glob(os.path.join(PROFILE_DIR, safe + ".*")):
        try:
            os.remove(f)
        except OSError:
            pass
    names = list_profile_names()
    val = names[0] if names else None
    return (
        gr.update(choices=names, value=val),
        gr.update(choices=names, value=val),
        (f"🗑 Deleted “{safe}”." if safe else ""),
    )


# ---- text chunking -------------------------------------------------------- #
def split_text(text, max_len=CHUNK_MAX):
    text = " ".join(text.split())
    chunks, cur = [], ""
    for s in re.split(r"(?<=[.!?])\s+", text):
        if not s:
            continue
        if len(s) > max_len:
            pieces = []
            for part in re.split(r"(?<=[,;:])\s+", s):
                while len(part) > max_len:
                    pieces.append(part[:max_len])
                    part = part[max_len:]
                if part:
                    pieces.append(part)
        else:
            pieces = [s]
        for p in pieces:
            if cur and len(cur) + len(p) + 1 > max_len:
                chunks.append(cur)
                cur = p
            else:
                cur = (cur + " " + p).strip()
    if cur:
        chunks.append(cur)
    return chunks or [text]


def recent_outputs(limit=10):
    files = sorted(
        glob.glob(os.path.join(OUTPUT_DIR, "*.wav")),
        key=os.path.getmtime,
        reverse=True,
    )
    return files[:limit]


# ---- generation (runs on GPU via ZeroGPU) --------------------------------- #
@gpu
def generate(profile, text, cfg_weight, temperature, exaggeration,
             progress=gr.Progress()):
    if not profile:
        raise gr.Error("Choose a saved voice profile (create one in tab ①).")
    if not (text or "").strip():
        raise gr.Error("Paste or type a script to speak.")
    ref = profile_audio_path(profile)
    if not ref:
        raise gr.Error(f"Voice profile '{profile}' not found.")

    model = get_model()
    chunks = split_text(text)
    gap = torch.zeros(int(GAP_SECONDS * model.sr))
    pieces = []
    for i, ch in enumerate(progress.tqdm(chunks, desc="Generating")):
        wav = model.generate(
            ch,
            audio_prompt_path=ref,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            temperature=temperature,
        )
        pieces.append(wav.squeeze(0).cpu())
        if i < len(chunks) - 1:
            pieces.append(gap)

    full = torch.cat(pieces).numpy()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())[:32].strip("-") or "clip"
    out = os.path.join(OUTPUT_DIR, f"{slug}-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}.wav")
    sf.write(out, full, model.sr)
    return (model.sr, full), recent_outputs()


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
def build_ui():
    names = list_profile_names()
    init = names[0] if names else None
    with gr.Blocks(title="Voice Clone Studio", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            "# 🎙️ Voice Clone Studio\n"
            "Clone a voice and generate speech — powered by Chatterbox TTS on a free GPU."
        )

        with gr.Tab("① Create Voice Profile"):
            with gr.Row():
                with gr.Column():
                    p_name = gr.Textbox(label="Profile name", placeholder="e.g. gayan")
                    p_audio = gr.Audio(label="Reference audio (10–60 s of clear speech)", type="filepath")
                    p_trans = gr.Textbox(label="Transcript / notes (optional)", lines=3,
                                         placeholder="Optional — Chatterbox clones from the audio alone.")
                    p_save = gr.Button("💾 Save voice profile", variant="primary")
                    p_msg = gr.Markdown()
                with gr.Column():
                    gr.Markdown("### Your voice profiles")
                    del_dd = gr.Dropdown(label="Saved profiles", choices=names, value=init)
                    del_btn = gr.Button("🗑 Delete selected")

        with gr.Tab("② Generate Audio"):
            gen_dd = gr.Dropdown(label="Choose voice profile", choices=names, value=init)
            g_text = gr.Textbox(label="Script", lines=8,
                                placeholder="Paste your script. Long scripts are split and stitched into one track…")
            with gr.Accordion("⚙️ Voice tuning (lower = cleaner / less artifacts)", open=False):
                cfg = gr.Slider(0, 1, value=0.3, step=0.05, label="CFG weight")
                temp = gr.Slider(0.05, 1.2, value=0.7, step=0.05, label="Temperature")
                exag = gr.Slider(0.25, 1, value=0.5, step=0.05, label="Exaggeration")
            g_btn = gr.Button("Generate Audio", variant="primary")
            g_audio = gr.Audio(label="Output", type="numpy", autoplay=True)
            g_hist = gr.Files(label="Recent generations (click to download)", value=recent_outputs())

        # refresh dropdown choices when this tab gains focus is automatic via events below
        p_save.click(save_profile, [p_name, p_audio, p_trans], [gen_dd, del_dd, p_msg])
        del_btn.click(delete_profile, [del_dd], [gen_dd, del_dd, p_msg])
        g_btn.click(generate, [gen_dd, g_text, cfg, temp, exag], [g_audio, g_hist])

    return demo


demo = build_ui()

if __name__ == "__main__":
    demo.queue().launch()
