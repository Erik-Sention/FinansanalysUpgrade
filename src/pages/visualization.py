"""
Datavisualisering med linjediagram för budget vs faktiska värden
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from utils.firebase_helpers import (
    get_companies, get_years_for_company, get_financial_data, 
    get_account_categories, get_company_by_id
)
from models.firebase_database import get_firebase_db

def get_all_accounts_for_company_year(company_id, year):
    """Hämta alla konton för ett företag och år med både faktiska och budgetdata"""
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
        
        # Hämta faktiska värden
        actual_values = firebase_db.get_values(dataset_id=target_dataset_id)
        
        # Hämta budgetdata
        budgets = firebase_db.get_budgets(company_id)
        budget_values = {}
        
        # Hitta senaste budget för året
        latest_budget_id = None
        latest_date = None
        
        for budget_id, budget_data in budgets.items():
            if budget_data.get('year') == year:
                updated_at = budget_data.get('updated_at', budget_data.get('created_at'))
                if latest_date is None or updated_at > latest_date:
                    latest_date = updated_at
                    latest_budget_id = budget_id
        
        if latest_budget_id:
            budget_values = firebase_db.get_budget_values(latest_budget_id)
        
        # Hämta referensdata
        accounts = firebase_db.get_accounts()
        categories = firebase_db.get_account_categories()
        
        # Bygg DataFrame
        data = []
        
        # Lägg till faktiska värden
        for value_id, value_data in actual_values.items():
            if value_data.get('value_type') != 'faktiskt':
                continue
                
            account_id = value_data.get('account_id')
            account_data = accounts.get(account_id, {})
            
            category_id = account_data.get('category_id')
            category_data = categories.get(category_id, {})
            
            data.append({
                'account_id': account_id,
                'account_name': account_data.get('name', 'Okänt konto'),
                'category': category_data.get('name', 'Okänd kategori'),
                'month': value_data.get('month'),
                'amount': value_data.get('amount', 0),
                'type': 'Faktiskt'
            })
        
        # Lägg till budgetvärden
        for value_data in budget_values.values():
            account_id = value_data.get('account_id')
            account_data = accounts.get(account_id, {})
            
            category_id = account_data.get('category_id')
            category_data = categories.get(category_id, {})
            
            data.append({
                'account_id': account_id,
                'account_name': account_data.get('name', 'Okänt konto'),
                'category': category_data.get('name', 'Okänd kategori'),
                'month': value_data.get('month'),
                'amount': value_data.get('amount', 0),
                'type': 'Budget'
            })
        
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
    
    # Skapa subplot för varje valt konto
    fig = make_subplots(
        rows=num_accounts, cols=1,
        subplot_titles=[f"{account}" for account in selected_accounts],
        vertical_spacing=0.08  # Fast spacing som fungerar med många diagram
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
    
    # Uppdatera layout - alltid samma stora format
    fig.update_layout(
        height=350 * num_accounts,  # Alltid 350px per diagram för stor, luftig layout
        title_text="Jämförelse: Budget vs Faktiska värden",
        title_x=0.5,
        title_font_size=20,  # Större titel
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=14)  # Större legend-text
        ),
        margin=dict(t=100, b=60, l=80, r=60),  # Större marginaler
        font=dict(size=12)  # Basfontstorlek för hela diagrammet
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
    
    # Hämta företag
    companies_list = get_companies()
    if not companies_list:
        st.warning("🔧 Ingen data hittad. Kör ETL-processen först.")
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
