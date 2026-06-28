# 🚀 Running Voice Clone Studio online

GitHub stores the code; it doesn't run it. Below are ready-to-use ways to run the
app online. The files for all of them are already in this repo.

| | ⭐ HF Space (ZeroGPU) | 🤗 HF Space (Docker, CPU) | ▶️ Google Colab |
|---|---|---|---|
| Cost | Free | Free | Free |
| Speed | **Fast** (on-demand GPU) | Slow (~min/clip) | Fast (GPU) |
| Stays online? | ✅ Always-on | ✅ Always-on | ❌ Only while notebook runs |
| Manual start each time? | ❌ No | ❌ No | ✅ Yes |
| UI | Gradio | Your custom Flask UI | Your custom Flask UI |
| Files | `huggingface_space/` | `Dockerfile` + `deploy/huggingface/` | `notebooks/` |

> **Recommended: ZeroGPU.** Always-on, free GPU, nothing to launch. The only
> trade-off is it uses a Gradio UI instead of the custom Flask one. This is the
> closest thing to "free GPU hosting with nothing to start."
>
> **Why there's no automatic Colab option:** Google Colab is an interactive
> notebook — it can't stay running on its own and hands out a new URL each run, so
> it always requires manually starting it. ZeroGPU replaces that need.

---

## Option ⭐ — Hugging Face Space with ZeroGPU (free GPU, always-on)

1. Create a free account at **https://huggingface.co**.
2. **New ▸ Space** → **SDK: Gradio**, name it, Create.
3. Upload the **contents of the `huggingface_space/` folder** to the Space root
   (`app.py`, `requirements.txt`, `README.md`). Easiest: clone the Space repo,
   copy those 3 files in, commit & push. (The Space's `README.md` must be the one
   from `huggingface_space/` — it has the Gradio + config header.)
4. **Settings ▸ Hardware ▸ select `ZeroGPU`** (free; may require a quick eligibility
   opt-in / PRO for higher limits, but the free tier works).
5. The Space builds and starts. First generation downloads the model (~1 min),
   then runs on a GPU. Share the Space URL — done, nothing to launch.

> ⚠️ Free-Space storage is ephemeral: saved profiles reset on restart. To keep them,
> add Persistent Storage in Settings or back them with a HF Dataset.

---

## Option A — Hugging Face Spaces (always-on)

1. Create a free account at **https://huggingface.co**.
2. **New** ▸ **Space**. Choose:
   - **SDK: Docker** (blank template)
   - Hardware: **CPU basic** (free) — or a **GPU** tier for speed (paid).
3. Push this project's files into the Space repo. Two easy ways:
   - **Link GitHub:** in the Space, *Settings ▸ link a GitHub repo* (if available), or
   - **Manual:** `git clone` your Space, copy in `app.py`, `templates/`,
     `requirements.txt`, `Dockerfile`, then commit & push.
4. **Important:** the Space's `README.md` must contain the Hugging Face config
   header. Use the one in [`deploy/huggingface/README.md`](deploy/huggingface/README.md)
   — copy it to the Space root as `README.md`.
5. The Space builds the Docker image and starts automatically. First load downloads
   the model (a few minutes). Done — share the Space URL.

> Free CPU Spaces have ~16 GB RAM (enough), but generation is slow. Upgrade the
> Space hardware to a GPU in Settings for fast results.

---

## Option B — Google Colab (fast, temporary)

1. Open **https://colab.research.google.com** ▸ **File ▸ Upload notebook** ▸ pick
   [`notebooks/voice_clone_colab.ipynb`](notebooks/voice_clone_colab.ipynb)
   (or open it straight from GitHub via *File ▸ Open notebook ▸ GitHub*).
2. Set **Runtime ▸ Change runtime type ▸ T4 GPU**.
3. In the first code cell, set `REPO_URL` to your GitHub repo URL.
4. **Runtime ▸ Run all.** The last cell prints a public
   `https://….trycloudflare.com` link — open it.
5. Keep the Colab tab open; the link stops working when the session ends.

---

## Note on data & profiles
`outputs/`, `uploads/`, and `profiles/` are git-ignored and are **not** uploaded.
On a fresh deployment the app starts with no saved voice profiles — create them
from the **Create Voice Profile** tab after it's running.
