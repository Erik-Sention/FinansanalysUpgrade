"""
Enkel Streamlit app som ENDAST använder Pyrebase (ingen firebase_admin)
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

# Importera moduler från root-nivån (endast de som INTE använder firebase_admin)
try:
    import pages_auth as auth
    import pages_visualization2 as visualization
    import pages_seasonal_analysis as seasonal_analysis
    from utils_auth import require_authentication, show_user_info, get_auth
    
    # Importera ENDAST från fungerende sidor
    from test_excel_import import show_excel_import_test
    from simple_budget_page import show_simple_budget_page
    
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
    
    # Navigation för inloggade användare (endast fungerende sidor)
    page = st.sidebar.selectbox(
        "Välj sida",
        ["📊 Test Excel-import", "💰 Budget-redigering", "📈 Visualisering v2", "📅 Säsongsanalys"],
        index=0  # Börja med Excel-import
    )
    
    st.sidebar.markdown("---")
    
    # Kräv autentisering för alla sidor
    require_authentication()
    
    # Visa vald sida
    if page == "📊 Test Excel-import":
        show_excel_import_test()
    elif page == "💰 Budget-redigering":
        show_simple_budget_page()
    elif page == "📈 Visualisering v2":
        visualization.show()
    elif page == "📅 Säsongsanalys":
        seasonal_analysis.show()
        
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
    **Finansiell Analys v2.0 (Pyrebase)**<br>
    Data från Firebase Realtime Database<br>
    Byggt med Streamlit + Pyrebase
    </small>
    """, 
    unsafe_allow_html=True
)
