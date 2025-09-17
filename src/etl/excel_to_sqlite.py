"""
ETL-script för att konvertera Excel-data till SQLite
Körs manuellt innan app deployment
"""
import pandas as pd
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys
import os

# Lägg till src-mappen i path för imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.insert(0, src_dir)

from sqlmodel import Session, select
from models.database import (
    get_engine, create_tables, init_database,
    Company, Dataset, RawLabel, Account, AccountCategory, 
    AccountMapping, Value, Budget, BudgetValue
)

class ExcelToSQLiteETL:
    def __init__(self, excel_path: str, db_path: str = "data/app.db"):
        self.excel_path = Path(excel_path)
        self.db_path = Path(db_path)
        self.engine = None
        
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
        """Initiera databas och skapa tabeller"""
        print("Skapar databas och tabeller...")
        self.engine = init_database()
        print(f"Databas skapad: {self.db_path}")

    def parse_sheet_name(self, sheet_name: str) -> Tuple[Optional[str], Optional[int]]:
        """
        Parsa fliknamn för att extrahera företag och år
        Ex: "KLAB 2022" -> ("KLAB", 2022)
        """
        pattern = r'([A-Z]{3,4})\s*(\d{4})'
        match = re.search(pattern, sheet_name.upper())
        
        if match:
            company_name = match.group(1)
            year = int(match.group(2))
            return company_name, year
        
        print(f"Varning: Kunde inte parsa fliknamn '{sheet_name}'")
        return None, None

    def categorize_account(self, label: str) -> str:
        """
        Automatisk kategorisering baserat på etiketttext
        """
        label_lower = label.lower()
        
        # Kolla intäktsnyckelord först
        for keyword in self.revenue_keywords:
            if keyword in label_lower:
                return "Intäkter"
        
        # Sedan kostnadsnyckelord
        for keyword in self.expense_keywords:
            if keyword in label_lower:
                return "Kostnader"
        
        # Default: anta kostnad
        return "Kostnader"

    def get_or_create_company(self, session: Session, name: str) -> Company:
        """Hämta eller skapa företag"""
        company = session.exec(select(Company).where(Company.name == name)).first()
        if not company:
            company = Company(name=name)
            session.add(company)
            session.commit()
            session.refresh(company)
        return company

    def get_or_create_account(self, session: Session, label: str) -> Account:
        """Hämta eller skapa konto med automatisk kategorisering"""
        # Först kolla om raw_label finns
        raw_label = session.exec(select(RawLabel).where(RawLabel.label == label)).first()
        if not raw_label:
            raw_label = RawLabel(label=label)
            session.add(raw_label)
            session.commit()
        
        # Kolla om mappning redan finns
        mapping = session.exec(
            select(AccountMapping).where(AccountMapping.raw_label_id == raw_label.id)
        ).first()
        
        if mapping:
            return mapping.account
        
        # Skapa nytt konto med automatisk kategorisering
        category_name = self.categorize_account(label)
        category = session.exec(
            select(AccountCategory).where(AccountCategory.name == category_name)
        ).first()
        
        if not category:
            category = AccountCategory(name=category_name)
            session.add(category)
            session.commit()
            session.refresh(category)
        
        # Skapa konto
        account = Account(
            name=label,
            category_id=category.id,
            description=f"Importerat från Excel: {label}"
        )
        session.add(account)
        session.commit()
        session.refresh(account)
        
        # Skapa mappning
        mapping = AccountMapping(
            raw_label_id=raw_label.id,
            account_id=account.id,
            confidence=0.8  # Automatisk mappning
        )
        session.add(mapping)
        session.commit()
        
        return account

    def process_excel_sheet(self, sheet_name: str, df: pd.DataFrame) -> bool:
        """Bearbeta en Excel-flik"""
        print(f"Bearbetar flik: {sheet_name}")
        
        # Parsa företag och år
        company_name, year = self.parse_sheet_name(sheet_name)
        if not company_name or not year:
            return False
        
        # Hitta header-rad med månadsnamn (vanligtvis rad med "Jan", "Feb", etc.)
        header_row = None
        data_start_row = None
        
        for idx, row in df.iterrows():
            row_str = str(row.iloc[1:].values).lower()  # Skippa första kolumnen
            if 'jan' in row_str and 'feb' in row_str:
                header_row = idx
                data_start_row = idx + 1
                break
        
        if header_row is None:
            print(f"Kunde inte hitta header-rad i {sheet_name}")
            return False
        
        # Hämta månadsnamn från header-raden
        month_headers = df.iloc[header_row, 1:].values  # Skippa första kolumnen
        month_mapping = {}
        
        for col_idx, header in enumerate(month_headers, 1):
            header_str = str(header).strip()
            for month_name, month_int in self.months.items():
                if month_name.lower() in header_str.lower():
                    month_mapping[col_idx] = month_int
                    break
        
        print(f"Hittade månader: {month_mapping}")
        
        with Session(self.engine) as session:
            # Hämta eller skapa företag
            company = self.get_or_create_company(session, company_name)
            
            # Skapa dataset
            dataset = Dataset(
                company_id=company.id,
                year=year,
                name=sheet_name
            )
            session.add(dataset)
            session.commit()
            session.refresh(dataset)
            
            # Bearbeta data från data_start_row
            success_count = 0
            error_count = 0
            
            for idx in range(data_start_row, len(df)):
                try:
                    row = df.iloc[idx]
                    
                    # Första kolumnen är kontoetikett
                    account_label = str(row.iloc[0]).strip()
                    if not account_label or account_label in ['nan', 'NaN', '', 'None']:
                        continue
                    
                    # Skippa kategorihuvuden (oftast versaler eller speciella format)
                    if (account_label.isupper() and len(account_label) > 3) or \
                       any(x in account_label.lower() for x in ['totalt', 'summa', 'resultat', 'intäkter', 'kostnader']):
                        continue
                    
                    account = self.get_or_create_account(session, account_label)
                    
                    # Bearbeta månadsvärden
                    for col_idx, month_num in month_mapping.items():
                        try:
                            cell_value = row.iloc[col_idx]
                            if pd.isna(cell_value):
                                continue
                            
                            # Hantera svenska decimaler (komma)
                            if isinstance(cell_value, str):
                                cell_value = cell_value.replace(',', '.')
                            
                            try:
                                amount = float(cell_value)
                                if amount == 0:  # Skippa nollvärden
                                    continue
                            except (ValueError, TypeError):
                                continue
                            
                            # Bestäm värdetyp (faktiskt vs budget)
                            value_type = "faktiskt"  # Anta faktiska värden som default
                            
                            # Spara värde
                            value = Value(
                                dataset_id=dataset.id,
                                account_id=account.id,
                                month=month_num,
                                value_type=value_type,
                                amount=amount
                            )
                            session.add(value)
                            success_count += 1
                            
                        except Exception as e:
                            error_count += 1
                            print(f"Fel vid bearbetning av cell {account_label}, månad {month_num}: {e}")
                            continue
                
                except Exception as e:
                    error_count += 1
                    print(f"Fel vid bearbetning av rad {idx}: {e}")
                    continue
            
            session.commit()
            print(f"Flik {sheet_name}: {success_count} värden importerade, {error_count} fel")
            return True

    def run_etl(self):
        """Kör hela ETL-processen"""
        print(f"Startar ETL från {self.excel_path}")
        
        if not self.excel_path.exists():
            print(f"Fel: Excel-fil finns inte: {self.excel_path}")
            return False
        
        # Initiera databas
        self.setup_database()
        
        try:
            # Läs Excel-fil
            excel_file = pd.ExcelFile(self.excel_path)
            print(f"Hittade {len(excel_file.sheet_names)} flikar: {excel_file.sheet_names}")
            
            successful_sheets = 0
            
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    
                    if df.empty:
                        print(f"Varning: Tom flik {sheet_name}")
                        continue
                    
                    if self.process_excel_sheet(sheet_name, df):
                        successful_sheets += 1
                
                except Exception as e:
                    print(f"Fel vid bearbetning av flik {sheet_name}: {e}")
                    continue
            
            print(f"ETL slutförd: {successful_sheets} flikar framgångsrikt importerade")
            return successful_sheets > 0
        
        except Exception as e:
            print(f"Fel vid läsning av Excel-fil: {e}")
            return False

def main():
    """Huvudfunktion för ETL"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Konvertera Excel till SQLite')
    parser.add_argument('excel_file', help='Sökväg till Excel-fil')
    parser.add_argument('--db', default='data/app.db', help='Sökväg till SQLite-databas')
    
    args = parser.parse_args()
    
    etl = ExcelToSQLiteETL(args.excel_file, args.db)
    success = etl.run_etl()
    
    if success:
        print("ETL slutförd framgångsrikt!")
        return 0
    else:
        print("ETL misslyckades!")
        return 1

if __name__ == "__main__":
    exit(main())
