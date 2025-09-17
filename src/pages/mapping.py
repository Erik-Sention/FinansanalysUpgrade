"""
Kategorimappning interface
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional
from sqlmodel import Session, select

from utils.database_helpers import get_session, get_account_categories
from models.database import (
    RawLabel, Account, AccountCategory, AccountMapping, 
    Company, Dataset, Value
)

def get_all_mappings() -> pd.DataFrame:
    """Hämta alla mappningar"""
    from models.database import get_engine
    engine = get_engine()
    
    query = """
    SELECT 
        rl.id as raw_label_id,
        rl.label as raw_label,
        a.id as account_id,
        a.name as account_name,
        ac.name as category_name,
        am.confidence,
        am.id as mapping_id
    FROM raw_labels rl
    LEFT JOIN account_mappings am ON rl.id = am.raw_label_id
    LEFT JOIN accounts a ON am.account_id = a.id
    LEFT JOIN account_categories ac ON a.category_id = ac.id
    ORDER BY rl.label
    """
    
    df = pd.read_sql_query(query, engine)
    return df

def get_unmapped_labels() -> List[RawLabel]:
    """Hämta omappade etiketter"""
    with get_session() as session:
        query = """
        SELECT rl.* FROM raw_labels rl
        LEFT JOIN account_mappings am ON rl.id = am.raw_label_id
        WHERE am.id IS NULL
        """
        
        result = session.exec(query).all()
        return list(result)

def create_account_mapping(raw_label_id: int, account_id: int, confidence: float = 1.0) -> bool:
    """Skapa ny mappning"""
    try:
        with get_session() as session:
            # Kontrollera om mappning redan finns
            existing = session.exec(
                select(AccountMapping).where(AccountMapping.raw_label_id == raw_label_id)
            ).first()
            
            if existing:
                # Uppdatera befintlig
                existing.account_id = account_id
                existing.confidence = confidence
            else:
                # Skapa ny
                mapping = AccountMapping(
                    raw_label_id=raw_label_id,
                    account_id=account_id,
                    confidence=confidence
                )
                session.add(mapping)
            
            session.commit()
            return True
            
    except Exception as e:
        st.error(f"Kunde inte skapa mappning: {e}")
        return False

def delete_mapping(mapping_id: int) -> bool:
    """Ta bort mappning"""
    try:
        with get_session() as session:
            mapping = session.get(AccountMapping, mapping_id)
            if mapping:
                session.delete(mapping)
                session.commit()
                return True
            return False
            
    except Exception as e:
        st.error(f"Kunde inte ta bort mappning: {e}")
        return False

def create_new_account(name: str, category_id: int, description: str = "") -> Optional[Account]:
    """Skapa nytt konto"""
    try:
        with get_session() as session:
            account = Account(
                name=name,
                category_id=category_id,
                description=description
            )
            session.add(account)
            session.commit()
            session.refresh(account)
            return account
            
    except Exception as e:
        st.error(f"Kunde inte skapa konto: {e}")
        return None

def get_all_accounts() -> pd.DataFrame:
    """Hämta alla konton"""
    from models.database import get_engine
    engine = get_engine()
    
    query = """
    SELECT 
        a.id,
        a.name,
        ac.name as category_name,
        a.description
    FROM accounts a
    JOIN account_categories ac ON a.category_id = ac.id
    ORDER BY ac.name, a.name
    """
    
    df = pd.read_sql_query(query, engine)
    return df

def get_mapping_statistics() -> Dict:
    """Hämta mappningsstatistik"""
    from models.database import get_engine
    engine = get_engine()
    
    import pandas as pd
    
    total_labels = pd.read_sql_query("SELECT COUNT(*) as count FROM raw_labels", engine).iloc[0]['count']
    mapped_labels = pd.read_sql_query("SELECT COUNT(*) as count FROM account_mappings", engine).iloc[0]['count']
    auto_mapped = pd.read_sql_query("SELECT COUNT(*) as count FROM account_mappings WHERE confidence < 1.0", engine).iloc[0]['count']
    
    return {
        'total_labels': total_labels,
        'mapped_labels': mapped_labels,
        'unmapped_labels': total_labels - mapped_labels,
        'auto_mapped': auto_mapped,
        'manual_mapped': mapped_labels - auto_mapped
    }

def show():
    """Visa kategorimappning sidan"""
    st.title("🔗 Kategorimappning")
    st.markdown("Hantera mappning mellan Excel-etiketter och kontokategorier")
    
    # Kontrollera databas
    try:
        stats = get_mapping_statistics()
    except Exception as e:
        st.error(f"Databasfel: {e}")
        return
    
    # Statistik-kort
    st.markdown("### 📊 Mappningsstatistik")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Totala etiketter", stats['total_labels'])
    
    with col2:
        st.metric("Mappade etiketter", stats['mapped_labels'])
    
    with col3:
        st.metric("Omappade etiketter", stats['unmapped_labels'])
    
    with col4:
        if stats['total_labels'] > 0:
            completion = (stats['mapped_labels'] / stats['total_labels']) * 100
            st.metric("Färdigställning", f"{completion:.1f}%")
        else:
            st.metric("Färdigställning", "0%")
    
    # Tabs för olika vyer
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Alla mappningar", 
        "❓ Omappade etiketter", 
        "➕ Skapa konto",
        "🛠️ Hantera konton"
    ])
    
    with tab1:
        st.markdown("#### Alla mappningar")
        
        try:
            mappings_df = get_all_mappings()
            
            if not mappings_df.empty:
                # Filter-alternativ
                col1, col2 = st.columns(2)
                
                with col1:
                    category_filter = st.selectbox(
                        "Filtrera efter kategori",
                        ["Alla"] + list(mappings_df['category_name'].dropna().unique()),
                        key="mapping_category_filter"
                    )
                
                with col2:
                    confidence_filter = st.selectbox(
                        "Filtrera efter typ",
                        ["Alla", "Automatisk (< 1.0)", "Manuell (1.0)"],
                        key="mapping_confidence_filter"
                    )
                
                # Tillämpa filter
                filtered_df = mappings_df.copy()
                
                if category_filter != "Alla":
                    filtered_df = filtered_df[filtered_df['category_name'] == category_filter]
                
                if confidence_filter == "Automatisk (< 1.0)":
                    filtered_df = filtered_df[filtered_df['confidence'] < 1.0]
                elif confidence_filter == "Manuell (1.0)":
                    filtered_df = filtered_df[filtered_df['confidence'] == 1.0]
                
                # Visa tabell
                display_columns = ['raw_label', 'account_name', 'category_name', 'confidence']
                if not filtered_df.empty:
                    st.dataframe(
                        filtered_df[display_columns].fillna('(Omappad)'),
                        use_container_width=True
                    )
                    
                    # Redigera mappning
                    st.markdown("##### ✏️ Redigera mappning")
                    
                    selected_label = st.selectbox(
                        "Välj etikett att redigera",
                        filtered_df['raw_label'].tolist(),
                        key="edit_mapping_label"
                    )
                    
                    if selected_label:
                        # Hämta tillgängliga konton
                        accounts_df = get_all_accounts()
                        account_options = {
                            f"{row['name']} ({row['category_name']})": row['id'] 
                            for _, row in accounts_df.iterrows()
                        }
                        
                        # Nuvarande mappning
                        current_mapping = filtered_df[filtered_df['raw_label'] == selected_label].iloc[0]
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if pd.notna(current_mapping['account_name']):
                                current_option = f"{current_mapping['account_name']} ({current_mapping['category_name']})"
                                current_index = list(account_options.keys()).index(current_option) if current_option in account_options else 0
                            else:
                                current_index = 0
                            
                            new_account = st.selectbox(
                                "Nytt konto",
                                list(account_options.keys()),
                                index=current_index,
                                key="edit_new_account"
                            )
                        
                        with col2:
                            confidence = st.slider(
                                "Konfidensgrad",
                                0.0, 1.0, 
                                value=float(current_mapping['confidence']) if pd.notna(current_mapping['confidence']) else 1.0,
                                step=0.1,
                                key="edit_confidence"
                            )
                        
                        if st.button("💾 Uppdatera mappning"):
                            if create_account_mapping(
                                current_mapping['raw_label_id'],
                                account_options[new_account],
                                confidence
                            ):
                                st.success("✅ Mappning uppdaterad!")
                                st.rerun()
                        
                        # Ta bort mappning
                        if pd.notna(current_mapping['mapping_id']):
                            if st.button("🗑️ Ta bort mappning", type="secondary"):
                                if delete_mapping(int(current_mapping['mapping_id'])):
                                    st.success("✅ Mappning borttagen!")
                                    st.rerun()
                
                else:
                    st.info("Inga mappningar hittade med valda filter")
            else:
                st.info("Inga mappningar hittade")
                
        except Exception as e:
            st.error(f"Kunde inte hämta mappningar: {e}")
    
    with tab2:
        st.markdown("#### Omappade etiketter")
        
        try:
            unmapped = get_unmapped_labels()
            
            if unmapped:
                st.info(f"Hittade {len(unmapped)} omappade etiketter")
                
                # Bulk-mappning
                accounts_df = get_all_accounts()
                account_options = {
                    f"{row['name']} ({row['category_name']})": row['id'] 
                    for _, row in accounts_df.iterrows()
                }
                
                for label in unmapped[:10]:  # Visa max 10 åt gången
                    st.markdown(f"**{label.label}**")
                    
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        selected_account = st.selectbox(
                            "Mappa till konto",
                            ["-- Välj konto --"] + list(account_options.keys()),
                            key=f"map_{label.id}"
                        )
                    
                    with col2:
                        confidence = st.slider(
                            "Konfidensgrad",
                            0.0, 1.0, 1.0,
                            step=0.1,
                            key=f"conf_{label.id}"
                        )
                    
                    with col3:
                        if st.button("💾", key=f"save_{label.id}"):
                            if selected_account != "-- Välj konto --":
                                if create_account_mapping(
                                    label.id,
                                    account_options[selected_account],
                                    confidence
                                ):
                                    st.success("✅")
                                    st.rerun()
                    
                    st.markdown("---")
                
                if len(unmapped) > 10:
                    st.info(f"Visar första 10 av {len(unmapped)} omappade etiketter")
            else:
                st.success("🎉 Alla etiketter är mappade!")
                
        except Exception as e:
            st.error(f"Kunde inte hämta omappade etiketter: {e}")
    
    with tab3:
        st.markdown("#### Skapa nytt konto")
        
        try:
            categories = get_account_categories()
            category_options = {cat.name: cat.id for cat in categories}
            
            with st.form("create_account_form"):
                account_name = st.text_input("Kontonamn")
                
                selected_category = st.selectbox(
                    "Kategori",
                    list(category_options.keys())
                )
                
                description = st.text_area("Beskrivning (valfritt)")
                
                submitted = st.form_submit_button("🆕 Skapa konto")
                
                if submitted:
                    if account_name and selected_category:
                        new_account = create_new_account(
                            account_name,
                            category_options[selected_category],
                            description
                        )
                        
                        if new_account:
                            st.success(f"✅ Konto '{account_name}' skapat!")
                            st.rerun()
                    else:
                        st.error("Ange kontonamn och kategori")
                        
        except Exception as e:
            st.error(f"Kunde inte skapa konto: {e}")
    
    with tab4:
        st.markdown("#### Hantera konton")
        
        try:
            accounts_df = get_all_accounts()
            
            if not accounts_df.empty:
                # Filter efter kategori
                category_filter = st.selectbox(
                    "Filtrera efter kategori",
                    ["Alla"] + list(accounts_df['category_name'].unique()),
                    key="account_category_filter"
                )
                
                if category_filter != "Alla":
                    filtered_accounts = accounts_df[accounts_df['category_name'] == category_filter]
                else:
                    filtered_accounts = accounts_df
                
                # Visa tabell
                st.dataframe(
                    filtered_accounts[['name', 'category_name', 'description']],
                    use_container_width=True
                )
                
                # Konto-statistik
                st.markdown("##### 📊 Kontostatistik")
                
                for category in accounts_df['category_name'].unique():
                    count = len(accounts_df[accounts_df['category_name'] == category])
                    st.metric(f"Konton i {category}", count)
            else:
                st.info("Inga konton hittade")
                
        except Exception as e:
            st.error(f"Kunde inte hämta konton: {e}")
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <small>
    **Mappningshantering**<br>
    **Senast uppdaterad:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
    </small>
    """, unsafe_allow_html=True)
