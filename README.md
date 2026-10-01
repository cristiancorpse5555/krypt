# 🎙️ Krypt v3.3

**Grabador y transcriptor inteligente de reuniones virtuales y audios.**  
Captura audio del sistema + micrófono, convierte automáticamente a MP3 o importa audios externos (WhatsApp, notas de voz, etc.), y los transcribe con **Google Gemini (Audio Nativo con Diarización de Hablantes)**.

> **Creado por Cristian Novoa · DMT Agencia**

---

## ✨ Funcionalidades

### 🤖 IA y Transcripción Multi-Modelo (Google Gemini)
- 🎙️ **Gemini 3.5 Transcribe (Por defecto)** — Modelo nativo de transcripción de Google con diarización acústica de interlocutores (`[Hablante 1]`, `[Hablante 2]`), marcas de tiempo exactas por palabra y cero alucinaciones.
- ⚡ **Gemini 3.7 Flash** — El modelo Flash más capaz e inteligente de Google, con soporte para workflows agénticos y ejecución multi-paso.
- 🐢 **Gemini 3.5 Flash Lite** — Opción de altísima velocidad y coste mínimo ($0.30/Mtok).
- 🔄 **Auto-Selección Inteligente** — Intenta con Gemini 3.5 Transcribe con fallback automático a Gemini 3.7 Flash y 3.5 Flash Lite si se agota la cuota.
- 👥 **Identificación de hablantes** — Separación de interlocutores y etiquetas consistentes.
- ⏱️ **Timestamps** — Marcas de tiempo cada intervención `[HH:MM:SS]`.
- 📝 **Salida Markdown** — Archivo `.md` limpio, formateado y estructurado guardado en `Documentos\Krypt\transcripciones`.

### 🎵 Grabación y Gestión de Audio
- 🎧 **Captura de audio del sistema** — Captura altavoces/auriculares (Zoom, Teams, Meet, llamadas web, etc.)
- 🎤 **Micrófono simultáneo** — Tu voz mezclada con la llamada
- 🎵 **Compresión MP3 Automática (FFmpeg)** — Convierte audios a MP3 mono 48kbps automáticamente. ¡Reduce el tamaño un 93%!
- 📎 **Subida de Audios Externos** — Importa archivos de WhatsApp (`.ogg`/`.opus`), MP3, WAV, M4A, AAC, FLAC, AMR, WebM, etc.
- ⏸️ **Pausar / Reanudar** — Pausa la grabación sin perder continuidad.
- 🚀 **Arranque Instantáneo (Lazy Loading)** — La ventana abre en ~1.5 segundos.
- ⚡ **RAM Plana (~5MB durante grabación)** — Streaming continuo a disco temporal, evitando saturar memoria en llamadas largas.

### Gestión e Interfaz
- ⚙️ **Configuración Integrada de API Key** — Diálogo de bienvenida al primer arranque y botón ⚙️ permanente para ingresar, verificar y cambiar tu API Key de Gemini sin tocar código.
- 📋 **Historial visual** — Tarjetas interactivas con estados (`transcrito`, `error`, `grabado`).
- 🔄 **Re-transcribir** — Cambia de modelo en cualquier momento y reintenta.
- ✏️ **Renombrar y 🗑️ Eliminar** — Gestión total de archivos y transcripciones.
- 📄 **Ver transcripción** — Abre el `.md` directamente desde el historial.

---

## 🚀 Instalación en Windows

### Como Usuario Final (Instalador Oficial)

No requieres tener instalado Python ni FFmpeg. El instalador incluye todo:

```
1. Ejecuta: dist_installer\Krypt_Setup_v3.3.exe
2. Se instalará automáticamente en C:\Program Files\Krypt
3. Creará el acceso directo en tu Escritorio y Menú Inicio
4. Al abrir, te pedirá tu Google Gemini API Key (o puedes configurarla desde ⚙️)
```

### Configurar API Key de Gemini
1. Obtén tu clave gratuita en [Google AI Studio](https://aistudio.google.com/apikey).
2. Pégala en el diálogo inicial de Krypt o haz clic en el ícono de **engranaje (⚙️)** en la barra superior.
3. Haz clic en **⚡ Probar Conexión** para validar que esté activa.
4. ¡Listo! La clave se guardará automáticamente en `Documentos\Krypt\config.json`.

---

## 🛠️ Flujo de Trabajo y Desarrollo

### 1. Modo Desarrollo (Modificar y Probar)
Si deseas hacer cambios en el código o probar funciones nuevas:
```bash
# Doble clic en:
Krypt_Dev.bat
# Abre la app directamente desde el código fuente sin compilar.
```

### 2. Generar Nuevo Instalador
Cuando los cambios estén listos y quieras generar un nuevo instalador para Windows:
```bash
# Doble clic en:
build_installer.bat
# Genera automáticamente el instalador en dist_installer\Krypt_Setup_v3.3.exe
```

---

## 📖 Guía de Uso

### Grabar una reunión

1. **Abre Krypt** (doble clic en el ícono del escritorio o en `Krypt_Dev.bat`)
2. **Presiona ⏺ Grabar** → comienza a capturar audio del sistema y micrófono
3. Inicia o únete a tu reunión virtual (Zoom, Teams, Meet, etc.)
4. Durante la grabación puedes:
   - **⏸ Pausar** → El audio se detiene (útil para breaks)
   - **▶ Reanudar** → Continúa grabando
5. **Presiona ⏹ Detener** → El audio se guarda e inicia la transcripción automática
6. **Espera** → La barra de progreso muestra el estado
7. **Listo** → El archivo `.md` se abre automáticamente al terminar

### Gestionar grabaciones (historial)

| Acción | Cómo |
|---|---|
| **Ver transcripción** | Click en 📄 en la tarjeta de la grabación |
| **Re-transcribir** | Click en 🔄 (si falló o quieres mejor resultado) |
| **Renombrar** | Click en ✏️ → escribe el nuevo nombre |
| **Eliminar** | Click en 🗑 → confirma en el diálogo |
| **Abrir carpeta** | Click en 📂 en el header "Grabaciones" |

### Si hay un error de transcripción

1. El audio **siempre queda guardado** en `grabaciones/`
2. La grabación aparece con estado **"Error ✗"** en el historial
3. Puedes hacer click en **🔄 Reintentar** cuando quieras
4. Si el error es 503 (servidor ocupado), la app reintenta automáticamente 3 veces con esperas de 15s, 30s y 60s

---

## 📁 Estructura del Proyecto

```
Transcriptor/
│
├── main.py                      # Aplicación principal (todo el código)
├── requirements.txt             # Dependencias Python
├── Transcriptor.bat             # Lanzador con auto-setup
├── crear_acceso_directo.bat     # Crea ícono en Escritorio (llama al .ps1)
├── crear_acceso_directo.ps1     # Script PowerShell para el acceso directo
├── README.md                    # Esta documentación
├── CHANGELOG.md                 # Historial de versiones
├── DESARROLLO.md                # Documentación técnica y arquitectura
│
├── grabaciones/                 # 💾 Audio WAV (persistente)
│   ├── recordings.json          # Base de datos de grabaciones (JSON)
│   ├── REC_20260420_180200.wav  # Archivos de audio
│   └── ...
│
├── transcripciones/             # 📝 Archivos Markdown generados
│   ├── Transcripcion_2026-04-20_18-02-30.md
│   └── ...
│
└── venv/                        # Entorno virtual Python (auto-generado)
```

---

## ⚙️ Configuración

### Cambiar el modelo de Gemini

Edita la **línea 21** de `main.py`:

```python
GEMINI_MODEL = "gemini-3-flash-preview"  # ← Cambia aquí
```

#### Modelos disponibles (agosto 2026)

| Modelo | Velocidad | Calidad | Free Tier | Notas |
|---|---|---|---|---|
| `gemini-3.5-transcribe` | ⚡⚡ Muy rápida | ⭐⭐⭐⭐⭐ | ✅ Sí | **Por Defecto**. Transcripción nativa con diarización acústica y timestamps por palabra. |
| `gemini-3.7-flash` | ⚡ Muy rápida | ⭐⭐⭐⭐⭐ | ✅ Sí | Modelo Flash generativo más capaz e inteligente. |
| `gemini-3.6-flash` | ⚡ Rápida | ⭐⭐⭐⭐ | ✅ Sí | Modelo anterior, estable. |
| `gemini-3.5-flash-lite` | ⚡⚡ Muy rápida | ⭐⭐⭐ | ✅ Sí | Ultra económico ($0.30/Mtok). |
| `gemini-3.1-pro-preview` | 🐢 Lenta | ⭐⭐⭐⭐⭐ | ❌ Billing | El más capaz. Requiere billing activo. |
| `groq-whisper` | ⚡⚡⚡ Ultra rápida | ⭐⭐⭐⭐ | ✅ Gratis | Whisper + Llama 3.3 para diarización. |

### Duración de cortes (Chunks dinámicos para reuniones largas)

- **Audios de ≤ 28 minutos**: No se dividen. Se procesan de forma 100% continua en un solo bloque.
- **Audios de > 28 minutos**: Se dividen en bloques óptimos de 25 minutos (`CHUNK_DURATION_SECONDS = 25 * 60`). Los timestamps acumulativos y offsets de tiempo se calculan y unifican de forma transparente.

---

## 🐛 Solución de Problemas

| Problema | Causa | Solución |
|---|---|---|
| **"No se encontró dispositivo de loopback"** | No hay salida de audio activa | Conecta auriculares o parlantes como dispositivo predeterminado |
| **Error 429 "limit: 0"** | El modelo elegido requiere billing | Cambia a un modelo con free tier (ver tabla arriba) |
| **Error 429 "rate limit"** | Demasiadas solicitudes por minuto | Espera 1-2 minutos y reintenta |
| **Error 503 "UNAVAILABLE"** | Servidores de Google congestionados | La app reintenta automático. Si persiste, intenta otro modelo. |
| **Python no encontrado** | Python no está en PATH | Reinstala Python 3.11+ marcando "Add Python to PATH" |
| **Audio vacío / silencio** | No hay sonido en el sistema | Verifica que el audio esté activo (reproduce algo durante la grabación) |
| **Transcripción cortada** | Audio muy largo para un solo chunk | Reduce `CHUNK_DURATION_SECONDS` a 20*60 (20 min) |
| **No se crea acceso directo** | Permisos de Windows | Ejecuta `crear_acceso_directo.bat` como administrador |

---

## 🗺️ Roadmap & Evolución a la Nube (Próxima Fase)

Consultar la especificación técnica en [DESARROLLO.md](file:///d:/OneDrive/Documentos/ANTIGRAVITY/Transcriptor/DESARROLLO.md#roadmap--evolución-a-la-nube-vps--bot-de-reuniones) para ver el plan de arquitectura para migrar este proyecto a un **Servicio Web en la Nube (VPS + Subdominio)** con **Bot de Reuniones Automático** (Google Meet, Teams, Zoom).

---

## 📜 Licencia

Proyecto personal. Uso libre.
