"""
Förenklad säsongsanalys-sida för finansiell analys
- Visar diagrammet direkt utan "Kör analys"-knapp
- Enklare UI med färre alternativ
- Fixar KeyError-problemet
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np
import time

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
def get_company_and_years_info(company_id):
    """Hämta endast företagsinfo och tillgängliga år - lättvikt"""
    try:
        firebase_db = get_firebase_db()

        # Hämta endast företagsinfo och år
        test_data_ref = firebase_db.get_ref("test_data")
        test_data = test_data_ref.get(firebase_db._get_token())

        if not test_data or not test_data.val():
            return None, []

        data_dict = test_data.val()
        companies_data = data_dict.get('companies', {})
        values_data = data_dict.get('values', {})

        # Hämta företagsinfo
        company_info = companies_data.get(company_id)

        # Hämta tillgängliga år
        years_found = set()
        for value_id, value_data in values_data.items():
            if value_data.get('company_id') == company_id:
                years_found.add(value_data.get('year'))

        return company_info, sorted(list(years_found))

    except Exception as e:
        st.error(f"Fel vid hämtning av företagsinfo: {e}")
        return None, []

@st.cache_data(ttl=300)
def get_accounts_list_simple(company_id):
    """Hämta kontolista för företaget - förenklad version"""
    try:
        firebase_db = get_firebase_db()

        # Hämta endast konton och kategorier
        test_data_ref = firebase_db.get_ref("test_data")
        test_data = test_data_ref.get(firebase_db._get_token())

        if not test_data or not test_data.val():
            return pd.DataFrame()

        data_dict = test_data.val()
        accounts_data = data_dict.get('accounts', {})
        categories_data = data_dict.get('categories', {})

        # Bygg kontolista
        accounts_list = []
        for account_id, account_info in accounts_data.items():
            if account_info.get('company_id') == company_id:
                category_id = account_info.get('category_id')
                category_info = categories_data.get(category_id, {})

                accounts_list.append({
                    'account_id': account_id,
                    'account_name': account_info.get('name', 'Okänt konto'),
                    'category': category_info.get('name', 'Okänd kategori')
                })

        df = pd.DataFrame(accounts_list)
        
        # Sortera som budget-sidan: först kategori, sedan kontonamn
        if not df.empty:
            df = df.sort_values(['category', 'account_name']).reset_index(drop=True)

        return df

    except Exception as e:
        st.error(f"Fel vid hämtning av kontolista: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_seasonal_data_simple(company_id, years, selected_accounts):
    """Hämta data för säsongsanalys - förenklad version med både faktiska och budgetdata"""
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

        # Bygg DataFrame för både faktiska värden och budgetdata
        data = []

        # Skapa account_id lookup för valda konton
        selected_account_ids = set()
        for account_id, account_info in accounts_data.items():
            if (account_info.get('company_id') == company_id and
                account_info.get('name') in selected_accounts):
                selected_account_ids.add(account_id)

        # Lägg till faktiska värden för alla valda år - ENDAST valda konton
        for value_id, value_data in values_data.items():
            if (value_data.get('company_id') == company_id and
                value_data.get('year') in years and
                value_data.get('type') == 'actual' and
                value_data.get('account_id') in selected_account_ids):

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

        # Lägg till budgetvärden för alla valda år - ENDAST valda konton
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

            # Hämta budget endast för valda konton
            for account_name in selected_accounts:
                for year in years:
                    budget_path = f"SIMPLE_BUDGETS/{company_name}/{year}/{account_name}/monthly_values"
                    budget_ref = firebase_db.get_ref(budget_path)
                    budget_data = budget_ref.get(firebase_db._get_token())

                    monthly_values = budget_data.val() if (budget_data and budget_data.val()) else {}

                    if not monthly_values:
                        continue

                    # Hitta account_id för detta kontonamn
                    account_id = None
                    for aid, account_info in accounts_data.items():
                        if (account_info.get('company_id') == company_id and
                            account_info.get('name') == account_name):
                            account_id = aid
                            break

                    if not account_id:
                        continue

                    category_id = accounts_data.get(account_id, {}).get('category_id')
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

def calculate_seasonal_metrics_simple(df, selected_accounts):
    """Beräkna säsongsmätvärden för valda konton - förenklad version med både faktiska och budgetdata"""
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

        if account_data.empty:
            continue

        # Separera faktiska och budgetdata
        actual_data = account_data[account_data['type'] == 'Faktiskt']
        budget_data = account_data[account_data['type'] == 'Budget']

        # Beräkna månadsmedel för faktiska värden
        if not actual_data.empty:
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
                    'monthly_avg': row['monthly_avg'],
                    'budget_avg': budget_amount,
                    'seasonal_index': row['seasonal_index'],
                    'yearly_percentage': row['yearly_percentage'],
                    'ma3': row['ma3'],
                    'min': row['min'],
                    'max': row['max'],
                    'data_points': row['data_points'],
                    'has_actual_data': True
                })

        elif not budget_data.empty:
            # Om inga faktiska data finns, använd budget som referens
            budget_monthly = budget_data.groupby('month')['amount'].mean().reset_index()
            budget_monthly.columns = ['month', 'budget_avg']

            for _, row in budget_monthly.iterrows():
                month = row['month']
                results.append({
                    'account_name': account,
                    'month': month,
                    'month_name': month_names[month],
                    'monthly_avg': row['budget_avg'],
                    'budget_avg': row['budget_avg'],
                    'seasonal_index': 100,
                    'yearly_percentage': 0,
                    'ma3': row['budget_avg'],
                    'min': row['budget_avg'],
                    'max': row['budget_avg'],
                    'data_points': 1,
                    'has_actual_data': False
                })

    return pd.DataFrame(results)

def create_simple_chart(seasonal_df, chart_type):
    """Skapa förenklat säsongsanalys-diagram med både faktiska och budgetdata"""
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
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']

        for i, account in enumerate(accounts):
            account_data = seasonal_df[seasonal_df['account_name'] == account]
            color = colors[i % len(colors)]

            # Visa faktiska värden om de finns
            if account_data['has_actual_data'].iloc[0]:
                fig.add_trace(go.Scatter(
                    x=account_data['month_name'],
                    y=account_data['monthly_avg'],
                    mode='lines+markers',
                    name=f"{account} (Faktiskt)",
                    line=dict(color=color, width=3),
                    marker=dict(size=8)
                ))

                # Visa budget som referenslinje om den finns
                if account_data['budget_avg'].iloc[0] > 0:
                    fig.add_trace(go.Scatter(
                        x=account_data['month_name'],
                        y=account_data['budget_avg'],
                        mode='lines',
                        name=f"{account} (Budget)",
                        line=dict(color=color, width=2, dash='dot'),
                        opacity=0.6
                    ))
            else:
                # Endast budget tillgänglig
                fig.add_trace(go.Scatter(
                    x=account_data['month_name'],
                    y=account_data['budget_avg'],
                    mode='lines+markers',
                    name=f"{account} (Budget)",
                    line=dict(color=color, width=3, dash='dot'),
                    marker=dict(size=8)
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

        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

        for i, account in enumerate(accounts, 1):
            account_data = seasonal_df[seasonal_df['account_name'] == account]
            color = colors[0]

            # Visa faktiska värden om de finns
            if account_data['has_actual_data'].iloc[0]:
                fig.add_trace(go.Scatter(
                    x=account_data['month_name'],
                    y=account_data['monthly_avg'],
                    mode='lines+markers',
                    name=f"{account} (Faktiskt)",
                    line=dict(color=color, width=3),
                    marker=dict(size=8),
                    showlegend=(i == 1)
                ), row=i, col=1)

                # Visa budget som referenslinje om den finns
                if account_data['budget_avg'].iloc[0] > 0:
                    fig.add_trace(go.Scatter(
                        x=account_data['month_name'],
                        y=account_data['budget_avg'],
                        mode='lines',
                        name=f"{account} (Budget)",
                        line=dict(color=colors[1], width=2, dash='dot'),
                        opacity=0.6,
                        showlegend=(i == 1)
                    ), row=i, col=1)
            else:
                # Endast budget tillgänglig
                fig.add_trace(go.Scatter(
                    x=account_data['month_name'],
                    y=account_data['budget_avg'],
                    mode='lines+markers',
                    name=f"{account} (Budget)",
                    line=dict(color=color, width=3, dash='dot'),
                    marker=dict(size=8),
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

def show():
    """Visa förenklad säsongsanalys-sida"""
    st.title("📅 Säsongsanalys (Förenklad)")
    st.markdown("**Analysera säsongsmönster för intäkter per månad**")

    # Hämta företag från test_data - lättvikt
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
        # Årval för säsongsanalys - lättvikt
        company_info, available_years = get_company_and_years_info(selected_company_id)

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

    # Hämta kontolista - lättvikt
    accounts_df = get_accounts_list_simple(selected_company_id)

    if accounts_df.empty:
        st.warning("Inga konton hittade för detta företag")
        return

    # Kontoval - förenklad version
    st.markdown("### Välj konton för säsongsanalys")

    categories = accounts_df['category'].unique()

    if len(categories) > 1:
        # Fixa namn på tabs - kostnader och intäkter är bytta!
        tab_names = []
        for category in categories:
            if "kostnad" in category.lower() or "cost" in category.lower():
                tab_names.append(f"💰 Intäkter")  # Detta är faktiskt intäkter
            elif "intäkt" in category.lower() or "revenue" in category.lower():
                tab_names.append(f"💸 Kostnader")  # Detta är faktiskt kostnader
            else:
                tab_names.append(f"📊 {category}")
        
        tabs = st.tabs(tab_names)
        
        selected_accounts = []
        
        for i, category in enumerate(categories):
            with tabs[i]:
                category_accounts = accounts_df[accounts_df['category'] == category]['account_name'].tolist()
                
                # Visa första 10 konton för enkelhet
                display_accounts = category_accounts[:10]
                
                for j, account in enumerate(display_accounts):
                    # Skapa unik nyckel med kategori och index för att undvika dubbletter
                    unique_key = f"simple_seasonal_account_{category}_{j}_{account}"
                    if st.checkbox(account, key=unique_key):
                        selected_accounts.append(account)
                
                if len(category_accounts) > 10:
                    st.info(f"... och {len(category_accounts) - 10} fler konton")
    else:
        category = categories[0]
        st.markdown(f"**{category}**")
        category_accounts = accounts_df[accounts_df['category'] == category]['account_name'].tolist()

        # Visa första 20 konton för enkelhet
        display_accounts = category_accounts[:20]
        
        selected_accounts = st.multiselect(
            "Välj konton",
            display_accounts,
            help="Välj ett eller flera konton för säsongsanalys"
        )

    if not selected_accounts:
        st.info("👆 Välj konton för säsongsanalys")
        return

    # Enkla UI-kontroller
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        chart_layout = st.radio(
            "Diagramlayout",
            ["Kombinerat", "Separata"],
            key="simple_seasonal_chart_layout",
            help="Kombinerat: alla konton i ett diagram. Separata: ett diagram per konto."
        )

    with col2:
        value_display = st.radio(
            "Värdevisning",
            ["Absolut (tkr)", "Index (=100)", "Andel av år (%)"],
            key="simple_seasonal_value_display",
            help="Absolut: faktiska belopp. Index: normaliserat (100 = årsmedel). Andel: procent av årsintäkt."
        )

    # Hämta och visa data direkt
    with st.spinner("🔄 Hämtar säsongsdata..."):
        seasonal_data_df = get_seasonal_data_simple(selected_company_id, selected_years, selected_accounts)

    if seasonal_data_df.empty:
        st.warning("Ingen säsongsdata hittad för valda konton och år")
        st.write("**Möjliga orsaker:**")
        st.write("- Inga faktiska värden för valda år")
        st.write("- Konton finns inte i databasen")
        st.write("- Felaktiga kontonamn (kontrollera stavning)")
        return

    # Beräkna säsongsmätvärden
    seasonal_metrics_df = calculate_seasonal_metrics_simple(seasonal_data_df, selected_accounts)

    if seasonal_metrics_df.empty:
        st.warning("Ingen säsongsdata hittad för valda konton och år")
        return

    # Visa prestanda-mätningar
    st.markdown("#### 🔍 Prestanda & Data-kvalitet")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Firebase-reads", "1")

    with col2:
        actual_accounts = seasonal_metrics_df[seasonal_metrics_df['has_actual_data'] == True]['account_name'].nunique()
        st.metric("Konton med faktiska data", actual_accounts)

    with col3:
        budget_accounts = seasonal_metrics_df[seasonal_metrics_df['budget_avg'] > 0]['account_name'].nunique()
        st.metric("Konton med budgetdata", budget_accounts)

    with col4:
        total_data_points = seasonal_metrics_df['data_points'].sum()
        st.metric("Totalt antal datapunkter", total_data_points)

    # Visa konton utan faktiska data
    no_actual_data = seasonal_metrics_df[seasonal_metrics_df['has_actual_data'] == False]['account_name'].unique()
    if len(no_actual_data) > 0:
        st.warning(f"⚠️ Konton utan faktiska data (visar endast budget): {', '.join(no_actual_data)}")

    # Skapa visualiseringar baserat på vald värdevisning
    if value_display == "Absolut (tkr)":
        create_simple_chart(seasonal_metrics_df, chart_layout)
    elif value_display == "Index (=100)":
        # Skapa index-diagram
        if not seasonal_metrics_df.empty:
            month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
                           'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
            seasonal_metrics_df['month_name'] = pd.Categorical(seasonal_metrics_df['month_name'], categories=month_order, ordered=True)
            seasonal_metrics_df_sorted = seasonal_metrics_df.sort_values('month_name')

            fig = go.Figure()

            accounts = seasonal_metrics_df_sorted['account_name'].unique()
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

            for i, account in enumerate(accounts):
                account_data = seasonal_metrics_df_sorted[seasonal_metrics_df_sorted['account_name'] == account]
                color = colors[i % len(colors)]

                fig.add_trace(go.Scatter(
                    x=account_data['month_name'],
                    y=account_data['seasonal_index'],
                    mode='lines+markers',
                    name=f"{account}",
                    line=dict(color=color, width=3),
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
    elif value_display == "Andel av år (%)":
        # Skapa andel-diagram
        if not seasonal_metrics_df.empty:
            month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
                           'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
            seasonal_metrics_df['month_name'] = pd.Categorical(seasonal_metrics_df['month_name'], categories=month_order, ordered=True)
            seasonal_metrics_df_sorted = seasonal_metrics_df.sort_values('month_name')

            fig = go.Figure()

            accounts = seasonal_metrics_df_sorted['account_name'].unique()
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

            for i, account in enumerate(accounts):
                account_data = seasonal_metrics_df_sorted[seasonal_metrics_df_sorted['account_name'] == account]
                color = colors[i % len(colors)]

                fig.add_trace(go.Scatter(
                    x=account_data['month_name'],
                    y=account_data['yearly_percentage'],
                    mode='lines+markers',
                    name=f"{account}",
                    line=dict(color=color, width=3),
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

    # Enkel tabell - fixar KeyError-problemet
    st.markdown("#### 📋 Säsongstabell")

    if not seasonal_metrics_df.empty:
        # Välj kolumner baserat på värdevisning
        if value_display == "Absolut (tkr)":
            display_value = seasonal_metrics_df['monthly_avg'].round(1)
            value_column = 'monthly_avg'
        elif value_display == "Index (=100)":
            display_value = seasonal_metrics_df['seasonal_index'].round(1)
            value_column = 'seasonal_index'
        elif value_display == "Andel av år (%)":
            display_value = seasonal_metrics_df['yearly_percentage'].round(1)
            value_column = 'yearly_percentage'
        else:
            display_value = seasonal_metrics_df['monthly_avg'].round(1)
            value_column = 'monthly_avg'

        # Skapa säker tabell
        table_data = seasonal_metrics_df[['account_name', 'month_name', value_column]].copy()
        table_data.columns = ['Konto', 'Månad', 'Värde']

        # Sortera efter månad
        month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
        table_data['Månad'] = pd.Categorical(table_data['Månad'], categories=month_order, ordered=True)
        table_data = table_data.sort_values(['Konto', 'Månad'])

        st.dataframe(table_data, use_container_width=True, hide_index=True)

        # Export-knapp
        csv_data = table_data.to_csv(index=False)
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
    **Säsongsanalys för:** {selected_company_name}<br>
    **📅 Förenklad version - visar diagrammet direkt**
    </small>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    show()
