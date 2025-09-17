"""
ETL-script för att konvertera Excel-data till Firebase Realtime Database
Körs manuellt innan app deployment
"""
import pandas as pd
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys
import os
from datetime import datetime

# Lägg till src-mappen i path för imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.insert(0, src_dir)

from models.firebase_database import FirebaseDB

class ExcelToFirebaseETL:
    def __init__(self, excel_path: str):
        self.excel_path = Path(excel_path)
        self.firebase_db = FirebaseDB()
        
        # Månadsmappning
        self.months = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'Maj': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Okt': 10, 'Nov': 11, 'Dec': 12,
            'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
            'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        
        # Mappningsregler för automatisk kategorisering
        self.revenue_keywords = [
            'intäkt', 'försäljning', 'membership', 'avgift', 'hyra', 'uthyrning',
            'revenue', 'income', 'sale', 'fee', 'rent', 'rental'
        ]
        
        self.expense_keywords = [
            'kostnad', 'utgift', 'lön', 'hyra', 'el', 'försäkring', 'material',
            'expense', 'cost', 'salary', 'wage', 'rent', 'electricity', 'insurance'
        ]

    def setup_database(self):
        """Initiera databas med grundläggande data"""
        print("🔄 Initierar Firebase databas...")
        self.firebase_db.init_database()
        print("✅ Firebase databas initierad")

    def read_excel_sheets(self) -> Dict[str, pd.DataFrame]:
        """Läs alla sheets från Excel-filen"""
        print(f"📖 Läser Excel-fil: {self.excel_path}")
        
        try:
            # PRODUKTIONSLÄGE: Läs ALLA sheets
            all_sheets = pd.ExcelFile(self.excel_path).sheet_names
            print(f"📋 Hittade {len(all_sheets)} flikar: {all_sheets}")
            
            excel_data = {}
            for sheet_name in all_sheets:
                print(f"📖 Läser: {sheet_name}")
                excel_data[sheet_name] = pd.read_excel(self.excel_path, sheet_name=sheet_name, header=None)
            
            print(f"✅ Läst {len(excel_data)} flikar")
            return excel_data
        except Exception as e:
            print(f"❌ Fel vid läsning av Excel: {e}")
            return {}

    def parse_sheet_name(self, sheet_name: str) -> Tuple[Optional[str], Optional[int]]:
        """Tolka sheet-namn för att extrahera företag och år"""
        # Exempel: "KLAB 2022", "Aktivitus AB 2023", "KMAB 2024"
        # Leta efter företagsnamn följt av år (4 siffror)
        match = re.search(r'^(.+?)\s+(\d{4})$', sheet_name.strip())
        if match:
            company_name = match.group(1).strip()
            year = int(match.group(2))
            print(f"   📋 Parsed: '{sheet_name}' → Företag: '{company_name}', År: {year}")
            return company_name, year
        
        print(f"   ⚠️ Kunde inte parsa sheet-namn: '{sheet_name}'")
        return None, None

    def find_data_start(self, df: pd.DataFrame) -> Tuple[int, List[Tuple[int, str]]]:
        """Hitta var den faktiska datan börjar och extrahera månadskolumner med positioner"""
        months_found = []
        start_row = None
        
        for idx, row in df.iterrows():
            # Leta efter månadsnamn i raderna
            row_months = []
            for col_idx, cell in enumerate(row):
                if pd.notna(cell) and str(cell).strip() in self.months:
                    row_months.append((col_idx, str(cell).strip()))
            
            # Om vi hittar månader, detta är förmodligen header-raden
            if len(row_months) >= 3:  # Minst 3 månader för att vara säker
                start_row = idx + 1
                months_found = sorted(row_months)  # (kolumn_index, månad_namn)
                break
        
        return start_row, months_found

    def clean_account_name(self, name: str) -> str:
        """Rensa kontonamn"""
        if pd.isna(name):
            return ""
        
        cleaned = str(name).strip()
        # Ta bort vanliga prefix/suffix
        cleaned = re.sub(r'^(Tot\s+|Total\s+)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+(Tot|Total)$', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned

    def find_sections(self, df: pd.DataFrame) -> Dict[str, Tuple[int, int]]:
        """
        Dynamiskt hitta start och slut för intäkter och kostnader sektioner
        Returnerar: {'intäkter': (start_row, end_row), 'kostnader': (start_row, end_row)}
        """
        sections = {}
        
        revenue_start = None
        revenue_end = None
        expense_start = None
        expense_end = None
        
        for idx, row in df.iterrows():
            col0 = str(df.iloc[idx, 0]).strip().upper() if pd.notna(df.iloc[idx, 0]) else ''
            
            # Leta efter intäkter sektion
            if 'RÖRELSENS INTÄKTER' in col0 and revenue_start is None:
                revenue_start = idx
                print(f"   🔍 Hittade RÖRELSENS INTÄKTER på rad {idx}")
            elif 'SUMMA RÖRELSENS INTÄKTER' in col0 and revenue_start is not None:
                revenue_end = idx
                print(f"   🔍 Hittade SUMMA RÖRELSENS INTÄKTER på rad {idx}")
                
            # Leta efter kostnader sektion
            elif 'RÖRELSENS KOSTNADER' in col0 and expense_start is None:
                expense_start = idx
                print(f"   🔍 Hittade RÖRELSENS KOSTNADER på rad {idx}")
            elif 'SUMMA RÖRELSENS KOSTNADER' in col0 and expense_start is not None:
                expense_end = idx
                print(f"   🔍 Hittade SUMMA RÖRELSENS KOSTNADER på rad {idx}")
        
        # Sätt sektioner om vi hittade start och slut
        if revenue_start is not None and revenue_end is not None:
            sections['intäkter'] = (revenue_start + 1, revenue_end - 1)
            print(f"   ✅ Intäkter sektion: rad {revenue_start + 1} till {revenue_end - 1}")
        
        if expense_start is not None and expense_end is not None:
            sections['kostnader'] = (expense_start + 1, expense_end - 1)
            print(f"   ✅ Kostnader sektion: rad {expense_start + 1} till {expense_end - 1}")
            
        return sections

    def categorize_account(self, account_name: str, row_index: int, sections: Dict[str, Tuple[int, int]]) -> str:
        """
        Dynamisk kategorisering baserat på sektioner som hittats i Excel-filen
        """
        # Kolla om raden är inom intäkter sektion
        if 'intäkter' in sections:
            start, end = sections['intäkter']
            if start <= row_index <= end:
                return "Intäkter"
        
        # Kolla om raden är inom kostnader sektion
        if 'kostnader' in sections:
            start, end = sections['kostnader']
            if start <= row_index <= end:
                return "Kostnader"
        
        # Fallback till nyckelord-baserad kategorisering
        name_lower = account_name.lower()
        
        # Kolla intäktsnyckelord
        for keyword in self.revenue_keywords:
            if keyword.lower() in name_lower:
                return "Intäkter"
        
        # Default till kostnader
        return "Kostnader"

    def process_sheet(self, sheet_name: str, df: pd.DataFrame) -> bool:
        """Processera ett enskilt sheet"""
        print(f"\n📋 Processar sheet: {sheet_name}")
        
        # Tolka sheet-namn
        company_name, year = self.parse_sheet_name(sheet_name)
        if not company_name or not year:
            print(f"⚠️ Kunde inte tolka sheet-namn: {sheet_name}")
            return False
        
        print(f"   Företag: {company_name}, År: {year}")
        
        # Hitta data-start
        start_row, months_found = self.find_data_start(df)
        if start_row is None:
            print(f"⚠️ Kunde inte hitta månadskolumner i {sheet_name}")
            return False
        
        print(f"   Månader hittade: {[month for _, month in months_found]}")
        print(f"   Data börjar på rad: {start_row}")
        
        # Hitta sektioner dynamiskt
        sections = self.find_sections(df)
        if not sections:
            print(f"   ⚠️ Kunde inte hitta intäkter/kostnader sektioner i {sheet_name}")
            return False
        
        # Skapa eller hämta företag
        companies = self.firebase_db.get_companies()
        company_id = None
        
        for cid, company_data in companies.items():
            if company_data.get('name') == company_name:
                company_id = cid
                break
        
        if not company_id:
            company_id = self.firebase_db.create_company(company_name, "Stockholm")
            print(f"   ✅ Skapat företag: {company_name} (ID: {company_id})")
        else:
            print(f"   ✅ Hittade befintligt företag: {company_name} (ID: {company_id})")
        
        # Skapa dataset
        dataset_name = f"{company_name} {year}"
        dataset_id = self.firebase_db.create_dataset(company_id, year, dataset_name)
        print(f"   ✅ Skapat dataset: {dataset_name} (ID: {dataset_id})")
        
        # Hämta kategorier
        categories = self.firebase_db.get_account_categories()
        revenue_category_id = None
        expense_category_id = None
        
        for cat_id, cat_data in categories.items():
            if cat_data.get('name') == 'Intäkter':
                revenue_category_id = cat_id
            elif cat_data.get('name') == 'Kostnader':
                expense_category_id = cat_id
        
        # Processera datarader
        processed_accounts = 0
        processed_values = 0
        
        for idx in range(start_row, len(df)):
            row = df.iloc[idx]
            
            # Första kolumnen är kontonamnet
            account_name = self.clean_account_name(row.iloc[0])
            if not account_name or account_name in ['', 'Tot', 'Total']:
                continue
            
            # Filtrera bort summerings-rader och rubriker
            name_upper = account_name.upper()
            skip_keywords = [
                'SUMMA', 'RÖRELSENS INTÄKTER', 'RÖRELSENS KOSTNADER', 
                'NETTOOMSÄTTNING', 'ÖVRIGA RÖRELSEINTÄKTER',
                'RÅVAROR OCH FÖRNÖDENHETER', 'ÖVRIGA EXTERNA KOSTNADER',
                'ÅRETS RESULTAT', 'BERÄKNAT RESULTAT'
            ]
            
            if any(keyword in name_upper for keyword in skip_keywords):
                print(f"   ⏭️ Hoppar över rubrik/summering: {account_name}")
                continue
            
            print(f"   📊 Processar konto: {account_name} (rad {idx})")
            
            # Kategorisera automatiskt baserat på dynamiska sektioner
            category_name = self.categorize_account(account_name, idx, sections)
            category_id = revenue_category_id if category_name == "Intäkter" else expense_category_id
            
            print(f"      → Kategoriserad som: {category_name}")
            
            # Skapa eller hämta konto
            accounts = self.firebase_db.get_accounts(category_id)
            account_id = None
            
            for acc_id, acc_data in accounts.items():
                if acc_data.get('name') == account_name:
                    account_id = acc_id
                    break
            
            if not account_id:
                account_id = self.firebase_db.create_account(account_name, category_id)
                print(f"      ✅ Skapat konto: {account_name} → {category_name}")
            
            # Skapa raw label och mappning
            raw_label_id = self.firebase_db.create_raw_label(account_name)
            self.firebase_db.create_account_mapping(raw_label_id, account_id, 1.0)
            
            # Processera månadsdata
            for col_idx, month_name in months_found:
                if col_idx < len(row):
                    value = row.iloc[col_idx]
                    
                    if pd.notna(value) and value != 0:
                        try:
                            # Hantera svenska decimalformat (komma → punkt)
                            if isinstance(value, str):
                                value_clean = value.replace(',', '.')
                            else:
                                value_clean = value
                            
                            amount = float(value_clean)
                            month_num = self.months[month_name]
                            
                            # Debug: visa värden som hittas
                            print(f"      {month_name}: {amount}")
                            
                            # Skapa värde
                            self.firebase_db.create_value(
                                dataset_id, account_id, month_num, "faktiskt", amount
                            )
                            processed_values += 1
                            
                        except (ValueError, TypeError) as e:
                            print(f"      ⚠️ Kunde inte konvertera {month_name}: {value} → {value_clean if 'value_clean' in locals() else 'N/A'} ({e})")
                            pass  # Hoppa över icke-numeriska värden
            
            processed_accounts += 1
        
        print(f"   ✅ Processat {processed_accounts} konton, {processed_values} värden")
        return True

    def run_etl(self):
        """Kör hela ETL-processen"""
        print("🚀 Startar Excel → Firebase ETL")
        
        # Kontrollera att Excel-filen finns
        if not self.excel_path.exists():
            print(f"❌ Excel-fil hittades inte: {self.excel_path}")
            return False
        
        # Setup databas
        self.setup_database()
        
        # Läs Excel-sheets
        excel_data = self.read_excel_sheets()
        if not excel_data:
            return False
        
        # Processera varje sheet
        success_count = 0
        total_sheets = len(excel_data)
        
        for sheet_name, df in excel_data.items():
            if self.process_sheet(sheet_name, df):
                success_count += 1
        
        # Sammanfattning
        print(f"\n📊 ETL Sammanfattning:")
        print(f"   Totalt sheets: {total_sheets}")
        print(f"   Framgångsrika: {success_count}")
        print(f"   Misslyckade: {total_sheets - success_count}")
        
        if success_count == total_sheets:
            print("✅ ETL slutförd framgångsrikt!")
            return True
        else:
            print("⚠️ ETL slutförd med varningar")
            return False

def main():
    """Huvudfunktion"""
    # Hitta Excel-filen i projektroten
    project_root = Path(__file__).parent.parent.parent
    excel_path = project_root / "Finansiell Data.xlsx"
    
    if not excel_path.exists():
        print(f"❌ Excel-fil hittades inte: {excel_path}")
        print("Se till att 'Finansiell Data.xlsx' finns i projektroten")
        return
    
    # Kör ETL
    etl = ExcelToFirebaseETL(str(excel_path))
    success = etl.run_etl()
    
    if success:
        print("\n🎉 Datan är nu redo för Firebase-appen!")
    else:
        print("\n❌ ETL misslyckades, kontrollera felen ovan")

if __name__ == "__main__":
    main()
