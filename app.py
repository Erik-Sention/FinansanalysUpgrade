"""
Huvudapplikation för finansiell analys i Streamlit
"""
import streamlit as st
import sys
import os
from pathlib import Path

# Konfigurera sidan
st.set_page_config(
    page_title="Finansiell Analys",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
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

# Importera moduler från root-nivån
try:
    import pages_auth as auth
    import pages_excel_view as excel_view  
    import pages_visualization as visualization
    from utils_auth import require_authentication, show_user_info, get_auth
    
except ImportError as e:
    st.error(f"Import fel: {e}")
    st.error("Kontrollera att alla nödvändiga filer finns på root-nivån")
    st.stop()

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