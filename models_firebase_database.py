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
        
    def _get_token(self):
        """Hämta idToken för autentiserad användare (krävs av reglerna)."""
        try:
            # Preferera explicit sparad token
            token = st.session_state.get('user_token')
            if token:
                return token
            # Fallback: token i user-objektet
            user = st.session_state.get('user')
            if isinstance(user, dict):
                return user.get('idToken')
        except Exception:
            pass
        return None
        
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
            data = companies_ref.get(self._get_token())
            return data.val() if data.val() else {}
        except Exception as e:
            print(f"Error getting companies: {e}")
            return {}

    def get_datasets(self, company_id: Optional[str] = None) -> Dict[str, Any]:
        """Hämta datasets, eventuellt filtrerade på företag"""
        try:
            datasets_ref = self.get_ref("datasets")
            data = datasets_ref.get(self._get_token())
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
            data = categories_ref.get(self._get_token())
            return data.val() if data.val() else {}
        except Exception as e:
            print(f"Error getting account categories: {e}")
            return {}

    def get_accounts(self, category_id: Optional[str] = None) -> Dict[str, Any]:
        """Hämta konton, eventuellt filtrerade på kategori"""
        try:
            accounts_ref = self.get_ref("accounts")
            data = accounts_ref.get(self._get_token())
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
            data = values_ref.get(self._get_token())
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
            data = budgets_ref.get(self._get_token())
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
            data = budget_values_ref.get(self._get_token())
            values = data.val() if data.val() else {}
            
            if budget_id:
                return {k: v for k, v in values.items() if v.get("budget_id") == budget_id}
            
            return values
        except Exception as e:
            print(f"Error getting budget values: {e}")
            return {}

    def create_budget(self, company_id: str, year: int, name: str) -> str:
        """Skapa ny budget"""
        try:
            budget_data = {
                "company_id": company_id,
                "year": year,
                "name": name,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            budgets_ref = self.get_ref("budgets")
            new_budget_ref = budgets_ref.push(budget_data, self._get_token())
            return new_budget_ref['name']  # Pyrebase returnerar {'name': 'key'}
        except Exception as e:
            print(f"Error creating budget: {e}")
            raise

    def update_budget_value(self, budget_id: str, account_id: str, month: int, amount: float) -> str:
        """Uppdatera eller skapa budgetvärde"""
        try:
            value_data = {
                "budget_id": budget_id,
                "account_id": account_id,
                "month": month,
                "amount": amount,
                "updated_at": datetime.now().isoformat()
            }
            
            print(f"🔥 SPARAR BUDGET VALUE: {value_data}")
            
            # Hitta befintligt värde eller skapa nytt
            budget_values_ref = self.get_ref("budget_values")
            existing_data = budget_values_ref.get(self._get_token())
            
            # Säker hantering av Pyrebase response
            existing_values = {}
            if existing_data and existing_data.val():
                existing_values = existing_data.val()
                # Säkerställ att det är en dict
                if not isinstance(existing_values, dict):
                    existing_values = {}
            
            print(f"🔥 EXISTING VALUES COUNT: {len(existing_values) if existing_values else 0}")
            
            # Sök efter befintligt värde
            found_existing = False
            if existing_values:
                for key, value in existing_values.items():
                    if (value and isinstance(value, dict) and
                        value.get("budget_id") == budget_id and 
                        value.get("account_id") == account_id and 
                        value.get("month") == month):
                        # Uppdatera befintligt värde
                        budget_values_ref.child(key).update(value_data, self._get_token())
                        print(f"🔥 UPPDATERADE BEFINTLIGT: key={key}")
                        found_existing = True
                        return key
            
            if not found_existing:
                # Skapa nytt värde
                new_value_ref = budget_values_ref.push(value_data, self._get_token())
                new_key = new_value_ref['name']
                print(f"🔥 SKAPADE NYTT: key={new_key}")
                return new_key
                
        except Exception as e:
            print(f"Error updating budget value: {e}")
            print(f"Debug - existing_data type: {type(existing_data) if 'existing_data' in locals() else 'Not set'}")
            print(f"Debug - existing_data: {existing_data if 'existing_data' in locals() else 'Not set'}")
            raise

# Global instans
def get_firebase_db():
    """Hämta Firebase databas instans"""
    if 'firebase_db' not in st.session_state:
        st.session_state.firebase_db = FirebaseDB()
    return st.session_state.firebase_db
