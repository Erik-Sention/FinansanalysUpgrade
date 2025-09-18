import streamlit as st
import pandas as pd
from datetime import datetime
from src.models.firebase_database import get_firebase_db

def load_budget_values(company_id: str, year: int = 2025):
    """Ladda budget-värden från BUDGET_DATABASE"""
    try:
        firebase_db = get_firebase_db()
        budget_ref = firebase_db.get_ref(f"BUDGET_DATABASE/{company_id}/{year}/accounts")
        data = budget_ref.get(firebase_db._get_token())
        
        if not (data and data.val()):
            return {}
        
        # Säker läsning från ny struktur
        budget_values = {}
        data_val = data.val()
        
        if isinstance(data_val, dict):
            for account_id, account_data in data_val.items():
                if isinstance(account_data, dict) and 'months' in account_data:
                    budget_values[account_id] = {}
                    months_data = account_data['months']
                    if isinstance(months_data, dict):
                        for month_idx, month_data in months_data.items():
                            if isinstance(month_data, dict):
                                budget_values[account_id][int(month_idx)] = month_data.get('budget_amount', 0)
        
        return budget_values
        
    except Exception as e:
        st.error(f"❌ Fel vid laddning av budget: {e}")
        return {}

def save_single_budget_value(company_id: str, year: int, account_id: str, account_name: str, category: str, month_idx: int, month_name: str, amount: float) -> bool:
    """Spara en enskild budget-cell direkt"""
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

def load_test_values(company_id: str, year: int = 2025):
    """Ladda test-värden för att få konton"""
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

def show_budget_page():
    """Visa dedikerad budget-sida"""
    st.title("💰 Budget-redigering")
    st.markdown("**Enkelt och överskådligt budgetverktyg**")
    
    # Hämta företag
    companies = load_test_companies()
    if not companies:
        st.warning("📭 Ingen Excel-data importerad ännu. Gå till 'Test Excel-import' först.")
        return
    
    # Välj företag
    company_options = {f"{c['name']} ({c['location']})": c['id'] for c in companies}
    
    selected_company_name = st.selectbox(
        "🏢 Välj företag:",
        list(company_options.keys()),
        key="budget_company_select"
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
    
    st.markdown(f"**År: {import_year}**")
    
    # Hämta konton från Excel-data
    values = load_test_values(selected_company_id, import_year)
    if not values:
        st.warning(f"Ingen data hittad för {selected_company_name}")
        return
    
    # Hämta kontonamn
    try:
        firebase_db = get_firebase_db()
        accounts_ref = firebase_db.get_ref("test_data/accounts")
        accounts_data = accounts_ref.get(firebase_db._get_token())
        
        account_names = {}
        if accounts_data and accounts_data.val():
            for acc_id, acc_data in accounts_data.val().items():
                account_names[acc_id] = acc_data.get('name', acc_id)
    except:
        account_names = {}
    
    # Organisera konton per kategori
    accounts_by_category = {'Intäkter': [], 'Kostnader': []}
    
    for account_id, month_values in values.items():
        account_name = account_names.get(account_id, account_id)
        
        # Bestäm kategori baserat på kontonamn
        account_lower = account_name.lower()
        if any(word in account_lower for word in ['försäljning', 'intäkt', 'revenue', 'upplupen', 'gruppträning', 'cykel', 'resor', 'autogenererade']):
            category = "Intäkter"
        else:
            category = "Kostnader"
        
        accounts_by_category[category].append({
            'id': account_id,
            'name': account_name,
            'category': category
        })
    
    # STEP 1: Välj kategori
    st.markdown("---")
    st.markdown("## 🎯 Steg 1: Välj kategori")
    
    tab1, tab2 = st.tabs(["💚 Intäkter", "💸 Kostnader"])
    
    with tab1:
        st.markdown("### Intäktskonton")
        for account in accounts_by_category['Intäkter']:
            if st.button(f"📊 {account['name']}", key=f"income_btn_{account['id']}", use_container_width=True):
                st.session_state.budget_selected_account = account['id']
                st.session_state.budget_selected_name = account['name']
                st.session_state.budget_selected_category = account['category']
                st.rerun()
    
    with tab2:
        st.markdown("### Kostnadskonton")
        for account in accounts_by_category['Kostnader']:
            if st.button(f"📊 {account['name']}", key=f"cost_btn_{account['id']}", use_container_width=True):
                st.session_state.budget_selected_account = account['id']
                st.session_state.budget_selected_name = account['name']
                st.session_state.budget_selected_category = account['category']
                st.rerun()
    
    # STEP 2: Redigera budget
    if hasattr(st.session_state, 'budget_selected_account'):
        account_id = st.session_state.budget_selected_account
        account_name = st.session_state.budget_selected_name
        category = st.session_state.budget_selected_category
        
        st.markdown("---")
        st.markdown("## ✏️ Steg 2: Redigera månadsbudget")
        
        # Stor tydlig header
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #4CAF50, #2196F3); padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h2 style="color: white; margin: 0;">📝 {account_name}</h2>
            <p style="color: white; margin: 5px 0; font-size: 18px;">Kategori: {category}</p>
            <p style="color: white; margin: 0; font-size: 14px;">Ändra värden nedan - sparas automatiskt!</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Hämta befintliga budget-värden
        budget_values = load_budget_values(selected_company_id, import_year)
        account_budget = budget_values.get(account_id, {})
        
        # Månadsredigering i 3 rader
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
        
        # Rad 1: Jan-Apr
        st.markdown("#### 🗓️ Kvartal 1")
        cols1 = st.columns(4)
        for i in range(4):
            month_name = months[i]
            month_idx = i + 1
            current_value = account_budget.get(month_idx, 0.0)
            
            with cols1[i]:
                new_value = st.number_input(
                    f"**{month_name}**",
                    value=float(current_value),
                    step=1000.0,
                    key=f"budget_q1_{account_id}_{month_idx}",
                    format="%.0f"
                )
                
                # Spara direkt om värdet ändrats
                if new_value != current_value:
                    if save_single_budget_value(selected_company_id, import_year, account_id, account_name, category, month_idx, month_name, new_value):
                        st.success(f"✅ Sparad!", icon="💾")
        
        # Rad 2: Maj-Aug
        st.markdown("#### 🗓️ Kvartal 2")
        cols2 = st.columns(4)
        for i in range(4, 8):
            month_name = months[i]
            month_idx = i + 1
            current_value = account_budget.get(month_idx, 0.0)
            
            with cols2[i-4]:
                new_value = st.number_input(
                    f"**{month_name}**",
                    value=float(current_value),
                    step=1000.0,
                    key=f"budget_q2_{account_id}_{month_idx}",
                    format="%.0f"
                )
                
                # Spara direkt om värdet ändrats
                if new_value != current_value:
                    if save_single_budget_value(selected_company_id, import_year, account_id, account_name, category, month_idx, month_name, new_value):
                        st.success(f"✅ Sparad!", icon="💾")
        
        # Rad 3: Sep-Dec
        st.markdown("#### 🗓️ Kvartal 3-4")
        cols3 = st.columns(4)
        for i in range(8, 12):
            month_name = months[i]
            month_idx = i + 1
            current_value = account_budget.get(month_idx, 0.0)
            
            with cols3[i-8]:
                new_value = st.number_input(
                    f"**{month_name}**",
                    value=float(current_value),
                    step=1000.0,
                    key=f"budget_q3_{account_id}_{month_idx}",
                    format="%.0f"
                )
                
                # Spara direkt om värdet ändrats
                if new_value != current_value:
                    if save_single_budget_value(selected_company_id, import_year, account_id, account_name, category, month_idx, month_name, new_value):
                        st.success(f"✅ Sparad!", icon="💾")
        
        # Knapp för att välja annat konto
        if st.button("🔄 Välj annat konto", type="primary"):
            if hasattr(st.session_state, 'budget_selected_account'):
                del st.session_state.budget_selected_account
                del st.session_state.budget_selected_name  
                del st.session_state.budget_selected_category
            st.rerun()
    
    else:
        st.info("👆 Välj ett konto ovan för att börja redigera budget")

if __name__ == "__main__":
    show_budget_page()
