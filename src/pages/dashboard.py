"""
Dashboard-sida för finansiell överblick
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional

from utils.database_helpers import (
    get_companies, get_years_for_company, calculate_monthly_summary,
    create_revenue_expense_chart, create_ytd_comparison_chart,
    get_top_accounts, format_currency
)

def show():
    """Visa dashboard-sidan"""
    st.title("📊 Finansiell Dashboard")
    st.markdown("Översikt av finansiell prestanda per företag och år")
    
    # Kontrollera om databas finns
    try:
        companies = get_companies()
        if not companies:
            st.warning("🔧 Ingen data hittad. Kör ETL-processen först för att importera Excel-data.")
            st.markdown("""
            **För att komma igång:**
            1. Kör ETL-scriptet: `python src/etl/excel_to_sqlite.py "Finansiell Data.xlsx"`
            2. Ladda om denna sida
            """)
            return
    except Exception as e:
        st.error(f"Databasfel: {e}")
        st.info("Kontrollera att databasen är korrekt konfigurerad.")
        return
    
    # Företags- och årval
    col1, col2 = st.columns(2)
    
    with col1:
        company_options = {f"{c.name} ({c.location or 'Okänd plats'})": c for c in companies}
        selected_company_name = st.selectbox(
            "Välj företag",
            list(company_options.keys()),
            key="dashboard_company"
        )
        selected_company = company_options[selected_company_name]
    
    with col2:
        available_years = get_years_for_company(selected_company.id)
        if not available_years:
            st.warning(f"Inga år hittade för {selected_company.name}")
            return
        
        selected_year = st.selectbox(
            "Välj år",
            available_years,
            index=len(available_years)-1,  # Senaste året som default
            key="dashboard_year"
        )
    
    # Hämta data för valt företag och år
    try:
        summary_data = calculate_monthly_summary(selected_company.id, selected_year)
    except Exception as e:
        st.error(f"Kunde inte hämta data: {e}")
        return
    
    # KPI-kort
    st.markdown("### 📈 Nyckeltal (YTD)")
    
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    with kpi_col1:
        st.metric(
            "Totala Intäkter",
            format_currency(summary_data['total_revenue']),
            delta=None
        )
    
    with kpi_col2:
        st.metric(
            "Totala Kostnader", 
            format_currency(summary_data['total_expense']),
            delta=None
        )
    
    with kpi_col3:
        result = summary_data['total_result']
        st.metric(
            "Resultat",
            format_currency(result),
            delta=None,
            delta_color="normal" if result >= 0 else "inverse"
        )
    
    with kpi_col4:
        if summary_data['total_revenue'] != 0:
            margin = (result / summary_data['total_revenue']) * 100
            st.metric(
                "Resultatmarginal",
                f"{margin:.1f}%",
                delta=None,
                delta_color="normal" if margin >= 0 else "inverse"
            )
        else:
            st.metric("Resultatmarginal", "N/A")
    
    st.markdown("---")
    
    # Huvuddiagram
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Månatlig översikt")
        fig_monthly = create_revenue_expense_chart(summary_data)
        st.plotly_chart(fig_monthly, use_container_width=True)
    
    with col2:
        st.markdown("### 📈 Year-to-Date trend")
        fig_ytd = create_ytd_comparison_chart(summary_data)
        st.plotly_chart(fig_ytd, use_container_width=True)
    
    # Top konton
    st.markdown("---")
    st.markdown("### 🔝 Största poster")
    
    tab1, tab2 = st.tabs(["💰 Intäkter", "💸 Kostnader"])
    
    with tab1:
        try:
            top_revenues = get_top_accounts(selected_company.id, selected_year, "Intäkter", 10)
            if not top_revenues.empty:
                # Skapa stapeldiagram för intäkter
                fig_rev = px.bar(
                    top_revenues,
                    x='total_amount',
                    y='account_name',
                    orientation='h',
                    title="Top 10 Intäktsposter",
                    color='total_amount',
                    color_continuous_scale='Greens'
                )
                fig_rev.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    xaxis_title="Belopp (SEK)",
                    yaxis_title="Konto"
                )
                st.plotly_chart(fig_rev, use_container_width=True)
                
                # Visa tabell också
                st.dataframe(
                    top_revenues.assign(
                        total_amount=top_revenues['total_amount'].apply(format_currency)
                    ),
                    use_container_width=True
                )
            else:
                st.info("Inga intäktsposter hittade")
        except Exception as e:
            st.error(f"Kunde inte hämta intäktsdata: {e}")
    
    with tab2:
        try:
            top_expenses = get_top_accounts(selected_company.id, selected_year, "Kostnader", 10)
            if not top_expenses.empty:
                # Gör kostnaderna positiva för bättre visualisering
                top_expenses_viz = top_expenses.copy()
                top_expenses_viz['total_amount'] = abs(top_expenses_viz['total_amount'])
                
                # Skapa stapeldiagram för kostnader
                fig_exp = px.bar(
                    top_expenses_viz,
                    x='total_amount',
                    y='account_name',
                    orientation='h',
                    title="Top 10 Kostnadsposter",
                    color='total_amount',
                    color_continuous_scale='Reds'
                )
                fig_exp.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    xaxis_title="Belopp (SEK)",
                    yaxis_title="Konto"
                )
                st.plotly_chart(fig_exp, use_container_width=True)
                
                # Visa tabell också
                st.dataframe(
                    top_expenses.assign(
                        total_amount=top_expenses['total_amount'].apply(format_currency)
                    ),
                    use_container_width=True
                )
            else:
                st.info("Inga kostnadsposter hittade")
        except Exception as e:
            st.error(f"Kunde inte hämta kostnadsdata: {e}")
    
    # Månadstabell
    st.markdown("---")
    st.markdown("### 📅 Månatlig sammanfattning")
    
    # Skapa DataFrame för tabellen
    monthly_df = pd.DataFrame({
        'Månad': summary_data['months'],
        'Intäkter': [format_currency(x) for x in summary_data['revenues']],
        'Kostnader': [format_currency(x) for x in summary_data['expenses']],
        'Resultat': [format_currency(x) for x in summary_data['results']]
    })
    
    st.dataframe(monthly_df, use_container_width=True)
    
    # Footer med metadata
    st.markdown("---")
    st.markdown(f"""
    <small>
    **Data för:** {selected_company.name} - {selected_year}<br>
    **Senast uppdaterad:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
    </small>
    """, unsafe_allow_html=True)
