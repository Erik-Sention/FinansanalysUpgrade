"""
Hjälpfunktioner för Firebase databasoperationer
"""
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from models_firebase_database import get_firebase_db

def get_companies() -> List[Dict]:
    """Hämta alla företag"""
    firebase_db = get_firebase_db()
    companies_dict = firebase_db.get_companies()
    
    companies = []
    for company_id, company_data in companies_dict.items():
        company_data['id'] = company_id
        companies.append(company_data)
    
    return companies

def get_years_for_company(company_id: str) -> List[int]:
    """Hämta alla år för ett företag"""
    firebase_db = get_firebase_db()
    datasets = firebase_db.get_datasets(company_id)
    
    years = set()
    for dataset_data in datasets.values():
        years.add(dataset_data.get('year'))
    
    return sorted(list(years))

def get_financial_data(company_id: str, year: int, value_type: str = "faktiskt") -> pd.DataFrame:
    """
    Hämta finansiell data för ett företag och år
    Returnerar DataFrame med kolumner: account_name, category, month, amount
    """
    firebase_db = get_firebase_db()
    
    # Hämta datasets för företaget och året
    datasets = firebase_db.get_datasets(company_id)
    target_dataset_id = None
    for dataset_id, dataset_data in datasets.items():
        if dataset_data.get('year') == year:
            target_dataset_id = dataset_id
            break
    
    if not target_dataset_id:
        return pd.DataFrame(columns=['account_name', 'category', 'month', 'amount'])
    
    # Hämta värden för dataset
    values = firebase_db.get_values(dataset_id=target_dataset_id)
    
    # Hämta referensdata
    accounts = firebase_db.get_accounts()
    categories = firebase_db.get_account_categories()
    
    # Bygg DataFrame
    data = []
    for value_id, value_data in values.items():
        if value_data.get('value_type') != value_type:
            continue
            
        account_id = value_data.get('account_id')
        account_data = accounts.get(account_id, {})
        
        category_id = account_data.get('category_id')
        category_data = categories.get(category_id, {})
        
        data.append({
            'account_name': account_data.get('name', 'Okänt konto'),
            'category': category_data.get('name', 'Okänd kategori'),
            'month': value_data.get('month'),
            'amount': value_data.get('amount', 0)
        })
    
    df = pd.DataFrame(data)
    
    if not df.empty:
        df = df.sort_values(['category', 'account_name', 'month'])
    
    return df

def calculate_monthly_summary(company_id: str, year: int) -> Dict:
    """
    Beräkna månatlig sammanfattning (intäkter, kostnader, resultat)
    """
    firebase_db = get_firebase_db()
    
    # Hämta datasets för företaget och året
    datasets = firebase_db.get_datasets(company_id)
    target_dataset_id = None
    for dataset_id, dataset_data in datasets.items():
        if dataset_data.get('year') == year:
            target_dataset_id = dataset_id
            break
    
    if not target_dataset_id:
        # Returnera tom data
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
        return {
            'months': month_names,
            'revenues': [0] * 12,
            'expenses': [0] * 12,
            'results': [0] * 12,
            'total_revenue': 0,
            'total_expense': 0,
            'total_result': 0
        }
    
    # Hämta alla värden för dataset
    values = firebase_db.get_values(dataset_id=target_dataset_id)
    
    # Hämta referensdata
    accounts = firebase_db.get_accounts()
    categories = firebase_db.get_account_categories()
    
    # Hitta kategori-IDs
    revenue_category_id = None
    expense_category_id = None
    for cat_id, cat_data in categories.items():
        if cat_data.get('name') == 'Intäkter':
            revenue_category_id = cat_id
        elif cat_data.get('name') == 'Kostnader':
            expense_category_id = cat_id
    
    # Organisera data per månad
    monthly_revenues = {i: 0 for i in range(1, 13)}
    monthly_expenses = {i: 0 for i in range(1, 13)}
    
    for value_data in values.values():
        if value_data.get('value_type') != 'faktiskt':
            continue
            
        account_id = value_data.get('account_id')
        account_data = accounts.get(account_id, {})
        category_id = account_data.get('category_id')
        
        month = value_data.get('month')
        amount = value_data.get('amount', 0)
        
        if category_id == revenue_category_id:
            monthly_revenues[month] += amount
        elif category_id == expense_category_id:
            monthly_expenses[month] += amount
    
    # Skapa listor för visualisering
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']
    
    revenues = [monthly_revenues[i] for i in range(1, 13)]
    expenses = [monthly_expenses[i] for i in range(1, 13)]
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

def get_budget_comparison(company_id: str, year: int) -> pd.DataFrame:
    """
    Jämför faktiska värden med budget
    """
    firebase_db = get_firebase_db()
    
    # Hämta datasets för företaget och året
    datasets = firebase_db.get_datasets(company_id)
    target_dataset_id = None
    for dataset_id, dataset_data in datasets.items():
        if dataset_data.get('year') == year:
            target_dataset_id = dataset_id
            break
    
    if not target_dataset_id:
        return pd.DataFrame(columns=['account_name', 'category', 'month', 'amount', 'value_type'])
    
    # Hämta alla värden för dataset
    values = firebase_db.get_values(dataset_id=target_dataset_id)
    
    # Hämta referensdata
    accounts = firebase_db.get_accounts()
    categories = firebase_db.get_account_categories()
    
    # Bygg DataFrame
    data = []
    for value_data in values.values():
        account_id = value_data.get('account_id')
        account_data = accounts.get(account_id, {})
        
        category_id = account_data.get('category_id')
        category_data = categories.get(category_id, {})
        
        data.append({
            'account_name': account_data.get('name', 'Okänt konto'),
            'category': category_data.get('name', 'Okänd kategori'),
            'month': value_data.get('month'),
            'amount': value_data.get('amount', 0),
            'value_type': value_data.get('value_type')
        })
    
    df = pd.DataFrame(data)
    
    if not df.empty:
        df = df.sort_values(['category', 'account_name', 'month', 'value_type'])
    
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

def get_top_accounts(company_id: str, year: int, category: str, limit: int = 10) -> pd.DataFrame:
    """
    Hämta top N konton för en kategori
    """
    firebase_db = get_firebase_db()
    
    # Hämta datasets för företaget och året
    datasets = firebase_db.get_datasets(company_id)
    target_dataset_id = None
    for dataset_id, dataset_data in datasets.items():
        if dataset_data.get('year') == year:
            target_dataset_id = dataset_id
            break
    
    if not target_dataset_id:
        return pd.DataFrame(columns=['account_name', 'total_amount'])
    
    # Hämta alla värden för dataset
    values = firebase_db.get_values(dataset_id=target_dataset_id)
    
    # Hämta referensdata
    accounts = firebase_db.get_accounts()
    categories = firebase_db.get_account_categories()
    
    # Hitta rätt kategori-ID
    target_category_id = None
    for cat_id, cat_data in categories.items():
        if cat_data.get('name') == category:
            target_category_id = cat_id
            break
    
    if not target_category_id:
        return pd.DataFrame(columns=['account_name', 'total_amount'])
    
    # Samla data per konto
    account_totals = {}
    for value_data in values.values():
        if value_data.get('value_type') != 'faktiskt':
            continue
            
        account_id = value_data.get('account_id')
        account_data = accounts.get(account_id, {})
        
        if account_data.get('category_id') != target_category_id:
            continue
        
        account_name = account_data.get('name', 'Okänt konto')
        amount = value_data.get('amount', 0)
        
        if account_name not in account_totals:
            account_totals[account_name] = 0
        account_totals[account_name] += amount
    
    # Skapa DataFrame och sortera
    data = [{'account_name': name, 'total_amount': total} 
            for name, total in account_totals.items()]
    
    df = pd.DataFrame(data)
    
    if not df.empty:
        df = df.reindex(df['total_amount'].abs().sort_values(ascending=False).index)
        df = df.head(limit)
    
    return df

def format_currency(amount: float) -> str:
    """Formatera belopp som valuta"""
    return f"{amount:,.0f} SEK".replace(',', ' ')

def get_account_categories() -> List[Dict]:
    """Hämta alla kontokategorier"""
    firebase_db = get_firebase_db()
    categories_dict = firebase_db.get_account_categories()
    
    categories = []
    for category_id, category_data in categories_dict.items():
        category_data['id'] = category_id
        categories.append(category_data)
    
    return categories

def get_company_by_id(company_id: str) -> Optional[Dict]:
    """Hämta specifikt företag"""
    firebase_db = get_firebase_db()
    companies = firebase_db.get_companies()
    
    if company_id in companies:
        company_data = companies[company_id].copy()
        company_data['id'] = company_id
        return company_data
    
    return None

def get_accounts_for_category(category_name: str) -> List[Dict]:
    """Hämta alla konton för en specifik kategori"""
    firebase_db = get_firebase_db()
    
    # Hitta kategori-ID
    categories = firebase_db.get_account_categories()
    target_category_id = None
    for cat_id, cat_data in categories.items():
        if cat_data.get('name') == category_name:
            target_category_id = cat_id
            break
    
    if not target_category_id:
        return []
    
    # Hämta konton för kategorin
    accounts_dict = firebase_db.get_accounts(category_id=target_category_id)
    
    accounts = []
    for account_id, account_data in accounts_dict.items():
        account_data['id'] = account_id
        accounts.append(account_data)
    
    return accounts
