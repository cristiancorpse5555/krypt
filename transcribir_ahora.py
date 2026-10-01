"""
=============================================================
  TRANSCRIPTOR - Script CLI de emergencia (v3.0)
  Transcribe un audio especifico con Gemini o Groq (Whisper)
  Chunks de 20 min (Gemini) o 5 min (Groq) con compresion MP3
=============================================================

Uso:
    python transcribir_ahora.py                           -> transcribe el audio mas reciente
    python transcribir_ahora.py REC_20260708_193940.wav   -> transcribe ese audio especifico
    python transcribir_ahora.py REC_20260708_193940.wav 5 -> modelo 5 (Groq Whisper)
"""

import sys
import io

# Configurar stdout/stderr para UTF-8 (necesario en consola Windows cp1252)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import os
import json
import time
import wave
import tempfile
import subprocess
import sys

# Flag para ocultar ventanas de consola de FFmpeg/ffprobe en Windows
_SUBPROCESS_FLAGS = 0
if sys.platform == "win32":
    _SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW
from pathlib import Path
from datetime import datetime

# =============================================================
#  CONFIGURACION
# =============================================================
# Cargar API key desde config.json de Krypt si existe
CONFIG_PATH = Path.home() / "Documents" / "Krypt" / "config.json"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if CONFIG_PATH.exists():
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if data.get("gemini_api_key"):
            GEMINI_API_KEY = data["gemini_api_key"]
    except Exception:
        pass

MODELS = {
    "1": ("gemini-3.5-transcribe",  "Gemini 3.5 Transcribe - Modelo por defecto (Diarización nativa)"),
    "2": ("auto",                  "Auto-Seleccionar (Gemini 3.5 con fallback a 3.7 y 3.5 Flash Lite)"),
    "3": ("gemini-3.7-flash",       "Gemini 3.7 Flash - Recomendado Flash"),
    "4": ("gemini-3.6-flash",       "Gemini 3.6 Flash - Modelo anterior"),
    "5": ("gemini-3.5-flash-lite",   "Gemini 3.5 Flash Lite - Economico y veloz"),
    "6": ("gemini-3.5-flash",       "Gemini 3.5 Flash - Modelo legacy"),
    "7": ("gemini-3-flash-preview",  "Gemini 3 Flash Preview - Mas cuota"),
    "8": ("gemini-3.1-flash-lite",   "Gemini 3.1 Flash Lite - Emergencia"),
    "9": ("gemini-3.1-pro-preview",  "Gemini 3.1 Pro Preview - Max precision"),
}
DEFAULT_MODEL_KEY = "1"

CHUNK_MINUTES = 25           # Default chunks para Gemini (25 min)
SAMPLE_WIDTH = 2
MAX_RETRIES = 3
RETRY_DELAYS = [20, 45, 90]

APP_DIR = Path(__file__).parent
RECORDINGS_DIR   = APP_DIR / "grabaciones"
TRANSCRIPTIONS_DIR = APP_DIR / "transcripciones"

# =============================================================
#  IMPORTS
# =============================================================
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: No se encontro google-genai. Instala con: pip install google-genai")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("ERROR: No se encontro numpy. Instala con: pip install numpy")
    sys.exit(1)


# =============================================================
#  AUDIO HELPERS
# =============================================================
def fmt_size(b):
    if b < 1024**2:
        return f"{b/1024:.0f} KB"
    return f"{b/1024**2:.1f} MB"

def fmt_dur(sec):
    h, r = divmod(int(sec), 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def get_audio_duration(audio_path: Path) -> float:
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, check=True, creationflags=_SUBPROCESS_FLAGS)
        return float(res.stdout.strip())
    except Exception:
        pass
    if audio_path.suffix.lower() == ".wav":
        try:
            with wave.open(str(audio_path), "rb") as wf:
                return wf.getnframes() / wf.getframerate()
        except Exception:
            pass
    return 0.0

def compress_to_mp3(wav_path: Path) -> Path:
    mp3_path = wav_path.with_suffix(".mp3")
    try:
        log(f"Comprimiendo {wav_path.name} a MP3 (48kbps mono)...")
        cmd = [
            "ffmpeg", "-y", "-i", str(wav_path),
            "-codec:a", "libmp3lame", "-b:a", "48k", "-ac", "1",
            str(mp3_path)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=True, creationflags=_SUBPROCESS_FLAGS)
        return mp3_path
    except Exception as e:
        log(f"Advertencia: no se pudo comprimir a MP3 ({e}), usando WAV.")
        return wav_path

def split_audio_ffmpeg(input_path: Path, chunk_sec: float, total_sec: float) -> list[Path]:
    chunks = []
    if total_sec <= chunk_sec + 10:
        return [input_path]
        
    import tempfile
    tmp_dir = Path(tempfile.mkdtemp(prefix="transcriptor_split_"))
    
    num_chunks = int(np.ceil(total_sec / chunk_sec))
    for i in range(num_chunks):
        start_sec = i * chunk_sec
        output_chunk = tmp_dir / f"chunk_{i:02d}{input_path.suffix}"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_sec),
            "-t", str(chunk_sec),
            "-i", str(input_path),
            "-c", "copy",
            str(output_chunk)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=True, creationflags=_SUBPROCESS_FLAGS)
            if output_chunk.exists() and output_chunk.stat().st_size > 1000:
                chunks.append(output_chunk)
        except Exception:
            pass
    return chunks if chunks else [input_path]


# =============================================================
#  SELECCION DE AUDIO & MODELO
# =============================================================
def pick_audio() -> Path:
    if len(sys.argv) > 1 and not sys.argv[1].isdigit():
        p = RECORDINGS_DIR / sys.argv[1]
        if not p.exists():
            p = Path(sys.argv[1])
        if not p.exists():
            print(f"ERROR: No se encontro: {sys.argv[1]}")
            sys.exit(1)
        return p

    wavs = sorted(list(RECORDINGS_DIR.glob("REC_*.wav")) + list(RECORDINGS_DIR.glob("REC_*.mp3")),
                  key=lambda f: f.stat().st_mtime, reverse=True)
    if not wavs:
        print("ERROR: No hay archivos de audio en grabaciones/")
        sys.exit(1)

    print("\nArchivos de audio disponibles (mas recientes primero):\n")
    for i, f in enumerate(wavs[:10]):
        size = fmt_size(f.stat().st_size)
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m %H:%M")
        est_dur = fmt_dur(get_audio_duration(f))
        print(f"  [{i}] {f.name}  |  {size}  |  ~{est_dur}  |  {mtime}")

    print()
    choice = input("Numero de audio (Enter = mas reciente [0]): ").strip()
    idx = int(choice) if choice.isdigit() else 0
    return wavs[min(idx, len(wavs)-1)]

def pick_model() -> str:
    if len(sys.argv) > 2 and sys.argv[2] in MODELS:
        key = sys.argv[2]
        name, desc = MODELS[key]
        print(f"\nModelo (desde argumento): {name} - {desc}")
        return name

    print("\nModelos disponibles:")
    for k, (name, desc) in MODELS.items():
        print(f"  [{k}] {name}  ->  {desc}")
    print()
    choice = input(f"Que modelo usar? (1-5, Enter = [{DEFAULT_MODEL_KEY}]): ").strip()
    key = choice if choice in MODELS else DEFAULT_MODEL_KEY
    name, desc = MODELS[key]
    print(f"Modelo seleccionado: {name}")
    return name


# =============================================================
#  PROMPT DE DIALOGO
# =============================================================
def build_prompt(offset_min: int, chunk_num: int, total: int) -> str:
    offset_note = ""
    if total > 1:
        h = offset_min // 60
        m = offset_min % 60
        offset_note = (
            f"\n\nEste es el segmento {chunk_num} de {total}. "
            f"Los timestamps del audio empiezan en 0:00, pero DEBES mostrarlos "
            f"sumando {offset_min} minutos al tiempo real del audio. "
            f"Ejemplo: si el audio marca 00:05:30, escribe [{h:02d}:{m+5:02d}:30]. "
            f"El segmento empieza en el minuto {offset_min} de la reunion total."
        )

    return f"""Eres un transcriptor profesional de reuniones. Tu unica tarea es 
transcribir LITERALMENTE todo lo que se dice en este audio, palabra por palabra.

REGLAS ABSOLUTAS - NO las ignores bajo ninguna circunstancia:
1. TRANSCRIBE TODO: Cada palabra, cada frase, cada intervencion. 
   PROHIBIDO resumir, condensar o saltarte partes del audio.
2. NUNCA inventes contenido: Si no entiendes algo, escribe [inaudible].
   JAMÁS rellenes con texto que no este en el audio.
3. IDIOMA: Transcribe en el idioma que se habla (principalmente espanol).
4. HABLANTES: Identifica cada hablante. Si detectas su nombre usalo,
   si no: [Hablante 1], [Hablante 2], etc. Se consistente durante toda la transcripcion.
5. TIMESTAMPS: Marca cada cambio de hablante con [HH:MM:SS].
6. FORMATO por intervencion:
   **[HH:MM:SS] [Nombre]:** Texto transcrito...
7. COMPLETITUD: Debes transcribir DESDE EL INICIO HASTA EL FINAL sin omitir nada.
8. Partes inaudibles o incomprensibles: [inaudible]
   Sonidos relevantes: [risas], [aplausos], [interrupcion]
{offset_note}

Comienza la transcripcion ahora. No escribas introducciones ni explicaciones. 
Solo la transcripcion:"""


# =============================================================
#  TRANSCRIPCION CON GEMINI
# =============================================================
def call_gemini(client, model: str, contents: list, chunk_num: int, total: int) -> str:
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            log(f"  Llamando a {model} (intento {attempt+1}/{MAX_RETRIES+1})...")
            resp = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=65535,
                ),
            )
            text = None
            try:
                text = resp.text
            except Exception:
                pass
            if not text:
                try:
                    text = resp.candidates[0].content.parts[0].text
                except Exception:
                    pass

            try:
                reason = resp.candidates[0].finish_reason
                reason_name = reason.name if reason and hasattr(reason, 'name') else str(reason)
                if reason_name == "MAX_TOKENS":
                    text = (text or "") + "\n\n> ADVERTENCIA: Respuesta cortada por limite de tokens."
                elif "SAFETY" in reason_name and not text:
                    text = "[Segmento bloqueado por filtros de seguridad de Gemini]"
            except Exception:
                pass

            return text if text else "[Sin texto en este segmento]"

        except Exception as e:
            last_err = e
            msg = str(e)
            is_quota   = "RESOURCE_EXHAUSTED" in msg or ("429" in msg and "limit: 0" in msg)
            is_retryable = ("503" in msg or "UNAVAILABLE" in msg or "500" in msg or
                            ("429" in msg and not is_quota))

            if is_quota:
                log(f"  ERROR: Cuota agotada en {model}. Prueba con otro modelo.")
                raise

            if is_retryable and attempt < MAX_RETRIES:
                wait = RETRY_DELAYS[attempt]
                log(f"  Servidor ocupado. Esperando {wait}s... (intento {attempt+1}/{MAX_RETRIES+1})")
                time.sleep(wait)
            else:
                raise

    raise last_err


# =============================================================
#  TRANSCRIPCION CON GEMINI 3.5 TRANSCRIBE (Interactions API)
# =============================================================
def format_interactions_transcription(interaction, offset_seconds: float = 0.0) -> str:
    words = []
    try:
        steps = getattr(interaction, "steps", []) or []
        for step in steps:
            contents = getattr(step, "content", []) or []
            for content in contents:
                annotations = getattr(content, "annotations", []) or []
                for ann in annotations:
                    ann_type = getattr(ann, "type", "") if not isinstance(ann, dict) else ann.get("type", "")
                    if ann_type == "word_info":
                        text = getattr(ann, "text", "") if not isinstance(ann, dict) else ann.get("text", "")
                        speaker = getattr(ann, "speaker", "") if not isinstance(ann, dict) else ann.get("speaker", "")
                        start_off = getattr(ann, "start_offset", "") if not isinstance(ann, dict) else ann.get("start_offset", "")
                        end_off = getattr(ann, "end_offset", "") if not isinstance(ann, dict) else ann.get("end_offset", "")
                        words.append({
                            "text": str(text).strip(),
                            "speaker": str(speaker).strip() if speaker else "spk:0",
                            "start_offset": str(start_off),
                            "end_offset": str(end_off)
                        })
    except Exception:
        words = []

    if not words:
        raw_text = getattr(interaction, "output_text", "") or ""
        return raw_text.strip() if raw_text else "[Sin texto en este segmento]"

    def parse_sec(offset_str: str) -> float:
        try:
            return float(str(offset_str).rstrip("s"))
        except Exception:
            return 0.0

    lines = []
    current_speaker = None
    current_start_sec = None
    current_words = []
    last_end_sec = 0.0

    for w in words:
        spk = w["speaker"] or "spk:0"
        if spk.startswith("spk:"):
            try:
                num = int(spk.split(":")[1]) + 1
                spk_label = f"Hablante {num}"
            except Exception:
                spk_label = spk
        elif spk.startswith("spk_"):
            try:
                num = int(spk.split("_")[1])
                spk_label = f"Hablante {num}"
            except Exception:
                spk_label = spk
        else:
            spk_label = spk

        start_sec = parse_sec(w["start_offset"]) + offset_seconds
        end_sec = parse_sec(w["end_offset"]) + offset_seconds

        if (current_speaker != spk_label) or (current_words and (start_sec - last_end_sec > 3.5)):
            if current_words:
                h = int(current_start_sec // 3600)
                m = int((current_start_sec % 3600) // 60)
                s = int(current_start_sec % 60)
                time_str = f"{h:02d}:{m:02d}:{s:02d}"
                speech_text = " ".join(current_words)
                lines.append(f"**[{time_str}] [{current_speaker}]:** {speech_text}")
            current_speaker = spk_label
            current_start_sec = start_sec
            current_words = [w["text"]]
        else:
            current_words.append(w["text"])
        last_end_sec = end_sec

    if current_words:
        h = int(current_start_sec // 3600)
        m = int((current_start_sec % 3600) // 60)
        s = int(current_start_sec % 60)
        time_str = f"{h:02d}:{m:02d}:{s:02d}"
        speech_text = " ".join(current_words)
        lines.append(f"**[{time_str}] [{current_speaker}]:** {speech_text}")

    return "\n\n".join(lines)


def call_gemini_interactions(client, uploaded, offset_seconds: float) -> str:
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            log(f"  Llamando a Gemini 3.5 Transcribe (intento {attempt+1}/{MAX_RETRIES+1})...")
            interaction = client.interactions.create(
                model="gemini-3.5-transcribe",
                input=[{
                    "type": "audio",
                    "uri": uploaded.uri,
                    "mime_type": uploaded.mime_type or "audio/wav",
                }],
                generation_config={
                    "transcription_config": {
                        "mode": {
                            "type": "verbatim",
                            "diarization_mode": "speaker",
                            "timestamp_granularities": ["word"],
                        }
                    }
                }
            )
            formatted = format_interactions_transcription(interaction, offset_seconds)
            return formatted if formatted else "[Sin texto en este segmento]"
        except Exception as e:
            last_err = e
            msg = str(e)
            is_quota = "RESOURCE_EXHAUSTED" in msg or ("429" in msg and "limit: 0" in msg)
            is_retryable = ("503" in msg or "UNAVAILABLE" in msg or "500" in msg or
                            ("429" in msg and not is_quota))
            if is_quota:
                log(f"  ERROR: Cuota agotada en gemini-3.5-transcribe.")
                raise
            if is_retryable and attempt < MAX_RETRIES:
                wait = RETRY_DELAYS[attempt]
                log(f"  Servidor ocupado. Esperando {wait}s... (intento {attempt+1}/{MAX_RETRIES+1})")
                time.sleep(wait)
            else:
                raise
    raise last_err


def transcribe_gemini_interactions(audio_path: Path, chunk_minutes: int) -> Path:
    duration = get_audio_duration(audio_path)
    if duration <= 28 * 60:
        chunks = [audio_path]
    else:
        chunks = split_audio_ffmpeg(audio_path, chunk_minutes * 60, duration)
    total = len(chunks)

    client = genai.Client(api_key=GEMINI_API_KEY)
    transcriptions = []
    errors = []

    for i, chunk in enumerate(chunks):
        num = i + 1
        is_temp = chunk != audio_path
        offset_seconds = i * chunk_minutes * 60
        offset_min = offset_seconds // 60

        print(f"\n--- Chunk {num}/{total} (min {offset_min}-{offset_min+chunk_minutes}) ---")

        log(f"Subiendo {chunk.name} ({fmt_size(chunk.stat().st_size)})...")
        try:
            uploaded = client.files.upload(file=str(chunk))
        except Exception as e:
            log(f"ERROR al subir chunk {num}: {e}")
            transcriptions.append(f"[Error al subir chunk {num}/{total}: {e}]")
            errors.append(str(e))
            continue

        log("Esperando procesamiento en Gemini Files API...")
        for tick in range(60):
            try:
                info = client.files.get(name=uploaded.name)
                if info.state and info.state.name == "ACTIVE":
                    break
                if info.state and info.state.name == "FAILED":
                    raise ValueError("Gemini rechazo el archivo (estado FAILED)")
            except ValueError:
                raise
            except Exception:
                pass
            time.sleep(2)

        try:
            text = call_gemini_interactions(client, uploaded, float(offset_seconds))
            transcriptions.append(text)
            lines = len(text.splitlines()) if text else 0
            log(f"OK - Chunk {num} transcrito ({lines} lineas con diarizacion)")
        except Exception as e:
            log(f"ERROR transcribiendo chunk {num}: {e}")
            transcriptions.append(f"[Error en chunk {num}/{total}: {e}]")
            errors.append(str(e))

        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass

        if is_temp:
            try:
                chunk.unlink()
            except Exception:
                pass

        if num < total:
            log("Pausa de 3s antes del siguiente chunk...")
            time.sleep(3)

    return save_markdown(audio_path, "gemini-3.5-transcribe", transcriptions, chunk_minutes, total, errors)


def transcribe_gemini(audio_path: Path, model: str, chunk_minutes: int) -> Path:
    chunks = split_audio_ffmpeg(audio_path, chunk_minutes * 60, get_audio_duration(audio_path))
    total  = len(chunks)

    client = genai.Client(api_key=GEMINI_API_KEY)
    transcriptions = []
    errors = []

    for i, chunk in enumerate(chunks):
        num     = i + 1
        is_temp = chunk != audio_path
        offset  = i * chunk_minutes

        print(f"\n--- Chunk {num}/{total} (min {offset}-{offset+chunk_minutes}) ---")

        # Upload
        log(f"Subiendo {chunk.name} ({fmt_size(chunk.stat().st_size)})...")
        try:
            uploaded = client.files.upload(file=str(chunk))
        except Exception as e:
            log(f"ERROR al subir chunk {num}: {e}")
            transcriptions.append(f"[Error al subir chunk {num}/{total}: {e}]")
            errors.append(str(e))
            continue

        # Esperar ACTIVE
        log("Esperando procesamiento en Gemini Files API...")
        for tick in range(60):
            try:
                info = client.files.get(name=uploaded.name)
                if info.state and info.state.name == "ACTIVE":
                    break
                if info.state and info.state.name == "FAILED":
                    raise ValueError("Gemini rechazo el archivo (estado FAILED)")
            except ValueError:
                raise
            except Exception:
                pass
            time.sleep(2)

        # Prompt y llamada
        prompt = build_prompt(offset, num, total)
        try:
            text = call_gemini(client, model, [prompt, uploaded], num, total)
            transcriptions.append(text)
            lines = len(text.splitlines()) if text else 0
            log(f"OK - Chunk {num} transcrito ({lines} lineas)")
        except Exception as e:
            log(f"ERROR transcribiendo chunk {num}: {e}")
            transcriptions.append(f"[Error en chunk {num}/{total}: {e}]")
            errors.append(str(e))

        # Limpiar archivo remoto
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass

        # Limpiar chunk temporal
        if is_temp:
            try:
                chunk.unlink()
            except Exception:
                pass

        # Pausa entre chunks para no saturar rate limits
        if num < total:
            log("Pausa de 3s antes del siguiente chunk...")
            time.sleep(3)

    return save_markdown(audio_path, model, transcriptions, chunk_minutes, total, errors)


# =============================================================
#  TRANSCRIPCION CON GROQ (Whisper + Llama 3.3)
# =============================================================
def llama_format(client, text: str) -> str:
    if not text.strip():
        return ""
    prompt = (
        "Eres un transcriptor experto de reuniones. Recibirás un texto de audio transcrito "
        "con timestamps al inicio de cada frase. Tu única tarea es estructurar y dar formato "
        "de diálogo al texto, identificando a los diferentes hablantes (e.g. [Hablante 1], [Hablante 2], "
        "etc.) de forma coherente según el flujo de la conversación.\n\n"
        "REGLAS:\n"
        "1. Agrupa las frases en párrafos por intervención.\n"
        "2. Mantén los timestamps originales al inicio de cada intervención (ajustándolos al formato **[HH:MM:SS] [Nombre]:**).\n"
        "3. Identifica a las personas por sus nombres si los mencionan en la conversación, de lo contrario sé consistente con [Hablante 1], [Hablante 2], etc.\n"
        "4. NO resumas, NO agregues comentarios y NO omitas palabras de la transcripción.\n"
        "5. Devuelve ÚNICAMENTE el diálogo formateado, sin introducciones ni explicaciones.\n"
    )
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"[Error formateando con Llama: {e}]\n\n{text}"


def transcribe_groq(audio_path: Path) -> Path:
    if not GROQ_API_KEY:
        print("ERROR: API key de Groq no encontrada en Api key grog.txt o variables de entorno.")
        sys.exit(1)

    # 1. Comprimir si es WAV para agilizar
    audio_to_use = audio_path
    is_temp_mp3 = False
    if audio_path.suffix.lower() == ".wav":
        audio_to_use = compress_to_mp3(audio_path)
        if audio_to_use != audio_path:
            is_temp_mp3 = True

    duration = get_audio_duration(audio_to_use)
    if duration <= 0:
        duration = 300.0

    # Chunks de 20 minutos para Groq (pesan ~7.2MB en MP3 a 48kbps, muy por debajo del límite de 25MB)
    groq_chunk_duration = 20 * 60
    chunks = split_audio_ffmpeg(audio_to_use, groq_chunk_duration, duration)
    total = len(chunks)

    log(f"Dividido en {total} parte(s) para Groq Whisper.")

    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    transcriptions = []
    errors = []

    for i, chunk in enumerate(chunks):
        num = i + 1
        is_temp_chunk = chunk != audio_to_use
        offset_min = i * groq_chunk_duration // 60

        print(f"\n--- Chunk {num}/{total} (min {offset_min}-{offset_min + 20}) ---")

        log(f"Subiendo a Groq Whisper ({fmt_size(chunk.stat().st_size)})...")
        try:
            with open(chunk, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(chunk.name, file.read()),
                    model="whisper-large-v3",
                    response_format="verbose_json",
                    language="es"
                )
            
            # Reconstruir timestamps
            segments_text = []
            for seg in getattr(transcription, "segments", []):
                start_sec = seg.get("start", 0) if isinstance(seg, dict) else getattr(seg, "start", 0)
                abs_sec = start_sec + (offset_min * 60)
                h = int(abs_sec // 3600)
                m = int((abs_sec % 3600) // 60)
                s = int(abs_sec % 60)
                t_val = seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
                segments_text.append(f"[{h:02d}:{m:02d}:{s:02d}] {t_val.strip()}")

            raw_timestamped = "\n".join(segments_text)
            
            log(f"Estructurando dialogo con Llama 3.3...")
            structured = llama_format(client, raw_timestamped)
            transcriptions.append(structured)
            log(f"OK - Chunk {num} completado.")
        except Exception as e:
            log(f"ERROR en segmento {num}: {e}")
            transcriptions.append(f"[Error en segmento {num}: {e}]")
            errors.append(str(e))

        if is_temp_chunk:
            try:
                chunk.unlink()
            except Exception:
                pass

    # Limpiar archivo MP3 temporal
    if is_temp_mp3 and audio_to_use.exists():
        try:
            audio_to_use.unlink()
        except Exception:
            pass

    return save_markdown(audio_path, "groq-whisper (Llama-3.3)", transcriptions, 5, total, errors)


# =============================================================
#  GUARDAR RESULTADO
# =============================================================
def save_markdown(audio_path: Path, model: str, transcriptions: list, chunk_minutes: int, total: int, errors: list) -> Path:
    TRANSCRIPTIONS_DIR.mkdir(parents=True, exist_ok=True)
    log("Guardando transcripcion...")

    ts          = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dt_display  = datetime.now().strftime("%d de %B de %Y, %H:%M")
    name_clean  = audio_path.stem
    fname       = f"Transcripcion_{ts}_{name_clean}.md"
    out_path    = TRANSCRIPTIONS_DIR / fname

    try:
        dt_audio   = datetime.strptime(name_clean, "REC_%Y%m%d_%H%M%S")
        audio_name = dt_audio.strftime("Grabacion %d de %B de %Y, %H:%M")
    except Exception:
        audio_name = name_clean

    lines = [
        f"# Transcripcion: {audio_name}",
        "",
        f"**Fecha:** {dt_display}",
        f"**Modelo:** {model}",
        f"**Chunks:** {total} segmentos de {chunk_minutes} min",
        f"**Audio:** {audio_path.name}",
        "",
        "---",
        "",
    ]

    for i, t in enumerate(transcriptions):
        if i > 0:
            lines += ["", "---", "", f"*- Segmento {i+1} de {total} -*", ""]
        lines.append(str(t) if t is not None else "[Sin texto]")

    lines += ["", "---", "", "*Generado con Transcriptor CLI*"]

    out_path.write_text("\n".join(lines), encoding="utf-8")

    if errors:
        log(f"Completado con {len(errors)} error(es).")
    else:
        log("Transcripcion completada sin errores.")
    log(f"Archivo: {out_path.name}")
    return out_path


# =============================================================
#  MAIN
# =============================================================
def main():
    print("\n" + "="*60)
    print("  TRANSCRIPTOR CLI - Script de emergencia (Gemini & Groq)")
    print("="*60 + "\n")

    audio_path = pick_audio()
    size_mb    = audio_path.stat().st_size / 1024**2
    est_dur    = fmt_dur(get_audio_duration(audio_path))
    print(f"\nAudio: {audio_path.name}")
    print(f"Tamano: {size_mb:.1f} MB  |  Duracion estimada: {est_dur}\n")

    model = pick_model()

    try:
        if model == "gemini-3.5-transcribe":
            chunk_str = input(f"\nChunk size en minutos? (Enter = [25]): ").strip()
            chunk_min = int(chunk_str) if chunk_str.isdigit() and int(chunk_str) > 0 else 25
            out_path = transcribe_gemini_interactions(audio_path, chunk_min)
        elif model == "auto":
            chunk_str = input(f"\nChunk size en minutos? (Enter = [25]): ").strip()
            chunk_min = int(chunk_str) if chunk_str.isdigit() and int(chunk_str) > 0 else 25
            try:
                log("Intentando con Gemini 3.5 Transcribe...")
                out_path = transcribe_gemini_interactions(audio_path, chunk_min)
            except Exception as e:
                try:
                    log(f"Gemini 3.5 sin cuota ({e}). Probando Gemini 3.7 Flash...")
                    time.sleep(2)
                    out_path = transcribe_gemini(audio_path, "gemini-3.7-flash", chunk_min)
                except Exception as e2:
                    log(f"Gemini 3.7 sin cuota ({e2}). Conectando con Gemini 3.5 Flash Lite...")
                    time.sleep(2)
                    out_path = transcribe_gemini(audio_path, "gemini-3.5-flash-lite", chunk_min)
        else:
            chunk_str = input(f"\nChunk size en minutos? (Enter = [25]): ").strip()
            chunk_min = int(chunk_str) if chunk_str.isdigit() and int(chunk_str) > 0 else 25
            out_path = transcribe_gemini(audio_path, model, chunk_min)

        print(f"\n{'='*60}")
        print(f"LISTO: {out_path.name}")
        print(f"Ubicacion: {out_path}")
        print(f"{'='*60}")
        try:
            os.startfile(str(out_path))
        except Exception:
            pass
    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario.")
    except Exception as e:
        print(f"\nERROR fatal: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
