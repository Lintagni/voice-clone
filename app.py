"""
Local AI Voice Cloning Tool
Flask backend powered by Chatterbox TTS (Resemble AI, MIT license).

Endpoints:
    POST /generate         -> start an (async) generation job, returns {job_id, total}
    GET  /status/<job_id>  -> progress / result of a job
    GET  /history          -> list of recent generations (last 5)
    POST /profile          -> save a reusable voice profile (name + audio)
    GET  /profiles         -> list saved voice profiles
    DELETE /profile/<name> -> delete a saved profile
    GET  /download/<file>  -> serve / download an output WAV
    GET  /                 -> single-page UI
"""

import os
import re
import glob
import time
import uuid
import logging
import threading
from datetime import datetime

# Make Python trust the OS certificate store (Windows/macOS). Needed when an
# antivirus or corporate proxy does TLS interception — otherwise the one-time
# HuggingFace model download fails with CERTIFICATE_VERIFY_FAILED. No-op if the
# package isn't installed.
try:
    import truststore

    truststore.inject_into_ssl()
except Exception:  # noqa: BLE001
    pass

# NOTE: torch / torchaudio / chatterbox are imported lazily inside get_model()
# so the Flask server (and UI) always start, even if the heavy ML stack isn't
# fully installed yet.
from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory,
    render_template,
    abort,
)
from werkzeug.utils import secure_filename

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PROFILE_DIR = os.path.join(BASE_DIR, "profiles")

for d in (OUTPUT_DIR, UPLOAD_DIR, PROFILE_DIR):
    os.makedirs(d, exist_ok=True)

ALLOWED_EXTENSIONS = {"wav", "mp3", "flac", "ogg", "m4a"}
MAX_CHARS = 8000               # whole-script cap (chunked internally)
CHUNK_MAX = 280                # target characters per generated chunk
GAP_SECONDS = 0.35             # silence inserted between stitched chunks
MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB upload cap
HISTORY_LIMIT = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("voice-clone")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
# Pick up edits to templates/index.html on refresh without a server restart.
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True

# --------------------------------------------------------------------------- #
# Model loading (lazy — only loaded on first job so the server boots fast)
# --------------------------------------------------------------------------- #
_model = None


def _pick_device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_model():
    """Load the Chatterbox model once and cache it."""
    global _model
    if _model is not None:
        return _model
    from chatterbox.tts import ChatterboxTTS  # imported lazily

    device = _pick_device()
    log.info("Loading Chatterbox TTS model on device: %s ...", device)
    t0 = time.time()
    _model = ChatterboxTTS.from_pretrained(device=device)
    log.info("Model loaded in %.1fs", time.time() - t0)
    return _model


# --------------------------------------------------------------------------- #
# Async job registry (single-worker: CPU model runs one job at a time)
# --------------------------------------------------------------------------- #
JOBS = {}                       # job_id -> dict(status, total, done, message, ...)
_gen_lock = threading.Lock()    # serialise generation
_active = {"running": False}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def split_text(text: str, max_len: int = CHUNK_MAX):
    """Split a long script into chunks <= max_len, preferring sentence ends."""
    text = " ".join(text.split())  # collapse whitespace/newlines
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, cur = [], ""
    for s in sentences:
        if not s:
            continue
        # a single sentence longer than max_len -> break on commas, then hard
        if len(s) > max_len:
            parts = re.split(r"(?<=[,;:])\s+", s)
            pieces = []
            for p in parts:
                while len(p) > max_len:
                    pieces.append(p[:max_len])
                    p = p[max_len:]
                if p:
                    pieces.append(p)
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


def list_history(limit: int = HISTORY_LIMIT):
    files = []
    for name in os.listdir(OUTPUT_DIR):
        if not name.lower().endswith(".wav"):
            continue
        path = os.path.join(OUTPUT_DIR, name)
        try:
            stat = os.stat(path)
        except OSError:
            continue
        files.append(
            {
                "filename": name,
                "url": f"/download/{name}",
                "size_kb": round(stat.st_size / 1024, 1),
                "created": datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "mtime": stat.st_mtime,
            }
        )
    files.sort(key=lambda f: f["mtime"], reverse=True)
    for f in files:
        f.pop("mtime", None)
    return files[:limit]


def make_output_name(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    slug = slug[:32] or "clip"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{slug}-{stamp}-{uuid.uuid4().hex[:6]}.wav"


def profile_path(name: str):
    """Return the stored AUDIO file path for a profile name, or None."""
    safe = secure_filename(name)
    if not safe:
        return None
    for ext in ALLOWED_EXTENSIONS:
        p = os.path.join(PROFILE_DIR, f"{safe}.{ext}")
        if os.path.exists(p):
            return p
    return None


def read_transcript(base: str) -> str:
    tpath = os.path.join(PROFILE_DIR, base + ".txt")
    if os.path.exists(tpath):
        try:
            with open(tpath, encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            pass
    return ""


def list_profiles():
    out, seen = [], set()
    for path in sorted(glob.glob(os.path.join(PROFILE_DIR, "*.*"))):
        base, ext = os.path.splitext(os.path.basename(path))
        ext = ext.lstrip(".").lower()
        if ext not in ALLOWED_EXTENSIONS or base in seen:
            continue
        seen.add(base)
        out.append(
            {
                "name": base,
                "size_kb": round(os.path.getsize(path) / 1024, 1),
                "transcript": read_transcript(base),
                "audio_url": f"/profile/{base}/audio",
            }
        )
    return out


# --------------------------------------------------------------------------- #
# Generation worker
# --------------------------------------------------------------------------- #
def run_job(job_id, chunks, ref_path, cleanup_ref, exaggeration, cfg_weight, temperature):
    job = JOBS[job_id]
    with _gen_lock:
        _active["running"] = True
        try:
            import torch
            import torchaudio as ta

            job["status"] = "loading"
            job["message"] = "Loading model (first run can take ~1 min)…"
            model = get_model()
            sr = model.sr
            gap = torch.zeros(1, int(GAP_SECONDS * sr))

            job["status"] = "running"
            wavs = []
            for i, chunk in enumerate(chunks, 1):
                job["done"] = i - 1
                job["message"] = f"Generating part {i} of {len(chunks)}…"
                log.info("[%s] part %d/%d (%d chars)", job_id[:6], i, len(chunks), len(chunk))
                wav = model.generate(
                    chunk,
                    audio_prompt_path=ref_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                    temperature=temperature,
                )
                wavs.append(wav)
                if i < len(chunks):
                    wavs.append(gap)

            job["message"] = "Stitching & saving…"
            full = torch.cat(wavs, dim=1)
            out_name = make_output_name(chunks[0])
            ta.save(os.path.join(OUTPUT_DIR, out_name), full, sr)

            job["done"] = len(chunks)
            job["status"] = "done"
            job["message"] = "Done"
            job["filename"] = out_name
            job["url"] = f"/download/{out_name}"
            job["history"] = list_history()
            log.info("[%s] saved %s", job_id[:6], out_name)
        except Exception as exc:  # noqa: BLE001
            log.exception("Generation failed")
            job["status"] = "error"
            job["error"] = (
                "Voice generation failed. Make sure the reference clip is clear "
                f"speech (10–60s). Details: {exc}"
            )
        finally:
            _active["running"] = False
            if cleanup_ref and ref_path:
                try:
                    os.remove(ref_path)
                except OSError:
                    pass


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    return render_template("index.html", max_chars=MAX_CHARS)


@app.route("/generate", methods=["POST"])
def generate():
    if _active["running"]:
        return jsonify({"error": "A generation is already running. Please wait for it to finish."}), 409

    text = (request.form.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Please enter some text to speak."}), 400
    if len(text) > MAX_CHARS:
        return jsonify({"error": f"Script too long (max {MAX_CHARS} characters)."}), 400

    def _fparam(name, default, lo, hi):
        try:
            return max(lo, min(hi, float(request.form.get(name, default))))
        except (TypeError, ValueError):
            return default

    exaggeration = _fparam("exaggeration", 0.5, 0.25, 1.0)
    cfg_weight = _fparam("cfg_weight", 0.3, 0.0, 1.0)
    temperature = _fparam("temperature", 0.7, 0.05, 1.5)

    # --- resolve the reference voice: saved profile OR fresh upload --------- #
    ref_path, cleanup_ref = None, False
    profile = (request.form.get("profile") or "").strip()
    upload = request.files.get("audio")

    if upload is not None and upload.filename:
        if not allowed_file(upload.filename):
            return jsonify({"error": "Unsupported audio format. Use WAV, MP3, FLAC, OGG or M4A."}), 400
        ref_name = secure_filename(upload.filename)
        ref_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex[:8]}-{ref_name}")
        upload.save(ref_path)
        cleanup_ref = True
    elif profile:
        ref_path = profile_path(profile)
        if not ref_path:
            return jsonify({"error": f"Saved voice '{profile}' not found."}), 404
    else:
        return jsonify({"error": "Choose a saved voice or upload a reference clip."}), 400

    chunks = split_text(text)
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {
        "status": "queued",
        "total": len(chunks),
        "done": 0,
        "message": "Starting…",
        "url": None,
        "filename": None,
        "error": None,
        "history": None,
    }
    threading.Thread(
        target=run_job,
        args=(job_id, chunks, ref_path, cleanup_ref, exaggeration, cfg_weight, temperature),
        daemon=True,
    ).start()
    return jsonify({"job_id": job_id, "total": len(chunks)})


@app.route("/status/<job_id>")
def status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Unknown job."}), 404
    return jsonify(job)


@app.route("/profiles")
def profiles():
    return jsonify({"profiles": list_profiles()})


@app.route("/profile", methods=["POST"])
def save_profile():
    name = (request.form.get("name") or "").strip()
    safe = secure_filename(name)
    if not safe:
        return jsonify({"error": "Please provide a valid profile name."}), 400
    f = request.files.get("audio")
    if f is None or not f.filename:
        return jsonify({"error": "Please attach a reference clip to save."}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": "Unsupported audio format. Use WAV, MP3, FLAC, OGG or M4A."}), 400
    # remove any existing profile with the same name (audio + transcript)
    for old in glob.glob(os.path.join(PROFILE_DIR, safe + ".*")):
        try:
            os.remove(old)
        except OSError:
            pass
    ext = f.filename.rsplit(".", 1)[1].lower()
    f.save(os.path.join(PROFILE_DIR, f"{safe}.{ext}"))

    transcript = (request.form.get("transcript") or "").strip()
    if transcript:
        with open(os.path.join(PROFILE_DIR, f"{safe}.txt"), "w", encoding="utf-8") as fh:
            fh.write(transcript)

    log.info("Saved voice profile '%s'", safe)
    return jsonify({"saved": safe, "profiles": list_profiles()})


@app.route("/profile/<name>/audio")
def profile_audio(name):
    p = profile_path(name)
    if not p:
        abort(404)
    return send_from_directory(PROFILE_DIR, os.path.basename(p), as_attachment=False)


@app.route("/profile/<name>", methods=["DELETE"])
def delete_profile(name):
    p = profile_path(name)
    if not p:
        return jsonify({"error": "Profile not found."}), 404
    safe = secure_filename(name)
    for f in glob.glob(os.path.join(PROFILE_DIR, safe + ".*")):
        try:
            os.remove(f)
        except OSError:
            pass
    return jsonify({"profiles": list_profiles()})


@app.route("/history")
def history():
    return jsonify({"history": list_history()})


@app.route("/download/<path:filename>")
def download(filename):
    safe = secure_filename(filename)
    if not safe or not os.path.exists(os.path.join(OUTPUT_DIR, safe)):
        abort(404)
    return send_from_directory(OUTPUT_DIR, safe, as_attachment=False)


@app.route("/output/<path:filename>", methods=["DELETE"])
def delete_output(filename):
    safe = secure_filename(filename)
    p = os.path.join(OUTPUT_DIR, safe)
    if not safe or not os.path.exists(p):
        return jsonify({"error": "File not found."}), 404
    try:
        os.remove(p)
    except OSError:
        pass
    return jsonify({"history": list_history()})


@app.errorhandler(413)
def too_large(_e):
    return jsonify({"error": "Upload too large (max 25 MB)."}), 413


if __name__ == "__main__":
    # PORT env var lets hosts override (Hugging Face Spaces uses 7860); default 5000.
    port = int(os.environ.get("PORT", "5000"))
    log.info("Voice clone server starting on http://0.0.0.0:%d", port)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
