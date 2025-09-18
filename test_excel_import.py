"""
Test Excel-import till Firebase - 2 företag, 1 år
Sparas i separat "test_data" mapp som lätt kan rensas
"""
import streamlit as st
import pandas as pd
from models_firebase_database import get_firebase_db
from datetime import datetime
import io

def load_excel_data(excel_file_path: str = "Finansiell Data.xlsx"):
    """
    Läs riktiga Excel-data från filen
    """
    try:
        # Läs Excel-filen - testa olika sheets
        excel_file = pd.ExcelFile(excel_file_path)
        
        st.info(f"📋 Hittade sheets: {excel_file.sheet_names}")
        
        # Läs första sheetet som default
        df = pd.read_excel(excel_file_path, sheet_name=0)
        
        st.success(f"✅ Laddade {len(df)} rader från Excel")
        st.write("**Kolumner i Excel:**", list(df.columns))
        st.write("**Första 5 raderna:**")
        st.dataframe(df.head(), use_container_width=True)
        
        return df
        
    except Exception as e:
        st.error(f"❌ Fel vid läsning av Excel: {e}")
        st.warning("Skapar sample-data istället...")
        
        # Fallback till sample-data
        data = {
            'Företag': ['KLAB', 'KLAB', 'KSAB', 'KSAB'],
            'Konto': ['Försäljning', 'Kostnader', 'Försäljning', 'Kostnader'],
            'Kategori': ['Intäkter', 'Kostnader', 'Intäkter', 'Kostnader'],
            'Jan': [850000, -180000, 920000, -210000],
            'Feb': [780000, -180000, 850000, -210000]
        }
        return pd.DataFrame(data)

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
                
        # Leta efter kategorikolumn
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['kategori', 'category', 'typ']):
                category_col = col
                break
        
        # Leta efter månadskolumner
        month_names = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec']
        for col in df.columns:
            if any(month in col.lower() for month in month_names):
                month_cols.append(col)
        
        st.info(f"🔍 Identifierade kolumner:")
        st.write(f"- Företag: {company_col}")
        st.write(f"- Konto: {account_col}")
        st.write(f"- Kategori: {category_col}")
        st.write(f"- Månader: {month_cols}")
        
        if not company_col or not account_col:
            st.error("❌ Kunde inte identifiera företag- eller kontokolumner i Excel-filen")
            return False
        
        # Skapa test_data struktur
        test_data = {
            "meta": {
                "created_at": datetime.now().isoformat(),
                "description": f"TEST: Excel import från BARA 2 företag ({len(companies_to_import)} av {len(df[company_col].unique())})",
                "year": 2024,  # Anta 2024 för nu
                "companies_count": len(companies_to_import),
                "accounts_count": len(filtered_df),
                "excel_columns": list(df.columns),
                "imported_companies": list(companies_to_import)
            },
            "companies": {},
            "accounts": {},
            "categories": {},
            "values": {}
        }
        
        # Processa data
        company_id_map = {}
        account_id_map = {}
        category_id_map = {}
        
        # 1. Skapa företag (BARA DE FÖRSTA 2 för test!)
        unique_companies = df[company_col].unique()
        st.info(f"🏢 Hittade {len(unique_companies)} företag: {list(unique_companies)}")
        
        # Begränsa till bara första 2 företag för test
        companies_to_import = unique_companies[:2]
        st.warning(f"⚠️ IMPORTERAR BARA DE FÖRSTA 2: {list(companies_to_import)}")
        
        # Säkerställ att companies_to_import är definierad för senare användning
        if len(companies_to_import) == 0:
            st.error("❌ Inga företag att importera!")
            return False
        
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
        
        # 3. Skapa konton (BARA för de 2 valda företagen!)
        filtered_df = df[df[company_col].isin(companies_to_import)]
        st.info(f"📋 Filtrerade data: {len(filtered_df)} rader för de 2 företagen")
        
        for i, (_, row) in enumerate(filtered_df.iterrows()):
            if pd.notna(row[account_col]):
                account_id = f"account_{i+1}"
                account_name = str(row[account_col])
                account_id_map[account_name] = account_id
                
                # Bestäm kategori
                if category_col and pd.notna(row[category_col]):
                    category_id = category_id_map.get(row[category_col], "category_1")
                else:
                    # Gissa kategori baserat på kontonamn
                    account_lower = account_name.lower()
                    if any(word in account_lower for word in ['försäljning', 'intäkt', 'revenue']):
                        category_id = category_id_map.get("Intäkter", "category_1")
                    else:
                        category_id = category_id_map.get("Kostnader", "category_2")
                
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
                                "year": 2024,  # Anta 2024
                                "month": month_num,
                                "amount": float(row[month_col]),
                                "type": "actual",
                                "created_at": datetime.now().isoformat()
                            }
        
        # Spara till Firebase under test_data nod
        test_ref = firebase_db.get_ref("test_data")
        test_ref.set(test_data, firebase_db._get_token())
        
        return True
        
    except Exception as e:
        st.error(f"❌ Fel vid sparande till Firebase: {e}")
        return False

def load_test_companies():
    """Ladda test-företag från Firebase"""
    try:
        firebase_db = get_firebase_db()
        test_ref = firebase_db.get_ref("test_data/companies")
        data = test_ref.get(firebase_db._get_token())
        
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
        
        # Filtrera konton för företag
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

def load_test_values(company_id: str, year: int = 2024):
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

def clear_test_data():
    """Rensa all test-data från Firebase"""
    try:
        firebase_db = get_firebase_db()
        test_ref = firebase_db.get_ref("test_data")
        test_ref.remove(firebase_db._get_token())
        return True
    except Exception as e:
        st.error(f"❌ Fel vid rensning: {e}")
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
            excel_df = load_excel_data()
            
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
            excel_df = load_excel_data()
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
            
            # Visa konton för valt företag
            accounts = load_test_accounts(selected_company_id)
            if accounts:
                st.markdown(f"#### 📋 Konton för {selected_company_name}")
                
                # Skapa översikt-tabell
                overview_data = []
                values = load_test_values(selected_company_id, 2024)
                
                for account in accounts:
                    account_id = account['id']
                    row = {
                        'Konto': account['name'],
                        'Kategori': account['category']
                    }
                    
                    # Lägg till månadsdata
                    months = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun']
                    total = 0
                    for month_idx, month_name in enumerate(months, 1):
                        amount = values.get(account_id, {}).get(month_idx, 0)
                        row[month_name] = f"{amount:,.0f}" if amount != 0 else "-"
                        total += amount
                    
                    row['Totalt'] = f"{total:,.0f}"
                    overview_data.append(row)
                
                if overview_data:
                    overview_df = pd.DataFrame(overview_data)
                    st.dataframe(overview_df, use_container_width=True)
                else:
                    st.warning("Ingen data hittad för detta företag")
            else:
                st.warning("Inga konton hittade för detta företag")
    else:
        st.info("📭 Ingen test-data importerad ännu")

if __name__ == "__main__":
    show_excel_import_test()
