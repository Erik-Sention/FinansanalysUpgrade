"""
Huvudapplikation för finansiell analys i Streamlit
"""
import streamlit as st
import sys
import os
from pathlib import Path

# Konfigurera sidan först
st.set_page_config(
    page_title="Finansiell Analys",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dynamisk import för att hantera olika environments
def safe_import():
    """Säker import som fungerar både lokalt och på Streamlit Cloud"""
    
    # Lägg till alla möjliga paths
    current_dir = Path(__file__).parent
    src_dir = current_dir / "src"
    
    # Lägg till paths
    paths_to_add = [
        str(current_dir),
        str(src_dir),
        str(current_dir / "src" / "pages"),
        str(current_dir / "src" / "utils"),
        str(current_dir / "src" / "models")
    ]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    # Prova flera olika import-strategier
    try:
        # Strategi 1: Absolut import med src prefix
        from src.pages import excel_view, visualization, auth
        from src.utils.auth import require_authentication, show_user_info, get_auth
        return excel_view, visualization, auth, require_authentication, show_user_info, get_auth
    except ImportError as e1:
        try:
            # Strategi 2: Relativ import utan src prefix
            from pages import excel_view, visualization, auth
            from utils.auth import require_authentication, show_user_info, get_auth
            return excel_view, visualization, auth, require_authentication, show_user_info, get_auth
        except ImportError as e2:
            try:
                # Strategi 3: Direkta imports
                import excel_view, visualization, auth
                from auth import require_authentication, show_user_info, get_auth
                return excel_view, visualization, auth, require_authentication, show_user_info, get_auth
            except ImportError as e3:
                # Visa detaljerad felsökning
                st.error("Import fel - alla strategier misslyckades:")
                st.code(f"Strategi 1 fel: {e1}")
                st.code(f"Strategi 2 fel: {e2}")
                st.code(f"Strategi 3 fel: {e3}")
                st.code(f"Nuvarande arbetskatalog: {os.getcwd()}")
                st.code(f"Sys.path: {sys.path[:5]}")
                st.code(f"Filer i current dir: {list(current_dir.iterdir())}")
                st.code(f"Filer i src: {list(src_dir.iterdir()) if src_dir.exists() else 'Src exists not'}")
                st.stop()

# Utför säker import
try:
    excel_view, visualization, auth, require_authentication, show_user_info, get_auth = safe_import()
except:
    st.error("Kritiskt fel vid import")
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