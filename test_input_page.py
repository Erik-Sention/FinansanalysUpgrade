"""
Test-sida för automatisk sparning till Firebase
"""
import streamlit as st
from models_firebase_database import get_firebase_db
from datetime import datetime

def save_test_value(value: float) -> bool:
    """
    Spara testvärde till Firebase
    
    Args:
        value: Värde att spara
        
    Returns:
        bool: True om sparning lyckades
    """
    try:
        firebase_db = get_firebase_db()
        
        # Spara till en enkel test-nod i Firebase
        test_data = {
            "value": value,
            "updated_at": datetime.now().isoformat(),
            "user": st.session_state.get('user', {}).get('email', 'unknown')
        }
        
        # Använd en fast nyckel för testet
        test_ref = firebase_db.get_ref("test_input")
        test_ref.set(test_data, firebase_db._get_token())
        
        return True
        
    except Exception as e:
        st.error(f"❌ Fel vid sparande: {e}")
        return False

def load_test_value() -> float:
    """
    Ladda testvärde från Firebase
    
    Returns:
        float: Sparat värde eller 0 som default
    """
    try:
        firebase_db = get_firebase_db()
        test_ref = firebase_db.get_ref("test_input")
        data = test_ref.get(firebase_db._get_token())
        
        if data and data.val():
            return float(data.val().get('value', 0))
        return 0.0
        
    except Exception as e:
        st.error(f"❌ Fel vid laddning: {e}")
        return 0.0

def show_test_input():
    """Visa test-input sidan"""
    st.title("🧪 Test: Automatisk sparning till Firebase")
    st.markdown("Testa den optimerade sparfunktionen med en enkel inputruta")
    
    # Info om testet
    with st.expander("ℹ️ Om detta test", expanded=False):
        st.markdown("""
        **Vad som testas:**
        - 📝 Input-ruta som börjar på 0
        - 💾 Automatisk sparning till Firebase när värdet ändras
        - ⚡ Omedelbar feedback när sparning sker
        - 🔄 Ladda befintligt värde från databasen
        
        **Firebase-struktur:**
        ```
        {
          "test_input": {
            "value": 123.45,
            "updated_at": "2025-09-18T11:20:00",
            "user": "erik@sention.health"
          }
        }
        ```
        """)
    
    st.markdown("---")
    
    # Ladda befintligt värde
    if 'test_value' not in st.session_state:
        st.session_state.test_value = load_test_value()
    
    st.markdown("### 📊 Test-input för Firebase-sparning")
    
    # Visa nuvarande värde från databasen
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Input-ruta
        new_value = st.number_input(
            "Ändra värdet (sparas automatiskt):",
            value=st.session_state.test_value,
            step=1.0,
            format="%.2f",
            key="test_input_field"
        )
    
    with col2:
        # Status
        if new_value != st.session_state.test_value:
            # Värdet har ändrats - spara automatiskt
            if save_test_value(new_value):
                st.success("✅ Sparat!")
                st.session_state.test_value = new_value
            else:
                st.error("❌ Fel vid sparning")
        else:
            st.info("💾 Klart")
    
    # Visa detaljer om senaste sparning
    st.markdown("---")
    st.markdown("### 🔍 Databas-status")
    
    try:
        firebase_db = get_firebase_db()
        test_ref = firebase_db.get_ref("test_input")
        data = test_ref.get(firebase_db._get_token())
        
        if data and data.val():
            test_data = data.val()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("💰 Sparat värde", f"{test_data.get('value', 0):,.2f}")
            
            with col2:
                updated_at = test_data.get('updated_at', 'Okänt')
                if updated_at != 'Okänt':
                    # Visa bara tid (inte datum)
                    time_only = updated_at.split('T')[1][:8] if 'T' in updated_at else updated_at
                    st.metric("🕐 Senast uppdaterad", time_only)
                else:
                    st.metric("🕐 Senast uppdaterad", "Okänt")
            
            with col3:
                user = test_data.get('user', 'Okänd')
                st.metric("👤 Användare", user)
            
            # Visa rådata
            with st.expander("🔍 Rådata från Firebase", expanded=False):
                st.json(test_data)
        else:
            st.warning("📭 Ingen data i databasen ännu")
            
    except Exception as e:
        st.error(f"❌ Kunde inte hämta databas-status: {e}")
    
    # Knappar för extra funktioner
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Ladda från databas", help="Ladda senaste värde från Firebase"):
            loaded_value = load_test_value()
            st.session_state.test_value = loaded_value
            st.success(f"✅ Laddade värde: {loaded_value}")
            st.rerun()
    
    with col2:
        if st.button("🗑️ Rensa test-data", help="Ta bort test-data från Firebase"):
            try:
                firebase_db = get_firebase_db()
                test_ref = firebase_db.get_ref("test_input")
                test_ref.remove(firebase_db._get_token())
                st.session_state.test_value = 0.0
                st.success("✅ Test-data rensad!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Fel vid rensning: {e}")
    
    with col3:
        if st.button("🎲 Slumpmässigt värde", help="Sätt ett slumpmässigt testvärde"):
            import random
            random_value = round(random.uniform(1, 1000), 2)
            if save_test_value(random_value):
                st.session_state.test_value = random_value
                st.success(f"✅ Sparat slumpmässigt värde: {random_value}")
                st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <small>
    **🧪 Test-läge aktiverat**<br>
    Data sparas i Firebase Realtime Database under noden 'test_input'<br>
    Perfekt för att testa automatisk sparning och databasanslutning!
    </small>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    show_test_input()
