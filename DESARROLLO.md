# 🔧 Documentación Técnica — Krypt v3.4

Documentación de arquitectura, decisiones de diseño, empaquetado y guía para desarrollo continuo.

---

## Arquitectura General

```
┌──────────────────────────────────────────────────────────────┐
│                         KryptWindow                          │
│                    (QMainWindow, PySide6)                    │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ AudioRecorder│  │ Transcription│  │  ConfigManager   │   │
│  │              │  │ Worker       │  │  & RecordingsDB  │   │
│  │ - loopback   │  │ (QThread)    │  │                  │   │
│  │ - mic        │  │              │  │  - config.json   │   │
│  │ - pause      │  │ - Gemini 3.5 │  │  - recordings    │   │
│  │ - mix        │  │   Transcribe │  │    .json         │   │
│  │ - disk stream│  │ - Flash fallb│  │  - API Key safe  │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                 │                   │              │
│         ▼                 ▼                   ▼              │
│  %TEMP%/.krypt_*.raw  Interactions API   Documents/Krypt/    │
│  (Cero RAM leak)      (Gemini Audio)     (Persistencia)     │
│         │                                     │              │
│         ▼                                     ▼              │
│    ffmpeg.exe                           grabaciones/         │
│  (MP3 48kbps mono)                      transcripciones/     │
└──────────────────────────────────────────────────────────────┘
```

---

## Componentes Principales

### 1. AudioRecorder (`main.py`)

**Responsabilidad:** Capturar audio del sistema y micrófono, mezclarlos, guardar como WAV.

**⚡ Optimización de RAM (v2.1):**
- **Antes:** Todo el audio se acumulaba en listas Python en RAM → ~500MB+ para 30min, crashes en PCs con 8GB.
- **Ahora:** El audio se escribe directamente a archivos temporales en disco (`grabaciones/.temp_*.raw`). La mezcla se hace en chunks de 10 segundos post-grabación.
- **RAM durante grabación:** ~5 MB constante, sin importar la duración.
- **RAM durante mezcla:** ~5 MB (un chunk de 10 segundos a la vez).
- **Crash safety:** Los archivos se flushean al disco cada ~2 segundos.

**Captura de audio:**
- Usa **PyAudioWPatch** que extiende PyAudio con soporte para WASAPI loopback
- WASAPI loopback permite capturar "lo que suena" sin instalar drivers virtuales
- Busca automáticamente el dispositivo de loopback que corresponde a la salida predeterminada
- El micrófono es opcional (si falla, graba solo el sistema)

**Pausa:**
- Al pausar, los recording threads siguen leyendo del stream (obligatorio para evitar buffer overflow)
- Pero los frames leídos NO se escriben al disco (`if not self.is_paused: fh.write(data)`)
- El audio resultante es continuo sin silencios durante la pausa

**Sincronía loopback ↔ micrófono (v3.4):**
- WASAPI loopback **no entrega paquetes mientras no suena nada** en la salida. Sin corrección, la pista del sistema pierde
  sus silencios y queda desfasada respecto al micrófono (que es continuo).
- `_start_silence()` reproduce silencio (callback de PortAudio) en la salida predeterminada durante la grabación, así el
  motor de audio entrega el loopback de forma continua.
- Red de seguridad en `_record_to_disk()`: compara los frames escritos con el reloj monotónico (descontando pausas) y
  rellena con ceros cualquier hueco mayor a `LOOPBACK_GAP_FILL_SECONDS` (0,5 s).
- Si un `stream.read()` falla (dispositivo desconectado) el hilo espera 50 ms en vez de girar al 100% de CPU.

**Mezcla (post-grabación):**
- **Principal — FFmpeg** (`_mix_with_ffmpeg`): lee los dos `.raw` (`-f s16le`), remuestrea a 48 kHz mono (`aformat`),
  `amix=duration=longest:normalize=0` + `alimiter`, y codifica directo a **MP3 mono 48 kbps / 44.1 kHz**.
- **Respaldo — numpy** (si FFmpeg no está): bloques de 10 s (`MIX_CHUNK_SECONDS`), remuestreo por interpolación lineal,
  `loopback*0.7 + mic*0.5`, la pista corta se completa con ceros. Salida WAV que luego se comprime con `compress_to_mp3`.
- La mezcla y compresión corren en `SaveRecordingWorker` (QThread) para no congelar la UI.

**Formato de salida:**
- MP3 mono 48 kbps (~21 MB/hora). Gemini acepta hasta 2 GB por archivo.

### 2. RecordingsDB (`main.py`)

**Responsabilidad:** CRUD de metadata de grabaciones.

**Almacenamiento:** JSON plano en `grabaciones/recordings.json`.

**Esquema de cada registro:**
```json
{
    "id":               "REC_20260420_180200",
    "name":             "Reunión de equipo",
    "audio_file":       "REC_20260420_180200.wav",
    "transcript_file":  "Transcripcion_2026-04-20_18-02-30.md",
    "created_at":       "2026-04-20T18:02:00.123456",
    "duration_seconds": 936.5,
    "status":           "transcribed",
    "error_message":    null
}
```

**Estados posibles:**
| Estado | Significado |
|---|---|
| `recorded` | Audio guardado, no transcrito |
| `transcribing` | Transcripción en progreso |
| `transcribed` | Transcripción completada exitosamente |
| `error` | Transcripción falló (error_message tiene detalles) |

**¿Por qué JSON y no SQLite?**  
Para uso personal con <100 grabaciones, JSON es suficiente, no agrega dependencias, y es fácil de inspeccionar/editar manualmente.

### 3. TranscriptionWorker (`main.py`)

**Responsabilidad:** Subir audio a Gemini o Groq, transcribir, guardar Markdown.

**Flujo con `gemini-3.5-transcribe`:**
1. Verificar si el audio necesita división (`>28 min`)
2. Si sí, dividir en chunks de 25 min en carpeta temporal del SO
3. Para cada chunk:
   a. Upload a Gemini Files API
   b. Esperar estado ACTIVE
   c. Llamar `client.interactions.create` con `transcription_config` (modo verbatim, diarización de hablantes y timestamps por palabra)
   d. Formatear las anotaciones en diálogo con marcas de tiempo acumuladas `**[HH:MM:SS] [Hablante N]:**`
   e. Limpiar archivo remoto y chunk temporal
4. Combinar transcripciones en un solo Markdown
5. Guardar en `transcripciones/`

**Retry logic:**
- **Error 503 (UNAVAILABLE) / 500:** Retry hasta 3 veces con delays de 20s, 45s, 90s
- **Error 429 con "limit: 0":** NO retry (requiere billing o cambio de modelo)
- **Error 429 temporal:** Retry hasta 3 veces
- **Otros errores:** No retry, error inmediato

### 4. UI (PySide6)

**Diseño:**
- Ventana frameless con bordes redondeados (16px)
- Fondo dark gradient (#12121a → #0a0a0f)
- Draggable (mousePressEvent/mouseMoveEvent)
- Tamaño fijo: 520 × 700 px

**Componentes UI:**
| Widget | Clase | Rol |
|---|---|---|
| Timer | QLabel | Muestra tiempo transcurrido |
| PulsingDot | QWidget custom | Indicador animado de grabación |
| Botón principal | QPushButton | Grabar / Pausar+Detener |
| Progress | QProgressBar + QLabel | Estado de transcripción |
| Historial | QScrollArea + RecordingCard[] | Lista de grabaciones |

**Estados del botón principal:**
| Estado | Botones visibles | Estilo |
|---|---|---|
| Idle | `⏺ Grabar` | Purple gradient |
| Recording | `⏸ Pausar` + `⏹ Detener` | Amber + Red |
| Paused | `▶ Reanudar` + `⏹ Detener` | Green + Red |
| Processing | `⏺ Grabar` (disabled) | Purple (disabled) |

---

## API de Gemini — Detalles

### SDK utilizado
```
google-genai >= 2.20.0
```
Es el **SDK unificado** de Google con soporte para la **Interactions API** (`client.interactions.create`).

### Inicialización
```python
from google import genai
client = genai.Client(api_key="...")
```

### Files API + Interactions API (`gemini-3.5-transcribe`)
```python
# 1. Upload
uploaded = client.files.upload(file="path/to/audio.wav")

# 2. Esperar estado ACTIVE
info = client.files.get(name=uploaded.name)

# 3. Transcribir con Interactions API
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

# 4. Limpiar
client.files.delete(name=uploaded.name)
```

### Límites importantes
| Límite | Valor |
|---|---|
| Audio continuo (gemini-3.5-transcribe con diarización) | 30 minutos por llamada |
| Audio continuo (gemini-3.5-transcribe modo smart) | 60 minutos por llamada |
| Tamaño máximo por archivo (Files API) | 2 GB |
| Almacenamiento total por proyecto | 20 GB |
| Retención de archivos | 48 horas |

---

## Dependencias

| Paquete | Versión | Uso |
|---|---|---|
| **PySide6** | ≥ 6.7.0 | GUI (Qt6 bindings para Python) |
| **PyAudioWPatch** | ≥ 0.2.12 | Captura WASAPI loopback + micrófono |
| **google-genai** | ≥ 2.20.0 | SDK de Google Gemini API (Interactions API) |
| **numpy** | ≥ 1.26.0 | Procesamiento de audio (mezcla, resample, normalización) |

### Dependencias transitivas notables
- `portaudio` (viene empaquetado con PyAudioWPatch)
- `httpx` (usado por google-genai)
- `pydantic` (usado por google-genai)
- Todas las DLLs de Qt6 (vienen con PySide6)

---

## Guía de Modificaciones Comunes

### Cambiar los modelos de IA
```python
# main.py, lista GEMINI_MODELS y GEMINI_MODEL_DEFAULT (al inicio del archivo)
GEMINI_MODEL_DEFAULT = "gemini-3.5-transcribe"
```

### Cambiar la mezcla de audio (volumen relativo)
```python
# AudioRecorder._mix_with_ffmpeg(): pesos de amix, p. ej. "amix=inputs=2:weights='1 0.8':..."
# Respaldo numpy en _mix_from_disk(): mixed[...] += lb_mono * 0.7 / mc_mono * 0.5
```

### Cambiar duración de chunks
```python
CHUNK_DURATION_SECONDS = 25 * 60  # main.py, sección de modelos
```

### Cambiar delays de retry
```python
RETRY_DELAYS = [20, 45, 90]  # main.py, segundos entre reintentos
```

### Cambiar el prompt de transcripción
```python
# En TranscriptionWorker._prompt()
# Modifica las instrucciones para cambiar formato, idioma, nivel de detalle, etc.
```

### Cambiar dimensiones de la ventana
```python
# En TranscriptorWindow.__init__()
self.setFixedSize(520, 700)  # ancho × alto en px
```

### Cambiar la tasa de muestreo
```python
# En AudioRecorder.__init__()
self._target_rate = 44100  # Hz (44100 = CD quality, 16000 = speech-optimized)
```
> Nota: Reducir a 16000 Hz reduce el tamaño del archivo ~2.7x pero puede degradar la calidad si hay música o efectos.

### Agregar un nuevo campo a las grabaciones
1. Modifica el diccionario en `_on_stop()` al crear el registro
2. Modifica `RecordingCard._build()` para mostrar el campo
3. El JSON es un esquema libre, no hay migraciones

---

## Arquitectura de Archivos de Audio

### Nomenclatura
```
REC_YYYYMMDD_HHMMSS.wav
```
Ejemplo: `REC_20260420_180200.wav` = grabación del 20 de abril de 2026 a las 18:02:00

### Formato
- **Codec:** PCM (sin compresión)
- **Canales:** 1 (mono)
- **Sample rate:** 44,100 Hz
- **Bit depth:** 16 bits
- **Tamaño aproximado:** ~5 MB por minuto

### Chunking para reuniones largas
- Si la grabación dura >31 minutos, se divide en segmentos de 30 minutos
- Los chunks se crean en una carpeta temporal del sistema (`tempfile.mkdtemp()`)
- Se eliminan después de transcribir
- El archivo original siempre permanece intacto

---

## Flujo de Estados de una Grabación

```
                    ┌──────────┐
        Detener     │ recorded │
    ───────────────▶│          │
                    └────┬─────┘
                         │ Auto / Manual
                         ▼
                    ┌──────────────┐
                    │ transcribing │◄──────────────┐
                    │              │               │
                    └──┬───────┬───┘               │
                       │       │                   │
                  OK   │       │ Error        Reintentar
                       ▼       ▼                   │
                ┌────────┐  ┌───────┐              │
                │transcri│  │ error │──────────────┘
                │  bed   │  │       │
                └────┬───┘  └───────┘
                     │
                Re-transcribir
                     │
                     └──────────▶ transcribing
```

---

## Entorno de Desarrollo

### Configuración
- **IDE:** VS Code con extensiones Python y Pylance
- **Python:** 3.13 (ver `venv/`)
- **OS:** Windows 11 (Huawei MateBook D14)

### Para desarrollar
```bash
# Activar entorno
venv\Scripts\activate

# Ejecutar con output de consola visible (para debug)
python main.py

# Ver logs de error directamente en la terminal
```

### Estructura del código (`main.py`)
El código está en un solo archivo organizado en secciones:

| Sección | Contenido |
|---|---|
| Config | API key, modelo, constantes, colores |
| Helpers | Funciones de formato (duración, tamaño, fecha) |
| RecordingsDB | Base de datos JSON |
| AudioRecorder | Captura a disco y mezcla chunked de audio |
| TranscriptionWorker | Upload, retry, transcripción, Markdown |
| PulsingDot | Widget animado de punto pulsante |
| RecordingCard | Widget de tarjeta de grabación |
| TranscriptorWindow | Ventana principal con toda la lógica UI |
| main() | Entry point |

### Perfil de RAM (medido en MateBook D14, 8GB)
| Operación | RAM estimada |
|---|---|
| App idle | ~200 MB (PySide6 + Python + deps) |
| Grabando (cualquier duración) | ~205 MB (constante, ~5 MB para buffers) |
| Mezclando post-grabación | ~210 MB (chunks de 10s, pico ~5 MB extra) |
| **Total pico** | **~210 MB** |

Comparación con v1.0/v2.0 (sin optimización):
| Duración | RAM v1-v2 (en memoria) | RAM v2.1 (a disco) |
|---|---|---|
| 5 min | ~300 MB | ~205 MB |
| 30 min | ~800 MB | ~205 MB |
| 1 hora | ~1.8 GB | ~205 MB |
| 2 horas | ~3.5 GB ❌ crash | ~205 MB ✅ |

---

## ☁️ Roadmap & Evolución a la Nube (VPS + Bot de Reuniones)

### 📌 Visión General del Proyecto Nube
El objetivo de la siguiente fase del desarrollo es migrar **Transcriptor** desde una aplicación de escritorio Windows local a una **Plataforma Web SaaS / Cloud 100% alojada en un Servidor VPS** (ej. Hetzner, DigitalOcean, AWS o servidor propio) bajo un subdominio personalizado (`transcriptor.tudominio.com`).

### 🎯 Problema que Resuelve
1. **Restricciones de Hardware y SO Móvil (Android / iOS)**: Android 10+ bloquea la captura de audio interno para llamadas VoIP (`USAGE_VOICE_COMMUNICATION` en Teams, Meet, Zoom, WhatsApp) y restringe el uso simultáneo de micrófono a apps de terceros. Un bot en la nube elimina totalmente esta barrera.
2. **Fricción de Micrófono en PC**: Elimina la necesidad de silenciar/activar manualmente el micrófono de la PC; el bot captura la mezcla pura de audio digital directamente de la sala de reuniones.
3. **Acceso Multi-Dispositivo y Colaboración**: Accesible desde cualquier dispositivo (Pixel 10 Pro, iPhone, PC, Tablet) por el usuario o su equipo de trabajo.

---

### 🏛️ Arquitectura del Servicio Web en la Nube

```
┌────────────────────────────────────────────────────────────────────────┐
│                        transcriptor.tudominio.com                      │
│                    (Web App Frontend / Dashboard)                      │
│   - Pegar URL de reunión (Meet / Teams / Zoom)                         │
│   - Historial de transcripciones, reproductor de audio MP3 y resumenes  │
│   - Integración futura con Google Calendar / Outlook                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Servidor Backend / Workstations (VPS)                │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                 🤖 Meeting Bot Engine Container                │   │
│   │  - Se une a la sala como "Asistente Transcriptor"              │   │
│   │  - Captura el stream de audio digital (WebRTC / Headless)      │   │
│   │  - Pipe de compresión inmediata a MP3 mono 48kbps / OGG        │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │                                    │
│                                   ▼                                    │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                🧠 Motor de Transcripción IA                    │   │
│   │  - Gemini 3.7 Flash / Gemini 3.5 Flash Lite                    │   │
│   │  - Fallback a Groq Whisper + Llama 3.3 (Diarización)          │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │                                    │
│                                   ▼                                    │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                 💾 Almacenamiento & Base de Datos              │   │
│   │  - Audios MP3 comprimidos en disco / S3 / Cloudflare R2        │   │
│   │  - Metadata y Markdown en Postgres / SQLite                    │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

### ⚠️ Nota & Directiva para la IA (Cloud Code / Desarrolladores Futuros)

> **INSTRUCCIÓN DIRECTA PARA LA IA QUE LEA ESTE DOCUMENTO:**
> Tienes **total libertad de cuestionar, auditar y proponer la arquitectura más conveniente, segura y estable** para el Bot de Reuniones y la infraestructura en la nube. No te limites únicamente a la solución planteada. Debes realizar tu propia investigación previa considerando:

1. **Estrategia de Construcción del Bot de Reunión**:
   - **Opción A (Bot Propio Headless)**: Docker con Chromium / Playwright / Node.js o Python + Sink virtual PulseAudio. Evaluar estabilidad de cambios en el DOM de Google Meet / Teams / Zoom vs costo $0 de licencias.
   - **Opción B (APIs de Infraestructura de Bots)**: Evaluar servicios existentes como *Recall.ai*, *MeetingBaas* o similares para delegar el ciclo de vida del bot vía Webhooks si se busca acelerar el time-to-market.
   - **Opción C (WebRTC Nativo / APIs Oficiales)**: Evaluar integración con Zoom Meeting SDK, Microsoft Graph Communication APIs o Google Meet REST API.

2. **Gestión de Audios y Compresión**:
   - Definir la estrategia de almacenamiento (disco local del VPS con ciclo de limpieza automático vs Object Storage S3 / Cloudflare R2).
   - Garantizar que todo audio capturado por el bot sea convertido en tiempo real o post-procesamiento inmediato a **MP3 mono 48kbps** o **OGG Opus** para mantener un peso ultraligero (<25 MB por hora) antes de enviarlo a Gemini 3.7 Flash o Groq.

3. **Seguridad, Privacidad y Control de Accesos**:
   - Definir autenticación (JWT / OAuth2) para acceso al panel `transcriptor.tudominio.com`.
   - Manejo seguro de llaves API (`GEMINI_API_KEY`, `GROQ_API_KEY`) almacenadas en variables de entorno `.env` en el VPS.
   - Consentimiento y aviso visual de presencia del bot al unirse a las salas.

---

## 🧭 Guía para Cambiar de PC, Control de Versiones y Trabajo Continuo

Esta guía está diseñada para gestionar el proyecto a largo plazo, cambiar de computadora sin perder nada y entender el flujo de trabajo entre la versión de desarrollo y el instalador.

### 1. ¿Cómo funciona hoy con OneDrive?
Actualmente la carpeta del proyecto está ubicada en:
`D:\OneDrive\Documentos\ANTIGRAVITY\Transcriptor`

- **Si inicias sesión en otro PC con tu misma cuenta de Microsoft:**
  OneDrive sincronizará automáticamente los archivos de código (`main.py`, `assets/`, `krypt.spec`, `installer.iss`, etc.).
- **⚠️ Lo que NO se debe sincronizar ni copiar manualmente:**
  La carpeta `venv\` (entorno virtual de Python) y las carpetas `build\` y `dist\`.
  *¿Por qué?* Porque `venv` contiene ejecutables de Python y librerías C compiladas con las rutas fijas de este PC en específico.
- **En un PC nuevo:**
  Solo haces doble clic en `Krypt_Dev.bat`. El script detecta si falta el entorno, lo crea de forma limpia en 1 minuto, instala las dependencias de `requirements.txt` y abre la app lista para trabajar.

---

### 2. ¿Cómo organizamos nuestro trabajo (Local vs. Instalable)?

El proyecto tiene un ciclo de trabajo en 2 pasos muy claro:

| Modo | Archivo | ¿Para qué sirve? |
|---|---|---|
| **🛠️ Modo Desarrollo (Trabajo conmigo)** | `Krypt_Dev.bat` | Ejecuta la app directamente desde el código fuente (`main.py`). Aquí es donde me pides cambios (nuevos modelos, botones, mejoras), los programo y tú los pruebas inmediatamente sin esperar tiempos de compilación. |
| **📦 Modo Instalador (Distribución)** | `build_installer.bat` | Cuando una versión ya está lista y probada, haces doble clic aquí. Compila todo en `dist_installer\Krypt_Setup_vX.X.exe`. Este es el archivo final que instalas en `C:\Program Files\Krypt` o le compartes a tus clientes/socios. |

---

### 3. ¿Cómo usar GitHub para que nunca se pierda nada?

**GitHub** es el estándar de la industria. Es como un Google Drive pero diseñado para software:
- Es **privado** (solo tú tienes acceso).
- Guarda **cada versión** en el tiempo (puedes volver a una versión anterior con un clic si algo se rompe).
- Si cambias de PC o me das acceso en otra máquina, solo descargas el proyecto con un clic o lo sincronizas de inmediato.
- Te permite publicar los instaladores (`.exe`) en la sección **Releases** de GitHub para tener un link de descarga seguro.

#### Cómo vincular esta carpeta a GitHub (Solo se hace una vez):
1. Crea una cuenta gratuita en [github.com](https://github.com/) si aún no tienes.
2. Crea un repositorio llamado `Krypt` y márcalo como **Private**.
3. En la terminal de la carpeta, ejecutas:
   ```bash
   git init
   git add .
   git commit -m "Krypt v3.3 - Versión instalable completa"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/Krypt.git
   git push -u origin main
   ```
*(Nota: El archivo `.gitignore` ya está configurado para que Git suba únicamente el código limpio, íconos y configuraciones, ignorando archivos pesados o temporales).*

---

### 4. ¿Dónde están mis datos personales y notas?

Tus archivos privados están completamente separados del código del programa:
- **Ruta:** `C:\Users\<tu_usuario>\Documents\Krypt\`
  - `grabaciones/`: Tus audios en MP3
  - `transcripciones/`: Tus notas y actas en Markdown (`.md`)
  - `config.json`: Tu Google Gemini API Key
- Si compartes la carpeta del proyecto o el instalador, **nadie tendrá acceso a tus audios ni a tu API Key**.

---

*Documentación actualizada el 27 de agosto de 2026. Versión actual: Krypt v3.3 (Cristian Novoa · DMT Agencia)*

