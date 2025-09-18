"""
Test Excel-import till Firebase - 2 företag, 1 år
Sparas i separat "test_data" mapp som lätt kan rensas
"""
import streamlit as st
import pandas as pd
from models_firebase_database import get_firebase_db
from datetime import datetime
import io

def create_sample_data():
    """
    Skapa test-data för 2 företag, 1 år (2024)
    """
    # Sample data för test
    data = {
        'Företag': ['KLAB', 'KLAB', 'KLAB', 'KLAB', 'KSAB', 'KSAB', 'KSAB', 'KSAB'],
        'Konto': ['Försäljning Linköping', 'Personalkostnader', 'Lokalhyra', 'Marknadsföring',
                  'Försäljning Stockholm', 'Personalkostnader', 'Lokalhyra', 'IT-kostnader'],
        'Kategori': ['Intäkter', 'Kostnader', 'Kostnader', 'Kostnader',
                     'Intäkter', 'Kostnader', 'Kostnader', 'Kostnader'],
        'Jan': [850000, -180000, -25000, -15000, 920000, -210000, -35000, -12000],
        'Feb': [780000, -180000, -25000, -18000, 850000, -210000, -35000, -14000],
        'Mar': [920000, -185000, -25000, -22000, 980000, -215000, -35000, -16000],
        'Apr': [890000, -185000, -25000, -20000, 940000, -215000, -35000, -15000],
        'Maj': [950000, -190000, -25000, -25000, 1020000, -220000, -35000, -18000],
        'Jun': [920000, -190000, -25000, -23000, 990000, -220000, -35000, -17000]
    }
    
    return pd.DataFrame(data)

def save_test_data_to_firebase(df: pd.DataFrame) -> bool:
    """
    Spara test-data till Firebase under "test_data" nod
    
    Args:
        df: DataFrame med finansiell data
        
    Returns:
        bool: True om sparning lyckades
    """
    try:
        firebase_db = get_firebase_db()
        
        # Skapa test_data struktur
        test_data = {
            "meta": {
                "created_at": datetime.now().isoformat(),
                "description": "Test Excel import - 2 företag, 1 år",
                "year": 2024,
                "companies_count": len(df['Företag'].unique()),
                "accounts_count": len(df)
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
        
        # 1. Skapa företag
        for i, company_name in enumerate(df['Företag'].unique()):
            company_id = f"company_{i+1}"
            company_id_map[company_name] = company_id
            
            test_data["companies"][company_id] = {
                "name": company_name,
                "location": "Linköping" if company_name == "KLAB" else "Stockholm",
                "created_at": datetime.now().isoformat()
            }
        
        # 2. Skapa kategorier
        for i, category_name in enumerate(df['Kategori'].unique()):
            category_id = f"category_{i+1}"
            category_id_map[category_name] = category_id
            
            test_data["categories"][category_id] = {
                "name": category_name,
                "description": f"Kategori för {category_name.lower()}",
                "created_at": datetime.now().isoformat()
            }
        
        # 3. Skapa konton
        for i, (_, row) in enumerate(df.iterrows()):
            account_id = f"account_{i+1}"
            account_id_map[row['Konto']] = account_id
            
            test_data["accounts"][account_id] = {
                "name": row['Konto'],
                "category_id": category_id_map[row['Kategori']],
                "company_id": company_id_map[row['Företag']],
                "created_at": datetime.now().isoformat()
            }
        
        # 4. Skapa värden (faktisk data för 2024)
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun']
        value_counter = 1
        
        for _, row in df.iterrows():
            account_id = account_id_map[row['Konto']]
            company_id = company_id_map[row['Företag']]
            
            for month_idx, month_name in enumerate(months, 1):
                if pd.notna(row[month_name]) and row[month_name] != 0:
                    value_id = f"value_{value_counter}"
                    value_counter += 1
                    
                    test_data["values"][value_id] = {
                        "company_id": company_id,
                        "account_id": account_id,
                        "year": 2024,
                        "month": month_idx,
                        "amount": float(row[month_name]),
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
        **Test-data:**
        - 🏢 **2 företag**: KLAB (Linköping), KSAB (Stockholm)
        - 📅 **1 år**: 2024 (Jan-Jun)
        - 📋 **Konton**: Försäljning, Personalkostnader, Lokalhyra, etc.
        - 💾 **Sparas under**: `test_data/` i Firebase
        
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
        if st.button("📤 Importera test-data", type="primary"):
            sample_df = create_sample_data()
            
            with st.spinner("Importerar data till Firebase..."):
                if save_test_data_to_firebase(sample_df):
                    st.success("✅ Test-data importerad framgångsrikt!")
                    st.dataframe(sample_df, use_container_width=True)
                else:
                    st.error("❌ Import misslyckades")
    
    with col2:
        if st.button("🗑️ Rensa test-data"):
            if clear_test_data():
                st.success("✅ Test-data rensad!")
            else:
                st.error("❌ Rensning misslyckades")
    
    with col3:
        if st.button("📋 Visa sample-data"):
            sample_df = create_sample_data()
            st.dataframe(sample_df, use_container_width=True)
    
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
