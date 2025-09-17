# 🚀 Enkel Firebase Setup (utan service account keys)

Eftersom du inte kan skapa nya service account keys, använder vi **Application Default Credentials** istället!

## 📋 Vad du behöver göra:

### 1. Aktivera Realtime Database
- ✅ Gå till [Firebase Console](https://console.firebase.google.com/project/finansanalys-c1a27)
- ✅ Klicka "Realtime Database" → "Create Database" 
- ✅ Välj "Start in test mode"
- ✅ Välj region `europe-west1`

### 2. Installera Google Cloud CLI
```bash
# På macOS med Homebrew
brew install google-cloud-sdk

# Eller ladda ner från: https://cloud.google.com/sdk/docs/install
```

### 3. Logga in med ditt Google-konto
```bash
gcloud auth login
gcloud config set project finansanalys-c1a27
gcloud auth application-default login
```

### 4. Förenkla .env filen
Skapa `.env` fil med bara dessa värden:
```env
# Bara dessa behövs för Application Default Credentials
FIREBASE_PROJECT_ID=finansanalys-c1a27
FIREBASE_DATABASE_URL=https://finansanalys-c1a27-default-rtdb.europe-west1.firebasedatabase.app

# Web config (för pyrebase4)
FIREBASE_API_KEY=AIzaSyBhsQoK0ltp3bLj84KhQRMBbgxw-qMj1R0
FIREBASE_AUTH_DOMAIN=finansanalys-c1a27.firebaseapp.com
FIREBASE_STORAGE_BUCKET=finansanalys-c1a27.appspot.com
FIREBASE_MESSAGING_SENDER_ID=394423457636
FIREBASE_APP_ID=1:394423457636:web:aedb913231ad86b646cc71
```

### 5. Kör setup
```bash
pip install -r requirements.txt
python src/etl/excel_to_firebase.py
streamlit run app.py
```

## 🔑 Hur det fungerar:

**Application Default Credentials** använder din Google-inloggning istället för service account keys. Det betyder:

- ✅ Inga känsliga keys att hantera
- ✅ Använder din befintliga Google-access
- ✅ Fungerar perfekt för utveckling
- ✅ Automatisk refresh av tokens

## 🚀 Fördelar:

- **Enklare setup** - bara gcloud login
- **Säkrare** - inga keys att läcka  
- **Automatiskt** - refresh av credentials

---

**Detta är den enklaste vägen framåt! 🎉**
