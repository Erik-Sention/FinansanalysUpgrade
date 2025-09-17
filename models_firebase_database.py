"""
Firebase Realtime Database modeller för finansiell analysapp - Enkel version med bara Pyrebase
"""
import os
from datetime import datetime
from typing import Optional, Dict, List, Any
import pyrebase
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path

# Ladda miljövariabler från .env fil
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

def get_env_var(key: str) -> str:
    """Hämta miljövariabel från .env eller Streamlit secrets"""
    # Först försök vanliga miljövariabler
    value = os.getenv(key)
    if value:
        return value
    
    # Sedan försök Streamlit secrets (för cloud deployment)
    try:
        return st.secrets[key]
    except (KeyError, AttributeError):
        return None

# Debug: Kontrollera att miljövariabler laddas
print(f"🔍 Debug - Database URL: {get_env_var('FIREBASE_DATABASE_URL')}")
print(f"🔍 Debug - API Key: {get_env_var('FIREBASE_API_KEY')[:10] if get_env_var('FIREBASE_API_KEY') else 'None'}...")

class FirebaseDB:
    """Firebase Realtime Database hanterare - Använder endast Pyrebase (ingen Service Account behövs!)"""
    
    def __init__(self):
        self._initialize_firebase()
        
    def _initialize_firebase(self):
        """Initiera Firebase anslutning med Pyrebase"""
        # Pyrebase konfiguration - behöver bara dessa 6 värden!
        self.firebase_config = {
            "apiKey": get_env_var("FIREBASE_API_KEY"),
            "authDomain": get_env_var("FIREBASE_AUTH_DOMAIN"),
            "databaseURL": get_env_var("FIREBASE_DATABASE_URL"),
            "storageBucket": get_env_var("FIREBASE_STORAGE_BUCKET"),
            "messagingSenderId": get_env_var("FIREBASE_MESSAGING_SENDER_ID"),
            "appId": get_env_var("FIREBASE_APP_ID")
        }
        
        # Kontrollera att alla värden finns
        missing = [k for k, v in self.firebase_config.items() if not v]
        if missing:
            raise Exception(f"Firebase config saknas: {missing}")
        
        try:
            self.firebase = pyrebase.initialize_app(self.firebase_config)
            self.db = self.firebase.database()
            print("✅ Firebase initialiserad med Pyrebase (ingen Service Account behövd!)")
        except Exception as e:
            print(f"❌ Firebase initialization failed: {e}")
            raise

    def get_ref(self, path: str = ""):
        """Hämta databas referens"""
        if path:
            return self.db.child(path)
        return self.db

    def get_companies(self) -> Dict[str, Any]:
        """Hämta alla företag"""
        try:
            companies_ref = self.get_ref("companies")
            data = companies_ref.get()
            return data.val() if data.val() else {}
        except Exception as e:
            print(f"Error getting companies: {e}")
            return {}

    def get_datasets(self, company_id: Optional[str] = None) -> Dict[str, Any]:
        """Hämta datasets, eventuellt filtrerade på företag"""
        try:
            datasets_ref = self.get_ref("datasets")
            data = datasets_ref.get()
            datasets = data.val() if data.val() else {}
            
            if company_id:
                return {k: v for k, v in datasets.items() if v.get("company_id") == company_id}
            
            return datasets
        except Exception as e:
            print(f"Error getting datasets: {e}")
            return {}

    def get_account_categories(self) -> Dict[str, Any]:
        """Hämta alla kontokategorier"""
        try:
            categories_ref = self.get_ref("account_categories")
            data = categories_ref.get()
            return data.val() if data.val() else {}
        except Exception as e:
            print(f"Error getting account categories: {e}")
            return {}

    def get_accounts(self, category_id: Optional[str] = None) -> Dict[str, Any]:
        """Hämta konton, eventuellt filtrerade på kategori"""
        try:
            accounts_ref = self.get_ref("accounts")
            data = accounts_ref.get()
            accounts = data.val() if data.val() else {}
            
            if category_id:
                return {k: v for k, v in accounts.items() if v.get("category_id") == category_id}
            
            return accounts
        except Exception as e:
            print(f"Error getting accounts: {e}")
            return {}

    def get_values(self, dataset_id: Optional[str] = None, account_id: Optional[str] = None) -> Dict[str, Any]:
        """Hämta värden med valfri filtrering"""
        try:
            values_ref = self.get_ref("values")
            data = values_ref.get()
            values = data.val() if data.val() else {}
            
            if dataset_id:
                values = {k: v for k, v in values.items() if v.get("dataset_id") == dataset_id}
            
            if account_id:
                values = {k: v for k, v in values.items() if v.get("account_id") == account_id}
            
            return values
        except Exception as e:
            print(f"Error getting values: {e}")
            return {}

    def get_budgets(self, company_id: Optional[str] = None) -> Dict[str, Any]:
        """Hämta budgetar"""
        try:
            budgets_ref = self.get_ref("budgets")
            data = budgets_ref.get()
            budgets = data.val() if data.val() else {}
            
            if company_id:
                return {k: v for k, v in budgets.items() if v.get("company_id") == company_id}
            
            return budgets
        except Exception as e:
            print(f"Error getting budgets: {e}")
            return {}

    def get_budget_values(self, budget_id: Optional[str] = None) -> Dict[str, Any]:
        """Hämta budgetvärden"""
        try:
            budget_values_ref = self.get_ref("budget_values")
            data = budget_values_ref.get()
            values = data.val() if data.val() else {}
            
            if budget_id:
                return {k: v for k, v in values.items() if v.get("budget_id") == budget_id}
            
            return values
        except Exception as e:
            print(f"Error getting budget values: {e}")
            return {}

# Global instans
def get_firebase_db():
    """Hämta Firebase databas instans"""
    if 'firebase_db' not in st.session_state:
        st.session_state.firebase_db = FirebaseDB()
    return st.session_state.firebase_db
