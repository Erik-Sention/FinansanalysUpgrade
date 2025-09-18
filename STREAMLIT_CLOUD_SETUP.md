# 🤖 Streamlit Cloud Setup för FinansAnalys

## 🚨 VIKTIGT: Firebase Secrets Setup

Streamlit Cloud kan INTE läsa från `env.local` filen. Du måste konfigurera secrets manuellt i Streamlit Cloud Dashboard.

### 📋 Steg-för-steg instruktioner:

#### 1. 🌐 Gå till Streamlit Cloud Dashboard
- Öppna: https://share.streamlit.io/
- Logga in med ditt GitHub-konto
- Hitta din app: `finansanalysupgrade`

#### 2. ⚙️ Konfigurera App Settings
- Klicka på din app
- Klicka på **"⚙️ Settings"** (högst upp till höger)
- Välj **"Secrets"** från menyn

#### 3. 🔑 Lägg till Firebase Secrets
Kopiera och klistra in exakt denna text i "Secrets" fältet:

```toml
# Firebase konfiguration för AktivitusFinans
FIREBASE_PROJECT_ID = "aktivitusfinans"
FIREBASE_DATABASE_URL = "https://aktivitusfinans-default-rtdb.europe-west1.firebasedatabase.app"
FIREBASE_API_KEY = "AIzaSyCWgow5O8sklURfyJX2pf-MiltKlANMdrg"
FIREBASE_AUTH_DOMAIN = "aktivitusfinans.firebaseapp.com"
FIREBASE_STORAGE_BUCKET = "aktivitusfinans.firebasestorage.app"
FIREBASE_MESSAGING_SENDER_ID = "684415073315"
FIREBASE_APP_ID = "1:684415073315:web:262b76342bf4f320038596"
```

#### 4. 💾 Spara och Restarta
- Klicka **"Save"**
- Klicka **"Reboot app"** för att starta om appen

### ✅ Verifiering
Efter att du lagt till secrets ska appen:
- ✅ Starta utan fel
- ✅ Visa inloggningssidan
- ✅ Ansluta till Firebase korrekt

### 🔍 Felsökning
Om appen fortfarande inte fungerar:

1. **Kontrollera secrets formatting:**
   - Inga extra spaces före/efter `=`
   - Alla värden inom citattecken `""`
   - Korrekt TOML-format

2. **Kontrollera Firebase Realtime Database:**
   - Gå till Firebase Console
   - Kontrollera att Realtime Database är aktiverad
   - Kontrollera databas-URL:en

3. **Kontrollera Firebase Authentication:**
   - Gå till Firebase Console → Authentication
   - Kontrollera att Email/Password är aktiverad

### 📱 App-URL
När secrets är konfigurerade kommer appen att vara tillgänglig på:
`https://finansanalysupgrade-[random-string].streamlit.app`

### 🔒 Säkerhet
- `.streamlit/secrets.toml` är ignorerad i Git (inte pushad till GitHub)
- Secrets måste konfigureras manuellt i Streamlit Cloud Dashboard
- Firebase credentials är säkra och exponeras inte publikt

---

## 🚀 Quick Fix Checklist:

- [ ] Gå till Streamlit Cloud Dashboard
- [ ] Öppna app settings → Secrets
- [ ] Klistra in Firebase-konfigurationen ovan
- [ ] Spara och restarta appen
- [ ] Verifiera att appen startar utan fel

**Efter dessa steg ska appen fungera perfekt! 🎉**
