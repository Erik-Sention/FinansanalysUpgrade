"""
Firebase Realtime Database modeller för finansiell analysapp
"""
import os
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
import firebase_admin
from firebase_admin import credentials, db
import pyrebase
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path

# Ladda miljövariabler från .env fil (lokalt) eller Streamlit secrets (cloud)
import streamlit as st

# Försök ladda från .env först (för lokal utveckling)
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
print(f"🔍 Debug - Project ID: {get_env_var('FIREBASE_PROJECT_ID')}")

class FirebaseDB:
    """Firebase Realtime Database hanterare"""
    
    def __init__(self):
        self._initialize_firebase()
        
    def _initialize_firebase(self):
        """Initiera Firebase anslutning"""
        try:
            # Kontrollera om Firebase redan är initialiserad
            firebase_admin.get_app()
        except ValueError:
            # Försök med service account credentials först
            if get_env_var("FIREBASE_PRIVATE_KEY"):
                try:
                    cred_dict = {
                        "type": get_env_var("FIREBASE_TYPE"),
                        "project_id": get_env_var("FIREBASE_PROJECT_ID"),
                        "private_key_id": get_env_var("FIREBASE_PRIVATE_KEY_ID"),
                        "private_key": get_env_var("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
                        "client_email": get_env_var("FIREBASE_CLIENT_EMAIL"),
                        "client_id": get_env_var("FIREBASE_CLIENT_ID"),
                        "auth_uri": get_env_var("FIREBASE_AUTH_URI"),
                        "token_uri": get_env_var("FIREBASE_TOKEN_URI"),
                        "auth_provider_x509_cert_url": get_env_var("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
                        "client_x509_cert_url": get_env_var("FIREBASE_CLIENT_X509_CERT_URL")
                    }
                    
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred, {
                        'databaseURL': get_env_var("FIREBASE_DATABASE_URL")
                    })
                except Exception as e:
                    print(f"Service account auth failed: {e}")
                    # Fallback till Application Default Credentials
                    self._initialize_with_gcloud()
            else:
                # Använd Application Default Credentials
                self._initialize_with_gcloud()
    
    def _initialize_with_gcloud(self):
        """Initiera med gcloud Application Default Credentials"""
        try:
            # Använd default credentials (från gcloud auth)
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {
                'databaseURL': get_env_var("FIREBASE_DATABASE_URL"),
                'projectId': get_env_var("FIREBASE_PROJECT_ID")
            })
            print("✅ Firebase initialiserad med Application Default Credentials")
        except Exception as e:
            print(f"❌ Firebase initialization failed: {e}")
            raise
        
        # Pyrebase konfiguration för enklare operationer  
        self.firebase_config = {
            "apiKey": get_env_var("FIREBASE_API_KEY"),
            "authDomain": get_env_var("FIREBASE_AUTH_DOMAIN"),
            "databaseURL": get_env_var("FIREBASE_DATABASE_URL"),
            "storageBucket": get_env_var("FIREBASE_STORAGE_BUCKET"),
            "messagingSenderId": get_env_var("FIREBASE_MESSAGING_SENDER_ID"),
            "appId": get_env_var("FIREBASE_APP_ID")
        }
        
        self.firebase = pyrebase.initialize_app(self.firebase_config)
        self.db_pyrebase = self.firebase.database()
        
        return db.reference()
    
    def get_authenticated_ref(self, path: str = ""):
        """Hämta autentiserad databas referens med användartoken"""
        try:
            # Försök hämta användartoken från session state
            if 'user_token' in st.session_state:
                token = st.session_state['user_token']
                # Använd pyrebase för autentiserade förfrågningar
                return self.db_pyrebase.child(path)
            else:
                # Fallback till admin SDK för server-operationer
                return db.reference(path)
        except Exception as e:
            print(f"Error getting authenticated reference: {e}")
            return db.reference(path)

    def get_ref(self, path: str = ""):
        """Hämta databas referens"""
        return db.reference(path)

    def create_company(self, name: str, location: Optional[str] = None) -> str:
        """Skapa nytt företag"""
        company_data = {
            "name": name,
            "location": location,
            "created_at": datetime.now().isoformat()
        }
        
        companies_ref = self.get_ref("companies")
        new_company_ref = companies_ref.push(company_data)
        return new_company_ref.key

    def get_companies(self) -> Dict[str, Any]:
        """Hämta alla företag"""
        companies_ref = self.get_ref("companies")
        return companies_ref.get() or {}

    def create_dataset(self, company_id: str, year: int, name: str) -> str:
        """Skapa nytt dataset"""
        dataset_data = {
            "company_id": company_id,
            "year": year,
            "name": name,
            "created_at": datetime.now().isoformat()
        }
        
        datasets_ref = self.get_ref("datasets")
        new_dataset_ref = datasets_ref.push(dataset_data)
        return new_dataset_ref.key

    def get_datasets(self, company_id: Optional[str] = None) -> Dict[str, Any]:
        """Hämta datasets, eventuellt filtrerade på företag"""
        datasets_ref = self.get_ref("datasets")
        datasets = datasets_ref.get() or {}
        
        if company_id:
            return {k: v for k, v in datasets.items() if v.get("company_id") == company_id}
        
        return datasets

    def create_raw_label(self, label: str) -> str:
        """Skapa ny raw label"""
        # Kontrollera om label redan finns
        existing = self.get_raw_label_by_name(label)
        if existing:
            return existing[0]
        
        label_data = {
            "label": label,
            "created_at": datetime.now().isoformat()
        }
        
        labels_ref = self.get_ref("raw_labels")
        new_label_ref = labels_ref.push(label_data)
        return new_label_ref.key

    def get_raw_labels(self) -> Dict[str, Any]:
        """Hämta alla raw labels"""
        labels_ref = self.get_ref("raw_labels")
        return labels_ref.get() or {}

    def get_raw_label_by_name(self, label: str) -> Optional[tuple]:
        """Hitta raw label med namn"""
        labels = self.get_raw_labels()
        for key, value in labels.items():
            if value.get("label") == label:
                return (key, value)
        return None

    def create_account_category(self, name: str, description: Optional[str] = None) -> str:
        """Skapa ny kontokategori"""
        category_data = {
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        
        categories_ref = self.get_ref("account_categories")
        new_category_ref = categories_ref.push(category_data)
        return new_category_ref.key

    def get_account_categories(self) -> Dict[str, Any]:
        """Hämta alla kontokategorier"""
        categories_ref = self.get_ref("account_categories")
        return categories_ref.get() or {}

    def create_account(self, name: str, category_id: str, description: Optional[str] = None) -> str:
        """Skapa nytt konto"""
        account_data = {
            "name": name,
            "category_id": category_id,
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        
        accounts_ref = self.get_ref("accounts")
        new_account_ref = accounts_ref.push(account_data)
        return new_account_ref.key

    def get_accounts(self, category_id: Optional[str] = None) -> Dict[str, Any]:
        """Hämta konton, eventuellt filtrerade på kategori"""
        accounts_ref = self.get_ref("accounts")
        accounts = accounts_ref.get() or {}
        
        if category_id:
            return {k: v for k, v in accounts.items() if v.get("category_id") == category_id}
        
        return accounts

    def create_account_mapping(self, raw_label_id: str, account_id: str, confidence: float = 1.0) -> str:
        """Skapa mappning från raw label till konto"""
        mapping_data = {
            "raw_label_id": raw_label_id,
            "account_id": account_id,
            "confidence": confidence,
            "created_at": datetime.now().isoformat()
        }
        
        mappings_ref = self.get_ref("account_mappings")
        new_mapping_ref = mappings_ref.push(mapping_data)
        return new_mapping_ref.key

    def get_account_mappings(self) -> Dict[str, Any]:
        """Hämta alla konto-mappningar"""
        mappings_ref = self.get_ref("account_mappings")
        return mappings_ref.get() or {}

    def create_value(self, dataset_id: str, account_id: str, month: int, value_type: str, amount: float) -> str:
        """Skapa nytt värde"""
        value_data = {
            "dataset_id": dataset_id,
            "account_id": account_id,
            "month": month,
            "value_type": value_type,  # "faktiskt" eller "budget"
            "amount": amount,
            "created_at": datetime.now().isoformat()
        }
        
        values_ref = self.get_ref("values")
        new_value_ref = values_ref.push(value_data)
        return new_value_ref.key

    def get_values(self, dataset_id: Optional[str] = None, account_id: Optional[str] = None) -> Dict[str, Any]:
        """Hämta värden med valfri filtrering"""
        values_ref = self.get_ref("values")
        values = values_ref.get() or {}
        
        if dataset_id:
            values = {k: v for k, v in values.items() if v.get("dataset_id") == dataset_id}
        
        if account_id:
            values = {k: v for k, v in values.items() if v.get("account_id") == account_id}
        
        return values

    def create_budget(self, company_id: str, year: int, name: str) -> str:
        """Skapa ny budget"""
        budget_data = {
            "company_id": company_id,
            "year": year,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        budgets_ref = self.get_ref("budgets")
        new_budget_ref = budgets_ref.push(budget_data)
        return new_budget_ref.key

    def get_budgets(self, company_id: Optional[str] = None) -> Dict[str, Any]:
        """Hämta budgetar"""
        budgets_ref = self.get_ref("budgets")
        budgets = budgets_ref.get() or {}
        
        if company_id:
            return {k: v for k, v in budgets.items() if v.get("company_id") == company_id}
        
        return budgets

    def update_budget_value(self, budget_id: str, account_id: str, month: int, amount: float) -> str:
        """Uppdatera eller skapa budgetvärde"""
        value_data = {
            "budget_id": budget_id,
            "account_id": account_id,
            "month": month,
            "amount": amount,
            "updated_at": datetime.now().isoformat()
        }
        
        # Hitta befintligt värde eller skapa nytt
        budget_values_ref = self.get_ref("budget_values")
        existing_values = budget_values_ref.get() or {}
        
        for key, value in existing_values.items():
            if (value.get("budget_id") == budget_id and 
                value.get("account_id") == account_id and 
                value.get("month") == month):
                # Uppdatera befintligt värde
                budget_values_ref.child(key).update(value_data)
                return key
        
        # Skapa nytt värde
        new_value_ref = budget_values_ref.push(value_data)
        return new_value_ref.key

    def get_budget_values(self, budget_id: Optional[str] = None) -> Dict[str, Any]:
        """Hämta budgetvärden"""
        budget_values_ref = self.get_ref("budget_values")
        values = budget_values_ref.get() or {}
        
        if budget_id:
            return {k: v for k, v in values.items() if v.get("budget_id") == budget_id}
        
        return values

    def create_seasonality_index(self, company_id: str, account_id: str) -> str:
        """Skapa säsongsindex"""
        index_data = {
            "company_id": company_id,
            "account_id": account_id,
            "created_at": datetime.now().isoformat()
        }
        
        indices_ref = self.get_ref("seasonality_indices")
        new_index_ref = indices_ref.push(index_data)
        return new_index_ref.key

    def update_seasonality_value(self, seasonality_index_id: str, year: int, month: int, index_value: float) -> str:
        """Uppdatera eller skapa säsongsvärde"""
        value_data = {
            "seasonality_index_id": seasonality_index_id,
            "year": year,
            "month": month,
            "index_value": index_value,
            "updated_at": datetime.now().isoformat()
        }
        
        # Hitta befintligt värde eller skapa nytt
        seasonality_values_ref = self.get_ref("seasonality_values")
        existing_values = seasonality_values_ref.get() or {}
        
        for key, value in existing_values.items():
            if (value.get("seasonality_index_id") == seasonality_index_id and 
                value.get("year") == year and 
                value.get("month") == month):
                # Uppdatera befintligt värde
                seasonality_values_ref.child(key).update(value_data)
                return key
        
        # Skapa nytt värde
        new_value_ref = seasonality_values_ref.push(value_data)
        return new_value_ref.key

    def init_database(self):
        """Initiera databasen med grundläggande data"""
        # Skapa grundläggande kategorier om de inte finns
        categories = self.get_account_categories()
        
        revenue_exists = any(cat.get("name") == "Intäkter" for cat in categories.values())
        if not revenue_exists:
            self.create_account_category("Intäkter", "Alla intäktsposter")
        
        expense_exists = any(cat.get("name") == "Kostnader" for cat in categories.values())
        if not expense_exists:
            self.create_account_category("Kostnader", "Alla kostnadsposter")

# Global instans
def get_firebase_db():
    """Hämta Firebase databas instans"""
    if 'firebase_db' not in st.session_state:
        st.session_state.firebase_db = FirebaseDB()
    return st.session_state.firebase_db
