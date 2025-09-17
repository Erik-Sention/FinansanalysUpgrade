"""
Säsongsfaktorer editor
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional
from sqlmodel import Session, select

from utils.database_helpers import (
    get_companies, get_session, format_currency
)
from models.database import (
    SeasonalityIndex, SeasonalityValue, Account, AccountCategory,
    Company, Dataset, Value
)

def get_seasonality_data(company_id: int, account_id: int) -> pd.DataFrame:
    """Hämta säsongsdata för ett konto"""
    from models.database import get_engine
    engine = get_engine()
    
    query = """
    SELECT 
        sv.year,
        sv.month,
        sv.index_value
    FROM seasonality_values sv
    JOIN seasonality_indices si ON sv.seasonality_index_id = si.id
    WHERE si.company_id = ? AND si.account_id = ?
    ORDER BY sv.year, sv.month
    """
    
    df = pd.read_sql_query(
        query,
        engine,
        params=(company_id, account_id)
    )
    
    return df

def get_historical_data(company_id: int, account_id: int) -> pd.DataFrame:
    """Hämta historisk data för beräkning av säsongsfaktorer"""
    from models.database import get_engine
    engine = get_engine()
    
    query = """
    SELECT 
        d.year,
        v.month,
        SUM(v.amount) as amount
    FROM "values" v
    JOIN datasets d ON v.dataset_id = d.id
    WHERE d.company_id = ? AND v.account_id = ? AND v.value_type = 'faktiskt'
    GROUP BY d.year, v.month
    ORDER BY d.year, v.month
    """
    
    df = pd.read_sql_query(
        query,
        engine,
        params=(company_id, account_id)
    )
    
    return df

def calculate_seasonality_indices(historical_df: pd.DataFrame) -> pd.DataFrame:
    """Beräkna säsongsfaktorer från historisk data"""
    if historical_df.empty:
        return pd.DataFrame()
    
    # Skapa pivot-tabell
    pivot_df = historical_df.pivot(index='month', columns='year', values='amount')
    pivot_df = pivot_df.fillna(0)
    
    # Beräkna årsmedelvärden
    yearly_means = pivot_df.mean(axis=0)
    
    # Beräkna säsongsindex för varje år och månad
    indices = []
    
    for year in pivot_df.columns:
        year_mean = yearly_means[year]
        if year_mean != 0:
            for month in pivot_df.index:
                month_value = pivot_df.loc[month, year]
                index_value = month_value / year_mean if year_mean != 0 else 0
                indices.append({
                    'year': year,
                    'month': month,
                    'index_value': index_value,
                    'amount': month_value
                })
    
    return pd.DataFrame(indices)

def save_seasonality_data(company_id: int, account_id: int, seasonality_data: Dict) -> bool:
    """Spara säsongsdata"""
    try:
        with get_session() as session:
            # Hämta eller skapa säsongsindex
            seasonality_index = session.exec(
                select(SeasonalityIndex).where(
                    SeasonalityIndex.company_id == company_id,
                    SeasonalityIndex.account_id == account_id
                )
            ).first()
            
            if not seasonality_index:
                seasonality_index = SeasonalityIndex(
                    company_id=company_id,
                    account_id=account_id
                )
                session.add(seasonality_index)
                session.commit()
                session.refresh(seasonality_index)
            
            # Ta bort befintliga värden
            session.exec(
                "DELETE FROM seasonality_values WHERE seasonality_index_id = ?",
                params=(seasonality_index.id,)
            )
            
            # Lägg till nya värden
            for year in range(2022, 2025):
                for month in range(1, 13):
                    key = f"{year}_{month}"
                    if key in seasonality_data and seasonality_data[key] is not None:
                        seasonality_value = SeasonalityValue(
                            seasonality_index_id=seasonality_index.id,
                            year=year,
                            month=month,
                            index_value=seasonality_data[key]
                        )
                        session.add(seasonality_value)
            
            session.commit()
            return True
            
    except Exception as e:
        st.error(f"Fel vid sparande: {e}")
        return False

def get_accounts_for_company(company_id: int) -> pd.DataFrame:
    """Hämta konton för ett företag"""
    from models.database import get_engine
    engine = get_engine()
    
    query = """
    SELECT DISTINCT a.id, a.name, ac.name as category_name
    FROM accounts a
    JOIN account_categories ac ON a.category_id = ac.id
    JOIN "values" v ON a.id = v.account_id
    JOIN datasets d ON v.dataset_id = d.id
    WHERE d.company_id = ?
    ORDER BY ac.name, a.name
    """
    
    df = pd.read_sql_query(query, engine, params=(company_id,))
    return df

def create_seasonality_chart(seasonality_df: pd.DataFrame, account_name: str) -> go.Figure:
    """Skapa säsongsdiagram"""
    if seasonality_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Ingen data tillgänglig", 
                          x=0.5, y=0.5, showarrow=False)
        return fig
    
    fig = go.Figure()
    
    # Månadsnamn
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
    
    years = sorted(seasonality_df['year'].unique())
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
    
    for i, year in enumerate(years):
        year_data = seasonality_df[seasonality_df['year'] == year]
        
        # Säkerställ att alla månader finns
        full_months = range(1, 13)
        y_values = []
        
        for month in full_months:
            month_data = year_data[year_data['month'] == month]
            if len(month_data) > 0:
                y_values.append(month_data['index_value'].iloc[0])
            else:
                y_values.append(None)
        
        fig.add_trace(go.Scatter(
            x=month_names,
            y=y_values,
            mode='lines+markers',
            name=str(year),
            line=dict(color=colors[i % len(colors)], width=3),
            marker=dict(size=8),
            connectgaps=False
        ))
    
    # Lägg till genomsnittslinje
    if len(years) > 1:
        avg_values = []
        for month in range(1, 13):
            month_values = seasonality_df[seasonality_df['month'] == month]['index_value']
            if len(month_values) > 0:
                avg_values.append(month_values.mean())
            else:
                avg_values.append(None)
        
        fig.add_trace(go.Scatter(
            x=month_names,
            y=avg_values,
            mode='lines',
            name='Genomsnitt',
            line=dict(color='black', width=2, dash='dash'),
            connectgaps=False
        ))
    
    # Lägg till referenslinje på 1.0
    fig.add_hline(y=1.0, line_dash="dot", line_color="gray", 
                  annotation_text="Normalvärde (1.0)")
    
    fig.update_layout(
        title=f'Säsongsfaktorer - {account_name}',
        xaxis_title='Månad',
        yaxis_title='Säsongsfaktor',
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig

def show():
    """Visa säsongsfaktorer sidan"""
    st.title("📈 Säsongsfaktorer")
    st.markdown("Analysera och redigera säsongsvariation för olika konton")
    
    # Kontrollera databas
    try:
        companies = get_companies()
        if not companies:
            st.warning("🔧 Ingen data hittad. Kör ETL-processen först.")
            return
    except Exception as e:
        st.error(f"Databasfel: {e}")
        return
    
    # Företagsval
    company_options = {f"{c.name} ({c.location or 'Okänd plats'})": c for c in companies}
    selected_company_name = st.selectbox(
        "Välj företag",
        list(company_options.keys()),
        key="seasonality_company"
    )
    selected_company = company_options[selected_company_name]
    
    # Hämta konton för företaget
    try:
        accounts_df = get_accounts_for_company(selected_company.id)
        if accounts_df.empty:
            st.warning("Inga konton hittade för detta företag")
            return
    except Exception as e:
        st.error(f"Kunde inte hämta konton: {e}")
        return
    
    # Kontoval
    account_options = {f"{row['name']} ({row['category_name']})": row['id'] for _, row in accounts_df.iterrows()}
    selected_account_name = st.selectbox(
        "Välj konto",
        list(account_options.keys()),
        key="seasonality_account"
    )
    selected_account_id = account_options[selected_account_name]
    
    # Tabs för olika vyer
    tab1, tab2, tab3 = st.tabs(["📊 Analys", "✏️ Redigera", "🧮 Beräkna"])
    
    with tab1:
        st.markdown("#### Säsongsanalys")
        
        # Hämta befintlig säsongsdata
        seasonality_df = get_seasonality_data(selected_company.id, selected_account_id)
        
        if not seasonality_df.empty:
            # Visa diagram
            account_name = selected_account_name.split(' (')[0]
            fig = create_seasonality_chart(seasonality_df, account_name)
            st.plotly_chart(fig, use_container_width=True)
            
            # Visa tabell
            st.markdown("##### 📅 Säsongsfaktorer per månad")
            
            # Skapa pivot för visning
            pivot_seasonality = seasonality_df.pivot(index='month', columns='year', values='index_value')
            
            # Månadsnamn
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
                           'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
            
            if not pivot_seasonality.empty:
                pivot_seasonality.index = [month_names[i-1] for i in pivot_seasonality.index]
                
                # Formatera som procent
                formatted_seasonality = pivot_seasonality.applymap(
                    lambda x: f"{x:.2f}" if pd.notna(x) else ""
                )
                
                st.dataframe(formatted_seasonality, use_container_width=True)
                
                # Sammanfattning
                st.markdown("##### 📊 Sammanfattning")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    max_month = pivot_seasonality.mean(axis=1).idxmax()
                    max_value = pivot_seasonality.mean(axis=1).max()
                    st.metric("Högsta säsong", max_month, f"{max_value:.2f}")
                
                with col2:
                    min_month = pivot_seasonality.mean(axis=1).idxmin()
                    min_value = pivot_seasonality.mean(axis=1).min()
                    st.metric("Lägsta säsong", min_month, f"{min_value:.2f}")
                
                with col3:
                    variation = pivot_seasonality.mean(axis=1).std()
                    st.metric("Säsongsvariation", f"{variation:.3f}")
        else:
            st.info("Inga säsongsfaktorer hittade för detta konto. Gå till 'Beräkna'-fliken för att generera dem.")
    
    with tab2:
        st.markdown("#### Redigera säsongsfaktorer")
        
        # Hämta befintlig data
        seasonality_df = get_seasonality_data(selected_company.id, selected_account_id)
        
        st.info("Säsongsfaktorer: 1.0 = normalvärde, >1.0 = över genomsnitt, <1.0 = under genomsnitt")
        
        # Månadsnamn
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
        
        # Skapa redigeringsformulär
        seasonality_data = {}
        
        for year in [2022, 2023, 2024]:
            st.markdown(f"##### {year}")
            
            cols = st.columns(6)
            
            for month_idx in range(12):
                month_num = month_idx + 1
                month_name = month_names[month_idx]
                col_idx = month_idx % 6
                
                # Ny rad efter 6 månader
                if month_idx == 6:
                    cols = st.columns(6)
                    col_idx = 0
                
                # Hämta befintligt värde
                existing_value = 1.0  # Default
                if not seasonality_df.empty:
                    existing_data = seasonality_df[
                        (seasonality_df['year'] == year) & 
                        (seasonality_df['month'] == month_num)
                    ]
                    if len(existing_data) > 0:
                        existing_value = existing_data['index_value'].iloc[0]
                
                with cols[col_idx]:
                    value = st.number_input(
                        month_name,
                        value=float(existing_value),
                        min_value=0.0,
                        max_value=3.0,
                        step=0.1,
                        format="%.2f",
                        key=f"seasonality_{year}_{month_num}"
                    )
                    seasonality_data[f"{year}_{month_num}"] = value
        
        # Spara-knappar
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Spara säsongsfaktorer", type="primary"):
                if save_seasonality_data(selected_company.id, selected_account_id, seasonality_data):
                    st.success("✅ Säsongsfaktorer sparade!")
                    st.rerun()
        
        with col2:
            if st.button("🔄 Återställ till 1.0"):
                reset_data = {}
                for year in [2022, 2023, 2024]:
                    for month in range(1, 13):
                        reset_data[f"{year}_{month}"] = 1.0
                
                if save_seasonality_data(selected_company.id, selected_account_id, reset_data):
                    st.success("✅ Återställt till normalvärden!")
                    st.rerun()
        
        with col3:
            if st.button("🗑️ Radera alla"):
                try:
                    with get_session() as session:
                        # Ta bort säsongsvärden
                        session.exec("""
                            DELETE FROM seasonality_values 
                            WHERE seasonality_index_id IN (
                                SELECT id FROM seasonality_indices 
                                WHERE company_id = ? AND account_id = ?
                            )
                        """, params=(selected_company.id, selected_account_id))
                        
                        # Ta bort säsongsindex
                        session.exec("""
                            DELETE FROM seasonality_indices 
                            WHERE company_id = ? AND account_id = ?
                        """, params=(selected_company.id, selected_account_id))
                        
                        session.commit()
                    
                    st.success("✅ Alla säsongsfaktorer raderade!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Kunde inte radera: {e}")
    
    with tab3:
        st.markdown("#### Beräkna säsongsfaktorer automatiskt")
        
        # Hämta historisk data
        historical_df = get_historical_data(selected_company.id, selected_account_id)
        
        if not historical_df.empty:
            st.success(f"Hittade historisk data för {len(historical_df['year'].unique())} år")
            
            # Visa historisk data
            st.markdown("##### 📊 Historisk data")
            
            # Skapa diagram för historisk data
            pivot_historical = historical_df.pivot(index='month', columns='year', values='amount')
            
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
                           'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
            
            fig_historical = go.Figure()
            
            for year in pivot_historical.columns:
                y_values = []
                for month in range(1, 13):
                    if month in pivot_historical.index:
                        y_values.append(pivot_historical.loc[month, year])
                    else:
                        y_values.append(0)
                
                fig_historical.add_trace(go.Bar(
                    x=month_names,
                    y=y_values,
                    name=str(year),
                    opacity=0.8
                ))
            
            fig_historical.update_layout(
                title='Historiska värden per månad',
                xaxis_title='Månad',
                yaxis_title='Belopp (SEK)',
                barmode='group',
                template='plotly_white'
            )
            
            st.plotly_chart(fig_historical, use_container_width=True)
            
            # Beräkna säsongsfaktorer
            if st.button("🧮 Beräkna säsongsfaktorer"):
                indices_df = calculate_seasonality_indices(historical_df)
                
                if not indices_df.empty:
                    # Konvertera till sparformat
                    calculated_data = {}
                    for _, row in indices_df.iterrows():
                        key = f"{int(row['year'])}_{int(row['month'])}"
                        calculated_data[key] = row['index_value']
                    
                    if save_seasonality_data(selected_company.id, selected_account_id, calculated_data):
                        st.success("✅ Säsongsfaktorer beräknade och sparade!")
                        st.rerun()
                else:
                    st.error("Kunde inte beräkna säsongsfaktorer")
        else:
            st.warning("Ingen historisk data hittad för detta konto. Säsongsfaktorer kan inte beräknas automatiskt.")
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <small>
    **Säsongsfaktorer för:** {selected_company.name} - {selected_account_name.split(' (')[0]}<br>
    **Senast uppdaterad:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
    </small>
    """, unsafe_allow_html=True)
