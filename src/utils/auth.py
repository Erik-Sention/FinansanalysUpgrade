"""
Firebase autentiseringsmodul för Streamlit
"""
import streamlit as st
import pyrebase
import json
from typing import Optional, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv

# Ladda miljövariabler från .env fil (lokalt) eller Streamlit secrets (cloud)
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

class FirebaseAuth:
    """Firebase autentisering för Streamlit"""
    
    def __init__(self):
        self.firebase_config = {
            "apiKey": get_env_var("FIREBASE_API_KEY"),
            "authDomain": get_env_var("FIREBASE_AUTH_DOMAIN"),
            "databaseURL": get_env_var("FIREBASE_DATABASE_URL"),
            "storageBucket": get_env_var("FIREBASE_STORAGE_BUCKET"),
            "messagingSenderId": get_env_var("FIREBASE_MESSAGING_SENDER_ID"),
            "appId": get_env_var("FIREBASE_APP_ID")
        }
        
        self.firebase = pyrebase.initialize_app(self.firebase_config)
        self.auth = self.firebase.auth()
        self.db = self.firebase.database()
    
    # Registrering borttagen - kontakta erik@sention.health för nya konton
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """
        Logga in användare
        """
        try:
            user = self.auth.sign_in_with_email_and_password(email, password)
            
            # Kontrollera om email är verifierad
            account_info = self.auth.get_account_info(user['idToken'])
            is_verified = account_info['users'][0]['emailVerified']
            
            if not is_verified:
                # Visa varning men tillåt inloggning ändå
                return {
                    'success': True,
                    'user': user,
                    'message': 'Inloggning lyckades!',
                    'warning': 'Din e-postadress är inte verifierad. Du kan använda applikationen, men vi rekommenderar att du verifierar din e-post för extra säkerhet.'
                }
            
            return {
                'success': True,
                'user': user,
                'message': 'Inloggning lyckades!'
            }
        except Exception as e:
            error_msg = self._parse_error(str(e))
            return {
                'success': False,
                'error': error_msg
            }
    
    def sign_out(self):
        """
        Logga ut användare
        """
        if 'user' in st.session_state:
            del st.session_state['user']
        if 'user_token' in st.session_state:
            del st.session_state['user_token']
        st.rerun()
    
    def is_authenticated(self) -> bool:
        """
        Kontrollera om användare är inloggad
        """
        return 'user' in st.session_state and 'user_token' in st.session_state
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        Hämta nuvarande användare
        """
        if self.is_authenticated():
            return st.session_state.get('user')
        return None
    
    def get_user_token(self) -> Optional[str]:
        """
        Hämta användarens ID token
        """
        if self.is_authenticated():
            return st.session_state.get('user_token')
        return None
    
    def refresh_token(self) -> bool:
        """
        Uppdatera användarens token
        """
        try:
            if 'user' in st.session_state:
                user = st.session_state['user']
                refreshed_user = self.auth.refresh(user['refreshToken'])
                st.session_state['user'] = refreshed_user
                st.session_state['user_token'] = refreshed_user['idToken']
                return True
        except Exception:
            # Om token refresh misslyckas, logga ut användaren
            self.sign_out()
        return False
    
    # Lösenordsåterställning borttagen - kontakta erik@sention.health för hjälp
    
    def _parse_error(self, error_str: str) -> str:
        """
        Översätt Firebase fel till svenska
        """
        error_mappings = {
            "EMAIL_EXISTS": "E-postadressen används redan av ett annat konto.",
            "OPERATION_NOT_ALLOWED": "E-post/lösenord-inloggning är inte aktiverat.",
            "TOO_MANY_ATTEMPTS_TRY_LATER": "För många misslyckade försök. Försök igen senare.",
            "EMAIL_NOT_FOUND": "Det finns inget användarkonto med denna e-postadress.",
            "INVALID_PASSWORD": "Felaktigt lösenord.",
            "USER_DISABLED": "Användarkontot har inaktiverats.",
            "WEAK_PASSWORD": "Lösenordet är för svagt. Välj ett starkare lösenord.",
            "INVALID_EMAIL": "E-postadressen är inte giltig.",
            "MISSING_PASSWORD": "Lösenord krävs."
        }
        
        # Försök hitta specifikt fel
        for error_code, swedish_message in error_mappings.items():
            if error_code in error_str:
                return swedish_message
        
        # Fallback för okända fel
        if "email" in error_str.lower():
            return "Problem med e-postadressen. Kontrollera att den är korrekt."
        elif "password" in error_str.lower():
            return "Problem med lösenordet. Kontrollera att det är korrekt."
        else:
            return "Ett oväntat fel uppstod. Försök igen senare."

# Global instans
def get_auth():
    """Hämta autentiseringsinstans"""
    if 'firebase_auth' not in st.session_state:
        st.session_state.firebase_auth = FirebaseAuth()
    return st.session_state.firebase_auth

def require_authentication():
    """
    Decorator/middleware för att kräva autentisering
    """
    auth = get_auth()
    if not auth.is_authenticated():
        st.error("🔒 Du måste logga in för att komma åt denna sida.")
        st.info("👈 Använd sidomenyn för att logga in.")
        st.stop()
    
    # Försök uppdatera token om det behövs
    try:
        auth.refresh_token()
    except Exception:
        st.error("🔒 Din session har gått ut. Logga in igen.")
        auth.sign_out()
        st.stop()

def show_user_info():
    """
    Visa användarinformation i sidebar
    """
    auth = get_auth()
    if auth.is_authenticated():
        user = auth.get_current_user()
        
        # Försök hämta e-post från användardatan
        email = None
        
        # Hämta e-post från användardata
        
        if user:
            # Prova olika fält där e-post kan finnas
            email = (user.get('email') or 
                    user.get('localId'))
        
        if not email:
            # Försök hämta från token account info
            try:
                token = auth.get_user_token()
                if token:
                    account_info = auth.auth.get_account_info(token)
                    if account_info and 'users' in account_info and len(account_info['users']) > 0:
                        email = account_info['users'][0].get('email')
            except Exception as e:
                # Kunde inte hämta account info
                pass
        
        # Fallback - visa något användbart
        display_email = email or "Inloggad användare"
        
        with st.sidebar:
            st.success(f"👤 Inloggad som: {display_email}")
            if st.button("🚪 Logga ut", key="logout_btn"):
                auth.sign_out()
