# 📋 Changelog — Krypt

Todas las versiones y cambios relevantes del proyecto.

## [v3.3] — 2026-08-27

### 🚀 Transformación a Krypt (App Instalable Windows)
- **Marca Oficial Krypt** — Creado por Cristian Novoa · DMT Agencia. Nuevo nombre, identidad y logotipo verde.
- **Instalador Oficial de Windows** — Paquete instalador profesional compilado con Inno Setup (`Krypt_Setup_v3.3.exe`) que instala automáticamente en `C:\Program Files\Krypt`.
- **Ejecución 100% Autónoma** — Python 3.13, PySide6 y FFmpeg van embebidos en el instalador; no requiere instalar Python ni herramientas externas en la PC del usuario final.
- **Ícono Oficial Corregido** — Se configuró la extracción de `krypt.ico` en la raíz de la instalación para que Windows muestre el ícono oficial en el escritorio, barra de tareas y menú inicio.
- **100% Limpio de Credenciales** — Código libre de claves por defecto para poder compartir el instalador públicamente con total seguridad.
- **Configuración de Google Gemini API Key en UI** — Diálogo de bienvenida interactivo en el primer inicio y botón permanente de engranaje (⚙️) con botón para probar la conexión en vivo.
- **Separación de Datos de Usuario** — Audios, transcripciones y base de datos se alojan en `Documentos\Krypt\`, garantizando cero errores de permisos en `Program Files`.
- **Desacople de Groq** — Retiro de Groq Whisper y dependencias; la auto-selección inteligente ahora hace cascada entre Gemini 3.5 Transcribe, Gemini 3.7 Flash y Gemini 3.5 Flash Lite.
- **Script de Compilación Automatizado** — Inclusión de `build_installer.bat` para regenerar el instalador con un solo clic.

### 🎙️ Modelo Nativo: Gemini 3.5 Transcribe
- **Gemini 3.5 Transcribe como Modelo por Defecto** — Integración del nuevo modelo de transcripción nativo de Google (`gemini-3.5-transcribe`) a través de la Interactions API de `google-genai` (SDK v2.20.0).
- **Diarización Acústica Nativa** — Identificación de turnos de interlocutores (`[Hablante 1]`, `[Hablante 2]`) basada en timbre de voz real.
- **Marcas de Tiempo Exactas** — Generación de timestamps precisos a nivel de palabra acumulados en formato `**[HH:MM:SS] [Hablante N]:**`.
- **Cortes Dinámicos Optimizados (25-28 min)** — Audios de hasta 28 minutos se procesan continuos sin cortes. Para reuniones más largas, división automática en bloques de 25 minutos.
- **Actualización CLI** — `transcribir_ahora.py` sincronizado con los mismos modelos y lectura de clave desde `config.json`.

---

## [v3.2] — 2026-08-14

### 🤖 Actualización de Modelos de Gemini
- **Gemini 3.7 Flash** — Nuevo modelo agregado como predeterminado en `Auto-Seleccionar`. Es el Flash más capaz e inteligente hasta la fecha, con soporte para coding, workflows agénticos y ejecución multi-paso. Input: $0.75/Mtok, Output: $3.75/Mtok.
- **Auto-Seleccionar actualizado** — Ahora intenta primero con Gemini 3.7 Flash (antes 3.6) con fallback a Groq Whisper.
- **Gemini 3.6 Flash** — Movido como modelo anterior (ya no es el recomendado por defecto).
- **Actualización en CLI** — `transcribir_ahora.py` actualizado con las mismas prioridades.

### 🐛 Corrección: Pantallas negras durante transcripción
- **Ventanas de consola ocultas** — Se agregó `CREATE_NO_WINDOW` a todas las llamadas de `subprocess.run` (FFmpeg y ffprobe) para evitar que aparezcan ventanas de consola negras parpadeando en Windows durante la compresión, segmentación y obtención de duración del audio.

### 🚀 Optimización: Archivos temporales de grabación
- **Temp files movidos a `%TEMP%`** — Los archivos temporales `.raw` de la grabación ahora se escriben en el directorio temporal del sistema (`tempfile.gettempdir()`) en vez de `grabaciones/`. Esto evita interferencias con sincronizadores de nube y reduce la presión de I/O sobre el disco del proyecto.

---

## [v3.1] — 2026-07-21

### 🤖 Actualización de Modelos de Gemini
- **Gemini 3.6 Flash** — Agregado al selector y definido como el modelo predeterminado inicial en el modo `Auto-Seleccionar` (con fallback a Groq Whisper si se agota la cuota).
- **Gemini 3.5 Flash Lite** — Incorporado como una alternativa de alta velocidad y muy bajo costo ($0.30/Mtok de entrada).
- **Actualización en CLI** — El script `transcribir_ahora.py` fue actualizado con las mismas prioridades y opciones de modelos actualizadas.

### 📎 Subir Audio Externo
- **Botón "📎 Subir Audio"** — Permite importar archivos de audio externos (WhatsApp `.ogg`/`.opus`, MP3, WAV, M4A, AAC, FLAC, WMA, AMR, etc.) directamente desde la interfaz gráfica.
- **Conversión automática** — Los archivos en formatos distintos a MP3 se convierten automáticamente a MP3 mono 48kbps con FFmpeg, reduciendo drásticamente su peso.
- **Integración completa** — Los audios importados aparecen en el historial de grabaciones con el prefijo 📎, listos para transcribir con cualquier modelo disponible.

---

## [v3.0] — 2026-07-17

### ⚡ Integración de Groq Whisper y Llama 3.3
- **Motor Groq Whisper** — Soporte para transcribir usando `whisper-large-v3` a través de Groq, libre de límites de cuota de Gemini y con una velocidad extrema (~4 min para audios de 1h 22m).
- **Formateador Llama 3.3** — Estructuración de transcripciones usando `llama-3.3-70b-versatile` para separar interlocutores y dar formato de diálogo limpio.
- **Auto-Selección Inteligente** — El modelo por defecto `Auto-Seleccionar` intenta transcribir con Gemini 3.5 Flash y, si falla por saturación o falta de cuota, realiza un fallback automático e inmediato a Groq Whisper.

### 🎵 Optimización de audio (Compresión MP3 con FFmpeg)
- **Compresión MP3 automática** — Al finalizar la grabación, el archivo WAV crudo se convierte automáticamente a MP3 mono a 48kbps.
- **Ahorro de espacio del 93%** — Un audio de 1 hora pasa de ocupar ~400 MB a solo ~21 MB, acelerando exponencialmente la sincronización con OneDrive y las subidas a las APIs.
- **Segmentación Inteligente** — Se reemplazó la lógica manual con la librería `wave` por llamadas rápidas a FFmpeg (`-c copy`) para segmentar los archivos MP3 en porciones de 20 minutos de forma instantánea.

### 🚀 Optimización de Arranque (Lazy Loading)
- **Arranque en ~2 segundos** — Se implementó carga perezosa (lazy-loading) de librerías de inicio pesadas (`numpy`, `pyaudiowpatch`, `google-genai`, `groq`). La interfaz gráfica ahora se muestra casi instantáneamente al no tener que importar estas dependencias hasta el momento en que son requeridas (al grabar o transcribir).

---

## [v2.1] — 2026-04-20

### 🚀 Optimización crítica de RAM

**Problema:** La app acumulaba todo el audio en listas Python en memoria RAM. Para grabaciones de 30+ minutos en el MateBook D14 (8GB RAM), esto causaba ~800MB-2GB de consumo, congelando o crasheando el sistema.

**Solución:** Reescritura completa de `AudioRecorder` para streaming a disco.

### Cambios técnicos
- **Streaming a disco** — El audio se escribe directamente a archivos temporales (`.temp_loopback.raw`, `.temp_mic.raw`) en vez de acumularse en RAM
- **Mezcla chunked** — Post-grabación, mezcla en chunks de 10 segundos (`MIX_CHUNK_SECONDS`), RAM constante
- **Flush periódico** — Archivos flusheados al disco cada ~2 segundos para crash safety
- **Clipeo suave** — `np.clip()` per-chunk en vez de normalización global

### Impacto de RAM
| Duración | Antes (v2.0) | Ahora (v2.1) |
|---|---|---|
| 5 min | ~300 MB | ~205 MB |
| 30 min | ~800 MB 🟡 | ~205 MB ✅ |
| 1 hora | ~1.8 GB 🔴 | ~205 MB ✅ |
| 2 horas | ~3.5 GB ❌ crash | ~205 MB ✅ |

---

## [v2.0] — 2026-04-20

### ✨ Nuevas funcionalidades
- **⏸ Pausar / ▶ Reanudar grabación** — Controla la grabación sin perder audio
- **📋 Historial de grabaciones** — Panel visual con tarjetas para cada grabación
- **🔄 Re-transcribir** — Vuelve a transcribir grabaciones fallidas o insatisfactorias
- **✏️ Renombrar grabaciones** — Cambia el nombre desde la interfaz (QInputDialog)
- **🗑 Eliminar grabaciones** — Borra audio + transcripción con confirmación
- **📄 Ver transcripción** — Abre el .md directamente desde la tarjeta
- **📂 Abrir carpeta** — Botón de acceso rápido a `grabaciones/`
- **🔁 Auto-retry en error 503** — Reintenta hasta 3 veces con backoff exponencial (15s, 30s, 60s)
- **💾 Audio persistente** — Los WAV nunca se borran automáticamente

### 🔧 Mejoras
- **Modelo cambiado a `gemini-3-flash-preview`** — Más rápido y menos congestionado que 2.5-flash
- **Errores legibles** — Los errores de API se traducen a mensajes claros en español
- **RecordingsDB** — Base de datos JSON (`recordings.json`) para metadata de grabaciones
- **Cierre seguro** — Si cierras la app grabando, el audio se guarda automáticamente
- **Bloqueo de transcripción concurrente** — Solo una transcripción a la vez para evitar conflictos de cuota
- **Eliminado `temp_audio/`** — Ya no se usa; los audios van directo a `grabaciones/`
- **Eliminado `soundfile`** — Dependencia innecesaria removida

### 🐛 Correcciones
- **Acceso directo del Escritorio** — Reescrito con PowerShell (.ps1) para compatibilidad con rutas OneDrive
- **Error 429 permanente** — Detecta "limit: 0" y muestra mensaje claro en vez de reintentar infinitamente
- **Errores raw de API** — Ya no muestra el JSON crudo del error, sino mensajes comprensibles

---

## [v1.0] — 2026-04-20

### ✨ Release inicial
- Ventana PySide6 frameless con diseño dark premium
- Grabación de audio del sistema (WASAPI loopback) + micrófono
- Mezcla automática de ambas fuentes en WAV mono 44.1kHz 16-bit
- Transcripción vía Gemini Files API
- Generación de archivo Markdown con timestamps e identificación de hablantes
- Chunking automático para reuniones >30 minutos
- Apertura automática de la carpeta con el resultado
- Scripts BAT para lanzar y crear acceso directo

### Stack técnico original
- PySide6 6.11 (GUI)
- PyAudioWPatch 0.2.12 (WASAPI loopback)
- google-genai 1.73 (SDK de Gemini)
- numpy 2.4 (procesamiento de audio)
- Modelo: `gemini-2.5-flash` → migrado a `gemini-3-flash-preview` en v2.0

---

## Convenciones

- Las versiones siguen formato `[major.minor]`
- Los archivos de audio se nombran `REC_YYYYMMDD_HHMMSS.wav`
- Las transcripciones se nombran `Transcripcion_YYYY-MM-DD_HH-MM-SS.md`
- La metadata se almacena en `grabaciones/recordings.json`
