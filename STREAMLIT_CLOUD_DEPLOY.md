# 🚀 Streamlit Cloud Deployment Guide

## 📋 Steg-för-steg deployment

### 1. Förbered GitHub Repository

```bash
# Navigera till ditt projekt
cd "/Users/erik/Desktop/FinansAnalys Upgrade"

# Initiera git (om inte redan gjort)
git init

# Lägg till alla filer (utom de i .gitignore)
git add .

# Commit
git commit -m "Initial commit - Finansiell Analys App med Firebase Auth"

# Lägg till din GitHub remote
git remote add origin https://github.com/DITT_ANVÄNDARNAMN/finansiell-analys.git

# Push till GitHub
git push -u origin main
```

### 2. Streamlit Cloud Setup

1. **Gå till:** https://share.streamlit.io/
2. **Logga in** med ditt GitHub-konto
3. **Klicka "New app"**
4. **Välj ditt repository:** `finansiell-analys`
5. **Main file path:** `app.py`
6. **Klicka "Deploy"**

### 3. Konfigurera Secrets

I Streamlit Cloud, gå till **App settings → Secrets** och lägg till:

```toml
FIREBASE_PROJECT_ID = "finansanalys-c1a27"
FIREBASE_DATABASE_URL = "https://finansanalys-c1a27-default-rtdb.europe-west1.firebasedatabase.app"
FIREBASE_API_KEY = "AIzaSyBhsQoK0ltp3bLj84KhQRMBbgxw-qMj1R0"
FIREBASE_AUTH_DOMAIN = "finansanalys-c1a27.firebaseapp.com"
FIREBASE_STORAGE_BUCKET = "finansanalys-c1a27.appspot.com"
FIREBASE_MESSAGING_SENDER_ID = "394423457636"
FIREBASE_APP_ID = "1:394423457636:web:aedb913231ad86b646cc71"
```

## 🔒 Säkerhetsaspekter

### ✅ Vad som är säkert:
- **Firebase API Key** - kan vara publik (används för webb-appar)
- **Project ID** - kan vara publik
- **Auth Domain** - kan vara publik
- **App ID** - kan vara publik

### ⚠️ Viktigt att komma ihåg:
- **.env filen** ska ALDRIG commitas till GitHub
- **Säkerheten** ligger i Firebase Security Rules, inte i API-nyckeln
- **Användarkonton** skapas manuellt av dig

### 🛡️ Säkerhetslager:

1. **Firebase Security Rules:** Endast autentiserade användare kan läsa/skriva
2. **Manuell kontoskapning:** Du skapar alla konton själv
3. **Ingen registrering:** Ingen kan skapa konto via appen
4. **Session-hantering:** Automatisk utloggning vid timeout

## 🌐 Firebase Authorized Domains

**Viktigt:** Lägg till din Streamlit Cloud URL i Firebase:

1. Gå till [Firebase Console](https://console.firebase.google.com/project/finansanalys-c1a27)
2. **Authentication → Settings → Authorized domains**
3. **Lägg till:** `din-app-namn.streamlit.app`

Exempel: `finansiell-analys-erik.streamlit.app`

## 📁 Filstruktur för GitHub

```
finansiell-analys/
├── .gitignore                    # ✅ Viktigt!
├── app.py                        # ✅ Huvudfil
├── requirements.txt              # ✅ Dependencies
├── firebase-rules.json           # ✅ Säkerhetsregler
├── README.md                     # ✅ Dokumentation
├── STREAMLIT_CLOUD_DEPLOY.md     # ✅ Denna guide
├── src/
│   ├── models/
│   │   └── firebase_database.py  # ✅ Uppdaterad för cloud
│   ├── utils/
│   │   └── auth.py               # ✅ Uppdaterad för cloud
│   └── pages/
│       ├── auth.py               # ✅ Inloggningssida
│       ├── excel_view.py         # ✅ Alla sidor
│       └── visualization.py      # ✅ Alla sidor
├── .env                          # 🚫 Inte i GitHub!
└── env.local                     # 🚫 Inte i GitHub!
```

## 🔧 Funktioner som fungerar på Cloud

### ✅ Kommer att fungera:
- **Firebase Authentication** - fullständigt stöd
- **Realtime Database** - läsning och skrivning
- **Användarhantering** - inloggning/utloggning
- **Datavisualisering** - alla Plotly-diagram
- **Excel-import** - via upload-funktion
- **Alla applikationsfunktioner**

### ❌ Kommer INTE att fungera:
- **gcloud Application Default Credentials** - bara lokalt
- **Lokal filåtkomst** till Excel-filer på din dator
- **Streamlit file uploader** krävs för Excel-import

## 📊 Performance Tips

### Snabbare laddning:
- Cachat Firebase-anslutning
- Optimerade databasfrågor
- Komprimerade bilder och assets

### Minnesoptimering:
- Streamlit Cloud har begränsat minne
- Stora Excel-filer kan behöva optimering
- Cache viktiga beräkningar

## 🎯 Slutresultat

Efter deployment får du:

✅ **Offentlig URL:** `https://din-app.streamlit.app`  
✅ **Säker autentisering** med Firebase  
✅ **Automatisk deployment** vid GitHub push  
✅ **SSL-certifikat** och HTTPS  
✅ **Global tillgänglighet** 24/7  

**Din finansanalysapp är nu tillgänglig för alla med rätt inloggningsuppgifter!** 🌍

## 🚨 Troubleshooting

### Om appen inte startar:
1. Kontrollera **requirements.txt**
2. Kolla **Streamlit logs** för fel
3. Verifiera **secrets** är korrekta
4. Kontrollera **Firebase authorized domains**

### Om autentisering failar:
1. Lägg till **Streamlit domain** i Firebase
2. Kontrollera **Firebase API key** i secrets
3. Verifiera **Firebase project settings**
