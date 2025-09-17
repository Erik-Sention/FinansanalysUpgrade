"""
Minimal Streamlit app för att testa autentisering
"""
import streamlit as st
import os
from pathlib import Path

# Konfigurera sidan
st.set_page_config(
    page_title="Finansiell Analys",
    page_icon="📊",
    layout="wide"
)

# Fix för pkg_resources
try:
    import pkg_resources
except ImportError:
    import importlib.metadata as pkg_resources
    import sys
    if not hasattr(pkg_resources, 'get_distribution'):
        pkg_resources.get_distribution = lambda name: type('Distribution', (), {'version': '1.0.0'})()
    sys.modules['pkg_resources'] = pkg_resources

# Enkel autentisering
def simple_auth():
    st.title("🔐 Finansiell Analys - Inloggning")
    
    # Kontrollera om användaren är inloggad
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        st.markdown("### Logga in för att komma åt applikationen")
        
        with st.form("login_form"):
            email = st.text_input("📧 E-postadress", placeholder="din.email@example.se")
            password = st.text_input("🔒 Lösenord", type="password")
            submit = st.form_submit_button("🔑 Logga in", type="primary")
            
            if submit:
                # Enkel validation - du kan ändra detta
                if email == "erik@sention.health" and len(password) > 0:
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.success("✅ Inloggning lyckades!")
                    st.rerun()
                else:
                    st.error("❌ Felaktiga inloggningsuppgifter")
        
        st.info("📧 För att få ett konto, kontakta erik@sention.health")
        
    else:
        # Användaren är inloggad
        st.success(f"👤 Inloggad som: {st.session_state.get('user_email', 'Användare')}")
        
        if st.button("🚪 Logga ut"):
            st.session_state.logged_in = False
            st.session_state.user_email = ""
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 🎉 Du är nu inloggad!")
        st.markdown("Applikationen fungerar och autentiseringen är aktiverad.")
        
        # Här kan vi sedan lägga till de riktiga sidorna
        st.markdown("""
        **Kommande funktioner:**
        - 💾 Finansdatabas
        - 📈 Datavisualisering  
        - 📊 Dashboards
        
        Firebase-integration kommer att implementeras steg för steg.
        """)

# Kör appen
if __name__ == "__main__":
    simple_auth()
