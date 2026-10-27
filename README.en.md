<p align="center">
  <img src="assets/icon/krypt-256.png" alt="Krypt" width="120"/>
</p>

<h1 align="center">Krypt</h1>

<p align="center">
  <b>Record your meetings and audio on Windows and transcribe them with AI, with every speaker identified.</b><br/>
  Zoom · Teams · Meet · web calls · WhatsApp voice notes
</p>

<p align="center">
  <a href="README.md">🇪🇸 Español</a> · 🇬🇧 English
</p>

<p align="center">
  <a href="https://github.com/cristiancorpse5555/krypt/releases/latest"><img alt="Download" src="https://img.shields.io/github/v/release/cristiancorpse5555/krypt?label=download&color=2ea44f"/></a>
  <img alt="Windows" src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6"/>
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue"/></a>
</p>

---

## What does it do?

Krypt records **your computer's sound and your microphone at the same time** (you and everyone else on the call), saves
it as a lightweight MP3 and transcribes it with **Google Gemini**. The result is a text file (Markdown) like this:

```markdown
**[00:00:04] [Speaker 1]:** Good morning, let's start with the project update.
**[00:00:11] [Speaker 2]:** Great. Section two was finished on Friday.
```

- 🎧 **Records the whole call:** system audio + microphone, in sync.
- 👥 **Identifies each speaker** and adds the **exact time** of every turn.
- 🌎 **Transcribes in the language being spoken** (Spanish, English and more).
- 📎 **Imports audio files** from WhatsApp (`.ogg`/`.opus`), MP3, WAV, M4A, FLAC and more.
- ⏸️ **Pause and resume** recording at any time.
- ⏱️ **Long meetings are fine:** anything over 28 minutes is split and joined back automatically.
- 🔒 **Your files stay on your PC.** Audio is only sent to Google to be transcribed and is deleted from there afterwards.
- 💸 **Free:** uses Google Gemini's free tier with your own key.

> [!NOTE]
> Krypt's interface is in **Spanish** (*Grabar* = Record, *Pausar* = Pause, *Detener* = Stop, *Subir Audio* = Upload
> audio). Transcriptions are produced in whatever language is spoken in the audio.

## 📥 Installation (for anyone)

1. Go to **[Downloads (Releases)](https://github.com/cristiancorpse5555/krypt/releases/latest)** and download
   **`Krypt_Setup_v3.4.exe`** (under *Assets*).
2. Double-click the downloaded file.
3. **If Windows shows "Windows protected your PC"** (this happens with new programs that haven't bought a code-signing
   certificate): click **"More info"** and then **"Run anyway"**.
4. Follow the wizard (*Next → Install*). Krypt is added to the **Start menu** and the **Desktop**.
5. The first time you open it, it asks for your **Google Gemini key** →
   **[how to get one for free, step by step](docs/GET_API_KEY.md)** (3 minutes).

You don't need to install Python or anything else: the installer includes everything.

**Requirements:** 64-bit Windows 10 or 11, an internet connection to transcribe, and speakers or headphones connected
(Windows needs an active audio output to capture the computer's sound).

## 🎙️ How to use it

> [!WARNING]
> **Muting yourself in Teams, Meet or Zoom does NOT mute you in Krypt.**
>
> Krypt records the **computer's microphone** directly, not the meeting's. If you only mute yourself inside Teams or
> Meet, the other participants stop hearing you, **but Krypt keeps recording you**: anything you say "while muted" will
> end up in the recording and in the transcript.
>
> **To keep something off the record, mute the computer's microphone**, not just the meeting:
> - With your device's **microphone mute key or button** (many laptops have a key with a crossed-out microphone, and
>   many headsets have a mute button).
> - Or from Windows: sound icon next to the clock → mute the microphone.
> - Or press **⏸ Pausar** (Pause) in Krypt while you say something that shouldn't be recorded.

### Record a meeting
1. Open Krypt and press **⏺ Grabar** (Record).
2. Join your meeting (Zoom, Teams, Meet…). Krypt captures what plays on the PC plus your microphone.
3. Use **⏸ Pausar / ▶ Reanudar** (Pause / Resume) if needed. Remember: muting yourself in the meeting doesn't mute you
   in Krypt (see the warning above).
4. Press **⏹ Detener** (Stop). Krypt saves the MP3 and **starts transcribing automatically**.
5. When it's done, the transcript opens.

### Transcribe an audio file you already have
Press **📎 Subir Audio** (Upload audio), choose the file and then **📤** on its card.

### The history
Each recording shows up as a card:

| Button | Action |
|---|---|
| 📄 | View the transcript |
| 📤 / 🔄 | Transcribe · retry · transcribe again with another model |
| ✏️ | Rename |
| 🗑 | Delete the audio and its transcript |
| 📂 / 📝 | Open the audio folder / transcripts folder |

### Choosing the model
Under **Modelo IA** (AI model) you can pick:
- **Gemini 3.5 Transcribe** *(default)*: native transcription with speakers and exact timestamps.
- **Auto-Seleccionar** (Auto-select): if a model runs out of free quota, it moves on to the next one.
- **Gemini 3.7 Flash / 3.5 Flash Lite** and others: alternatives if the day's quota runs out.

### Where are my files?
Everything is in **`Documents\Krypt`**: `grabaciones\` (MP3 recordings), `transcripciones\` (Markdown transcripts) and
your settings.

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| "No se encontró dispositivo de loopback" (no loopback device found) | Connect speakers or headphones and set them as Windows' default output. |
| "Cuota agotada" (quota exhausted, 429 / limit: 0) | The day's free quota for that model is used up: pick another one under **Modelo IA** or use *Auto-Seleccionar*. |
| "Servidor sobrecargado" (server overloaded, 503) | Krypt retries 3 times on its own; if it persists, wait a few minutes or switch models. |
| "API Key inválida" (invalid API key) | Check it under ⚙️ → *Probar Conexión* (Test connection). See [the key guide](docs/GET_API_KEY.md). |
| Something I said while muted in the meeting got recorded | Krypt records the computer's microphone, not Teams/Meet's. Mute the device's microphone or use **⏸ Pausar**. |
| The recording is silent | Make sure sound plays through the default speakers/headphones and that microphone access is allowed in *Windows Settings → Privacy → Microphone*. |

## 👩‍💻 For developers

Krypt is built with **Python 3.13**, **PySide6** (UI), **PyAudioWPatch** (WASAPI capture), **FFmpeg** (audio) and
**google-genai** (Gemini). Architecture details (in Spanish) in [`DESARROLLO.md`](DESARROLLO.md).

```bash
git clone https://github.com/cristiancorpse5555/krypt.git
cd krypt
py -3.13 -m venv venv
venv\Scripts\pip install -r requirements.txt
```

1. Download FFmpeg for Windows (<https://www.gyan.dev/ffmpeg/builds/>) and copy `ffmpeg.exe` and `ffprobe.exe` into a
   `bin\` folder inside the project (they're not in the repository because of their size).
2. Run from source: **`Krypt_Dev.bat`**.
3. Build the installer: install [Inno Setup 6](https://jrsoftware.org/isinfo.php) and run **`build_installer.bat`**
   → `dist_installer\Krypt_Setup_v3.4.exe`.

Found a bug or have an idea? Open an **[Issue](https://github.com/cristiancorpse5555/krypt/issues)** (English or
Spanish). Pull requests are welcome.

## 📄 License

Code under the **[MIT](LICENSE)** license © 2026 DMT Consultora.
The installer bundles third-party components (FFmpeg under GPL v3, Qt under LGPL v3, among others): see
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

Krypt is not affiliated with Google. Gemini and Google AI Studio are trademarks of Google LLC.
