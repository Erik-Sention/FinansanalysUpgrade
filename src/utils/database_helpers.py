"""
Hjälpfunktioner för databasoperationer
"""
import pandas as pd
from typing import List, Dict, Optional, Tuple
from sqlmodel import Session, select
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from models.database import (
    get_session, get_engine, Company, Dataset, Account, AccountCategory, 
    Value, Budget, BudgetValue, SeasonalityIndex, SeasonalityValue
)

def get_companies() -> List[Company]:
    """Hämta alla företag"""
    with get_session() as session:
        companies = session.exec(select(Company)).all()
        return list(companies)

def get_years_for_company(company_id: int) -> List[int]:
    """Hämta alla år för ett företag"""
    with get_session() as session:
        datasets = session.exec(
            select(Dataset.year).where(Dataset.company_id == company_id).distinct()
        ).all()
        return sorted(list(datasets))

def get_financial_data(company_id: int, year: int, value_type: str = "faktiskt") -> pd.DataFrame:
    """
    Hämta finansiell data för ett företag och år
    Returnerar DataFrame med kolumner: account_name, category, month, amount
    """
    engine = get_engine()
    
    # SQL-query för att hämta data
    query = """
    SELECT 
        a.name as account_name,
        ac.name as category,
        v.month,
        v.amount
    FROM "values" v
    JOIN accounts a ON v.account_id = a.id
    JOIN account_categories ac ON a.category_id = ac.id
    JOIN datasets d ON v.dataset_id = d.id
    WHERE d.company_id = ? AND d.year = ? AND v.value_type = ?
    ORDER BY ac.name, a.name, v.month
    """
    
    df = pd.read_sql_query(
        query, 
        engine, 
        params=(company_id, year, value_type)
    )
    
    return df

def calculate_monthly_summary(company_id: int, year: int) -> Dict:
    """
    Beräkna månatlig sammanfattning (intäkter, kostnader, resultat)
    """
    engine = get_engine()
    
    # Hämta intäkter per månad
    revenue_query = """
    SELECT v.month, SUM(v.amount) as total
    FROM "values" v
    JOIN accounts a ON v.account_id = a.id
    JOIN account_categories ac ON a.category_id = ac.id
    JOIN datasets d ON v.dataset_id = d.id
    WHERE d.company_id = ? AND d.year = ? AND ac.name = 'Intäkter' AND v.value_type = 'faktiskt'
    GROUP BY v.month
    ORDER BY v.month
    """
    
    revenue_df = pd.read_sql_query(
        revenue_query,
        engine,
        params=(company_id, year)
    )
    
    # Hämta kostnader per månad
    expense_query = """
    SELECT v.month, SUM(v.amount) as total
    FROM "values" v
    JOIN accounts a ON v.account_id = a.id
    JOIN account_categories ac ON a.category_id = ac.id
    JOIN datasets d ON v.dataset_id = d.id
    WHERE d.company_id = ? AND d.year = ? AND ac.name = 'Kostnader' AND v.value_type = 'faktiskt'
    GROUP BY v.month
    ORDER BY v.month
    """
    
    expense_df = pd.read_sql_query(
        expense_query,
        engine,
        params=(company_id, year)
    )
    
    # Skapa fullständig månadsserie (1-12)
    months = list(range(1, 13))
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
    
    revenues = []
    expenses = []
    
    for month in months:
        rev_row = revenue_df[revenue_df['month'] == month]
        exp_row = expense_df[expense_df['month'] == month]
        
        revenue = rev_row['total'].iloc[0] if len(rev_row) > 0 else 0
        expense = exp_row['total'].iloc[0] if len(exp_row) > 0 else 0
        
        revenues.append(revenue)
        expenses.append(expense)
    
    results = [rev - exp for rev, exp in zip(revenues, expenses)]
    
    return {
        'months': month_names,
        'revenues': revenues,
        'expenses': expenses,
        'results': results,
        'total_revenue': sum(revenues),
        'total_expense': sum(expenses),
        'total_result': sum(results)
    }

def get_budget_comparison(company_id: int, year: int) -> pd.DataFrame:
    """
    Jämför faktiska värden med budget
    """
    engine = get_engine()
    
    query = """
    SELECT 
        a.name as account_name,
        ac.name as category,
        v.month,
        v.amount,
        v.value_type
    FROM "values" v
    JOIN accounts a ON v.account_id = a.id
    JOIN account_categories ac ON a.category_id = ac.id
    JOIN datasets d ON v.dataset_id = d.id
    WHERE d.company_id = ? AND d.year = ?
    ORDER BY ac.name, a.name, v.month, v.value_type
    """
    
    df = pd.read_sql_query(
        query,
        engine,
        params=(company_id, year)
    )
    
    return df

def create_revenue_expense_chart(summary_data: Dict) -> go.Figure:
    """
    Skapa diagram för intäkter vs kostnader
    """
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=summary_data['months'],
        y=summary_data['revenues'],
        name='Intäkter',
        marker_color='#2E8B57'
    ))
    
    fig.add_trace(go.Bar(
        x=summary_data['months'],
        y=summary_data['expenses'],
        name='Kostnader',
        marker_color='#DC143C'
    ))
    
    fig.add_trace(go.Scatter(
        x=summary_data['months'],
        y=summary_data['results'],
        mode='lines+markers',
        name='Resultat',
        line=dict(color='#4169E1', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title='Månatlig översikt - Intäkter vs Kostnader',
        xaxis_title='Månad',
        yaxis_title='Belopp (SEK)',
        barmode='group',
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig

def create_ytd_comparison_chart(summary_data: Dict) -> go.Figure:
    """
    Skapa YTD-jämförelsediagram
    """
    # Beräkna ackumulerade värden
    ytd_revenues = []
    ytd_expenses = []
    ytd_results = []
    
    running_revenue = 0
    running_expense = 0
    
    for rev, exp in zip(summary_data['revenues'], summary_data['expenses']):
        running_revenue += rev
        running_expense += exp
        
        ytd_revenues.append(running_revenue)
        ytd_expenses.append(running_expense)
        ytd_results.append(running_revenue - running_expense)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=summary_data['months'],
        y=ytd_revenues,
        mode='lines+markers',
        name='YTD Intäkter',
        line=dict(color='#2E8B57', width=3),
        marker=dict(size=6)
    ))
    
    fig.add_trace(go.Scatter(
        x=summary_data['months'],
        y=ytd_expenses,
        mode='lines+markers',
        name='YTD Kostnader',
        line=dict(color='#DC143C', width=3),
        marker=dict(size=6)
    ))
    
    fig.add_trace(go.Scatter(
        x=summary_data['months'],
        y=ytd_results,
        mode='lines+markers',
        name='YTD Resultat',
        line=dict(color='#4169E1', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title='Year-to-Date (YTD) utveckling',
        xaxis_title='Månad',
        yaxis_title='Ackumulerat belopp (SEK)',
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig

def get_top_accounts(company_id: int, year: int, category: str, limit: int = 10) -> pd.DataFrame:
    """
    Hämta top N konton för en kategori
    """
    engine = get_engine()
    
    query = """
    SELECT 
        a.name as account_name,
        SUM(v.amount) as total_amount
    FROM "values" v
    JOIN accounts a ON v.account_id = a.id
    JOIN account_categories ac ON a.category_id = ac.id
    JOIN datasets d ON v.dataset_id = d.id
    WHERE d.company_id = ? AND d.year = ? AND ac.name = ? AND v.value_type = 'faktiskt'
    GROUP BY a.id, a.name
    ORDER BY ABS(total_amount) DESC
    LIMIT ?
    """
    
    df = pd.read_sql_query(
        query,
        engine,
        params=(company_id, year, category, limit)
    )
    
    return df

def format_currency(amount: float) -> str:
    """Formatera belopp som valuta"""
    return f"{amount:,.0f} SEK".replace(',', ' ')

def get_account_categories() -> List[AccountCategory]:
    """Hämta alla kontokategorier"""
    with get_session() as session:
        categories = session.exec(select(AccountCategory)).all()
        return list(categories)
