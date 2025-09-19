"""
Test Excel-import till Firebase - 2 företag, 1 år
Sparas i separat "test_data" mapp som lätt kan rensas
"""
import streamlit as st
import pandas as pd
from models_firebase_database import get_firebase_db
from datetime import datetime
import io

def load_excel_data_correct(excel_file_path: str = "Finansiell Data.xlsx"):
    """
    Läs Excel-data RÄTT - från specifika sheets för bara 2 företag
    """
    try:
        # Läs Excel-filen och lista alla sheets
        excel_file = pd.ExcelFile(excel_file_path)
        all_sheets = excel_file.sheet_names
        
        st.info(f"📋 Hittade {len(all_sheets)} sheets: {all_sheets}")
        
        # Välj bara första 2 företag (KLAB och KSAB) och senaste året för varje
        target_companies = ['KLAB', 'KSAB']  # Bara första 2 företag
        selected_sheets = []
        
        for company in target_companies:
            # Hitta senaste året för detta företag
            company_sheets = [s for s in all_sheets if s.startswith(f"{company} ")]
            if company_sheets:
                # Sortera och ta senaste året
                latest_sheet = sorted(company_sheets)[-1]
                selected_sheets.append(latest_sheet)
        
        st.warning(f"🎯 VÄLJER BARA: {selected_sheets}")
        
        # Kombinera data från valda sheets
        combined_data = []
        
        for sheet_name in selected_sheets:
            st.info(f"📖 Läser sheet: {sheet_name}")
            
            # Parsa företag och år från sheet-namn
            parts = sheet_name.split(' ')
            company_name = parts[0]
            year = int(parts[1])
            
            # Läs sheet utan headers
            df = pd.read_excel(excel_file_path, sheet_name=sheet_name, header=None)
            
            # Hitta månadskolumner (denna logik från original ETL)
            months_found = []
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
            
            for idx, row in df.iterrows():
                row_months = []
                for col_idx, cell in enumerate(row):
                    if pd.notna(cell) and str(cell).strip() in month_names:
                        row_months.append((col_idx, str(cell).strip()))
                
                if len(row_months) >= 3:  # Minst 3 månader
                    months_found = sorted(row_months)
                    data_start_row = idx + 1
                    break
            
            if not months_found:
                st.warning(f"⚠️ Kunde inte hitta månader i {sheet_name}")
                continue
            
            st.success(f"✅ Hittade månader: {[m[1] for m in months_found]}")
            
            # Extrahera konton och data
            for row_idx in range(data_start_row, len(df)):
                row = df.iloc[row_idx]
                account_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
                
                # Skippa tomma rader och summor
                if (not account_name or 
                    account_name in ['', 'Tot', 'Total'] or
                    'SUMMA' in account_name.upper()):
                    continue
                
                # Skapa rad för kombinerad data
                data_row = {
                    'Företag': company_name,
                    'År': year,
                    'Konto': account_name,
                    'Kategori': 'Intäkter' if 'intäkt' in account_name.lower() or 'försäljning' in account_name.lower() else 'Kostnader'
                }
                
                # Lägg till månadsdata
                for col_idx, month_name in months_found:
                    if col_idx < len(row):
                        value = row.iloc[col_idx]
                        if pd.notna(value) and value != 0:
                            try:
                                # Hantera svenska decimalformat
                                if isinstance(value, str):
                                    value = value.replace(',', '.')
                                data_row[month_name] = float(value)
                            except:
                                data_row[month_name] = 0
                        else:
                            data_row[month_name] = 0
                
                combined_data.append(data_row)
        
        if combined_data:
            result_df = pd.DataFrame(combined_data)
            st.success(f"✅ Kombinerade data: {len(result_df)} rader från {len(selected_sheets)} sheets")
            st.write("**Kombinerad data:**")
            st.dataframe(result_df.head(10), use_container_width=True)
            return result_df
        else:
            st.error("❌ Ingen data extraherad från Excel")
            return None
        
    except Exception as e:
        st.error(f"❌ Fel vid läsning av Excel: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None

def find_excel_sections(df: pd.DataFrame) -> dict:
    """
    Hitta sektioner i Excel för intäkter och kostnader
    Returnerar: {'intäkter': (start_row, end_row), 'kostnader': (start_row, end_row)}
    """
    sections = {}
    
    revenue_start = None
    revenue_end = None
    expense_start = None
    expense_end = None
    
    for idx in range(len(df)):
        # Kolla första kolumnen för sektionsrubriker (behåll original för visning)
        cell_value = ""
        cell_value_lower = ""
        if len(df.columns) > 0 and idx < len(df):
            try:
                original_value = str(df.iloc[idx, 0]).strip() if pd.notna(df.iloc[idx, 0]) else ''
                cell_value = original_value  # För visning i print
                cell_value_lower = original_value.lower()  # För jämförelse
            except:
                continue
        
        # Vi behöver inte denna debug längre
        
        # Leta efter EXAKT vad som finns i Excel-filen
        if cell_value_lower == 'rörelsens intäkter' and revenue_start is None:
            revenue_start = idx
            print(f"✅ HITTADE RÖRELSENS INTÄKTER på rad {idx}")
        elif cell_value_lower == 'summa rörelsens intäkter' and revenue_start is not None:
            revenue_end = idx
            print(f"✅ HITTADE SUMMA RÖRELSENS INTÄKTER på rad {idx}")
            
        elif cell_value_lower == 'rörelsens kostnader' and expense_start is None:
            expense_start = idx
            print(f"✅ HITTADE RÖRELSENS KOSTNADER på rad {idx}")
        elif cell_value_lower == 'summa rörelsens kostnader' and expense_start is not None:
            expense_end = idx
            print(f"✅ HITTADE SUMMA RÖRELSENS KOSTNADER på rad {idx}")
    
    # Sätt sektioner om vi hittade start och slut
    if revenue_start is not None and revenue_end is not None:
        sections['intäkter'] = (revenue_start + 1, revenue_end - 1)
        print(f"✅ Intäkter sektion: rad {revenue_start + 1} till {revenue_end - 1}")
    
    if expense_start is not None and expense_end is not None:
        sections['kostnader'] = (expense_start + 1, expense_end - 1)
        print(f"✅ Kostnader sektion: rad {expense_start + 1} till {expense_end - 1}")
        
    return sections

def categorize_account_by_values(account_name: str, row_data, month_cols: list) -> str:
    """
    Kategorisera konto baserat på om värdena är positiva (intäkter) eller negativa (kostnader)
    """
    values = []
    
    # Samla alla månadsvärden för detta konto
    for month_col in month_cols:
        if month_col in row_data and pd.notna(row_data[month_col]):
            try:
                value = float(row_data[month_col])
                if value != 0:  # Ignorera nollvärden
                    values.append(value)
            except (ValueError, TypeError):
                continue
    
    if not values:
        print(f"   ⚠️ Inga värden hittade för {account_name}, defaultar till Kostnader")
        return "Kostnader"
    
    # Räkna positiva och negativa värden
    positive_count = sum(1 for v in values if v > 0)
    negative_count = sum(1 for v in values if v < 0)
    
    print(f"   📊 {account_name}: {positive_count} positiva, {negative_count} negativa värden")
    
    # Kategorisera baserat på majoritet av värden
    if positive_count > negative_count:
        return "Intäkter"
    elif negative_count > positive_count:
        return "Kostnader"
    else:
        # Om lika många positiva och negativa, kolla genomsnitt
        avg_value = sum(values) / len(values)
        if avg_value > 0:
            return "Intäkter"
        else:
            return "Kostnader"

def save_test_data_to_firebase(df: pd.DataFrame) -> bool:
    """
    Spara Excel-data till Firebase under "test_data" nod
    
    Args:
        df: DataFrame med finansiell data från Excel
        
    Returns:
        bool: True om sparning lyckades
    """
    try:
        firebase_db = get_firebase_db()
        
        st.info("🔍 Analyserar Excel-data...")
        st.write("**Kolumner hittade:**", list(df.columns))
        
        # Kategoriserar baserat på om värdena är positiva (intäkter) eller negativa (kostnader)
        st.info("📊 Kategoriserar baserat på värdenas tecken (positiva = intäkter, negativa = kostnader)")
        
        # Försök identifiera kolumner automatiskt
        company_col = None
        account_col = None
        category_col = None
        month_cols = []
        
        # Leta efter företagskolumn
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['företag', 'company', 'bolag']):
                company_col = col
                break
        
        # Leta efter kontokolumn  
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['konto', 'account', 'beskrivning']):
                account_col = col
                break
                
        # VI ANVÄNDER INTE KATEGORIKOLUMN - kategorin bestäms av position i Excel!
        category_col = None  # ALLTID None eftersom vi bestämmer kategori från position
        
        # Leta efter månadskolumner
        month_names = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec']
        for col in df.columns:
            if any(month in col.lower() for month in month_names):
                month_cols.append(col)
        
        st.info(f"🔍 Identifierade kolumner:")
        st.write(f"- Företag: {company_col}")
        st.write(f"- Konto: {account_col}")
        st.write(f"- Månader: {month_cols}")
        st.info("📍 Kategorier bestäms automatiskt från Excel-position (Intäkter/Kostnader sektioner)")
        
        if not company_col or not account_col:
            st.error("❌ Kunde inte identifiera företag- eller kontokolumner i Excel-filen")
            return False
        
        # Processa data först för att få companies_to_import
        company_id_map = {}
        account_id_map = {}
        category_id_map = {}
        
        # 1. Skapa företag (från kombinerade Excel-data)
        unique_companies = df[company_col].unique()
        st.info(f"🏢 Hittade {len(unique_companies)} företag: {list(unique_companies)}")
        
        # Data är redan filtrerad till 2 företag från Excel-läsningen
        companies_to_import = unique_companies
        st.success(f"✅ IMPORTERAR DESSA FÖRETAG: {list(companies_to_import)}")
        
        # Säkerställ att companies_to_import är definierad för senare användning
        if len(companies_to_import) == 0:
            st.error("❌ Inga företag att importera!")
            return False
        
        # Bestäm år från data (ta från första raden)
        import_year = df['År'].iloc[0] if 'År' in df.columns else 2025
        
        # Skapa test_data struktur
        test_data = {
            "meta": {
                "created_at": datetime.now().isoformat(),
                "description": f"Excel import från 2 företag för år {import_year}",
                "year": int(import_year),
                "companies_count": len(companies_to_import),
                "accounts_count": len(df),
                "excel_columns": list(df.columns),
                "imported_companies": list(companies_to_import)
            },
            "companies": {},
            "accounts": {},
            "categories": {},
            "values": {}
        }
        
        for i, company_name in enumerate(companies_to_import):
            if pd.notna(company_name):
                company_id = f"company_{i+1}"
                company_id_map[company_name] = company_id
                
                # Gissa location baserat på företagsnamn
                location = "Stockholm"  # Default
                if "KLAB" in str(company_name):
                    location = "Linköping"
                elif "KMAB" in str(company_name):
                    location = "Malmö"
                elif "AAB" in str(company_name):
                    location = "Göteborg"
                elif "KFAB" in str(company_name):
                    location = "Falun"
                
                test_data["companies"][company_id] = {
                    "name": str(company_name),
                    "location": location,
                    "created_at": datetime.now().isoformat()
                }
        
        # 2. Skapa kategorier (om kategorikolumn finns)
        if category_col:
            for i, category_name in enumerate(df[category_col].unique()):
                if pd.notna(category_name):
                    category_id = f"category_{i+1}"
                    category_id_map[category_name] = category_id
                    
                    test_data["categories"][category_id] = {
                        "name": str(category_name),
                        "description": f"Kategori för {str(category_name).lower()}",
                        "created_at": datetime.now().isoformat()
                    }
        else:
            # Skapa default kategorier
            default_categories = ["Intäkter", "Kostnader"]
            for i, category_name in enumerate(default_categories):
                category_id = f"category_{i+1}"
                category_id_map[category_name] = category_id
                
                test_data["categories"][category_id] = {
                    "name": category_name,
                    "description": f"Standard kategori för {category_name.lower()}",
                    "created_at": datetime.now().isoformat()
                }
        
        # 3. Skapa konton (data är redan filtrerad från Excel-läsningen)
        filtered_df = df  # Data är redan filtrerad till 2 företag
        st.info(f"📋 Processerar {len(filtered_df)} rader för företagen")
        
        for i, (original_index, row) in enumerate(filtered_df.iterrows()):
            if pd.notna(row[account_col]):
                account_id = f"account_{i+1}"
                account_name = str(row[account_col])
                account_id_map[account_name] = account_id
                
                # Bestäm kategori baserat på om värdena är positiva eller negativa
                category_name = categorize_account_by_values(account_name, row, month_cols)
                category_id = category_id_map.get(category_name, "category_2")
                
                # Debugg-info för ALLA konton
                print(f"💰 Konto: '{account_name}' → {category_name}")
                st.write(f"🔍 **{account_name}** → **{category_name}**")
                
                test_data["accounts"][account_id] = {
                    "name": account_name,
                    "category_id": category_id,
                    "company_id": company_id_map.get(row[company_col], "company_1"),
                    "created_at": datetime.now().isoformat()
                }
        
        # 4. Skapa värden från månadskolumner (BARA för de 2 företagen!)
        value_counter = 1
        
        for _, row in filtered_df.iterrows():
            if pd.notna(row[account_col]) and pd.notna(row[company_col]):
                account_name = str(row[account_col])
                account_id = account_id_map.get(account_name)
                company_id = company_id_map.get(row[company_col])
                
                if account_id and company_id:
                    # Gå igenom alla månadskolumner
                    for month_col in month_cols:
                        if pd.notna(row[month_col]) and row[month_col] != 0:
                            # Gissa månadsnummer från kolumnnamn
                            month_num = 1  # Default
                            month_col_lower = month_col.lower()
                            month_mapping = {
                                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'maj': 5, 'jun': 6,
                                'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12
                            }
                            
                            for month_name, month_idx in month_mapping.items():
                                if month_name in month_col_lower:
                                    month_num = month_idx
                                    break
                            
                            value_id = f"value_{value_counter}"
                            value_counter += 1
                            
                            test_data["values"][value_id] = {
                                "company_id": company_id,
                                "account_id": account_id,
                                "year": int(import_year),
                                "month": month_num,
                                "amount": float(row[month_col]),
                                "type": "actual",
                                "created_at": datetime.now().isoformat()
                            }
        
        # Spara till Firebase under test_data nod
        test_ref = firebase_db.get_ref("test_data")
        test_ref.set(test_data, firebase_db._get_token())
        
        # Visa kategoriseringssammanfattning
        category_counts = {}
        for account_data in test_data['accounts'].values():
            category_id = account_data['category_id']
            category_name = "Intäkter" if category_id == category_id_map.get("Intäkter") else "Kostnader"
            category_counts[category_name] = category_counts.get(category_name, 0) + 1
        
        st.success("✅ Test-data sparat till Firebase!")
        st.info(f"📊 **Sammanfattning:** {len(test_data['companies'])} företag, {len(test_data['accounts'])} konton, {len(test_data['values'])} värden")
        
        # Visa kategoriseringsresultat
        col1, col2 = st.columns(2)
        with col1:
            st.metric("💰 Intäkter", category_counts.get("Intäkter", 0))
        with col2:
            st.metric("💸 Kostnader", category_counts.get("Kostnader", 0))
        
        return True
        
    except Exception as e:
        st.error(f"❌ Fel vid sparande till Firebase: {e}")
        return False

def load_test_companies():
    """Ladda test-företag från Firebase"""
    try:
        firebase_db = get_firebase_db()
        companies_ref = firebase_db.get_ref("test_data/companies")
        data = companies_ref.get(firebase_db._get_token())
        
        if data and data.val():
            companies = []
            for company_id, company_data in data.val().items():
                companies.append({
                    'id': company_id,
                    'name': company_data['name'],
                    'location': company_data['location']
                })
            return companies
        return []
        
    except Exception as e:
        st.error(f"❌ Fel vid laddning av företag: {e}")
        return []

def load_test_accounts(company_id: str):
    """Ladda test-konton för ett företag"""
    try:
        firebase_db = get_firebase_db()
        accounts_ref = firebase_db.get_ref("test_data/accounts")
        categories_ref = firebase_db.get_ref("test_data/categories")
        
        accounts_data = accounts_ref.get(firebase_db._get_token())
        categories_data = categories_ref.get(firebase_db._get_token())
        
        if not (accounts_data and accounts_data.val()):
            return []
        
        # Skapa kategori-mappning
        categories = {}
        if categories_data and categories_data.val():
            for cat_id, cat_data in categories_data.val().items():
                categories[cat_id] = cat_data['name']
        
        # Filtrera konton för företag (enkel version)
        accounts = []
        for account_id, account_data in accounts_data.val().items():
            if account_data.get('company_id') == company_id:
                accounts.append({
                    'id': account_id,
                    'name': account_data['name'],
                    'category': categories.get(account_data.get('category_id', ''), 'Okänd'),
                    'category_id': account_data.get('category_id', '')
                })
        
        return accounts
        
    except Exception as e:
        st.error(f"❌ Fel vid laddning av konton: {e}")
        return []

def load_test_data_with_categories(company_id: str, year: int = 2025):
    """Ladda test-data med kategorier för ett företag och år - OPTIMERAD VERSION"""
    try:
        firebase_db = get_firebase_db()
        
        # Hämta ALLT på en gång från test_data root
        test_data_ref = firebase_db.get_ref("test_data")
        test_data = test_data_ref.get(firebase_db._get_token())
        
        if not test_data or not test_data.val():
            return pd.DataFrame()
        
        data_dict = test_data.val()
        values = data_dict.get('values', {})
        accounts = data_dict.get('accounts', {})
        categories = data_dict.get('categories', {})
        
        # Bygg DataFrame med kategorier
        data = []
        for value_id, value_data in values.items():
            if (value_data.get('company_id') == company_id and 
                value_data.get('year') == year):
                
                account_id = value_data.get('account_id')
                account_info = accounts.get(account_id, {})
                
                category_id = account_info.get('category_id')
                category_info = categories.get(category_id, {})
                
                data.append({
                    'Företag': company_id,
                    'År': year,
                    'Konto': account_info.get('name', 'Okänt'),
                    'Kategori': category_info.get('name', 'Okänd'),
                    'Månad': value_data.get('month'),
                    'Belopp': value_data.get('amount', 0)
                })
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Pivotera för att få månader som kolumner (använd månadsnummer som kolumner)
        df_pivot = df.pivot_table(
            index=['Företag', 'År', 'Konto', 'Kategori'], 
            columns='Månad', 
            values='Belopp', 
            fill_value=0
        ).reset_index()
        
        # Mappa månadsnummer till månadsnamn
        month_mapping = {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'Maj', 6: 'Jun',
            7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dec'
        }
        
        # Byt namn på kolumner från månadsnummer till månadsnamn
        df_pivot.columns = [month_mapping.get(col, col) if isinstance(col, int) and col in month_mapping else col for col in df_pivot.columns]
        
        # Lägg till månadskolumner i rätt ordning (om någon saknas)
        months_order = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
        for month in months_order:
            if month not in df_pivot.columns:
                df_pivot[month] = 0
        
        # Ordna kolumner (ta bort Företag och År-kolumnerna)
        final_columns = ['Konto', 'Kategori'] + months_order
        df_pivot = df_pivot[final_columns]
        
        return df_pivot
        
    except Exception as e:
        st.error(f"❌ Fel vid laddning av data med kategorier: {e}")
        return pd.DataFrame()

def load_test_values(company_id: str, year: int = 2025):
    """Ladda test-värden för ett företag och år"""
    try:
        firebase_db = get_firebase_db()
        values_ref = firebase_db.get_ref("test_data/values")
        data = values_ref.get(firebase_db._get_token())
        
        if not (data and data.val()):
            return {}
        
        # Filtrera värden för företag och år
        values = {}
        for value_id, value_data in data.val().items():
            if (value_data.get('company_id') == company_id and 
                value_data.get('year') == year):
                
                account_id = value_data.get('account_id')
                month = value_data.get('month')
                amount = value_data.get('amount', 0)
                
                if account_id not in values:
                    values[account_id] = {}
                values[account_id][month] = amount
        
        return values
        
    except Exception as e:
        st.error(f"❌ Fel vid laddning av värden: {e}")
        return {}

def load_budget_values(company_id: str, year: int = 2025):
    """Ladda budget-värden från BUDGET_DATABASE"""
    try:
        firebase_db = get_firebase_db()
        budget_ref = firebase_db.get_ref(f"BUDGET_DATABASE/{company_id}/{year}/accounts")
        data = budget_ref.get(firebase_db._get_token())
        
        if not (data and data.val()):
            return {}
        
        # Läs från ny struktur
        budget_values = {}
        for account_id, account_data in data.val().items():
            if 'months' in account_data:
                budget_values[account_id] = {}
                for month_idx, month_data in account_data['months'].items():
                    budget_values[account_id][int(month_idx)] = month_data.get('budget_amount', 0)
        
        return budget_values
        
    except Exception as e:
        st.error(f"❌ Fel vid laddning av budget: {e}")
        return {}

# Gamla komplicerade budget-funktionen borttagen - ersatt med save_single_budget_value

def save_single_budget_value(company_id: str, year: int, account_id: str, account_name: str, category: str, month_idx: int, month_name: str, amount: float) -> bool:
    """Spara en enskild budget-cell direkt (som test-input)"""
    try:
        firebase_db = get_firebase_db()
        
        # Enkel path för enskild cell
        budget_path = f"BUDGET_DATABASE/{company_id}/{year}/accounts/{account_id}/months/{month_idx}"
        budget_ref = firebase_db.get_ref(budget_path)
        
        if amount == 0 or amount == 0.0:
            # Ta bort 0-värden
            budget_ref.remove(firebase_db._get_token())
        else:
            # Spara värdet
            budget_ref.set({
                'account_name': account_name,
                'category': category,
                'month': month_idx,
                'month_name': month_name,
                'budget_amount': float(amount),
                'updated_at': datetime.now().isoformat()
            }, firebase_db._get_token())
        
        return True
        
    except Exception as e:
        st.error(f"❌ Fel vid sparande av {month_name}: {e}")
        return False

def clear_test_data():
    """Rensa ENDAST Excel test-data från Firebase (behåller budget)"""
    try:
        firebase_db = get_firebase_db()
        test_ref = firebase_db.get_ref("test_data")
        test_ref.remove(firebase_db._get_token())
        
        # RENSA INTE budget-data längre!
        # budget_ref = firebase_db.get_ref("test_budget_data")
        # budget_ref.remove(firebase_db._get_token())
        
        return True
    except Exception as e:
        st.error(f"❌ Fel vid rensning: {e}")
        return False

def clear_budget_data():
    """Rensa ENDAST budget-data från BUDGET_DATABASE"""
    try:
        firebase_db = get_firebase_db()
        budget_ref = firebase_db.get_ref("BUDGET_DATABASE")
        budget_ref.remove(firebase_db._get_token())
        return True
    except Exception as e:
        st.error(f"❌ Fel vid rensning av budget: {e}")
        return False

def show_excel_import_test():
    """Visa Excel-import test-sidan"""
    st.title("📊 Test: Excel-import till Firebase")
    st.markdown("Importera 2 företag och 1 år som test-data")
    
    # Info om testet
    with st.expander("ℹ️ Om detta test", expanded=False):
        st.markdown("""
        **Test-import:**
        - 🏢 **BARA första 2 företag** från din Excel-fil
        - 📅 **1 år**: 2024 (alla månader som finns)
        - 📋 **Konton**: Alla konton för de 2 företagen
        - 💾 **Sparas under**: `test_data/` i Firebase (lätt att rensa!)
        
        **Firebase-struktur:**
        ```
        test_data/
          ├── companies/
          ├── categories/
          ├── accounts/
          └── values/
        ```
        """)
    
    st.markdown("---")
    
    # Knappar för import
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📤 Läs och importera Excel-data", type="primary"):
            excel_df = load_excel_data_correct()
            
            if excel_df is not None and not excel_df.empty:
                with st.spinner("Importerar Excel-data till Firebase..."):
                    if save_test_data_to_firebase(excel_df):
                        st.success("✅ Excel-data importerad framgångsrikt!")
                        st.markdown("**Importerad data:**")
                        st.dataframe(excel_df, use_container_width=True)
                    else:
                        st.error("❌ Import misslyckades")
            else:
                st.error("❌ Kunde inte ladda Excel-data")
    
    with col2:
        if st.button("🗑️ Rensa test-data"):
            if clear_test_data():
                st.success("✅ Test-data rensad!")
            else:
                st.error("❌ Rensning misslyckades")
    
    with col3:
        if st.button("📋 Förhandsgranska Excel"):
            excel_df = load_excel_data_correct()
            if excel_df is not None and not excel_df.empty:
                st.success("✅ Excel-data laddad för förhandsgranskning")
            else:
                st.error("❌ Kunde inte ladda Excel-data")
    
    # Visa importerad data
    st.markdown("---")
    st.markdown("### 🔍 Importerad data")
    
    companies = load_test_companies()
    if companies:
        st.success(f"✅ {len(companies)} företag importerade")
        
        # Välj företag för att visa data
        company_options = {f"{c['name']} ({c['location']})": c['id'] for c in companies}
        
        if company_options:
            selected_company_name = st.selectbox(
                "Välj företag för att visa data:",
                list(company_options.keys())
            )
            selected_company_id = company_options[selected_company_name]
            
            # Hämta år från metadata
            try:
                firebase_db = get_firebase_db()
                meta_ref = firebase_db.get_ref("test_data/meta")
                meta_data = meta_ref.get(firebase_db._get_token())
                import_year = meta_data.val().get('year', 2025) if meta_data and meta_data.val() else 2025
            except:
                import_year = 2025
            
            # Ladda och visa all data med kategorier
            st.markdown(f"#### 📊 Data för {selected_company_name} (År: {import_year})")
            
            # Hämta data med kategorier
            df_with_categories = load_test_data_with_categories(selected_company_id, import_year)
            
            if not df_with_categories.empty:
                st.success(f"✅ Hittade data för {len(df_with_categories)} konton")
                st.dataframe(df_with_categories, use_container_width=True, height=400)
                st.info(f"📊 Visar {len(df_with_categories)} rader med finansiell data")
            else:
                st.warning(f"Ingen data hittad för {selected_company_name} år {import_year}")
                
                # Debug för att se vad som finns
                st.write("🔍 DEBUG: Kontrollerar vad som finns i databasen...")
                try:
                    firebase_db = get_firebase_db()
                    values_ref = firebase_db.get_ref("test_data/values")
                    all_values = values_ref.get(firebase_db._get_token())
                    
                    if all_values and all_values.val():
                        unique_companies = set()
                        unique_years = set()
                        for val_data in all_values.val().values():
                            unique_companies.add(val_data.get('company_id'))
                            unique_years.add(val_data.get('year'))
                        
                        st.write(f"📋 Company IDs i databasen: {list(unique_companies)}")
                        st.write(f"📋 År i databasen: {list(unique_years)}")
                        st.write(f"🎯 Söker efter: company_id='{selected_company_id}', year={import_year}")
                except Exception as e:
                    st.error(f"Debug fel: {e}")
            
            # BUDGET-SEKTION FLYTTAD TILL EGEN SIDA
            st.markdown("---")
            st.markdown("## 💰 Budget")
            st.info("💡 Budget-funktionen finns nu på egen sida! Gå till '💰 Budget-redigering' i sidmenyn.")
            
            if st.button("🚀 Gå till Budget-redigering", type="primary"):
                st.switch_page("Budget-redigering")
                
    else:
        st.info("📭 Ingen test-data importerad ännu")
        
        # Visa placeholder för budget även här
        st.markdown("---")
        st.markdown("## 💰 Budget")
        st.info("💡 Budget-funktionen finns nu på egen sida! Gå till '💰 Budget-redigering' i sidmenyn.")
        st.info("📭 Importera Excel-data först, sedan kan du skapa budget")

if __name__ == "__main__":
    show_excel_import_test()
