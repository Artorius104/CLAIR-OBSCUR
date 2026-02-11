import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from database.getDataFromDatabase import *
from datetime import datetime, timedelta
import time

# Configuration de la page
st.set_page_config(
    page_title="Firewall Logs Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Titre principal
st.title("🛡️ Firewall Logs Analysis Dashboard")
st.markdown("---")

# Sidebar pour les filtres
with st.sidebar:
    st.header("⚙️ Filtres")
    
    # Sélection de la période
    time_range = st.selectbox(
        "Période d'analyse",
        [
            "Dernière heure", 
            "Dernières 6 heures", 
            "Dernières 24 heures", 
            "Derniers 7 jours", 
            "Derniers 10 jours",
            "Derniers 100 jours",
            "Tout"
        ],
        index=0
    )
    
    st.info("💡 Les données sont mises à jour automatiquement en arrière-plan par le Consumer Kafka.")
    
# Fonction pour charger les données
@st.cache_data(ttl=60)
def load_data(time_range_selection):
    time_filter = None
    
    try:
        # Récupérer la date du dernier log pour ancrer l'analyse
        # C'est CRITIQUE pour que les données s'affichent si elles sont anciennes
        last_log_time = get_last_log_time()
        
        if last_log_time and time_range_selection != "Tout":
            if time_range_selection == "Dernière heure":
                time_filter = last_log_time - timedelta(hours=1)
            elif time_range_selection == "Dernières 6 heures":
                time_filter = last_log_time - timedelta(hours=6)
            elif time_range_selection == "Dernières 24 heures":
                time_filter = last_log_time - timedelta(hours=24)
            elif time_range_selection == "Derniers 7 jours":
                time_filter = last_log_time - timedelta(days=7)
            elif time_range_selection == "Derniers 10 jours":
                time_filter = last_log_time - timedelta(days=10)
            elif time_range_selection == "Derniers 100 jours":
                time_filter = last_log_time - timedelta(days=100)
        elif not last_log_time:
            # Fallback si pas de données
            pass
            
        global_stats = get_global_stats(time_filter)
        stats_by_firewall = get_stats_by_firewall(time_filter)
        stats_by_protocol = get_stats_by_protocol(time_filter)
        recent_logs = get_recent_logs(100) 
        return global_stats, stats_by_firewall, stats_by_protocol, recent_logs, last_log_time
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {e}")
        return None, None, None, None, None

# Charger les données
with st.spinner("Chargement des données..."):
    # On force le rafraichissement du cache si nécessaire, mais ici on laisse le ttl faire son travail
    # L'utilisateur a demandé d'enlever le bouton de refresh explicite
    global_stats, stats_by_firewall, stats_by_protocol, recent_logs, last_db_time = load_data(time_range)

if last_db_time:
    st.sidebar.info(f"📅 Dernier log en base : {last_db_time.strftime('%d/%m/%Y %H:%M')}")

if global_stats is not None and not global_stats.empty:
    stats = global_stats.iloc[0]
    
    # KPIs principaux
    st.header("📊 Vue d'ensemble")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Gérer le cas où la base de données est vide (après clean)
    total = int(stats['total_logs'] or 0)
    allowed = int(stats['allowed_count'] or 0)
    denied = int(stats['denied_count'] or 0)
    
    with col1:
        st.metric(
            "Total des logs",
            f"{total:,}",
            help="Nombre total de logs enregistrés"
        )
    
    with col2:
        percentage = (allowed / total * 100) if total > 0 else 0
        st.metric(
            "Connexions autorisées",
            f"{allowed:,}",
            f"{percentage:.1f}%",
            delta_color="normal"
        )
    
    with col3:
        percentage = (denied / total * 100) if total > 0 else 0
        st.metric(
            "Connexions bloquées",
            f"{denied:,}",
            f"{percentage:.1f}%",
            delta_color="inverse"
        )
    
    with col4:
        unique_ips = int(stats['unique_src_ips'] or 0)
        st.metric(
            "IPs sources uniques",
            f"{unique_ips:,}",
            help="Nombre d'adresses IP sources distinctes"
        )
    
    with col5:
        total_bytes = stats['total_bytes'] or 0
        bytes_gb = total_bytes / (1024**3) if pd.notna(total_bytes) and total_bytes > 0 else 0
        st.metric(
            "Volume total",
            f"{bytes_gb:.2f} GB",
            help="Volume total de données transférées"
        )
    
    st.markdown("---")
    
    # Graphiques principaux
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📈 Distribution Actions (ALLOW vs DENY)")
        
        if stats_by_protocol is not None and not stats_by_protocol.empty:
            # Créer un DataFrame pour le graphique
            action_data = pd.DataFrame({
                'Action': ['ALLOW', 'DENY'],
                'Count': [int(stats['allowed_count']), int(stats['denied_count'])]
            })
            
            fig = px.pie(
                action_data,
                values='Count',
                names='Action',
                color='Action',
                color_discrete_map={'ALLOW': '#28a745', 'DENY': '#dc3545'},
                hole=0.4
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(showlegend=True, height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_right:
        st.subheader("🌐 Distribution par Protocole")
        
        if stats_by_protocol is not None and not stats_by_protocol.empty:
            fig = px.bar(
                stats_by_protocol,
                x='protocol',
                y='total_logs',
                color='protocol',
                text='total_logs',
                title="",
                labels={'total_logs': 'Nombre de logs', 'protocol': 'Protocole'}
            )
            fig.update_traces(texttemplate='%{text:,}', textposition='outside')
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Statistiques par Firewall
    st.subheader("🔥 Statistiques par Firewall")
    
    if stats_by_firewall is not None and not stats_by_firewall.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Graphique en barres
            fig = px.bar(
                stats_by_firewall,
                x='firewall_id',
                y='total_logs',
                color='firewall_id',
                title="Logs par Firewall",
                labels={'total_logs': 'Nombre de logs', 'firewall_id': 'Firewall'}
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Graphique empilé ALLOW vs DENY par firewall
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='ALLOW',
                x=stats_by_firewall['firewall_id'],
                y=stats_by_firewall['allowed_count'],
                marker_color='#28a745'
            ))
            fig.add_trace(go.Bar(
                name='DENY',
                x=stats_by_firewall['firewall_id'],
                y=stats_by_firewall['denied_count'],
                marker_color='#dc3545'
            ))
            fig.update_layout(
                barmode='stack',
                title="ALLOW vs DENY par Firewall",
                xaxis_title="Firewall",
                yaxis_title="Nombre d'événements",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Tableau détaillé
        st.dataframe(
            stats_by_firewall.style.format({
                'total_logs': '{:,.0f}',
                'allowed_count': '{:,.0f}',
                'denied_count': '{:,.0f}',
                'total_bytes': '{:,.0f}',
                'avg_duration_ms': '{:.2f}',
                'unique_src_ips': '{:,.0f}',
                'unique_dst_ips': '{:,.0f}'
            }),
            use_container_width=True
        )
    
    st.markdown("---")
    
    # Top IPs et Ports
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌍 Top 10 IPs Sources")
        try:
            top_src_ips = get_top_src_ips(10)
            if not top_src_ips.empty:
                fig = px.bar(
                    top_src_ips,
                    x='connection_count',
                    y='src_ip',
                    orientation='h',
                    text='connection_count',
                    title="",
                    labels={'connection_count': 'Connexions', 'src_ip': 'IP Source'}
                )
                fig.update_traces(texttemplate='%{text:,}', textposition='outside')
                fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erreur: {e}")
    
    with col2:
        st.subheader("🎯 Top 10 IPs Bloquées")
        try:
            top_blocked = get_top_blocked_ips(10)
            if not top_blocked.empty:
                fig = px.bar(
                    top_blocked,
                    x='block_count',
                    y='src_ip',
                    orientation='h',
                    text='block_count',
                    color='block_count',
                    color_continuous_scale='Reds',
                    title="",
                    labels={'block_count': 'Blocages', 'src_ip': 'IP Source'}
                )
                fig.update_traces(texttemplate='%{text:,}', textposition='outside')
                fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erreur: {e}")
    
    st.markdown("---")
    
    # Logs récents
    st.subheader("📋 Logs Récents")
    
    if recent_logs is not None and not recent_logs.empty:
        # Filtres pour les logs
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_action = st.selectbox("Action", ["Tous", "ALLOW", "DENY"])
        with col2:
            filter_protocol = st.selectbox("Protocole", ["Tous"] + recent_logs['protocol'].unique().tolist())
        with col3:
            filter_firewall = st.selectbox("Firewall", ["Tous"] + recent_logs['firewall_id'].unique().tolist())
        
        # Appliquer les filtres
        filtered_logs = recent_logs.copy()
        if filter_action != "Tous":
            filtered_logs = filtered_logs[filtered_logs['action'] == filter_action]
        if filter_protocol != "Tous":
            filtered_logs = filtered_logs[filtered_logs['protocol'] == filter_protocol]
        if filter_firewall != "Tous":
            filtered_logs = filtered_logs[filtered_logs['firewall_id'] == filter_firewall]
        
        # Afficher le tableau
        st.dataframe(
            filtered_logs[[
                'timestamp', 'firewall_id', 'src_ip', 'dst_ip', 
                'src_port', 'dst_port', 'protocol', 'action', 'bytes', 'status'
            ]].style.apply(
                lambda x: ['background-color: #ffebee' if x['action'] == 'DENY' else '' for _ in x],
                axis=1
            ),
            use_container_width=True,
            height=400
        )
        
        # Bouton de téléchargement
        csv = filtered_logs.to_csv(index=False)
        st.download_button(
            label="📥 Télécharger les logs (CSV)",
            data=csv,
            file_name=f"firewall_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

else:
    st.warning("⚠️ Aucune donnée disponible. Vérifiez que le Consumer a bien inséré des données dans la base PostgreSQL.")
    st.info("💡 Conseil : Vérifiez les logs du Consumer et assurez-vous que la connexion à PostgreSQL fonctionne.")

# Footer
st.markdown("---")
st.caption(f"Dashboard mis à jour le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
