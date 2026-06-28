# 🚀 Running Voice Clone Studio online

GitHub stores the code; it doesn't run it. Below are two ready-to-use ways to run
the app online. Pick whichever fits — the files for both are already in this repo.

| | 🤗 Hugging Face Spaces | ▶️ Google Colab |
|---|---|---|
| Cost | Free (CPU) | Free |
| Speed | Slow (~min/clip on CPU) | **Fast** (free GPU) |
| Stays online? | ✅ Always-on, public URL | ❌ Only while the notebook runs |
| Best for | A permanent public demo | Quick, fast personal use |

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
