# 🎙️ Voice Clone Studio

A local, web-based AI **voice cloning** tool. Upload a short reference clip,
type a script, and Chatterbox TTS speaks your text in that voice — all running
on your own machine. No cloud, no account, no database.

Built with **Python (Flask)** + **[Chatterbox TTS](https://github.com/resemble-ai/chatterbox)**
(Resemble AI, MIT license).

---

## ✨ Features

- Clean, dark, single-page UI (Tailwind via CDN)
- Upload a reference voice (WAV/MP3/FLAC/OGG/M4A, ~10–60 s)
- **Saved voice profiles** — store a reference once, reuse it without re-uploading
- **Long scripts** — paste paragraphs/pages (up to 8000 chars); they're split into
  sentences and **stitched into one continuous WAV track**
- **Async generation with a live progress bar** ("Generating part 3 of 8…") so long
  jobs on CPU don't look frozen
- **Voice tuning** — `cfg_weight` / `temperature` / `exaggeration` sliders plus
  one-click **A / B / C presets** (punchy → cleanest) to reduce artifacts
- One-click **Generate** → in-browser audio player with auto-play
- **Download** the result as a WAV
- History of the last 5 generations with download links
- Live status indicator + friendly error handling

---

## 📁 Project structure

```
voice clone/
├── app.py                 # Flask backend / REST API
├── requirements.txt       # Python dependencies
├── README.md
├── templates/
│   └── index.html         # Single-page frontend
├── outputs/               # Generated WAV files (auto-created)
├── profiles/              # Saved voice profiles (auto-created, persistent)
└── uploads/               # Temp reference uploads (auto-created, auto-cleaned)
```

---

## 🔧 Setup

### 1. Prerequisites
- **Python 3.10 or 3.11** (Chatterbox/torch wheels are most reliable here)
- ~3–4 GB free disk for the model download on first run
- Optional but much faster: an NVIDIA GPU with CUDA (the app auto-detects
  CUDA / Apple MPS / CPU)

### 2. Create a virtual environment

**Windows (PowerShell):**
```powershell
cd "D:\webapp\voice clone"
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
cd "voice clone"
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **GPU users:** if you have CUDA, install a matching torch build first for big
> speedups, then the rest:
> ```bash
> pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
> pip install -r requirements.txt
> ```

### 4. Run
```bash
python app.py
```
Open **http://localhost:5000**

> The model is **lazy-loaded on the first Generate click**, so the server starts
> instantly. The first generation will take longer while the model downloads and
> loads into memory; subsequent runs are fast.

---

## 🔌 API reference

Generation is **asynchronous**: `POST /generate` returns a `job_id` immediately,
then you poll `GET /status/<job_id>` for progress and the final result.

| Method   | Endpoint              | Description                                            |
|----------|-----------------------|--------------------------------------------------------|
| `GET`    | `/`                   | Serves the single-page UI                              |
| `POST`   | `/generate`           | Form-data: `text`, plus either `audio` (file) **or** `profile` (saved name); optional `cfg_weight`/`temperature`/`exaggeration`. Returns `{job_id, total}` |
| `GET`    | `/status/<job_id>`    | Job progress/result: `{status, done, total, message, url, filename, history, error}` |
| `GET`    | `/profiles`           | List saved voice profiles                              |
| `POST`   | `/profile`            | Save a profile. Form-data: `name`, `audio` (file)      |
| `DELETE` | `/profile/<name>`     | Delete a saved profile                                 |
| `GET`    | `/history`            | Returns `{history: [...]}` — last 5 clips              |
| `GET`    | `/download/<filename>`| Streams / downloads a generated WAV                    |

**Example (`curl`):**
```bash
# save a reusable voice profile
curl -X POST http://localhost:5000/profile -F "name=gayan" -F "audio=@reference.wav"

# generate a (possibly long) script using the saved profile
curl -X POST http://localhost:5000/generate \
  -F "profile=gayan" \
  -F "text=Paste your whole script here. It can be many sentences long."
# -> {"job_id":"...","total":3}   then poll:
curl http://localhost:5000/status/<job_id>
```

---

## 💡 Tips for good results
- Use a **clean, single-speaker** reference clip with little background noise.
- 10–30 seconds of natural speech is usually plenty.
- **Save the clip as a profile** once, then just paste scripts and generate.
- Long scripts are auto-split into sentences and stitched into one track — but on
  CPU each sentence takes ~2–4 min, so a long script can take a while.
- Lower the **CFG/temperature** (presets B or C) if delivery sounds harsh or rushed.

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| Server won't start / `Failed to initialize NumPy` on `import torch` | You have NumPy 2.x. Run `pip install "numpy<2"`. (The app now lazy-loads torch so the UI still starts, but generation needs this fixed.) |
| `RuntimeError: operator torchvision::nms does not exist` | A leftover old `torchvision` is mismatched with the torch chatterbox installed. Remove it: `pip uninstall torchvision -y` (chatterbox doesn't need it). |
| `chatterbox-tts` fails to install | Use Python 3.10/3.11 (3.12 works but is less tested); upgrade pip; on Windows install the [MSVC Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) if a build error mentions a C++ compiler. |
| Very slow generation | You're on CPU. Install a CUDA torch build (see above) or expect ~minutes per clip. |
| Audio doesn't auto-play | Browsers block autoplay until you interact with the page — just press play. |
| `Upload too large` | Reference files are capped at 25 MB; trim the clip. |
| Out of memory | Use a shorter reference clip / shorter script, or run on a machine with more RAM/VRAM. |

---

## 📜 License & credits
- Your application code: use freely.
- **Chatterbox TTS** by **Resemble AI** — MIT license.
- Please use voice cloning **ethically** and only with consent of the speaker.
