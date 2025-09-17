"""
Autentiseringssida för inloggning och registrering
"""
import streamlit as st
import sys
from pathlib import Path

# Path setup för både lokal och Streamlit Cloud deployment
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

from utils.auth import get_auth

def show():
    """Visa autentiseringssida"""
    
    st.title("🔐 Inloggning")
    st.markdown("---")
    
    auth = get_auth()
    
    # Kontrollera om användaren redan är inloggad
    if auth.is_authenticated():
        st.success("✅ Du är redan inloggad!")
        user = auth.get_current_user()
        st.info(f"👤 Inloggad som: {user.get('email', 'Okänd användare')}")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("📊 Gå till Dashboard", type="primary"):
                st.switch_page("app.py")
        with col2:
            if st.button("🚪 Logga ut"):
                auth.sign_out()
        return
    
    # Endast inloggning tillgänglig
    st.subheader("Logga in på ditt konto")
    st.info("📧 För att få ett konto eller återställa lösenord, kontakta erik@sention.health")
    
    show_login_form(auth)

def show_login_form(auth):
    """Visa inloggningsformulär"""
    
    with st.form("login_form"):
        email = st.text_input(
            "📧 E-postadress",
            placeholder="din.email@exempel.se",
            help="Ange din registrerade e-postadress"
        )
        
        password = st.text_input(
            "🔒 Lösenord",
            type="password",
            placeholder="Ditt lösenord",
            help="Ange ditt lösenord"
        )
        
        submitted = st.form_submit_button("🔑 Logga in", type="primary")
        
        if submitted:
            if not email or not password:
                st.error("⚠️ Fyll i både e-postadress och lösenord.")
                return
            
            with st.spinner("Loggar in..."):
                result = auth.sign_in(email, password)
            
            if result['success']:
                st.success(result['message'])
                
                # Visa varning om e-post inte är verifierad
                if 'warning' in result:
                    st.warning(f"⚠️ {result['warning']}")
                
                # Spara användardata i session state
                st.session_state['user'] = result['user']
                st.session_state['user_token'] = result['user']['idToken']
                
                # Vänta en kort stund och ladda om
                st.balloons()
                st.rerun()
            else:
                st.error(f"❌ {result['error']}")

# Registrering och lösenordsåterställning borttagna
# Kontakta erik@sention.health för att få konto eller återställa lösenord

if __name__ == "__main__":
    show()
