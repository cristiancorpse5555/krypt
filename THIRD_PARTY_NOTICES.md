# Componentes de terceros

Krypt se distribuye bajo la licencia MIT (ver `LICENSE`). El instalador de Windows incluye los siguientes componentes de
terceros, cada uno bajo su propia licencia:

| Componente | Uso en Krypt | Licencia | Sitio / código fuente |
|---|---|---|---|
| **FFmpeg** (`ffmpeg.exe`, `ffprobe.exe`, build *full* de gyan.dev) | Mezcla y compresión de audio a MP3 | **GPL v3** | <https://ffmpeg.org> · build: <https://www.gyan.dev/ffmpeg/builds/> · fuente: <https://github.com/FFmpeg/FFmpeg> |
| **PySide6 / Qt** | Interfaz gráfica | LGPL v3 | <https://www.qt.io/qt-for-python> |
| **PyAudioWPatch** (PortAudio) | Captura de audio del sistema y micrófono (WASAPI) | MIT | <https://github.com/s0d3s/PyAudioWPatch> |
| **NumPy** | Mezcla de audio de respaldo | BSD 3-Clause | <https://numpy.org> |
| **google-genai** | Cliente de la API de Google Gemini | Apache 2.0 | <https://github.com/googleapis/python-genai> |
| **Python** | Intérprete embebido | PSF License | <https://www.python.org> |

FFmpeg se incluye como programa independiente (ejecutables separados que Krypt invoca), sin modificaciones. Su código
fuente completo y la configuración de compilación están disponibles en los enlaces de arriba; texto de la GPL v3:
<https://www.gnu.org/licenses/gpl-3.0.html>. Las licencias de los paquetes de Python se incluyen en la carpeta de
instalación (`_internal`).
