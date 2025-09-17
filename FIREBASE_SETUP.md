# Firebase Setup Guide

## 🔥 Firebase Realtime Database Setup

### 1. Skapa Firebase Projekt

1. Gå till [Firebase Console](https://console.firebase.google.com/)
2. Klicka på "Add project" eller "Lägg till projekt"
3. Namnge ditt projekt (t.ex. "finansanalys-app")
4. Följ setup-guiden

### 2. Aktivera Realtime Database

1. I Firebase Console, gå till "Realtime Database" i sidomenyn
2. Klicka "Create Database"
3. Välj "Start in test mode" (du kan ändra säkerhetsregler senare)
4. Välj region (t.ex. "europe-west1")

### 3. Skapa Service Account

1. Gå till "Project Settings" (kugghjulet)
2. Gå till fliken "Service accounts"
3. Klicka "Generate new private key"
4. Ladda ner JSON-filen (detta är din service account key)

### 4. Hämta Web Config

1. I "Project Settings", gå till fliken "General"
2. Scrolla ner till "Your apps"
3. Klicka på "</>" ikonen för att lägga till en web app
4. Namnge appen och klicka "Register app"
5. Kopiera config-objektet som visas

### 5. Konfigurera Miljövariabler

Skapa en `.env` fil i projektroten baserat på `env.example`:

```bash
cp env.example .env
```

Uppdatera `.env` filen med dina Firebase credentials från service account JSON-filen:

```env
# Firebase Service Account (från nedladdad JSON-fil)
FIREBASE_TYPE=service_account
FIREBASE_PROJECT_ID=finansanalys-c1a27
FIREBASE_PRIVATE_KEY_ID=din-private-key-id-från-json
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\ndin-faktiska-private-key\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=din-service-account@finansanalys-c1a27.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=din-client-id-från-json
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
FIREBASE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/din-service-account%40finansanalys-c1a27.iam.gserviceaccount.com

# Firebase Realtime Database URL (uppdateras automatiskt när du aktiverar database)
FIREBASE_DATABASE_URL=https://finansanalys-c1a27-default-rtdb.europe-west1.firebasedatabase.app/

# Firebase Web Config (redan konfigurerat för ditt projekt)
FIREBASE_API_KEY=AIzaSyBhsQoK0ltp3bLj84KhQRMBbgxw-qMj1R0
FIREBASE_AUTH_DOMAIN=finansanalys-c1a27.firebaseapp.com
FIREBASE_STORAGE_BUCKET=finansanalys-c1a27.appspot.com
FIREBASE_MESSAGING_SENDER_ID=394423457636
FIREBASE_APP_ID=1:394423457636:web:aedb913231ad86b646cc71
```

**Viktigt:** Du behöver bara uppdatera service account-uppgifterna (private_key, private_key_id, client_email, client_id) från den JSON-fil du laddar ner i steg 3.

### 6. Installera Dependencies

```bash
pip install -r requirements.txt
```

### 7. Kör ETL för att ladda data

```bash
python src/etl/excel_to_firebase.py
```

### 8. Starta appen

```bash
streamlit run app.py
```

## 🔐 Säkerhetsregler (Rekommenderas för produktion)

I Firebase Console → Realtime Database → Rules, ersätt med:

```json
{
  "rules": {
    ".read": "auth != null",
    ".write": "auth != null"
  }
}
```

## 📊 Datastruktur i Firebase

```
finansanalys-app/
├── companies/
│   └── {company-id}/
│       ├── name: "KLAB"
│       ├── location: "Stockholm"
│       └── created_at: "2024-01-01T12:00:00Z"
├── datasets/
│   └── {dataset-id}/
│       ├── company_id: "{company-id}"
│       ├── year: 2022
│       ├── name: "KLAB 2022"
│       └── created_at: "2024-01-01T12:00:00Z"
├── account_categories/
│   └── {category-id}/
│       ├── name: "Intäkter"
│       └── description: "Alla intäktsposter"
├── accounts/
│   └── {account-id}/
│       ├── name: "Memberships"
│       ├── category_id: "{category-id}"
│       └── description: ""
├── values/
│   └── {value-id}/
│       ├── dataset_id: "{dataset-id}"
│       ├── account_id: "{account-id}"
│       ├── month: 1
│       ├── value_type: "faktiskt"
│       ├── amount: 50000
│       └── created_at: "2024-01-01T12:00:00Z"
└── budgets/
    └── {budget-id}/
        ├── company_id: "{company-id}"
        ├── year: 2025
        ├── name: "Budget 2025"
        ├── created_at: "2024-01-01T12:00:00Z"
        └── updated_at: "2024-01-01T12:00:00Z"
```

## 🚨 Viktiga Anteckningar

1. **Säkerhet**: .env-filen innehåller känsliga uppgifter - lägg aldrig till den i git
2. **Firebase Rules**: Standardreglerna är öppna för utveckling - ändra för produktion
3. **Backup**: Firebase har automatisk backup, men överväg export för viktiga data
4. **Kostnader**: Realtime Database debiteras per GB lagring och transfer
5. **Limits**: Realtime Database har begränsningar för samtidiga anslutningar

## 🔧 Felsökning

### Firebase Connection Error
- Kontrollera att `.env` filen har korrekta värden
- Verifiera att databasens URL stämmer
- Kontrollera att service account har rätt behörigheter

### Data Loading Issues  
- Kör `python src/etl/excel_to_firebase.py` för att ladda om data
- Kontrollera att Excel-filen finns på rätt plats
- Verifiera att sheet-namnen följer formatet "FÖRETAG ÅRTAL"

### Streamlit Errors
- Kontrollera att alla dependencies är installerade
- Starta om Streamlit efter miljövariabel-ändringar
- Rensa Streamlit cache: `streamlit cache clear`
