"""
Datavisualisering med linjediagram för budget vs faktiska värden
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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

def get_all_accounts_for_company_year(company_id, year):
    """Hämta alla konton för företag och år från test_data"""
    try:
        firebase_db = get_firebase_db()
        
        # Hämta ALLT från test_data root
        test_data_ref = firebase_db.get_ref("test_data")
        test_data = test_data_ref.get(firebase_db._get_token())
        
        if not test_data or not test_data.val():
            return pd.DataFrame()
        
        data_dict = test_data.val()
        values_data = data_dict.get('values', {})
        accounts_data = data_dict.get('accounts', {})
        categories_data = data_dict.get('categories', {})
        
        
        # Bygg DataFrame
        data = []
        
        # Lägg till faktiska värden från test_data
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
        
        # Lägg till budgetvärden från SIMPLE_BUDGETS (samma som budget-redigeringssidan)
        try:
            print(f"🔍 DEBUG: Söker budgetdata för company_id={company_id}, year={year}")
            
            # Hämta företagsnamn från companies_data
            company_name = None
            for comp_id, comp_info in companies_data.items():
                if comp_id == company_id:
                    company_name = comp_info.get('name')
                    break
            
            print(f"🔍 DEBUG: company_name = {company_name}")
            
            if company_name:
                # Hämta alla konton för detta företag
                for account_id, account_info in accounts_data.items():
                    if account_info.get('company_id') == company_id:
                        account_name = account_info.get('name')
                        print(f"🔍 DEBUG: Kontrollerar konto: {account_name}")
                        
                        # Hämta budget för detta konto från SIMPLE_BUDGETS
                        budget_path = f"SIMPLE_BUDGETS/{company_name}/{year}/{account_name}/monthly_values"
                        print(f"🔍 DEBUG: Söker på sökväg: {budget_path}")
                        
                        budget_ref = firebase_db.get_ref(budget_path)
                        budget_data = budget_ref.get(firebase_db._get_token())
                        
                        print(f"🔍 DEBUG: budget_data = {budget_data}")
                        if budget_data:
                            print(f"🔍 DEBUG: budget_data.val() = {budget_data.val()}")
                        
                        if budget_data and budget_data.val():
                            monthly_values = budget_data.val()
                            print(f"🔍 DEBUG: ✅ Hittade budgetdata på {budget_path}")
                            print(f"🔍 DEBUG: monthly_values = {monthly_values}")
                            
                            # Lägg till varje månad (Firebase har månadsnamn som nycklar)
                            month_mapping = {
                                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
                                'Maj': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
                                'Sep': 9, 'Okt': 10, 'Nov': 11, 'Dec': 12
                            }
                            
                            budget_count = 0
                            for month_name, amount in monthly_values.items():
                                if amount != 0 and month_name in month_mapping:  # Bara lägg till om det finns värde
                                    category_id = account_info.get('category_id')
                                    category_info = categories_data.get(category_id, {})
                                    
                                    data.append({
                                        'account_id': account_id,
                                        'account_name': account_name,
                                        'category': category_info.get('name', 'Okänd kategori'),
                                        'month': month_mapping[month_name],
                                        'amount': float(amount),
                                        'type': 'Budget'
                                    })
                                    budget_count += 1
                                    print(f"🔍 DEBUG: ✅ Lade till budget: {month_name} = {amount}")
                            
                            print(f"🔍 DEBUG: ✅ Totalt {budget_count} budgetvärden lade till för {account_name}")
                        else:
                            print(f"🔍 DEBUG: ❌ Ingen budgetdata på {budget_path}")
            else:
                print(f"🔍 DEBUG: ❌ Kunde inte hitta company_name för company_id={company_id}")
        except Exception as e:
            print(f"🔍 DEBUG: ❌ Fel vid hämtning av budgetdata: {e}")
            import traceback
            traceback.print_exc()
        
        # Lägg till budgetvärden från SIMPLE_BUDGETS (samma som budget-redigeringssidan)
        try:
            print(f"🔍 DEBUG: Söker budgetdata för company_id={company_id}, year={year}")
            
            # Hämta företagsnamn från companies_data
            company_name = None
            for comp_id, comp_info in companies_data.items():
                if comp_id == company_id:
                    company_name = comp_info.get('name')
                    break
            
            print(f"🔍 DEBUG: company_name = {company_name}")
            
            if company_name:
                # Hämta alla konton för detta företag
                for account_id, account_info in accounts_data.items():
                    if account_info.get('company_id') == company_id:
                        account_name = account_info.get('name')
                        print(f"🔍 DEBUG: Kontrollerar konto: {account_name}")
                        
                        # Hämta budget för detta konto från SIMPLE_BUDGETS
                        budget_path = f"SIMPLE_BUDGETS/{company_name}/{year}/{account_name}/monthly_values"
                        print(f"🔍 DEBUG: Söker på sökväg: {budget_path}")
                        
                        budget_ref = firebase_db.get_ref(budget_path)
                        budget_data = budget_ref.get(firebase_db._get_token())
                        
                        print(f"🔍 DEBUG: budget_data = {budget_data}")
                        if budget_data:
                            print(f"🔍 DEBUG: budget_data.val() = {budget_data.val()}")
                        
                        if budget_data and budget_data.val():
                            monthly_values = budget_data.val()
                            print(f"🔍 DEBUG: ✅ Hittade budgetdata på {budget_path}")
                            print(f"🔍 DEBUG: monthly_values = {monthly_values}")
                            
                            # Lägg till varje månad (Firebase har månadsnamn som nycklar)
                            month_mapping = {
                                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
                                'Maj': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
                                'Sep': 9, 'Okt': 10, 'Nov': 11, 'Dec': 12
                            }
                            
                            budget_count = 0
                            for month_name, amount in monthly_values.items():
                                if amount != 0 and month_name in month_mapping:  # Bara lägg till om det finns värde
                                    category_id = account_info.get('category_id')
                                    category_info = categories_data.get(category_id, {})
                                    
                                    data.append({
                                        'account_id': account_id,
                                        'account_name': account_name,
                                        'category': category_info.get('name', 'Okänd kategori'),
                                        'month': month_mapping[month_name],
                                        'amount': float(amount),
                                        'type': 'Budget'
                                    })
                                    budget_count += 1
                                    print(f"🔍 DEBUG: ✅ Lade till budget: {month_name} = {amount}")
                            
                            print(f"🔍 DEBUG: ✅ Totalt {budget_count} budgetvärden lade till för {account_name}")
                        else:
                            print(f"🔍 DEBUG: ❌ Ingen budgetdata på {budget_path}")
            else:
                print(f"🔍 DEBUG: ❌ Kunde inte hitta company_name för company_id={company_id}")
        except Exception as e:
            print(f"🔍 DEBUG: ❌ Fel vid hämtning av budgetdata: {e}")
            import traceback
            traceback.print_exc()
        
        df = pd.DataFrame(data)
        
        if not df.empty:
            df = df.sort_values(['category', 'account_name', 'month'])
        
        return df
    except Exception as e:
        st.error(f"Fel vid hämtning av data: {e}")
        return pd.DataFrame()

def create_line_chart(df, selected_accounts):
    """Skapa linjediagram för valda konton"""
    if df.empty or not selected_accounts:
        st.warning("Ingen data att visa")
        return
    
    # Filtrera data för valda konton
    filtered_df = df[df['account_name'].isin(selected_accounts)].copy()
    
    if filtered_df.empty:
        st.warning("Ingen data för valda konton")
        return
    
    # Månadsnamn för x-axeln
    month_names = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
        5: 'Maj', 6: 'Jun', 7: 'Jul', 8: 'Aug',
        9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dec'
    }
    
    filtered_df['month_name'] = filtered_df['month'].map(month_names)
    
    # Skapa subplot för varje valt konto med fast spacing
    num_accounts = len(selected_accounts)
    
    # Skapa subplot för varje valt konto med bättre spacing
    fig = make_subplots(
        rows=num_accounts, cols=1,
        subplot_titles=[f"{account}" for account in selected_accounts],
        vertical_spacing=0.12  # Mer spacing mellan diagram
    )
    
    colors = {'Faktiskt': '#1f77b4', 'Budget': '#ff7f0e'}
    
    for i, account in enumerate(selected_accounts, 1):
        account_data = filtered_df[filtered_df['account_name'] == account]
        
        for data_type in ['Faktiskt', 'Budget']:
            type_data = account_data[account_data['type'] == data_type]
            
            if not type_data.empty:
                # Sortera efter månad för korrekt linjediagram
                type_data = type_data.sort_values('month')
                
                fig.add_trace(
                    go.Scatter(
                        x=type_data['month_name'],
                        y=type_data['amount'],
                        mode='lines+markers',
                        name=f"{account} - {data_type}",
                        line=dict(color=colors[data_type], width=2),
                        marker=dict(size=6),
                        showlegend=(i == 1)  # Visa legend bara för första subploten
                    ),
                    row=i, col=1
                )
    
    # Uppdatera layout - alltid samma stora format med bättre spacing
    fig.update_layout(
        height=400 * num_accounts,  # Högre för bättre spacing
        title_text="Jämförelse: Budget vs Faktiska värden",
        title_x=0.5,
        title_font_size=22,  # Större titel
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,  # Högre upp för bättre spacing
            xanchor="right",
            x=1,
            font=dict(size=16)  # Större legend-text
        ),
        margin=dict(t=120, b=80, l=100, r=80),  # Större marginaler för bättre spacing
        font=dict(size=14)  # Större basfontstorlek
    )
    
    # Uppdatera x-axel för alla subplots med större text
    fig.update_xaxes(
        title_text="Månad", 
        title_font_size=14,
        tickfont_size=12
    )
    fig.update_yaxes(
        title_text="Belopp (tkr)", 
        title_font_size=14,
        tickfont_size=12
    )
    
    # Uppdatera subplot-titlar med större text
    for i in range(num_accounts):
        fig.layout.annotations[i].update(font_size=16)
    
    st.plotly_chart(fig, width='stretch')

def show():
    """Visa visualiseringssida"""
    st.title("📈 Datavisualisering")
    st.markdown("Välj konton för att jämföra budget mot faktiska värden i linjediagram")
    
    # DEBUG: Visa att vi är i rätt fil
    st.error("🔍 DEBUG: Vi är i pages_visualization.py - den RÄTTA filen!")
    
    # DEBUG: Testa budget-hämtning direkt
    try:
        firebase_db = get_firebase_db()
        budget_path = "SIMPLE_BUDGETS/AAB/2025/Autogenererade KF-fakturor från autogirot MS, 6% moms/monthly_values"
        budget_ref = firebase_db.get_ref(budget_path)
        budget_data = budget_ref.get(firebase_db._get_token())
        
        if budget_data and budget_data.val():
            st.success(f"✅ HITTADE BUDGETDATA! {budget_data.val()}")
        else:
            st.error(f"❌ INGEN BUDGETDATA på {budget_path}")
    except Exception as e:
        st.error(f"❌ FEL vid budget-hämtning: {e}")
    
    # DEBUG: Visa att budgetdata nu ska visas
    st.info("🎯 Nu ska budgetdata visas i diagrammet och tabellen!")
    
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
    
    # Skapa två kolumner för val
    col1, col2 = st.columns(2)
    
    with col1:
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
    
    with col2:
        # Årval från test_data
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
    
    # Hämta all data för valt företag och år
    all_data_df = get_all_accounts_for_company_year(selected_company_id, selected_year)
    
    if all_data_df.empty:
        st.warning("Ingen data hittad för valt företag och år")
        return
    
    # Få unika konton grupperade efter kategori
    unique_accounts = all_data_df[['account_name', 'category']].drop_duplicates()
    unique_accounts = unique_accounts.sort_values(['category', 'account_name'])
    
    # Skapa val för konton
    st.markdown("### Välj konton att visualisera")
    
    categories = unique_accounts['category'].unique()
    
    # Skapa tabs för varje kategori
    if len(categories) > 1:
        tabs = st.tabs([f"📊 {category}" for category in categories])
        
        selected_accounts = []
        
        for i, category in enumerate(categories):
            with tabs[i]:
                category_accounts = unique_accounts[unique_accounts['category'] == category]['account_name'].tolist()
                
                # Kolumner för kompakt layout
                cols = st.columns(2)
                
                for j, account in enumerate(category_accounts):
                    with cols[j % 2]:
                        if st.checkbox(account, key=f"account_{category}_{account}"):
                            selected_accounts.append(account)
    else:
        # Om bara en kategori, visa direkt
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
        st.markdown(f"### Linjediagram för {len(selected_accounts)} valda konton")
        
        # Skapa och visa diagrammet
        create_line_chart(all_data_df, selected_accounts)
        
        # Visa sammanfattningstabeller
        st.markdown("---")
        st.markdown("### Sammanfattning")
        
        # Sammanfattning för valda konton
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
            st.dataframe(summary_df, width='stretch', hide_index=True)
    
    else:
        st.info("👆 Välj konton ovan för att se linjediagram")
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <small>
    **Data för:** {selected_company_name} - {selected_year}<br>
    **📈 Interaktiv visualisering med Plotly**
    </small>
    """, unsafe_allow_html=True)
