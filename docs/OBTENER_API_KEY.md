# 🔑 Cómo obtener tu clave de Google Gemini (paso a paso)

Krypt usa la inteligencia artificial **Gemini** de Google para transcribir. Para eso necesita una **clave de API**: un
código largo que identifica tu cuenta. Es **gratis** para un uso normal y toma unos 3 minutos.

> No necesitas tarjeta de crédito ni saber programar. Solo una cuenta de Google (la misma de Gmail).

---

## Paso 1 · Entra a Google AI Studio

1. Abre tu navegador (Chrome, Edge, etc.).
2. Ve a: **<https://aistudio.google.com/apikey>**
3. Si te lo pide, **inicia sesión** con tu cuenta de Google.

## Paso 2 · Acepta las condiciones (solo la primera vez)

La primera vez aparece una ventana con los términos de servicio de Google AI Studio.
Marca la casilla de aceptación y pulsa **Continuar**.

## Paso 3 · Crea la clave

1. Pulsa el botón **"Crear clave de API"** (*"Create API key"* si tu cuenta está en inglés).
2. Si te pregunta por un **proyecto**, elige el que aparece por defecto o pulsa **"Crear clave de API en un proyecto
   nuevo"**. Cualquiera de los dos sirve.
3. En unos segundos aparece tu clave: un texto largo que empieza por **`AIza`**.

## Paso 4 · Copia la clave

Pulsa el botón **Copiar** que está junto a la clave.

## Paso 5 · Pégala en Krypt

1. Abre **Krypt**.
   - La primera vez se abre sola la ventana de bienvenida: pega la clave y pulsa **Guardar y Continuar**.
   - Si ya la pasaste, pulsa el engranaje **⚙️** arriba a la derecha.
2. Pega la clave (clic derecho → Pegar, o `Ctrl + V`).
3. Pulsa **⚡ Probar Conexión**. Debe decir ✅ *API Key válida*.
4. Pulsa **Guardar**. ¡Listo! Ya puedes grabar y transcribir.

---

## ❓ Preguntas frecuentes

**¿Cuesta dinero?**
Google ofrece un **nivel gratuito** con un límite de uso diario que alcanza para un uso personal normal. Si un día lo
superas, Krypt te avisa ("cuota agotada"): espera al día siguiente o elige otro modelo en el selector. Solo pagarías si tú
mismo activas la facturación en Google Cloud.

**¿Es segura mi clave?**
La clave se guarda **solo en tu PC**, en `Documentos\Krypt\config.json`. Krypt no la envía a nadie más que a Google.
**No la compartas**: quien la tenga puede usar tu cuota.

**Creo que alguien vio mi clave, ¿qué hago?**
Vuelve a <https://aistudio.google.com/apikey>, **borra** esa clave (ícono de papelera) y crea una nueva. Pégala de nuevo
en Krypt (⚙️ → Guardar).

**Dice "API Key inválida".**
Revisa que copiaste la clave completa, sin espacios al inicio o al final. Si sigue fallando, crea una clave nueva.

**Mis audios, ¿quedan en Google?**
Para transcribir, el audio se sube a Google Gemini y **Krypt lo borra de los servidores de Google al terminar** (también si
la transcripción falla). Las grabaciones y transcripciones quedan solo en tu PC, en `Documentos\Krypt`.
