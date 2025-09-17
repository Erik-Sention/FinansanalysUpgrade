# 📊 Finansiell Analys - Streamlit App

En professionell finansiell analysapp byggd med Streamlit som använder SQLite som databas för att analysera företagsdata från Excel.

## 🎯 Funktioner

- **📈 Dashboard**: Översikt av nyckeltal, intäkter, kostnader och resultat
- **📋 P&L (Resultaträkning)**: Detaljerad resultaträkning med månadsvis data
- **💰 Budget**: Skapa och redigera budgetar för olika företag och år
- **🔗 Kategorimappning**: Hantera mappning mellan Excel-etiketter och kontokategorier
- **📈 Säsongsfaktorer**: Analysera och redigera säsongsvariation
- **📄 Export**: Exportera data till Excel/CSV

## 🏗️ Arkitektur

- **Frontend**: Streamlit (Python)
- **Databas**: SQLite (lokal fil)
- **ORM**: SQLModel/SQLAlchemy
- **Visualisering**: Plotly
- **Excel-hantering**: pandas + openpyxl

## 📁 Projektstruktur

```
FinansAnalys Upgrade/
├── app.py                      # Huvudapplikation
├── requirements.txt            # Python-dependencies
├── data/
│   └── app.db                 # SQLite-databas
├── src/
│   ├── models/
│   │   └── database.py        # Databasmodeller
│   ├── etl/
│   │   └── excel_to_sqlite.py # ETL-script
│   ├── pages/
│   │   ├── dashboard.py       # Dashboard-sida
│   │   ├── pnl.py            # P&L-sida
│   │   ├── budget.py         # Budget-editor
│   │   ├── mapping.py        # Kategorimappning
│   │   └── seasonality.py    # Säsongsfaktorer
│   └── utils/
│       └── database_helpers.py # Hjälpfunktioner
└── Finansiell Data.xlsx       # Excel-källa
```

## 🚀 Installation och Användning

### 1. Installera dependencies

```bash
pip install -r requirements.txt
```

### 2. Kör ETL för att importera Excel-data

```bash
python src/etl/excel_to_sqlite.py "Finansiell Data.xlsx"
```

### 3. Starta Streamlit-appen

```bash
streamlit run app.py
```

Appen öppnas automatiskt i din webbläsare på `http://localhost:8501`

## 📊 Datamodell

### Kärnentiteter

- **Companies**: Företagsinformation
- **Datasets**: Dataset per företag och år
- **Accounts**: Konton (intäkter/kostnader)
- **Values**: Månadsvärden (faktiskt/budget)
- **Budgets**: Manuellt skapade budgetar
- **SeasonalityIndices**: Säsongsfaktorer

### Excel-format

Appen förväntar sig Excel-filer med:
- Flikar namngivna som `{FÖRETAG} {ÅR}` (ex: "KLAB 2022")
- Header-rad med månadsnamn (Jan, Feb, Mar, etc.)
- Första kolumnen innehåller kontonamn
- Påföljande kolumner innehåller månadsvärden

## 🔧 ETL-process

ETL-scriptet (`excel_to_sqlite.py`) hanterar:

1. **Parsing av fliknamn** för att extrahera företag och år
2. **Automatisk header-igenkänning** för månadskolumner
3. **Kategorisering av konton** baserat på nyckelord
4. **Datavalidering och rensning**
5. **Lagring i normaliserad SQLite-databas**

### Automatisk kategorisering

- **Intäkter**: "intäkt", "försäljning", "membership", "avgift", "uthyrning"
- **Kostnader**: "kostnad", "utgift", "lön", "hyra", "el", "försäkring"

## 📈 Funktionalitet per sida

### Dashboard
- KPI-kort med totaler
- Månatliga diagram (intäkter vs kostnader)
- YTD-trender
- Top 10 intäkts-/kostnadsposter

### P&L (Resultaträkning)
- Detaljerad månadsvis resultaträkning
- Jämförelse faktiskt vs budget
- Export till Excel
- Filterning per företag och år

### Budget
- Skapa/redigera budgetar
- Kopiera från föregående år
- Månadsvis input per konto
- Realtids-sammanfattning

### Kategorimappning
- Hantera mappning Excel → Kontokategorier
- Automatisk vs manuell mappning
- Konfidensgrad för mappningar
- Skapa nya konton

### Säsongsfaktorer
- Automatisk beräkning från historisk data
- Manuell redigering av faktorer
- Visualisering av säsongsmönster
- Support för åren 2022-2024

## 🌐 Deployment

### Lokal deployment
Följ installationsinstruktionerna ovan.

### Streamlit Cloud
1. Ladda upp projektet till GitHub
2. Inkludera `app.db` i repository
3. Anslut till Streamlit Cloud
4. Appen deployas automatiskt

### Docker (valfritt)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## 🛠️ Utveckling

### Lägga till nya sidor
1. Skapa ny fil i `src/pages/`
2. Implementera `show()` funktion
3. Importera och lägg till i `app.py`

### Uppdatera datamodell
1. Ändra modeller i `src/models/database.py`
2. Kör migration eller återskapa databas
3. Uppdatera ETL-script vid behov

### Anpassning för nya Excel-format
Uppdatera `process_excel_sheet()` i `src/etl/excel_to_sqlite.py`

## 📋 Krav och kompatibilitet

- **Python**: 3.9+
- **Webbläsare**: Chrome, Firefox, Safari, Edge
- **Excel**: .xlsx format (Office 2007+)
- **OS**: Windows, macOS, Linux

## 🐛 Felsökning

### Vanliga problem

**Import misslyckas**
- Kontrollera Excel-filformat
- Verifiera att flikar följer namnkonvention
- Kolla att månadsheaders finns

**Appen startar inte**
- Kontrollera att alla dependencies är installerade
- Verifiera att `data/app.db` finns
- Kör ETL-script först

**Inga data visas**
- Kontrollera att ETL-import lyckades
- Välj korrekt företag och år i dropdown

## 📞 Support

För teknisk support eller frågor, kontakta utvecklingsteamet.

## 📄 Licens

Internt verktyg - Alla rättigheter förbehållna.
