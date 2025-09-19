"""
Ny, ren visualiseringssida som faktiskt fungerar!
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# Path setup
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

from utils_firebase_helpers import (
    get_companies, get_years_for_company, get_financial_data, 
    get_account_categories, get_company_by_id
)
from models_firebase_database import get_firebase_db

@st.cache_data(ttl=300)
def get_visualization_data(company_id, year):
    """Hämta data för visualisering - enkel och snabb version"""
    try:
        firebase_db = get_firebase_db()
        
        # Hämta ALLT från test_data i EN enda call
        test_data_ref = firebase_db.get_ref("test_data")
        test_data = test_data_ref.get(firebase_db._get_token())
        
        if not test_data or not test_data.val():
            return pd.DataFrame()
        
        data_dict = test_data.val()
        values_data = data_dict.get('values', {})
        accounts_data = data_dict.get('accounts', {})
        categories_data = data_dict.get('categories', {})
        companies_data = data_dict.get('companies', {})
        
        # Bygg DataFrame för faktiska värden
        data = []
        
        # Lägg till faktiska värden
        for value_id, value_data in values_data.items():
            if (value_data.get('company_id') == company_id and 
                value_data.get('year') == year and
                value_data.get('type') == 'actual'):
                
                account_id = value_data.get('account_id')
                account_info = accounts_data.get(account_id, {})
                category_id = account_info.get('category_id')
                category_info = categories_data.get(category_id, {})
                
                data.append({
                    'account_id': account_id,
                    'account_name': account_info.get('name', 'Okänt konto'),
                    'category': category_info.get('name', 'Okänd kategori'),
                    'month': value_data.get('month'),
                    'amount': value_data.get('amount', 0),
                    'type': 'Faktiskt'
                })
        
        # Lägg till budgetvärden från SIMPLE_BUDGETS - EN ENDA FETCH FÖR HELA ÅRET
        company_name = None
        for comp_id, comp_info in companies_data.items():
            if comp_id == company_id:
                company_name = comp_info.get('name')
                break
        
        if not company_name:
            print(f"DEBUG: company_name saknas för {company_id}")
        else:
            # 1 enda RTDB-fetch: alla konton under SIMPLE_BUDGETS/<company>/<year>
            budget_year_ref = firebase_db.get_ref(f"SIMPLE_BUDGETS/{company_name}/{year}")
            budget_year_data = budget_year_ref.get(firebase_db._get_token())
            year_node = budget_year_data.val() if (budget_year_data and budget_year_data.val()) else {}
            
            # Tolerera sv/eng månadsnamn
            month_mapping = {
                'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4, 'Maj':5, 'May':5, 'Jun':6, 'Jul':7,
                'Aug':8, 'Sep':9, 'Okt':10, 'Oct':10, 'Nov':11, 'Dec':12
            }
            
            # Undvik dubbletter: håll koll på (account_id, month)
            seen = set()
            
            for account_id, account_info in accounts_data.items():
                if account_info.get('company_id') != company_id:
                    continue
                
                account_name = account_info.get('name')
                node = year_node.get(account_name, {})
                monthly_values = (node or {}).get('monthly_values', {})
                
                if not monthly_values:
                    continue
                
                category_id = account_info.get('category_id')
                category_info = categories_data.get(category_id, {})
                
                for month_name, amount in monthly_values.items():
                    if month_name not in month_mapping or not amount:
                        continue
                    
                    m = month_mapping[month_name]
                    key = (account_id, m)
                    if key in seen:
                        # skydd mot dubletter vid ev. återanrop
                        continue
                    seen.add(key)
                    
                    try:
                        amt = float(amount)
                    except (TypeError, ValueError):
                        continue
                    
                    data.append({
                        'account_id': account_id,
                        'account_name': account_name,
                        'category': category_info.get('name', 'Okänd kategori'),
                        'month': m,
                        'amount': amt,
                        'type': 'Budget'
                    })
            print(f"DEBUG: lade till {len([r for r in data if r['type']=='Budget'])} budgetrader.")
        
        df = pd.DataFrame(data)
        
        if not df.empty:
            df = df.sort_values(['category', 'account_name', 'month'])
        
        return df
        
    except Exception as e:
        st.error(f"Fel vid hämtning av data: {e}")
        return pd.DataFrame()

def create_simple_chart(df, selected_accounts):
    """Skapa enkel linjediagram"""
    if df.empty or not selected_accounts:
        st.warning("Ingen data att visa")
        return
    
    # Filtrera data
    filtered_df = df[df['account_name'].isin(selected_accounts)].copy()
    
    if filtered_df.empty:
        st.warning("Ingen data för valda konton")
        return
    
    # Månadsnamn
    month_names = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
        5: 'Maj', 6: 'Jun', 7: 'Jul', 8: 'Aug',
        9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dec'
    }
    
    filtered_df['month_name'] = filtered_df['month'].map(month_names)
    
    # Skapa subplot för varje konto
    num_accounts = len(selected_accounts)
    fig = make_subplots(
        rows=num_accounts, cols=1,
        subplot_titles=[f"{account}" for account in selected_accounts],
        vertical_spacing=0.15
    )
    
    colors = {'Faktiskt': '#1f77b4', 'Budget': '#ff7f0e'}
    
    for i, account in enumerate(selected_accounts, 1):
        account_data = filtered_df[filtered_df['account_name'] == account]
        
        for data_type in ['Faktiskt', 'Budget']:
            type_data = account_data[account_data['type'] == data_type]
            
            if not type_data.empty:
                type_data = type_data.sort_values('month')
                
                fig.add_trace(
                    go.Scatter(
                        x=type_data['month_name'],
                        y=type_data['amount'],
                        mode='lines+markers',
                        name=f"{data_type}",
                        line=dict(color=colors[data_type], width=3),
                        marker=dict(size=8),
                        showlegend=(i == 1)
                    ),
                    row=i, col=1
                )
    
    # Layout
    fig.update_layout(
        height=400 * num_accounts,
        title_text="📈 Budget vs Faktiska värden",
        title_x=0.5,
        title_font_size=24,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=16)
        ),
        margin=dict(t=120, b=80, l=100, r=80),
        font=dict(size=14)
    )
    
    # Axlar
    fig.update_xaxes(title_text="Månad", title_font_size=16, tickfont_size=14)
    fig.update_yaxes(title_text="Belopp (tkr)", title_font_size=16, tickfont_size=14)
    
    # Subplot-titlar
    for i in range(num_accounts):
        fig.layout.annotations[i].update(font_size=18)
    
    st.plotly_chart(fig, use_container_width=True)

def show():
    """Visa den nya visualiseringssidan"""
    st.title("📈 Datavisualisering v2")
    st.markdown("**Ny, snabb version som faktiskt fungerar!**")
    
    # Hämta företag från test_data
    try:
        firebase_db = get_firebase_db()
        test_data_ref = firebase_db.get_ref("test_data")
        test_data = test_data_ref.get(firebase_db._get_token())
        
        companies_list = []
        if test_data and test_data.val():
            companies_data = test_data.val().get('companies', {})
            for company_id, company_info in companies_data.items():
                companies_list.append({
                    'id': company_id,
                    'name': company_info['name'],
                    'location': company_info['location']
                })
    except Exception as e:
        st.error(f"Fel vid hämtning av företag: {e}")
        companies_list = []
    
    if not companies_list:
        st.warning("🔧 Ingen data hittad. Kör Excel-import först.")
        return
    
    # Företagsval
    col1, col2 = st.columns(2)
    
    with col1:
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
            city = city_mapping.get(company_name, "Stockholm")
            company_options[f"{company_name} ({city})"] = company['id']
        
        selected_company_name = st.selectbox(
            "Välj företag",
            list(company_options.keys()),
        )
        selected_company_id = company_options[selected_company_name]
    
    with col2:
        # Årval
        try:
            firebase_db = get_firebase_db()
            test_data_ref = firebase_db.get_ref("test_data")
            test_data = test_data_ref.get(firebase_db._get_token())
            
            available_years = []
            if test_data and test_data.val():
                values_data = test_data.val().get('values', {})
                years_found = set()
                for value_id, value_data in values_data.items():
                    if value_data.get('company_id') == selected_company_id:
                        years_found.add(value_data.get('year'))
                available_years = sorted(list(years_found))
        except Exception as e:
            st.error(f"Fel vid hämtning av år: {e}")
            available_years = []
        
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
    with st.spinner("🔄 Hämtar data..."):
        all_data_df = get_visualization_data(selected_company_id, selected_year)
    
    if all_data_df.empty:
        st.warning("Ingen data hittad för valt företag och år")
        return
    
    # Visa debug-info EFTER tom-kollen
    st.info(f"📊 **Data laddad:** {len(all_data_df)} rader totalt")
    type_counts = all_data_df['type'].value_counts()
    st.write(f"**Faktiskt:** {type_counts.get('Faktiskt', 0)} rader | **Budget:** {type_counts.get('Budget', 0)} rader")
    
    # Få unika konton
    unique_accounts = all_data_df[['account_name', 'category']].drop_duplicates()
    unique_accounts = unique_accounts.sort_values(['category', 'account_name'])
    
    # Kontoval
    st.markdown("### Välj konton att visualisera")
    
    categories = unique_accounts['category'].unique()
    
    if len(categories) > 1:
        tabs = st.tabs([f"📊 {category}" for category in categories])
        
        selected_accounts = []
        
        for i, category in enumerate(categories):
            with tabs[i]:
                category_accounts = unique_accounts[unique_accounts['category'] == category]['account_name'].tolist()
                
                cols = st.columns(2)
                
                for j, account in enumerate(category_accounts):
                    with cols[j % 2]:
                        if st.checkbox(account, key=f"account_{category}_{account}"):
                            selected_accounts.append(account)
    else:
        category = categories[0]
        st.markdown(f"**{category}**")
        category_accounts = unique_accounts[unique_accounts['category'] == category]['account_name'].tolist()
        
        selected_accounts = st.multiselect(
            "Välj konton",
            category_accounts,
            help="Välj ett eller flera konton att visualisera"
        )
    
    if selected_accounts:
        st.markdown("---")
        st.markdown(f"### 📈 Linjediagram för {len(selected_accounts)} valda konton")
        
        # Skapa diagram
        create_simple_chart(all_data_df, selected_accounts)
        
        # Sammanfattningstabell
        st.markdown("---")
        st.markdown("### 📊 Sammanfattning")
        
        summary_data = []
        for account in selected_accounts:
            account_data = all_data_df[all_data_df['account_name'] == account]
            
            faktiskt_total = account_data[account_data['type'] == 'Faktiskt']['amount'].sum()
            budget_total = account_data[account_data['type'] == 'Budget']['amount'].sum()
            skillnad = faktiskt_total - budget_total
            skillnad_procent = (skillnad / budget_total * 100) if budget_total != 0 else 0
            
            summary_data.append({
                'Konto': account,
                'Faktiskt totalt': f"{faktiskt_total:,.0f} tkr".replace(',', ' '),
                'Budget totalt': f"{budget_total:,.0f} tkr".replace(',', ' '),
                'Skillnad': f"{skillnad:,.0f} tkr".replace(',', ' '),
                'Skillnad %': f"{skillnad_procent:.1f}%"
            })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    else:
        st.info("👆 Välj konton ovan för att se linjediagram")
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <small>
    **Data för:** {selected_company_name} - {selected_year}<br>
    **📈 Ny visualiseringssida v2 - Snabb och fungerande!**
    </small>
    """, unsafe_allow_html=True)
