"""
Säsongsanalys-sida för finansiell analys
Separat från Visualisering v2 för optimal prestanda
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np

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
def get_seasonal_data(company_id, years):
    """Hämta data för säsongsanalys över flera år - effektiv och snabb"""
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
        
        # Bygg DataFrame för faktiska värden över alla år
        data = []
        
        # Lägg till faktiska värden för alla valda år
        for value_id, value_data in values_data.items():
            if (value_data.get('company_id') == company_id and 
                value_data.get('year') in years and
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
                    'year': value_data.get('year'),
                    'type': 'Faktiskt'
                })
        
        # Lägg till budgetvärden för alla valda år
        company_name = None
        for comp_id, comp_info in companies_data.items():
            if comp_id == company_id:
                company_name = comp_info.get('name')
                break
        
        if company_name:
            month_mapping = {
                'Jan':1,'Feb':2,'Mar':3,'Apr':4,'Maj':5,'May':5,'Jun':6,'Jul':7,
                'Aug':8,'Sep':9,'Okt':10,'Oct':10,'Nov':11,'Dec':12
            }
            
            processed_names = set()
            for account_id, account_info in accounts_data.items():
                if account_info.get('company_id') != company_id:
                    continue
                
                account_name = account_info.get('name')
                if account_name in processed_names:
                    continue
                processed_names.add(account_name)
                
                for year in years:
                    budget_path = f"SIMPLE_BUDGETS/{company_name}/{year}/{account_name}/monthly_values"
                    budget_ref = firebase_db.get_ref(budget_path)
                    budget_data = budget_ref.get(firebase_db._get_token())
                    monthly_values = budget_data.val() if (budget_data and budget_data.val()) else {}
                    
                    if not monthly_values:
                        continue
                    
                    category_id = account_info.get('category_id')
                    category_info = categories_data.get(category_id, {})
                    
                    for month_name, amount in monthly_values.items():
                        m = month_mapping.get(month_name)
                        if not m or not amount:
                            continue
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
                            'year': year,
                            'type': 'Budget'
                        })
        
        df = pd.DataFrame(data)
        
        if not df.empty:
            # Dedupe budget-rader på kontonamn+månad+år
            mask = df['type'] == 'Budget'
            df_budget = df[mask].drop_duplicates(subset=['account_name','month','year'])
            df_actual = df[~mask]
            df = pd.concat([df_actual, df_budget], ignore_index=True) \
                   .sort_values(['category','account_name','year','month'])
        
        return df
        
    except Exception as e:
        st.error(f"Fel vid hämtning av säsongsdata: {e}")
        return pd.DataFrame()

def calculate_seasonal_metrics(df, selected_accounts, years):
    """Beräkna säsongsmätvärden för valda konton"""
    if df.empty or not selected_accounts:
        return pd.DataFrame()
    
    # Filtrera data för valda konton
    filtered_df = df[df['account_name'].isin(selected_accounts)].copy()
    
    if filtered_df.empty:
        return pd.DataFrame()
    
    # Månadsnamn
    month_names = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
        5: 'Maj', 6: 'Jun', 7: 'Jul', 8: 'Aug',
        9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dec'
    }
    
    results = []
    
    for account in selected_accounts:
        account_data = filtered_df[filtered_df['account_name'] == account]
        
        # Faktiska värden för säsongsberäkningar
        actual_data = account_data[account_data['type'] == 'Faktiskt']
        
        if actual_data.empty:
            # Om inga faktiska data finns, använd budget som referens
            budget_data = account_data[account_data['type'] == 'Budget']
            if not budget_data.empty:
                for _, row in budget_data.iterrows():
                    results.append({
                        'account_name': account,
                        'month': row['month'],
                        'month_name': month_names[row['month']],
                        'amount_actual': 0,
                        'amount_budget': row['amount'],
                        'monthly_avg': row['amount'],
                        'seasonal_index': 100,
                        'yearly_percentage': 0,
                        'ma3': row['amount'],
                        'has_actual_data': False
                    })
            continue
        
        # Beräkna månadsmedel för faktiska värden
        monthly_stats = actual_data.groupby('month').agg({
            'amount': ['mean', 'min', 'max', 'count']
        }).round(2)
        
        monthly_stats.columns = ['monthly_avg', 'min', 'max', 'data_points']
        monthly_stats = monthly_stats.reset_index()
        
        # Beräkna bas (medel av alla månadsmedel)
        base = monthly_stats['monthly_avg'].mean()
        
        # Beräkna säsongsindex och andel av år
        monthly_stats['seasonal_index'] = (monthly_stats['monthly_avg'] / base * 100).round(1)
        yearly_total = monthly_stats['monthly_avg'].sum()
        monthly_stats['yearly_percentage'] = (monthly_stats['monthly_avg'] / yearly_total * 100).round(1)
        
        # Beräkna 3-månaders glidande medel
        monthly_stats['ma3'] = monthly_stats['monthly_avg'].rolling(window=3, center=True).mean().round(2)
        
        # Lägg till budgetvärden om de finns
        budget_data = account_data[account_data['type'] == 'Budget']
        budget_monthly = budget_data.groupby('month')['amount'].mean().reset_index()
        budget_monthly.columns = ['month', 'budget_avg']
        
        # Kombinera data
        for _, row in monthly_stats.iterrows():
            month = row['month']
            budget_amount = budget_monthly[budget_monthly['month'] == month]['budget_avg'].iloc[0] if not budget_monthly.empty and month in budget_monthly['month'].values else 0
            
            results.append({
                'account_name': account,
                'month': month,
                'month_name': month_names[month],
                'amount_actual': row['monthly_avg'],
                'amount_budget': budget_amount,
                'monthly_avg': row['monthly_avg'],
                'seasonal_index': row['seasonal_index'],
                'yearly_percentage': row['yearly_percentage'],
                'ma3': row['ma3'],
                'min': row['min'],
                'max': row['max'],
                'data_points': row['data_points'],
                'has_actual_data': True
            })
    
    return pd.DataFrame(results)

def create_seasonal_chart(seasonal_df, chart_type, show_budget, show_ma3, show_bands):
    """Skapa säsongsanalys-diagram med säker fillcolor-hantering"""
    if seasonal_df.empty:
        st.warning("Ingen säsongsdata att visa")
        return
    
    # Månadsordning
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
    seasonal_df['month_name'] = pd.Categorical(seasonal_df['month_name'], categories=month_order, ordered=True)
    seasonal_df = seasonal_df.sort_values('month_name')
    
    if chart_type == "Kombinerat":
        # Kombinerat diagram - alla konton i ett diagram
        fig = go.Figure()
        
        accounts = seasonal_df['account_name'].unique()
        colors = px.colors.qualitative.Set1[:len(accounts)]
        
        for i, account in enumerate(accounts):
            account_data = seasonal_df[seasonal_df['account_name'] == account]
            
            # Huvudlinje (faktiskt eller budget)
            if account_data['has_actual_data'].iloc[0]:
                fig.add_trace(go.Scatter(
                    x=account_data['month_name'],
                    y=account_data['monthly_avg'],
                    mode='lines+markers',
                    name=f"{account} (Faktiskt)",
                    line=dict(color=colors[i], width=3),
                    marker=dict(size=8)
                ))
                
                # Konfidensband om flera år - SÄKER FILLCOLOR-HANTERING
                if show_bands and len(account_data) > 1:
                    # Kontrollera att vi har giltiga värden för band
                    max_values = account_data['max'].dropna()
                    min_values = account_data['min'].dropna()
                    
                    if len(max_values) > 0 and len(min_values) > 0:
                        # Säker färgkonvertering
                        color_rgb = colors[i].lstrip('#')
                        r, g, b = tuple(int(color_rgb[j:j+2], 16) for j in (0, 2, 4))
                        safe_fillcolor = f"rgba({r}, {g}, {b}, 0.2)"
                        
                        fig.add_trace(go.Scatter(
                            x=account_data['month_name'],
                            y=account_data['max'],
                            mode='lines',
                            line=dict(width=0),
                            showlegend=False,
                            hoverinfo='skip'
                        ))
                        fig.add_trace(go.Scatter(
                            x=account_data['month_name'],
                            y=account_data['min'],
                            mode='lines',
                            fill='tonexty',
                            fillcolor=safe_fillcolor,
                            line=dict(width=0),
                            name=f"{account} (Min-Max)",
                            showlegend=True
                        ))
                
                # MA3 glättning
                if show_ma3:
                    fig.add_trace(go.Scatter(
                        x=account_data['month_name'],
                        y=account_data['ma3'],
                        mode='lines',
                        name=f"{account} (MA3)",
                        line=dict(color=colors[i], width=2, dash='dash'),
                        opacity=0.7
                    ))
            else:
                # Endast budget tillgänglig
                fig.add_trace(go.Scatter(
                    x=account_data['month_name'],
                    y=account_data['amount_budget'],
                    mode='lines+markers',
                    name=f"{account} (Budget)",
                    line=dict(color=colors[i], width=3, dash='dot'),
                    marker=dict(size=8)
                ))
            
            # Budget som referenslinje
            if show_budget and account_data['amount_budget'].iloc[0] > 0:
                fig.add_trace(go.Scatter(
                    x=account_data['month_name'],
                    y=account_data['amount_budget'],
                    mode='lines',
                    name=f"{account} (Budget)",
                    line=dict(color=colors[i], width=2, dash='dot'),
                    opacity=0.6
                ))
        
        fig.update_layout(
            title="📅 Säsongsanalys - Kombinerat",
            xaxis_title="Månad",
            yaxis_title="Belopp (tkr)",
            height=600,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
    else:
        # Separata diagram - ett subplot per konto
        accounts = seasonal_df['account_name'].unique()
        fig = make_subplots(
            rows=len(accounts), cols=1,
            subplot_titles=[f"{account}" for account in accounts],
            vertical_spacing=0.15
        )
        
        colors = px.colors.qualitative.Set1
        
        for i, account in enumerate(accounts, 1):
            account_data = seasonal_df[seasonal_df['account_name'] == account]
            
            if account_data['has_actual_data'].iloc[0]:
                # Faktiska värden
                fig.add_trace(go.Scatter(
                    x=account_data['month_name'],
                    y=account_data['monthly_avg'],
                    mode='lines+markers',
                    name=f"{account} (Faktiskt)",
                    line=dict(color=colors[0], width=3),
                    marker=dict(size=8),
                    showlegend=(i == 1)
                ), row=i, col=1)
                
                # MA3 glättning
                if show_ma3:
                    fig.add_trace(go.Scatter(
                        x=account_data['month_name'],
                        y=account_data['ma3'],
                        mode='lines',
                        name=f"{account} (MA3)",
                        line=dict(color=colors[1], width=2, dash='dash'),
                        showlegend=(i == 1)
                    ), row=i, col=1)
            else:
                # Endast budget
                fig.add_trace(go.Scatter(
                    x=account_data['month_name'],
                    y=account_data['amount_budget'],
                    mode='lines+markers',
                    name=f"{account} (Budget)",
                    line=dict(color=colors[0], width=3, dash='dot'),
                    marker=dict(size=8),
                    showlegend=(i == 1)
                ), row=i, col=1)
            
            # Budget som referenslinje
            if show_budget and account_data['amount_budget'].iloc[0] > 0:
                fig.add_trace(go.Scatter(
                    x=account_data['month_name'],
                    y=account_data['amount_budget'],
                    mode='lines',
                    name=f"{account} (Budget)",
                    line=dict(color=colors[2], width=2, dash='dot'),
                    opacity=0.6,
                    showlegend=(i == 1)
                ), row=i, col=1)
        
        fig.update_layout(
            title="📅 Säsongsanalys - Separata diagram",
            height=400 * len(accounts),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        fig.update_xaxes(title_text="Månad")
        fig.update_yaxes(title_text="Belopp (tkr)")
    
    st.plotly_chart(fig, use_container_width=True)

def create_index_chart(seasonal_df):
    """Skapa säsongsindex-diagram (bas=100)"""
    if seasonal_df.empty:
        st.warning("Ingen säsongsdata att visa")
        return
    
    # Månadsordning
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
    seasonal_df['month_name'] = pd.Categorical(seasonal_df['month_name'], categories=month_order, ordered=True)
    seasonal_df = seasonal_df.sort_values('month_name')
    
    fig = go.Figure()
    
    accounts = seasonal_df['account_name'].unique()
    colors = px.colors.qualitative.Set1[:len(accounts)]
    
    for i, account in enumerate(accounts):
        account_data = seasonal_df[seasonal_df['account_name'] == account]
        
        if account_data['has_actual_data'].iloc[0]:
            fig.add_trace(go.Scatter(
                x=account_data['month_name'],
                y=account_data['seasonal_index'],
                mode='lines+markers',
                name=f"{account}",
                line=dict(color=colors[i], width=3),
                marker=dict(size=8)
            ))
    
    # Lägg till referenslinje vid 100
    fig.add_hline(y=100, line_dash="dash", line_color="gray", 
                  annotation_text="Bas (100)", annotation_position="top right")
    
    fig.update_layout(
        title="📅 Säsongsindex (Bas = 100)",
        xaxis_title="Månad",
        yaxis_title="Index",
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_percentage_chart(seasonal_df):
    """Skapa andel av årsintäkt-diagram"""
    if seasonal_df.empty:
        st.warning("Ingen säsongsdata att visa")
        return
    
    # Månadsordning
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
    seasonal_df['month_name'] = pd.Categorical(seasonal_df['month_name'], categories=month_order, ordered=True)
    seasonal_df = seasonal_df.sort_values('month_name')
    
    fig = go.Figure()
    
    accounts = seasonal_df['account_name'].unique()
    colors = px.colors.qualitative.Set1[:len(accounts)]
    
    for i, account in enumerate(accounts):
        account_data = seasonal_df[seasonal_df['account_name'] == account]
        
        if account_data['has_actual_data'].iloc[0]:
            fig.add_trace(go.Scatter(
                x=account_data['month_name'],
                y=account_data['yearly_percentage'],
                mode='lines+markers',
                name=f"{account}",
                line=dict(color=colors[i], width=3),
                marker=dict(size=8)
            ))
    
    fig.update_layout(
        title="📅 Andel av årsintäkt per månad (%)",
        xaxis_title="Månad",
        yaxis_title="Andel av år (%)",
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_heatmap_chart(seasonal_df):
    """Skapa värmekarta för säsongsanalys"""
    if seasonal_df.empty:
        st.warning("Ingen säsongsdata att visa")
        return
    
    # Månadsordning
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
    
    # Skapa pivot-tabell för värmekarta
    heatmap_data = seasonal_df.pivot_table(
        values='seasonal_index', 
        index='account_name', 
        columns='month_name',
        aggfunc='mean'
    )
    
    # Sortera kolumner enligt månadsordning
    heatmap_data = heatmap_data.reindex(columns=month_order)
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns,
        y=heatmap_data.index,
        colorscale='RdYlBu_r',
        hoverongaps=False,
        text=heatmap_data.values,
        texttemplate="%{text:.1f}",
        textfont={"size": 12},
        colorbar=dict(title="Säsongsindex")
    ))
    
    fig.update_layout(
        title="📅 Säsongsindex - Värmekarta",
        xaxis_title="Månad",
        yaxis_title="Konto",
        height=400,
        font=dict(size=12)
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show():
    """Visa säsongsanalys-sidan"""
    st.title("📅 Säsongsanalys")
    st.markdown("**Analysera säsongsmönster för intäkter per månad**")
    
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
        # Årval för säsongsanalys
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
        
        selected_years = st.multiselect(
            "Välj år för säsongsanalys",
            available_years,
            default=[available_years[-1]] if available_years else [],
            help="Välj ett eller flera år för att analysera säsongsmönster"
        )
    
    if not selected_years:
        st.info("👆 Välj år för säsongsanalys")
        return
    
    # Hämta data för kontoval
    with st.spinner("🔄 Hämtar data för kontoval..."):
        seasonal_data_df = get_seasonal_data(selected_company_id, selected_years)
    
    if seasonal_data_df.empty:
        st.warning("Ingen säsongsdata hittad för valt företag och år")
        return
    
    # Få unika konton
    unique_accounts = seasonal_data_df[['account_name', 'category']].drop_duplicates()
    unique_accounts = unique_accounts.sort_values(['category', 'account_name'])
    
    # Kontoval
    st.markdown("### Välj konton för säsongsanalys")
    
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
                        if st.checkbox(account, key=f"seasonal_account_{category}_{account}"):
                            selected_accounts.append(account)
    else:
        category = categories[0]
        st.markdown(f"**{category}**")
        category_accounts = unique_accounts[unique_accounts['category'] == category]['account_name'].tolist()
        
        selected_accounts = st.multiselect(
            "Välj konton",
            category_accounts,
            help="Välj ett eller flera konton för säsongsanalys"
        )
    
    if not selected_accounts:
        st.info("👆 Välj konton för säsongsanalys")
        return
    
    st.markdown("---")
    
    # UI-kontroller för säsongsanalys
    st.markdown("#### Kontroller")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        chart_layout = st.radio(
            "Diagramlayout",
            ["Kombinerat", "Separata"],
            help="Kombinerat: alla konton i ett diagram. Separata: ett diagram per konto."
        )
    
    with col2:
        value_display = st.radio(
            "Värdevisning",
            ["Absolut (tkr)", "Index (=100)", "Andel av år (%)"],
            help="Absolut: faktiska belopp. Index: normaliserat (100 = årsmedel). Andel: procent av årsintäkt."
        )
    
    with col3:
        show_budget_ref = st.checkbox(
            "Visa budget som referens",
            value=True,
            help="Visa budgetvärden som streckad referenslinje"
        )
    
    # Ytterligare kontroller
    col1, col2 = st.columns(2)
    
    with col1:
        show_ma3 = st.checkbox(
            "Glätta medel (MA3)",
            help="Visa 3-månaders glidande medel för att jämna ut brus"
        )
    
    with col2:
        show_bands = st.checkbox(
            "Historikband (min–max)",
            value=len(selected_years) > 1,
            disabled=len(selected_years) <= 1,
            help="Visa min-max band runt månadsmedel (kräver flera år)"
        )
    
    # Hjälptext
    with st.expander("ℹ️ Om säsongsanalys", expanded=False):
        st.markdown("""
        **Definitioner:**
        - **Månadsmedel**: Genomsnittligt faktiskt belopp per månad över valda år
        - **Bas (index)**: Medel av samtliga månadsmedel (=100)
        - **Säsongsindex**: (månadsmedel / bas) × 100
        - **Andel av år**: (månadsmedel / 12-månaderssumma) × 100
        - **MA3**: Glidande medel över tre månader (J–F–M, F–M–A, …)
        
        **Tips:**
        - Index (=100) gör kurvor jämförbara mellan konton och år
        - 120 betyder 20% över årsmedel
        - Historikband visar variation mellan år
        """)
    
    # Beräkna säsongsmätvärden
    seasonal_metrics_df = calculate_seasonal_metrics(seasonal_data_df, selected_accounts, selected_years)
    
    if seasonal_metrics_df.empty:
        st.warning("Ingen säsongsdata hittad för valda konton och år")
        return
    
    # QA-checkar och debug-info
    st.markdown("#### 🔍 Data-kvalitet")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        actual_accounts = seasonal_metrics_df[seasonal_metrics_df['has_actual_data'] == True]['account_name'].nunique()
        st.metric("Konton med faktiska data", actual_accounts)
    
    with col2:
        budget_accounts = seasonal_metrics_df[seasonal_metrics_df['amount_budget'] > 0]['account_name'].nunique()
        st.metric("Konton med budgetdata", budget_accounts)
    
    with col3:
        total_months = seasonal_metrics_df['month'].nunique()
        st.metric("Månader med data", total_months)
    
    # Visa konton utan faktiska data
    no_actual_data = seasonal_metrics_df[seasonal_metrics_df['has_actual_data'] == False]['account_name'].unique()
    if len(no_actual_data) > 0:
        st.warning(f"⚠️ Konton utan faktiska data (visar endast budget): {', '.join(no_actual_data)}")
    
    # Skapa visualiseringar baserat på vald värdevisning
    if value_display == "Absolut (tkr)":
        create_seasonal_chart(seasonal_metrics_df, chart_layout, show_budget_ref, show_ma3, show_bands)
    elif value_display == "Index (=100)":
        create_index_chart(seasonal_metrics_df)
    elif value_display == "Andel av år (%)":
        create_percentage_chart(seasonal_metrics_df)
    
    # Värmekarta (alltid tillgänglig)
    if len(selected_accounts) > 1:
        st.markdown("#### 🔥 Värmekarta - Säsongsindex")
        create_heatmap_chart(seasonal_metrics_df)
    
    # Säsongstabell
    st.markdown("#### 📋 Säsongstabell")
    
    # Förbered data för tabell
    table_data = seasonal_metrics_df.copy()
    
    if value_display == "Absolut (tkr)":
        table_data['Värde'] = table_data['monthly_avg'].round(1)
        table_data['MA3'] = table_data['ma3'].round(1)
    elif value_display == "Index (=100)":
        table_data['Värde'] = table_data['seasonal_index'].round(1)
        table_data['MA3'] = table_data['ma3'].round(1)
    elif value_display == "Andel av år (%)":
        table_data['Värde'] = table_data['yearly_percentage'].round(1)
        table_data['MA3'] = table_data['ma3'].round(1)
    
    # Välj kolumner att visa
    display_columns = ['account_name', 'month_name', 'Värde']
    if show_ma3:
        display_columns.append('MA3')
    if show_bands and len(selected_years) > 1:
        display_columns.extend(['min', 'max'])
    if show_budget_ref:
        display_columns.append('amount_budget')
    
    table_df = table_data[display_columns].copy()
    table_df.columns = ['Konto', 'Månad', 'Värde'] + [col for col in table_df.columns[3:]]
    
    # Sortera efter månad
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
    table_df['Månad'] = pd.Categorical(table_df['Månad'], categories=month_order, ordered=True)
    table_df = table_df.sort_values(['Konto', 'Månad'])
    
    st.dataframe(table_df, use_container_width=True, hide_index=True)
    
    # Export-knapp
    csv_data = table_df.to_csv(index=False)
    st.download_button(
        label="📥 Ladda ner säsongstabell (CSV)",
        data=csv_data,
        file_name=f"säsongsanalys_{selected_company_name}_{'-'.join(map(str, selected_years))}.csv",
        mime="text/csv"
    )
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <small>
    **Säsongsanalys för:** {selected_company_name} - {', '.join(map(str, selected_years))}<br>
    **📅 Separat säsongsanalys-sida för optimal prestanda**
    </small>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    show()
