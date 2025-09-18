"""
Excel-liknande vy för säsongsfaktorer och budgetredigering
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Path setup för både lokal och Streamlit Cloud deployment
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

from utils_firebase_helpers import (
    get_companies, get_years_for_company, get_financial_data, 
    get_account_categories, get_company_by_id
)
from models_firebase_database import get_firebase_db

def get_financial_data_with_categories(company_id, year):
    """Hämta finansiell data med kategorier för företag och år"""
    try:
        firebase_db = get_firebase_db()
        
        # Hämta datasets för företaget och året
        datasets = firebase_db.get_datasets(company_id)
        target_dataset_id = None
        for dataset_id, dataset_data in datasets.items():
            if dataset_data.get('year') == year:
                target_dataset_id = dataset_id
                break
        
        if not target_dataset_id:
            return pd.DataFrame()
        
        # Hämta värden för dataset
        values = firebase_db.get_values(dataset_id=target_dataset_id)
        
        # Hämta referensdata
        accounts = firebase_db.get_accounts()
        categories = firebase_db.get_account_categories()
        
        # Bygg DataFrame
        data = []
        for value_id, value_data in values.items():
            if value_data.get('value_type') != 'faktiskt':
                continue
                
            account_id = value_data.get('account_id')
            account_data = accounts.get(account_id, {})
            
            category_id = account_data.get('category_id')
            category_data = categories.get(category_id, {})
            
            data.append({
                'account_name': account_data.get('name', 'Okänt konto'),
                'category': category_data.get('name', 'Okänd kategori'),
                'month': value_data.get('month'),
                'amount': value_data.get('amount', 0),
                'account_id': account_id,
                'category_id': category_id
            })
        
        df = pd.DataFrame(data)
        
        if not df.empty:
            df = df.sort_values(['category', 'account_name', 'month'])
        
        return df
    except Exception as e:
        st.error(f"Fel vid hämtning av data: {e}")
        return pd.DataFrame()

def get_budget_data(company_id, year):
    """Hämta budgetdata från senaste budgeten"""
    try:
        firebase_db = get_firebase_db()
        
        # Hämta budgetar för företaget och året
        budgets = firebase_db.get_budgets(company_id)
        
        # Hitta senaste budget för året
        target_budget = None
        latest_date = None
        
        # Säker hantering av budgets dict
        if budgets and isinstance(budgets, dict):
            for budget_id, budget_data in budgets.items():
                if budget_data and budget_data.get('year') == year:
                    updated_at = budget_data.get('updated_at', budget_data.get('created_at'))
                    if latest_date is None or updated_at > latest_date:
                        latest_date = updated_at
                        target_budget = (budget_id, budget_data)
        
        if not target_budget:
            return pd.DataFrame()
        
        budget_id, budget_info = target_budget
        
        # Hämta budgetvärden för denna budget
        budget_values = firebase_db.get_budget_values(budget_id)
        
        print(f"🔥 GET_BUDGET_DATA: budget_id={budget_id}")
        print(f"🔥 GET_BUDGET_DATA: budget_values typ={type(budget_values)}")
        print(f"🔥 GET_BUDGET_DATA: budget_values längd={len(budget_values) if budget_values else 0}")
        
        # Hämta referensdata
        accounts = firebase_db.get_accounts()
        categories = firebase_db.get_account_categories()
        
        # Bygg DataFrame - säker hantering av budget_values
        data = []
        if budget_values and isinstance(budget_values, dict):
            print(f"🔥 GET_BUDGET_DATA: Itererar över {len(budget_values)} budget_values")
            for key, value_data in budget_values.items():
                if value_data and isinstance(value_data, dict):
                    account_id = value_data.get('account_id')
                    account_data = accounts.get(account_id, {})
                    
                    category_id = account_data.get('category_id')
                    category_data = categories.get(category_id, {})
                    
                    print(f"🔥 BUDGET VALUE: {key} -> {value_data}")
                    
                    data.append({
                        'account_name': account_data.get('name', ''),
                        'category': category_data.get('name', ''),
                        'month': value_data.get('month'),
                        'amount': value_data.get('amount', 0),
                        'account_id': account_id
                    })
        
        df = pd.DataFrame(data)
        
        if not df.empty:
            df = df.sort_values(['category', 'account_name', 'month'])
        
        print(f"🔥 GET_BUDGET_DATA: Slutliga DataFrame har {len(df)} rader")
        
        # Visa vilken budget som används med korrekt antal
        budget_count = len(budget_values) if budget_values else 0
        st.info(f"📊 Laddar budget från budget_id: {budget_id} ({budget_count} värden)")
        
        return df
    except Exception as e:
        st.error(f"Fel vid hämtning av budget: {e}")
        return pd.DataFrame()

def get_all_categories():
    """Hämta alla kategorier"""
    try:
        firebase_db = get_firebase_db()
        categories_dict = firebase_db.get_account_categories()
        
        data = []
        for category_id, category_data in categories_dict.items():
            data.append({
                'id': category_id,
                'name': category_data.get('name', '')
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df = df.sort_values('name')
        
        return df
    except Exception as e:
        st.error(f"Fel vid hämtning av kategorier: {e}")
        return pd.DataFrame()

def update_account_category(account_id, new_category_id):
    """Uppdatera kontokategori"""
    try:
        firebase_db = get_firebase_db()
        
        # Hämta befintligt konto
        accounts = firebase_db.get_accounts()
        if account_id not in accounts:
            st.error("Konto hittades inte")
            return False
        
        # Uppdatera kategorin
        account_ref = firebase_db.get_ref(f"accounts/{account_id}")
        account_ref.update({
            "category_id": new_category_id,
            "updated_at": datetime.now().isoformat()
        })
        
        return True
    except Exception as e:
        st.error(f"Fel vid uppdatering av kategori: {e}")
        return False

def create_excel_table_with_categories(actual_df, budget_df):
    """Skapa Excel-liknande tabell - VISAR FAKTISK DATA, budget visas separat"""
    month_names = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                   'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    
    result_data = []
    
    # Använd alla konton från faktisk data
    if not actual_df.empty:
        unique_accounts = actual_df[['account_name', 'category', 'account_id', 'category_id']].drop_duplicates()
        
        for _, account_info in unique_accounts.iterrows():
            account = account_info['account_name']
            category = account_info['category']
            account_id = account_info['account_id']
            category_id = account_info['category_id']
            
            row = {
                'account': account, 
                'category': category,
                'account_id': account_id,
                'category_id': category_id
            }
            
            # Faktiska värden för alla månader
            account_data = actual_df[actual_df['account_name'] == account]
            for i, month in enumerate(month_names, 1):
                month_data = account_data[account_data['month'] == i]
                value = month_data['amount'].sum() if len(month_data) > 0 else 0
                row[month] = value
            
            result_data.append(row)
    
    return pd.DataFrame(result_data)

def save_budget(company_id, year, budget_updates):
    """Spara budget till databasen - ENKEL OCH SÄKER VERSION"""
    try:
        firebase_db = get_firebase_db()
        
        # Hitta eller skapa budget för detta företag och år
        budgets = firebase_db.get_budgets(company_id)
        target_budget_id = None
        
        # Leta efter befintlig budget för detta år
        if budgets and isinstance(budgets, dict):
            for budget_id, budget_data in budgets.items():
                if budget_data and budget_data.get('year') == year:
                    target_budget_id = budget_id
                    break
        
        # Skapa ny budget om ingen finns
        if not target_budget_id:
            target_budget_id = firebase_db.create_budget(company_id, year, f"Budget {year}")
        
        # Debug: visa vad som ska sparas
        st.write(f"🔍 DEBUG: Sparar för budget_id: {target_budget_id}")
        st.write(f"🔍 DEBUG: Budget updates: {budget_updates}")
        
        # Spara bara de värden som skickats in
        saved_count = 0
        for account_id, months_data in budget_updates.items():
            for month, amount in months_data.items():
                try:
                    # Använd account_id som string (Firebase använder string-IDs)
                    firebase_db.update_budget_value(target_budget_id, str(account_id), int(month), float(amount))
                    saved_count += 1
                    st.write(f"✅ Sparade: konto {account_id}, månad {month}, belopp {amount}")
                except Exception as e:
                    st.error(f"❌ Fel vid sparande: {e}")
        
        st.success(f"✅ Budget sparad! {saved_count} värden uppdaterade.")
        return True
        
    except Exception as e:
        st.error(f"❌ Fel vid sparande av budget: {e}")
        return False

def collect_budget_updates(actual_df, budget_df):
    """Läs alla number_input-värden från session_state och bygg budget_updates.

    Faller tillbaka till befintlig budget om ett fält inte finns i sessionen.
    """
    month_numbers = list(range(1, 13))
    updates = {}
    # Befintlig budget per (account_id, month)
    existing = {}
    if not budget_df.empty:
        for _, row in budget_df.iterrows():
            existing[(int(row['account_id']), int(row['month']))] = float(row['amount'])

    unique_accounts = actual_df[['account_name', 'category', 'account_id']].drop_duplicates()
    for _, acc in unique_accounts.iterrows():
        account_id = int(acc['account_id'])
        category = acc['category']
        month_map = {}
        for m in month_numbers:
            key = f"{category}_budget_{account_id}_{m}"
            if key in st.session_state:
                try:
                    month_map[m] = float(st.session_state[key])
                except Exception:
                    month_map[m] = 0.0
            else:
                month_map[m] = existing.get((account_id, m), 0.0)
        updates[account_id] = month_map
    return updates

def show():
    """Visa finansdatabas-sida"""
    st.title("💾 Finansdatabas")
    st.markdown("Hantera och redigera företagets finansiella data, budgetar och kontokategorier")
    
    # Hämta företag
    companies_list = get_companies()
    if not companies_list:
        st.warning("🔧 Ingen data hittad. Kör ETL-processen först.")
        return
    
    # Företagsval med rätt städer
    city_mapping = {
        "KLAB": "Linköping",
        "KSAB": "Stockholm", 
        "KMAB": "Malmö",
        "AAB": "Göteborg",
        "KFAB": "Falun"
    }
    
    company_options = {}
    for company in companies_list:
        company_name = company['name']
        city = city_mapping.get(company_name, "Stockholm")  # Fallback till Stockholm
        company_options[f"{company_name} ({city})"] = company['id']
    
    selected_company_name = st.selectbox(
        "Välj företag",
        list(company_options.keys()),
    )
    selected_company_id = company_options[selected_company_name]
    
    # Årval
    available_years = get_years_for_company(selected_company_id)
    if not available_years:
        st.warning("Inga år hittade för detta företag")
        return
    
    selected_year = st.selectbox(
        "Välj år",
        available_years,
        index=len(available_years)-1 if available_years else 0
    )
    
    st.markdown("---")
    
    # Hämta data
    actual_df = get_financial_data_with_categories(selected_company_id, selected_year)
    budget_df = get_budget_data(selected_company_id, selected_year)
    categories_df = get_all_categories()
    
    if actual_df.empty:
        st.warning("Ingen data hittad för valt företag och år")
        return
    
    # Skapa tabellen med kategorival
    table_df = create_excel_table_with_categories(actual_df, budget_df)
    
    if not table_df.empty:
        st.markdown("### Finansiell översikt")
        
        # Visa kategoriredigering kompakt
        st.markdown("#### Kategoriredigering")
        with st.expander("🔧 Ändra kontokategorier", expanded=False):
            categories = table_df['category'].unique()
            for category in categories:
                st.markdown(f"**{category}**")
                category_data = table_df[table_df['category'] == category].copy()
                
                # Visa alla konton i kategorin med dropdown
                for idx, row in category_data.iterrows():
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(row['account'])
                    
                    with col2:
                        current_cat_id = row['category_id']
                        cat_options = {cat_row['name']: cat_row['id'] for _, cat_row in categories_df.iterrows()}
                        current_cat_name = next((name for name, id in cat_options.items() if id == current_cat_id), category)
                        
                        new_category = st.selectbox(
                            "Ny kategori",
                            list(cat_options.keys()),
                            index=list(cat_options.keys()).index(current_cat_name) if current_cat_name in cat_options else 0,
                            key=f"cat_{row['account_id']}",
                            label_visibility="collapsed"
                        )
                    
                    with col3:
                        if cat_options[new_category] != current_cat_id:
                            if st.button("✓", key=f"update_{row['account_id']}", help="Uppdatera kategori"):
                                if update_account_category(row['account_id'], cat_options[new_category]):
                                    st.success(f"✅ {row['account']} flyttad till {new_category}")
                                    st.rerun()

        # Visa tabeller uppdelade efter kategori
        categories = table_df['category'].unique()
        
        for category in categories:
            st.markdown(f"#### {category}")
            category_data = table_df[table_df['category'] == category].copy()
            
            # Skapa tabell utan kategoriredigering
            month_cols = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                         'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
            
            display_data = []
            for idx, row in category_data.iterrows():
                account_id = row['account_id']
                
                # Faktisk data rad
                month_data = [row['account']]  # Starta med kontonamnet
                for month in month_cols:
                    value = row.get(month, 0)
                    # Visa alla värden, även 0
                    formatted_value = f"{value:,.1f}".replace(',', ' ').rstrip('0').rstrip('.')
                    month_data.append(formatted_value)
                display_data.append(month_data)
                
                # Budget data rad (endast om budget finns för detta konto)
                if not budget_df.empty:
                    account_budget = budget_df[budget_df['account_id'] == account_id]
                    if not account_budget.empty:
                        budget_month_data = [f"  └ Budget: {row['account']}"]  # Indenterad budget-rad
                        for i, month in enumerate(month_cols, 1):
                            budget_for_month = account_budget[account_budget['month'] == i]
                            budget_value = budget_for_month['amount'].sum() if not budget_for_month.empty else 0
                            formatted_budget = f"{budget_value:,.1f}".replace(',', ' ').rstrip('0').rstrip('.')
                            budget_month_data.append(formatted_budget)
                        display_data.append(budget_month_data)
            
            if display_data:
                display_df = pd.DataFrame(display_data, columns=['Konto'] + month_cols)

                st.dataframe(display_df.set_index('Konto'), use_container_width=True)
        
        # Totaler
        st.markdown("#### Totaler")
        total_data = []
        
        for category in categories:
            category_data = table_df[table_df['category'] == category]
            total_row = {'account': f'Tot {category} (faktiska)', 'category': category}
            
            month_cols = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                         'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
            for month in month_cols:
                total = category_data[month].sum()
                total_row[month] = f"{total:,.1f}".replace(',', ' ').rstrip('0').rstrip('.')
            
            total_data.append(total_row)
            
            # Budget totaler
            if not budget_df.empty:
                budget_category = budget_df[budget_df['category'] == category]
                budget_total_row = {'account': f'Tot {category} (budget)', 'category': category}
                
                for i, month in enumerate(month_cols, 1):
                    budget_total = budget_category[budget_category['month'] == i]['amount'].sum()
                    budget_total_row[month] = f"{budget_total:,.1f}".replace(',', ' ').rstrip('0').rstrip('.')
                
                total_data.append(budget_total_row)
        
        if total_data:
            totals_df = pd.DataFrame(total_data)
            display_totals = totals_df.drop('category', axis=1).set_index('account')
            st.dataframe(display_totals, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### Redigera Budget")
    
    # Budget-redigering i tabellform (st.data_editor)
    if not actual_df.empty:
        categories = ["Intäkter", "Kostnader"]
        tabs = st.tabs([f"📊 Budget - {cat}" for cat in categories])

        def build_budget_grid(category: str) -> pd.DataFrame:
            month_map = [('Jan',1),('Feb',2),('Mar',3),('Apr',4),('Maj',5),('Jun',6),
                         ('Jul',7),('Aug',8),('Sep',9),('Okt',10),('Nov',11),('Dec',12)]
            accounts = (
                actual_df[actual_df['category'] == category]
                [['account_name','account_id']]
                .drop_duplicates()
                .sort_values('account_name')
            )
            rows = []
            for _, r in accounts.iterrows():
                account_id = r['account_id']  # Firebase använder string-IDs
                account_name = r['account_name']
                row = { 'Konto': account_name, 'account_id': account_id }
                for label, num in month_map:
                    existing = 0.0
                    if not budget_df.empty:
                        match = budget_df[(budget_df['account_id'] == account_id) & (budget_df['month'] == num)]
                        if not match.empty:
                            existing = float(match['amount'].iloc[0])
                    row[label] = existing
                rows.append(row)
            return pd.DataFrame(rows)

        def diff_budget_updates(original_df: pd.DataFrame, edited_df: pd.DataFrame) -> dict:
            """Returnera endast ändrade celler som updates {account_id: {month: amount}}"""
            month_labels = ['Jan','Feb','Mar','Apr','Maj','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
            month_to_num = {m:i+1 for i,m in enumerate(month_labels)}

            # Hämta endast de kolumner vi bryr oss om och aligna rader på account_id
            orig = original_df[['account_id'] + month_labels].copy()
            edit = edited_df[['account_id'] + month_labels].copy()

            # Konvertera till float och fyll NaN med 0.0
            for df in (orig, edit):
                for col in month_labels:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

            merged = orig.merge(edit, on='account_id', how='outer', suffixes=('_orig', '_edit'))

            updates: dict[str, dict[int, float]] = {}
            for _, row in merged.iterrows():
                account_id = row['account_id']
                for m in month_labels:
                    b = float(row.get(f"{m}_orig", 0.0) if pd.notna(row.get(f"{m}_orig", 0.0)) else 0.0)
                    e = float(row.get(f"{m}_edit", 0.0) if pd.notna(row.get(f"{m}_edit", 0.0)) else 0.0)
                    if abs(e - b) > 1e-9:
                        updates.setdefault(account_id, {})[month_to_num[m]] = e
            return updates

        for i, category in enumerate(categories):
            with tabs[i]:
                st.markdown(f"### Budget för {category}")
                grid_df = build_budget_grid(category)

                # Kolumnkonfiguration
                num_cols = {
                    label: st.column_config.NumberColumn(label=label, step=1.0, format="%.1f")
                    for label in ['Jan','Feb','Mar','Apr','Maj','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
                }

                edited_df = st.data_editor(
                    grid_df,
                    hide_index=True,
                    column_config={
                        'Konto': st.column_config.TextColumn(label='Konto', width='large'),
                        'account_id': st.column_config.TextColumn(label='account_id', disabled=True, width='small'),
                        **num_cols,
                    },
                    use_container_width=True,
                    key=f"grid_{category}"
                )

                if st.button(f"💾 Spara budget – {category}", type="primary", key=f"save_{category}"):
                    # Spara endast ändrade celler
                    updates = diff_budget_updates(grid_df, edited_df)
                    if not updates:
                        st.info("Inga ändringar att spara.")
                        st.stop()
                    if save_budget(selected_company_id, selected_year, updates):
                        st.success("✅ Budget sparad till databasen!")
                        import time
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Kunde inte spara budget")
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <small>
    **Data för:** {selected_company_name} - {selected_year}<br>
    **💾 Firebase Realtime Database**
    </small>
    """, unsafe_allow_html=True)