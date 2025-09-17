# 🚀 Guide för att migrera alla flikar till Firebase

## 🎯 Vad som är klart:
✅ **Dynamisk sektions-detektion** - ETL hittar automatiskt intäkter/kostnader för varje flik  
✅ **Budgetsparandet** - Fungerar perfekt med debug-information  
✅ **Testresultat** - Verifierat på flera flikar med olika strukturer  

## 📊 Flikar som kommer migreras:
Du har **19 flikar** redo för migrering:

### KLAB (4 flikar):
- KLAB 2022, 2023, 2024, 2025

### KSAB (4 flikar):  
- KSAB 2022, 2023, 2024, 2025

### KMAB (4 flikar):
- KMAB 2022, 2023, 2024, 2025

### AAB (4 flikar):
- AAB 2022, 2023, 2024, 2025

### KFAB (3 flikar):
- KFAB 2023, 2024, 2025

## 🔧 Tre sätt att köra migreringen:

### Alternativ 1: I din lokala miljö
```bash
# Navigera till projektet
cd "/Users/erik/Desktop/FinansAnalys Upgrade"

# Kontrollera att Firebase är konfigurerat
cat .env

# Kör ETL för alla flikar
python src/etl/excel_to_firebase.py
```

### Alternativ 2: Via Streamlit-appen
1. Gå till appen på `http://localhost:8501`
2. Leta efter ETL/Import-funktioner i menyn
3. Kör migreringen via UI

### Alternativ 3: Steg-för-steg manuellt
Lägg upp flikar en i taget för bättre kontroll:

```python
# Exempel-kod för att köra specifika flikar
from src.etl.excel_to_firebase import ExcelToFirebaseETL

etl = ExcelToFirebaseETL("Finansiell Data.xlsx")

# Testa med en flik först
sheets_to_migrate = ["KSAB 2022", "KMAB 2022", "AAB 2022"]

for sheet in sheets_to_migrate:
    print(f"Migrerar {sheet}...")
    # ETL kommer automatiskt hitta rätt sektioner
```

## 🎯 Vad som kommer hända:

För varje flik kommer ETL att:

1. **🔍 Hitta sektioner automatiskt**
   - Scanna efter "RÖRELSENS INTÄKTER" och "RÖRELSENS KOSTNADER"
   - Identifiera start/slut-rader för varje sektion

2. **📊 Kategorisera konton korrekt**
   - Allt mellan intäkter-rubrikerna → **INTÄKTER**
   - Allt mellan kostnader-rubrikerna → **KOSTNADER**

3. **💾 Spara till Firebase**
   - Skapa företag (KLAB, KSAB, KMAB, AAB, KFAB)
   - Skapa datasets för varje år
   - Kategorisera och spara alla konton
   - Importera alla månadsvärden

## 📈 Förväntade resultat:

Baserat på våra tester:
- **KSAB 2022**: ~79 konton (16 intäkter + 63 kostnader)
- **KMAB 2022**: ~53 konton (8 intäkter + 45 kostnader)  
- **AAB 2022**: ~50 konton (16 intäkter + 34 kostnader)

**Totalt för alla 19 flikar: ~1000+ konton med fullständig månadsdata**

## 🚨 Innan du kör:

1. **Kontrollera Firebase-anslutning:**
   ```bash
   # Verifiera att .env innehåller korrekt Firebase-config
   cat .env
   ```

2. **Backup (valfritt):**
   - Ta backup av nuvarande Firebase-data om det finns viktig data

3. **Testskript för verifiering:**
   Du kan använda det här scriptet för att dubbelkolla att allt ser rätt ut innan full migrering.

## 🎉 Efter migreringen:

Du kommer ha:
- ✅ **5 företag** (KLAB, KSAB, KMAB, AAB, KFAB)
- ✅ **19 datasets** (ett för varje flik)
- ✅ **1000+ konton** korrekt kategoriserade
- ✅ **Fullständig månadsdata** för alla år
- ✅ **Fungerande budgetsystem** för alla företag och år

Är du redo att köra? Vilket alternativ föredrar du?
