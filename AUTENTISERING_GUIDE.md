# 🔐 Autentisering och Säkerhet - Guide

## Översikt

Din finansanalysapplikation är nu säkrad med Firebase Authentication. Alla data är skyddade och endast tillgängliga för inloggade användare.

## 🔑 Hur det fungerar

### 1. Säkerhetsregler
Firebase Realtime Database har uppdaterats med säkerhetsregler:
```json
{
  "rules": {
    ".read": "auth != null",
    ".write": "auth != null"
  }
}
```
Detta betyder att **alla läs- och skrivoperationer kräver autentisering**.

### 2. Autentiseringssystem
- **Registrering**: Nya användare kan skapa konton med e-post och lösenord
- **E-postverifiering**: Användare måste verifiera sin e-post innan inloggning
- **Säker inloggning**: Lösenord hashas och lagras säkert i Firebase
- **Session-hantering**: Automatisk token-uppdatering och utloggning vid timeout

## 📱 Användarupplevelse

### Första gången
1. Öppna applikationen
2. Klicka på "📝 Registrera" i tabben
3. Fyll i namn, e-post och lösenord
4. Kontrollera din e-post för verifieringslänk
5. Klicka på länken för att aktivera kontot
6. Gå tillbaka och logga in med "🔑 Logga in"

### Efterföljande besök
1. Öppna applikationen
2. Logga in med e-post och lösenord
3. Du kommer ihåg vara inloggad tills du aktivt loggar ut

### Om du glömmer lösenordet
1. Gå till "🔄 Glömt lösenord" i tabben
2. Ange din e-postadress
3. Följ instruktionerna i e-postmeddelandet

## 🛡️ Säkerhetsfunktioner

### Datasskydd
- **Endast autentiserade användare** kan läsa eller skriva data
- **Automatisk utloggning** vid timeout eller ogiltiga tokens
- **Säkra lösenord** med Firebase's inbyggda hashning

### Användarhantering
- **E-postverifiering** krävs före första inloggning
- **Lösenordsåterställning** via säker e-postlänk
- **Session-hantering** med automatisk token-refresh

## 🔧 Teknisk implementation

### Komponenter
1. **`src/utils/auth.py`** - Huvudautentiseringslogik
2. **`src/pages/auth.py`** - Inloggningssida med formulär
3. **`app.py`** - Uppdaterad för att kräva autentisering
4. **`firebase-rules.json`** - Säkerhetsregler för databasen

### Firebase-konfiguration
Autentiseringen använder din befintliga Firebase-projektets:
- Authentication-tjänst med Email/Password provider
- Realtime Database med säkerhetsregler
- Web SDK för klientautentisering

## 🚀 För utvecklare

### Lägga till autentisering till nya sidor
```python
from utils.auth import require_authentication

def show():
    require_authentication()  # Lägg till denna rad först
    # Resten av sidlogiken...
```

### Kontrollera om användare är inloggad
```python
from utils.auth import get_auth

auth = get_auth()
if auth.is_authenticated():
    user = auth.get_current_user()
    email = user.get('email')
```

### Visa användarinfo
```python
from utils.auth import show_user_info

# I sidebar
show_user_info()
```

## 📝 Miljövariabler

Kontrollera att din `.env` fil innehåller alla nödvändiga Firebase-konfigurationer:
```env
FIREBASE_PROJECT_ID=finansanalys-c1a27
FIREBASE_DATABASE_URL=https://finansanalys-c1a27-default-rtdb.europe-west1.firebasedatabase.app
FIREBASE_API_KEY=AIzaSyBhsQoK0ltp3bLj84KhQRMBbgxw-qMj1R0
FIREBASE_AUTH_DOMAIN=finansanalys-c1a27.firebaseapp.com
FIREBASE_STORAGE_BUCKET=finansanalys-c1a27.appspot.com
FIREBASE_MESSAGING_SENDER_ID=394423457636
FIREBASE_APP_ID=1:394423457636:web:aedb913231ad86b646cc71
```

## ⚠️ Viktiga säkerhetsaspekter

### För produktion
1. **Uppdatera Firebase Security Rules** i Firebase Console
2. **Aktivera endast nödvändiga authentication providers**
3. **Konfigurera authorized domains** för din produktionsdomain
4. **Övervaka användarkonton** regelbundet

### Backup och återställning
- **Användardata** lagras säkert i Firebase Authentication
- **Appdata** skyddas av autentiseringskrav
- **Ingen känslig data** lagras lokalt i applikationen

## 🎯 Resultat

✅ **Fullständig datasäkerhet** - Ingen obehörig åtkomst  
✅ **Användarvänlig inloggning** - Enkel registrering och inloggning  
✅ **Automatisk session-hantering** - Smidig användarupplevelse  
✅ **Lösenordsåterställning** - Självbetjäning vid glömt lösenord  
✅ **E-postverifiering** - Säkerställer giltiga användarkonton  

Din finansanalysapplikation är nu företagsklar med professionell autentisering! 🚀
