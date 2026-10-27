"""
╔══════════════════════════════════════════════════════════════════╗
║  KRYPT v3.4 — Transcriptor Inteligente de Reuniones y Audio      ║
║  Captura audio del sistema + micrófono → Transcribe con Gemini   ║
║  Creado por Cristian Novoa · DMT Agencia                         ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import json
import time
import wave
import shutil
import threading
import subprocess
from pathlib import Path
from datetime import datetime

# PySide6 para la UI moderna
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QFrame, QScrollArea,
    QInputDialog, QMessageBox, QSizePolicy, QToolTip, QComboBox,
    QFileDialog, QDialog, QLineEdit
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QObject, QThread, QSize, QUrl
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QRadialGradient, QPen, QBrush, QCursor,
    QIcon, QDesktopServices, QPixmap
)

# ═════════════════════════════════════════════════════════════════
#  APPLICATION IDENTITY & PATHS
# ═════════════════════════════════════════════════════════════════
APP_NAME = "Krypt"
APP_VERSION = "3.4"
APP_AUTHOR = "Cristian Novoa · DMT Agencia"

# Directorio base del aplicativo (soporta modo script y PyInstaller frozen)
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
    BIN_DIR = Path(sys.executable).parent / "bin"
    if not BIN_DIR.exists():
        BIN_DIR = APP_DIR / "bin"
else:
    APP_DIR = Path(__file__).parent
    BIN_DIR = APP_DIR / "bin"

ASSETS_DIR = APP_DIR / "assets"
if not ASSETS_DIR.exists():
    ASSETS_DIR = Path(__file__).parent / "assets"

ICON_PATH = ASSETS_DIR / "icon" / "krypt.ico"
if not ICON_PATH.exists():
    ICON_PATH = Path(__file__).parent / "assets" / "icon" / "krypt.ico"

# Almacenamiento seguro en Documentos/Krypt para evitar errores de permisos en C:\Program Files
DOCUMENTS_DIR = Path.home() / "Documents"
if not DOCUMENTS_DIR.exists():
    DOCUMENTS_DIR = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Documents"

DATA_DIR = DOCUMENTS_DIR / "Krypt"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RECORDINGS_DIR = DATA_DIR / "grabaciones"
TRANSCRIPTIONS_DIR = DATA_DIR / "transcripciones"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
TRANSCRIPTIONS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "recordings.json"
CONFIG_PATH = DATA_DIR / "config.json"
SETTINGS_PATH = DATA_DIR / "settings.json"

# ═════════════════════════════════════════════════════════════════
#  MODELOS DE GEMINI DISPONIBLES
# ═════════════════════════════════════════════════════════════════
GEMINI_MODELS = [
    # (Display name, API model ID, description tooltip)
    ("Gemini 3.5 Transcribe", "gemini-3.5-transcribe",   "🎙️ Audio nativo · Diarización acústica de hablantes, marcas de tiempo exactas (Default)."),
    ("Auto-Seleccionar",      "auto",                    "🔄 Recomendado · Usa Gemini 3.5 Transcribe con fallback a Gemini 3.7 y 3.5 Flash Lite."),
    ("Gemini 3.7 Flash",      "gemini-3.7-flash",        "⭐ Audio: $0.75/Mtok · El más capaz e inteligente de los Flash (Nuevo)."),
    ("Gemini 3.6 Flash",      "gemini-3.6-flash",        "⚡ Audio: $1.50/Mtok · Modelo anterior."),
    ("Gemini 3.5 Flash Lite", "gemini-3.5-flash-lite",   "🐢 Audio: $0.30/Mtok · Excelente velocidad y bajo costo."),
    ("Gemini 3.5 Flash",      "gemini-3.5-flash",        "⚡ Audio: $1.50/Mtok · Modelo legacy."),
    ("Gemini 3 Flash Preview","gemini-3-flash-preview",  "⚡ Audio: Más cuota."),
    ("Gemini 3.1 Flash Lite", "gemini-3.1-flash-lite",   "🐢 Audio: Emergencia / alta cuota."),
    ("Gemini 3.1 Pro Preview","gemini-3.1-pro-preview",  "🧠 Audio: costoso · Máxima precisión, cuota baja."),
]
GEMINI_MODEL_DEFAULT = "gemini-3.5-transcribe"
CHUNK_DURATION_SECONDS = 25 * 60  # 25 min chunks (óptimo y seguro con gemini-3.5-transcribe)

# ── Lazy-loaded modules (para arranque ultrarrápido en ~1.5 segundos) ──
_np = None        # numpy
_pyaudio = None   # pyaudiowpatch
_genai = None     # google.genai
_genai_types = None  # google.genai.types

def _ensure_numpy():
    global _np
    if _np is None:
        import numpy as np
        _np = np
    return _np

def _ensure_pyaudio():
    global _pyaudio
    if _pyaudio is None:
        import pyaudiowpatch as pyaudio
        _pyaudio = pyaudio
    return _pyaudio

def _ensure_genai():
    global _genai, _genai_types
    if _genai is None:
        from google import genai
        from google.genai import types
        _genai = genai
        _genai_types = types
    return _genai, _genai_types

# ═════════════════════════════════════════════════════════════════
#  CONFIG MANAGER (Google Gemini API Key & Persistencia)
# ═════════════════════════════════════════════════════════════════
class ConfigManager:
    @staticmethod
    def load() -> dict:
        cfg = {"gemini_api_key": "", "selected_model": GEMINI_MODEL_DEFAULT}
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                cfg.update(data)
            except Exception:
                pass
        elif SETTINGS_PATH.exists():
            try:
                data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                cfg.update(data)
            except Exception:
                pass

        if not cfg.get("gemini_api_key"):
            env_key = os.environ.get("GEMINI_API_KEY", "").strip()
            cfg["gemini_api_key"] = env_key if env_key else ""
        return cfg

    @staticmethod
    def save(cfg: dict):
        try:
            CONFIG_PATH.write_text(
                json.dumps(cfg, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            # Mantener sincronizado settings.json por retrocompatibilidad
            SETTINGS_PATH.write_text(
                json.dumps(cfg, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"Error guardando configuración: {e}")

    @staticmethod
    def get_api_key() -> str:
        cfg = ConfigManager.load()
        return cfg.get("gemini_api_key", "").strip()

    @staticmethod
    def set_api_key(key: str):
        cfg = ConfigManager.load()
        cfg["gemini_api_key"] = key.strip()
        ConfigManager.save(cfg)

    @staticmethod
    def validate_api_key(key: str) -> tuple[bool, str]:
        k = key.strip()
        if not k:
            return False, "La clave no puede estar vacía."
        try:
            genai, _ = _ensure_genai()
            client = genai.Client(api_key=k)
            pager = client.models.list(config={"page_size": 2})
            for _ in pager:
                break
            return True, "API Key válida y lista para transcribir."
        except Exception as e:
            err = str(e)
            if "API_KEY_INVALID" in err or "400" in err:
                return False, "API Key inválida. Verifica en Google AI Studio."
            elif "403" in err:
                return False, "Permiso denegado para esta API Key."
            return False, f"Error de conexión: {err[:120]}"

def _migrate_legacy_data():
    """Migra datos de desarrollo previos a Documentos/Krypt si existen."""
    try:
        legacy_dir = Path(__file__).parent / "grabaciones"
        legacy_db = legacy_dir / "recordings.json"
        if legacy_db.exists() and not DB_PATH.exists():
            shutil.copy2(str(legacy_db), str(DB_PATH))
            for f in legacy_dir.glob("*.wav"):
                dest = RECORDINGS_DIR / f.name
                if not dest.exists():
                    shutil.copy2(str(f), str(dest))
            for f in legacy_dir.glob("*.mp3"):
                dest = RECORDINGS_DIR / f.name
                if not dest.exists():
                    shutil.copy2(str(f), str(dest))
    except Exception:
        pass

def load_settings() -> dict:
    return ConfigManager.load()

def save_settings(settings: dict):
    ConfigManager.save(settings)

# ═════════════════════════════════════════════════════════════════
#  AUDIO PROCESSING & FFMPEG HELPERS (Autónomo en cualquier PC)
# ═════════════════════════════════════════════════════════════════
_SUBPROCESS_FLAGS = 0
if sys.platform == "win32":
    _SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW

def get_ffmpeg_bin() -> str:
    local_bin = BIN_DIR / "ffmpeg.exe"
    if local_bin.exists():
        return str(local_bin)
    exe_bin = Path(sys.executable).parent / "ffmpeg.exe"
    if exe_bin.exists():
        return str(exe_bin)
    app_bin = APP_DIR / "ffmpeg.exe"
    if app_bin.exists():
        return str(app_bin)
    sys_path = shutil.which("ffmpeg")
    if sys_path:
        return sys_path
    return "ffmpeg"

def get_ffprobe_bin() -> str:
    local_bin = BIN_DIR / "ffprobe.exe"
    if local_bin.exists():
        return str(local_bin)
    exe_bin = Path(sys.executable).parent / "ffprobe.exe"
    if exe_bin.exists():
        return str(exe_bin)
    app_bin = APP_DIR / "ffprobe.exe"
    if app_bin.exists():
        return str(app_bin)
    sys_path = shutil.which("ffprobe")
    if sys_path:
        return sys_path
    return "ffprobe"

def get_audio_duration(audio_path: Path) -> float:
    try:
        cmd = [
            get_ffprobe_bin(), "-v", "error", "-show_entries", "format=duration",
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
        cmd = [
            get_ffmpeg_bin(), "-y", "-i", str(wav_path),
            "-codec:a", "libmp3lame", "-b:a", "48k", "-ac", "1",
            str(mp3_path)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=True, creationflags=_SUBPROCESS_FLAGS)
        return mp3_path
    except Exception:
        return wav_path

def split_audio_ffmpeg(input_path: Path, chunk_sec: float, total_sec: float) -> list[Path]:
    chunks = []
    if total_sec <= chunk_sec + 10:
        return [input_path]
        
    import tempfile
    import math
    tmp_dir = Path(tempfile.mkdtemp(prefix="krypt_split_"))
    
    num_chunks = math.ceil(total_sec / chunk_sec)
    for i in range(num_chunks):
        start_sec = i * chunk_sec
        output_chunk = tmp_dir / f"chunk_{i:02d}{input_path.suffix}"
        cmd = [
            get_ffmpeg_bin(), "-y",
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


# Constantes de audio - se resuelven lazy cuando se necesiten
SAMPLE_WIDTH = 2  # 16-bit

MAX_RETRIES = 3
RETRY_DELAYS = [20, 45, 90]  # segundos entre reintentos (igual que CLI, más conservador)

MONTHS_ES = ["ene", "feb", "mar", "abr", "may", "jun",
             "jul", "ago", "sep", "oct", "nov", "dic"]
MONTHS_ES_FULL = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                  "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# ═════════════════════════════════════════════════════════════════
#  COLORS
# ═════════════════════════════════════════════════════════════════
C = {
    "bg":           "#0a0a0f",
    "bg2":          "#12121a",
    "card":         "#1a1a2e",
    "card_hover":   "#22223a",
    "card_border":  "#2a2a40",
    "card_border_h":"#3a3a55",
    "purple":       "#6c5ce7",
    "purple_light": "#a29bfe",
    "red":          "#ff6b6b",
    "red_dark":     "#ee5a5a",
    "green":        "#2ed573",
    "green_dark":   "#27ae60",
    "amber":        "#ffa502",
    "cyan":         "#00d2d3",
    "text":         "#e8e8f0",
    "text2":        "#8888a8",
    "text3":        "#555570",
    "border":       "#2a2a40",
    "rec_pulse":    "#ff4757",
}


# ═════════════════════════════════════════════════════════════════
#  HELPERS
# ═════════════════════════════════════════════════════════════════
def fmt_duration(sec: float) -> str:
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_size(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 ** 2:
        return f"{b / 1024:.0f} KB"
    return f"{b / 1024**2:.1f} MB"


def fmt_date(iso: str) -> str:
    dt = datetime.fromisoformat(iso)
    return f"{dt.day} {MONTHS_ES[dt.month - 1]} {dt.year}, {dt.hour:02d}:{dt.minute:02d}"


def make_btn(text, tooltip="", obj_name="", size=None):
    b = QPushButton(text)
    if tooltip:
        b.setToolTip(tooltip)
    if obj_name:
        b.setObjectName(obj_name)
    if size:
        b.setFixedSize(*size)
    b.setCursor(QCursor(Qt.PointingHandCursor))
    return b


# ═════════════════════════════════════════════════════════════════
#  RECORDINGS DATABASE (JSON)
# ═════════════════════════════════════════════════════════════════
class RecordingsDB:
    """Simple JSON-backed database for recording metadata."""

    def __init__(self):
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        self.records: list[dict] = []
        self._load()

    def _load(self):
        if DB_PATH.exists():
            try:
                self.records = json.loads(DB_PATH.read_text(encoding="utf-8"))
            except Exception:
                # Archivo dañado: se aparta en vez de sobrescribirlo con una lista vacía
                try:
                    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    DB_PATH.replace(DB_PATH.with_name(f"recordings.danado-{stamp}.json"))
                except Exception:
                    pass
                self.records = []
        else:
            self.records = []

    def _save(self):
        # Escritura atómica: un corte de luz a mitad de escritura no deja el JSON roto
        tmp = DB_PATH.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self.records, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(tmp, DB_PATH)

    def add(self, rec: dict):
        self.records.insert(0, rec)
        self._save()

    def update(self, rec_id: str, **kw):
        for r in self.records:
            if r["id"] == rec_id:
                r.update(kw)
                break
        self._save()

    def delete(self, rec_id: str):
        self.records = [r for r in self.records if r["id"] != rec_id]
        self._save()

    def get(self, rec_id: str) -> dict | None:
        return next((r for r in self.records if r["id"] == rec_id), None)

    def all(self) -> list[dict]:
        return self.records


# ═════════════════════════════════════════════════════════════════
#  AUDIO RECORDER — Optimized: streams to disk, ~5MB RAM constant
# ═════════════════════════════════════════════════════════════════
MIX_CHUNK_SECONDS = 10  # Process audio in 10-second chunks during mixing (fallback numpy)
LOOPBACK_GAP_FILL_SECONDS = 0.5  # Huecos del audio del sistema mayores a esto se rellenan con silencio


class AudioRecorder:
    """
    Records system audio (WASAPI loopback) + microphone.
    Audio is streamed directly to temp files on disk to avoid RAM
    accumulation. Mixing is done post-recording (FFmpeg, o numpy por bloques).

    Sincronía: WASAPI loopback NO entrega datos mientras nada suena en el PC.
    Para que las dos pistas queden alineadas en el tiempo:
      1. Se reproduce silencio inaudible en la salida mientras se graba, así
         Windows entrega el audio del sistema de forma continua.
      2. Red de seguridad: si aun así hay un hueco, se rellena con silencio
         según el reloj real (descontando las pausas).
    """

    def __init__(self):
        self.is_recording = False
        self.is_paused = False
        self._pa = None
        self._loopback_stream = None
        self._mic_stream = None
        self._silence_stream = None
        self._loopback_info = None
        self._mic_info = None
        self._target_rate = 44100
        self._thread_loopback = None
        self._thread_mic = None
        self._loopback_rate = 44100
        self._loopback_channels = 2
        self._mic_rate = 44100
        self._mic_channels = 1
        # Pausas (reloj monotónico) para el relleno de huecos
        self._paused_total = 0.0
        self._pause_began = None
        # File handles for disk streaming
        self._lb_fh = None
        self._mc_fh = None
        self._lb_temp_path = None
        self._mc_temp_path = None

    def _find_loopback(self, pa):
        """Devuelve (dispositivo loopback, dispositivo de salida predeterminado)."""
        pyaudio = _ensure_pyaudio()
        wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        out = pa.get_device_info_by_index(wasapi["defaultOutputDevice"])
        if out.get("isLoopbackDevice"):
            return out, out
        for dev in pa.get_loopback_device_info_generator():
            if out["name"] in dev["name"]:
                return dev, out
        raise RuntimeError(
            "No se encontró dispositivo de loopback WASAPI.\n"
            "Conecta altavoces o auriculares."
        )

    def _find_mic(self, pa):
        pyaudio = _ensure_pyaudio()
        wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        return pa.get_device_info_by_index(wasapi["defaultInputDevice"])

    def _start_silence(self, out):
        """Reproduce silencio en la salida para que el loopback no se detenga."""
        pyaudio = _ensure_pyaudio()
        if out.get("isLoopbackDevice") or int(out.get("maxOutputChannels", 0)) < 1:
            return
        channels = min(int(out["maxOutputChannels"]), 2)
        frame_bytes = channels * SAMPLE_WIDTH

        def _callback(in_data, frame_count, time_info, status):
            return (bytes(frame_count * frame_bytes), pyaudio.paContinue)

        try:
            self._silence_stream = self._pa.open(
                format=pyaudio.paInt16, channels=channels,
                rate=int(out["defaultSampleRate"]), output=True,
                output_device_index=out["index"], stream_callback=_callback,
            )
            self._silence_stream.start_stream()
        except Exception:
            self._silence_stream = None  # el relleno de huecos sigue cubriendo

    def _paused_seconds(self) -> float:
        extra = time.monotonic() - self._pause_began if self._pause_began else 0.0
        return self._paused_total + extra

    def _record_to_disk(self, stream, fh, chunk, rate=None, frame_bytes=None):
        """Record thread: reads from stream, writes raw PCM to disk.
        Con rate/frame_bytes (loopback) rellena con silencio los huecos."""
        write_count = 0
        written_frames = 0
        t0 = time.monotonic()
        while self.is_recording:
            try:
                data = stream.read(chunk, exception_on_overflow=False)
            except Exception:
                if not self.is_recording:
                    break
                time.sleep(0.05)  # dispositivo caído: no consumir 100% de CPU
                continue
            if self.is_paused:
                continue
            if rate:
                n = len(data) // frame_bytes
                expected = int((time.monotonic() - t0 - self._paused_seconds()) * rate)
                gap = expected - (written_frames + n)
                if gap > rate * LOOPBACK_GAP_FILL_SECONDS:
                    fh.write(bytes(gap * frame_bytes))
                    written_frames += gap
                written_frames += n
            fh.write(data)
            write_count += 1
            # Flush to disk every ~2 seconds for crash safety
            if write_count % 86 == 0:  # ~86 reads/sec at 44100/1024
                fh.flush()

    def start(self):
        pyaudio = _ensure_pyaudio()
        self._pa = pyaudio.PyAudio()
        self.is_paused = False
        self._paused_total = 0.0
        self._pause_began = None
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

        # Create temp files for raw PCM (streamed to disk, not RAM)
        # Se usa el directorio TEMP del sistema para evitar interferencias
        # con sincronizadores de nube y reducir presión de I/O en el disco del proyecto
        import tempfile
        _tmp = Path(tempfile.gettempdir())
        self._lb_temp_path = _tmp / ".transcriptor_loopback.raw"
        self._mc_temp_path = _tmp / ".transcriptor_mic.raw"
        self._lb_fh = open(self._lb_temp_path, "wb")

        # Loopback
        self._loopback_info, out_dev = self._find_loopback(self._pa)
        lb = self._loopback_info
        self._loopback_rate = int(lb["defaultSampleRate"])
        self._loopback_channels = lb["maxInputChannels"]

        AUDIO_FORMAT = pyaudio.paInt16
        self._loopback_stream = self._pa.open(
            format=AUDIO_FORMAT, channels=self._loopback_channels,
            rate=self._loopback_rate, input=True,
            input_device_index=lb["index"], frames_per_buffer=1024,
        )

        # Mic (optional)
        self._mc_fh = None
        try:
            self._mic_info = self._find_mic(self._pa)
            mc = self._mic_info
            self._mic_rate = int(mc["defaultSampleRate"])
            self._mic_channels = min(mc["maxInputChannels"], 2)
            self._mic_stream = self._pa.open(
                format=AUDIO_FORMAT, channels=self._mic_channels,
                rate=self._mic_rate, input=True,
                input_device_index=mc["index"], frames_per_buffer=1024,
            )
            self._mc_fh = open(self._mc_temp_path, "wb")
        except Exception:
            self._mic_info = None
            self._mic_stream = None

        self._start_silence(out_dev)
        self.is_recording = True

        self._thread_loopback = threading.Thread(
            target=self._record_to_disk,
            args=(self._loopback_stream, self._lb_fh, 1024,
                  self._loopback_rate, self._loopback_channels * SAMPLE_WIDTH),
            daemon=True,
        )
        self._thread_loopback.start()

        if self._mic_stream and self._mc_fh:
            self._thread_mic = threading.Thread(
                target=self._record_to_disk,
                args=(self._mic_stream, self._mc_fh, 1024),
                daemon=True,
            )
            self._thread_mic.start()

    def pause(self):
        if not self.is_paused:
            self._pause_began = time.monotonic()
        self.is_paused = True

    def resume(self):
        if self._pause_began:
            self._paused_total += time.monotonic() - self._pause_began
            self._pause_began = None
        self.is_paused = False

    def stop(self) -> Path:
        self.is_recording = False

        # El silencio sigue sonando hasta que los hilos terminan: así el
        # read() del loopback no se queda bloqueado esperando audio.
        for t in [self._thread_loopback, self._thread_mic]:
            if t:
                t.join(timeout=3)

        for s in [self._loopback_stream, self._mic_stream, self._silence_stream]:
            if s:
                try:
                    s.stop_stream()
                    s.close()
                except Exception:
                    pass
        self._silence_stream = None

        # Close temp file handles
        if self._lb_fh:
            self._lb_fh.close()
            self._lb_fh = None
        if self._mc_fh:
            self._mc_fh.close()
            self._mc_fh = None

        # Mix from disk files (chunked, low RAM)
        output = self._mix_from_disk()

        # Cleanup temp files
        for p in [self._lb_temp_path, self._mc_temp_path]:
            if p and p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass

        if self._pa:
            self._pa.terminate()
            self._pa = None

        return output

    def _chunk_to_mono(self, raw_bytes, channels, rate):
        """Convert a small chunk of raw PCM bytes to mono float32 at target rate."""
        np = _ensure_numpy()
        audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if channels > 1:
            rem = len(audio) % channels
            if rem:
                audio = audio[:-rem]
            audio = audio.reshape(-1, channels).mean(axis=1)
        if rate != self._target_rate and len(audio):
            # Interpolación lineal (antes se tomaba la muestra más cercana → distorsión)
            n = int(round(len(audio) / rate * self._target_rate))
            audio = np.interp(np.linspace(0, len(audio) - 1, n),
                              np.arange(len(audio)), audio).astype(np.float32)
        return audio

    def _mix_with_ffmpeg(self, has_mic: bool) -> Path | None:
        """Mezcla las pistas crudas directo a MP3 con FFmpeg (remuestreo de
        alta calidad, sin cortar la pista más larga). None si FFmpeg falla."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = RECORDINGS_DIR / f"REC_{ts}.mp3"
        cmd = [get_ffmpeg_bin(), "-y",
               "-f", "s16le", "-ar", str(self._loopback_rate),
               "-ac", str(self._loopback_channels), "-i", str(self._lb_temp_path)]
        if has_mic:
            cmd += ["-f", "s16le", "-ar", str(self._mic_rate),
                    "-ac", str(self._mic_channels), "-i", str(self._mc_temp_path),
                    "-filter_complex",
                    "[0:a]aformat=sample_rates=48000:channel_layouts=mono[a];"
                    "[1:a]aformat=sample_rates=48000:channel_layouts=mono[b];"
                    "[a][b]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95"]
        cmd += ["-ar", str(self._target_rate), "-ac", "1",
                "-codec:a", "libmp3lame", "-b:a", "48k", str(path)]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=True, creationflags=_SUBPROCESS_FLAGS)
            if path.exists() and path.stat().st_size > 0:
                return path
        except Exception:
            pass
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        return None

    def _mix_from_disk(self) -> Path:
        """Mezcla loopback + mic. Primero FFmpeg (→ MP3); si no está, numpy por
        bloques (→ WAV, RAM ~5 MB)."""
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

        has_mic = bool(self._mic_info and self._mc_temp_path and self._mc_temp_path.exists()
                       and self._mc_temp_path.stat().st_size > 0)
        has_lb = self._lb_temp_path and self._lb_temp_path.exists()

        if has_lb:
            mp3 = self._mix_with_ffmpeg(has_mic)
            if mp3:
                return mp3

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = RECORDINGS_DIR / f"REC_{ts}.wav"

        # Bytes per MIX_CHUNK_SECONDS for each source
        lb_chunk_bytes = MIX_CHUNK_SECONDS * self._loopback_rate * self._loopback_channels * SAMPLE_WIDTH
        mc_chunk_bytes = MIX_CHUNK_SECONDS * self._mic_rate * self._mic_channels * SAMPLE_WIDTH

        if not has_lb:
            # No audio at all — create 1 second of silence
            np = _ensure_numpy()
            with wave.open(str(path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(SAMPLE_WIDTH)
                wf.setframerate(self._target_rate)
                wf.writeframes(np.zeros(self._target_rate, dtype=np.int16).tobytes())
            return path

        with (
            open(self._lb_temp_path, "rb") as lb_f,
            wave.open(str(path), "wb") as out_wf,
        ):
            out_wf.setnchannels(1)
            out_wf.setsampwidth(SAMPLE_WIDTH)
            out_wf.setframerate(self._target_rate)

            mc_f = open(self._mc_temp_path, "rb") if has_mic else None

            np = _ensure_numpy()
            try:
                while True:
                    lb_raw = lb_f.read(lb_chunk_bytes)
                    mc_raw = mc_f.read(mc_chunk_bytes) if mc_f else b""
                    if not lb_raw and not mc_raw:
                        break

                    # Ninguna pista se corta: la más corta se completa con silencio
                    lb_mono = self._chunk_to_mono(lb_raw, self._loopback_channels, self._loopback_rate)
                    mc_mono = self._chunk_to_mono(mc_raw, self._mic_channels, self._mic_rate)
                    n = max(len(lb_mono), len(mc_mono))
                    mixed = np.zeros(n, dtype=np.float32)
                    mixed[:len(lb_mono)] += lb_mono * 0.7
                    mixed[:len(mc_mono)] += mc_mono * 0.5
                    mixed = np.clip(mixed, -1.0, 1.0)

                    # Write chunk to output WAV
                    pcm = (mixed * 32767).astype(np.int16)
                    out_wf.writeframes(pcm.tobytes())
            finally:
                if mc_f:
                    mc_f.close()

        return path


def finalize_recording(recorder: AudioRecorder) -> Path:
    """Detiene la grabación, mezcla y deja el audio final en MP3 (si se puede)."""
    path = recorder.stop()
    if path.suffix.lower() == ".wav":
        mp3 = compress_to_mp3(path)
        if mp3 != path and mp3.exists():
            try:
                path.unlink()
            except Exception:
                pass
            path = mp3
    return path


class SaveRecordingWorker(QThread):
    """Mezcla y compresión fuera del hilo de la UI (en reuniones largas la
    ventana quedaba 'No responde' mientras se guardaba)."""
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, recorder: AudioRecorder):
        super().__init__()
        self.recorder = recorder
        self.result: Path | None = None

    def run(self):
        try:
            self.result = finalize_recording(self.recorder)
            self.done.emit(str(self.result))
        except Exception as e:
            self.failed.emit(str(e))


# ═════════════════════════════════════════════════════════════════
#  TRANSCRIPTION WORKER (with retry)
# ═════════════════════════════════════════════════════════════════
class TranscriptionSignals(QObject):
    progress = Signal(str, int)        # message, percentage
    finished = Signal(str, str)        # rec_id, transcript_path
    error = Signal(str, str)           # rec_id, error_message


class TranscriptionWorker(QThread):

    def __init__(self, rec_id: str, audio_path: Path, rec_name: str,
                 model: str = GEMINI_MODEL_DEFAULT):
        super().__init__()
        self.rec_id = rec_id
        self.audio_path = audio_path
        self.rec_name = rec_name
        self.model = model
        self.signals = TranscriptionSignals()

    def run(self):
        try:
            if self.model == "auto":
                try:
                    # Intenta Gemini 3.5 Transcribe primero (modelo nativo por defecto)
                    self.model = "gemini-3.5-transcribe"
                    self.signals.progress.emit("Intentando con Gemini 3.5 Transcribe (Audio Nativo)...", 5)
                    path = self._transcribe()
                except Exception as e:
                    try:
                        self.model = "gemini-3.7-flash"
                        self.signals.progress.emit("Gemini 3.5 sin cuota. Conectando con Gemini 3.7 Flash...", -1)
                        time.sleep(2)
                        path = self._transcribe()
                    except Exception as e2:
                        self.model = "gemini-3.5-flash-lite"
                        self.signals.progress.emit("Gemini 3.7 sin cuota. Conectando con Gemini 3.5 Flash Lite...", -1)
                        time.sleep(2)
                        path = self._transcribe()
            else:
                path = self._transcribe()
            self.signals.finished.emit(self.rec_id, str(path))
        except Exception as e:
            self.signals.error.emit(self.rec_id, self._clean_error(str(e)))

    # ── Error cleanup ────────────────────────────────────────
    def _clean_error(self, msg: str) -> str:
        if "RESOURCE_EXHAUSTED" in msg or ("429" in msg and "limit: 0" in msg):
            return (
                f"Cuota agotada para '{self.model}'.\n"
                "Cambia el modelo en el selector de arriba y reintenta.\n"
                "Orden recomendado: Gemini 3.5 Transcribe → 3.7 Flash → 3.5 Flash Lite."
            )
        if "429" in msg:
            return "Demasiadas solicitudes a Gemini. Espera unos minutos y reintenta."
        if "API_KEY" in msg.upper() or "401" in msg:
            return "API key de Gemini no configurada o inválida. Revísala en Configuración (⚙️)."
        if "503" in msg or "UNAVAILABLE" in msg:
            return (
                f"Servidor sobrecargado para '{self.model}' tras varios intentos.\n"
                "Prueba con otro modelo (Gemini 3.7 Flash o 3.5 Flash Lite) o espera unos minutos."
            )
        return msg[:300] if len(msg) > 300 else msg

    # ── Chunk splitting ──────────────────────────────────────
    def _split_if_needed(self) -> list[Path]:
        duration = get_audio_duration(self.audio_path)
        # Hasta 28 minutos se procesa en una sola llamada sin dividir
        if duration <= 28 * 60:
            return [self.audio_path]
        return split_audio_ffmpeg(self.audio_path, CHUNK_DURATION_SECONDS, duration)

    # ── Format interaction (Gemini 3.5 Transcribe) ───────────
    def _format_interaction(self, interaction, offset_seconds: float = 0.0) -> str:
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

    # ── Gemini 3.5 Transcribe Interactions call with retry ───
    def _call_gemini_interactions(self, client, uploaded, offset_seconds: float) -> str:
        last_err = None
        for attempt in range(MAX_RETRIES + 1):
            try:
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
                formatted = self._format_interaction(interaction, offset_seconds)
                return formatted if formatted else "[Sin texto en este segmento]"
            except Exception as e:
                last_err = e
                msg = str(e)
                is_quota = "RESOURCE_EXHAUSTED" in msg or ("429" in msg and "limit: 0" in msg)
                retryable = ("503" in msg or "UNAVAILABLE" in msg or "500" in msg or
                             ("429" in msg and not is_quota))
                if retryable and attempt < MAX_RETRIES:
                    wait = RETRY_DELAYS[attempt]
                    self.signals.progress.emit(
                        f"Servidor ocupado. Reintentando en {wait}s… "
                        f"(intento {attempt + 2}/{MAX_RETRIES + 1})",
                        -1,
                    )
                    time.sleep(wait)
                else:
                    raise
        raise last_err

    # ── Gemini Generative LLM call with retry ────────────────
    def _call_gemini(self, client, contents) -> str:
        """Llama a Gemini con retry y siempre devuelve un str (nunca None)."""
        last_err = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                _, types = _ensure_genai()
                resp = client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=65535,
                    ),
                )
                # Extraer texto de forma segura
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

                # Verificar finish_reason para diagnóstico / advertencias
                try:
                    reason = resp.candidates[0].finish_reason
                    reason_name = reason.name if reason and hasattr(reason, 'name') else str(reason)
                    if reason_name == "MAX_TOKENS":
                        warning = (
                            "\n\n> ⚠️ **ADVERTENCIA:** La respuesta fue cortada por límite "
                            "de tokens. El segmento es muy largo."
                        )
                        text = (text or "") + warning
                    elif "SAFETY" in reason_name and not text:
                        text = "[Segmento bloqueado por filtros de seguridad de Gemini]"
                except Exception:
                    pass

                # Garantizar que siempre devolvemos un str
                return text if text else "[Sin texto en este segmento]"

            except Exception as e:
                last_err = e
                msg = str(e)
                is_quota = "RESOURCE_EXHAUSTED" in msg or ("429" in msg and "limit: 0" in msg)
                retryable = ("503" in msg or "UNAVAILABLE" in msg or "500" in msg or
                             ("429" in msg and not is_quota))
                if retryable and attempt < MAX_RETRIES:
                    wait = RETRY_DELAYS[attempt]
                    self.signals.progress.emit(
                        f"Servidor ocupado. Reintentando en {wait}s… "
                        f"(intento {attempt + 2}/{MAX_RETRIES + 1})",
                        -1,
                    )
                    time.sleep(wait)
                else:
                    raise
        raise last_err  # should never reach here

    # ── Main transcription flow ──────────────────────────────
    def _transcribe(self) -> Path:
        self.signals.progress.emit("Preparando audio…", 5)

        chunks = self._split_if_needed()
        total = len(chunks)
        self.signals.progress.emit(f"Audio: {total} parte(s).", 10)

        genai, _ = _ensure_genai()
        api_key = ConfigManager.get_api_key()
        if not api_key:
            raise ValueError("No se ha configurado la API Key de Google Gemini. Ve a Configuración (⚙️) para agregarla.")
        client = genai.Client(api_key=api_key)
        transcriptions = []

        try:
            for i, chunk in enumerate(chunks):
                num = i + 1
                base = 10 + int(i / total * 80)

                # Upload
                self.signals.progress.emit(f"Subiendo audio ({num}/{total})…", base)
                uploaded = client.files.upload(file=str(chunk))
                try:
                    # Wait for ACTIVE
                    self.signals.progress.emit(f"Procesando ({num}/{total})…", base + 5)
                    for _ in range(60):
                        info = client.files.get(name=uploaded.name)
                        state = info.state.name if info.state else ""
                        if state == "ACTIVE":
                            break
                        if state == "FAILED":
                            raise RuntimeError("Google no pudo procesar el archivo de audio (estado FAILED).")
                        time.sleep(2)

                    # Transcribe
                    self.signals.progress.emit(
                        f"Transcribiendo ({num}/{total})… Puede tomar minutos.",
                        base + int(40 / total),
                    )
                    # Calculate actual offset in seconds and minutes from chunk position
                    offset_seconds = i * CHUNK_DURATION_SECONDS
                    offset_minutes = offset_seconds // 60

                    if self.model == "gemini-3.5-transcribe":
                        response_text = self._call_gemini_interactions(client, uploaded, float(offset_seconds))
                    else:
                        prompt = self._prompt(offset_minutes, num, total)
                        response_text = self._call_gemini(client, [prompt, uploaded])

                    transcriptions.append(response_text)
                finally:
                    # El audio no se queda en los servidores de Google aunque falle
                    try:
                        client.files.delete(name=uploaded.name)
                    except Exception:
                        pass

                # Small pause between chunks to avoid rate limits
                if num < total:
                    time.sleep(3)
        finally:
            # Partes temporales (y su carpeta) se borran pase lo que pase
            temp_chunks = [c for c in chunks if c != self.audio_path]
            for c in temp_chunks:
                try:
                    c.unlink(missing_ok=True)
                except Exception:
                    pass
            if temp_chunks:
                shutil.rmtree(temp_chunks[0].parent, ignore_errors=True)

        # Save markdown
        self.signals.progress.emit("Generando Markdown…", 92)
        out = self._save_md(transcriptions)
        self.signals.progress.emit("¡Completado!", 100)
        return out

    # ── Prompt ───────────────────────────────────────────────
    def _prompt(self, offset_min: int, chunk_num: int, total: int) -> str:
        offset_note = ""
        if total > 1:
            # Ejemplo: 5 min 30 s dentro del segmento (antes el minuto podía pasar de 59)
            h, m = divmod(offset_min + 5, 60)
            offset_note = (
                f"\n\nEste es el segmento {chunk_num} de {total}. "
                f"Los timestamps del audio empiezan en 0:00 pero debes mostrarlos "
                f"sumando {offset_min} minutos al tiempo real del audio. "
                f"Ejemplo: si el audio marca 00:05:30, escribe [{h:02d}:{m:02d}:30]. "
                f"El segmento empieza en el minuto {offset_min} de la reunión total."
            )
        return f"""Eres un transcriptor profesional de reuniones. Tu única tarea es 
transcribir LITERALMENTE todo lo que se dice en este audio, palabra por palabra.

REGLAS ABSOLUTAS — NO las ignores bajo ninguna circunstancia:
1. TRANSCRIBE TODO: Cada palabra, cada frase, cada intervención. 
   PROHIBIDO resumir, condensar o saltarte partes del audio.
2. NUNCA inventes contenido: Si no entiendes algo, escribe [inaudible].
   JAMÁS rellenes con texto que no esté en el audio.
3. IDIOMA: Transcribe en el idioma que se habla (principalmente español).
4. HABLANTES: Identifica cada hablante. Si detectas su nombre úsalo,
   si no: [Hablante 1], [Hablante 2], etc. Sé consistente.
5. TIMESTAMPS: Marca cada cambio de hablante con [HH:MM:SS].
6. FORMATO por intervención:
   **[HH:MM:SS] [Nombre]:** Texto transcrito...
7. COMPLETITUD: El audio puede durar 30 minutos o más. 
   Debes transcribir DESDE EL INICIO HASTA EL FINAL sin omitir nada.
8. Partes inaudibles o incomprensibles: [inaudible]
   Sonidos relevantes: [risas], [aplausos], [interrupción]
{offset_note}

Comienza la transcripción ahora. No escribas introducciones ni explicaciones. 
Solo la transcripción:"""

    # ── Save Markdown ────────────────────────────────────────
    def _save_md(self, parts: list[str]) -> Path:
        TRANSCRIPTIONS_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        ts = now.strftime("%Y-%m-%d_%H-%M-%S")
        # %B depende del idioma de Windows (salía "October"); se arma en español
        dt_display = f"{now.day} de {MONTHS_ES_FULL[now.month - 1]} de {now.year}, {now:%H:%M}"
        fname = f"Transcripcion_{ts}.md"
        path = TRANSCRIPTIONS_DIR / fname

        segments = (f"{len(parts)} de {CHUNK_DURATION_SECONDS // 60} min cada uno"
                    if len(parts) > 1 else "1 (audio completo)")
        lines = [
            f"# 📝 {self.rec_name}",
            "",
            f"**Fecha:** {dt_display}",
            f"**Modelo:** {self.model}",
            f"**Segmentos:** {segments}",
            "",
            "---",
            "",
        ]
        for i, t in enumerate(parts):
            if i > 0:
                lines += ["", "---", "", f"*— Segmento {i + 1} —*", ""]
            lines.append(t)
        lines += ["", "---", "", f"*Generado con {APP_NAME} v{APP_VERSION} ({APP_AUTHOR})*"]

        path.write_text("\n".join(lines), encoding="utf-8")
        return path


# ═════════════════════════════════════════════════════════════════
#  UI: PULSING DOT
# ═════════════════════════════════════════════════════════════════
class PulsingDot(QWidget):
    def __init__(self, color=C["rec_pulse"], parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self._opacity = 1.0
        self._color = color
        self._growing = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._timer.start(50)

    def stop(self):
        self._timer.stop()
        self._opacity = 1.0
        self.update()

    def set_color(self, color):
        self._color = color
        self.update()

    def _tick(self):
        self._opacity += 0.06 if self._growing else -0.06
        if self._opacity >= 1.0:
            self._opacity = 1.0
            self._growing = False
        elif self._opacity <= 0.2:
            self._opacity = 0.2
            self._growing = True
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # Glow
        p.setOpacity(self._opacity * 0.5)
        g = QRadialGradient(7, 7, 7)
        g.setColorAt(0, QColor(self._color))
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(g))
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, 14, 14)
        # Core
        p.setOpacity(1.0)
        p.setBrush(QColor(self._color))
        p.drawEllipse(3, 3, 8, 8)
        p.end()


# ═════════════════════════════════════════════════════════════════
#  UI: RECORDING CARD
# ═════════════════════════════════════════════════════════════════
class RecordingCard(QFrame):
    """A card representing one recording in the history list."""

    transcribe_clicked = Signal(str)  # rec_id
    rename_clicked = Signal(str)      # rec_id
    delete_clicked = Signal(str)      # rec_id
    view_clicked = Signal(str)        # rec_id

    def __init__(self, rec: dict, parent=None):
        super().__init__(parent)
        self.rec = rec
        self.setObjectName("recCard")
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.setFixedHeight(72)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # ── Top row: dot + name + duration + status ──
        top = QHBoxLayout()
        top.setSpacing(8)

        # Status dot
        status = self.rec.get("status", "recorded")
        dot_colors = {
            "recorded": C["purple"],
            "transcribing": C["amber"],
            "transcribed": C["green"],
            "error": C["red"],
        }
        dot = QLabel("●")
        dot.setFixedWidth(16)
        dot.setFont(QFont("Segoe UI", 9))
        dot.setStyleSheet(f"color: {dot_colors.get(status, C['text3'])};")
        top.addWidget(dot)

        # Name
        name = QLabel(self.rec.get("name", "Sin nombre"))
        name.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        name.setStyleSheet(f"color: {C['text']};")
        name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        name.setMinimumWidth(0)
        top.addWidget(name, stretch=1)

        # Duration
        dur_sec = self.rec.get("duration_seconds", 0)
        dur = QLabel(fmt_duration(dur_sec))
        dur.setFont(QFont("Consolas", 9))
        dur.setStyleSheet(f"color: {C['text2']};")
        top.addWidget(dur)

        # Status badge
        badge_map = {
            "recorded":      ("Grabada",         C["text3"]),
            "transcribing":  ("Transcribiendo…", C["amber"]),
            "transcribed":   ("Transcrita ✓",    C["green"]),
            "error":         ("Error ✗",         C["red"]),
        }
        badge_text, badge_color = badge_map.get(status, ("", C["text3"]))
        badge = QLabel(badge_text)
        badge.setFont(QFont("Segoe UI", 8))
        badge.setStyleSheet(f"color: {badge_color};")
        top.addWidget(badge)

        layout.addLayout(top)

        # ── Bottom row: date + size + buttons ──
        bottom = QHBoxLayout()
        bottom.setSpacing(6)

        # Date + size
        created = self.rec.get("created_at", "")
        date_str = fmt_date(created) if created else ""

        audio_file = RECORDINGS_DIR / self.rec.get("audio_file", "")
        size_str = ""
        if audio_file.exists():
            size_str = f"  •  {fmt_size(audio_file.stat().st_size)}"

        meta = QLabel(f"{date_str}{size_str}")
        meta.setFont(QFont("Segoe UI", 8))
        meta.setStyleSheet(f"color: {C['text3']};")
        bottom.addWidget(meta, stretch=1)

        # Action buttons
        btn_style = f"""
            QPushButton {{
                background: transparent; color: {C['text2']};
                border: none; border-radius: 4px; font-size: 13px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background: {C['card_hover']}; color: {C['text']};
            }}
        """
        rec_id = self.rec["id"]

        if status == "transcribed":
            b = make_btn("📄", "Ver transcripción", size=(28, 24))
            b.setStyleSheet(btn_style)
            b.clicked.connect(lambda: self.view_clicked.emit(rec_id))
            bottom.addWidget(b)

        if status in ("recorded", "error"):
            label = "🔄" if status == "error" else "📤"
            tip = "Reintentar transcripción" if status == "error" else "Transcribir"
            b = make_btn(label, tip, size=(28, 24))
            b.setStyleSheet(btn_style)
            b.clicked.connect(lambda: self.transcribe_clicked.emit(rec_id))
            bottom.addWidget(b)

        if status == "transcribed":
            b = make_btn("🔄", "Re-transcribir", size=(28, 24))
            b.setStyleSheet(btn_style)
            b.clicked.connect(lambda: self.transcribe_clicked.emit(rec_id))
            bottom.addWidget(b)

        if status != "transcribing":
            b = make_btn("✏️", "Renombrar", size=(28, 24))
            b.setStyleSheet(btn_style)
            b.clicked.connect(lambda: self.rename_clicked.emit(rec_id))
            bottom.addWidget(b)

            b = make_btn("🗑", "Eliminar", size=(28, 24))
            b.setStyleSheet(btn_style)
            b.clicked.connect(lambda: self.delete_clicked.emit(rec_id))
            bottom.addWidget(b)

        layout.addLayout(bottom)


# ═════════════════════════════════════════════════════════════════
#  UI: DIALOGS (SETTINGS & API KEY SETUP)
# ═════════════════════════════════════════════════════════════════
class SettingsDialog(QDialog):
    """Ventana modal de configuración: API Key de Google Gemini y rutas."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración — Krypt")
        self.setFixedWidth(470)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        header = QLabel("⚙️ Configuración de Krypt")
        header.setFont(QFont("Segoe UI", 13, QFont.Bold))
        header.setStyleSheet("color: #f1f5f9;")
        layout.addWidget(header)

        # API Key Section
        api_box = QFrame()
        api_box.setObjectName("settingCard")
        api_layout = QVBoxLayout(api_box)
        api_layout.setContentsMargins(14, 14, 14, 14)
        api_layout.setSpacing(8)

        api_lbl = QLabel("Google Gemini API Key:")
        api_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        api_lbl.setStyleSheet("color: #94a3b8;")
        api_layout.addWidget(api_lbl)

        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setPlaceholderText("Pega tu API Key de Gemini (AIzaSy...)")
        self.key_input.setText(ConfigManager.get_api_key())
        self.key_input.setFixedHeight(34)
        self.key_input.setStyleSheet("""
            QLineEdit {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 0 10px;
                color: #f8fafc;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
            QLineEdit:focus { border: 1px solid #3b82f6; }
        """)
        key_row.addWidget(self.key_input)

        self.btn_toggle_vis = QPushButton("👁️")
        self.btn_toggle_vis.setFixedSize(34, 34)
        self.btn_toggle_vis.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_toggle_vis.setToolTip("Mostrar/Ocultar clave")
        self.btn_toggle_vis.setStyleSheet("""
            QPushButton { background: #1e293b; border: 1px solid #334155; border-radius: 6px; color: #cbd5e1; font-size: 13px; }
            QPushButton:hover { background: #334155; }
        """)
        self.btn_toggle_vis.clicked.connect(self._toggle_visibility)
        key_row.addWidget(self.btn_toggle_vis)
        api_layout.addLayout(key_row)

        test_row = QHBoxLayout()
        self.btn_test = QPushButton("⚡ Probar Conexión")
        self.btn_test.setFixedHeight(28)
        self.btn_test.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_test.setStyleSheet("""
            QPushButton { background: #1e293b; border: 1px solid #475569; border-radius: 4px; color: #93c5fd; font-weight: bold; font-size: 10px; padding: 0 12px; }
            QPushButton:hover { background: #334155; }
        """)
        self.btn_test.clicked.connect(self._test_key)
        test_row.addWidget(self.btn_test)

        test_row.addStretch()

        help_link = QLabel('<a href="https://aistudio.google.com/apikey" style="color:#60a5fa; text-decoration:none; font-size:11px;">🔑 Obtener clave gratis</a>')
        help_link.setOpenExternalLinks(True)
        test_row.addWidget(help_link)
        api_layout.addLayout(test_row)

        self.lbl_test_result = QLabel("")
        self.lbl_test_result.setWordWrap(True)
        self.lbl_test_result.setFont(QFont("Segoe UI", 9))
        self.lbl_test_result.setVisible(False)
        api_layout.addWidget(self.lbl_test_result)

        layout.addWidget(api_box)

        # Storage Section
        store_box = QFrame()
        store_box.setObjectName("settingCard")
        store_layout = QVBoxLayout(store_box)
        store_layout.setContentsMargins(14, 12, 14, 12)
        store_layout.setSpacing(6)

        store_lbl = QLabel("Carpeta de Grabaciones y Notas:")
        store_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        store_lbl.setStyleSheet("color: #94a3b8;")
        store_layout.addWidget(store_lbl)

        dir_row = QHBoxLayout()
        dir_text = QLabel(str(DATA_DIR))
        dir_text.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        dir_text.setWordWrap(True)
        dir_row.addWidget(dir_text, stretch=1)

        btn_open_dir = QPushButton("📂 Abrir")
        btn_open_dir.setFixedHeight(28)
        btn_open_dir.setCursor(QCursor(Qt.PointingHandCursor))
        btn_open_dir.setStyleSheet("""
            QPushButton { background: #1e293b; border: 1px solid #475569; border-radius: 4px; color: #cbd5e1; font-size: 10px; padding: 0 10px; }
            QPushButton:hover { background: #334155; }
        """)
        btn_open_dir.clicked.connect(lambda: os.startfile(str(DATA_DIR)))
        dir_row.addWidget(btn_open_dir)
        store_layout.addLayout(dir_row)

        layout.addWidget(store_box)

        # Credits & Info
        info_box = QLabel(f"Krypt v{APP_VERSION}  •  {APP_AUTHOR}\nDesarrollado para Windows")
        info_box.setAlignment(Qt.AlignCenter)
        info_box.setStyleSheet("color: #64748b; font-size: 10px; margin: 4px 0;")
        layout.addWidget(info_box)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setFixedSize(90, 32)
        self.btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_cancel.setStyleSheet("""
            QPushButton { background: #1e293b; border: 1px solid #334155; border-radius: 6px; color: #94a3b8; font-weight: bold; font-size: 11px; }
            QPushButton:hover { background: #334155; color: #f8fafc; }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Guardar")
        self.btn_save.setFixedSize(90, 32)
        self.btn_save.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_save.setStyleSheet("""
            QPushButton { background: #2563eb; border: none; border-radius: 6px; color: #ffffff; font-weight: bold; font-size: 11px; }
            QPushButton:hover { background: #1d4ed8; }
        """)
        self.btn_save.clicked.connect(self._save_and_close)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _toggle_visibility(self):
        if self.key_input.echoMode() == QLineEdit.Password:
            self.key_input.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_vis.setText("🙈")
        else:
            self.key_input.setEchoMode(QLineEdit.Password)
            self.btn_toggle_vis.setText("👁️")

    def _test_key(self):
        k = self.key_input.text().strip()
        if not k:
            self.lbl_test_result.setText("⚠️ Ingresa una clave antes de probar.")
            self.lbl_test_result.setStyleSheet("color: #f59e0b;")
            self.lbl_test_result.setVisible(True)
            return

        self.lbl_test_result.setText("⏳ Verificando con Google Gemini...")
        self.lbl_test_result.setStyleSheet("color: #93c5fd;")
        self.lbl_test_result.setVisible(True)
        QApplication.processEvents()

        ok, msg = ConfigManager.validate_api_key(k)
        if ok:
            self.lbl_test_result.setText("✅ " + msg)
            self.lbl_test_result.setStyleSheet("color: #22c55e;")
        else:
            self.lbl_test_result.setText("❌ " + msg)
            self.lbl_test_result.setStyleSheet("color: #ef4444;")

    def _save_and_close(self):
        k = self.key_input.text().strip()
        ConfigManager.set_api_key(k)
        self.accept()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
            }
            #settingCard {
                background-color: #141c2e;
                border: 1px solid #1e293b;
                border-radius: 10px;
            }
        """)


class ApiKeySetupDialog(QDialog):
    """Diálogo de bienvenida e introducción de API Key en el primer arranque."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bienvenido a Krypt")
        self.setFixedWidth(460)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(14)

        # Icon and title
        header_layout = QHBoxLayout()
        png_icon = ASSETS_DIR / "icon" / "krypt-48.png"
        if png_icon.exists():
            pm = QLabel()
            pm.setPixmap(QPixmap(str(png_icon)).scaled(38, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            header_layout.addWidget(pm)
        else:
            ic = QLabel("🎙️")
            ic.setFont(QFont("Segoe UI Emoji", 22))
            header_layout.addWidget(ic)

        title_vbox = QVBoxLayout()
        title = QLabel("¡Bienvenido a Krypt!")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        title.setStyleSheet("color: #f8fafc;")
        subtitle = QLabel("Transcriptor Inteligente de Reuniones y Audio")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 11px;")
        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        header_layout.addLayout(title_vbox)
        layout.addLayout(header_layout)

        desc = QLabel(
            "Para transcribir llamadas y audios con inteligencia artificial "
            "(diarización de hablantes y marcas de tiempo exactas), ingresa tu API Key de Google Gemini."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #cbd5e1; font-size: 11px; line-height: 1.4;")
        layout.addWidget(desc)

        # Link card
        step_card = QFrame()
        step_card.setObjectName("setupCard")
        sc_layout = QVBoxLayout(step_card)
        sc_layout.setContentsMargins(12, 10, 12, 10)
        sc_layout.setSpacing(4)
        step1 = QLabel("1. Obtén tu clave gratuita en:")
        step1.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold;")
        link = QLabel('<a href="https://aistudio.google.com/apikey" style="color:#60a5fa; font-weight:bold; text-decoration:none; font-size:11px;">👉 aistudio.google.com/apikey</a>')
        link.setOpenExternalLinks(True)
        sc_layout.addWidget(step1)
        sc_layout.addWidget(link)
        layout.addWidget(step_card)

        # Input
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Pega tu clave aquí (comienza con AIzaSy...)")
        self.key_input.setFixedHeight(36)
        self.key_input.setStyleSheet("""
            QLineEdit {
                background: #0f172a;
                border: 1px solid #3b82f6;
                border-radius: 6px;
                padding: 0 10px;
                color: #f8fafc;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.key_input)

        self.lbl_status = QLabel("")
        self.lbl_status.setFont(QFont("Segoe UI", 9))
        self.lbl_status.setVisible(False)
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        # Buttons
        btns = QHBoxLayout()
        self.btn_later = QPushButton("Omitir por ahora")
        self.btn_later.setFixedHeight(34)
        self.btn_later.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_later.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: #64748b; font-size: 11px; }
            QPushButton:hover { color: #94a3b8; }
        """)
        self.btn_later.clicked.connect(self.reject)
        btns.addWidget(self.btn_later)

        btns.addStretch()

        self.btn_save = QPushButton("Guardar y Continuar")
        self.btn_save.setFixedHeight(36)
        self.btn_save.setMinimumWidth(160)
        self.btn_save.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_save.setStyleSheet("""
            QPushButton { background: #2563eb; border: none; border-radius: 6px; color: #ffffff; font-weight: bold; font-size: 12px; }
            QPushButton:hover { background: #1d4ed8; }
        """)
        self.btn_save.clicked.connect(self._on_save)
        btns.addWidget(self.btn_save)

        layout.addLayout(btns)

    def _on_save(self):
        k = self.key_input.text().strip()
        if not k:
            self.lbl_status.setText("⚠️ Ingresa tu API Key o haz clic en 'Omitir por ahora'.")
            self.lbl_status.setStyleSheet("color: #f59e0b;")
            self.lbl_status.setVisible(True)
            return

        self.lbl_status.setText("⏳ Verificando API Key con Google...")
        self.lbl_status.setStyleSheet("color: #93c5fd;")
        self.lbl_status.setVisible(True)
        QApplication.processEvents()

        ok, msg = ConfigManager.validate_api_key(k)
        if ok:
            ConfigManager.set_api_key(k)
            self.accept()
        else:
            self.lbl_status.setText("❌ " + msg)
            self.lbl_status.setStyleSheet("color: #ef4444;")

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background-color: #0b0f19; }
            #setupCard { background-color: #141c2e; border: 1px solid #1e293b; border-radius: 8px; }
        """)


# ═════════════════════════════════════════════════════════════════
#  UI: MAIN WINDOW
# ═════════════════════════════════════════════════════════════════
class TranscriptorWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.db = RecordingsDB()
        self.settings = load_settings()
        self.recorder = AudioRecorder()
        self.worker: TranscriptionWorker | None = None
        self._save_worker: SaveRecordingWorker | None = None
        self._pending_duration = 0.0
        self.is_recording = False
        self.is_paused = False
        self._rec_start = 0.0
        self._paused_total = 0.0
        self._pause_start = 0.0
        self._current_transcription_id: str | None = None

        self.setWindowTitle(APP_NAME)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setFixedSize(520, 700)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos = None

        self._build_ui()
        self._apply_styles()

        # Set selected model from settings
        idx = self.model_combo.findData(self.settings.get("selected_model", GEMINI_MODEL_DEFAULT))
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)

        self._recover_stuck_transcriptions()  # Fix stuck states on startup
        self._refresh_history()

        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._update_clock)

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    # ── BUILD UI ─────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame()
        self.card.setObjectName("mainCard")
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(28, 20, 28, 20)
        cl.setSpacing(0)

        # ── Title bar ──
        tb = QHBoxLayout()
        png_icon = ASSETS_DIR / "icon" / "krypt-32.png"
        if png_icon.exists():
            ic = QLabel()
            ic.setPixmap(QPixmap(str(png_icon)).scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            ic = QLabel("🎙️")
            ic.setFont(QFont("Segoe UI Emoji", 16))

        title = QLabel(APP_NAME)
        title.setObjectName("title")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))

        self.btn_settings = make_btn("⚙️", "Configuración y API Key", obj_name="winBtn", size=(30, 30))
        self.btn_settings.clicked.connect(self._open_settings)
        self.btn_min = make_btn("─", "Minimizar", obj_name="winBtn", size=(30, 30))
        self.btn_close = make_btn("✕", "Cerrar", obj_name="closeBtn", size=(30, 30))
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_close.clicked.connect(self.close)

        tb.addWidget(ic)
        tb.addSpacing(8)
        tb.addWidget(title)
        tb.addStretch()
        tb.addWidget(self.btn_settings)
        tb.addSpacing(3)
        tb.addWidget(self.btn_min)
        tb.addSpacing(3)
        tb.addWidget(self.btn_close)
        cl.addLayout(tb)
        cl.addSpacing(20)

        # ── Timer ──
        self.time_lbl = QLabel("00:00:00")
        self.time_lbl.setObjectName("timer")
        self.time_lbl.setAlignment(Qt.AlignCenter)
        self.time_lbl.setFont(QFont("Consolas", 42, QFont.Bold))
        cl.addWidget(self.time_lbl)

        # ── Status ──
        st_row = QHBoxLayout()
        st_row.setAlignment(Qt.AlignCenter)
        self.pulse_dot = PulsingDot()
        self.pulse_dot.setVisible(False)
        self.status_lbl = QLabel("Listo para grabar")
        self.status_lbl.setObjectName("status")
        self.status_lbl.setFont(QFont("Segoe UI", 10))
        st_row.addWidget(self.pulse_dot)
        st_row.addSpacing(5)
        st_row.addWidget(self.status_lbl)
        cl.addLayout(st_row)
        cl.addSpacing(8)

        # ── Model Selector ──
        model_layout = QHBoxLayout()
        model_layout.setAlignment(Qt.AlignCenter)
        model_layout.setSpacing(8)

        model_lbl = QLabel("Modelo IA:")
        model_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        model_lbl.setStyleSheet(f"color: {C['text2']};")

        self.model_combo = QComboBox()
        self.model_combo.setObjectName("modelCombo")
        self.model_combo.setToolTip(
            "Elige el modelo de Gemini a utilizar.\n"
            "Pasa el cursor sobre cada opción para ver cuándo usarlo."
        )

        for name, model_id, desc in GEMINI_MODELS:
            self.model_combo.addItem(name, model_id)

        for idx, (name, model_id, desc) in enumerate(GEMINI_MODELS):
            self.model_combo.setItemData(idx, desc, Qt.ToolTipRole)

        model_layout.addWidget(model_lbl)
        model_layout.addWidget(self.model_combo)

        cl.addLayout(model_layout)
        cl.addSpacing(14)

        # ── Buttons: IDLE ──
        self.btn_record = make_btn("⏺  Grabar", obj_name="btnRecord")
        self.btn_record.setFixedHeight(52)
        self.btn_record.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_record.clicked.connect(self._on_record)
        cl.addWidget(self.btn_record)

        # ── Upload Audio Button ──
        self.btn_upload = make_btn("📎  Subir Audio", obj_name="btnUpload")
        self.btn_upload.setFixedHeight(36)
        self.btn_upload.setFont(QFont("Segoe UI", 10))
        self.btn_upload.setToolTip("Subir un audio externo (WhatsApp, MP3, OGG, etc.) para transcribir")
        self.btn_upload.clicked.connect(self._on_upload_audio)
        cl.addWidget(self.btn_upload)
        cl.addSpacing(6)

        # ── Buttons: RECORDING / PAUSED ──
        self.rec_btns = QWidget()
        rb = QHBoxLayout(self.rec_btns)
        rb.setContentsMargins(0, 0, 0, 0)
        rb.setSpacing(12)
        self.btn_pause = make_btn("⏸  Pausar", obj_name="btnPause")
        self.btn_pause.setFixedHeight(52)
        self.btn_pause.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.btn_pause.clicked.connect(self._on_pause)
        self.btn_stop = make_btn("⏹  Detener", obj_name="btnStop")
        self.btn_stop.setFixedHeight(52)
        self.btn_stop.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.btn_stop.clicked.connect(self._on_stop)
        rb.addWidget(self.btn_pause, stretch=1)
        rb.addWidget(self.btn_stop, stretch=1)
        self.rec_btns.setVisible(False)
        cl.addWidget(self.rec_btns)

        cl.addSpacing(10)

        # ── Progress ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("pbar")
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        cl.addWidget(self.progress_bar)
        cl.addSpacing(4)
        self.progress_lbl = QLabel("")
        self.progress_lbl.setObjectName("ptext")
        self.progress_lbl.setAlignment(Qt.AlignCenter)
        self.progress_lbl.setFont(QFont("Segoe UI", 9))
        self.progress_lbl.setWordWrap(True)
        self.progress_lbl.setVisible(False)
        cl.addWidget(self.progress_lbl)

        cl.addSpacing(14)

        # ── Divider ──
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {C['border']};")
        cl.addWidget(div)
        cl.addSpacing(10)

        # ── History header ──
        hh = QHBoxLayout()
        self.history_title = QLabel("Grabaciones")
        self.history_title.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        self.history_title.setStyleSheet(f"color: {C['text']};")
        hh.addWidget(self.history_title)
        hh.addStretch()
        folder_btn_style = f"""
            QPushButton {{ background: transparent; border: none;
                           font-size: 14px; border-radius: 4px; }}
            QPushButton:hover {{ background: {C['card']}; }}
        """
        btn_folder_audio = make_btn("📂", "Abrir carpeta de audios", size=(28, 28))
        btn_folder_audio.setStyleSheet(folder_btn_style)
        btn_folder_audio.clicked.connect(lambda: os.startfile(str(RECORDINGS_DIR)))
        hh.addWidget(btn_folder_audio)
        btn_folder_trans = make_btn("📝", "Abrir carpeta de transcripciones", size=(28, 28))
        btn_folder_trans.setStyleSheet(folder_btn_style)
        btn_folder_trans.clicked.connect(
            lambda: os.startfile(str(TRANSCRIPTIONS_DIR))
            if TRANSCRIPTIONS_DIR.exists()
            else os.startfile(str(RECORDINGS_DIR))
        )
        hh.addWidget(btn_folder_trans)
        cl.addLayout(hh)
        cl.addSpacing(6)

        # ── History scroll ──
        self.scroll = QScrollArea()
        self.scroll.setObjectName("historyScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 4, 0)
        self.scroll_layout.setSpacing(6)
        self.scroll_layout.addStretch()
        self.scroll.setWidget(self.scroll_content)

        cl.addWidget(self.scroll, stretch=1)

        cl.addSpacing(8)

        # ── Footer ──
        ft = QLabel(f"Krypt v{APP_VERSION}  •  {APP_AUTHOR}  •  Powered by Gemini AI")
        ft.setObjectName("footer")
        ft.setAlignment(Qt.AlignCenter)
        ft.setFont(QFont("Segoe UI", 8))
        ft.setStyleSheet(f"color: {C['text3']};")
        cl.addWidget(ft)

        root.addWidget(self.card)

    # ── STYLES ───────────────────────────────────────────────
    def _apply_styles(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background: transparent; }}

            #mainCard {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {C['bg2']}, stop:1 {C['bg']});
                border: 1px solid {C['border']};
                border-radius: 14px;
            }}
            #title {{ color: {C['text']}; }}
            #timer {{ color: {C['text']}; letter-spacing: 3px; }}
            #status {{ color: {C['text2']}; }}
            #footer {{ color: {C['text3']}; }}

            /* ── Window buttons ── */
            #winBtn {{
                background: transparent; color: {C['text2']};
                border: none; border-radius: 15px; font-size: 13px;
            }}
            #winBtn:hover {{ background: {C['card']}; color: {C['text']}; }}
            #closeBtn {{
                background: transparent; color: {C['text2']};
                border: none; border-radius: 15px; font-size: 13px;
            }}
            #closeBtn:hover {{ background: {C['red']}; color: white; }}

            /* ── Record button ── */
            #btnRecord {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {C['purple']}, stop:1 {C['purple_light']});
                color: white; border: none; border-radius: 10px;
            }}
            #btnRecord:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {C['purple_light']}, stop:1 {C['purple']});
            }}

            /* ── Pause button ── */
            #btnPause {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {C['amber']}, stop:1 #ffbe76);
                color: #1a1a2e; border: none; border-radius: 10px;
            }}
            #btnPause:hover {{ background: #ffbe76; }}

            /* ── Resume button ── */
            #btnResume {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {C['green']}, stop:1 #7bed9f);
                color: #1a1a2e; border: none; border-radius: 10px;
            }}
            #btnResume:hover {{ background: #7bed9f; }}

            /* ── Stop button ── */
            #btnStop {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {C['red']}, stop:1 #ff8e8e);
                color: white; border: none; border-radius: 10px;
            }}
            #btnStop:hover {{ background: {C['red_dark']}; }}

            /* ── Upload button ── */
            #btnUpload {{
                background: {C['card']};
                color: {C['text']};
                border: 1px solid {C['card_border']};
                border-radius: 8px;
            }}
            #btnUpload:hover {{
                background: {C['card_hover']};
                border-color: {C['purple']};
                color: {C['purple_light']};
            }}

            /* ── Progress ── */
            #pbar {{
                background: {C['card']}; border: none; border-radius: 2px;
            }}
            #pbar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {C['purple']}, stop:1 {C['cyan']});
                border-radius: 2px;
            }}
            #ptext {{ color: {C['text2']}; }}

            /* ── Scroll area ── */
            #historyScroll {{
                background: transparent; border: none;
            }}
            #historyScroll > QWidget > QWidget {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {C['bg']}; width: 6px; border: none;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {C['card_border']}; border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {C['text3']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}

            /* ── Recording cards ── */
            #recCard {{
                background: {C['card']};
                border: 1px solid {C['card_border']};
                border-radius: 10px;
            }}
            #recCard:hover {{
                background: {C['card_hover']};
                border-color: {C['card_border_h']};
            }}

            /* ── Model Selector ── */
            QComboBox {{
                background: {C['card']};
                color: {C['text']};
                border: 1px solid {C['card_border']};
                border-radius: 8px;
                padding: 4px 10px;
                min-width: 180px;
                font-family: 'Segoe UI';
                font-size: 12px;
            }}
            QComboBox:hover {{
                background: {C['card_hover']};
                border-color: {C['purple']};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 0px;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QComboBox::down-arrow {{
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {C['text2']};
                width: 0;
                height: 0;
            }}
            QComboBox QAbstractItemView {{
                background: {C['bg2']};
                color: {C['text']};
                border: 1px solid {C['card_border']};
                border-radius: 8px;
                selection-background-color: {C['purple']};
                selection-color: white;
                outline: none;
                padding: 4px;
            }}
        """)

    def _on_model_changed(self):
        self.settings["selected_model"] = self.model_combo.currentData()
        save_settings(self.settings)

    # ── STARTUP RECOVERY ─────────────────────────────────────
    def _recover_stuck_transcriptions(self):
        """
        On startup, any recording stuck in 'transcribing' state means
        the app was closed mid-transcription. Reset these to 'error'
        so the user sees the retry button instead of a frozen card.
        """
        stuck = [r for r in self.db.all() if r.get("status") == "transcribing"]
        for rec in stuck:
            self.db.update(
                rec["id"],
                status="error",
                error_message="La app se cerró durante la transcripción. Presiona 🔄 para reintentar.",
            )

    # ── HISTORY LIST ─────────────────────────────────────────

    def _refresh_history(self):
        # Clear existing cards
        while self.scroll_layout.count() > 1:  # keep the stretch
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        records = self.db.all()
        self.history_title.setText(
            f"Grabaciones ({len(records)})" if records else "Grabaciones"
        )

        if not records:
            empty = QLabel("Aún no hay grabaciones")
            empty.setAlignment(Qt.AlignCenter)
            empty.setFont(QFont("Segoe UI", 10))
            empty.setStyleSheet(f"color: {C['text3']}; padding: 30px;")
            self.scroll_layout.insertWidget(0, empty)
            return

        for rec in records:
            card = RecordingCard(rec)
            card.transcribe_clicked.connect(self._on_transcribe_card)
            card.rename_clicked.connect(self._on_rename_card)
            card.delete_clicked.connect(self._on_delete_card)
            card.view_clicked.connect(self._on_view_card)
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, card)

    # ── RECORDING ACTIONS ────────────────────────────────────
    def _on_record(self):
        try:
            self.recorder.start()
        except Exception as e:
            self.status_lbl.setText(f"Error: {e}")
            self.status_lbl.setStyleSheet(f"color: {C['red']};")
            return

        self.is_recording = True
        self.is_paused = False
        self._rec_start = time.time()
        self._paused_total = 0

        self.btn_record.setVisible(False)
        self.rec_btns.setVisible(True)
        self.btn_pause.setText("⏸  Pausar")
        self.btn_pause.setObjectName("btnPause")
        self._apply_styles()

        self.status_lbl.setText("Grabando…")
        self.status_lbl.setStyleSheet(f"color: {C['rec_pulse']};")
        self.pulse_dot.set_color(C["rec_pulse"])
        self.pulse_dot.setVisible(True)
        self.pulse_dot.start()

        self.progress_bar.setVisible(False)
        self.progress_lbl.setVisible(False)

        self._tick_timer.start(100)

    def _on_pause(self):
        if not self.is_paused:
            # PAUSE
            self.recorder.pause()
            self.is_paused = True
            self._pause_start = time.time()

            self.btn_pause.setText("▶  Reanudar")
            self.btn_pause.setObjectName("btnResume")
            self._apply_styles()

            self.status_lbl.setText("En pausa")
            self.status_lbl.setStyleSheet(f"color: {C['amber']};")
            self.pulse_dot.set_color(C["amber"])
        else:
            # RESUME
            self.recorder.resume()
            self.is_paused = False
            self._paused_total += time.time() - self._pause_start

            self.btn_pause.setText("⏸  Pausar")
            self.btn_pause.setObjectName("btnPause")
            self._apply_styles()

            self.status_lbl.setText("Grabando…")
            self.status_lbl.setStyleSheet(f"color: {C['rec_pulse']};")
            self.pulse_dot.set_color(C["rec_pulse"])

    def _on_stop(self):
        self.is_recording = False
        self._tick_timer.stop()

        self.btn_record.setVisible(True)
        self.rec_btns.setVisible(False)
        self.btn_record.setEnabled(False)
        self.btn_record.setText("⏳  Guardando…")

        self.status_lbl.setText("Procesando audio…")
        self.status_lbl.setStyleSheet(f"color: {C['text2']};")
        self.pulse_dot.stop()
        self.pulse_dot.setVisible(False)

        # Calculate duration
        if self.is_paused:
            self._paused_total += time.time() - self._pause_start
        self.is_paused = False
        self._pending_duration = time.time() - self._rec_start - self._paused_total

        # Mezcla y compresión en segundo plano (la ventana no se congela)
        self._save_worker = SaveRecordingWorker(self.recorder)
        self._save_worker.done.connect(self._on_recording_saved)
        self._save_worker.failed.connect(self._on_recording_save_failed)
        self._save_worker.start()

    def _on_recording_saved(self, audio_path_str: str):
        rec_id = self._register_recording(Path(audio_path_str), self._pending_duration)

        # Reset button
        self.btn_record.setText("⏺  Grabar")
        self.btn_record.setEnabled(True)
        self.status_lbl.setText("✅ Audio guardado")
        self.status_lbl.setStyleSheet(f"color: {C['green']};")

        # Auto-start transcription
        self._start_transcription(rec_id)

    def _on_recording_save_failed(self, error_msg: str):
        self.btn_record.setText("⏺  Grabar")
        self.btn_record.setEnabled(True)
        self.status_lbl.setText(f"❌ No se pudo guardar el audio: {error_msg[:120]}")
        self.status_lbl.setStyleSheet(f"color: {C['red']};")

    def _register_recording(self, audio_path: Path, fallback_duration: float) -> str:
        # La duración real del archivo manda; el reloj de la ventana es respaldo
        duration = get_audio_duration(audio_path) or fallback_duration

        # Register in DB
        ts = datetime.now()
        rec_id = f"REC_{ts.strftime('%Y%m%d_%H%M%S')}"
        name = f"Grabación {ts.day} {MONTHS_ES[ts.month - 1]} {ts.year}, {ts.hour:02d}:{ts.minute:02d}"

        self.db.add({
            "id": rec_id,
            "name": name,
            "audio_file": audio_path.name,
            "transcript_file": None,
            "created_at": ts.isoformat(),
            "duration_seconds": round(duration, 1),
            "status": "recorded",
            "error_message": None,
        })

        self._refresh_history()
        return rec_id

    # ── UPLOAD EXTERNAL AUDIO ────────────────────────────────
    def _on_upload_audio(self):
        """Permite al usuario seleccionar un archivo de audio externo
        (WhatsApp .ogg/.opus, MP3, WAV, M4A, AAC, FLAC, etc.),
        lo copia a grabaciones/, lo convierte a MP3 si es necesario,
        y lo registra en la base de datos para transcribir."""
        if self.is_recording:
            QMessageBox.warning(self, "Grabando",
                                "Detén la grabación antes de subir un audio.")
            return

        AUDIO_FILTERS = (
            "Archivos de audio (*.mp3 *.wav *.ogg *.opus *.m4a *.aac "
            "*.flac *.wma *.amr *.webm *.mp4 *.3gp);;"
            "Todos los archivos (*)"
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de audio", "", AUDIO_FILTERS
        )
        if not file_path:
            return  # El usuario canceló

        src = Path(file_path)
        if not src.exists():
            QMessageBox.warning(self, "Error", f"No se encontró el archivo:\n{src}")
            return

        self.status_lbl.setText("Importando audio...")
        self.status_lbl.setStyleSheet(f"color: {C['amber']};")
        self.btn_upload.setEnabled(False)
        QApplication.processEvents()

        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

        # Generar nombre único
        ts = datetime.now()
        base_name = f"UPLOAD_{ts.strftime('%Y%m%d_%H%M%S')}"

        # Copiar y convertir a MP3 si no es MP3
        if src.suffix.lower() == ".mp3":
            dest = RECORDINGS_DIR / f"{base_name}.mp3"
            shutil.copy2(str(src), str(dest))
        else:
            # Convertir cualquier formato a MP3 mono 48kbps con FFmpeg
            dest = RECORDINGS_DIR / f"{base_name}.mp3"
            try:
                cmd = [
                    get_ffmpeg_bin(), "-y", "-i", str(src),
                    "-codec:a", "libmp3lame", "-b:a", "48k", "-ac", "1",
                    str(dest)
                ]
                subprocess.run(
                    cmd, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, check=True,
                    creationflags=_SUBPROCESS_FLAGS
                )
            except Exception as e:
                # Si FFmpeg falla, copiar el archivo tal cual
                dest = RECORDINGS_DIR / f"{base_name}{src.suffix}"
                shutil.copy2(str(src), str(dest))

        # Obtener duración
        duration = get_audio_duration(dest)

        # Nombre amigable basado en el archivo original
        friendly_name = src.stem.replace("_", " ").replace("-", " ")
        name = f"📎 {friendly_name}"

        # Registrar en la base de datos
        rec_id = f"UPLOAD_{ts.strftime('%Y%m%d_%H%M%S')}"
        self.db.add({
            "id": rec_id,
            "name": name,
            "audio_file": dest.name,
            "transcript_file": None,
            "created_at": ts.isoformat(),
            "duration_seconds": round(duration, 1),
            "status": "recorded",
            "error_message": None,
        })

        self._refresh_history()
        self.btn_upload.setEnabled(True)

        size_mb = dest.stat().st_size / 1024**2
        self.status_lbl.setText(
            f"✅ Audio importado ({size_mb:.1f} MB, {fmt_duration(duration)})"
        )
        self.status_lbl.setStyleSheet(f"color: {C['green']};")

    def _update_clock(self):
        if self.is_paused:
            elapsed = self._pause_start - self._rec_start - self._paused_total
        else:
            elapsed = time.time() - self._rec_start - self._paused_total
        h = int(elapsed // 3600)
        m = int((elapsed % 3600) // 60)
        s = int(elapsed % 60)
        self.time_lbl.setText(f"{h:02d}:{m:02d}:{s:02d}")

    # ── TRANSCRIPTION ────────────────────────────────────────
    def _start_transcription(self, rec_id: str):
        if not ConfigManager.get_api_key():
            setup_dlg = ApiKeySetupDialog(self)
            if setup_dlg.exec() != QDialog.Accepted or not ConfigManager.get_api_key():
                QMessageBox.warning(
                    self, "API Key requerida",
                    "Debes configurar tu API Key de Google Gemini para poder transcribir.\n\n"
                    "Haz clic en el engranaje (⚙️) en la parte superior para ingresarla."
                )
                return

        if self._current_transcription_id:
            QMessageBox.information(
                self, "Espera",
                "Ya hay una transcripción en progreso.\n"
                "Espera a que termine antes de iniciar otra.",
            )
            return

        rec = self.db.get(rec_id)
        if not rec:
            return

        audio_path = RECORDINGS_DIR / rec["audio_file"]
        if not audio_path.exists():
            QMessageBox.warning(
                self, "Audio no encontrado",
                f"El archivo de audio no existe:\n{audio_path.name}",
            )
            return

        self._current_transcription_id = rec_id
        self.db.update(rec_id, status="transcribing", error_message=None)
        self._refresh_history()

        # Show progress
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_lbl.setText("Iniciando transcripción…")
        self.progress_lbl.setVisible(True)
        self.status_lbl.setText("Transcribiendo…")
        self.status_lbl.setStyleSheet(f"color: {C['cyan']};")

        selected_model = self.model_combo.currentData()
        self.worker = TranscriptionWorker(rec_id, audio_path, rec["name"], model=selected_model)
        self.worker.signals.progress.connect(self._on_tx_progress)
        self.worker.signals.finished.connect(self._on_tx_finished)
        self.worker.signals.error.connect(self._on_tx_error)
        self.worker.start()

    def _on_tx_progress(self, msg: str, pct: int):
        self.progress_lbl.setText(msg)
        if pct >= 0:
            self.progress_bar.setValue(pct)

    def _on_tx_finished(self, rec_id: str, transcript_path: str):
        self._current_transcription_id = None
        self.db.update(
            rec_id,
            status="transcribed",
            transcript_file=Path(transcript_path).name,
            error_message=None,
        )
        self._refresh_history()

        self.status_lbl.setText("✅ ¡Transcripción completada!")
        self.status_lbl.setStyleSheet(f"color: {C['green']};")
        self.progress_lbl.setText(Path(transcript_path).name)
        self.progress_bar.setValue(100)

        # Open the transcript
        os.startfile(transcript_path)

    def _on_tx_error(self, rec_id: str, error_msg: str):
        self._current_transcription_id = None
        self.db.update(rec_id, status="error", error_message=error_msg)
        self._refresh_history()

        self.status_lbl.setText("❌ Error en transcripción")
        self.status_lbl.setStyleSheet(f"color: {C['red']};")
        self.progress_lbl.setText(error_msg)

    # ── CARD ACTIONS ─────────────────────────────────────────
    def _on_transcribe_card(self, rec_id: str):
        self._start_transcription(rec_id)

    def _on_rename_card(self, rec_id: str):
        rec = self.db.get(rec_id)
        if not rec:
            return
        new_name, ok = QInputDialog.getText(
            self, "Renombrar grabación",
            "Nuevo nombre:", text=rec["name"],
        )
        if ok and new_name.strip():
            self.db.update(rec_id, name=new_name.strip())
            self._refresh_history()

    def _on_delete_card(self, rec_id: str):
        rec = self.db.get(rec_id)
        if not rec:
            return
        reply = QMessageBox.question(
            self, "Eliminar grabación",
            f"¿Eliminar «{rec['name']}»?\n\n"
            "Se borrará el audio y la transcripción.\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Delete audio file
        audio = RECORDINGS_DIR / rec.get("audio_file", "")
        if audio.exists():
            try:
                audio.unlink()
            except Exception:
                pass

        # Delete transcript file
        tx = rec.get("transcript_file")
        if tx:
            tx_path = TRANSCRIPTIONS_DIR / tx
            if tx_path.exists():
                try:
                    tx_path.unlink()
                except Exception:
                    pass

        self.db.delete(rec_id)
        self._refresh_history()

    def _on_view_card(self, rec_id: str):
        rec = self.db.get(rec_id)
        if not rec or not rec.get("transcript_file"):
            return
        path = TRANSCRIPTIONS_DIR / rec["transcript_file"]
        if path.exists():
            os.startfile(str(path))
        else:
            QMessageBox.warning(
                self, "Archivo no encontrado",
                f"No se encontró: {rec['transcript_file']}",
            )

    # ── WINDOW DRAG ──────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _):
        self._drag_pos = None

    # ── CLOSE EVENT ──────────────────────────────────────────
    def closeEvent(self, event):
        busy = self.worker is not None and self.worker.isRunning()
        if busy:
            reply = QMessageBox.question(
                self, "Transcripción en curso",
                "Hay una transcripción en curso. Si cierras Krypt se cancelará\n"
                "(el audio queda guardado y puedes reintentarla después).\n\n¿Cerrar de todos modos?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return

        if self.is_recording:
            # Guardar de forma síncrona: la app se va a cerrar
            self.is_recording = False
            self._tick_timer.stop()
            if self.is_paused:
                self._paused_total += time.time() - self._pause_start
            duration = time.time() - self._rec_start - self._paused_total
            self.status_lbl.setText("Guardando grabación…")
            QApplication.processEvents()
            try:
                self._register_recording(finalize_recording(self.recorder), duration)
            except Exception:
                pass
        elif self._save_worker is not None and self._save_worker.isRunning():
            # Registrar aquí (sin auto-transcribir): la señal ya no llegaría
            self._save_worker.done.disconnect()
            self._save_worker.wait()
            if self._save_worker.result:
                self._register_recording(self._save_worker.result, self._pending_duration)

        if busy:
            # Un QThread vivo al salir hace que Python aborte; la tarjeta queda
            # como "error" al reabrir (_recover_stuck_transcriptions).
            self.worker.terminate()
            self.worker.wait(2000)
        event.accept()


# ═════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═════════════════════════════════════════════════════════════════
# Alias para el nuevo nombre oficial
KryptWindow = TranscriptorWindow


# ═════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═════════════════════════════════════════════════════════════════
def main():
    _migrate_legacy_data()
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTIONS_DIR.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    if ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_PATH)))

    # Si no hay API key configurada (primer inicio en PC nuevo), mostrar bienvenida
    api_key = ConfigManager.get_api_key()
    if not api_key:
        setup_dlg = ApiKeySetupDialog()
        setup_dlg.exec()

    win = KryptWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

