import streamlit as st
import pandas as pd
from datetime import datetime
from utils_firebase_helpers import get_firebase_db

def load_companies_and_years():
    """Hämta alla företag och år från Excel-data"""
    try:
        firebase_db = get_firebase_db()
        
        # Hämta företag
        companies_ref = firebase_db.get_ref("test_data/companies")
        companies_data = companies_ref.get(firebase_db._get_token())
        
        # Hämta konton för att se vilka företag som har data
        accounts_ref = firebase_db.get_ref("test_data/accounts")
        accounts_data = accounts_ref.get(firebase_db._get_token())
        
        # Hämta år från metadata
        meta_ref = firebase_db.get_ref("test_data/meta")
        meta_data = meta_ref.get(firebase_db._get_token())
        year = meta_data.val().get('year', 2025) if meta_data and meta_data.val() else 2025
        
        companies = []
        if companies_data and companies_data.val():
            for company_id, company_info in companies_data.val().items():
                companies.append({
                    'id': company_id,
                    'name': company_info['name'],
                    'location': company_info['location'],
                    'display_name': f"{company_info['name']} ({company_info['location']})"
                })
        
        return companies, year
        
    except Exception as e:
        st.error(f"❌ Fel vid laddning av företag: {e}")
        return [], 2025

def load_accounts_for_company(company_id: str):
    """Hämta alla konton för ett specifikt företag"""
    try:
        firebase_db = get_firebase_db()
        
        # Hämta alla konton
        accounts_ref = firebase_db.get_ref("test_data/accounts")
        accounts_data = accounts_ref.get(firebase_db._get_token())
        
        accounts = []
        if accounts_data and accounts_data.val():
            for account_id, account_info in accounts_data.val().items():
                if account_info.get('company_id') == company_id:
                    accounts.append({
                        'id': account_id,
                        'name': account_info['name']
                    })
        
        return accounts
        
    except Exception as e:
        st.error(f"❌ Fel vid laddning av konton: {e}")
        return []

def save_simple_budget(company_name: str, year: int, account_name: str, monthly_values: dict):
    """Spara budget med ENKLA namn i Firebase"""
    try:
        firebase_db = get_firebase_db()
        
        # ENKEL path med riktiga namn
        budget_path = f"SIMPLE_BUDGETS/{company_name}/{year}/{account_name}"
        budget_ref = firebase_db.get_ref(budget_path)
        
        # Spara med månadsnamn istället för siffror
        budget_data = {
            'company': company_name,
            'year': year,
            'account': account_name,
            'created_at': datetime.now().isoformat(),
            'monthly_values': {
                'Jan': monthly_values.get('Jan', 0),
                'Feb': monthly_values.get('Feb', 0),
                'Mar': monthly_values.get('Mar', 0),
                'Apr': monthly_values.get('Apr', 0),
                'Maj': monthly_values.get('Maj', 0),
                'Jun': monthly_values.get('Jun', 0),
                'Jul': monthly_values.get('Jul', 0),
                'Aug': monthly_values.get('Aug', 0),
                'Sep': monthly_values.get('Sep', 0),
                'Okt': monthly_values.get('Okt', 0),
                'Nov': monthly_values.get('Nov', 0),
                'Dec': monthly_values.get('Dec', 0)
            }
        }
        
        budget_ref.set(budget_data, firebase_db._get_token())
        return True
        
    except Exception as e:
        st.error(f"❌ Fel vid sparande: {e}")
        return False

def load_simple_budget(company_name: str, year: int, account_name: str):
    """Ladda budget med ENKLA namn"""
    try:
        firebase_db = get_firebase_db()
        
        # ENKEL path med riktiga namn
        budget_path = f"SIMPLE_BUDGETS/{company_name}/{year}/{account_name}"
        budget_ref = firebase_db.get_ref(budget_path)
        data = budget_ref.get(firebase_db._get_token())
        
        if data and data.val():
            return data.val().get('monthly_values', {})
        return {}
        
    except Exception as e:
        st.error(f"❌ Fel vid laddning: {e}")
        return {}

def show_simple_budget_page():
    """Visa ENKEL budget-sida"""
    st.title("📊 Budgethantering")
    st.markdown("Skapa och hantera budgetar för företagets konton")
    
    # STEG 1: Ladda företag och år
    companies, year = load_companies_and_years()
    
    if not companies:
        st.warning("📭 Ingen Excel-data importerad. Gå till 'Test Excel-import' först.")
        return
    
    st.markdown("### 1. Välj företag")
    
    # Dropdown med företagsnamn
    company_options = {company['display_name']: company for company in companies}
    selected_company_display = st.selectbox(
        "Välj företag:",
        list(company_options.keys()),
        key="simple_company_select"
    )
    
    selected_company = company_options[selected_company_display]
    company_id = selected_company['id']
    company_name = selected_company['name']
    
    st.info(f"Valt företag: **{company_name}** | År: **{year}**")
    
    # STEG 2: Välj konto
    st.markdown("### 2. Välj konto")
    
    accounts = load_accounts_for_company(company_id)
    if not accounts:
        st.warning(f"Inga konton hittade för {company_name}")
        return
    
    # Dropdown med kontonamn
    account_options = {account['name']: account for account in accounts}
    selected_account_name = st.selectbox(
        "Välj konto att skapa budget för:",
        list(account_options.keys()),
        key="simple_account_select"
    )
    
    selected_account = account_options[selected_account_name]
    
    st.info(f"Valt konto: **{selected_account_name}**")
    
    # STEG 3: Redigera månadsbudget
    st.markdown("### 3. Ange månadsbudget")
    
    # Ladda befintlig budget om den finns
    existing_budget = load_simple_budget(company_name, year, selected_account_name)
    
    # 12 input-fält för månader i korrekt ordning (Jan-Dec)
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
    monthly_values = {}
    
    # Dela upp i 3 rader med 4 månader per rad
    # Rad 1: Jan-Apr
    st.markdown("#### Q1 (Kvartal 1)")
    cols1 = st.columns(4)
    for i in range(4):
        month = months[i]
        with cols1[i]:
            current_value = existing_budget.get(month, 0)
            monthly_values[month] = st.number_input(
                f"{month}",
                value=float(current_value),
                step=1000.0,
                key=f"simple_budget_{month}",
                format="%.0f"
            )
    
    # Rad 2: Maj-Aug
    st.markdown("#### Q2 (Kvartal 2)")
    cols2 = st.columns(4)
    for i in range(4, 8):
        month = months[i]
        with cols2[i-4]:
            current_value = existing_budget.get(month, 0)
            monthly_values[month] = st.number_input(
                f"{month}",
                value=float(current_value),
                step=1000.0,
                key=f"simple_budget_{month}",
                format="%.0f"
            )
    
    # Rad 3: Sep-Dec
    st.markdown("#### Q3-Q4 (Kvartal 3-4)")
    cols3 = st.columns(4)
    for i in range(8, 12):
        month = months[i]
        with cols3[i-8]:
            current_value = existing_budget.get(month, 0)
            monthly_values[month] = st.number_input(
                f"{month}",
                value=float(current_value),
                step=1000.0,
                key=f"simple_budget_{month}",
                format="%.0f"
            )
    
    # SPARA-knapp
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col2:
        if st.button("Spara budget", type="primary", use_container_width=True):
            if save_simple_budget(company_name, year, selected_account_name, monthly_values):
                st.success("Budget har sparats")
            else:
                st.error("Fel vid sparande av budget")
    
    # Visa befintliga budgetar
    if existing_budget and any(v != 0 for v in existing_budget.values()):
        st.markdown("---")
        st.markdown("### Aktuell budget")
        
        # Visa i tabell-format med rätt månadsordning
        ordered_budget = {}
        for month in months:
            ordered_budget[month] = existing_budget.get(month, 0)
        
        budget_df = pd.DataFrame([ordered_budget])
        st.dataframe(budget_df, use_container_width=True)
        
        # Räkna ut totaler
        total = sum(existing_budget.values())
        st.metric("Total årsbudget", f"{total:,.0f} kr")

if __name__ == "__main__":
    show_simple_budget_page()
