"""
Huvudapplikation för finansiell analys i Streamlit
"""
import streamlit as st
import sys
import os
from pathlib import Path

# Path setup för både lokal och Streamlit Cloud deployment
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

# Importera sidor och autentisering med fallback för olika environments
try:
    # Försök först med src prefix (Streamlit Cloud)
    from src.pages import excel_view, visualization, auth
    from src.utils.auth import require_authentication, show_user_info, get_auth
except ImportError:
    try:
        # Fallback utan src prefix (lokal utveckling)
        from pages import excel_view, visualization, auth
        from utils.auth import require_authentication, show_user_info, get_auth
    except ImportError:
        st.error("Import fel - kontrollera filstruktur")
        st.stop()

# Konfigurera sidan
st.set_page_config(
    page_title="Finansiell Analys",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Kontrollera autentisering
firebase_auth = get_auth()

# Sidebar navigation
st.sidebar.title("📊 Finansiell Analys")
st.sidebar.markdown("---")

# Visa användarinfo eller inloggningslänk
if firebase_auth.is_authenticated():
    show_user_info()
    st.sidebar.markdown("---")
    
    # Navigation för inloggade användare
    page = st.sidebar.selectbox(
        "Välj sida",
        ["💾 Finansdatabas", "📈 Visualisering"],
        index=0
    )
    
    st.sidebar.markdown("---")
    
    # Kräv autentisering för alla sidor
    require_authentication()
    
    # Visa vald sida
    if page == "💾 Finansdatabas":
        excel_view.show()
    elif page == "📈 Visualisering":
        visualization.show()
        
else:
    # Visa inloggningsalternativ för ej inloggade användare
    st.sidebar.info("🔒 Du måste logga in för att komma åt applikationen.")
    
    if st.sidebar.button("🔑 Logga in", type="primary"):
        auth.show()
    else:
        # Visa inloggningssidan som standard
        auth.show()

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <small>
    **Finansiell Analys v2.0**<br>
    Data från Firebase Realtime Database<br>
    Byggt med Streamlit
    </small>
    """, 
    unsafe_allow_html=True
)
