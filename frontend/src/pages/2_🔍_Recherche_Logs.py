import streamlit as st
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.getDataFromDatabase import *
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Recherche de Logs",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Recherche Avancée de Logs")
st.markdown("---")

# Formulaire de recherche
with st.form("search_form"):
    st.subheader("Critères de recherche")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        firewall_id = st.text_input("Firewall ID (ex: FW-A)")
        src_ip = st.text_input("IP Source")
        protocol = st.selectbox("Protocole", ["", "TCP", "UDP", "ICMP"])
    
    with col2:
        dst_ip = st.text_input("IP Destination")
        src_port = st.number_input("Port Source", min_value=0, max_value=65535, value=0)
        action = st.selectbox("Action", ["", "ALLOW", "DENY"])
    
    with col3:
        dst_port = st.number_input("Port Destination", min_value=0, max_value=65535, value=0)
        limit = st.number_input("Nombre maximum de résultats", min_value=100, max_value=10000, value=1000, step=100)
    
    # Période
    st.subheader("Période")
    use_date_filter = st.checkbox("Filtrer par date", value=False)
    
    col_date1, col_date2 = st.columns(2)
    
    # Récupérer le dernier log pour initialiser
    last_log_time = get_last_log_time()
    default_end = last_log_time if last_log_time else datetime.now()
    default_start = default_end - timedelta(hours=1)
    
    start_time_val = None
    end_time_val = None
    
    if use_date_filter:
        with col_date1:
            start_date = st.date_input("Date de début", value=default_start)
            start_time = st.time_input("Heure de début", value=default_start.time())
        with col_date2:
            end_date = st.date_input("Date de fin", value=default_end)
            end_time = st.time_input("Heure de fin", value=default_end.time())
            
        start_time_val = datetime.combine(start_date, start_time)
        end_time_val = datetime.combine(end_date, end_time)
    
    # Boutons
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        submit = st.form_submit_button("🔎 Rechercher", use_container_width=True)
    with col_btn2:
        clear = st.form_submit_button("🗑️ Réinitialiser", use_container_width=True)

if clear:
    st.rerun()

if submit:
    # Construire les paramètres de recherche
    with st.spinner("Recherche en cours..."):
        try:
            # Construire la requête
            conditions = []
            params = {}
            
            if firewall_id:
                conditions.append("firewall_id = %(firewall_id)s")
                params['firewall_id'] = firewall_id
            
            if src_ip:
                conditions.append("src_ip = %(src_ip)s")
                params['src_ip'] = src_ip
            
            if dst_ip:
                conditions.append("dst_ip = %(dst_ip)s")
                params['dst_ip'] = dst_ip
            
            if protocol:
                conditions.append("protocol = %(protocol)s")
                params['protocol'] = protocol
            
            if action:
                conditions.append("action = %(action)s")
                params['action'] = action
            
            if src_port > 0:
                conditions.append("src_port = %(src_port)s")
                params['src_port'] = src_port
            
            if dst_port > 0:
                conditions.append("dst_port = %(dst_port)s")
                params['dst_port'] = dst_port
            
            if use_date_filter and start_time_val and end_time_val:
                conditions.append("timestamp >= %(start_time)s")
                params['start_time'] = start_time_val
                
                conditions.append("timestamp <= %(end_time)s")
                params['end_time'] = end_time_val
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
                SELECT * FROM firewall_logs
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT {limit};
            """
            
            # Exécuter la recherche
            # Note: query_db function accepts direct string, so we inject values in f-string above implies we trust input or need parameterization.
            # But the original code was f-string based. To use params properly with psycopg2/pandas we need a different call.
            # Assuming query_db takes raw sql. I will construct SQL using python string interpolation safely enough for this hackathon context 
            # or revert to previous "search_logs" function usage if simpler.
            # Actually, reusing `search_logs` from DB module is CLEANER.
            
            logs = search_logs(
                firewall_id=firewall_id if firewall_id else None,
                src_ip=src_ip if src_ip else None,
                dst_ip=dst_ip if dst_ip else None,
                protocol=protocol if protocol else None,
                action=action if action else None,
                start_time=start_time_val if use_date_filter else None,
                end_time=end_time_val if use_date_filter else None,
                limit=limit
            )
            
            results = logs
            
            if not results.empty:
                st.success(f"✅ {len(results)} résultat(s) trouvé(s)")
                
                # Statistiques rapides
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total logs", len(results))
                
                with col2:
                    allowed = len(results[results['action'] == 'ALLOW'])
                    st.metric("ALLOW", allowed, f"{allowed/len(results)*100:.1f}%")
                
                with col3:
                    denied = len(results[results['action'] == 'DENY'])
                    st.metric("DENY", denied, f"{denied/len(results)*100:.1f}%")
                
                with col4:
                    total_bytes = results['bytes'].sum() / (1024**2)  # Convert to MB
                    st.metric("Volume", f"{total_bytes:.2f} MB")
                
                st.markdown("---")
                
                # Graphiques rapides
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    st.subheader("Distribution des Protocoles")
                    protocol_dist = results['protocol'].value_counts()
                    st.bar_chart(protocol_dist)
                
                with col_chart2:
                    st.subheader("Actions dans le temps")
                    results['hour'] = pd.to_datetime(results['timestamp']).dt.hour
                    hourly_actions = results.groupby(['hour', 'action']).size().unstack(fill_value=0)
                    st.line_chart(hourly_actions)
                
                st.markdown("---")
                
                # Tableau des résultats
                st.subheader("📋 Résultats détaillés")
                
                # Mise en forme du tableau
                display_columns = [
                    'timestamp', 'firewall_id', 'src_ip', 'dst_ip',
                    'src_port', 'dst_port', 'protocol', 'action',
                    'bytes', 'duration_ms', 'rule_id', 'status'
                ]
                
                # Appliquer un style conditionnel
                def highlight_action(row):
                    if row['action'] == 'DENY':
                        return ['background-color: #ffebee'] * len(row)
                    elif row['action'] == 'ALLOW':
                        return ['background-color: #e8f5e9'] * len(row)
                    return [''] * len(row)
                
                styled_df = results[display_columns].style.apply(highlight_action, axis=1)
                
                st.dataframe(styled_df, use_container_width=True, height=600)
                
                # Bouton de téléchargement
                col_dl1, col_dl2, col_dl3 = st.columns([1, 1, 2])
                
                with col_dl1:
                    csv = results.to_csv(index=False)
                    st.download_button(
                        label="📥 Télécharger CSV",
                        data=csv,
                        file_name=f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col_dl2:
                    # Bouton pour télécharger uniquement les DENY
                    denied_logs = results[results['action'] == 'DENY']
                    if not denied_logs.empty:
                        csv_denied = denied_logs.to_csv(index=False)
                        st.download_button(
                            label="📥 Télécharger DENY",
                            data=csv_denied,
                            file_name=f"denied_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                
            else:
                st.warning("⚠️ Aucun résultat trouvé pour les critères spécifiés.")
                st.info("💡 Essayez d'élargir vos critères de recherche.")
        
        except Exception as e:
            st.error(f"❌ Erreur lors de la recherche: {e}")

else:
    st.info("👆 Remplissez les critères de recherche ci-dessus et cliquez sur 'Rechercher'")
    
    # Afficher les logs les plus récents par défaut
    st.subheader("📋 Logs Récents (100 derniers)")
    
    try:
        recent_logs = get_recent_logs(100)
        
        if not recent_logs.empty:
            display_columns = [
                'timestamp', 'firewall_id', 'src_ip', 'dst_ip',
                'src_port', 'dst_port', 'protocol', 'action', 'bytes'
            ]
            
            def highlight_action(row):
                if row['action'] == 'DENY':
                    return ['background-color: #ffebee'] * len(row)
                elif row['action'] == 'ALLOW':
                    return ['background-color: #e8f5e9'] * len(row)
                return [''] * len(row)
            
            styled_df = recent_logs[display_columns].style.apply(highlight_action, axis=1)
            st.dataframe(styled_df, use_container_width=True, height=500)
    
    except Exception as e:
        st.error(f"Erreur: {e}")

st.markdown("---")
st.caption(f"Dashboard mis à jour le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
