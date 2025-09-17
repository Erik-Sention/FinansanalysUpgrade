"""
SQLModel databasmodeller för finansiell analysapp
"""
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, create_engine, Session
import sqlite3
from pathlib import Path
import streamlit as st

class Company(SQLModel, table=True):
    """Företagstabell"""
    __tablename__ = "companies"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    location: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    datasets: List["Dataset"] = Relationship(back_populates="company")

class Dataset(SQLModel, table=True):
    """Dataset per företag och år"""
    __tablename__ = "datasets"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    year: int
    name: str  # T.ex. "KLAB 2022"
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    company: Company = Relationship(back_populates="datasets")
    values: List["Value"] = Relationship(back_populates="dataset")

class RawLabel(SQLModel, table=True):
    """Originaletiketter från Excel"""
    __tablename__ = "raw_labels"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    label: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.now)

class AccountCategory(SQLModel, table=True):
    """Huvudkategorier (Intäkter, Kostnader)"""
    __tablename__ = "account_categories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)  # "Intäkter", "Kostnader"
    description: Optional[str] = None
    
    # Relationships
    accounts: List["Account"] = Relationship(back_populates="category")

class Account(SQLModel, table=True):
    """Konton (Memberships, Löner, Hyra, etc.)"""
    __tablename__ = "accounts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    category_id: int = Field(foreign_key="account_categories.id")
    description: Optional[str] = None
    
    # Relationships
    category: AccountCategory = Relationship(back_populates="accounts")
    mappings: List["AccountMapping"] = Relationship(back_populates="account")
    values: List["Value"] = Relationship(back_populates="account")

class AccountMapping(SQLModel, table=True):
    """Mappning från raw_label till account"""
    __tablename__ = "account_mappings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    raw_label_id: int = Field(foreign_key="raw_labels.id")
    account_id: int = Field(foreign_key="accounts.id")
    confidence: float = Field(default=1.0)  # 0.0-1.0 för automatisk mappning
    
    # Relationships
    account: Account = Relationship(back_populates="mappings")

class Value(SQLModel, table=True):
    """Månadsvärden (faktiskt/budget)"""
    __tablename__ = "values"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    dataset_id: int = Field(foreign_key="datasets.id")
    account_id: int = Field(foreign_key="accounts.id")
    month: int = Field(ge=1, le=12)  # 1-12
    value_type: str  # "faktiskt", "budget"
    amount: float
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    dataset: Dataset = Relationship(back_populates="values")
    account: Account = Relationship(back_populates="values")

class Budget(SQLModel, table=True):
    """Manuellt redigerad budget"""
    __tablename__ = "budgets"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    year: int
    name: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    budget_values: List["BudgetValue"] = Relationship(back_populates="budget")

class BudgetValue(SQLModel, table=True):
    """Budgetvärden per månad och konto"""
    __tablename__ = "budget_values"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    budget_id: int = Field(foreign_key="budgets.id")
    account_id: int = Field(foreign_key="accounts.id")
    month: int = Field(ge=1, le=12)
    amount: float
    
    # Relationships
    budget: Budget = Relationship(back_populates="budget_values")

class SeasonalityIndex(SQLModel, table=True):
    """Säsongsindex för åren 2022-2024"""
    __tablename__ = "seasonality_indices"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    account_id: int = Field(foreign_key="accounts.id")
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    seasonality_values: List["SeasonalityValue"] = Relationship(back_populates="seasonality_index")

class SeasonalityValue(SQLModel, table=True):
    """Säsongsvärden (index 0-1) per månad och år"""
    __tablename__ = "seasonality_values"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    seasonality_index_id: int = Field(foreign_key="seasonality_indices.id")
    year: int = Field(ge=2022, le=2024)
    month: int = Field(ge=1, le=12)
    index_value: float = Field(ge=0.0, le=2.0)  # 0-2 för flexibilitet
    
    # Relationships
    seasonality_index: SeasonalityIndex = Relationship(back_populates="seasonality_values")

# Databasanslutning
DATABASE_PATH = Path("data/app.db")

@st.cache_resource
def get_engine():
    """Hämta SQLite engine med caching för att undvika konflikter"""
    DATABASE_PATH.parent.mkdir(exist_ok=True)
    return create_engine(f"sqlite:///{DATABASE_PATH}")

def create_tables():
    """Skapa alla tabeller"""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    return engine

def get_session():
    """Hämta databassession"""
    engine = get_engine()
    return Session(engine)

def init_database():
    """Initiera databasen med grundläggande data"""
    engine = create_tables()
    
    with Session(engine) as session:
        # Skapa grundläggande kategorier om de inte finns
        revenue_cat = session.query(AccountCategory).filter(AccountCategory.name == "Intäkter").first()
        if not revenue_cat:
            revenue_cat = AccountCategory(name="Intäkter", description="Alla intäktsposter")
            session.add(revenue_cat)
        
        expense_cat = session.query(AccountCategory).filter(AccountCategory.name == "Kostnader").first()
        if not expense_cat:
            expense_cat = AccountCategory(name="Kostnader", description="Alla kostnadsposter")
            session.add(expense_cat)
        
        session.commit()
        
    return engine
