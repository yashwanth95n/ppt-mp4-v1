# Slides to Voice — PPT → narrated video (all-Gemini pipeline)

Upload a `.pptx`, pick a narrator (male/female, Indian-accented English) and a
speaking speed, and get back an MP4 with every slide voiced over. Script
length is auto-scaled — and the final video is auto-padded if needed — so a
10-slide deck produces at least a 20-minute video, no matter which speed you
pick.

**Both AI steps run on Gemini, using the one API key you already have:**
- **Script writing**: `gemini-2.5-flash` writes the spoken narration for each slide.
- **Voice**: Gemini's native TTS models (`gemini-2.5-flash-preview-tts` /
  `gemini-2.5-pro-preview-tts`) generate the actual audio — a real generative
  voice model, not a traditional TTS engine. Accent, tone, and pace are all
  steered with a natural-language instruction baked into the request (Gemini
  TTS doesn't take a numeric "rate" parameter the way older TTS engines do).

Slide rendering (LibreOffice/poppler) and final video assembly (ffmpeg) stay
local — no AI needed there, they're just file format conversion.

## How it works
1. `python-pptx` reads each slide's title, bullet text, and speaker notes.
2. Gemini (text model) expands that into a spoken narration script, long
   enough to fill that slide's target on-screen time.
3. Gemini (TTS model) turns the script into audio, instructed to speak in
   an Indian English accent, at the gender/pace you picked.
4. LibreOffice + poppler render each slide to a PNG image.
5. ffmpeg pairs each image with its audio (held on screen for exactly the
   audio's length), then concatenates all slides into one MP4.
6. If the assembled video comes in under your minimum length — Gemini TTS's
   pace is instruction-steered, not exact, so this can happen — the app
   automatically pads the tail with a frozen last frame + silence to meet it.

## 1. Install system dependencies
You need **LibreOffice**, **poppler-utils** (for `pdftoppm`), and **ffmpeg**.

- Windows: `winget install TheDocumentFoundation.LibreOffice`, `winget install Gyan.FFmpeg`, `winget install oschwartz10612.Poppler` (reopen your terminal afterward)
- macOS: `brew install libreoffice poppler ffmpeg`
- Ubuntu/Debian: `sudo apt install libreoffice poppler-utils ffmpeg`

## 2. Install Python dependencies
```bash
cd ppt2video
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

## 3. Get your API key
- Go to https://aistudio.google.com/apikey, sign in with any Google account,
  click **Create API key**.
- Copy `.env.example` to `.env` (`copy .env.example .env` on Windows, `cp` on
  Mac/Linux) and paste the key in as `GEMINI_API_KEY`.

### About the Pro TTS model
`GEMINI_TTS_MODEL` in `.env` defaults to `gemini-2.5-flash-preview-tts`,
which works on the free tier. `gemini-2.5-pro-preview-tts` sounds noticeably
better but **requires a paid/billing-enabled API project** — this is
different from a "Gemini Plus"/Google AI Pro *app* subscription. To check or
enable it: go to https://aistudio.google.com, open your project's API key
settings, and see whether it's on the free tier or has billing linked. If it
does, switch the env var to the pro model.

**Free tier limits to know**: roughly 1,000+ requests/day, ~10-15
requests/minute for the flash models. One conversion of a 10-slide deck
uses about 10 script calls + 10 TTS calls — comfortably inside that.

## 4. Run it
```bash
python app.py
```
This starts the server on **port 8086**.

## 5. Access it
Open your browser to:

**http://localhost:8086/home**

Upload a `.pptx`, choose the narrator's gender and speed, hit **Convert to
video**, and watch the progress bar. When it finishes, the video plays back
right on the page and you can download the MP4.

## Notes & things you may want to adjust
- **Voices**: `converter/tts.py` maps "male"/"female" to `Charon` and
  `Kore`. There are 30 official Gemini TTS voices with different
  personalities (Puck = upbeat, Zephyr = bright, Enceladus = breathy,
  etc.) — swap the `VOICE_MAP` values for a different narrator personality.
- **Accent**: steered via the instruction Gemini is given
  ("...in a warm, natural Indian English accent..."), not a separate
  language parameter. Edit that sentence in
  `converter/tts.py::synthesize_to_file` for Hindi-accented English, a
  different regional accent, etc.
- **Minimum video length**: `MIN_TOTAL_MINUTES` in `converter/pipeline.py`
  (defaults to 20), divided evenly across the slide count with a
  2-minute-per-slide floor. The automatic tail-padding step (see above)
  backstops this against Gemini TTS's variable pacing.
- **Large decks**: conversion time scales with slide count — each slide
  needs one LLM call, one TTS call, and one ffmpeg encode. A 10-slide deck
  should take a few minutes; expect longer for bigger decks.
- **Jobs are in-memory**: restarting the server clears job history (not the
  generated files, which stay in `jobs/<job_id>/output.mp4`).
- This is a working scaffold, not a hardened production app — for real
  deployment you'd want persistent job storage (e.g. Redis), auth, and
  input validation hardening.
