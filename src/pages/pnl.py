"""
P&L (Resultaträkning) sida
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Optional

from utils.database_helpers import (
    get_companies, get_years_for_company, get_financial_data,
    get_budget_comparison, format_currency
)

def show():
    """Visa P&L-sidan"""
    st.title("📋 Resultaträkning (P&L)")
    st.markdown("Detaljerad resultaträkning med jämförelse mot budget")
    
    # Kontrollera databas
    try:
        companies = get_companies()
        if not companies:
            st.warning("🔧 Ingen data hittad. Kör ETL-processen först.")
            return
    except Exception as e:
        st.error(f"Databasfel: {e}")
        return
    
    # Företags- och årval
    col1, col2 = st.columns(2)
    
    with col1:
        company_options = {f"{c.name} ({c.location or 'Okänd plats'})": c for c in companies}
        selected_company_name = st.selectbox(
            "Välj företag",
            list(company_options.keys()),
            key="pnl_company"
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
            index=len(available_years)-1,
            key="pnl_year"
        )
    
    # Visa/dölj alternativ
    st.markdown("### ⚙️ Visningsalternativ")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        show_budget = st.checkbox("Visa budget", value=True)
    with col2:
        show_variance = st.checkbox("Visa avvikelse", value=True)
    with col3:
        show_percentage = st.checkbox("Visa procent", value=False)
    
    # Hämta data
    try:
        # Hämta faktiska värden
        actual_data = get_financial_data(selected_company.id, selected_year, "faktiskt")
        
        # Hämta budgetdata om vald
        budget_data = None
        if show_budget:
            budget_data = get_financial_data(selected_company.id, selected_year, "budget")
        
        if actual_data.empty:
            st.warning("Ingen data hittad för valt företag och år")
            return
        
    except Exception as e:
        st.error(f"Kunde inte hämta data: {e}")
        return
    
    # Bygg P&L-tabellen
    st.markdown("---")
    st.markdown(f"### 📊 Resultaträkning - {selected_company.name} {selected_year}")
    
    # Skapa pivot-tabell för faktiska värden
    actual_pivot = actual_data.pivot_table(
        index=['category', 'account_name'],
        columns='month',
        values='amount',
        aggfunc='sum',
        fill_value=0
    )
    
    # Skapa budget pivot om budget finns
    budget_pivot = None
    if budget_data is not None and not budget_data.empty:
        budget_pivot = budget_data.pivot_table(
            index=['category', 'account_name'],
            columns='month',
            values='amount',
            aggfunc='sum',
            fill_value=0
        )
    
    # Månadsnamn
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
    
    # Bygg resultaträkning per kategori
    for category in ['Intäkter', 'Kostnader']:
        if category in actual_pivot.index.get_level_values(0):
            st.markdown(f"#### 💰 {category}")
            
            # Filtrera data för denna kategori
            category_data = actual_pivot.loc[category]
            
            # Säkerställ att alla månader finns (1-12)
            for month in range(1, 13):
                if month not in category_data.columns:
                    category_data[month] = 0
            
            # Sortera kolumner
            category_data = category_data.reindex(sorted(category_data.columns), axis=1)
            
            # Byt namn på kolumner till månadnamn
            category_data.columns = [month_names[i-1] for i in category_data.columns]
            
            # Lägg till YTD-kolumn
            category_data['YTD'] = category_data.sum(axis=1)
            
            # Budget-data om tillgänglig
            if budget_pivot is not None and category in budget_pivot.index.get_level_values(0):
                budget_category = budget_pivot.loc[category]
                
                # Säkerställ samma struktur
                for month in range(1, 13):
                    if month not in budget_category.columns:
                        budget_category[month] = 0
                
                budget_category = budget_category.reindex(sorted(budget_category.columns), axis=1)
                budget_category.columns = [month_names[i-1] for i in budget_category.columns]
                budget_category['YTD'] = budget_category.sum(axis=1)
                
                # Kombinera faktiskt och budget
                display_data = pd.DataFrame()
                
                for account in category_data.index:
                    actual_row = category_data.loc[account]
                    budget_row = budget_category.loc[account] if account in budget_category.index else pd.Series(0, index=actual_row.index)
                    variance_row = actual_row - budget_row
                    
                    # Lägg till rader
                    display_data.loc[f"{account} (Faktiskt)", :] = actual_row
                    if show_budget:
                        display_data.loc[f"{account} (Budget)", :] = budget_row
                    if show_variance:
                        display_data.loc[f"{account} (Avvikelse)", :] = variance_row
            else:
                display_data = category_data
            
            # Formatera som valuta
            formatted_data = display_data.map(format_currency)
            
            # Visa tabell
            st.dataframe(formatted_data, use_container_width=True)
            
            # Visa diagram för denna kategori
            if len(category_data) > 0:
                fig = px.bar(
                    x=category_data.columns[:-1],  # Exkludera YTD
                    y=category_data.sum(axis=0)[:-1],  # Exkludera YTD
                    title=f"{category} per månad",
                    labels={'x': 'Månad', 'y': 'Belopp (SEK)'},
                    color_discrete_sequence=['#2E8B57' if category == 'Intäkter' else '#DC143C']
                )
                fig.update_layout(template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
    
    # Sammanfattning
    st.markdown("---")
    st.markdown("#### 📊 Sammanfattning")
    
    # Beräkna totaler per månad
    total_revenue = pd.Series(0, index=range(1, 13))
    total_expenses = pd.Series(0, index=range(1, 13))
    
    if 'Intäkter' in actual_pivot.index.get_level_values(0):
        revenue_data = actual_pivot.loc['Intäkter']
        for month in range(1, 13):
            if month in revenue_data.columns:
                total_revenue[month] = revenue_data[month].sum()
    
    if 'Kostnader' in actual_pivot.index.get_level_values(0):
        expense_data = actual_pivot.loc['Kostnader']
        for month in range(1, 13):
            if month in expense_data.columns:
                total_expenses[month] = expense_data[month].sum()
    
    results = total_revenue - total_expenses
    
    # Skapa sammanfattningstabelle
    summary_data = pd.DataFrame({
        'Intäkter': [format_currency(x) for x in total_revenue],
        'Kostnader': [format_currency(x) for x in total_expenses],
        'Resultat': [format_currency(x) for x in results]
    }, index=month_names)
    
    # Lägg till YTD
    summary_data.loc['YTD'] = [
        format_currency(total_revenue.sum()),
        format_currency(total_expenses.sum()),
        format_currency(results.sum())
    ]
    
    st.dataframe(summary_data, use_container_width=True)
    
    # Resultatdiagram
    fig_result = px.bar(
        x=month_names,
        y=results,
        title="Månadsresultat",
        labels={'x': 'Månad', 'y': 'Resultat (SEK)'},
        color=results,
        color_continuous_scale='RdYlGn'
    )
    fig_result.update_layout(template='plotly_white')
    st.plotly_chart(fig_result, use_container_width=True)
    
    # Export-knapp
    st.markdown("---")
    if st.button("📄 Exportera P&L till Excel"):
        try:
            # Skapa Excel-fil i minnet
            import io
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Exportera sammanfattning
                summary_data.to_excel(writer, sheet_name='Sammanfattning')
                
                # Exportera detaljer per kategori
                for category in ['Intäkter', 'Kostnader']:
                    if category in actual_pivot.index.get_level_values(0):
                        category_data = actual_pivot.loc[category]
                        category_data.to_excel(writer, sheet_name=category)
            
            output.seek(0)
            
            st.download_button(
                label="💾 Ladda ner Excel-fil",
                data=output.getvalue(),
                file_name=f"PL_{selected_company.name}_{selected_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            st.error(f"Kunde inte skapa Excel-fil: {e}")
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <small>
    **P&L för:** {selected_company.name} - {selected_year}<br>
    **Genererad:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
    </small>
    """, unsafe_allow_html=True)
