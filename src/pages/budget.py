"""
Budget-editor sida
"""
import streamlit as st
import pandas as pd
from typing import Optional, Dict, List
from sqlmodel import Session, select

from utils.database_helpers import (
    get_companies, get_years_for_company, format_currency, get_session
)
from models.database import (
    Budget, BudgetValue, Account, AccountCategory, Company, Dataset
)

def get_budget_for_company_year(company_id: int, year: int) -> Optional[Budget]:
    """Hämta budget för företag och år"""
    with get_session() as session:
        budget = session.exec(
            select(Budget).where(
                Budget.company_id == company_id,
                Budget.year == year
            )
        ).first()
        return budget

def get_budget_values(budget_id: int) -> pd.DataFrame:
    """Hämta budgetvärden som DataFrame"""
    from models.database import get_engine
    engine = get_engine()
    
    query = """
    SELECT 
        a.name as account_name,
        ac.name as category,
        bv.month,
        bv.amount,
        a.id as account_id
    FROM budget_values bv
    JOIN accounts a ON bv.account_id = a.id
    JOIN account_categories ac ON a.category_id = ac.id
    WHERE bv.budget_id = ?
    ORDER BY ac.name, a.name, bv.month
    """
    
    df = pd.read_sql_query(
        query,
        engine,
        params=(budget_id,)
    )
    
    return df

def get_available_accounts(company_id: int, year: int) -> pd.DataFrame:
    """Hämta tillgängliga konton för företag och år"""
    from models.database import get_engine
    engine = get_engine()
    
    query = """
    SELECT DISTINCT a.id, a.name, ac.name as category_name
    FROM accounts a
    JOIN account_categories ac ON a.category_id = ac.id
    JOIN "values" v ON a.id = v.account_id
    JOIN datasets d ON v.dataset_id = d.id
    WHERE d.company_id = ? AND d.year = ?
    ORDER BY ac.name, a.name
    """
    
    df = pd.read_sql_query(query, engine, params=(company_id, year))
    return df

def create_or_update_budget(company_id: int, year: int, budget_data: Dict) -> bool:
    """Skapa eller uppdatera budget"""
    try:
        with get_session() as session:
            # Hämta eller skapa budget
            budget = session.exec(
                select(Budget).where(
                    Budget.company_id == company_id,
                    Budget.year == year
                )
            ).first()
            
            if not budget:
                budget = Budget(
                    company_id=company_id,
                    year=year,
                    name=f"Budget {year}"
                )
                session.add(budget)
                session.commit()
                session.refresh(budget)
            
            # Ta bort befintliga budgetvärden
            session.exec(
                "DELETE FROM budget_values WHERE budget_id = ?",
                params=(budget.id,)
            )
            
            # Lägg till nya budgetvärden
            for account_id, months_data in budget_data.items():
                for month, amount in months_data.items():
                    if amount != 0:  # Spara bara icke-noll värden
                        budget_value = BudgetValue(
                            budget_id=budget.id,
                            account_id=account_id,
                            month=month,
                            amount=amount
                        )
                        session.add(budget_value)
            
            session.commit()
            return True
            
    except Exception as e:
        st.error(f"Fel vid sparande av budget: {e}")
        return False

def show():
    """Visa budget-editor sidan"""
    st.title("💰 Budget Editor")
    st.markdown("Skapa och redigera budgetar för företag")
    
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
            key="budget_company"
        )
        selected_company = company_options[selected_company_name]
    
    with col2:
        available_years = get_years_for_company(selected_company.id)
        
        # Lägg till möjlighet att skapa budget för nästa år
        current_max_year = max(available_years) if available_years else 2024
        extended_years = available_years + [current_max_year + 1]
        
        selected_year = st.selectbox(
            "Välj år",
            extended_years,
            index=len(extended_years)-1,  # Nästa år som default
            key="budget_year"
        )
    
    # Kontrollera om budget redan finns
    existing_budget = get_budget_for_company_year(selected_company.id, selected_year)
    
    if existing_budget:
        st.success(f"✅ Budget finns för {selected_company.name} {selected_year}")
        st.info(f"Skapad: {existing_budget.created_at.strftime('%Y-%m-%d %H:%M')}")
    else:
        st.info(f"💡 Ingen budget hittad för {selected_company.name} {selected_year}")
    
    # Hämta tillgängliga konton
    try:
        # Använd föregående år som bas om budget för nytt år
        base_year = selected_year if selected_year in available_years else max(available_years)
        accounts_df = get_available_accounts(selected_company.id, base_year)
            
        if accounts_df.empty:
            st.warning("Inga konton hittade för detta företag och år")
            return
            
    except Exception as e:
        st.error(f"Kunde inte hämta konton: {e}")
        return
    
    # Hämta befintliga budgetvärden om budget finns
    budget_df = pd.DataFrame()
    if existing_budget:
        try:
            budget_df = get_budget_values(existing_budget.id)
        except Exception as e:
            st.error(f"Kunde inte hämta budgetdata: {e}")
    
    # Budget-editor interface
    st.markdown("---")
    st.markdown("### ✏️ Redigera Budget")
    
    # Månadsnamn
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
    
    # Gruppera konton per kategori
    budget_data = {}
    categories = accounts_df['category_name'].unique()
    
    # Tabs per kategori
    category_tabs = st.tabs([f"💰 {cat}" for cat in categories])
    
    for i, category in enumerate(categories):
        with category_tabs[i]:
            st.markdown(f"#### {category}")
            
            category_accounts = accounts_df[accounts_df['category_name'] == category]
            
            for _, account_row in category_accounts.iterrows():
                account_id = account_row['id']
                account_name = account_row['name']
                
                # Hämta befintliga värden för detta konto
                existing_values = {}
                if not budget_df.empty:
                    account_budget = budget_df[budget_df['account_id'] == account_id]
                    for _, row in account_budget.iterrows():
                        existing_values[row['month']] = row['amount']
                
                st.markdown(f"**{account_name}**")
                
                # Skapa kolumner för månader
                month_cols = st.columns(6)
                account_budget_values = {}
                
                for month_idx in range(12):
                    month_num = month_idx + 1
                    month_name = month_names[month_idx]
                    col_idx = month_idx % 6
                    
                    # Ny rad efter 6 månader
                    if month_idx == 6:
                        month_cols = st.columns(6)
                        col_idx = 0
                    
                    with month_cols[col_idx]:
                        default_value = existing_values.get(month_num, 0.0)
                        value = st.number_input(
                            month_name,
                            value=float(default_value),
                            key=f"budget_{account_id}_{month_num}",
                            step=1000.0,
                            format="%.0f"
                        )
                        account_budget_values[month_num] = value
                
                budget_data[account_id] = account_budget_values
                
                # Visa årssum
                total = sum(account_budget_values.values())
                st.markdown(f"*Årssum: {format_currency(total)}*")
                st.markdown("---")
    
    # Spara-knapp
    st.markdown("### 💾 Spara Budget")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Spara Budget", type="primary"):
            if create_or_update_budget(selected_company.id, selected_year, budget_data):
                st.success("✅ Budget sparad framgångsrikt!")
                st.rerun()
            else:
                st.error("❌ Kunde inte spara budget")
    
    with col2:
        if existing_budget and st.button("🗑️ Radera Budget"):
            try:
                with get_session() as session:
                    # Ta bort budgetvärden
                    session.exec(
                        "DELETE FROM budget_values WHERE budget_id = ?",
                        params=(existing_budget.id,)
                    )
                    # Ta bort budget
                    session.delete(existing_budget)
                    session.commit()
                
                st.success("✅ Budget raderad!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Kunde inte radera budget: {e}")
    
    with col3:
        if st.button("📋 Kopiera från föregående år"):
            if available_years:
                prev_year = max([y for y in available_years if y < selected_year] + [selected_year - 1])
                prev_budget = get_budget_for_company_year(selected_company.id, prev_year)
                
                if prev_budget:
                    prev_budget_df = get_budget_values(prev_budget.id)
                    
                    # Kopiera data
                    copied_data = {}
                    for account_id in budget_data.keys():
                        account_prev = prev_budget_df[prev_budget_df['account_id'] == account_id]
                        copied_values = {}
                        
                        for month in range(1, 13):
                            month_data = account_prev[account_prev['month'] == month]
                            copied_values[month] = month_data['amount'].iloc[0] if len(month_data) > 0 else 0.0
                        
                        copied_data[account_id] = copied_values
                    
                    if create_or_update_budget(selected_company.id, selected_year, copied_data):
                        st.success(f"✅ Budget kopierad från {prev_year}!")
                        st.rerun()
                    else:
                        st.error("❌ Kunde inte kopiera budget")
                else:
                    st.warning(f"Ingen budget hittad för {prev_year}")
            else:
                st.warning("Inga tidigare år tillgängliga")
    
    # Budget-sammanfattning
    if budget_data:
        st.markdown("---")
        st.markdown("### 📊 Budget Sammanfattning")
        
        # Beräkna totaler per kategori
        category_totals = {}
        monthly_totals = {month: 0 for month in range(1, 13)}
        
        for account_id, months_data in budget_data.items():
            account_info = accounts_df[accounts_df['id'] == account_id].iloc[0]
            category = account_info['category_name']
            
            if category not in category_totals:
                category_totals[category] = 0
            
            account_total = sum(months_data.values())
            category_totals[category] += account_total
            
            for month, amount in months_data.items():
                monthly_totals[month] += amount
        
        # Visa kategoritotaler
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Totaler per kategori:**")
            for category, total in category_totals.items():
                st.metric(category, format_currency(total))
        
        with col2:
            # Beräkna resultat
            revenue_total = category_totals.get('Intäkter', 0)
            expense_total = category_totals.get('Kostnader', 0)
            result = revenue_total - expense_total
            
            st.markdown("**Resultat:**")
            st.metric("Budget Resultat", format_currency(result),
                     delta_color="normal" if result >= 0 else "inverse")
        
        # Månadsvis sammanfattning
        st.markdown("**Månatlig budget:**")
        monthly_summary = pd.DataFrame({
            'Månad': month_names,
            'Budget': [format_currency(monthly_totals[i+1]) for i in range(12)]
        })
        st.dataframe(monthly_summary, use_container_width=True)
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <small>
    **Budget för:** {selected_company.name} - {selected_year}<br>
    **Senast redigerad:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
    </small>
    """, unsafe_allow_html=True)
