# 🔑 How to get your Google Gemini key (step by step)

<p><a href="OBTENER_API_KEY.md">🇪🇸 Español</a> · 🇬🇧 English</p>

Krypt uses Google's **Gemini** AI to transcribe. To do that it needs an **API key**: a long code that identifies your
account. It's **free** for normal use and takes about 3 minutes.

> You don't need a credit card or any programming knowledge. Just a Google account (the same one you use for Gmail).

---

## Step 1 · Go to Google AI Studio

1. Open your browser (Chrome, Edge, etc.).
2. Go to: **<https://aistudio.google.com/apikey>**
3. If asked, **sign in** with your Google account.

## Step 2 · Accept the terms (first time only)

The first time, a window with the Google AI Studio terms of service appears.
Tick the checkbox to accept and click **Continue**.

## Step 3 · Create the key

1. Click the **"Create API key"** button.
2. If it asks you for a **project**, choose the one shown by default or click **"Create API key in new project"**.
   Either works.
3. After a few seconds your key appears: a long piece of text starting with **`AIza`**.

## Step 4 · Copy the key

Click the **Copy** button next to the key.

## Step 5 · Paste it into Krypt

1. Open **Krypt**.
   - The first time, the welcome window opens by itself: paste the key and click **Guardar y Continuar** (Save and
     continue).
   - If you skipped it, click the **⚙️** gear icon at the top right.
2. Paste the key (right-click → Paste, or `Ctrl + V`).
3. Click **⚡ Probar Conexión** (Test connection). It should say ✅ *API Key válida* (valid).
4. Click **Guardar** (Save). Done! You can now record and transcribe.

---

## ❓ Frequently asked questions

**Does it cost money?**
Google offers a **free tier** with a daily usage limit that's enough for normal personal use. If you go over it one
day, Krypt tells you ("cuota agotada" = quota exhausted): wait until the next day or pick another model in the selector.
You'd only pay if you yourself enable billing in Google Cloud.

**Is my key safe?**
The key is stored **only on your PC**, in `Documents\Krypt\config.json`. Krypt doesn't send it to anyone except Google.
**Don't share it**: whoever has it can use your quota.

**I think someone saw my key, what do I do?**
Go back to <https://aistudio.google.com/apikey>, **delete** that key (trash icon) and create a new one. Paste it into
Krypt again (⚙️ → Guardar).

**It says "API Key inválida" (invalid).**
Check that you copied the whole key, with no spaces at the beginning or end. If it still fails, create a new key.

**Do my recordings stay on Google's servers?**
To transcribe, the audio is uploaded to Google Gemini and **Krypt deletes it from Google's servers when it's done** (also
if the transcription fails). Recordings and transcripts stay only on your PC, in `Documents\Krypt`.
