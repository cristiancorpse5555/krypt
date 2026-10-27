<p align="center">
  <img src="assets/icon/krypt-256.png" alt="Krypt" width="120"/>
</p>

<h1 align="center">Krypt</h1>

<p align="center">
  <b>Graba tus reuniones y audios en Windows y transcríbelos con IA, con cada hablante identificado.</b><br/>
  Zoom · Teams · Meet · llamadas web · notas de voz de WhatsApp
</p>

<p align="center">
  <a href="https://github.com/cristiancorpse5555/krypt/releases/latest"><img alt="Descargar" src="https://img.shields.io/github/v/release/cristiancorpse5555/krypt?label=descargar&color=2ea44f"/></a>
  <img alt="Windows" src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6"/>
  <a href="LICENSE"><img alt="Licencia MIT" src="https://img.shields.io/badge/licencia-MIT-blue"/></a>
</p>

---

## ¿Qué hace?

Krypt graba **al mismo tiempo el sonido de tu PC y tu micrófono** (tú y las demás personas de la llamada), lo guarda
como MP3 liviano y lo transcribe con **Google Gemini**. El resultado es un archivo de texto (Markdown) así:

```markdown
**[00:00:04] [Hablante 1]:** Buenos días, arrancamos con el avance de obra.
**[00:00:11] [Hablante 2]:** Perfecto. El tramo dos quedó listo el viernes.
```

- 🎧 **Graba la llamada completa:** audio del sistema + micrófono, sincronizados.
- 👥 **Identifica a cada hablante** y pone la **hora exacta** de cada intervención.
- 📎 **Importa audios** de WhatsApp (`.ogg`/`.opus`), MP3, WAV, M4A, FLAC y más.
- ⏸️ **Pausa y reanuda** la grabación cuando quieras.
- ⏱️ **Reuniones largas sin problema:** las de más de 28 minutos se dividen y se unen solas.
- 🔒 **Tus archivos se quedan en tu PC.** El audio solo sale hacia Google para transcribirse y se borra de allá al terminar.
- 💸 **Gratis:** usa el nivel gratuito de Google Gemini con tu propia clave.

## 📥 Instalación (para cualquier persona)

1. Ve a **[Descargas (Releases)](https://github.com/cristiancorpse5555/krypt/releases/latest)** y descarga
   **`Krypt_Setup_v3.4.exe`** (en la sección *Assets*).
2. Haz doble clic en el archivo descargado.
3. **Si Windows muestra "Windows protegió su PC"** (pasa con programas nuevos que no compraron un certificado de firma):
   pulsa **"Más información"** y luego **"Ejecutar de todas formas"**.
4. Sigue el asistente (*Siguiente → Instalar*). Krypt queda en el **menú Inicio** y en el **Escritorio**.
5. Al abrirlo por primera vez te pide tu **clave de Google Gemini** →
   **[cómo obtenerla gratis, paso a paso](docs/OBTENER_API_KEY.md)** (3 minutos).

No necesitas instalar Python ni nada más: el instalador trae todo.

**Requisitos:** Windows 10 u 11 de 64 bits, conexión a internet para transcribir, y parlantes o audífonos conectados
(Windows necesita una salida de audio activa para captar el sonido del PC).

## 🎙️ Cómo se usa

> [!WARNING]
> **Silenciarte en Teams, Meet o Zoom NO te silencia en Krypt.**
>
> Krypt graba directamente el **micrófono del computador**, no el de la reunión. Si apagas el micrófono solo dentro de
> Teams o Meet, los demás participantes dejan de oírte, **pero Krypt te sigue grabando**: cualquier comentario que hagas
> "con el micrófono apagado" quedará en la grabación y en la transcripción.
>
> **Para que algo no quede grabado, apaga el micrófono del computador**, no solo el de la reunión:
> - Con la **tecla o botón de silenciar micrófono** del equipo (muchos portátiles tienen una tecla con un micrófono
>   tachado, o un botón en los audífonos).
> - O desde Windows: ícono de sonido junto al reloj → silenciar el micrófono.
> - O pulsa **⏸ Pausar** en Krypt mientras hablas algo que no deba quedar grabado.

### Grabar una reunión
1. Abre Krypt y pulsa **⏺ Grabar**.
2. Entra a tu reunión (Zoom, Teams, Meet…). Krypt capta lo que suena en el PC y tu micrófono.
3. Usa **⏸ Pausar / ▶ Reanudar** si lo necesitas. Recuerda: silenciarte en la reunión no te silencia en Krypt (ver el
   aviso de arriba).
4. Pulsa **⏹ Detener**. Krypt guarda el MP3 y **empieza a transcribir solo**.
5. Al terminar se abre la transcripción.

### Transcribir un audio que ya tienes
Pulsa **📎 Subir Audio**, elige el archivo y luego **📤** en su tarjeta.

### El historial
Cada grabación aparece como una tarjeta:

| Botón | Acción |
|---|---|
| 📄 | Ver la transcripción |
| 📤 / 🔄 | Transcribir · reintentar · volver a transcribir con otro modelo |
| ✏️ | Renombrar |
| 🗑 | Eliminar el audio y su transcripción |
| 📂 / 📝 | Abrir la carpeta de audios / de transcripciones |

### Elegir el modelo
En **Modelo IA** puedes elegir:
- **Gemini 3.5 Transcribe** *(predeterminado)*: transcripción nativa con hablantes y tiempos exactos.
- **Auto-Seleccionar**: si un modelo se queda sin cuota gratuita, pasa al siguiente.
- **Gemini 3.7 Flash / 3.5 Flash Lite** y otros: alternativas si se agota la cuota del día.

### ¿Dónde quedan mis archivos?
Todo en **`Documentos\Krypt`**: `grabaciones\` (MP3), `transcripciones\` (Markdown) y tu configuración.

## 🛠️ Solución de problemas

| Problema | Solución |
|---|---|
| "No se encontró dispositivo de loopback" | Conecta parlantes o audífonos y elígelos como salida predeterminada de Windows. |
| "Cuota agotada" (429 / limit: 0) | Se acabó la cuota gratuita del día para ese modelo: elige otro en **Modelo IA** o usa *Auto-Seleccionar*. |
| "Servidor sobrecargado" (503) | Krypt reintenta solo 3 veces; si sigue, espera unos minutos o cambia de modelo. |
| "API Key inválida" | Revísala en ⚙️ → *Probar Conexión*. Ver [la guía de la clave](docs/OBTENER_API_KEY.md). |
| Quedó grabado algo que dije con el micrófono apagado en la reunión | Krypt graba el micrófono del computador, no el de Teams/Meet. Apaga el micrófono del equipo o usa **⏸ Pausar**. |
| La grabación quedó en silencio | Verifica que el sonido salga por los parlantes/audífonos predeterminados y que el micrófono esté permitido en *Configuración de Windows → Privacidad → Micrófono*. |

## 👩‍💻 Para desarrolladores

Krypt está hecho en **Python 3.13** con **PySide6** (interfaz), **PyAudioWPatch** (captura WASAPI), **FFmpeg** (audio) y
**google-genai** (Gemini). Detalles de arquitectura en [`DESARROLLO.md`](DESARROLLO.md).

```bash
git clone https://github.com/cristiancorpse5555/krypt.git
cd krypt
py -3.13 -m venv venv
venv\Scripts\pip install -r requirements.txt
```

1. Descarga FFmpeg para Windows (<https://www.gyan.dev/ffmpeg/builds/>) y copia `ffmpeg.exe` y `ffprobe.exe` en una
   carpeta `bin\` dentro del proyecto (no se suben al repositorio por su tamaño).
2. Ejecuta desde el código: **`Krypt_Dev.bat`**.
3. Genera el instalador: instala [Inno Setup 6](https://jrsoftware.org/isinfo.php) y ejecuta **`build_installer.bat`**
   → `dist_installer\Krypt_Setup_v3.4.exe`.

¿Encontraste un error o tienes una idea? Abre un **[Issue](https://github.com/cristiancorpse5555/krypt/issues)**.
Las contribuciones (*pull requests*) son bienvenidas.

## 📄 Licencia

Código bajo licencia **[MIT](LICENSE)** © 2026 DMT Consultora.
El instalador incluye componentes de terceros (FFmpeg bajo GPL v3, Qt bajo LGPL v3, entre otros): ver
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

Krypt no está afiliado a Google. Gemini y Google AI Studio son marcas de Google LLC.
