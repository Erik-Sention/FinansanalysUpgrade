"""
Optimerad Excel-vy med effektiv sparning av enskilda celler
"""
import streamlit as st
import pandas as pd
import time
from datetime import datetime
from src.models.database import get_companies, get_financial_data_with_categories, get_budget_data, get_all_categories, update_account_category
from src.models.firebase_database import get_firebase_db
from typing import Dict, Any

# Import original functions
from src.pages.excel_view import (
    get_years_for_company, 
    create_excel_table_with_categories,
    collect_budget_updates
)

def save_single_budget_cell(company_id: str, year: int, account_id: str, month: int, amount: float) -> bool:
    """
    Spara en enskild budget-cell effektivt till Firebase
    
    Args:
        company_id: Företagets ID
        year: År för budgeten
        account_id: Kontots ID  
        month: Månad (1-12)
        amount: Belopp att spara
    
    Returns:
        bool: True om sparning lyckades
    """
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
            st.info(f"📝 Skapade ny budget för {year}")
        
        # Spara endast denna cell
        firebase_db.update_budget_value(target_budget_id, str(account_id), int(month), float(amount))
        
        # Visa sparningsbekräftelse
        month_names = ['Jan','Feb','Mar','Apr','Maj','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
        month_name = month_names[month-1] if 1 <= month <= 12 else str(month)
        
        if abs(amount) <= 1e-9:  # Nollvärde
            st.success(f"🗑️ Tog bort värde för {month_name}")
        else:
            st.success(f"💾 Sparade {amount:,.0f} kr för {month_name}")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Fel vid sparande av cell: {e}")
        return False

def create_interactive_budget_grid(category_data: pd.DataFrame, category: str, company_id: str, year: int) -> pd.DataFrame:
    """
    Skapa interaktiv budget-grid med cell-för-cell sparning
    
    Args:
        category_data: Data för kategorin
        category: Kategorinamn  
        company_id: Företagets ID
        year: År för budgeten
        
    Returns:
        pd.DataFrame: Redigerat data
    """
    
    # Skapa grid med konto-namn och månader
    grid_data = []
    for _, row in category_data.iterrows():
        grid_row = {
            'Konto': row['account'],
            'account_id': row['account_id']
        }
        
        # Lägg till månadskolumner med befintliga värden
        month_names = ['Jan','Feb','Mar','Apr','Maj','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
        for i, month_name in enumerate(month_names, 1):
            # Hämta befintligt värde från budget_df om det finns
            existing_value = row.get(f'budget_month_{i}', 0.0)
            grid_row[month_name] = existing_value
        
        grid_data.append(grid_row)
    
    grid_df = pd.DataFrame(grid_data)
    
    # Kolumnkonfiguration för redigering
    column_config = {
        'Konto': st.column_config.TextColumn(label='Konto', width='large', disabled=True),
        'account_id': st.column_config.TextColumn(label='account_id', disabled=True, width='small'),
    }
    
    # Lägg till månadskolumner
    for month_name in ['Jan','Feb','Mar','Apr','Maj','Jun','Jul','Aug','Sep','Okt','Nov','Dec']:
        column_config[month_name] = st.column_config.NumberColumn(
            label=month_name, 
            step=1000.0, 
            format="%.0f"
        )
    
    # Visa redigerbar tabell
    edited_df = st.data_editor(
        grid_df,
        hide_index=True,
        column_config=column_config,
        use_container_width=True,
        key=f"optimized_grid_{category}",
        on_change=None,  # Vi hanterar ändringar manuellt
        disabled=['Konto', 'account_id']
    )
    
    return edited_df

def detect_and_save_changes(original_df: pd.DataFrame, edited_df: pd.DataFrame, 
                           company_id: str, year: int, category: str) -> int:
    """
    Detektera ändringar och spara endast de celler som ändrats
    
    Args:
        original_df: Ursprunglig data
        edited_df: Redigerad data
        company_id: Företagets ID
        year: År
        category: Kategorinamn
        
    Returns:
        int: Antal sparade celler
    """
    changes_saved = 0
    month_names = ['Jan','Feb','Mar','Apr','Maj','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
    
    # Jämför rad för rad
    for idx in range(len(edited_df)):
        account_id = edited_df.iloc[idx]['account_id']
        account_name = edited_df.iloc[idx]['Konto']
        
        # Jämför månadskolumner
        for month_idx, month_name in enumerate(month_names, 1):
            old_value = original_df.iloc[idx][month_name] if idx < len(original_df) else 0.0
            new_value = edited_df.iloc[idx][month_name]
            
            # Kontrollera om värdet ändrats (med tolerans för flyttal)
            if abs(old_value - new_value) > 1e-6:
                # Spara den ändrade cellen
                if save_single_budget_cell(company_id, year, account_id, month_idx, new_value):
                    changes_saved += 1
                    
                    # Visa vilken ändring som gjordes
                    with st.expander(f"📝 Ändring sparad för {account_name}", expanded=False):
                        st.write(f"**Månad:** {month_name}")
                        st.write(f"**Gammalt värde:** {old_value:,.0f} kr")
                        st.write(f"**Nytt värde:** {new_value:,.0f} kr")
                        st.write(f"**Differens:** {new_value - old_value:+,.0f} kr")
    
    return changes_saved

def show_optimized():
    """
    Visa optimerad finansdatabas-sida med cell-för-cell sparning
    """
    st.title("💾 Finansdatabas (Optimerad)")
    st.markdown("Hantera och redigera företagets finansiella data med intelligent cellsparning")
    
    # Info om optimering
    with st.expander("ℹ️ Om den optimerade versionen", expanded=False):
        st.markdown("""
        **Förbättringar:**
        - 🎯 Sparar endast de celler som faktiskt ändrats
        - ⚡ Snabbare prestanda - ingen massa-sparning 
        - 🔍 Visar exakt vilka ändringar som gjorts
        - 💾 Effektivare databasanvändning
        - ⏱️ Omedelbar sparning när du klickar "Spara ändringar"
        """)
    
    # Hämta företag
    companies_list = get_companies()
    if not companies_list:
        st.warning("🔧 Ingen data hittad. Kör ETL-processen först.")
        return
    
    # Företagsval
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
    
    if actual_df.empty:
        st.warning("Ingen data hittad för valt företag och år")
        return
    
    # Skapa tabellen med kategorival
    table_df = create_excel_table_with_categories(actual_df, budget_df)
    
    if not table_df.empty:
        st.markdown("### 📊 Budget-redigering per kategori")
        
        # Dela upp i kategorier för redigering
        categories = table_df['category'].unique()
        
        # Skapa tabs för varje kategori
        tabs = st.tabs([f"💰 {cat}" for cat in categories])
        
        # Spara original data för jämförelse
        if 'original_data' not in st.session_state:
            st.session_state.original_data = {}
        
        for i, category in enumerate(categories):
            with tabs[i]:
                st.markdown(f"### Budget för {category}")
                
                # Filtrera data för denna kategori
                category_data = table_df[table_df['category'] == category].copy()
                
                # Skapa interaktiv grid
                original_grid = create_interactive_budget_grid(category_data, category, selected_company_id, selected_year)
                
                # Spara original data första gången
                if f"{category}_{selected_company_id}_{selected_year}" not in st.session_state.original_data:
                    st.session_state.original_data[f"{category}_{selected_company_id}_{selected_year}"] = original_grid.copy()
                
                # Knappar för sparning
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"💾 Spara ändringar – {category}", type="primary", key=f"save_changes_{category}"):
                        original_key = f"{category}_{selected_company_id}_{selected_year}"
                        original_data = st.session_state.original_data.get(original_key, original_grid)
                        
                        # Detektera och spara ändringar
                        changes_saved = detect_and_save_changes(
                            original_data, 
                            original_grid,  # Använd current state från data_editor
                            selected_company_id, 
                            selected_year, 
                            category
                        )
                        
                        if changes_saved > 0:
                            st.success(f"✅ {changes_saved} ändringar sparade för {category}")
                            # Uppdatera original data
                            st.session_state.original_data[original_key] = original_grid.copy()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.info("ℹ️ Inga ändringar att spara")
                
                with col2:
                    if st.button(f"🔄 Återställ – {category}", key=f"reset_{category}"):
                        # Återställ till original data
                        original_key = f"{category}_{selected_company_id}_{selected_year}"
                        if original_key in st.session_state.original_data:
                            del st.session_state.original_data[original_key]
                        st.rerun()
                
                with col3:
                    if st.button(f"📊 Visa sammanfattning – {category}", key=f"summary_{category}"):
                        # Visa kategorisammanfattning
                        with st.expander(f"Sammanfattning för {category}", expanded=True):
                            month_names = ['Jan','Feb','Mar','Apr','Maj','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
                            
                            for month_name in month_names:
                                month_total = original_grid[month_name].sum()
                                if abs(month_total) > 1e-6:
                                    st.write(f"**{month_name}:** {month_total:,.0f} kr")
                            
                            year_total = sum(original_grid[month].sum() for month in month_names)
                            st.write(f"**Årssum:** {year_total:,.0f} kr")
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <small>
    **Data för:** {selected_company_name} - {selected_year}<br>
    **💾 Firebase Realtime Database (Optimerad)**<br>
    **🎯 Intelligent cellsparning aktiverad**
    </small>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    show_optimized()
